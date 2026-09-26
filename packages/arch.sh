#!/usr/bin/env bash
# ==============================================================================
# Arch Linux Package Adapter for Niri Desktop
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}📦 Arch Linux tizimi uchun paketlar tekshirilmoqda...${NC}"

PACKAGES=(
    git
    curl
    wget
    jq
    which
    bc
    rsync
    base-devel
    gtk3
    gtk-layer-shell
    libxkbcommon
    niri
    waybar
    wofi
    foot
    dunst
    swaylock
    swww
    grim
    slurp
    wl-clipboard
    brightnessctl
    playerctl
    pavucontrol
    wireplumber
    pipewire
    fontconfig
)

AUR_PACKAGES=(
    wlogout
)

echo -e "${YELLOW}📥 Pacman orqali paketlar o'rnatilmoqda...${NC}"
sudo pacman -Sy --needed --noconfirm "${PACKAGES[@]}" || {
    echo -e "${YELLOW}⚠️ Ba'zi paketlar o'rnatilmadi.${NC}"
}

# AUR helper mavjud bo'lsa
if command -v yay >/dev/null 2>&1; then
    echo -e "${BLUE}yay orqali AUR paketlari o'rnatilmoqda...${NC}"
    yay -S --needed --noconfirm "${AUR_PACKAGES[@]}" 2>/dev/null || true
elif command -v paru >/dev/null 2>&1; then
    echo -e "${BLUE}paru orqali AUR paketlari o'rnatilmoqda...${NC}"
    paru -S --needed --noconfirm "${AUR_PACKAGES[@]}" 2>/dev/null || true
else
    echo -e "${YELLOW}💡 Maslahat: AUR helper (yay/paru) topilmadi. wlogout ni qo'lda o'rnatish kerak bo'lishi mumkin.${NC}"
fi

echo -e "${GREEN}✓ Arch Linux paketlar bosqichi yakunlandi.${NC}"
