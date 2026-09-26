#!/usr/bin/env bash
# ==============================================================================
# Niri Overview & Waybar Realtime Synchronization Daemon
# High performance, reactive event listener with zero flickering
# ==============================================================================

# Faqat bitta nusxada ishlashini ta'minlash (singleton)
exec 200>/tmp/niri-waybar-event-listener.lock
flock -n 200 || exit 0

STATE_FILE="/tmp/waybar_state"

show_waybar() {
    local cur
    cur=$(cat "$STATE_FILE" 2>/dev/null || echo "hidden")
    if [ "$cur" != "shown" ]; then
        echo "shown" > "$STATE_FILE"
        killall -SIGUSR1 waybar 2>/dev/null
    fi
}

hide_waybar() {
    local cur
    cur=$(cat "$STATE_FILE" 2>/dev/null || echo "hidden")
    if [ "$cur" != "hidden" ]; then
        echo "hidden" > "$STATE_FILE"
        killall -SIGUSR1 waybar 2>/dev/null
    fi
}

sync_state() {
    local is_open
    is_open=$(niri msg -j overview-state 2>/dev/null | jq -r '.is_open')
    if [ "$is_open" = "true" ]; then
        show_waybar
    else
        hide_waybar
    fi
}

# Waybar ishga tushishini kutish va boshlang'ich holatni o'rnatish
sleep 0.5
# Waybar mode: hide bilan boshlangani sababli boshlang'ich holat: hidden
echo "hidden" > "$STATE_FILE"
sync_state

# Event stream: Overview ochilganda/yopilganda darhol 0ms ichida reaksiya berish
while true; do
    niri msg -j event-stream 2>/dev/null | while read -r line; do
        if [[ "$line" == *'"OverviewOpenedOrClosed":{"is_open":true}'* ]]; then
            show_waybar
        elif [[ "$line" == *'"OverviewOpenedOrClosed":{"is_open":false}'* ]]; then
            hide_waybar
        fi
    done
    sleep 1
done