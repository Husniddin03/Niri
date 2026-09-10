#!/usr/bin/env bash
# ==============================================================================
# Niri Desktop Environment Setup & Dotfiles Installer
# ==============================================================================

set -e

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Niri Dotfiles o'rnatilmoqda..."

# 1. Konfiguratsiya papkalarini yaratish
mkdir -p "$HOME/.config"
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/Pictures/Wallpapers"

# 2. .config papkalarini nusxalash / link qilish
echo "📦 Konfiguratsiyalar joylanmoqda..."
for dir in niri waybar dunst mako swaylock wlogout fuzzel foot niri-gestures quick-ai; do
    if [ -d "$DOTFILES_DIR/.config/$dir" ]; then
        mkdir -p "$HOME/.config/$dir"
        cp -r "$DOTFILES_DIR/.config/$dir/"* "$HOME/.config/$dir/" 2>/dev/null || true
        echo "  ✓ ~/.config/$dir yangilandi"
    fi
done

# Quick-AI konfiguratsiya shabloni
if [ ! -f "$HOME/.config/quick-ai/config.json" ] && [ -f "$DOTFILES_DIR/.config/quick-ai/config.example.json" ]; then
    cp "$DOTFILES_DIR/.config/quick-ai/config.example.json" "$HOME/.config/quick-ai/config.json"
    echo "  ⚠️  ~/.config/quick-ai/config.json yaratildi (API kalitingizni kiriting)"
fi

# 3. .local/bin skriptlarini nusxalash va ijro ruxsatini berish
echo "⚙️  Skriptlar ~/.local/bin ga nusxalanmoqda..."
cp "$DOTFILES_DIR/.local/bin/"* "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/"*
echo "  ✓ Barcha skriptlar o'rnatildi va ruxsatlar berildi"

# 4. Fon rasmlari
if [ -d "$DOTFILES_DIR/wallpapers" ]; then
    cp -r "$DOTFILES_DIR/wallpapers/"* "$HOME/Pictures/Wallpapers/" 2>/dev/null || true
    echo "  ✓ Fon rasmlari joylandi"
fi

# 5. Native dasturlarni kompilatsiya qilish (agar kerak bo'lsa)
if [ -d "$HOME/.config/niri-gestures/native" ]; then
    echo "🔨 Native modullarni tekshirish..."
    cd "$HOME/.config/niri-gestures/native"
    if [ -f "waypaste.c" ] && [ ! -f "$HOME/.local/bin/waypaste" ]; then
        gcc -O2 waypaste.c virtual-keyboard-unstable-v1-protocol.c $(pkg-config --cflags --libs wayland-client xkbcommon 2>/dev/null) -o "$HOME/.local/bin/waypaste" 2>/dev/null || true
    fi
fi

echo "✨ O'rnatish yakunlandi! Niri muhitini qayta yuklashingiz mumkin."
