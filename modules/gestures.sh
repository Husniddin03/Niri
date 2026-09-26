#!/usr/bin/env bash
# ==============================================================================
# OpenCV Hand Gestures Module
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🖐️  OpenCV Hand Gestures moduli sozlanmoqda...${NC}"

GESTURES_DIR="$HOME/.config/niri-gestures"

if [ ! -d "$GESTURES_DIR" ]; then
    echo -e "${YELLOW}⚠️ $GESTURES_DIR papkasi topilmadi, o'tkazib yuborilmoqda.${NC}"
    exit 0
fi

# Python virtual muhit yaratish
if command -v python3 >/dev/null 2>&1; then
    if [ ! -d "$GESTURES_DIR/.venv" ]; then
        echo -e "${BLUE}Python virtual muhiti (.venv) yaratilmoqda...${NC}"
        python3 -m venv "$GESTURES_DIR/.venv" 2>/dev/null || {
            echo -e "${YELLOW}python3-venv o'rnatilmagan bo'lishi mumkin. O'rnatish: sudo apt install python3-venv${NC}"
        }
    fi

    if [ -f "$GESTURES_DIR/.venv/bin/pip" ]; then
        echo -e "${BLUE}Kutubxonalar (opencv-python, mediapipe) o'rnatilmoqda...${NC}"
        "$GESTURES_DIR/.venv/bin/pip" install --upgrade pip 2>/dev/null || true
        "$GESTURES_DIR/.venv/bin/pip" install opencv-python mediapipe numpy 2>/dev/null || true
    fi
fi

# Native C dasturlarni kompilatsiya qilish
if [ -d "$GESTURES_DIR/native" ]; then
    echo -e "${BLUE}Native modullarni kompilatsiya qilish...${NC}"
    mkdir -p "$HOME/.local/bin"
    if [ -f "$GESTURES_DIR/native/waymouse.c" ] && command -v gcc >/dev/null 2>&1; then
        gcc -O2 "$GESTURES_DIR/native/waymouse.c" $(pkg-config --cflags --libs wayland-client 2>/dev/null) -o "$HOME/.local/bin/waymouse" 2>/dev/null || true
    fi
fi

echo -e "${GREEN}✓ Gestures moduli yakunlandi.${NC}"
