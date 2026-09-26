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

echo -e "\n${BOLD}3. Shriftlar (Nerd Fonts):${NC}"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if fc-list : family 2>/dev/null | grep -qi "JetBrainsMono Nerd Font"; then
    echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "JetBrainsMono NF") ${GREEN}O'rnatilgan${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "  ${RED}✗${NC} $(printf '%-20s' "JetBrainsMono NF") ${RED}O'rnatilmagan${NC} (Piktogrammalar chiqmasligi mumkin)"
fi

echo -e "\n${BOLD}4. Muhit va Yo'llar (\$PATH):${NC}"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
    echo -e "  ${GREEN}✓${NC} $(printf '%-20s' "~/.local/bin") ${GREEN}\$PATH ga qo'shilgan${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "  ${YELLOW}!${NC} $(printf '%-20s' "~/.local/bin") ${YELLOW}\$PATH da yo'q${NC} (~/.bashrc yoki ~/.zshrc ga qo'shish tavsiya etiladi)"
fi

echo -e "\n${BOLD}5. Konfiguratsiya fayllari sintaksisi:${NC}"
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
