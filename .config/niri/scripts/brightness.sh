#!/usr/bin/env bash
# ==============================================================================
# Niri Brightness Control & OSD Notification
# ==============================================================================

ACTION="$1"

case "$ACTION" in
    up)
        brightnessctl --class=backlight set +5% >/dev/null
        ;;
    down)
        brightnessctl --class=backlight set 5%- >/dev/null
        ;;
esac

BRI=$(brightnessctl -m 2>/dev/null | cut -d, -f4 | tr -d '%')
[ -z "$BRI" ] && BRI="50"

ID_FILE="/tmp/niri-osd-bri.id"
ID=$(cat "$ID_FILE" 2>/dev/null || echo 0)

ICON="display-brightness"
NEW_ID=$(notify-send -r "$ID" -p -c osd -a "OSD" -h "int:value:$BRI" -h string:synchronous:osd-bri -t 1200 -i "$ICON" "Ekran yorug'ligi" "${BRI}%")
[ -n "$NEW_ID" ] && echo "$NEW_ID" > "$ID_FILE"

