#!/usr/bin/env bash
# Start animated swww overview daemon permanently
USER_ID=$(id -u)
ln -sf "/run/user/$USER_ID/${WAYLAND_DISPLAY:-wayland-1}" "/run/user/$USER_ID/wayland-overview"

if ! pgrep -f "swww-overview-daemon" > /dev/null; then
    rm -f "/run/user/$USER_ID/swww-wayland-overview.socket"
    setsid -f env WAYLAND_DISPLAY=wayland-overview $HOME/.local/bin/swww-overview-daemon > /tmp/swww-overview.log 2>&1
    sleep 0.4
fi

OVERVIEW_WP=$(cat "$HOME/.cache/current_overview_backdrop" 2>/dev/null || echo "$HOME/Pictures/Wallpapers/obmqa6r-imgur.jpg")
if [ -f "$OVERVIEW_WP" ]; then
    WAYLAND_DISPLAY=wayland-overview swww img "$OVERVIEW_WP" --transition-type none
fi
