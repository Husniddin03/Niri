#!/usr/bin/env bash
# ==============================================================================
# Niri Desktop Environment Doctor & Diagnostic Tool
# ==============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${BOLD}${CYAN}🔍 Niri Desktop Environment Diagnostikasi${NC}"
echo -e "${CYAN}────────────────────────────────────────────${NC}"

TOTAL_CHECKS=0
PASSED_CHECKS=0

check_cmd() {
    local cmd="$1"
    local desc="$2"
    local required="${3:-true}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if command -v "$cmd" >/dev/null 2>&1 || [ -f "$HOME/.local/bin/$cmd" ]; then
        echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "$cmd") ${GREEN}O'rnatilgan${NC} ($desc)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        if [ "$required" = "true" ]; then
            echo -e "  ${RED}✗${NC} $(printf '%-20s' "$cmd") ${RED}Topilmadi (Majburiy)${NC} ($desc)"
        else
            echo -e "  ${YELLOW}!${NC} $(printf '%-20s' "$cmd") ${YELLOW}Mavjud emas (Ixtiyoriy)${NC} ($desc)"
        fi
    fi
}

echo -e "\n${BOLD}1. Asosiy dasturlar (Core):${NC}"
check_cmd "niri" "Window Manager" "true"
check_cmd "waybar" "Status Bar" "true"
check_cmd "wofi" "App Launcher" "true"
check_cmd "foot" "Terminal" "true"
check_cmd "dunst" "Bildirishnomalar" "true"
check_cmd "swaylock" "Ekran qulfi" "true"
check_cmd "wlogout" "O'chirish menyusi" "false"

echo -e "\n${BOLD}2. Tizim utilitalari:${NC}"
check_cmd "swww" "Fon rasmi (daemon)" "false"
check_cmd "jq" "JSON tahlilchi" "true"
check_cmd "grim" "Skrinshot oluvchi" "true"
check_cmd "slurp" "Ekran maydonini tanlash" "true"
check_cmd "wl-copy" "Clipboard (wl-clipboard)" "true"
check_cmd "brightnessctl" "Yorug'lik boshqaruvi" "true"
check_cmd "playerctl" "Media boshqaruvi" "false"

echo -e "\n${BOLD}3. Python va GTK Layer Shell kutubxonalari (Smart Launcher, Wallpaper Picker):${NC}"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if python3 -c "import gi; gi.require_version('Gtk', '3.0'); gi.require_version('GtkLayerShell', '0.1'); from gi.repository import Gtk, GtkLayerShell; import cairo" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "GtkLayerShell/Cairo") ${GREEN}To'liq tayyor${NC} (Mod+D va Mod+W ishlaydi)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "  ${RED}✗${NC} $(printf '%-20s' "GtkLayerShell/Cairo") ${RED}Kutubxonalar yetishmaydi${NC} (gir1.2-gtklayershell-0.1, python3-cairo, python3-gi)"
fi

echo -e "\n${BOLD}4. Shriftlar (Nerd Fonts):${NC}"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if fc-list : family 2>/dev/null | grep -qi "JetBrainsMono Nerd Font"; then
    echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "JetBrainsMono NF") ${GREEN}O'rnatilgan${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "  ${RED}✗${NC} $(printf '%-20s' "JetBrainsMono NF") ${RED}O'rnatilmagan${NC} (Piktogrammalar chiqmasligi mumkin)"
fi

echo -e "\n${BOLD}5. Fon rasmlari (Wallpapers):${NC}"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
WP_COUNT=$(find "$HOME/Pictures/Wallpapers" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.webp" \) 2>/dev/null | wc -l)
if [ "$WP_COUNT" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "Wallpapers") ${GREEN}$WP_COUNT ta rasm mavjud${NC} (~/Pictures/Wallpapers)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "  ${YELLOW}!${NC} $(printf '%-20s' "Wallpapers") ${YELLOW}Rasm topilmadi${NC} (~/Pictures/Wallpapers bo'sh)"
fi

echo -e "\n${BOLD}6. Qo'l harakatlari boshqaruvi (Gestures - Mod+G):${NC}"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -f "$HOME/.config/niri-gestures/.venv/bin/python" ]; then
    if "$HOME/.config/niri-gestures/.venv/bin/python" -c "import cv2, mediapipe, numpy" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "Gestures venv") ${GREEN}Tayyor${NC} (cv2, mediapipe o'rnatilgan)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "  ${YELLOW}!${NC} $(printf '%-20s' "Gestures venv") ${YELLOW}Paketlar to'liq emas${NC} (pip install opencv-python mediapipe)"
    fi
else
    echo -e "  ${YELLOW}!${NC} $(printf '%-20s' "Gestures venv") ${YELLOW}O'rnatilmagan${NC} (Ixtiyoriy modul)"
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if ls /dev/video* >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "Kamera (/dev/video)") ${GREEN}Mavjud${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "  ${YELLOW}!${NC} $(printf '%-20s' "Kamera (/dev/video)") ${YELLOW}Topilmadi${NC}"
fi

echo -e "\n${BOLD}7. Muhit va Yo'llar (\$PATH):${NC}"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
    echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "~/.local/bin") ${GREEN}\$PATH ga qo'shilgan${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "  ${YELLOW}!${NC} $(printf '%-20s' "~/.local/bin") ${YELLOW}\$PATH da yo'q${NC} (~/.bashrc ga qo'shish tavsiya etiladi)"
fi

echo -e "\n${BOLD}8. Konfiguratsiya fayllari sintaksisi:${NC}"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if command -v niri >/dev/null 2>&1; then
    if niri validate >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "Niri config") ${GREEN}To'g'ri (Valid)${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "  ${RED}✗${NC} $(printf '%-20s' "Niri config") ${RED}Xatolik bor${NC} (niri validate buyrug'ini tekshiring)"
    fi
else
    echo -e "  ${YELLOW}!${NC} $(printf '%-20s' "Niri config") ${YELLOW}Tekshirib bo'lmadi${NC} (Niri topilmadi)"
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -f "$HOME/.config/waybar/config" ] && jq . "$HOME/.config/waybar/config" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "Waybar config") ${GREEN}To'g'ri (Valid JSON)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "  ${RED}✗${NC} $(printf '%-20s' "Waybar config") ${RED}JSON formatida xato${NC}"
fi

echo -e "\n${CYAN}────────────────────────────────────────────${NC}"
if [ "$PASSED_CHECKS" -eq "$TOTAL_CHECKS" ]; then
    echo -e "${BOLD}${GREEN}Natija: $PASSED_CHECKS / $TOTAL_CHECKS barcha komponentlar joyida! 🚀${NC}\n"
else
    echo -e "${BOLD}${YELLOW}Natija: $PASSED_CHECKS / $TOTAL_CHECKS komponentlar tayyor.${NC}\n"
fi
