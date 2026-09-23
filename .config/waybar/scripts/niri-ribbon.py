#!/usr/bin/env python3
import subprocess
import json
import sys
import os

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
    icon = "󰖯"
    name = (title or app_id or "Oyna").strip()
    if len(name) > 12:
        name = name[:10] + "…"
    return icon, name

def render_ribbon(windows, workspaces):
    curr_ws = next((w["id"] for w in workspaces if w.get("is_focused")), None)
    if curr_ws is None:
        return {"text": "", "tooltip": ""}

    ws_windows = [w for w in windows if w.get("workspace_id") == curr_ws]
    if not ws_windows:
        return {"text": " 󰖯 [Bo'sh stol] ", "tooltip": "Bu ishchi stolda ochiq oynalar yo'q"}

    tiled_wins = [w for w in ws_windows if not w.get("is_floating", False)]
    floating_wins = [w for w in ws_windows if w.get("is_floating", False)]

    def get_col(w):
        return w.get("layout", {}).get("pos_in_scrolling_layout", [99, 1])[0]

    tiled_wins.sort(key=get_col)

    ribbon_items = []
    has_offscreen = False

    for w in tiled_wins:
        app_id = w.get("app_id", "")
        title = w.get("title", "")
        is_focused = w.get("is_focused", False)
        view_pos = w.get("layout", {}).get("tile_pos_in_workspace_view")
        icon, name = format_app(app_id, title)

        if view_pos is None:
            has_offscreen = True
            if is_focused:
                ribbon_items.append(f"<b>[{icon} {name}]*</b>")
            else:
                ribbon_items.append(f"<i>{icon} {name}</i>")
        else:
            if is_focused:
                ribbon_items.append(f"<b><span color='#38bdf8'>[{icon} {name}]*</span></b>")
            else:
                ribbon_items.append(f"{icon} {name}")

    for fw in floating_wins:
        f_app = fw.get("app_id", "")
        f_title = fw.get("title", "")
        f_focused = fw.get("is_focused", False)
        icon, name = format_app(f_app, f_title)
        if f_focused:
            ribbon_items.append(f"<b><span color='#f59e0b'>[📌 {name}]*</span></b>")
        else:
            ribbon_items.append(f"📌 {name}")

    display_text = " │ ".join(ribbon_items) if ribbon_items else "󰖯"

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

    return {
        "text": display_text,
        "tooltip": "\n".join(tooltip_lines),
        "class": css_class
    }

def main():
    # If one-shot requested:
    if len(sys.argv) > 1 and sys.argv[1] == "--oneshot":
        try:
            w_raw = subprocess.check_output(["niri", "msg", "-j", "windows"], text=True)
            ws_raw = subprocess.check_output(["niri", "msg", "-j", "workspaces"], text=True)
            print(json.dumps(render_ribbon(json.loads(w_raw), json.loads(ws_raw))))
        except Exception:
            print(json.dumps({"text": "", "tooltip": ""}))
        return

    # Continuous streaming event loop
    try:
        proc = subprocess.Popen(["niri", "msg", "-j", "event-stream"], stdout=subprocess.PIPE, text=True)
    except Exception:
        sys.exit(1)

    windows = []
    workspaces = []

    # Emit initial state immediately
    try:
        w_raw = subprocess.check_output(["niri", "msg", "-j", "windows"], text=True)
        ws_raw = subprocess.check_output(["niri", "msg", "-j", "workspaces"], text=True)
        windows = json.loads(w_raw)
        workspaces = json.loads(ws_raw)
        print(json.dumps(render_ribbon(windows, workspaces)), flush=True)
    except (BrokenPipeError, IOError):
        sys.exit(0)
    except Exception:
        pass

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue

        needs_render = False

        if "WorkspacesChanged" in event:
            workspaces = event["WorkspacesChanged"].get("workspaces", workspaces)
            needs_render = True
        elif "WindowsChanged" in event:
            windows = event["WindowsChanged"].get("windows", windows)
            needs_render = True
        elif "WindowOpenedOrChanged" in event:
            changed_win = event["WindowOpenedOrChanged"].get("window")
            if changed_win:
                w_id = changed_win.get("id")
                windows = [w for w in windows if w.get("id") != w_id]
                windows.append(changed_win)
                needs_render = True
        elif "WindowClosed" in event:
            closed_id = event["WindowClosed"].get("id")
            windows = [w for w in windows if w.get("id") != closed_id]
            needs_render = True
        elif "WorkspaceActivated" in event:
            act_id = event["WorkspaceActivated"].get("id")
            for ws in workspaces:
                ws["is_focused"] = (ws.get("id") == act_id)
            needs_render = True
        elif "WorkspaceActiveWindowChanged" in event:
            act_ws_id = event["WorkspaceActiveWindowChanged"].get("workspace_id")
            act_win_id = event["WorkspaceActiveWindowChanged"].get("active_window_id")
            for w in windows:
                w["is_focused"] = (w.get("id") == act_win_id)
            needs_render = True

        if needs_render:
            out = render_ribbon(windows, workspaces)
            try:
                print(json.dumps(out), flush=True)
            except (BrokenPipeError, IOError):
                sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        sys.exit(0)

