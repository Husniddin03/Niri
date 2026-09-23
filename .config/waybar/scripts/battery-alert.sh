#!/usr/bin/env bash
# ==============================================================================
# Battery Smart Alert Daemon
# ==============================================================================

NOTIFIED_LOW=0
NOTIFIED_CRIT=0
NOTIFIED_FULL=0

while true; do
    BAT_PATH="/sys/class/power_supply/BAT0"

    if [ -d "$BAT_PATH" ]; then
        CAPACITY=$(cat "$BAT_PATH/capacity" 2>/dev/null || echo 100)
        STATUS=$(cat "$BAT_PATH/status" 2>/dev/null || echo "Unknown")

        if [ "$STATUS" = "Discharging" ]; then
            NOTIFIED_FULL=0

            # 10% Kritik daraja
            if [ "$CAPACITY" -le 10 ] && [ "$NOTIFIED_CRIT" -eq 0 ]; then
                notify-send -u critical -a "Batareya" -i battery-caution \
                    "⚠️ Kritik quvvat: ${CAPACITY}%" \
                    "Iltimos, zaryadlovchi qurilmani zudlik bilan ulang!"
                NOTIFIED_CRIT=1
                NOTIFIED_LOW=1
            # 20% Ogohlantirish darajasi
            elif [ "$CAPACITY" -le 20 ] && [ "$NOTIFIED_LOW" -eq 0 ]; then
                notify-send -u normal -a "Batareya" -i battery-low \
                    "🔋 Batareya kam: ${CAPACITY}%" \
                    "Zaryadlovchi qurilmani ulash tavsiya etiladi."
                NOTIFIED_LOW=1
            fi
        elif [ "$STATUS" = "Charging" ] || [ "$STATUS" = "Full" ]; then
            NOTIFIED_LOW=0
            NOTIFIED_CRIT=0

            # 99-100% To'liq zaryadlangan
            if [ "$CAPACITY" -ge 99 ] && [ "$NOTIFIED_FULL" -eq 0 ]; then
                notify-send -u low -a "Batareya" -i battery-full-charged \
                    "⚡ Batareya to'ldi: 100%" \
                    "Batareya umrini asrash uchun kabelni uzishingiz mumkin."
                NOTIFIED_FULL=1
            fi
        fi
    fi

    sleep 45
done
