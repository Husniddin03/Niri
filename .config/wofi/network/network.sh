#!/usr/bin/env bash

# Wofi allaqachon ochiq bo'lsa, uni yopish (Toggle)
if pgrep -x wofi >/dev/null; then
    pkill -x wofi
    exit 0
fi

export NO_AT_BRIDGE=1
export GTK_A11Y=none

DIR="$HOME/.config/wofi/network"
CONF_FILE="$DIR/network.conf"
STYLE_FILE="$DIR/network.css"

# 1. Hotspot holatini aniqlash
if nmcli -t -f NAME connection show --active | grep -Fxq "NiriHotspot"; then
    COUNT=$(ip neigh show dev wlo1 2>/dev/null | grep -v "FAILED" | grep -c . || echo "0")
    HOTSPOT_TEXT="📡 Hotspot (Niri): [YONIQ] (${COUNT} ta ulangan) ➜ O'chirish"
    HOTSPOT_ACTION="hotspot_off"
else
    HOTSPOT_TEXT="📡 Hotspot (Niri): [O'CHIQ] ➜ Yoqish"
    HOTSPOT_ACTION="hotspot_on"
fi

# 2. Wi-Fi holatini aniqlash
WIFI_STATE=$(nmcli radio wifi 2>/dev/null)
if [ "$WIFI_STATE" = "enabled" ]; then
    WIFI_TEXT="📶 Wi-Fi: [YONIQ] ➜ O'chirish"
    WIFI_ACTION="wifi_off"
else
    WIFI_TEXT="📶 Wi-Fi: [O'CHIQ] ➜ Yoqish"
    WIFI_ACTION="wifi_on"
fi

# 3. Bluetooth holatini aniqlash
if systemctl is-active --quiet bluetooth 2>/dev/null; then
    if timeout 0.5 bluetoothctl show 2>/dev/null | grep -q "Powered: yes"; then
        BT_TEXT="🔵 Bluetooth: [YONIQ] ➜ O'chirish"
        BT_ACTION="bt_off"
    else
        BT_TEXT="🔵 Bluetooth: [O'CHIQ] ➜ Yoqish"
        BT_ACTION="bt_on"
    fi
else
    BT_TEXT="🔵 Bluetooth: [Xizmat o'chiq] ➜ Yoqish"
    BT_ACTION="bt_start"
fi

# 4. Qo'shimcha amallar
LIST_TEXT="📱 Ulangan qurilmalar ro'yxati (share-list)"
LIST_ACTION="share_list"

# Menyuni tuzish
MENU="${HOTSPOT_TEXT}\n${WIFI_TEXT}\n${BT_TEXT}\n${LIST_TEXT}"

# Wofi oynasini chiqarish
CHOSEN=$(printf "%b" "$MENU" | wofi --dmenu \
    --conf "$CONF_FILE" \
    --style "$STYLE_FILE" \
    --lines 4 \
    --prompt "Tarmoq sozlamalari")

[ -z "$CHOSEN" ] && exit 0

# Tanlangan amalni bajarish
case "$CHOSEN" in
    *"Hotspot"*"Yoqish"*)
        LIMIT=$(echo "" | wofi --dmenu \
            --conf "$CONF_FILE" \
            --style "$STYLE_FILE" \
            --lines 0 \
            --prompt "Nechta qurilma ulansin? (Enter: 10)")
        
        # Agar bekor qilinsa
        [ $? -ne 0 ] && exit 0
        LIMIT=${LIMIT:-10}
        
        /home/husniddin/.local/bin/share-on "$LIMIT"
        notify-send "📡 Hotspot (Niri)" "Hotspot yoqildi!\nSSID: Niri\nLimit: ${LIMIT} ta qurilma" -u normal
        ;;
    *"Hotspot"*"O'chirish"*)
        /home/husniddin/.local/bin/share-off
        notify-send "📡 Hotspot (Niri)" "Hotspot o'chirildi." -u normal
        ;;
    *"Wi-Fi"*"O'chirish"*)
        nmcli radio wifi off
        notify-send "📶 Wi-Fi" "Wi-Fi to'liq o'chirildi." -u normal
        ;;
    *"Wi-Fi"*"Yoqish"*)
        nmcli radio wifi on
        notify-send "📶 Wi-Fi" "Wi-Fi yoqildi." -u normal
        ;;
    *"Bluetooth"*"O'chirish"*)
        bluetoothctl power off 2>/dev/null
        notify-send "🔵 Bluetooth" "Bluetooth o'chirildi." -u normal
        ;;
    *"Bluetooth"*"Yoqish"*)
        bluetoothctl power on 2>/dev/null
        notify-send "🔵 Bluetooth" "Bluetooth yoqildi." -u normal
        ;;
    *"Bluetooth"*"Xizmat o'chiq"*)
        systemctl start bluetooth 2>/dev/null || pkexec systemctl start bluetooth
        bluetoothctl power on 2>/dev/null
        notify-send "🔵 Bluetooth" "Bluetooth xizmati ishga tushirildi." -u normal
        ;;
    *"Ulangan qurilmalar"*)
        OUTPUT=$(/home/husniddin/.local/bin/share-list)
        notify-send -t 6000 "📱 Hotspot qurilmalari" "$OUTPUT" -u normal
        ;;
esac
