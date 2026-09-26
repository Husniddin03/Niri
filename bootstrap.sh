#!/usr/bin/env bash
# ==============================================================================
# Niri Desktop Environment - Bootstrap One-Liner
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/Husniddin03/Niri.git"
TARGET_DIR="${NIRI_DOTFILES_DIR:-$HOME/.dotfiles-niri}"

echo -e "\n${BOLD}${BLUE}⚡ Niri Desktop Bootstrap boshlanmoqda...${NC}"

# 1. Git mavjudligini tekshirish
if ! command -v git >/dev/null 2>&1; then
    echo -e "${YELLOW}Git topilmadi. O'rnatilmoqda...${NC}"
    if [ -f /etc/debian_version ]; then
        sudo apt update && sudo apt install -y git
    elif [ -f /etc/arch-release ]; then
        sudo pacman -Sy --noconfirm git
    elif [ -f /etc/fedora-release ]; then
        sudo dnf install -y git
    else
        echo -e "${RED}✗ Iltimos, avval Git dasturini o'rnating.${NC}"
        exit 1
    fi
fi

# 2. Repozitoriyni klonlash yoki yangilash
if [ -d "$TARGET_DIR/.git" ]; then
    echo -e "${BLUE}Mavjud repozitoriy yangilanmoqda: $TARGET_DIR${NC}"
    cd "$TARGET_DIR"
    git pull origin main 2>/dev/null || true
else
    echo -e "${BLUE}Repozitoriy klonlanmoqda: $TARGET_DIR${NC}"
    git clone "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
fi

# 3. Ruxsatlarni berish va install.sh ni chaqirish
chmod +x install.sh doctor.sh update.sh uninstall.sh packages/*.sh modules/*.sh 2>/dev/null || true

echo -e "${GREEN}✓ Bootstrap tayyor! O'rnatuvchi ishga tushirilmoqda...${NC}\n"
exec ./install.sh "$@"
