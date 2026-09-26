#!/usr/bin/env bash
# ==============================================================================
# Arch Linux Package Adapter for Niri Desktop
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
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
    mesa
    vulkan-icd-loader
    xdg-desktop-portal
    xdg-desktop-portal-gtk
    seatd
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

# GPU tekshirish
if lspci 2>/dev/null | grep -qi "nvidia"; then
    echo -e "\n${BOLD}${YELLOW}🎮 Nvidia GPU aniqlandi!${NC}"
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        echo -e "${YELLOW}Arch Linux uchun nvidia drayverini o'rnatish: sudo pacman -S nvidia-dkms nvidia-utils${NC}\n"
    fi
fi

# AUR helper
if command -v yay >/dev/null 2>&1; then
    echo -e "${BLUE}yay orqali AUR paketlari o'rnatilmoqda...${NC}"
    yay -S --needed --noconfirm "${AUR_PACKAGES[@]}" 2>/dev/null || true
elif command -v paru >/dev/null 2>&1; then
    echo -e "${BLUE}paru orqali AUR paketlari o'rnatilmoqda...${NC}"
    paru -S --needed --noconfirm "${AUR_PACKAGES[@]}" 2>/dev/null || true
fi

echo -e "${GREEN}✓ Arch Linux paketlar bosqichi yakunlandi.${NC}"
