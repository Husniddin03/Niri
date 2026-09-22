#!/usr/bin/env bash

# Environment
export XDG_DATA_DIRS="/usr/share:/usr/local/share:$HOME/.local/share:$HOME/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:${XDG_DATA_DIRS}"

# Make sure swww-daemon is running if wallpaper is active
if [ "$(cat "$HOME/.cache/current_wallpaper" 2>/dev/null)" != "transparent" ] && ! pgrep -x "swww-daemon" > /dev/null; then
    swww-daemon &
    sleep 0.2
fi

exec python3 "$HOME/.config/wofi/wallpaper/live_selector.py" --mode wallpaper
