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
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell, Pango
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

def infer_app_category(app):
    name = app.get("name", "").lower()
    exec_str = app.get("exec", "").lower()
    comment = app.get("comment", "").lower()
    app_id = app.get("id", "").lower()
    text = f"{name} {exec_str} {comment} {app_id}"

    if any(k in text for k in ["firefox", "chrome", "chromium", "brave", "browser", "tor", "edge", "web"]):
        return ("Brauzer", "#38bdf8", "#0f2e4a")
    elif any(k in text for k in ["code", "cursor", "zed", "sublime", "neovim", "vim", "ide", "git", "python", "dev"]):
        return ("Dasturlash", "#818cf8", "#1e1b4b")
    elif any(k in text for k in ["telegram", "discord", "slack", "chat", "signal", "whatsapp", "mail", "thunderbird"]):
        return ("Muloqot", "#34d399", "#064e3b")
    elif any(k in text for k in ["terminal", "alacritty", "foot", "kitty", "bash", "console", "cmd"]):
        return ("Terminal", "#fbbf24", "#451a03")
    elif any(k in text for k in ["flameshot", "vlc", "mpv", "audio", "video", "media", "music", "spotify", "sound", "pavucontrol"]):
        return ("Media", "#f472b6", "#4c0519")
    elif any(k in text for k in ["calc", "calculator", "hisob", "math"]):
        return ("Hisoblash", "#a78bfa", "#2e1065")
    elif any(k in text for k in ["nautilus", "nemo", "thunar", "file", "fayl", "archive"]):
        return ("Fayllar", "#38bdf8", "#082f49")
    elif any(k in text for k in ["setting", "config", "control", "stacer", "btop", "system", "bluetooth", "network"]):
        return ("Tizim", "#94a3b8", "#1e293b")
    else:
        return ("Ilova", "#94a3b8", "#1e293b")

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
        self.set_default_size(800, 520)

        self.theme = Gtk.IconTheme.get_default()

        self.load_css()

        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.on_destroy)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.get_style_context().add_class("launcher-window")
        self.add(main_box)

        # Header Search Bar
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.get_style_context().add_class("search-header")

        lbl_search_icon = Gtk.Label()
        lbl_search_icon.set_markup("<span color='#38bdf8' font_desc='14'>⌕</span>")
        lbl_search_icon.get_style_context().add_class("search-icon")
        header.pack_start(lbl_search_icon, False, False, 0)

        entry_overlay = Gtk.Overlay()

        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class("launcher-entry")
        self.entry.connect("changed", self.on_query_changed)
        self.entry.connect("activate", self.on_activate_entry)
        entry_overlay.add(self.entry)

        self.lbl_placeholder = Gtk.Label(label="Qidiruv yoki hisoblash (masalan: 12 * 45)...")
        self.lbl_placeholder.set_xalign(0)
        self.lbl_placeholder.set_can_focus(False)
        self.lbl_placeholder.get_style_context().add_class("placeholder-label")
        self.lbl_placeholder.set_no_show_all(True)
        entry_overlay.add_overlay(self.lbl_placeholder)
        entry_overlay.set_overlay_pass_through(self.lbl_placeholder, True)
        self.lbl_placeholder.show()

        header.pack_start(entry_overlay, True, True, 0)

        lbl_esc = Gtk.Label()
        lbl_esc.set_markup("<span font_desc='10' weight='bold'>esc</span>")
        lbl_esc.get_style_context().add_class("esc-pill")
        header.pack_end(lbl_esc, False, False, 0)

        main_box.pack_start(header, False, False, 0)

        # Body Split (Left: List, Right: Preview Inspector)
        body_split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body_split.get_style_context().add_class("body-split")
        main_box.pack_start(body_split, True, True, 0)

        # Left List Area
        list_pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        list_pane.get_style_context().add_class("list-pane")
        list_pane.set_size_request(480, -1)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_min_content_height(400)
        self.scroll.get_style_context().add_class("launcher-scroll")

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self.on_row_activated)
        self.listbox.connect("row-selected", self.on_row_selected)
        self.scroll.add(self.listbox)
        list_pane.pack_start(self.scroll, True, True, 0)

        body_split.pack_start(list_pane, True, True, 0)

        # Vertical Divider
        divider = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        divider.get_style_context().add_class("panel-divider")
        body_split.pack_start(divider, False, False, 0)

        # Right Preview Inspector Pane
        self.preview_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.preview_panel.get_style_context().add_class("preview-panel")
        self.preview_panel.set_size_request(320, -1)

        self.prev_badge = Gtk.Label()
        self.prev_badge.set_xalign(0)
        self.preview_panel.pack_start(self.prev_badge, False, False, 0)

        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hero_box.set_halign(Gtk.Align.CENTER)

        self.prev_icon_box = Gtk.Box()
        self.prev_icon_box.get_style_context().add_class("preview-icon-wrapper")
        self.prev_icon_box.set_halign(Gtk.Align.CENTER)
        self.prev_icon = Gtk.Image()
        self.prev_icon_box.add(self.prev_icon)
        hero_box.pack_start(self.prev_icon_box, False, False, 0)

        self.prev_title = Gtk.Label()
        self.prev_title.get_style_context().add_class("preview-title")
        self.prev_title.set_justify(Gtk.Justification.CENTER)
        hero_box.pack_start(self.prev_title, False, False, 0)

        self.prev_desc = Gtk.Label()
        self.prev_desc.get_style_context().add_class("preview-desc")
        self.prev_desc.set_line_wrap(True)
        self.prev_desc.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.prev_desc.set_max_width_chars(32)
        self.prev_desc.set_justify(Gtk.Justification.CENTER)
        hero_box.pack_start(self.prev_desc, False, False, 0)

        self.preview_panel.pack_start(hero_box, False, False, 4)

        # Monospace Exec Box
        self.meta_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_meta_title = Gtk.Label(label="BUYRUQ (COMMAND)")
        lbl_meta_title.set_xalign(0)
        lbl_meta_title.get_style_context().add_class("preview-chip-title")
        self.meta_box.pack_start(lbl_meta_title, False, False, 0)

        self.prev_exec_label = Gtk.Label()
        self.prev_exec_label.set_xalign(0)
        self.prev_exec_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.prev_exec_label.set_max_width_chars(30)
        self.prev_exec_label.get_style_context().add_class("preview-chip")
        self.meta_box.pack_start(self.prev_exec_label, False, False, 0)
        self.preview_panel.pack_start(self.meta_box, False, False, 4)

        # Spacer
        spacer = Gtk.Box()
        self.preview_panel.pack_start(spacer, True, True, 0)

        # Actions Box
        actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.prev_action_btn = Gtk.Label()
        self.prev_action_btn.get_style_context().add_class("preview-action-btn")
        actions_box.pack_start(self.prev_action_btn, False, False, 0)

        self.prev_action_hint = Gtk.Label(label="Ctrl+C  Buyruqni nusxalash")
        self.prev_action_hint.set_xalign(0.5)
        self.prev_action_hint.get_style_context().add_class("preview-action-hint")
        actions_box.pack_start(self.prev_action_hint, False, False, 0)

        self.preview_panel.pack_end(actions_box, False, False, 0)

        body_split.pack_end(self.preview_panel, False, False, 0)

        # Footer Bar
        self.footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.footer.get_style_context().add_class("launcher-footer")

        self.lbl_count = Gtk.Label()
        self.lbl_count.set_markup(f"<span color='#10b981'>●</span> <span color='#94a3b8' font_desc='11'>{len(self.apps)} ta dastur mavjud</span>")
        self.lbl_count.set_xalign(0)
        self.footer.pack_start(self.lbl_count, False, False, 4)

        lbl_hints = Gtk.Label()
        lbl_hints.set_markup("<span color='#8b949e' font_desc='11'><span font_family='JetBrains Mono' bgcolor='#1e232d' color='#cbd5e1'> ↵ </span> Ochish   <span font_family='JetBrains Mono' bgcolor='#1e232d' color='#cbd5e1'> ↑↓ </span> Tanlash   <span font_family='JetBrains Mono' bgcolor='#1e232d' color='#cbd5e1'> esc </span> Yopish</span>")
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
            background-color: rgba(14, 17, 24, 0.96);
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 18px;
            box-shadow: 0 32px 80px rgba(0, 0, 0, 0.85);
            font-family: "Cantarell", "SF Pro Display", "SF Pro Text", "JetBrains Mono", sans-serif;
            color: #ffffff;
            padding: 0;
        }
        .search-header {
            padding: 12px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.07);
            background-color: transparent;
        }
        .search-icon {
            font-size: 16px;
            font-weight: bold;
            color: #38bdf8;
            margin-right: 8px;
        }
        .launcher-entry {
            background-color: transparent;
            border: none;
            box-shadow: none;
            color: #ffffff;
            font-size: 16px;
            font-weight: 500;
            padding: 2px 0px;
            caret-color: #38bdf8;
        }
        .launcher-entry:focus {
            border: none;
            box-shadow: none;
        }
        .placeholder-label {
            color: rgba(255, 255, 255, 0.32);
            font-size: 15px;
            font-weight: 400;
            padding-left: 0px;
        }
        .esc-pill {
            background-color: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 11px;
            font-family: "JetBrains Mono", monospace;
            color: #94a3b8;
        }

        /* Body Split */
        .body-split {
            background-color: transparent;
        }
        .list-pane {
            background-color: transparent;
        }
        .launcher-scroll {
            padding: 6px 8px;
        }
        list {
            background-color: transparent;
        }
        row {
            background-color: transparent;
            border: none;
            border-radius: 10px;
            margin: 2px 4px;
            padding: 7px 12px;
            transition: all 0.12s ease;
        }
        row:hover {
            background-color: rgba(255, 255, 255, 0.04);
        }
        row:selected {
            background: linear-gradient(90deg, rgba(56, 189, 248, 0.14) 0%, rgba(56, 189, 248, 0.03) 100%);
            border-left: 3px solid #38bdf8;
            border-radius: 8px;
            padding: 7px 12px 7px 9px;
        }
        .item-title {
            font-size: 14px;
            font-weight: 600;
            color: #f1f5f9;
        }
        row:selected .item-title {
            color: #ffffff;
        }
        .item-desc {
            font-size: 11.5px;
            font-weight: 400;
            color: #64748b;
        }
        row:selected .item-desc {
            color: #94a3b8;
        }
        .cat-badge {
            border-radius: 6px;
            padding: 2px 7px;
            font-size: 10px;
            font-weight: 600;
        }

        /* Hairline Divider */
        .panel-divider {
            background-color: rgba(255, 255, 255, 0.07);
            min-width: 1px;
        }

        /* Right Inspector Panel */
        .preview-panel {
            background-color: rgba(0, 0, 0, 0.22);
            padding: 20px 22px;
        }
        .preview-icon-wrapper {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 18px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            padding: 14px;
        }
        .preview-title {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
        }
        .preview-desc {
            font-size: 12px;
            color: #94a3b8;
        }
        .preview-chip-title {
            font-size: 9.5px;
            font-weight: 700;
            color: #64748b;
            letter-spacing: 0.5px;
        }
        .preview-chip {
            background: rgba(0, 0, 0, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 6px 10px;
            font-family: "JetBrains Mono", monospace;
            font-size: 11px;
            color: #38bdf8;
        }
        .preview-action-btn {
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.22) 0%, rgba(14, 165, 233, 0.15) 100%);
            border: 1px solid rgba(56, 189, 248, 0.45);
            border-radius: 8px;
            padding: 8px 12px;
            color: #38bdf8;
            font-size: 12px;
            font-weight: 600;
        }
        .preview-action-hint {
            font-size: 11px;
            color: #64748b;
        }

        /* Footer */
        .launcher-footer {
            padding: 9px 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.07);
            background-color: rgba(0, 0, 0, 0.28);
        }
        .keycap {
            background-color: #1e232d;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            padding: 1px 5px;
            font-family: "JetBrains Mono", monospace;
            color: #cbd5e1;
            font-size: 10px;
        }

        /* Scrollbar */
        scrollbar {
            background: transparent;
            border: none;
        }
        scrollbar slider {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            min-width: 4px;
        }
        scrollbar slider:hover {
            background: rgba(56, 189, 248, 0.4);
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
        elif bool(event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval in [Gdk.KEY_c, Gdk.KEY_C]:
            sel = self.listbox.get_selected_row()
            if sel:
                data = getattr(sel, "action_data", "")
                if data:
                    subprocess.run(["wl-copy", data])
                    subprocess.run(["notify-send", "Nusxalandi", f"{data}", "-u", "low"])
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
            self.update_preview(rows[0])
        self.lbl_count.set_markup(f"<span color='#10b981'>●</span> <span color='#94a3b8' font_desc='11'>{len(self.apps)} ta dastur mavjud</span>")

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
        row.app_info = app

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        icon_img = create_icon_widget(app["icon"], self.theme, 32)
        box.pack_start(icon_img, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label(label=app["name"])
        lbl_title.set_xalign(0)
        lbl_title.get_style_context().add_class("item-title")
        v.pack_start(lbl_title, False, False, 0)

        desc = app["comment"] if app["comment"] else "Tizim ilovasi"
        if len(desc) > 55:
            desc = desc[:52] + "..."
        lbl_desc = Gtk.Label(label=desc)
        lbl_desc.set_xalign(0)
        lbl_desc.get_style_context().add_class("item-desc")
        v.pack_start(lbl_desc, False, False, 0)

        box.pack_start(v, True, True, 0)

        cat_name, cat_fg, cat_bg = infer_app_category(app)
        lbl_cat = Gtk.Label()
        lbl_cat.set_markup(f"<span bgcolor='{cat_bg}' color='{cat_fg}' font_desc='9' weight='bold'>  {cat_name}  </span>")
        lbl_cat.set_valign(Gtk.Align.CENTER)
        box.pack_end(lbl_cat, False, False, 0)

        row.add(box)
        return row

    def create_math_row(self, query, result):
        row = Gtk.ListBoxRow()
        row.action_type = "math"
        row.action_data = str(result)
        row.app_title = f"{query} = {result}"
        row.math_query = query
        row.math_result = result

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        icon_img = create_icon_widget("accessories-calculator", self.theme, 32)
        box.pack_start(icon_img, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<span color='#34d399' font_desc='14' weight='bold'>{query} = {result}</span>")
        lbl_title.set_xalign(0)
        v.pack_start(lbl_title, False, False, 0)

        lbl_desc = Gtk.Label(label="Natijani xotiraga nusxalash (Enter)")
        lbl_desc.set_xalign(0)
        lbl_desc.get_style_context().add_class("item-desc")
        v.pack_start(lbl_desc, False, False, 0)

        box.pack_start(v, True, True, 0)

        lbl_cat = Gtk.Label()
        lbl_cat.set_markup("<span bgcolor='#064e3b' color='#34d399' font_desc='9' weight='bold'>  Hisob  </span>")
        lbl_cat.set_valign(Gtk.Align.CENTER)
        box.pack_end(lbl_cat, False, False, 0)

        row.add(box)
        return row

    def create_search_row(self, query):
        row = Gtk.ListBoxRow()
        row.action_type = "search"
        row.action_data = query
        row.app_title = f"Google: {query}"
        row.search_query = query

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        icon_img = create_icon_widget("firefox", self.theme, 32)
        box.pack_start(icon_img, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label()
        escaped_q = GLib.markup_escape_text(query)
        lbl_title.set_markup(f"Google: <b>\"{escaped_q}\"</b>")
        lbl_title.set_xalign(0)
        lbl_title.get_style_context().add_class("item-title")
        v.pack_start(lbl_title, False, False, 0)

        lbl_desc = Gtk.Label(label="Firefox brauzerida ochish")
        lbl_desc.set_xalign(0)
        lbl_desc.get_style_context().add_class("item-desc")
        v.pack_start(lbl_desc, False, False, 0)

        box.pack_start(v, True, True, 0)

        lbl_cat = Gtk.Label()
        lbl_cat.set_markup("<span bgcolor='#082f49' color='#38bdf8' font_desc='9' weight='bold'>  Google  </span>")
        lbl_cat.set_valign(Gtk.Align.CENTER)
        box.pack_end(lbl_cat, False, False, 0)

        row.add(box)
        return row

    def on_row_selected(self, listbox, row):
        if row:
            self.update_preview(row)

    def update_preview(self, row):
        act_type = getattr(row, "action_type", None)

        if act_type == "app":
            app = getattr(row, "app_info", None)
            if not app:
                return
            cat_name, cat_fg, cat_bg = infer_app_category(app)
            self.prev_badge.set_markup(f"<span bgcolor='{cat_bg}' color='{cat_fg}' font_desc='9.5' weight='bold'>  ● {cat_name.upper()}  </span>")

            for ch in self.prev_icon_box.get_children():
                self.prev_icon_box.remove(ch)
            new_icon = create_icon_widget(app["icon"], self.theme, 56)
            self.prev_icon_box.add(new_icon)
            self.prev_icon_box.show_all()

            self.prev_title.set_markup(f"<span font_desc='15' weight='bold' color='#ffffff'>{GLib.markup_escape_text(app['name'])}</span>")
            desc = app["comment"] if app["comment"] else "Tizim ilovasi"
            self.prev_desc.set_text(desc)

            self.meta_box.show()
            self.prev_exec_label.set_text(f"$ {app['exec']}")
            self.prev_action_btn.set_markup("<span font_desc='11' weight='bold'>↵  Ochish</span>")
            self.prev_action_hint.set_text("Ctrl+C  Buyruqni nusxalash")
            self.prev_action_hint.show()

        elif act_type == "math":
            self.prev_badge.set_markup("<span bgcolor='#064e3b' color='#34d399' font_desc='9.5' weight='bold'>  ● MATEMATIKA  </span>")

            for ch in self.prev_icon_box.get_children():
                self.prev_icon_box.remove(ch)
            new_icon = create_icon_widget("accessories-calculator", self.theme, 56)
            self.prev_icon_box.add(new_icon)
            self.prev_icon_box.show_all()

            self.prev_title.set_markup("<span font_desc='15' weight='bold' color='#ffffff'>Hisoblash Natijasi</span>")
            m_query = getattr(row, "math_query", "")
            m_res = getattr(row, "math_result", "")
            self.prev_desc.set_markup(f"<span color='#94a3b8'>{m_query} =</span>\n<span color='#34d399' font_desc='20' weight='bold'>{m_res}</span>")

            self.meta_box.hide()
            self.prev_action_btn.set_markup("<span font_desc='11' weight='bold'>↵  Nusxalash</span>")
            self.prev_action_hint.set_text("Natijani buferga nusxalash")
            self.prev_action_hint.show()

        elif act_type == "search":
            self.prev_badge.set_markup("<span bgcolor='#082f49' color='#38bdf8' font_desc='9.5' weight='bold'>  ● GOOGLE QIDIRUV  </span>")

            for ch in self.prev_icon_box.get_children():
                self.prev_icon_box.remove(ch)
            new_icon = create_icon_widget("firefox", self.theme, 56)
            self.prev_icon_box.add(new_icon)
            self.prev_icon_box.show_all()

            self.prev_title.set_markup("<span font_desc='15' weight='bold' color='#ffffff'>Veb Qidiruv</span>")
            s_query = getattr(row, "search_query", "")
            self.prev_desc.set_text(f"\"{s_query}\" bo'yicha Google qidiruv natijalarini Firefox brauzerida ochish")

            self.meta_box.hide()
            self.prev_action_btn.set_markup("<span font_desc='11' weight='bold'>↵  Firefox'da ochish</span>")
            self.prev_action_hint.hide()

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

        math_res = eval_math(clean_query)
        if math_res is not None:
            self.listbox.add(self.create_math_row(clean_query, math_res))

        scored_apps = []
        for app in self.apps:
            s = score_app(app, clean_query)
            if s > 0:
                scored_apps.append((s, app))

        scored_apps.sort(key=lambda x: x[0], reverse=True)

        for _, app in scored_apps[:20]:
            self.listbox.add(self.create_app_row(app))

        self.listbox.add(self.create_search_row(clean_query))

        self.listbox.show_all()
        rows = self.listbox.get_children()
        if rows:
            self.listbox.select_row(rows[0])
            self.update_preview(rows[0])

        count_text = f"{len(scored_apps)} ta dastur topildi" if scored_apps else "Qidiruv natijasi"
        self.lbl_count.set_markup(f"<span color='#38bdf8'>●</span> <span color='#94a3b8' font_desc='11'>{count_text}</span>")

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
        flatpak_cmd = ["flatpak", "run", "org.mozilla.firefox", url]
        local_cmd = [os.path.expanduser("~/.local/bin/firefox", url]
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
