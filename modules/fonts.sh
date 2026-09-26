#!/usr/bin/env bash
# ==============================================================================
# Font Installer Module: JetBrainsMono Nerd Font & FontAwesome
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

FONT_DIR="$HOME/.local/share/fonts"
mkdir -p "$FONT_DIR"

echo -e "${BLUE}🔤 Shriftlar tekshirilmoqda...${NC}"

# JetBrainsMono Nerd Font tekshirish
if fc-list : family | grep -qi "JetBrainsMono Nerd Font"; then
    echo -e "${GREEN}✓ JetBrainsMono Nerd Font allaqachon o'rnatilgan.${NC}"
else
    echo -e "${YELLOW}📥 JetBrainsMono Nerd Font yuklab olinmoqda...${NC}"
    TEMP_DIR=$(mktemp -d)
    NERD_URL="https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.tar.xz"
    if curl -sSL "$NERD_URL" -o "$TEMP_DIR/jb.tar.xz" 2>/dev/null; then
        mkdir -p "$FONT_DIR/JetBrainsMono"
        tar -xf "$TEMP_DIR/jb.tar.xz" -C "$FONT_DIR/JetBrainsMono"
        rm -rf "$TEMP_DIR"
        echo -e "${GREEN}✓ JetBrainsMono o'rnatildi.${NC}"
    else
        rm -rf "$TEMP_DIR"
        echo -e "${YELLOW}⚠️ Nerd Font yuklab bo'lmadi.${NC}"
    fi
fi

# Font keshini yangilash
if command -v fc-cache >/dev/null 2>&1; then
    echo -e "${BLUE}🔄 Font keshi yangilanmoqda (fc-cache)...${NC}"
    fc-cache -f "$FONT_DIR" >/dev/null 2>&1 || true
fi

echo -e "${GREEN}✓ Shriftlar moduli yakunlandi.${NC}"
