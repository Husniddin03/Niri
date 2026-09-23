#!/usr/bin/env bash

# Environment
export NO_AT_BRIDGE=1
export GTK_A11Y=none
export XDG_DATA_DIRS="/usr/share:/usr/local/share:$HOME/.local/share:$HOME/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:${XDG_DATA_DIRS}"

# Make sure overview daemon is running
if ! pgrep -f "swww-overview-daemon" > /dev/null; then
    "$HOME/.config/niri/scripts/overview-daemon-start.sh" &
    sleep 0.2
fi

# Open overview so user directly sees the animated backdrop live preview!
if command -v niri >/dev/null 2>&1; then
    niri msg action open-overview >/dev/null 2>&1
fi

exec python3 "$HOME/.config/wofi/wallpaper/live_selector.py" --mode overview
