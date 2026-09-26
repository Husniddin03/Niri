#!/usr/bin/env python3
import os
import sys

# Disable accessibility bridge to eliminate 250-500ms D-Bus timeouts
os.environ["NO_AT_BRIDGE"] = "1"
os.environ["GTK_A11Y"] = "none"

# Ensure system paths for icons & MIME
xdg = os.environ.get("XDG_DATA_DIRS", "")
std_dirs = "/usr/share:/usr/local/share:" + os.path.expanduser("~/.local/share")
if "/usr/share" not in xdg:
    os.environ["XDG_DATA_DIRS"] = std_dirs + (":" + xdg if xdg else "")

import json
import time
import signal
import subprocess
import cairo

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell, Pango, GdkPixbuf

CACHE_DIR = os.path.expanduser("~/.cache/clip_history")
HISTORY_FILE = os.path.join(CACHE_DIR, "history.json")
PID_FILE = "/tmp/smart-clipboard.pid"

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

def format_relative_time(ts):
    if not ts:
        return ""
    diff = int(time.time()) - int(ts)
    if diff < 60:
        return "Hozirgina"
    elif diff < 3600:
        return f"{diff // 60} daq. oldin"
    elif diff < 86400:
        return f"{diff // 3600} soat oldin"
    else:
        return f"{diff // 86400} kun oldin"

def infer_clip_type(item):
    t = item.get("type", "text")
    if t == "image":
        return ("Rasm", "#ec4899", "#4c0519", "🖼️")
    content = item.get("content", "")
    trimmed = content.strip()
    if trimmed.startswith("http://") or trimmed.startswith("https://") or trimmed.startswith("ftp://"):
        return ("Havola", "#38bdf8", "#082f49", "🌐")
    if any(k in trimmed for k in ["def ", "function ", "class ", "import ", "const ", "let ", "var ", "=>", "</", "/>", "SELECT ", "curl "]):
        return ("Kod", "#818cf8", "#1e1b4b", "💻")
    return ("Matn", "#94a3b8", "#1e293b", "📝")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    tmp_file = HISTORY_FILE + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=1)
        os.replace(tmp_file, HISTORY_FILE)
    except Exception:
        pass

class SmartClipboard(Gtk.Window):
    def __init__(self, history):
        super().__init__(title="Clipboard Manager")
        self.history = history
        self._idle_id = None
        self._idle_index = 0

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(820, 520)

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
        lbl_search_icon.set_markup("<span color='#38bdf8' font_desc='14'>📋</span>")
        header.pack_start(lbl_search_icon, False, False, 0)

        entry_overlay = Gtk.Overlay()

        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class("launcher-entry")
        self.entry.connect("changed", self.on_query_changed)
        self.entry.connect("activate", self.on_activate_entry)
        entry_overlay.add(self.entry)

        self.lbl_placeholder = Gtk.Label(label="Nusxalangan matn yoki rasmlarni qidirish...")
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

        # Split Body (Left: List, Right: Live Inspector)
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

        # Divider
        divider = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        divider.get_style_context().add_class("panel-divider")
        body_split.pack_start(divider, False, False, 0)

        # Right Preview Inspector Pane
        self.preview_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.preview_panel.get_style_context().add_class("preview-panel")
        self.preview_panel.set_size_request(340, -1)

        self.prev_badge = Gtk.Label()
        self.prev_badge.set_xalign(0)
        self.preview_panel.pack_start(self.prev_badge, False, False, 0)

        # Content container
        self.preview_content_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.preview_panel.pack_start(self.preview_content_area, True, True, 0)

        # Actions Box at bottom
        actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.prev_action_btn = Gtk.Label()
        self.prev_action_btn.get_style_context().add_class("preview-action-btn")
        actions_box.pack_start(self.prev_action_btn, False, False, 0)

        lbl_hints_detail = Gtk.Label(label="↵ Nusxalash   Del O'chirish")
        lbl_hints_detail.set_xalign(0.5)
        lbl_hints_detail.get_style_context().add_class("preview-action-hint")
        actions_box.pack_start(lbl_hints_detail, False, False, 0)

        self.preview_panel.pack_end(actions_box, False, False, 0)

        body_split.pack_end(self.preview_panel, False, False, 0)

        # Footer Bar
        self.footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.footer.get_style_context().add_class("launcher-footer")

        self.lbl_count = Gtk.Label()
        self.lbl_count.set_markup(f"<span color='#10b981'>●</span> <span color='#94a3b8' font_desc='11'>{len(self.history)} ta nusxa saqlangan</span>")
        self.lbl_count.set_xalign(0)
        self.footer.pack_start(self.lbl_count, False, False, 4)

        lbl_hints = Gtk.Label()
        lbl_hints.set_markup("<span color='#8b949e' font_desc='11'><span font_family='JetBrains Mono' bgcolor='#1e232d' color='#cbd5e1'> ↵ </span> Nusxalash   <span font_family='JetBrains Mono' bgcolor='#1e232d' color='#cbd5e1'> del </span> O'chirish   <span font_family='JetBrains Mono' bgcolor='#1e232d' color='#cbd5e1'> esc </span> Yopish</span>")
        lbl_hints.set_xalign(1)
        self.footer.pack_end(lbl_hints, False, False, 4)

        main_box.pack_start(self.footer, False, False, 0)

        self.populate_initial_items()

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
            padding: 8px 12px;
            transition: all 0.12s ease;
        }
        row:hover {
            background-color: rgba(255, 255, 255, 0.04);
        }
        row:selected {
            background: linear-gradient(90deg, rgba(56, 189, 248, 0.14) 0%, rgba(56, 189, 248, 0.03) 100%);
            border-left: 3px solid #38bdf8;
            border-radius: 8px;
            padding: 8px 12px 8px 9px;
        }
        .item-title {
            font-size: 13.5px;
            font-weight: 500;
            color: #f1f5f9;
        }
        row:selected .item-title {
            color: #ffffff;
            font-weight: 600;
        }
        .item-time {
            font-size: 11px;
            color: #64748b;
        }
        .cat-badge {
            border-radius: 6px;
            padding: 2px 7px;
            font-size: 10px;
            font-weight: 600;
        }
        .panel-divider {
            background-color: rgba(255, 255, 255, 0.07);
            min-width: 1px;
        }
        .preview-panel {
            background-color: rgba(0, 0, 0, 0.22);
            padding: 18px 20px;
        }
        .preview-scroll {
            background: rgba(0, 0, 0, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            padding: 10px;
        }
        .preview-text {
            font-family: "JetBrains Mono", monospace;
            font-size: 12px;
            color: #e2e8f0;
            background: transparent;
        }
        .preview-img-box {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 10px;
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
        .launcher-footer {
            padding: 9px 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.07);
            background-color: rgba(0, 0, 0, 0.28);
        }
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
        elif event.keyval == Gdk.KEY_Delete:
            if event.state & Gdk.ModifierType.SHIFT_MASK:
                self.clear_all_history()
            else:
                self.delete_selected()
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

    def populate_initial_items(self):
        self._cancel_idle()
        initial_count = 14
        for item in self.history[:initial_count]:
            row = self.create_item_row(item)
            self.listbox.add(row)

        if not self.history:
            empty_row = self.create_empty_row()
            self.listbox.add(empty_row)

        self.listbox.show_all()
        rows = self.listbox.get_children()
        if rows:
            self.listbox.select_row(rows[0])
            self.update_preview(rows[0])

        self.lbl_count.set_markup(f"<span color='#10b981'>●</span> <span color='#94a3b8' font_desc='11'>{len(self.history)} ta nusxa saqlangan</span>")

        if len(self.history) > initial_count:
            self._idle_index = initial_count
            self._idle_id = GLib.idle_add(self._idle_populate_chunk)

    def _idle_populate_chunk(self):
        if not hasattr(self, "_idle_index") or self._idle_index >= len(self.history):
            self._idle_id = None
            return False

        if self.entry.get_text().strip():
            self._idle_id = None
            return False

        chunk = self.history[self._idle_index:self._idle_index + 12]
        self._idle_index += len(chunk)
        for item in chunk:
            row = self.create_item_row(item)
            self.listbox.add(row)
            row.show_all()

        if self._idle_index < len(self.history):
            return True
        self._idle_id = None
        return False

    def create_empty_row(self):
        row = Gtk.ListBoxRow()
        row.item_data = None
        row.is_empty = True
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label()
        lbl.set_markup("<span color='#64748b' font_desc='13'>Tarix bo'sh. Hech narsa nusxalanmagan.</span>")
        box.pack_start(lbl, True, True, 20)
        row.add(box)
        return row

    def create_item_row(self, item):
        row = Gtk.ListBoxRow()
        row.item_data = item
        row.is_empty = False

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        cat_name, cat_fg, cat_bg, glyph = infer_clip_type(item)

        lbl_glyph = Gtk.Label()
        lbl_glyph.set_markup(f"<span font_desc='14'>{glyph}</span>")
        box.pack_start(lbl_glyph, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        prev_text = item.get("preview", "").replace("\n", " ").strip()
        if len(prev_text) > 48:
            prev_text = prev_text[:45] + "..."
        lbl_text = Gtk.Label(label=prev_text)
        lbl_text.set_xalign(0)
        lbl_text.set_ellipsize(Pango.EllipsizeMode.END)
        lbl_text.get_style_context().add_class("item-title")
        v.pack_start(lbl_text, False, False, 0)

        rel_time = format_relative_time(item.get("time"))
        lbl_time = Gtk.Label(label=rel_time)
        lbl_time.set_xalign(0)
        lbl_time.get_style_context().add_class("item-time")
        v.pack_start(lbl_time, False, False, 0)

        box.pack_start(v, True, True, 0)

        lbl_cat = Gtk.Label()
        lbl_cat.set_markup(f"<span bgcolor='{cat_bg}' color='{cat_fg}' font_desc='9' weight='bold'>  {cat_name}  </span>")
        lbl_cat.set_valign(Gtk.Align.CENTER)
        box.pack_end(lbl_cat, False, False, 0)

        row.add(box)
        return row

    def on_row_selected(self, listbox, row):
        if row:
            self.update_preview(row)

    def update_preview(self, row):
        for ch in self.preview_content_area.get_children():
            self.preview_content_area.remove(ch)

        if getattr(row, "is_empty", False):
            self.prev_badge.set_markup("<span color='#64748b' font_desc='10'>BO'SH</span>")
            self.prev_action_btn.set_markup("<span font_desc='11'>—</span>")
            return

        item = getattr(row, "item_data", None)
        if not item:
            return

        cat_name, cat_fg, cat_bg, glyph = infer_clip_type(item)
        rel_time = format_relative_time(item.get("time"))
        self.prev_badge.set_markup(f"<span bgcolor='{cat_bg}' color='{cat_fg}' font_desc='9.5' weight='bold'>  ● {cat_name.upper()} ({rel_time})  </span>")

        if item.get("type") == "image":
            file_path = item.get("file") or item.get("thumb")
            img_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            img_box.set_halign(Gtk.Align.CENTER)
            img_box.get_style_context().add_class("preview-img-box")

            if file_path and os.path.exists(file_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(file_path, 260, 260, True)
                    gtk_img = Gtk.Image.new_from_pixbuf(pixbuf)
                    img_box.pack_start(gtk_img, False, False, 0)
                except Exception:
                    pass

            self.preview_content_area.pack_start(img_box, False, False, 10)
            self.prev_action_btn.set_markup("<span font_desc='11' weight='bold'>↵  Rasmni nusxalash</span>")

        else:
            content = item.get("content", "")
            scrolled = Gtk.ScrolledWindow()
            scrolled.get_style_context().add_class("preview-scroll")
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

            text_view = Gtk.TextView()
            text_view.set_editable(False)
            text_view.set_cursor_visible(False)
            text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            text_view.get_style_context().add_class("preview-text")
            buffer = text_view.get_buffer()
            buffer.set_text(content)

            scrolled.add(text_view)
            self.preview_content_area.pack_start(scrolled, True, True, 0)

            chars = len(content)
            words = len(content.split())
            lines = len(content.splitlines())
            lbl_stats = Gtk.Label()
            lbl_stats.set_markup(f"<span color='#64748b' font_desc='10'>{chars} ta belgi  •  {words} ta so'z  •  {lines} ta qator</span>")
            lbl_stats.set_xalign(0)
            self.preview_content_area.pack_start(lbl_stats, False, False, 0)

            self.prev_action_btn.set_markup("<span font_desc='11' weight='bold'>↵  Nusxalash</span>")

        self.preview_content_area.show_all()

    def on_query_changed(self, entry):
        self._cancel_idle()
        query = entry.get_text().strip().lower()
        has_text = bool(query)

        if has_text:
            self.lbl_placeholder.hide()
        else:
            self.lbl_placeholder.show()

        for child in self.listbox.get_children():
            self.listbox.remove(child)

        if not has_text:
            self.populate_initial_items()
            return

        filtered = []
        for item in self.history:
            if item.get("type") == "image":
                if "rasm" in query or "image" in query or query in item.get("preview", "").lower():
                    filtered.append(item)
            else:
                content = item.get("content", "").lower()
                preview = item.get("preview", "").lower()
                if query in content or query in preview:
                    filtered.append(item)

        for item in filtered[:25]:
            self.listbox.add(self.create_item_row(item))

        if not filtered:
            lbl = Gtk.Label()
            lbl.set_markup(f"<span color='#64748b' font_desc='13'>'{query}' bo'yicha hech narsa topilmadi</span>")
            r = Gtk.ListBoxRow()
            r.is_empty = True
            r.add(lbl)
            self.listbox.add(r)

        self.listbox.show_all()
        rows = self.listbox.get_children()
        if rows:
            self.listbox.select_row(rows[0])
            self.update_preview(rows[0])

        self.lbl_count.set_markup(f"<span color='#38bdf8'>●</span> <span color='#94a3b8' font_desc='11'>{len(filtered)} ta mos nusxa topildi</span>")

    def on_activate_entry(self, entry):
        sel = self.listbox.get_selected_row()
        if sel:
            self.execute_copy(sel)

    def on_row_activated(self, listbox, row):
        self.execute_copy(row)

    def execute_copy(self, row):
        if getattr(row, "is_empty", False):
            return
        item = getattr(row, "item_data", None)
        if not item:
            return

        if item.get("type") == "image":
            file_path = item.get("file")
            if file_path and os.path.exists(file_path):
                subprocess.Popen(f"wl-copy -t image/png < '{file_path}'", shell=True)
                subprocess.run(["notify-send", "📷 Rasm nusxalandi", "Xotiraga nusxalandi.", "-u", "low"])
                if os.path.exists(os.path.expanduser("~/.local/bin/waypaste"):
                    subprocess.Popen([os.path.expanduser("~/.local/bin/waypaste"])
        else:
            content = item.get("content", "")
            if content:
                p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, text=True)
                p.communicate(input=content)
                subprocess.run(["notify-send", "📋 Nusxalandi", f"{content[:60]}...", "-u", "low"])
                if os.path.exists(os.path.expanduser("~/.local/bin/waypaste"):
                    subprocess.Popen([os.path.expanduser("~/.local/bin/waypaste"])

        self.close_launcher()

    def clear_all_history(self):
        self.history = []
        save_history([])
        for ch in self.listbox.get_children():
            self.listbox.remove(ch)
        empty_row = self.create_empty_row()
        self.listbox.add(empty_row)
        self.listbox.show_all()
        self.update_preview(empty_row)
        self.lbl_count.set_markup("<span color='#10b981'>●</span> <span color='#94a3b8' font_desc='11'>Tarix tozalandi</span>")
        subprocess.run(["notify-send", "📋 Nusxalar tarixi", "Barcha nusxalar tarixi tozalandi.", "-u", "low"])

    def delete_selected(self):
        sel = self.listbox.get_selected_row()
        if not sel or getattr(sel, "is_empty", False):
            return
        item = getattr(sel, "item_data", None)
        if not item:
            return

        self.history = [h for h in self.history if h != item]
        save_history(self.history)

        idx = sel.get_index()
        self.listbox.remove(sel)
        rows = self.listbox.get_children()
        if rows:
            new_idx = min(idx, len(rows) - 1)
            self.listbox.select_row(rows[new_idx])
            self.update_preview(rows[new_idx])
        else:
            empty_row = self.create_empty_row()
            self.listbox.add(empty_row)
            self.listbox.show_all()
            self.update_preview(empty_row)

        self.lbl_count.set_markup(f"<span color='#10b981'>●</span> <span color='#94a3b8' font_desc='11'>{len(self.history)} ta nusxa saqlangan</span>")

def main():
    check_single_instance()
    history = load_history()
    win = SmartClipboard(history)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
