#!/usr/bin/env python3
import os
import sys
import time
import glob
import random
import signal
import subprocess

# Ensure XDG_DATA_DIRS includes /usr/share for MIME & GdkPixbuf loaders
os.environ["XDG_DATA_DIRS"] = f"/usr/share:/usr/local/share:{os.path.expanduser('~/.local/share')}:{os.environ.get('XDG_DATA_DIRS', '')}"

PID_FILE = "/tmp/wallpaper_live_selector.pid"

# Safe toggle check: only kill and exit if an actual live_selector process is currently running
if os.path.exists(PID_FILE):
    try:
        with open(PID_FILE) as f:
            old_pid = int(f.read().strip())
        cmdline_path = f"/proc/{old_pid}/cmdline"
        if os.path.exists(cmdline_path):
            with open(cmdline_path, "rb") as f:
                cmdline = f.read().decode("utf-8", errors="ignore")
            if "live_selector.py" in cmdline:
                os.kill(old_pid, signal.SIGTERM)
                try:
                    os.remove(PID_FILE)
                except Exception:
                    pass
                sys.exit(0)
    except Exception:
        pass

try:
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
except Exception:
    pass

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GdkPixbuf, GtkLayerShell, GLib

MODE = "wallpaper"
if len(sys.argv) > 1 and sys.argv[1] in ["--mode", "-m"] and len(sys.argv) > 2:
    MODE = sys.argv[2]
elif "--overview" in sys.argv:
    MODE = "overview"

WP_DIR = os.path.expanduser("~/Pictures/Wallpapers")
CACHE_DIR = os.path.expanduser("~/.cache/wallpaper-selector")
CURRENT_WP_CACHE = os.path.expanduser("~/.cache/current_wallpaper")
CURRENT_OVERVIEW_CACHE = os.path.expanduser("~/.cache/current_overview_backdrop")

def ensure_swww_desktop():
    sock = f"/run/user/{os.getuid()}/swww-wayland-1.socket"
    if not os.path.exists(sock):
        subprocess.Popen(["swww-daemon"])
        for _ in range(25):
            if os.path.exists(sock):
                break
            time.sleep(0.02)

class LiveWallpaperSelector(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.mode = MODE
        self.selected_item = None
        self.preview_timer_id = None
        self.idle_loader_id = None
        self.user_navigated = False
        self.initial_path = self.get_current_wallpaper()

        # 1. Enable RGBA visual for true glass transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.connect("draw", self.on_draw)

        # 2. GtkLayerShell configuration
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "wallpaper-selector")
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        
        # Center in active monitor (no anchors)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)

        # Explicit size request: 920px width x 660px height
        self.set_size_request(920, 660)

        self.cards_data = []
        self.pending_wallpapers = []

        self.setup_ui()
        self.apply_css()

        self.connect("destroy", self.on_destroy)
        self.connect("key-press-event", self.on_key_press)

    def on_draw(self, widget, cr):
        # Clear window surface with full alpha transparency
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def get_current_wallpaper(self):
        cache_file = CURRENT_OVERVIEW_CACHE if self.mode == "overview" else CURRENT_WP_CACHE
        if os.path.isfile(cache_file):
            try:
                with open(cache_file) as f:
                    return f.read().strip()
            except Exception:
                pass
        return None

    def setup_ui(self):
        # Outer container with rounded corners and semi-transparent dark glass background
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_name("outer-box")
        self.main_box.set_size_request(920, 660)
        self.main_box.set_margin_top(12)
        self.main_box.set_margin_bottom(12)
        self.main_box.set_margin_start(12)
        self.main_box.set_margin_end(12)
        self.add(self.main_box)

        # Header Search entry
        prompt_text = "🌌 Overview orqa fonini tanlang (Strelkalar bilan ko'ring)..." if self.mode == "overview" else "🖼️ Fon rasmini tanlang (Strelkalar bilan ko'ring)..."
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(prompt_text)
        self.search_entry.set_name("input")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.main_box.pack_start(self.search_entry, False, False, 0)

        # Scrolled window
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_name("scroll")
        self.scrolled.set_min_content_width(880)
        self.scrolled.set_min_content_height(570)
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.main_box.pack_start(self.scrolled, True, True, 0)

        # FlowBox for 3-column grid
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_name("inner-box")
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_min_children_per_line(3)
        self.flowbox.set_column_spacing(12)
        self.flowbox.set_row_spacing(12)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.connect("selected-children-changed", self.on_selection_changed)
        self.flowbox.connect("child-activated", self.on_child_activated)
        self.flowbox.connect("button-press-event", self.on_flowbox_button_press)
        self.scrolled.add(self.flowbox)

    def on_flowbox_button_press(self, widget, event):
        self.user_navigated = True

        self.load_initial_cards()

    def load_initial_cards(self):
        # 1. Shuffle card
        shuffle_icon = os.path.join(CACHE_DIR, "000_random_tasodifiy_shuffle.png")
        if os.path.isfile(shuffle_icon):
            self.add_card("shuffle", "Tasodifiy", shuffle_icon)

        # 2. Transparent card (only for desktop wallpaper)
        if self.mode == "wallpaper":
            trans_icon = os.path.join(CACHE_DIR, "001_transparent_shaffof.png")
            if os.path.isfile(trans_icon):
                self.add_card("transparent", "Shaffof", trans_icon)

        # 3. Queue all wallpapers from WP_DIR
        if os.path.isdir(WP_DIR):
            all_files = sorted([f for f in os.listdir(WP_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
            # Load first 24 wallpapers immediately so UI opens with 0 lag
            first_batch = all_files[:24]
            self.pending_wallpapers = all_files[24:]

            for wp in first_batch:
                base = os.path.splitext(wp)[0]
                thumb = os.path.join(CACHE_DIR, base + ".png")
                full_path = os.path.join(WP_DIR, wp)
                if os.path.isfile(thumb):
                    self.add_card("image", full_path, thumb, name=base)

            # Schedule loading of remaining wallpapers in background chunks of 24
            if self.pending_wallpapers:
                self.idle_loader_id = GLib.idle_add(self.load_background_batch)

    def load_background_batch(self):
        if not self.pending_wallpapers:
            self.idle_loader_id = None
            return False

        chunk = self.pending_wallpapers[:24]
        self.pending_wallpapers = self.pending_wallpapers[24:]

        for wp in chunk:
            base = os.path.splitext(wp)[0]
            thumb = os.path.join(CACHE_DIR, base + ".png")
            full_path = os.path.join(WP_DIR, wp)
            if os.path.isfile(thumb):
                self.add_card("image", full_path, thumb, name=base)

        self.flowbox.show_all()
        return bool(self.pending_wallpapers)

    def add_card(self, item_type, target_path, thumb_path, name=""):
        child = Gtk.FlowBoxChild()
        child.set_name("entry")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_halign(Gtk.Align.CENTER)

        try:
            pb = GdkPixbuf.Pixbuf.new_from_file(thumb_path)
            img = Gtk.Image.new_from_pixbuf(pb)
        except Exception:
            img = Gtk.Image()

        img.set_name("img")
        box.pack_start(img, True, True, 0)
        child.add(box)

        self.flowbox.add(child)
        self.cards_data.append({
            "type": item_type,
            "path": target_path,
            "name": name.lower(),
            "child": child
        })

    def apply_css(self):
        css = b"""
        window {
            background-color: transparent;
            background: transparent;
        }
        #outer-box {
            background-color: rgba(18, 20, 26, 0.82);
            border: 1.5px solid rgba(255, 255, 255, 0.16);
            border-radius: 20px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7);
        }
        #input {
            background-color: rgba(255, 255, 255, 0.08);
            border: 1.5px solid rgba(255, 255, 255, 0.14);
            border-radius: 14px;
            padding: 10px 16px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 500;
            margin: 4px 6px 10px 6px;
        }
        #input:focus {
            border: 1.5px solid #10b981;
            background-color: rgba(255, 255, 255, 0.12);
        }
        #entry {
            padding: 3px;
            margin: 4px;
            background-color: transparent;
            border-radius: 14px;
            border: 2.5px solid transparent;
            transition: all 0.12s ease-in-out;
        }
        #entry:selected {
            background-color: transparent;
            border: 2.5px solid #10b981;
            box-shadow: 0 0 16px rgba(16, 185, 129, 0.75);
        }
        #img {
            border-radius: 10px;
        }
        scrollbar {
            background: transparent;
            border: none;
        }
        scrollbar slider {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            min-width: 4px;
        }
        scrollbar slider:hover {
            background: rgba(16, 185, 129, 0.6);
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def get_visible_items(self):
        return [item for item in self.cards_data if item["child"].get_visible()]

    def on_search_changed(self, entry):
        # If user searches, finish loading pending wallpapers so search finds everything
        if self.pending_wallpapers:
            while self.pending_wallpapers:
                self.load_background_batch()

        text = entry.get_text().strip().lower()
        first_visible = None
        for item in self.cards_data:
            match = (not text) or (text in item["name"]) or (item["type"] in ["shuffle", "transparent"])
            item["child"].set_visible(match)
            if match and first_visible is None:
                first_visible = item["child"]
        if first_visible:
            was_nav = self.user_navigated
            self.flowbox.select_child(first_visible)
            if not was_nav and self.preview_timer_id is not None:
                GLib.source_remove(self.preview_timer_id)
                self.preview_timer_id = None

    def on_selection_changed(self, flowbox):
        selected = flowbox.get_selected_children()
        if not selected:
            return
        child = selected[0]
        for item in self.cards_data:
            if item["child"] == child:
                self.selected_item = item
                break

        if not self.user_navigated:
            return

        # Debounce live preview by 70ms so rapid arrow navigation is smooth without stutter
        if self.preview_timer_id is not None:
            GLib.source_remove(self.preview_timer_id)
            self.preview_timer_id = None
        self.preview_timer_id = GLib.timeout_add(70, self.do_live_preview)

    def do_live_preview(self):
        self.preview_timer_id = None
        if not self.user_navigated or not self.selected_item:
            return False

        item_type = self.selected_item["type"]
        path = self.selected_item["path"]

        # Smooth right-to-left wipe animation: angle 0 is right to left in swww
        transition_args = [
            "--transition-type", "wipe",
            "--transition-angle", "0",
            "--transition-fps", "60",
            "--transition-duration", "0.45"
        ]

        if self.mode == "wallpaper":
            if item_type == "shuffle":
                all_wps = [os.path.join(WP_DIR, f) for f in os.listdir(WP_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                if all_wps:
                    rand_wp = random.choice(all_wps)
                    ensure_swww_desktop()
                    subprocess.Popen(["swww", "img", rand_wp] + transition_args)
            elif item_type == "transparent":
                subprocess.Popen(["pkill", "-x", "swww-daemon"])
            else:
                ensure_swww_desktop()
                subprocess.Popen(["swww", "img", path] + transition_args)
        else: # overview
            env = os.environ.copy()
            env["WAYLAND_DISPLAY"] = "wayland-overview"
            if item_type == "shuffle":
                all_wps = [os.path.join(WP_DIR, f) for f in os.listdir(WP_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                if all_wps:
                    rand_wp = random.choice(all_wps)
                    subprocess.Popen(["swww", "img", rand_wp] + transition_args, env=env)
            else:
                subprocess.Popen(["swww", "img", path] + transition_args, env=env)

        return False

    def on_child_activated(self, flowbox, child):
        self.confirm_and_close()

    def confirm_and_close(self):
        if not self.selected_item:
            self.close()
            return

        item_type = self.selected_item["type"]
        path = self.selected_item["path"]

        if self.mode == "wallpaper":
            if item_type == "transparent":
                with open(CURRENT_WP_CACHE, "w") as f:
                    f.write("transparent")
                subprocess.Popen(["pkill", "-x", "swww-daemon"])
                subprocess.Popen(["notify-send", "✨ Fon holati", "Bekraund shaffof qilindi", "-u", "low"])
            else:
                final_path = path
                if item_type == "shuffle":
                    all_wps = [os.path.join(WP_DIR, f) for f in os.listdir(WP_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                    final_path = random.choice(all_wps) if all_wps else path

                with open(CURRENT_WP_CACHE, "w") as f:
                    f.write(final_path)
                subprocess.Popen(["notify-send", "🖼️ Fon rasmi", "Asosiy ekran foni yangilandi", "-i", final_path, "-u", "low"])
        else: # overview
            final_path = path
            if item_type == "shuffle":
                all_wps = [os.path.join(WP_DIR, f) for f in os.listdir(WP_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                final_path = random.choice(all_wps) if all_wps else path

            with open(CURRENT_OVERVIEW_CACHE, "w") as f:
                f.write(final_path)
            subprocess.Popen(["notify-send", "🌌 Overview Foni", "Overview orqa foni yangilandi", "-i", final_path, "-u", "low"])

        self.close()

    def on_key_press(self, widget, event):
        kv = event.keyval

        # Escape cancels and restores initial
        if kv == Gdk.KEY_Escape:
            self.restore_initial_and_close()
            return True

        # Enter confirms
        if kv in [Gdk.KEY_Return, Gdk.KEY_KP_Enter]:
            self.confirm_and_close()
            return True

        # If user is editing text in search entry, allow Left/Right cursor movement inside entry
        if self.search_entry.is_focus() and len(self.search_entry.get_text()) > 0:
            if kv in [Gdk.KEY_Left, Gdk.KEY_Right, Gdk.KEY_Home, Gdk.KEY_End]:
                return False

        # Arrow key navigation
        visible = self.get_visible_items()
        if not visible:
            return False

        current_idx = 0
        if self.selected_item:
            for idx, itm in enumerate(visible):
                if itm == self.selected_item:
                    current_idx = idx
                    break

        new_idx = current_idx
        cols = 3

        if kv in [Gdk.KEY_Left, Gdk.KEY_h]:
            new_idx = max(0, current_idx - 1)
        elif kv in [Gdk.KEY_Right, Gdk.KEY_l]:
            new_idx = min(len(visible) - 1, current_idx + 1)
        elif kv in [Gdk.KEY_Up, Gdk.KEY_k]:
            new_idx = max(0, current_idx - cols)
        elif kv in [Gdk.KEY_Down, Gdk.KEY_j]:
            new_idx = min(len(visible) - 1, current_idx + cols)
        elif kv == Gdk.KEY_Home:
            new_idx = 0
        elif kv == Gdk.KEY_End:
            new_idx = len(visible) - 1
        elif kv == Gdk.KEY_Page_Up:
            new_idx = max(0, current_idx - cols * 3)
        elif kv == Gdk.KEY_Page_Down:
            new_idx = min(len(visible) - 1, current_idx + cols * 3)
        elif kv == Gdk.KEY_Tab:
            new_idx = min(len(visible) - 1, current_idx + 1)
        elif kv == Gdk.KEY_ISO_Left_Tab:
            new_idx = max(0, current_idx - 1)
        else:
            return False

        if new_idx != current_idx or not self.user_navigated:
            self.user_navigated = True
            target_child = visible[new_idx]["child"]
            self.flowbox.select_child(target_child)
            
            # Smooth scroll to keep selected child visible
            adj = self.scrolled.get_vadjustment()
            alloc = target_child.get_allocation()
            if alloc.y < adj.get_value():
                adj.set_value(max(0, alloc.y - 12))
            elif alloc.y + alloc.height > adj.get_value() + adj.get_page_size():
                adj.set_value(alloc.y + alloc.height - adj.get_page_size() + 12)

            return True

        return False

    def restore_initial_and_close(self):
        if not self.user_navigated:
            self.close()
            return

        transition_args = [
            "--transition-type", "wipe",
            "--transition-angle", "0",
            "--transition-fps", "60",
            "--transition-duration", "0.4"
        ]

        if self.initial_path and os.path.isfile(self.initial_path):
            if self.mode == "wallpaper":
                ensure_swww_desktop()
                subprocess.Popen(["swww", "img", self.initial_path] + transition_args)
            else:
                env = os.environ.copy()
                env["WAYLAND_DISPLAY"] = "wayland-overview"
                subprocess.Popen(["swww", "img", self.initial_path] + transition_args, env=env)
        elif self.initial_path == "transparent" and self.mode == "wallpaper":
            subprocess.Popen(["pkill", "-x", "swww-daemon"])

        self.close()

    def on_destroy(self, widget):
        if self.idle_loader_id is not None:
            GLib.source_remove(self.idle_loader_id)
            self.idle_loader_id = None
        if self.preview_timer_id is not None:
            GLib.source_remove(self.preview_timer_id)
            self.preview_timer_id = None

        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE) as f:
                    if int(f.read().strip()) == os.getpid():
                        os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

if __name__ == "__main__":
    win = LiveWallpaperSelector()
    win.show_all()

    # Find matching card for current active wallpaper
    initial_child = None
    for item in win.cards_data:
        if win.initial_path and item["path"] == win.initial_path:
            initial_child = item["child"]
            break
        elif win.initial_path == "transparent" and item["type"] == "transparent":
            initial_child = item["child"]
            break

    visible = win.get_visible_items()
    if initial_child and initial_child.get_visible():
        win.flowbox.select_child(initial_child)
    elif visible:
        win.flowbox.select_child(visible[0]["child"])

    # Ensure no preview runs until user actually moves with arrow keys or clicks
    win.user_navigated = False
    if win.preview_timer_id is not None:
        GLib.source_remove(win.preview_timer_id)
        win.preview_timer_id = None

    Gtk.main()
