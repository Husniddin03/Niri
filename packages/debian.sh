#!/usr/bin/env bash
# ==============================================================================
# Debian / Ubuntu Package Adapter for Niri Desktop
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}📦 Debian / Ubuntu tizimi uchun paketlar tekshirilmoqda...${NC}"

# Sudo ruxsatini tekshirish
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
else
    SUDO=""
fi

# 1. Asosiy CLI va utilitalar
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
    echo -e "${GREEN}✓ Barcha asosiy paketlar allaqachon o'rnatilgan.${NC}"
fi

# 2. Niri mavjudligini tekshirish (Debian 12 da apt omborida yo'q)
if ! command -v niri >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Niri kompozitori tizimda topilmadi.${NC}"
    
    # apt da niri bormi tekshiramiz
    if apt-cache show niri >/dev/null 2>&1; then
        echo -e "${BLUE}Niri apt orqali o'rnatilmoqda...${NC}"
        $SUDO apt install -y niri
    else
        echo -e "${YELLOW}Debian/Ubuntu omborida Niri mavjud emas.${NC}"
        echo -e "${BLUE}GitHub Releases dan Niri binary fayli yuklab olinmoqda...${NC}"
        mkdir -p "$HOME/.local/bin"
        
        NIRI_RELEASE_URL="https://github.com/YaLTeR/niri/releases/latest/download/niri-linux-x86_64.tar.gz"
        TEMP_DIR=$(mktemp -d)
        if curl -sSL "$NIRI_RELEASE_URL" -o "$TEMP_DIR/niri.tar.gz"; then
            tar -xzf "$TEMP_DIR/niri.tar.gz" -C "$TEMP_DIR"
            # binaryni topib ~/.local/bin ga ko'chirish
            find "$TEMP_DIR" -type f -name "niri" -exec cp {} "$HOME/.local/bin/niri" \;
            chmod +x "$HOME/.local/bin/niri"
            rm -rf "$TEMP_DIR"
            echo -e "${GREEN}✓ Niri ~/.local/bin/niri ga muvaffaqiyatli o'rnatildi.${NC}"
        else
            rm -rf "$TEMP_DIR"
            echo -e "${RED}✗ Niri avtomatik yuklanmadi. Iltimos, Rust (cargo) orqali o'rnating:${NC}"
            echo -e "  cargo install --locked niri"
        fi
    fi
else
    echo -e "${GREEN}✓ Niri allaqachon o'rnatilgan: $(command -v niri)${NC}"
fi

# 3. SWWW (Fon rasmi xizmati - apt da bo'lmasa)
if ! command -v swww >/dev/null 2>&1 && [ ! -f "$HOME/.local/bin/swww" ]; then
    echo -e "${BLUE}SWWW wallpaper daemon yuklab olinmoqda...${NC}"
    mkdir -p "$HOME/.local/bin"
    SWWW_URL="https://github.com/LGFae/swww/releases/latest/download/swww-x86_64-unknown-linux-gnu.tar.gz"
    TEMP_DIR=$(mktemp -d)
    if curl -sSL "$SWWW_URL" -o "$TEMP_DIR/swww.tar.gz" 2>/dev/null; then
        tar -xzf "$TEMP_DIR/swww.tar.gz" -C "$TEMP_DIR"
        find "$TEMP_DIR" -type f -name "swww" -exec cp {} "$HOME/.local/bin/swww" \;
        find "$TEMP_DIR" -type f -name "swww-daemon" -exec cp {} "$HOME/.local/bin/swww-daemon" \;
        chmod +x "$HOME/.local/bin/swww" "$HOME/.local/bin/swww-daemon" 2>/dev/null || true
        rm -rf "$TEMP_DIR"
        echo -e "${GREEN}✓ SWWW ~/.local/bin ga o'rnatildi.${NC}"
    else
        rm -rf "$TEMP_DIR"
        echo -e "${YELLOW}⚠️ SWWW yuklab olinmadi.${NC}"
    fi
fi

echo -e "${GREEN}✓ Debian/Ubuntu paketlar bosqichi yakunlandi.${NC}"
