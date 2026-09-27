#!/usr/bin/env bash
# ==============================================================================
# Niri Overview & Waybar Realtime Synchronization Daemon
# High performance, reactive event listener with zero flickering
# ==============================================================================

# Faqat bitta nusxada ishlashini ta'minlash (singleton)
exec 200>/tmp/niri-waybar-event-listener.lock
flock -n 200 || exit 0

show_waybar() {
    local layer
    layer=$(niri msg -j layers 2>/dev/null | jq -r '.[] | select(.namespace=="waybar") | .layer' | head -n 1)
    if [ "$layer" != "Top" ]; then
        killall -SIGUSR1 waybar 2>/dev/null
    fi
}

hide_waybar() {
    local layer
    layer=$(niri msg -j layers 2>/dev/null | jq -r '.[] | select(.namespace=="waybar") | .layer' | head -n 1)
    if [ "$layer" = "Top" ]; then
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

# 1. Waybar to'liq ishga tushib, surface yaratishini kutish (5 soniyagacha)
for i in {1..50}; do
    layer=$(niri msg -j layers 2>/dev/null | jq -r '.[] | select(.namespace=="waybar") | .layer' | head -n 1)
    [ -n "$layer" ] && break
    sleep 0.1
done

# 2. Boshlang'ich holatni to'g'rilash (boot paytida Waybar oynalar ustida qolib ketmasligi uchun)
sync_state

# 3. Event stream: Overview ochilganda/yopilganda darhol 0ms ichida reaksiya berish
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