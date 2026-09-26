#!/usr/bin/env bash
# ==============================================================================
# Fedora Package Adapter for Niri Desktop
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}📦 Fedora tizimi uchun paketlar tekshirilmoqda...${NC}"

PACKAGES=(
    git
    curl
    wget
    jq
    bc
    rsync
    gcc
    gcc-c++
    pkgconf-pkg-config
    gtk3-devel
    gtk-layer-shell-devel
    libxkbcommon-devel
    mesa-dri-drivers
    mesa-vulkan-drivers
    xdg-desktop-portal
    xdg-desktop-portal-gtk
    waybar
    wofi
    foot
    dunst
    swaylock
    wlogout
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

# Niri COPR omborini yoqish
if ! sudo dnf info niri >/dev/null 2>&1; then
    echo -e "${BLUE}Niri COPR ombori yoqilmoqda (yalter/niri)...${NC}"
    sudo dnf copr enable -y yalter/niri 2>/dev/null || true
fi

echo -e "${YELLOW}📥 DNF orqali paketlar o'rnatilmoqda...${NC}"
sudo dnf install -y "${PACKAGES[@]}" niri 2>/dev/null || {
    echo -e "${YELLOW}⚠️ Ba'zi paketlar o'rnatilmadi.${NC}"
}

# GPU tekshirish
if lspci 2>/dev/null | grep -qi "nvidia"; then
    echo -e "\n${BOLD}${YELLOW}🎮 Nvidia GPU aniqlandi!${NC}"
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        echo -e "${YELLOW}Fedora uchun RPM Fusion orqali nvidia drayverini o'rnatish tavsiya etiladi.${NC}\n"
    fi
fi

echo -e "${GREEN}✓ Fedora paketlar bosqichi yakunlandi.${NC}"
