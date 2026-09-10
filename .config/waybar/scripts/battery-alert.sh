#!/bin/bash

THRESHOLD=20
NOTIFIED=0

while true; do
    BAT_PATH="/sys/class/power_supply/BAT0"

    if [ -d "$BAT_PATH" ]; then
        CAPACITY=$(cat $BAT_PATH/capacity)
        STATUS=$(cat $BAT_PATH/status)

        if [ "$CAPACITY" -le "$THRESHOLD" ] && [ "$STATUS" != "Charging" ] && [ "$NOTIFIED" -eq 0 ]; then
            notify-send "🔋 Batareya past!" "Batareya: ${CAPACITY}%"
            NOTIFIED=1
        fi

        # zaryadga ulangan bo‘lsa reset
        if [ "$STATUS" = "Charging" ]; then
            NOTIFIED=0
        fi
    fi

    sleep 60
done
