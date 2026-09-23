#!/usr/bin/env bash
# ==============================================================================
# Flameshot Screenshot Helper for Niri (Wayland)
# ==============================================================================

export XDG_CURRENT_DESKTOP=sway
export QT_QPA_PLATFORM=wayland

DIR="${HOME}/Pictures/Screenshots"
mkdir -p "$DIR"

FILENAME="Screenshot_$(date +'%Y-%m-%d_%H-%M-%S').png"
TARGET="${DIR}/${FILENAME}"

if flameshot gui --raw > "$TARGET" 2>/dev/null && [ -s "$TARGET" ]; then
    wl-copy --type image/png < "$TARGET"
    notify-send -a "Flameshot" -i "$TARGET" -t 3500 \
        "Skrinshot olindi ✓" \
        "Nusxalandi va saqlandi:\n${FILENAME}"
else
    # Agar bekor qilingan bo'lsa yoki bo'sh fayl yaratilgan bo'lsa, o'chiramiz
    rm -f "$TARGET"
fi
