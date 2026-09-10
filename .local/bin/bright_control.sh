#!/bin/bash
# Yorqinlikni o'zgartirish va bildirishnoma
brightnessctl set $1
current_bright=$(brightnessctl info | grep -Po '\d+(?=%)')
ID_FILE="/tmp/niri-osd-bri.id"
ID=$(cat "$ID_FILE" 2>/dev/null || echo 0)
NEW_ID=$(notify-send -r "$ID" -p -c osd -a "OSD" -h "int:value:$current_bright" -h string:synchronous:osd-bri "Yorqinlik" "Daraja: $current_bright%" -t 1200)
[ -n "$NEW_ID" ] && echo "$NEW_ID" > "$ID_FILE"

