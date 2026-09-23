#!/usr/bin/env bash
# ==============================================================================
# Niri Overview & Waybar Auto-Visibility Event Listener
# High-efficiency event processor (zero subprocess forks during event loop)
# ==============================================================================

rm -f /tmp/waybar_should_be_hidden

# Wait briefly for Waybar to initialize
sleep 1

# Hide waybar initially
killall -SIGUSR1 waybar 2>/dev/null
touch /tmp/waybar_should_be_hidden

niri msg -j event-stream 2>/dev/null | while read -r line; do
    if [[ "$line" == *'"OverviewOpenedOrClosed":{"is_open":true}'* ]]; then
        # Show waybar when overview opens
        if [ -f /tmp/waybar_should_be_hidden ]; then
            killall -SIGUSR1 waybar 2>/dev/null
            rm -f /tmp/waybar_should_be_hidden
        fi
    elif [[ "$line" == *'"OverviewOpenedOrClosed":{"is_open":false}'* ]]; then
        # Hide waybar when overview closes
        if [ ! -f /tmp/waybar_should_be_hidden ]; then
            killall -SIGUSR1 waybar 2>/dev/null
            touch /tmp/waybar_should_be_hidden
        fi
    fi
done