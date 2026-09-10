#!/bin/bash
CSS_FILE="$HOME/.config/waybar/visibility.css"

if [ "$1" = "show" ]; then
    # Barni ko'rsatish va sichqoncha ishlaydigan qilish
    echo "window#waybar { opacity: 1; margin-top: 0; pointer-events: auto; }" > "$CSS_FILE"
else
    # Barni tepaga 100 pikselga yashirish va ko'rinmas qilish
    echo "window#waybar { opacity: 0; margin-top: -100px; pointer-events: none; }" > "$CSS_FILE"
fi

# Waybar-ga CSS o'zgarganini tezda bildirish (chiroyli va silliq qayta yuklanadi)
killall -SIGUSR2 waybar