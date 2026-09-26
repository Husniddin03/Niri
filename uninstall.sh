#!/usr/bin/env bash
# ==============================================================================
# Niri Desktop Environment Uninstaller & Rollback Tool
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "\n${BOLD}${RED}⚠️  Niri Desktop Environment o'chirilmoqda...${NC}"

read -p "Haqiqatan ham Niri konfiguratsiyalarini o'chirmoqchimisiz? (y/N): " -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Amal bekor qilindi.${NC}"
    exit 0
fi

# 1. Symlinklarni olib tashlash
CONFIGS=(niri waybar wofi foot dunst swaylock wlogout niri-gestures quick-ai)
echo -e "${YELLOW}🗑️  Symlinklar o'chirilmoqda...${NC}"
for c in "${CONFIGS[@]}"; do
    TARGET="$HOME/.config/$c"
    if [ -L "$TARGET" ]; then
        rm -f "$TARGET"
        echo -e "  ✓ ~/.config/$c havolasi olib tashlandi"
    fi
done

# 2. .local/bin dagi bog'langan skriptlarni tozalash
if [ -d "$SCRIPT_DIR/.local/bin" ]; then
    echo -e "${YELLOW}🗑️  ~/.local/bin dagi skriptlar tozalanmoqda...${NC}"
    for script in "$SCRIPT_DIR/.local/bin/"*; do
        name=$(basename "$script")
        target="$HOME/.local/bin/$name"
        if [ -L "$target" ] || [ -f "$target" ]; then
            rm -f "$target"
        fi
    done
fi

# 3. Zaxira nusxani (backup) qayta tiklash
LATEST_BACKUP=$(ls -td "$HOME/.config-backup"/* 2>/dev/null | head -n 1 || true)
if [ -n "$LATEST_BACKUP" ] && [ -d "$LATEST_BACKUP" ]; then
    echo -e "\n${BLUE}Oxirgi zaxira nusxa topildi: $LATEST_BACKUP${NC}"
    read -p "Ushbu zaxira nusxani qayta tiklaymizmi? (Y/n): " -r RESTORE
    if [[ ! "$RESTORE" =~ ^[Nn]$ ]]; then
        cp -r "$LATEST_BACKUP/"* "$HOME/.config/" 2>/dev/null || true
        echo -e "${GREEN}✓ Zaxira nusxa muvaffaqiyatli tiklandi!${NC}"
    fi
fi

echo -e "\n${BOLD}${GREEN}O'chirish yakunlandi. Tizim avvalgi holatiga qaytarildi.${NC}\n"
