#!/usr/bin/env python3
import os
import sys

# Disable accessibility bridge to eliminate 250-500ms D-Bus timeouts
os.environ["NO_AT_BRIDGE"] = "1"
os.environ["GTK_A11Y"] = "none"

import re
import json
import signal
import subprocess
import urllib.parse
import ast
import operator as op
import glob

# Ensure system paths for icons & MIME
xdg = os.environ.get("XDG_DATA_DIRS", "")
std_dirs = "/usr/share:/usr/local/share:" + os.path.expanduser("~/.local/share")
if "/usr/share" not in xdg:
    os.environ["XDG_DATA_DIRS"] = std_dirs + (":" + xdg if xdg else "")

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell
import cairo

PID_FILE = "/tmp/smart-launcher.pid"

def check_single_instance():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
            os.remove(PID_FILE)
            sys.exit(0)
        except Exception:
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def cleanup_pid():
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

def eval_math(expr):
    clean = expr.strip().replace(" ", "").replace("^", "**").replace("x", "*").replace("X", "*")
    if not clean or not any(c in clean for c in "+-*/%"):
        return None
    valid_chars = set("0123456789+-*/%.()eE")
    if not all(c in valid_chars for c in clean):
        return None
    
    allowed_ops = {
        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
        ast.Div: op.truediv, ast.Pow: op.pow, ast.Mod: op.mod,
        ast.USub: op.neg, ast.UAdd: op.pos
    }
    def _eval(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return allowed_ops[type(node.op)](_eval(node.operand))
        raise ValueError()
    try:
        tree = ast.parse(clean, mode="eval")
        res = _eval(tree.body)
        if isinstance(res, float) and res.is_integer():
            return int(res)
        if isinstance(res, float):
            return round(res, 6)
        return res
    except Exception:
        return None

EXCLUDE_BASENAMES = {
    "foot-server.desktop", "footclient.desktop",
    "libreoffice-startcenter.desktop",
    "scrcpy-console.desktop",
    "idle-python3.11.desktop",
    "debian-uxterm.desktop", "uxterm.desktop",
    "nemo.desktop", "nemo-autorun-software.desktop", "nemo-autostart.desktop",
    "systemsettings.desktop",
    "software-properties-drivers.desktop", "software-properties-livepatch.desktop",
}

POPULAR_PRIORITY = [
    "org.mozilla.firefox.desktop",
    "org.telegram.desktop.desktop",
    "code.desktop",
    "cursor.desktop",
    "Alacritty.desktop",
    "org.gnome.Nautilus.desktop",
    "google-chrome.desktop",
    "dev.zed.Zed.desktop",
    "org.flameshot.Flameshot.desktop",
    "org.localsend.localsend_app.desktop",
    "vlc.desktop",
    "com.rustdesk.RustDesk.desktop",
    "antigravity.desktop",
    "devin-desktop.desktop",
    "stacer.desktop",
    "btop.desktop",
]

APP_ALIASES = {
    "org.telegram.desktop.desktop": ["tg", "tele", "tlg", "chat", "yozishma"],
    "org.mozilla.firefox.desktop": ["firefox", "browser", "web", "internet", "brauzer", "fox"],
    "google-chrome.desktop": ["chrome", "google", "browser", "web", "brauzer"],
    "code.desktop": ["code", "vscode", "vsc", "visual studio code", "vs"],
    "cursor.desktop": ["cursor", "ai code", "editor", "vsc"],
    "dev.zed.Zed.desktop": ["zed", "editor", "text editor"],
    "Alacritty.desktop": ["term", "terminal", "console", "alacritty"],
    "foot.desktop": ["term", "terminal", "foot"],
    "nemo.desktop": ["nemo", "fayllar", "file", "files", "fayl", "folder", "papka"],
    "org.gnome.Nautilus.desktop": ["nautilus", "file", "files", "fayl"],
    "org.flameshot.Flameshot.desktop": ["screenshot", "skrinshot", "ekran", "rasm", "snip"],
    "libreoffice-calc.desktop": ["calc", "hisob", "excel", "jadval"],
    "libreoffice-writer.desktop": ["word", "hujjat", "doc", "yozuv"],
    "pavucontrol.desktop": ["sound", "audio", "volume", "ovoz"],
    "blueman-manager.desktop": ["bluetooth", "blutuz"],
    "nm-connection-editor.desktop": ["wifi", "tarmoq", "network", "internet"],
}

THEME_ICON_MAP = {
    "vscode": "com.visualstudio.code",
    "rustdesk-logo": "rustdesk",
}

_SURFACE_CACHE = {}
_ICON_RESOLVE_CACHE = {}

def load_scaled_png_surface(filepath, target_size=32):
    cache_key = (filepath, target_size)
    if cache_key in _SURFACE_CACHE:
        return _SURFACE_CACHE[cache_key]
    try:
        src = cairo.ImageSurface.create_from_png(filepath)
        w, h = src.get_width(), src.get_height()
        dest = cairo.ImageSurface(cairo.FORMAT_ARGB32, target_size, target_size)
        cr = cairo.Context(dest)
        scale = target_size / max(w, h)
        cr.scale(scale, scale)
        cr.set_source_surface(src, 0, 0)
        cr.paint()
        _SURFACE_CACHE[cache_key] = dest
        return dest
    except Exception:
        return None

def resolve_icon(icon_name, theme):
    if not icon_name:
        return ("name", "application-x-executable")
    if icon_name in _ICON_RESOLVE_CACHE:
        return _ICON_RESOLVE_CACHE[icon_name]

    if icon_name in THEME_ICON_MAP:
        mapped = THEME_ICON_MAP[icon_name]
        if theme.has_icon(mapped):
            res = ("name", mapped)
            _ICON_RESOLVE_CACHE[icon_name] = res
            return res

    if os.path.isabs(icon_name) and os.path.exists(icon_name) and icon_name.endswith(".png"):
        res = ("surface_file", icon_name)
        _ICON_RESOLVE_CACHE[icon_name] = res
        return res

    # Check /usr/share/pixmaps
    pixmap_path = f"/usr/share/pixmaps/{icon_name}.png"
    if os.path.exists(pixmap_path):
        res = ("surface_file", pixmap_path)
        _ICON_RESOLVE_CACHE[icon_name] = res
        return res

    if theme.has_icon(icon_name):
        res = ("name", icon_name)
        _ICON_RESOLVE_CACHE[icon_name] = res
        return res

    res = ("name", "application-x-executable")
    _ICON_RESOLVE_CACHE[icon_name] = res
    return res

def create_icon_widget(icon_name, theme, size=32):
    kind, val = resolve_icon(icon_name, theme)
    if kind == "surface_file":
        s = load_scaled_png_surface(val, size)
        if s:
            return Gtk.Image.new_from_surface(s)
        kind, val = "name", "application-x-executable"

    img = Gtk.Image.new_from_icon_name(val, Gtk.IconSize.LARGE_TOOLBAR)
    img.set_pixel_size(size)
    return img

APPS_CACHE_FILE = os.path.expanduser("~/.cache/smart_launcher_apps.json")

def get_apps_cache_mtime(dirs):
    latest = 0.0
    for d in dirs:
        if os.path.isdir(d):
            try:
                m = os.path.getmtime(d)
                if m > latest:
                    latest = m
            except OSError:
                pass
    return latest

def load_desktop_apps():
    dirs = [
        os.path.expanduser("~/.local/share/applications"),
        "/usr/local/share/applications",
        "/usr/share/applications",
        "/var/lib/flatpak/exports/share/applications",
        os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
    ]

    # Fast path: load cached apps if newer than application dirs
    if os.path.exists(APPS_CACHE_FILE):
        try:
            cache_mtime = os.path.getmtime(APPS_CACHE_FILE)
            dirs_mtime = get_apps_cache_mtime(dirs)
            if cache_mtime >= dirs_mtime:
                with open(APPS_CACHE_FILE, "r", encoding="utf-8") as f:
                    cached_apps = json.load(f)
                    if cached_apps:
                        return cached_apps
        except Exception:
            pass

    apps = []
    seen_ids = set()
    seen_normalized_names = {}

    for d in dirs:
        if not os.path.isdir(d):
            continue
        for f in sorted(glob.glob(d + "/**/*.desktop", recursive=True)):
            base = os.path.basename(f)
            if base in EXCLUDE_BASENAMES or base in seen_ids:
                continue

            name, comment, exec_cmd, icon, nodisplay = None, "", None, None, False
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    in_entry = False
                    for line in fp:
                        line = line.strip()
                        if line == "[Desktop Entry]":
                            in_entry = True
                            continue
                        elif line.startswith("[") and in_entry:
                            break
                        if not in_entry:
                            continue
                        if line.startswith("Name=") and not name:
                            name = line.split("=", 1)[1]
                        elif line.startswith("Comment=") and not comment:
                            comment = line.split("=", 1)[1]
                        elif line.startswith("Exec=") and not exec_cmd:
                            exec_cmd = line.split("=", 1)[1]
                        elif line.startswith("Icon=") and not icon:
                            icon = line.split("=", 1)[1]
                        elif line == "NoDisplay=true":
                            nodisplay = True
            except Exception:
                continue

            if not name or not exec_cmd or nodisplay:
                continue

            seen_ids.add(base)

            norm_name = re.sub(r"\s*(desktop|app|application|client)\s*$", "", name, flags=re.IGNORECASE).strip().lower()
            if norm_name in seen_normalized_names:
                continue
            seen_normalized_names[norm_name] = base

            clean_exec = " ".join([part for part in exec_cmd.split() if not part.startswith("%") and part not in ["@@u", "@@"]])

            display_name = name
            if base == "org.gnome.Nautilus.desktop":
                display_name = "Fayllar (Files)"

            prio = 999
            if base in POPULAR_PRIORITY:
                prio = POPULAR_PRIORITY.index(base)

            apps.append({
                "id": base,
                "name": display_name,
                "comment": comment,
                "exec": clean_exec,
                "icon": icon or "application-x-executable",
                "priority": prio
            })

    apps.sort(key=lambda a: (a["priority"], a["name"].lower()))

    # Write to cache for next instant launch
    try:
        os.makedirs(os.path.dirname(APPS_CACHE_FILE), exist_ok=True)
        with open(APPS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(apps, f, ensure_ascii=False)
    except Exception:
        pass

    return apps


def score_app(app, query):
    q = query.strip().lower()
    if not q:
        return 0
    name = app["name"].lower()
    app_id = app.get("id", "").lower().replace(".desktop", "")
    
    exec_parts = app["exec"].split()
    exec_bin = ""
    for p in exec_parts:
        base = p.split("/")[-1]
        if base not in ["bash", "sh", "flatpak", "env", "sudo", "pkexec"]:
            exec_bin = base
            break

    comment = app.get("comment", "").lower()
    words = [w for w in re.split(r"[^a-z0-9]+", name) if w]
    acronym = "".join(w[0] for w in words)
    aliases = APP_ALIASES.get(app.get("id", ""), [])

    score = 0

    # 1. Aliases
    for al in aliases:
        if q == al:
            return 1200
        elif al.startswith(q):
            score = max(score, 1000 - len(al))
        elif q in al:
            score = max(score, 850)

    # 2. Exact match
    if name == q:
        return 1100
    if exec_bin == q or (app_id and app_id == q):
        return 950

    # 3. Name starts with query
    if name.startswith(q):
        score = max(score, 900 - len(name))
    elif any(w.startswith(q) for w in words):
        score = max(score, 750 - len(name))

    # 4. Acronym match
    if (len(q) > 1 and acronym.startswith(q)) or (len(q) > 1 and q == acronym):
        score = max(score, 700)
    elif len(q) > 1 and q in acronym:
        score = max(score, 600)

    # 5. Binary or App ID starts with query
    if exec_bin.startswith(q) or (app_id and app_id.startswith(q)):
        score = max(score, 550)

    # 6. Substring in name
    if q in name:
        score = max(score, 450 - len(name))

    # 7. Substring in binary or ID
    if (app_id and q in app_id) or (len(q) > 2 and q in exec_bin):
        score = max(score, 300)

    # 8. Comment match
    if len(q) >= 3 and q in comment:
        score = max(score, 150)

    return score

class SmartLauncher(Gtk.Window):
    def __init__(self, apps):
        super().__init__(title="App Launcher")
        self.apps = apps
        self._idle_id = None
        self._idle_index = 0

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(660, 490)

        # Setup Icon theme paths
        self.theme = Gtk.IconTheme.get_default()
        self.theme.append_search_path("/usr/share/icons")
        self.theme.append_search_path("/usr/share/pixmaps")
        self.theme.append_search_path("/usr/local/share/icons")
        self.theme.append_search_path("/var/lib/flatpak/exports/share/icons")
        self.theme.append_search_path(os.path.expanduser("~/.local/share/icons"))

        self.load_css()

        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.on_destroy)

        # Main Box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.get_style_context().add_class("launcher-window")
        self.add(main_box)

        # Header Search Bar (Clean full-width input, no decorative emojis/lupa)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        header.get_style_context().add_class("search-header")

        entry_overlay = Gtk.Overlay()

        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class("launcher-entry")
        self.entry.connect("changed", self.on_query_changed)
        self.entry.connect("activate", self.on_activate_entry)
        entry_overlay.add(self.entry)

        self.lbl_placeholder = Gtk.Label(label="Qidiruv yoki hisoblash (2+3)...")
        self.lbl_placeholder.set_xalign(0)
        self.lbl_placeholder.set_can_focus(False)
        self.lbl_placeholder.get_style_context().add_class("placeholder-label")
        self.lbl_placeholder.set_no_show_all(True)
        entry_overlay.add_overlay(self.lbl_placeholder)
        entry_overlay.set_overlay_pass_through(self.lbl_placeholder, True)
        self.lbl_placeholder.show()

        header.pack_start(entry_overlay, True, True, 0)
        main_box.pack_start(header, False, False, 0)

        # Scrolled List
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_min_content_height(370)
        self.scroll.get_style_context().add_class("launcher-scroll")

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self.on_row_activated)
        self.scroll.add(self.listbox)
        main_box.pack_start(self.scroll, True, True, 0)

        # Footer Bar
        self.footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.footer.get_style_context().add_class("launcher-footer")

        self.lbl_count = Gtk.Label()
        self.lbl_count.set_markup("<span color='#6e7681' font_desc='11'>57 ta dastur</span>")
        self.lbl_count.set_xalign(0)
        self.footer.pack_start(self.lbl_count, False, False, 4)

        lbl_hints = Gtk.Label()
        lbl_hints.set_markup("<span color='#8b949e' font_desc='11'><span font_family='JetBrains Mono' bgcolor='#242830'> ↵ </span> Ochish   <span font_family='JetBrains Mono' bgcolor='#242830'> esc </span> Yopish</span>")
        lbl_hints.set_xalign(1)
        self.footer.pack_end(lbl_hints, False, False, 4)

        main_box.pack_start(self.footer, False, False, 0)

        self.populate_initial_apps()

    def load_css(self):
        css_provider = Gtk.CssProvider()
        css = """
        window {
            background-color: transparent;
        }
        .launcher-window {
            background-color: rgba(15, 17, 21, 0.96);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.75);
            font-family: "Cantarell", "SF Pro Display", "SF Pro Text", "Noto Sans", sans-serif;
            color: #ffffff;
            padding: 0;
        }
        .search-header {
            padding: 14px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            background-color: transparent;
        }
        .launcher-entry {
            background-color: transparent;
            border: none;
            box-shadow: none;
            color: #ffffff;
            font-size: 16px;
            font-weight: 500;
            padding: 2px 0px;
            caret-color: #10b981;
        }
        .launcher-entry:focus {
            border: none;
            box-shadow: none;
        }
        .placeholder-label {
            color: rgba(255, 255, 255, 0.32);
            font-size: 16px;
            font-weight: 400;
            padding-left: 0px;
        }
        .launcher-scroll {
            padding: 6px 10px;
        }
        list {
            background-color: transparent;
        }
        row {
            background-color: transparent;
            border: none;
            border-radius: 8px;
            margin: 1.5px 0;
            padding: 7px 12px;
            transition: all 0.1s ease;
        }
        row:hover {
            background-color: rgba(255, 255, 255, 0.03);
        }
        row:selected {
            background-color: rgba(255, 255, 255, 0.065);
            border-left: 3px solid #10b981;
            border-radius: 6px;
            padding: 7px 12px 7px 9px;
        }
        .item-title {
            font-size: 14.5px;
            font-weight: 500;
            color: #ffffff;
        }
        .item-desc {
            font-size: 12px;
            font-weight: 400;
            color: #8b949e;
        }
        .launcher-footer {
            padding: 10px 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            background-color: rgba(0, 0, 0, 0.22);
        }
        scrollbar {
            background: transparent;
            border: none;
        }
        scrollbar slider {
            background: rgba(255, 255, 255, 0.12);
            border-radius: 6px;
            min-width: 4px;
        }
        scrollbar slider:hover {
            background: rgba(16, 185, 129, 0.4);
        }
        """
        css_provider.load_from_data(css.encode())
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape or event.hardware_keycode == 9:
            self.close_launcher()
            return True
        elif event.keyval == Gdk.KEY_Down:
            self.move_selection(1)
            return True
        elif event.keyval == Gdk.KEY_Up:
            self.move_selection(-1)
            return True
        elif event.keyval == Gdk.KEY_Page_Down:
            self.move_selection(5)
            return True
        elif event.keyval == Gdk.KEY_Page_Up:
            self.move_selection(-5)
            return True
        return False

    def move_selection(self, step):
        rows = self.listbox.get_children()
        if not rows:
            return
        idx = self.get_selected_index()
        new_idx = max(0, min(len(rows) - 1, idx + step))
        if new_idx != idx:
            self.listbox.select_row(rows[new_idx])
            self.scroll_to_row(rows[new_idx])
            self.entry.grab_focus_without_selecting()

    def scroll_to_row(self, row):
        adj = self.scroll.get_vadjustment()
        alloc = row.get_allocation()
        val = adj.get_value()
        page = adj.get_page_size()
        if alloc.height > 0:
            if alloc.y < val:
                adj.set_value(max(0, alloc.y - 10))
            elif alloc.y + alloc.height > val + page:
                adj.set_value(alloc.y + alloc.height - page + 10)

    def get_selected_index(self):
        sel = self.listbox.get_selected_row()
        if not sel:
            return -1
        return sel.get_index()

    def _cancel_idle(self):
        if self._idle_id is not None:
            try:
                GLib.source_remove(self._idle_id)
            except Exception:
                pass
            self._idle_id = None

    def close_launcher(self):
        self._cancel_idle()
        cleanup_pid()
        Gtk.main_quit()

    def on_destroy(self, *args):
        self._cancel_idle()
        cleanup_pid()
        Gtk.main_quit()

    def populate_initial_apps(self):
        self._cancel_idle()
        initial_count = 12
        for app in self.apps[:initial_count]:
            row = self.create_app_row(app)
            self.listbox.add(row)
        self.listbox.show_all()
        rows = self.listbox.get_children()
        if rows:
            self.listbox.select_row(rows[0])
        self.lbl_count.set_markup(f"<span color='#6e7681' font_desc='11'>{len(self.apps)} ta dastur</span>")

        if len(self.apps) > initial_count:
            self._idle_index = initial_count
            self._idle_id = GLib.idle_add(self._idle_populate_chunk)

    def _idle_populate_chunk(self):
        if not hasattr(self, "_idle_index") or self._idle_index >= len(self.apps):
            self._idle_id = None
            return False

        if self.entry.get_text().strip():
            self._idle_id = None
            return False

        chunk = self.apps[self._idle_index:self._idle_index + 12]
        self._idle_index += len(chunk)
        for app in chunk:
            row = self.create_app_row(app)
            self.listbox.add(row)
            row.show_all()

        if self._idle_index < len(self.apps):
            return True
        self._idle_id = None
        return False

    def create_app_row(self, app):
        row = Gtk.ListBoxRow()
        row.action_type = "app"
        row.action_data = app["exec"]
        row.app_title = app["name"]

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        icon_img = create_icon_widget(app["icon"], self.theme, 32)
        box.pack_start(icon_img, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        lbl_title = Gtk.Label(label=app["name"])
        lbl_title.set_xalign(0)
        lbl_title.get_style_context().add_class("item-title")
        v.pack_start(lbl_title, False, False, 0)

        desc = app["comment"] if app["comment"] else "Dastur"
        if len(desc) > 80:
            desc = desc[:77] + "..."
        lbl_desc = Gtk.Label(label=desc)
        lbl_desc.set_xalign(0)
        lbl_desc.get_style_context().add_class("item-desc")
        v.pack_start(lbl_desc, False, False, 0)

        box.pack_start(v, True, True, 0)
        row.add(box)
        return row

    def create_math_row(self, query, result):
        row = Gtk.ListBoxRow()
        row.action_type = "math"
        row.action_data = str(result)
        row.app_title = f"{query} = {result}"

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        icon_img = create_icon_widget("accessories-calculator", self.theme, 32)
        box.pack_start(icon_img, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<span color='#34d399' font_desc='15' weight='bold'>{query} = {result}</span>")
        lbl_title.set_xalign(0)
        v.pack_start(lbl_title, False, False, 0)

        lbl_desc = Gtk.Label(label="Natijani xotiraga nusxalash (Enter)")
        lbl_desc.set_xalign(0)
        lbl_desc.get_style_context().add_class("item-desc")
        v.pack_start(lbl_desc, False, False, 0)

        box.pack_start(v, True, True, 0)
        row.add(box)
        return row

    def create_search_row(self, query):
        row = Gtk.ListBoxRow()
        row.action_type = "search"
        row.action_data = query
        row.app_title = f"Firefox: {query}"

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        icon_img = create_icon_widget("firefox", self.theme, 32)
        box.pack_start(icon_img, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        lbl_title = Gtk.Label()
        escaped_q = GLib.markup_escape_text(query)
        lbl_title.set_markup(f"Google'da qidirish: <b>\"{escaped_q}\"</b>")
        lbl_title.set_xalign(0)
        lbl_title.get_style_context().add_class("item-title")
        v.pack_start(lbl_title, False, False, 0)

        lbl_desc = Gtk.Label(label="Firefox brauzerida ochish")
        lbl_desc.set_xalign(0)
        lbl_desc.get_style_context().add_class("item-desc")
        v.pack_start(lbl_desc, False, False, 0)

        box.pack_start(v, True, True, 0)
        row.add(box)
        return row

    def on_query_changed(self, entry):
        self._cancel_idle()
        query = entry.get_text()
        has_text = bool(query.strip())
        if has_text:
            self.lbl_placeholder.hide()
        else:
            self.lbl_placeholder.show()

        for child in self.listbox.get_children():
            self.listbox.remove(child)

        if not has_text:
            self.populate_initial_apps()
            return

        clean_query = query.strip()

        # 1. Math calculation check
        math_res = eval_math(clean_query)
        if math_res is not None:
            self.listbox.add(self.create_math_row(clean_query, math_res))

        # 2. Intelligent Scoring & Ranking
        scored_apps = []
        for app in self.apps:
            s = score_app(app, clean_query)
            if s > 0:
                scored_apps.append((s, app))

        scored_apps.sort(key=lambda x: x[0], reverse=True)

        for _, app in scored_apps[:20]:
            self.listbox.add(self.create_app_row(app))

        # 3. Web Search Item
        self.listbox.add(self.create_search_row(clean_query))

        self.listbox.show_all()
        rows = self.listbox.get_children()
        if rows:
            self.listbox.select_row(rows[0])

        count_text = f"{len(scored_apps)} ta dastur topildi" if scored_apps else "Qidiruv natijasi"
        self.lbl_count.set_markup(f"<span color='#6e7681' font_desc='11'>{count_text}</span>")

    def on_activate_entry(self, entry):
        sel = self.listbox.get_selected_row()
        if sel:
            self.execute_action(sel)
        else:
            query = entry.get_text().strip()
            if query:
                self.open_web_search(query)
            self.close_launcher()

    def on_row_activated(self, listbox, row):
        self.execute_action(row)

    def execute_action(self, row):
        act_type = getattr(row, "action_type", None)
        data = getattr(row, "action_data", None)

        if act_type == "math":
            subprocess.run(["wl-copy", data])
            subprocess.run(["notify-send", "Hisoblash natijasi", f"Nusxalandi: {data}", "-u", "low"])
            self.close_launcher()
        elif act_type == "search":
            self.open_web_search(data)
            self.close_launcher()
        elif act_type == "app":
            subprocess.Popen(data, shell=True, start_new_session=True)
            self.close_launcher()

    def open_web_search(self, query):
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        # Strictly open Firefox as requested by user
        flatpak_cmd = ["flatpak", "run", "org.mozilla.firefox", url]
        local_cmd = ["/home/husniddin/.local/bin/firefox", url]
        try:
            subprocess.Popen(flatpak_cmd, start_new_session=True)
        except Exception:
            subprocess.Popen(local_cmd, start_new_session=True)

def main():
    check_single_instance()
    apps = load_desktop_apps()
    win = SmartLauncher(apps)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
