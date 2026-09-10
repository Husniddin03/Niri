#!/usr/bin/env bash

export XDG_CURRENT_DESKTOP=sway
export QT_QPA_PLATFORM=wayland

TMP_FILE=$(mktemp /tmp/flameshot-XXXXXX.png)

if flameshot gui --raw > "$TMP_FILE" 2>/dev/null && [ -s "$TMP_FILE" ]; then
    wl-copy --type image/png < "$TMP_FILE"
    notify-send "Skrinshot olindi" "Rasm clipboard'ga nusxalandi" -i "$TMP_FILE" -t 2500
fi

rm -f "$TMP_FILE"
