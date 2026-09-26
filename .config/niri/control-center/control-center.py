#!/usr/bin/env python3
import os
import sys
import signal
import time
import subprocess
import threading
from datetime import datetime

# Disable accessibility bridge to eliminate 250-500ms D-Bus timeouts
os.environ["NO_AT_BRIDGE"] = "1"
os.environ["GTK_A11Y"] = "none"

# Ensure standard system data dirs exist in XDG_DATA_DIRS for MIME and icons
xdg = os.environ.get("XDG_DATA_DIRS", "")
std_dirs = "/usr/share:/usr/local/share:" + os.path.expanduser("~/.local/share")
if "/usr/share" not in xdg:
    os.environ["XDG_DATA_DIRS"] = std_dirs + (":" + xdg if xdg else "")

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

PID_FILE = "/tmp/niri-control-center.pid"

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

def run_cmd(cmd, timeout=5):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip(), res.returncode
    except Exception as e:
        return "", -1

class ControlCenterWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Boshqaruv Markazi")

        # Layer Shell Setup
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.set_default_size(700, 530)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Load CSS
        self.load_css()

        # Keyboard shortcuts (Escape closes)
        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.on_destroy)

        # Main Layout Box
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_vbox)

        # 1. Header Bar
        main_vbox.pack_start(self.create_header(), False, False, 0)

        # 2. Top Quick Action Tabs
        main_vbox.pack_start(self.create_top_tabs(), False, False, 0)

        # 3. Dynamic Stack Content
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(200)

        self.page_hotspot = self.create_hotspot_page()
        self.page_wifi = self.create_wifi_page()
        self.page_bluetooth = self.create_bluetooth_page()
        self.page_ethernet = self.create_ethernet_page()

        self.stack.add_named(self.page_hotspot, "hotspot")
        self.stack.add_named(self.page_wifi, "wifi")
        self.stack.add_named(self.page_bluetooth, "bluetooth")
        self.stack.add_named(self.page_ethernet, "ethernet")

        main_vbox.pack_start(self.stack, True, True, 0)

        # State tracking
        self.updating_ui = False
        self.current_tab = "hotspot"
        self.switch_tab("hotspot")

        # Start periodic status refresh
        self.refresh_all_status()
        GLib.timeout_add_seconds(3, self.periodic_check)

    def load_css(self):
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)
            settings.set_property("gtk-theme-name", "Adwaita-dark")

        css_provider = Gtk.CssProvider()
        css_path = os.path.expanduser("~/.config/niri/control-center/style.css")
        if os.path.exists(css_path):
            css_provider.load_from_path(css_path)
            screen = Gdk.Screen.get_default()
            Gtk.StyleContext.add_provider_for_screen(
                screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
            )

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape or event.hardware_keycode == 9:
            self.close_window()
            return True
        return False

    def close_window(self, *args):
        cleanup_pid()
        Gtk.main_quit()

    def on_destroy(self, *args):
        cleanup_pid()
        Gtk.main_quit()

    # ── Header ──────────────────────────────────────────────────────────
    def create_header(self):
        grid = Gtk.Grid()
        grid.set_column_homogeneous(True)
        grid.get_style_context().add_class("header-box")

        title = Gtk.Label(label="⚡  Boshqaruv Markazi")
        title.set_halign(Gtk.Align.START)
        title.get_style_context().add_class("header-title")
        grid.attach(title, 0, 0, 1, 1)

        self.lbl_time = Gtk.Label()
        self.lbl_time.set_halign(Gtk.Align.CENTER)
        self.lbl_time.get_style_context().add_class("header-time")
        self.update_time()
        GLib.timeout_add_seconds(10, self.update_time)
        grid.attach(self.lbl_time, 1, 0, 1, 1)

        btn_close = Gtk.Button(label="✕")
        btn_close.set_halign(Gtk.Align.END)
        btn_close.get_style_context().add_class("btn-close")
        btn_close.connect("clicked", self.close_window)
        grid.attach(btn_close, 2, 0, 1, 1)

        return grid

    def update_time(self):
        now = datetime.now().strftime("%H:%M")
        self.lbl_time.set_text(now)
        return True

    # ── Top Quick Action Tabs ──────────────────────────────────────────
    def create_top_tabs(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_homogeneous(True)
        box.get_style_context().add_class("tabs-box")

        # Tab 1: Hotspot
        self.btn_tab_hotspot = Gtk.Button()
        self.btn_tab_hotspot.get_style_context().add_class("tab-btn")
        self.btn_tab_hotspot.connect("clicked", lambda w: self.switch_tab("hotspot"))
        self.lbl_hotspot_badge = Gtk.Label(label="O'CHIQ")
        self.lbl_hotspot_badge.get_style_context().add_class("tab-badge-off")
        box.pack_start(self.make_tab_content("📡", "Hotspot", self.lbl_hotspot_badge, self.btn_tab_hotspot), True, True, 0)

        # Tab 2: Wi-Fi
        self.btn_tab_wifi = Gtk.Button()
        self.btn_tab_wifi.get_style_context().add_class("tab-btn")
        self.btn_tab_wifi.connect("clicked", lambda w: self.switch_tab("wifi"))
        self.lbl_wifi_badge = Gtk.Label(label="YONIQ")
        self.lbl_wifi_badge.get_style_context().add_class("tab-badge-on")
        box.pack_start(self.make_tab_content("📶", "Wi-Fi", self.lbl_wifi_badge, self.btn_tab_wifi), True, True, 0)

        # Tab 3: Bluetooth
        self.btn_tab_bt = Gtk.Button()
        self.btn_tab_bt.get_style_context().add_class("tab-btn")
        self.btn_tab_bt.connect("clicked", lambda w: self.switch_tab("bluetooth"))
        self.lbl_bt_badge = Gtk.Label(label="O'CHIQ")
        self.lbl_bt_badge.get_style_context().add_class("tab-badge-off")
        box.pack_start(self.make_tab_content("🔵", "Bluetooth", self.lbl_bt_badge, self.btn_tab_bt), True, True, 0)

        # Tab 4: Ethernet
        self.btn_tab_eth = Gtk.Button()
        self.btn_tab_eth.get_style_context().add_class("tab-btn")
        self.btn_tab_eth.connect("clicked", lambda w: self.switch_tab("ethernet"))
        self.lbl_eth_badge = Gtk.Label(label="eno1")
        self.lbl_eth_badge.get_style_context().add_class("tab-badge-on")
        box.pack_start(self.make_tab_content("🌐", "Ethernet", self.lbl_eth_badge, self.btn_tab_eth), True, True, 0)

        return box

    def make_tab_content(self, icon, title, badge_lbl, button):
        inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_icon = Gtk.Label(label=icon)
        lbl_icon.get_style_context().add_class("tab-icon")
        inner.pack_start(lbl_icon, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label(label=title)
        lbl_title.set_xalign(0)
        lbl_title.get_style_context().add_class("tab-title")
        v.pack_start(lbl_title, False, False, 0)

        badge_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        badge_box.pack_start(badge_lbl, False, False, 0)
        v.pack_start(badge_box, False, False, 0)

        inner.pack_start(v, True, True, 0)
        button.add(inner)
        return button

    def switch_tab(self, name):
        self.current_tab = name
        self.stack.set_visible_child_name(name)

        # Update button highlights
        tabs = [
            ("hotspot", self.btn_tab_hotspot),
            ("wifi", self.btn_tab_wifi),
            ("bluetooth", self.btn_tab_bt),
            ("ethernet", self.btn_tab_eth),
        ]
        for tab_name, btn in tabs:
            ctx = btn.get_style_context()
            if tab_name == name:
                ctx.add_class("tab-btn-active")
            else:
                ctx.remove_class("tab-btn-active")

        # Specific page refreshes
        if name == "wifi":
            self.refresh_wifi_scan()
        elif name == "hotspot":
            self.refresh_hotspot_clients()
        elif name == "bluetooth":
            self.refresh_bluetooth_devices()

    # ── Page 1: Hotspot ────────────────────────────────────────────────
    def create_hotspot_page(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        container.get_style_context().add_class("content-box")

        # 1. Main Status Card with Switch
        card_status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card_status.get_style_context().add_class("card")

        icon = Gtk.Label(label="📡")
        icon.set_markup("<span font='24'>📡</span>")
        card_status.pack_start(icon, False, False, 4)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.lbl_hotspot_status = Gtk.Label(label="Wi-Fi Hotspot")
        self.lbl_hotspot_status.set_xalign(0)
        self.lbl_hotspot_status.get_style_context().add_class("card-title")
        info_box.pack_start(self.lbl_hotspot_status, False, False, 0)

        self.lbl_hotspot_desc = Gtk.Label(label="Oʻchiq")
        self.lbl_hotspot_desc.set_xalign(0)
        self.lbl_hotspot_desc.get_style_context().add_class("card-desc")
        info_box.pack_start(self.lbl_hotspot_desc, False, False, 0)
        card_status.pack_start(info_box, True, True, 0)

        self.switch_hotspot = Gtk.Switch()
        self.switch_hotspot.set_valign(Gtk.Align.CENTER)
        self.switch_hotspot.connect("notify::active", self.on_hotspot_switch_toggled)
        card_status.pack_end(self.switch_hotspot, False, False, 0)
        container.pack_start(card_status, False, False, 0)

        # 2. SSID, Password & Limit Row
        row_params = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # SSID & Password Card
        card_cred = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_cred.get_style_context().add_class("card")

        lbl_ssid = Gtk.Label()
        lbl_ssid.set_markup("<b>SSID:</b> <span color='#10b981' weight='bold'>Niri</span>")
        lbl_ssid.set_xalign(0)
        card_cred.pack_start(lbl_ssid, False, False, 0)

        pass_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_pass = Gtk.Label()
        lbl_pass.set_markup("<b>Parol:</b> <tt>330440311</tt>")
        lbl_pass.set_xalign(0)
        pass_row.pack_start(lbl_pass, False, False, 0)

        self.btn_copy_pass = Gtk.Button(label="Nusxalash")
        self.btn_copy_pass.get_style_context().add_class("btn-secondary")
        self.btn_copy_pass.connect("clicked", self.on_copy_password)
        pass_row.pack_end(self.btn_copy_pass, False, False, 0)
        card_cred.pack_start(pass_row, False, False, 0)

        row_params.pack_start(card_cred, True, True, 0)

        # Limit Card
        card_limit = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_limit.get_style_context().add_class("card")

        lbl_lim = Gtk.Label(label="Maksimal ulanishlar soni:")
        lbl_lim.set_xalign(0)
        lbl_lim.get_style_context().add_class("card-title")
        card_limit.pack_start(lbl_lim, False, False, 0)

        lim_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.spin_limit = Gtk.SpinButton.new_with_range(1, 50, 1)
        self.spin_limit.set_value(10)
        lim_row.pack_start(self.spin_limit, True, True, 0)

        btn_apply_lim = Gtk.Button(label="Qo'llash")
        btn_apply_lim.get_style_context().add_class("btn-primary")
        btn_apply_lim.connect("clicked", self.on_apply_limit)
        lim_row.pack_end(btn_apply_lim, False, False, 0)
        card_limit.pack_start(lim_row, False, False, 0)

        row_params.pack_start(card_limit, True, True, 0)
        container.pack_start(row_params, False, False, 0)

        # 3. Connected Devices Section
        hdr_dev = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_clients_hdr = Gtk.Label(label="Ulangan qurilmalar")
        self.lbl_clients_hdr.get_style_context().add_class("card-title")
        hdr_dev.pack_start(self.lbl_clients_hdr, False, False, 0)

        btn_ref_dev = Gtk.Button(label="🔄 Yangilash")
        btn_ref_dev.get_style_context().add_class("btn-secondary")
        btn_ref_dev.connect("clicked", lambda w: self.refresh_hotspot_clients())
        hdr_dev.pack_end(btn_ref_dev, False, False, 0)
        container.pack_start(hdr_dev, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(140)

        self.box_clients = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll.add(self.box_clients)
        container.pack_start(scroll, True, True, 0)

        return container

    def on_copy_password(self, btn):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text("330440311", -1)
        btn.set_label("Nusxalandi! ✓")
        GLib.timeout_add_seconds(2, lambda: btn.set_label("Nusxalash"))

    def on_apply_limit(self, btn):
        val = int(self.spin_limit.get_value())
        threading.Thread(target=self._apply_limit_thread, args=(val,), daemon=True).start()

    def _apply_limit_thread(self, limit):
        run_cmd(f"{os.path.expanduser('~/.local/bin/share-on')} {limit}")
        GLib.idle_add(self.refresh_all_status)
        run_cmd(f"notify-send '📡 Hotspot (Niri)' 'Limit {limit} ta qurilmaga oʻzgartirildi' -u normal")

    def on_hotspot_switch_toggled(self, switch, gparam):
        if self.updating_ui:
            return
        is_active = switch.get_active()
        limit = int(self.spin_limit.get_value())
        threading.Thread(target=self._toggle_hotspot_thread, args=(is_active, limit), daemon=True).start()

    def _toggle_hotspot_thread(self, enable, limit):
        if enable:
            run_cmd(f"{os.path.expanduser('~/.local/bin/share-on')} {limit}")
            run_cmd("notify-send '📡 Hotspot (Niri)' 'Hotspot muvaffaqiyatli yoqildi' -u normal")
        else:
            run_cmd(f"{os.path.expanduser('~/.local/bin/share-off')}")
            run_cmd("notify-send '📡 Hotspot (Niri)' 'Hotspot oʻchirildi' -u normal")
        GLib.idle_add(self.refresh_all_status)

    def refresh_hotspot_clients(self):
        threading.Thread(target=self._fetch_hotspot_clients, daemon=True).start()

    def _fetch_hotspot_clients(self):
        out, _ = run_cmd("ip neigh show dev wlo1")
        lines = [l for l in out.splitlines() if "FAILED" not in l and l.strip()]
        clients = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                ip = parts[0]
                mac = parts[2]
                state = parts[3]
                clients.append((ip, mac, state))
        GLib.idle_add(self._render_hotspot_clients, clients)

    def _render_hotspot_clients(self, clients):
        for child in self.box_clients.get_children():
            self.box_clients.remove(child)

        self.lbl_clients_hdr.set_text(f"Ulangan qurilmalar ({len(clients)} ta)")

        if not clients:
            lbl = Gtk.Label(label="Hozircha hech qanday qurilma ulanmagan.")
            lbl.get_style_context().add_class("card-desc")
            lbl.set_padding(10, 10)
            self.box_clients.pack_start(lbl, False, False, 0)
        else:
            for ip, mac, state in clients:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                row.get_style_context().add_class("list-item")

                icon = Gtk.Label(label="📱")
                row.pack_start(icon, False, False, 4)

                v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                l_ip = Gtk.Label()
                l_ip.set_markup(f"<b>IP:</b> <tt>{ip}</tt>")
                l_ip.set_xalign(0)
                v.pack_start(l_ip, False, False, 0)

                l_mac = Gtk.Label()
                l_mac.set_markup(f"<span color='#9ca3af'>{mac}</span>")
                l_mac.set_xalign(0)
                v.pack_start(l_mac, False, False, 0)
                row.pack_start(v, True, True, 0)

                badge = Gtk.Label(label="Faol" if state in ["REACHABLE", "STALE"] else state)
                badge.get_style_context().add_class("tab-badge-on" if state in ["REACHABLE", "STALE"] else "tab-badge-off")
                row.pack_end(badge, False, False, 4)

                self.box_clients.pack_start(row, False, False, 0)

        self.box_clients.show_all()

    # ── Page 2: Wi-Fi ──────────────────────────────────────────────────
    def create_wifi_page(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        container.get_style_context().add_class("content-box")

        # 1. Main Status Card
        card_status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card_status.get_style_context().add_class("card")

        icon = Gtk.Label(label="📶")
        icon.set_markup("<span font='24'>📶</span>")
        card_status.pack_start(icon, False, False, 4)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.lbl_wifi_status = Gtk.Label(label="Wi-Fi Tarmoqlari")
        self.lbl_wifi_status.set_xalign(0)
        self.lbl_wifi_status.get_style_context().add_class("card-title")
        info_box.pack_start(self.lbl_wifi_status, False, False, 0)

        self.lbl_wifi_desc = Gtk.Label(label="Faol")
        self.lbl_wifi_desc.set_xalign(0)
        self.lbl_wifi_desc.get_style_context().add_class("card-desc")
        info_box.pack_start(self.lbl_wifi_desc, False, False, 0)
        card_status.pack_start(info_box, True, True, 0)

        self.switch_wifi = Gtk.Switch()
        self.switch_wifi.set_valign(Gtk.Align.CENTER)
        self.switch_wifi.connect("notify::active", self.on_wifi_switch_toggled)
        card_status.pack_end(self.switch_wifi, False, False, 0)
        container.pack_start(card_status, False, False, 0)

        # 2. Available Networks Header
        hdr_net = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_wifi_list_hdr = Gtk.Label(label="Atrofdagi Wi-Fi tarmoqlari")
        self.lbl_wifi_list_hdr.get_style_context().add_class("card-title")
        hdr_net.pack_start(self.lbl_wifi_list_hdr, False, False, 0)

        self.btn_scan_wifi = Gtk.Button(label="🔄 Qidirish")
        self.btn_scan_wifi.get_style_context().add_class("btn-secondary")
        self.btn_scan_wifi.connect("clicked", lambda w: self.refresh_wifi_scan())
        hdr_net.pack_end(self.btn_scan_wifi, False, False, 0)
        container.pack_start(hdr_net, False, False, 0)

        # 3. Networks List Scroll
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(250)

        self.box_wifi_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll.add(self.box_wifi_list)
        container.pack_start(scroll, True, True, 0)

        return container

    def on_wifi_switch_toggled(self, switch, gparam):
        if self.updating_ui:
            return
        is_active = switch.get_active()
        threading.Thread(target=self._toggle_wifi_thread, args=(is_active,), daemon=True).start()

    def _toggle_wifi_thread(self, enable):
        state = "on" if enable else "off"
        run_cmd(f"nmcli radio wifi {state}")
        GLib.idle_add(self.refresh_all_status)
        run_cmd(f"notify-send '📶 Wi-Fi' 'Wi-Fi {state.upper()} qilindi' -u normal")

    def refresh_wifi_scan(self):
        self.btn_scan_wifi.set_label("Qidirilmoqda...")
        self.btn_scan_wifi.set_sensitive(False)
        threading.Thread(target=self._scan_wifi_thread, daemon=True).start()

    def _scan_wifi_thread(self):
        out, _ = run_cmd("nmcli -t -f active,ssid,signal,security device wifi list --rescan yes", timeout=8)
        networks = []
        seen = set()
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 4:
                active = (parts[0] == "yes")
                ssid = parts[1].strip()
                signal = parts[2].strip()
                sec = parts[3].strip() if len(parts) > 3 else "Open"
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    networks.append((active, ssid, signal, sec))
        GLib.idle_add(self._render_wifi_networks, networks)

    def _render_wifi_networks(self, networks):
        self.btn_scan_wifi.set_label("🔄 Qidirish")
        self.btn_scan_wifi.set_sensitive(True)

        for child in self.box_wifi_list.get_children():
            self.box_wifi_list.remove(child)

        if not networks:
            lbl = Gtk.Label(label="Tarmoqlar topilmadi yoki Wi-Fi o'chiq.")
            lbl.get_style_context().add_class("card-desc")
            self.box_wifi_list.pack_start(lbl, False, False, 10)
        else:
            for active, ssid, sig, sec in networks:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                row.get_style_context().add_class("list-item")

                icon_str = "📶" if active else "◽"
                l_icon = Gtk.Label(label=icon_str)
                row.pack_start(l_icon, False, False, 4)

                v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                l_ssid = Gtk.Label()
                if active:
                    l_ssid.set_markup(f"<b>{ssid}</b>  <span color='#10b981' weight='bold'>✓ Ulangan</span>")
                else:
                    l_ssid.set_markup(f"<b>{ssid}</b>")
                l_ssid.set_xalign(0)
                v.pack_start(l_ssid, False, False, 0)

                sec_info = "🔒 Himoyalangan" if sec and "WPA" in sec else "🔓 Ochiq"
                l_sec = Gtk.Label()
                l_sec.set_markup(f"<span color='#9ca3af'>{sec_info}   •   Signal: {sig}%</span>")
                l_sec.set_xalign(0)
                v.pack_start(l_sec, False, False, 0)
                row.pack_start(v, True, True, 0)

                if active:
                    btn_disc = Gtk.Button(label="Uzish")
                    btn_disc.get_style_context().add_class("btn-secondary")
                    btn_disc.connect("clicked", lambda w, s=ssid: self.on_disconnect_wifi(s))
                    row.pack_end(btn_disc, False, False, 4)
                else:
                    btn_conn = Gtk.Button(label="Ulanish")
                    btn_conn.get_style_context().add_class("btn-primary")
                    btn_conn.connect("clicked", lambda w, s=ssid, sc=sec: self.on_connect_wifi(s, sc))
                    row.pack_end(btn_conn, False, False, 4)

                self.box_wifi_list.pack_start(row, False, False, 0)

        self.box_wifi_list.show_all()

    def on_disconnect_wifi(self, ssid):
        threading.Thread(target=lambda: run_cmd(f"nmcli connection down id '{ssid}'"), daemon=True).start()
        GLib.timeout_add_seconds(1, self.refresh_wifi_scan)

    def on_connect_wifi(self, ssid, security):
        if "WPA" in security:
            # Show Password Dialog
            dialog = Gtk.Dialog(title=f"{ssid} tarmog'iga ulanish", parent=self, flags=Gtk.DialogFlags.MODAL)
            dialog.set_default_size(320, 160)
            d_box = dialog.get_content_area()
            d_box.set_spacing(10)
            d_box.set_margin_top(15)
            d_box.set_margin_bottom(15)
            d_box.set_margin_start(15)
            d_box.set_margin_end(15)

            lbl = Gtk.Label(label=f"'{ssid}' parolini kiriting:")
            lbl.set_xalign(0)
            d_box.pack_start(lbl, False, False, 0)

            entry = Gtk.Entry()
            entry.set_visibility(False)
            d_box.pack_start(entry, False, False, 0)

            dialog.add_button("Bekor qilish", Gtk.ResponseType.CANCEL)
            dialog.add_button("Ulanish", Gtk.ResponseType.OK)
            dialog.show_all()

            resp = dialog.run()
            pwd = entry.get_text()
            dialog.destroy()

            if resp == Gtk.ResponseType.OK and pwd:
                def _connect():
                    run_cmd(f"nmcli device wifi connect '{ssid}' password '{pwd}'", timeout=15)
                    GLib.idle_add(self.refresh_wifi_scan)
                threading.Thread(target=_connect, daemon=True).start()
        else:
            threading.Thread(target=lambda: run_cmd(f"nmcli device wifi connect '{ssid}'"), daemon=True).start()
            GLib.timeout_add_seconds(2, self.refresh_wifi_scan)

    # ── Page 3: Bluetooth ──────────────────────────────────────────────
    def create_bluetooth_page(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        container.get_style_context().add_class("content-box")

        # 1. Status Card
        card_status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card_status.get_style_context().add_class("card")

        icon = Gtk.Label(label="🔵")
        icon.set_markup("<span font='24'>🔵</span>")
        card_status.pack_start(icon, False, False, 4)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.lbl_bt_status = Gtk.Label(label="Bluetooth")
        self.lbl_bt_status.set_xalign(0)
        self.lbl_bt_status.get_style_context().add_class("card-title")
        info_box.pack_start(self.lbl_bt_status, False, False, 0)

        self.lbl_bt_desc = Gtk.Label(label="Oʻchiq")
        self.lbl_bt_desc.set_xalign(0)
        self.lbl_bt_desc.get_style_context().add_class("card-desc")
        info_box.pack_start(self.lbl_bt_desc, False, False, 0)
        card_status.pack_start(info_box, True, True, 0)

        self.switch_bt = Gtk.Switch()
        self.switch_bt.set_valign(Gtk.Align.CENTER)
        self.switch_bt.connect("notify::active", self.on_bt_switch_toggled)
        card_status.pack_end(self.switch_bt, False, False, 0)
        container.pack_start(card_status, False, False, 0)

        # 2. Devices Header
        hdr_bt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_bt_list_hdr = Gtk.Label(label="Juftlangan qurilmalar")
        self.lbl_bt_list_hdr.get_style_context().add_class("card-title")
        hdr_bt.pack_start(self.lbl_bt_list_hdr, False, False, 0)

        self.btn_scan_bt = Gtk.Button(label="🔍 Qidirish (Scan)")
        self.btn_scan_bt.get_style_context().add_class("btn-secondary")
        self.btn_scan_bt.connect("clicked", lambda w: self.on_bt_scan_toggle())
        hdr_bt.pack_end(self.btn_scan_bt, False, False, 0)
        container.pack_start(hdr_bt, False, False, 0)

        # 3. Devices List
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(250)

        self.box_bt_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll.add(self.box_bt_list)
        container.pack_start(scroll, True, True, 0)

        return container

    def on_bt_switch_toggled(self, switch, gparam):
        if self.updating_ui:
            return
        is_active = switch.get_active()
        threading.Thread(target=self._toggle_bt_thread, args=(is_active,), daemon=True).start()

    def _toggle_bt_thread(self, enable):
        if enable:
            run_cmd("systemctl start bluetooth 2>/dev/null || pkexec systemctl start bluetooth")
            run_cmd("bluetoothctl power on")
            run_cmd("notify-send '🔵 Bluetooth' 'Bluetooth yoqildi' -u normal")
        else:
            run_cmd("bluetoothctl power off")
            run_cmd("notify-send '🔵 Bluetooth' 'Bluetooth oʻchirildi' -u normal")
        GLib.idle_add(self.refresh_all_status)

    def on_bt_scan_toggle(self):
        self.btn_scan_bt.set_label("Qidirilmoqda...")
        threading.Thread(target=self._bt_scan_thread, daemon=True).start()

    def _bt_scan_thread(self):
        run_cmd("timeout 5 bluetoothctl scan on")
        GLib.idle_add(self.refresh_bluetooth_devices)

    def refresh_bluetooth_devices(self):
        threading.Thread(target=self._fetch_bt_devices, daemon=True).start()

    def _fetch_bt_devices(self):
        out, _ = run_cmd("bluetoothctl devices")
        devs = []
        for line in out.splitlines():
            parts = line.split(maxsplit=2)
            if len(parts) >= 3 and parts[0] == "Device":
                mac = parts[1]
                name = parts[2]
                info, _ = run_cmd(f"bluetoothctl info {mac}")
                is_connected = "Connected: yes" in info
                devs.append((mac, name, is_connected))
        GLib.idle_add(self._render_bt_devices, devs)

    def _render_bt_devices(self, devs):
        self.btn_scan_bt.set_label("🔍 Qidirish (Scan)")
        for child in self.box_bt_list.get_children():
            self.box_bt_list.remove(child)

        if not devs:
            lbl = Gtk.Label(label="Qurilmalar mavjud emas yoki Bluetooth o'chiq.")
            lbl.get_style_context().add_class("card-desc")
            self.box_bt_list.pack_start(lbl, False, False, 10)
        else:
            for mac, name, is_conn in devs:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                row.get_style_context().add_class("list-item")

                icon = Gtk.Label(label="🎧" if "head" in name.lower() or "airpod" in name.lower() else "📱")
                row.pack_start(icon, False, False, 4)

                v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                l_name = Gtk.Label()
                l_name.set_markup(f"<b>{name}</b>")
                l_name.set_xalign(0)
                v.pack_start(l_name, False, False, 0)

                l_mac = Gtk.Label()
                l_mac.set_markup(f"<span color='#9ca3af'>{mac}</span>")
                l_mac.set_xalign(0)
                v.pack_start(l_mac, False, False, 0)
                row.pack_start(v, True, True, 0)

                if is_conn:
                    btn_disc = Gtk.Button(label="Uzish")
                    btn_disc.get_style_context().add_class("btn-secondary")
                    btn_disc.connect("clicked", lambda w, m=mac: self.on_bt_connect_toggle(m, False))
                    row.pack_end(btn_disc, False, False, 4)
                else:
                    btn_conn = Gtk.Button(label="Ulanish")
                    btn_conn.get_style_context().add_class("btn-primary")
                    btn_conn.connect("clicked", lambda w, m=mac: self.on_bt_connect_toggle(m, True))
                    row.pack_end(btn_conn, False, False, 4)

                self.box_bt_list.pack_start(row, False, False, 0)

        self.box_bt_list.show_all()

    def on_bt_connect_toggle(self, mac, connect):
        action = "connect" if connect else "disconnect"
        def _th():
            run_cmd(f"bluetoothctl {action} {mac}")
            GLib.idle_add(self.refresh_bluetooth_devices)
        threading.Thread(target=_th, daemon=True).start()

    # ── Page 4: Ethernet ───────────────────────────────────────────────
    def create_ethernet_page(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        container.get_style_context().add_class("content-box")

        # 1. Ethernet Status Card
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("card")

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Label(label="🌐")
        icon.set_markup("<span font='22'>🌐</span>")
        top.pack_start(icon, False, False, 0)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label(label="Simli tarmoq (eno1)")
        lbl_title.set_xalign(0)
        lbl_title.get_style_context().add_class("card-title")
        v.pack_start(lbl_title, False, False, 0)

        self.lbl_eth_ip = Gtk.Label(label="IP: Aniqlanmoqda...")
        self.lbl_eth_ip.set_xalign(0)
        self.lbl_eth_ip.get_style_context().add_class("card-desc")
        v.pack_start(self.lbl_eth_ip, False, False, 0)
        top.pack_start(v, True, True, 0)

        self.badge_eth_status = Gtk.Label(label="ULANGAN")
        self.badge_eth_status.get_style_context().add_class("tab-badge-on")
        top.pack_end(self.badge_eth_status, False, False, 0)
        card.pack_start(top, False, False, 0)

        # Gateway & DNS
        self.lbl_eth_details = Gtk.Label()
        self.lbl_eth_details.set_xalign(0)
        card.pack_start(self.lbl_eth_details, False, False, 4)
        container.pack_start(card, False, False, 0)

        # 2. Routing & Hotspot Sharing Card
        card_route = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_route.get_style_context().add_class("card")

        lbl_r_title = Gtk.Label(label="Internetni uzatish (Hotspot Gateway):")
        lbl_r_title.set_xalign(0)
        lbl_r_title.get_style_context().add_class("card-title")
        card_route.pack_start(lbl_r_title, False, False, 0)

        self.lbl_route_info = Gtk.Label()
        self.lbl_route_info.set_xalign(0)
        card_route.pack_start(self.lbl_route_info, False, False, 0)
        container.pack_start(card_route, False, False, 0)

        return container

    def refresh_ethernet_info(self):
        threading.Thread(target=self._fetch_ethernet_info, daemon=True).start()

    def _fetch_ethernet_info(self):
        ip_out, _ = run_cmd("ip -4 -o addr show dev eno1")
        ip_addr = ip_out.split()[3] if ip_out and len(ip_out.split()) >= 4 else "Aniqlanmadi"

        gw_out, _ = run_cmd("ip route | grep '^default.*eno1'")
        gw = gw_out.split()[2] if gw_out and len(gw_out.split()) >= 3 else "Standart"

        fwd_out, _ = run_cmd("cat /proc/sys/net/ipv4/ip_forward")
        is_forwarding = (fwd_out == "1")

        GLib.idle_add(self._render_ethernet_info, ip_addr, gw, is_forwarding)

    def _render_ethernet_info(self, ip_addr, gw, is_forwarding):
        self.lbl_eth_ip.set_markup(f"<b>Lokal IP:</b> <tt>{ip_addr}</tt>")
        self.lbl_eth_details.set_markup(
            f"<b>Shlyuz:</b> <tt>{gw}</tt>   •   <b>Internet:</b> <span color='#10b981'>Faol ✓</span>"
        )
        fwd_text = "<span color='#10b981'>Faol</span>" if is_forwarding else "<span color='#ef4444'>Oʻchiq</span>"
        self.lbl_route_info.set_markup(
            f"<b>Hotspot shlyuzi:</b> <tt>10.42.0.1</tt>   •   <b>Forwarding:</b> {fwd_text}"
        )

    # ── Global Status Polling ──────────────────────────────────────────
    def periodic_check(self):
        self.refresh_all_status()
        return True

    def refresh_all_status(self):
        threading.Thread(target=self._fetch_all_status, daemon=True).start()

    def _fetch_all_status(self):
        # 1. Hotspot
        hs_out, _ = run_cmd("nmcli -t -f NAME connection show --active | grep -Fx 'NiriHotspot'")
        hs_active = bool(hs_out)
        hs_count = 0
        if hs_active:
            c_out, _ = run_cmd("ip neigh show dev wlo1 | grep -v 'FAILED' | grep -c .")
            try:
                hs_count = int(c_out.strip())
            except Exception:
                pass

        # 2. Wi-Fi
        wifi_out, _ = run_cmd("nmcli radio wifi")
        wifi_enabled = (wifi_out.strip() == "enabled")

        # 3. Bluetooth
        bt_active = False
        bt_svc, _ = run_cmd("systemctl is-active bluetooth")
        if bt_svc.strip() == "active":
            bt_show, _ = run_cmd("timeout 0.5 bluetoothctl show")
            bt_active = ("Powered: yes" in bt_show)

        # 4. Ethernet
        eth_out, _ = run_cmd("ip -4 -o addr show dev eno1")
        eth_connected = bool(eth_out)

        GLib.idle_add(self._apply_all_status, hs_active, hs_count, wifi_enabled, bt_active, eth_connected)

    def _apply_all_status(self, hs_active, hs_count, wifi_enabled, bt_active, eth_connected):
        self.updating_ui = True

        # Hotspot
        self.switch_hotspot.set_active(hs_active)
        if hs_active:
            self.lbl_hotspot_status.set_text("Hotspot: FAOL")
            self.lbl_hotspot_desc.set_text(f"{hs_count} ta qurilma ulangan")
            self.lbl_hotspot_badge.set_text(f"YONIQ ({hs_count})")
            self.lbl_hotspot_badge.get_style_context().remove_class("tab-badge-off")
            self.lbl_hotspot_badge.get_style_context().add_class("tab-badge-on")
        else:
            self.lbl_hotspot_status.set_text("Hotspot: O'CHIQ")
            self.lbl_hotspot_desc.set_text("Tarmoq to'xtatilgan")
            self.lbl_hotspot_badge.set_text("O'CHIQ")
            self.lbl_hotspot_badge.get_style_context().remove_class("tab-badge-on")
            self.lbl_hotspot_badge.get_style_context().add_class("tab-badge-off")

        # Wi-Fi
        self.switch_wifi.set_active(wifi_enabled)
        if wifi_enabled:
            self.lbl_wifi_status.set_text("Wi-Fi: FAOL")
            self.lbl_wifi_desc.set_text("Tarmoqqa tayyor")
            self.lbl_wifi_badge.set_text("YONIQ")
            self.lbl_wifi_badge.get_style_context().remove_class("tab-badge-off")
            self.lbl_wifi_badge.get_style_context().add_class("tab-badge-on")
        else:
            self.lbl_wifi_status.set_text("Wi-Fi: O'CHIQ")
            self.lbl_wifi_desc.set_text("O'chirilgan")
            self.lbl_wifi_badge.set_text("O'CHIQ")
            self.lbl_wifi_badge.get_style_context().remove_class("tab-badge-on")
            self.lbl_wifi_badge.get_style_context().add_class("tab-badge-off")

        # Bluetooth
        self.switch_bt.set_active(bt_active)
        if bt_active:
            self.lbl_bt_status.set_text("Bluetooth: FAOL")
            self.lbl_bt_desc.set_text("Qurilmalarga tayyor")
            self.lbl_bt_badge.set_text("YONIQ")
            self.lbl_bt_badge.get_style_context().remove_class("tab-badge-off")
            self.lbl_bt_badge.get_style_context().add_class("tab-badge-on")
        else:
            self.lbl_bt_status.set_text("Bluetooth: O'CHIQ")
            self.lbl_bt_desc.set_text("O'chirilgan")
            self.lbl_bt_badge.set_text("O'CHIQ")
            self.lbl_bt_badge.get_style_context().remove_class("tab-badge-on")
            self.lbl_bt_badge.get_style_context().add_class("tab-badge-off")

        # Ethernet
        if eth_connected:
            self.lbl_eth_badge.set_text("eno1 ✓")
            self.lbl_eth_badge.get_style_context().remove_class("tab-badge-off")
            self.lbl_eth_badge.get_style_context().add_class("tab-badge-on")
            self.badge_eth_status.set_text("ULANGAN")
            self.badge_eth_status.get_style_context().remove_class("tab-badge-off")
            self.badge_eth_status.get_style_context().add_class("tab-badge-on")
        else:
            self.lbl_eth_badge.set_text("UZILGAN")
            self.lbl_eth_badge.get_style_context().remove_class("tab-badge-on")
            self.lbl_eth_badge.get_style_context().add_class("tab-badge-off")
            self.badge_eth_status.set_text("UZILGAN")
            self.badge_eth_status.get_style_context().remove_class("tab-badge-on")
            self.badge_eth_status.get_style_context().add_class("tab-badge-off")

        self.refresh_ethernet_info()
        self.updating_ui = False

def main():
    check_single_instance()
    win = ControlCenterWindow()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
