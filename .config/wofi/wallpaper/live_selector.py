#!/usr/bin/env python3
import os
import sys
import glob
import random
import subprocess

# Ensure XDG_DATA_DIRS includes /usr/share for MIME & GdkPixbuf loaders
os.environ["XDG_DATA_DIRS"] = f"/usr/share:/usr/local/share:{os.path.expanduser('~/.local/share')}:{os.environ.get('XDG_DATA_DIRS', '')}"

PID_FILE = "/tmp/wallpaper_live_selector.pid"
if os.path.exists(PID_FILE):
    try:
        with open(PID_FILE) as f:
            old_pid = int(f.read().strip())
        if os.path.exists(f"/proc/{old_pid}"):
            os.kill(old_pid, 9)
            os.remove(PID_FILE)
            sys.exit(0)
    except Exception:
        pass

with open(PID_FILE, "w") as f:
    f.write(str(os.getpid()))

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

class LiveWallpaperSelector(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.mode = MODE
        self.selected_item = None
        self.preview_timer_id = None
        self.initial_path = self.get_current_wallpaper()

        # GtkLayerShell overlay configuration
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        
        # Center in active monitor
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)

        self.set_default_size(890, 680)

        self.setup_ui()
        self.apply_css()

        self.connect("destroy", self.on_destroy)
        self.connect("key-press-event", self.on_key_press)

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
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_name("outer-box")
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        self.add(main_box)

        # Header Search entry
        prompt_text = "🌌 Overview orqa fonini tanlang (Strelkalar bilan yuring)..." if self.mode == "overview" else "🖼️ Fon rasmini tanlang (Strelkalar bilan yuring)..."
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(prompt_text)
        self.search_entry.set_name("input")
        self.search_entry.connect("search-changed", self.on_search_changed)
        main_box.pack_start(self.search_entry, False, False, 0)

        # Scrolled window
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_name("scroll")
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_box.pack_start(self.scrolled, True, True, 0)

        # FlowBox for 3-column grid
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_name("inner-box")
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_min_children_per_line(3)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.connect("selected-children-changed", self.on_selection_changed)
        self.flowbox.connect("child-activated", self.on_child_activated)
        self.scrolled.add(self.flowbox)

        self.cards_data = []
        self.load_cards()

    def load_cards(self):
        # 1. Shuffle card
        shuffle_icon = os.path.join(CACHE_DIR, "000_random_tasodifiy_shuffle.png")
        if os.path.isfile(shuffle_icon):
            self.add_card("shuffle", "Tasodifiy", shuffle_icon)

        # 2. Transparent card (only for desktop wallpaper)
        if self.mode == "wallpaper":
            trans_icon = os.path.join(CACHE_DIR, "001_transparent_shaffof.png")
            if os.path.isfile(trans_icon):
                self.add_card("transparent", "Shaffof", trans_icon)

        # 3. Wallpaper images
        wallpapers = sorted([f for f in os.listdir(WP_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
        for wp in wallpapers:
            base = os.path.splitext(wp)[0]
            thumb = os.path.join(CACHE_DIR, base + ".png")
            full_path = os.path.join(WP_DIR, wp)
            if os.path.isfile(thumb):
                self.add_card("image", full_path, thumb, name=base)

        self.flowbox.show_all()

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
            background-color: rgba(20, 21, 24, 0.96);
            border: 1.5px solid rgba(255, 255, 255, 0.15);
            border-radius: 20px;
        }
        #input {
            background-color: rgba(255, 255, 255, 0.08);
            border: 1.5px solid rgba(255, 255, 255, 0.14);
            border-radius: 14px;
            padding: 10px 16px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 500;
            margin: 4px 6px 8px 6px;
        }
        #input:focus {
            border: 1.5px solid #10b981;
            background-color: rgba(255, 255, 255, 0.12);
        }
        #entry {
            padding: 2px;
            margin: 4px;
            background-color: transparent;
            border-radius: 14px;
            border: 2.5px solid transparent;
            transition: all 0.15s ease-in-out;
        }
        #entry:selected {
            background-color: transparent;
            border: 2.5px solid #10b981;
            box-shadow: 0 0 16px rgba(16, 185, 129, 0.7);
        }
        #img {
            border-radius: 10px;
        }
        scrollbar {
            background: transparent;
            border: none;
        }
        scrollbar slider {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 6px;
            min-width: 4px;
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
        text = entry.get_text().strip().lower()
        first_visible = None
        for item in self.cards_data:
            match = (not text) or (text in item["name"]) or (item["type"] in ["shuffle", "transparent"])
            item["child"].set_visible(match)
            if match and first_visible is None:
                first_visible = item["child"]
        if first_visible:
            self.flowbox.select_child(first_visible)

    def on_selection_changed(self, flowbox):
        selected = flowbox.get_selected_children()
        if not selected:
            return
        child = selected[0]
        for item in self.cards_data:
            if item["child"] == child:
                self.selected_item = item
                break

        # Debounce live preview by 60ms so fast arrow clicks don't queue multiple transitions
        if self.preview_timer_id is not None:
            GLib.source_remove(self.preview_timer_id)
            self.preview_timer_id = None

        self.preview_timer_id = GLib.timeout_add(60, self.do_live_preview)

    def do_live_preview(self):
        self.preview_timer_id = None
        if not self.selected_item:
            return False

        item_type = self.selected_item["type"]
        path = self.selected_item["path"]

        if self.mode == "wallpaper":
            if item_type == "shuffle":
                all_wps = [os.path.join(WP_DIR, f) for f in os.listdir(WP_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                if all_wps:
                    rand_wp = random.choice(all_wps)
                    subprocess.Popen([
                        "swww", "img", rand_wp,
                        "--transition-type", "wipe",
                        "--transition-angle", "30",
                        "--transition-fps", "60",
                        "--transition-duration", "0.5"
                    ])
            elif item_type == "transparent":
                subprocess.Popen(["pkill", "-x", "swww-daemon"])
            else:
                if not os.path.exists("/run/user/1000/swww-wayland-1.socket"):
                    subprocess.Popen(["swww-daemon"])
                subprocess.Popen([
                    "swww", "img", path,
                    "--transition-type", "wipe",
                    "--transition-angle", "30",
                    "--transition-fps", "60",
                    "--transition-duration", "0.5"
                ])
        else: # overview
            env = os.environ.copy()
            env["WAYLAND_DISPLAY"] = "wayland-overview"
            if item_type == "shuffle":
                all_wps = [os.path.join(WP_DIR, f) for f in os.listdir(WP_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                if all_wps:
                    rand_wp = random.choice(all_wps)
                    subprocess.Popen([
                        "swww", "img", rand_wp,
                        "--transition-type", "wipe",
                        "--transition-angle", "30",
                        "--transition-fps", "60",
                        "--transition-duration", "0.5"
                    ], env=env)
            else:
                subprocess.Popen([
                    "swww", "img", path,
                    "--transition-type", "wipe",
                    "--transition-angle", "30",
                    "--transition-fps", "60",
                    "--transition-duration", "0.5"
                ], env=env)

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

        # Arrow navigation
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
        else:
            return False

        if new_idx != current_idx:
            target_child = visible[new_idx]["child"]
            self.flowbox.select_child(target_child)
            
            # Smoothly scroll to reveal target_child
            adj = self.scrolled.get_vadjustment()
            alloc = target_child.get_allocation()
            if alloc.y < adj.get_value():
                adj.set_value(max(0, alloc.y - 10))
            elif alloc.y + alloc.height > adj.get_value() + adj.get_page_size():
                adj.set_value(alloc.y + alloc.height - adj.get_page_size() + 10)

            return True

        return False

    def restore_initial_and_close(self):
        if self.initial_path and os.path.isfile(self.initial_path):
            if self.mode == "wallpaper":
                subprocess.Popen([
                    "swww", "img", self.initial_path,
                    "--transition-type", "wipe",
                    "--transition-angle", "30",
                    "--transition-fps", "60",
                    "--transition-duration", "0.4"
                ])
            else:
                env = os.environ.copy()
                env["WAYLAND_DISPLAY"] = "wayland-overview"
                subprocess.Popen([
                    "swww", "img", self.initial_path,
                    "--transition-type", "wipe",
                    "--transition-angle", "30",
                    "--transition-fps", "60",
                    "--transition-duration", "0.4"
                ], env=env)
        elif self.initial_path == "transparent" and self.mode == "wallpaper":
            subprocess.Popen(["pkill", "-x", "swww-daemon"])

        self.close()

    def on_destroy(self, widget):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

if __name__ == "__main__":
    win = LiveWallpaperSelector()
    win.show_all()
    # Initially select first child
    visible = win.get_visible_items()
    if visible:
        win.flowbox.select_child(visible[0]["child"])
    Gtk.main()
