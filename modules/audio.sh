#!/usr/bin/env bash
# ==============================================================================
# Audio & System Control Module
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔊 Audio va yorug'lik boshqaruvi sozlanmoqda...${NC}"

# Brightnessctl uchun ruxsatlar (agar foydalanuvchi video guruhida bo'lmasa)
if command -v brightnessctl >/dev/null 2>&1; then
    if ! groups "$USER" | grep -q "\bvideo\b"; then
        echo -e "${YELLOW}💡 Foydalanuvchi 'video' guruhiga qo'shilmoqda (ekran yorug'ligi uchun)...${NC}"
        sudo usermod -aG video "$USER" 2>/dev/null || true
    fi
fi

# Pipewire / Wireplumber foydalanuvchi xizmatlarini faollashtirish
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user enable --now pipewire pipewire-pulse wireplumber 2>/dev/null || true
fi

echo -e "${GREEN}✓ Audio moduli yakunlandi.${NC}"
