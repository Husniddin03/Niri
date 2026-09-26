#!/usr/bin/env bash
# ==============================================================================
# Wallpapers Module
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

TARGET_DIR="$HOME/Pictures/Wallpapers"
mkdir -p "$TARGET_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}🖼️  Fon rasmlari sozlanmoqda...${NC}"

if [ -d "$SCRIPT_DIR/wallpapers" ]; then
    cp -r "$SCRIPT_DIR/wallpapers/"* "$TARGET_DIR/" 2>/dev/null || true
    echo -e "${GREEN}✓ Fon rasmlari $TARGET_DIR ga joylandi.${NC}"
fi

# Thumbnail va ikonka assetlarini keshga joylash
CACHE_WP="$HOME/.cache/wallpaper-selector"
mkdir -p "$CACHE_WP"
if [ -d "$SCRIPT_DIR/.config/wofi/wallpaper/assets" ]; then
    cp -r "$SCRIPT_DIR/.config/wofi/wallpaper/assets/"* "$CACHE_WP/" 2>/dev/null || true
fi

# Birinchi rasmni default sifatida keshga yozib qo'yish
FIRST_WALL=$(find "$TARGET_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.webp" \) 2>/dev/null | head -n 1 || true)
if [ -n "$FIRST_WALL" ]; then
    mkdir -p "$HOME/.cache"
    echo "$FIRST_WALL" > "$HOME/.cache/current_wallpaper"
    echo "$FIRST_WALL" > "$HOME/.cache/current_overview_backdrop"
fi

echo -e "${GREEN}✓ Fon rasmlari moduli yakunlandi.${NC}"
