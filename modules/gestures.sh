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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -d "$GESTURES_DIR" ]; then
    if [ -d "$SCRIPT_DIR/.config/niri-gestures" ]; then
        mkdir -p "$GESTURES_DIR"
        cp -r "$SCRIPT_DIR/.config/niri-gestures/"* "$GESTURES_DIR/"
    else
        echo -e "${YELLOW}⚠️ $GESTURES_DIR papkasi topilmadi, o'tkazib yuborilmoqda.${NC}"
        exit 0
    fi
fi

# Kameradan foydalanish uchun foydalanuvchini video guruhiga qo'shish
if [ -n "$USER" ] && command -v sudo >/dev/null 2>&1; then
    sudo usermod -aG video "$USER" 2>/dev/null || true
fi

# Python virtual muhit yaratish (--system-site-packages GTK/LayerShell kutubxonalari uchun shart)
if command -v python3 >/dev/null 2>&1; then
    if [ ! -d "$GESTURES_DIR/.venv" ]; then
        echo -e "${BLUE}Python virtual muhiti (.venv) tizim paketlari bilan yaratilmoqda...${NC}"
        python3 -m venv --system-site-packages "$GESTURES_DIR/.venv" 2>/dev/null || {
            echo -e "${YELLOW}python3-venv o'rnatilmagan bo'lishi mumkin.${NC}"
        }
    fi

    if [ -f "$GESTURES_DIR/.venv/bin/pip" ]; then
        echo -e "${BLUE}Kutubxonalar (opencv-python, mediapipe, numpy) tekshirilmoqda...${NC}"
        "$GESTURES_DIR/.venv/bin/pip" install --upgrade pip 2>/dev/null || true
        "$GESTURES_DIR/.venv/bin/pip" install opencv-python mediapipe numpy 2>/dev/null || {
            echo -e "${YELLOW}⚠️ Mediapipe/opencv o'rnatishda xatolik yuz berdi.${NC}"
        }
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

# Systemd User Service o'rnatish
mkdir -p "$HOME/.config/systemd/user"
if [ -f "$SCRIPT_DIR/.config/systemd/user/niri-gestures.service" ]; then
    cp -f "$SCRIPT_DIR/.config/systemd/user/niri-gestures.service" "$HOME/.config/systemd/user/"
    systemctl --user daemon-reload 2>/dev/null || true
    echo -e "${GREEN}✓ niri-gestures.service tizimga ulandi.${NC}"
fi

# Skriptlar va daemon uchun ijro huquqi
chmod +x "$GESTURES_DIR/daemon.py" 2>/dev/null || true
chmod +x "$GESTURES_DIR/bin/"* 2>/dev/null || true
chmod +x "$HOME/.local/bin/niri-gestures-toggle" 2>/dev/null || true

echo -e "${GREEN}✓ Gestures moduli muvaffaqiyatli yakunlandi.${NC}"
