#!/usr/bin/env bash
# Start animated swww overview daemon permanently
ln -sf /run/user/1000/${WAYLAND_DISPLAY:-wayland-1} /run/user/1000/wayland-overview
rm -f /run/user/1000/swww-wayland-overview.socket

if ! pgrep -f "swww-overview-daemon" > /dev/null; then
    setsid -f env WAYLAND_DISPLAY=wayland-overview /home/husniddin/.local/bin/swww-overview-daemon > /tmp/swww-overview.log 2>&1
    sleep 0.5
fi

OVERVIEW_WP=$(cat "$HOME/.cache/current_overview_backdrop" 2>/dev/null || echo "$HOME/Pictures/Wallpapers/obmqa6r-imgur.jpg")
if [ -f "$OVERVIEW_WP" ]; then
    WAYLAND_DISPLAY=wayland-overview swww img "$OVERVIEW_WP" --transition-type none
fi
