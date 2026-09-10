#!/bin/bash

# Batareya nomini avtomatik aniqlash (BAT0 yoki BAT1)
BAT=$(ls /sys/class/power_supply/ | grep BAT | head -n 1)
STATE_FILE="/tmp/battery_level_state"

while true; do
    capacity=$(cat /sys/class/power_supply/$BAT/capacity)
    status=$(cat /sys/class/power_supply/$BAT/status)

    # State fayli bo'lmasa yaratish
    [ ! -f "$STATE_FILE" ] && echo "normal" > "$STATE_FILE"
    state=$(cat "$STATE_FILE")

    if [ "$status" != "Charging" ]; then
        # 10% - Oddiy signal
        if [ "$capacity" -le 10 ] && [ "$capacity" -gt 5 ] && [ "$state" != "level10" ]; then
            notify-send -u normal "🔋 Batareya past" "Quvvat: $capacity%"
            paplay /usr/share/sounds/freedesktop/stereo/message.oga 2>/dev/null
            echo "level10" > "$STATE_FILE"

        # 5% - Balandroq signal
        elif [ "$capacity" -le 5 ] && [ "$capacity" -gt 3 ] && [ "$state" != "level5" ]; then
            notify-send -u critical "🚨 Juda kam batareya!" "Quvvat: $capacity%"
            paplay /usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga 2>/dev/null
            echo "level5" > "$STATE_FILE"

        # 3% - Kritik (Har 60 soniyada signal beradi)
        elif [ "$capacity" -le 3 ]; then
            notify-send -u critical "💀 KRITIK HOLAT!" "Quvvat: $capacity% - HOZIR ZARYAD QIL!"
            paplay /usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga 2>/dev/null
            echo "level3" > "$STATE_FILE"
        fi
    else
        # Zaryad olayotgan bo'lsa holatni tiklash
        echo "normal" > "$STATE_FILE"
    fi

    # Har 60 soniyada tekshirish
    sleep 60
done
