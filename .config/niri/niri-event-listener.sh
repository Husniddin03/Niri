#!/usr/bin/env bash
# ==============================================================================
# Niri Overview & Waybar Realtime Synchronization & Self-Healing Daemon
# ==============================================================================

# Faqat bitta nusxada ishlashini ta'minlash (singleton)
exec 200>/tmp/niri-waybar-event-listener.lock
flock -n 200 || exit 0

echo 0 > /tmp/waybar_last_toggle

check_and_toggle() {
    local target_state="$1" # "open" yoki "closed"
    local now
    now=$(date +%s%3N)
    local last=0
    [ -f /tmp/waybar_last_toggle ] && last=$(cat /tmp/waybar_last_toggle 2>/dev/null || echo 0)

    # Debounce: oxirgi toggledan beri kamida 400ms o'tgan bo'lishi shart
    if [ $((now - last)) -lt 400 ]; then
        return
    fi

    local layer
    layer=$(niri msg -j layers 2>/dev/null | jq -r '.[] | select(.namespace=="waybar") | .layer' | head -n 1)
    [ -z "$layer" ] && return

    if [ "$target_state" = "open" ] && [ "$layer" != "Top" ]; then
        echo "$now" > /tmp/waybar_last_toggle
        killall -SIGUSR1 waybar 2>/dev/null
    elif [ "$target_state" = "closed" ] && [ "$layer" = "Top" ]; then
        echo "$now" > /tmp/waybar_last_toggle
        killall -SIGUSR1 waybar 2>/dev/null
    fi
}

sync_state() {
    local is_open
    is_open=$(niri msg -j overview-state 2>/dev/null | jq -r '.is_open')
    if [ "$is_open" = "true" ]; then
        check_and_toggle "open"
    elif [ "$is_open" = "false" ]; then
        check_and_toggle "closed"
    fi
}

# 1. Background watchdog: Waybar qayta yuklanganda (reload) yoki restarted bo'lganda
# avtomatik ravishda holatni to'g'irlaydi
(
    while true; do
        sleep 0.35
        sync_state
    done
) &
WATCHER_PID=$!

cleanup() {
    kill "$WATCHER_PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Boshlang'ich holatni tekshirish
sync_state

# 2. Event stream: Overview ochilganda/yopilganda darhol reaksiya berish (0ms kechikish)
while true; do
    niri msg -j event-stream 2>/dev/null | while read -r line; do
        if [[ "$line" == *'"OverviewOpenedOrClosed":{"is_open":true}'* ]]; then
            check_and_toggle "open"
        elif [[ "$line" == *'"OverviewOpenedOrClosed":{"is_open":false}'* ]]; then
            check_and_toggle "closed"
        fi
    done
    sleep 0.5
done