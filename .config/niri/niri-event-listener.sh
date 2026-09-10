#!/bin/bash
# Vaqtinchalik faylni o'chirish
rm -f /tmp/waybar_should_be_hidden

# WAYBAR-GA OYLENI TIKLAB OLISHI UCHUN 1 SONIYA VAQT BERAMIZ
sleep 1

# Endi Waybar signalni qabul qila oladi, uni silliq yashiramiz
killall -SIGUSR1 waybar 2>/dev/null
touch /tmp/waybar_should_be_hidden

niri msg -j event-stream | while read -r line; do
    if echo "$line" | grep -q '"OverviewOpenedOrClosed":{"is_open":true}'; then
        # Overview ochilganda barni ko'rsatish
        if [ -f /tmp/waybar_should_be_hidden ]; then
            killall -SIGUSR1 waybar 2>/dev/null
            rm -f /tmp/waybar_should_be_hidden
        fi
    elif echo "$line" | grep -q '"OverviewOpenedOrClosed":{"is_open":false}'; then
        # Overview yopilganda barni yashirish
        if [ ! -f /tmp/waybar_should_be_hidden ]; then
            killall -SIGUSR1 waybar 2>/dev/null
            touch /tmp/waybar_should_be_hidden
        fi
    fi
done