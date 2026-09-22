#!/usr/bin/env python3
import subprocess
import json
import sys

# Ilovalar uchun qisqa va chiroyli nomlar hamda ikonkalari
APP_MAP = {
    "org.mozilla.firefox": ("󰈹", "Firefox"),
    "firefox": ("󰈹", "Firefox"),
    "google-chrome": ("", "Chrome"),
    "foot": ("󰆍", "Foot"),
    "alacritty": ("󰆍", "Alacritty"),
    "scratchpad-term": ("", "Scratchpad"),
    "org.telegram.desktop": ("", "Telegram"),
    "telegram-desktop": ("", "Telegram"),
    "code": ("󰨞", "Code"),
    "cursor": ("󰨞", "Cursor"),
    "nautilus": ("󰉋", "Fayllar"),
    "nemo": ("󰉋", "Fayllar"),
    "vlc": ("󰕼", "VLC"),
    "mpv": ("", "MPV"),
    "spotify": ("", "Spotify"),
    "obsidian": ("󱓧", "Obsidian"),
}

def format_app(app_id, title):
    if not app_id:
        app_id = ""
    app_id_clean = app_id.lower()
    for key, (icon, name) in APP_MAP.items():
        if key in app_id_clean:
            return icon, name
    # Default holat
    icon = "󰖯"
    name = (title or app_id or "Oyna").strip()
    if len(name) > 12:
        name = name[:10] + "…"
    return icon, name

def main():
    try:
        wins_raw = subprocess.check_output(["niri", "msg", "-j", "windows"], text=True)
        ws_raw = subprocess.check_output(["niri", "msg", "-j", "workspaces"], text=True)
        windows = json.loads(wins_raw)
        workspaces = json.loads(ws_raw)
    except Exception:
        print(json.dumps({"text": "", "tooltip": ""}))
        return

    curr_ws = next((w["id"] for w in workspaces if w.get("is_focused")), None)
    if curr_ws is None:
        print(json.dumps({"text": "", "tooltip": ""}))
        return

    # Faqat joriy ishchi stoldagi oynalar
    ws_windows = [w for w in windows if w.get("workspace_id") == curr_ws]
    if not ws_windows:
        print(json.dumps({"text": " 󰖯 [Bo'sh stol] ", "tooltip": "Bu ishchi stolda ochiq oynalar yo'q"}))
        return

    # Tiled (lenta) oynalarni ustun tartibi (column) bo'yicha saralash
    tiled_wins = [w for w in ws_windows if not w.get("is_floating", False)]
    floating_wins = [w for w in ws_windows if w.get("is_floating", False)]

    def get_col(w):
        return w.get("layout", {}).get("pos_in_scrolling_layout", [99, 1])[0]

    tiled_wins.sort(key=get_col)

    # Lenta elementlarini yig'ish
    ribbon_items = []
    has_offscreen = False

    for w in tiled_wins:
        app_id = w.get("app_id", "")
        title = w.get("title", "")
        is_focused = w.get("is_focused", False)
        view_pos = w.get("layout", {}).get("tile_pos_in_workspace_view")
        icon, name = format_app(app_id, title)

        # Agar oyna ekrandan chetda (offscreen) bo'lsa
        if view_pos is None:
            has_offscreen = True
            if is_focused:
                ribbon_items.append(f"<b>[{icon} {name}]*</b>")
            else:
                ribbon_items.append(f"<i>{icon} {name}</i>")
        else:
            # Ekranda ko'rinayotgan bo'lsa
            if is_focused:
                ribbon_items.append(f"<b><span color='#64D2FF'>[{icon} {name}]*</span></b>")
            else:
                ribbon_items.append(f"{icon} {name}")

    # Floating / Sticky oynalarni ham qo'shamiz
    for fw in floating_wins:
        f_app = fw.get("app_id", "")
        f_title = fw.get("title", "")
        f_focused = fw.get("is_focused", False)
        icon, name = format_app(f_app, f_title)
        if f_focused:
            ribbon_items.append(f"<b><span color='#FFD60A'>[📌 {name}]*</span></b>")
        else:
            ribbon_items.append(f"📌 {name}")

    # Agar lentada hech narsa bo'lmasa
    if not ribbon_items:
        display_text = "󰖯"
    else:
        display_text = " │ ".join(ribbon_items)

    # Tooltip tayyorlaymiz
    tooltip_lines = ["<b>Ishchi stoldagi oyna lentasi (Ribbon):</b>"]
    for idx, w in enumerate(tiled_wins, 1):
        view = "Ekranda" if w.get("layout", {}).get("tile_pos_in_workspace_view") is not None else "Chetda (Scroll qiling)"
        focus = " (Fokusda)" if w.get("is_focused") else ""
        tooltip_lines.append(f"{idx}. {w.get('app_id', '')}: {w.get('title', '')} [{view}]{focus}")

    for fw in floating_wins:
        focus = " (Fokusda)" if fw.get("is_focused") else ""
        tooltip_lines.append(f"📌 [Suzuvchi]: {fw.get('app_id', '')}: {fw.get('title', '')}{focus}")

    tooltip_lines.append("\n<i>Ustiga bossangiz: Overview ochiladi</i>")

    css_class = "has-offscreen" if has_offscreen else "normal"

    out = {
        "text": display_text,
        "tooltip": "\n".join(tooltip_lines),
        "class": css_class
    }
    print(json.dumps(out))

if __name__ == "__main__":
    main()
