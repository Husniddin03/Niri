#!/usr/bin/env bash

# Environment
export XDG_DATA_DIRS="/usr/share:/usr/local/share:$HOME/.local/share:$HOME/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:${XDG_DATA_DIRS}"

# Make sure overview daemon is running
if ! pgrep -f "swww-overview-daemon" > /dev/null; then
    "$HOME/.config/niri/scripts/overview-daemon-start.sh" &
    sleep 0.2
fi

exec python3 "$HOME/.config/wofi/wallpaper/live_selector.py" --mode overview
