#!/usr/bin/env bash
# ==============================================================================
# Niri Volume Control & OSD Notification
# ==============================================================================

ACTION="$1"

case "$ACTION" in
    up)
        wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.05+ -l 1.0
        ;;
    down)
        wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.05-
        ;;
    mute)
        wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle
        ;;
    mic-mute)
        wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle
        ;;
esac

# Ovoz holatini olish
OUT=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null)
VOL_RAW=$(echo "$OUT" | awk '{print $2}')
VOL=$(python3 -c "print(int(float('${VOL_RAW:-0}') * 100))" 2>/dev/null || echo "0")

ID_FILE="/tmp/niri-osd-vol.id"
ID=$(cat "$ID_FILE" 2>/dev/null || echo 0)

if echo "$OUT" | grep -q "\[MUTED\]"; then
    ICON="notification-audio-volume-muted"
    NEW_ID=$(notify-send -r "$ID" -p -c osd -a "OSD" -h string:synchronous:osd-vol -t 1200 -i "$ICON" "Ovoz" "O'chirilgan (Muted)")
else
    if [ "$VOL" -eq 0 ]; then
        ICON="notification-audio-volume-low"
    elif [ "$VOL" -lt 50 ]; then
        ICON="notification-audio-volume-medium"
    else
        ICON="notification-audio-volume-high"
    fi
    NEW_ID=$(notify-send -r "$ID" -p -c osd -a "OSD" -h "int:value:$VOL" -h string:synchronous:osd-vol -t 1200 -i "$ICON" "Ovoz" "${VOL}%")
fi

[ -n "$NEW_ID" ] && echo "$NEW_ID" > "$ID_FILE"

