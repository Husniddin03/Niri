#!/usr/bin/env bash
# ==============================================================================
# Niri Desktop Environment Safe Updater (niri-update)
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "\n${BOLD}${BLUE}🚀 Niri Desktop Environment yangilanmoqda...${NC}"

cd "$SCRIPT_DIR"

if [ ! -d ".git" ]; then
    echo -e "${RED}✗ Xato: $SCRIPT_DIR Git repozitoriysi emas!${NC}"
    exit 1
fi

# 1. Lokal o'zgarishlarni tekshirish
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️ Lokal o'zgarishlar topildi. Ular xavfsiz saqlanmoqda (git stash)...${NC}"
    git stash push -m "local-changes-$(date +%Y%m%d_%H%M%S)"
fi

# 2. Yangilanishlarni olish
echo -e "${BLUE}📥 GitHub dan eng so'nggi o'zgarishlar olinmoqda...${NC}"
git fetch origin main
if git pull origin main; then
    echo -e "${GREEN}✓ Yangi o'zgarishlar yuklandi.${NC}"
else
    echo -e "${RED}✗ Yangilanishda xatolik yuz berdi.${NC}"
    exit 1
fi

# 3. Yangi skriptlarga ruxsat berish
chmod +x "$SCRIPT_DIR/.local/bin/"* 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true
chmod +x "$SCRIPT_DIR/packages/"*.sh 2>/dev/null || true
chmod +x "$SCRIPT_DIR/modules/"*.sh 2>/dev/null || true

# 4. Sintaksisni tekshirish
echo -e "${BLUE}🔍 Konfiguratsiyalar tekshirilmoqda...${NC}"
if command -v niri >/dev/null 2>&1; then
    if ! niri validate >/dev/null 2>&1; then
        echo -e "${RED}✗ Diqqat: Yangilangan Niri konfiguratsiyasida xatolik bor!${NC}"
    fi
fi

# 5. Niri va Waybar'ni qayta yuklash
echo -e "${BLUE}🔄 Tizim qayta yuklanmoqda...${NC}"
if command -v niri >/dev/null 2>&1; then
    niri msg action load-config-file 2>/dev/null || true
fi

if command -v waybar-reload >/dev/null 2>&1; then
    waybar-reload 2>/dev/null || true
elif [ -f "$HOME/.local/bin/waybar-reload" ]; then
    "$HOME/.local/bin/waybar-reload" 2>/dev/null || true
fi

if command -v notify-send >/dev/null 2>&1; then
    notify-send -a "Niri System" "✨ Yangilanish yakunlandi" "Barcha konfiguratsiyalar muvaffaqiyatli yangilandi" -i system-software-update
fi

echo -e "${BOLD}${GREEN}✨ Niri Desktop muvaffaqiyatli yangilandi!${NC}\n"
