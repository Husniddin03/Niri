#!/bin/bash
# Ovozni o'zgartirish va bildirishnoma chiqarish
pactl set-sink-volume @DEFAULT_SINK@ $1
# 100% dan oshib ketmasligini ta'minlash
current_vol=$(pactl get-sink-volume @DEFAULT_SINK@ | grep -Po '\d+(?=%)' | head -n 1)
if [ "$current_vol" -gt 100 ]; then
    pactl set-sink-volume @DEFAULT_SINK@ 100%
    current_vol=100
fi
ID_FILE="/tmp/niri-osd-vol.id"
ID=$(cat "$ID_FILE" 2>/dev/null || echo 0)
NEW_ID=$(notify-send -r "$ID" -p -c osd -a "OSD" -h "int:value:$current_vol" -h string:synchronous:osd-vol "Audio" "Daraja: $current_vol%" -t 1200)
[ -n "$NEW_ID" ] && echo "$NEW_ID" > "$ID_FILE"

