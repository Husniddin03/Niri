#!/usr/bin/env bash
# ==============================================================================
# Debian / Ubuntu Package Adapter for Niri Desktop
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}📦 Debian / Ubuntu tizimi uchun paketlar tekshirilmoqda...${NC}"

# Sudo ruxsatini tekshirish
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
else
    SUDO=""
fi

# 1. Asosiy CLI, grafik drayver va Wayland utilitalari
PACKAGES=(
    git
    curl
    wget
    jq
    whiptail
    bc
    rsync
    build-essential
    pkg-config
    libgtk-3-dev
    libgtk-layer-shell-dev
    libxkbcommon-dev
    mesa-vulkan-drivers
    libgl1-mesa-dri
    libgbm1
    xdg-desktop-portal
    xdg-desktop-portal-gtk
    seatd
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

echo -e "${YELLOW}🔄 Repozitoriyalar yangilanmoqda (apt update)...${NC}"
$SUDO apt update -y

echo -e "${YELLOW}📥 Kerakli paketlar o'rnatilmoqda...${NC}"
MISSING_PKGS=()
for pkg in "${PACKAGES[@]}"; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        MISSING_PKGS+=("$pkg")
    fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo -e "${BLUE}O'rnatiladigan paketlar: ${MISSING_PKGS[*]}${NC}"
    $SUDO apt install -y "${MISSING_PKGS[@]}" || {
        echo -e "${YELLOW}⚠️ Ba'zi paketlar o'rnatilmadi, qolganlari davom ettiriladi.${NC}"
    }
else
    echo -e "${GREEN}✓ Barcha asosiy paketlar va drayverlar allaqachon o'rnatilgan.${NC}"
fi

# 2. GPU Drayverlarini tekshirish (Nvidia / Intel / AMD)
if lspci 2>/dev/null | grep -qi "nvidia"; then
    echo -e "\n${BOLD}${YELLOW}🎮 Nvidia GPU aniqlandi!${NC}"
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        echo -e "${YELLOW}💡 Eslatma: Tizimda xususiy Nvidia drayveri topilmadi.${NC}"
        echo -e "${YELLOW}Niri Wayland'da eng yuqori FPS va silliq ishlashi uchun drayverni o'rnatish tavsiya etiladi:${NC}"
        echo -e "  sudo apt install -y nvidia-driver\n"
    else
        echo -e "${GREEN}✓ Nvidia drayverlari faol.${NC}"
    fi
fi

# 3. Niri mavjudligini tekshirish
if ! command -v niri >/dev/null 2>&1 && [ ! -f "$HOME/.local/bin/niri" ]; then
    echo -e "${YELLOW}⚠️ Niri kompozitori tizimda topilmadi.${NC}"
    
    if apt-cache show niri >/dev/null 2>&1; then
        echo -e "${BLUE}Niri apt orqali o'rnatilmoqda...${NC}"
        $SUDO apt install -y niri
    else
        echo -e "${YELLOW}Debian/Ubuntu rasmiy omborida Niri mavjud emas.${NC}"
        echo -e "${BLUE}Rust (Cargo) orqali Niri yig'ilishi tekshirilmoqda...${NC}"
        if command -v cargo >/dev/null 2>&1; then
            echo -e "${BLUE}Cargo orqali niri o'rnatilmoqda (cargo install --locked niri)...${NC}"
            cargo install --locked niri 2>/dev/null || true
        else
            echo -e "${YELLOW}💡 Niri o'rnatish uchun Rust toolchain (rustup) o'rnatish tavsiya etiladi:${NC}"
            echo -e "  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            echo -e "  cargo install --locked niri"
        fi
    fi
else
    echo -e "${GREEN}✓ Niri allaqachon o'rnatilgan: $(command -v niri || echo "$HOME/.local/bin/niri")${NC}"
fi

# 4. Display Manager uchun Wayland sessiyasi (GDM / SDDM / LightDM)
if [ ! -f "/usr/share/wayland-sessions/niri.desktop" ] && [ ! -f "$HOME/.local/share/wayland-sessions/niri.desktop" ]; then
    echo -e "${BLUE}🖥️  Login ekrani uchun Niri sessiyasi yaratilmoqda...${NC}"
    SESSION_CONTENT="[Desktop Entry]
Name=Niri
Comment=Scrollable-tiling Wayland compositor
Exec=niri-session
Type=Application
DesktopNames=niri"
    if [ -w "/usr/share/wayland-sessions" ] || [ -n "$SUDO" ]; then
        echo "$SESSION_CONTENT" | $SUDO tee /usr/share/wayland-sessions/niri.desktop >/dev/null 2>&1 || true
    fi
    mkdir -p "$HOME/.local/share/wayland-sessions"
    echo "$SESSION_CONTENT" > "$HOME/.local/share/wayland-sessions/niri.desktop"
    echo -e "${GREEN}✓ Niri sessiyasi ro'yxatga olindi.${NC}"
fi

# 5. niri-session skripti
if ! command -v niri-session >/dev/null 2>&1 && [ ! -f "$HOME/.local/bin/niri-session" ]; then
    cat > "$HOME/.local/bin/niri-session" << 'EOF'
#!/bin/sh
if hash dbus-update-activation-environment 2>/dev/null; then
    dbus-update-activation-environment --all
fi
exec niri --session
EOF
    chmod +x "$HOME/.local/bin/niri-session"
fi

# 6. SWWW (Fon rasmi xizmati)
if ! command -v swww >/dev/null 2>&1 && [ ! -f "$HOME/.local/bin/swww" ]; then
    echo -e "${BLUE}SWWW wallpaper daemon yuklab olinmoqda...${NC}"
    mkdir -p "$HOME/.local/bin"
    SWWW_URL="https://github.com/LGFae/swww/releases/latest/download/swww-x86_64-unknown-linux-gnu.tar.gz"
    TEMP_DIR=$(mktemp -d)
    if curl -sSL "$SWWW_URL" -o "$TEMP_DIR/swww.tar.gz" 2>/dev/null; then
        tar -xzf "$TEMP_DIR/swww.tar.gz" -C "$TEMP_DIR" 2>/dev/null || true
        find "$TEMP_DIR" -type f -name "swww" -exec cp {} "$HOME/.local/bin/swww" \; 2>/dev/null || true
        find "$TEMP_DIR" -type f -name "swww-daemon" -exec cp {} "$HOME/.local/bin/swww-daemon" \; 2>/dev/null || true
        chmod +x "$HOME/.local/bin/swww" "$HOME/.local/bin/swww-daemon" 2>/dev/null || true
        rm -rf "$TEMP_DIR"
        echo -e "${GREEN}✓ SWWW o'rnatildi.${NC}"
    else
        rm -rf "$TEMP_DIR"
        echo -e "${YELLOW}⚠️ SWWW yuklab olinmadi.${NC}"
    fi
fi

echo -e "${GREEN}✓ Debian/Ubuntu paketlar bosqichi yakunlandi.${NC}"
