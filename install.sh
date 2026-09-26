#!/usr/bin/env bash
# ==============================================================================
# Niri Desktop Environment - Universal Master Installer
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Flags va Argumentlarni tekshirish ─────────────────────────────────────────
case "$1" in
    --doctor)
        bash "$DOTFILES_DIR/doctor.sh"
        exit 0
        ;;
    --update)
        bash "$DOTFILES_DIR/update.sh"
        exit 0
        ;;
    --uninstall)
        bash "$DOTFILES_DIR/uninstall.sh"
        exit 0
        ;;
    --dry-run)
        DRY_RUN=true
        ;;
    *)
        DRY_RUN=false
        ;;
esac

echo -e "\n${BOLD}${CYAN}🚀 Niri Desktop Environment O'rnatuvchisi${NC}"
echo -e "${CYAN}────────────────────────────────────────────────${NC}"

if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}⚠️  DRY-RUN REJIMI: Tizimga hech qanday o'zgartirish kiritilmaydi.${NC}\n"
fi

# 1. Distro (OS) aniqlash
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_LIKE=${ID_LIKE:-$ID}
    else
        DISTRO="unknown"
    fi
}

detect_distro
echo -e "${BLUE}Tizim aniqlandi:${NC} ${BOLD}$DISTRO${NC} (Baza: $DISTRO_LIKE)"

# 2. Interaktiv Modul Tanlovi (TUI Checkbox)
CHOSEN_MODULES=""

if command -v whiptail >/dev/null 2>&1 && [ -t 0 ] && [ "$DRY_RUN" = "false" ]; then
    # Whiptail orqali chiroyli TUI menyu
    CHOICES=$(whiptail --title "Niri Desktop O'rnatuvchi" --checklist \
        "O'rnatmoqchi bo'lgan komponentlaringizni tanlang:\n(Space - belgilash, Enter - tasdiqlash)" 18 70 6 \
        "CORE" "Asosiy Desktop (Niri, Waybar, Wofi, Foot)" ON \
        "FONTS" "Shriftlar (JetBrainsMono Nerd Font)" ON \
        "AUDIO" "Audio & Yorug'lik boshqaruvi" ON \
        "WALLPAPERS" "Fon rasmlari to'plami" ON \
        "GESTURES" "OpenCV Kamera orqali boshqaruv" OFF \
        "QUICK_AI" "Quick AI Yordamchi darchasi" OFF \
        3>&1 1>&2 2>&3) || {
            echo -e "${YELLOW}O'rnatish foydalanuvchi tomonidan bekor qilindi.${NC}"
            exit 0
        }
    CHOSEN_MODULES="$CHOICES"
else
    # Fallback oddiy CLI menyu
    echo -e "\n${BOLD}O'rnatish rejimi tanlandi:${NC}"
    echo -e "  [X] CORE (Niri, Waybar, Wofi, Foot)"
    echo -e "  [X] FONTS (JetBrainsMono Nerd Font)"
    echo -e "  [X] AUDIO (Audio & Yorug'lik)"
    echo -e "  [X] WALLPAPERS (Fon rasmlari)"
    echo -e "  [ ] GESTURES (OpenCV Gestures)"
    echo -e "  [ ] QUICK_AI (Quick AI)"
    CHOSEN_MODULES='"CORE" "FONTS" "AUDIO" "WALLPAPERS"'
fi

# 3. Paketlarni o'rnatish
install_system_packages() {
    echo -e "\n${BOLD}${BLUE}📦 Tizim paketlarini o'rnatish...${NC}"
    if [ "$DRY_RUN" = "true" ]; then
        echo "  [Dry-run] $DISTRO uchun packages/$DISTRO.sh ishga tushirilgan bo'lardi."
        return
    fi

    if [[ "$DISTRO" =~ (debian|ubuntu|linuxmint|pop) ]] || [[ "$DISTRO_LIKE" =~ (debian|ubuntu) ]]; then
        bash "$DOTFILES_DIR/packages/debian.sh"
    elif [[ "$DISTRO" =~ (arch|manjaro|endeavouros) ]] || [[ "$DISTRO_LIKE" =~ arch ]]; then
        bash "$DOTFILES_DIR/packages/arch.sh"
    elif [[ "$DISTRO" =~ (fedora|rhel|centos) ]] || [[ "$DISTRO_LIKE" =~ fedora ]]; then
        bash "$DOTFILES_DIR/packages/fedora.sh"
    else
        echo -e "${YELLOW}⚠️ Noma'lum distributiv ($DISTRO). Paketlarni qo'lda o'rnatish talab qilinishi mumkin.${NC}"
    fi
}

install_system_packages

# 4. Zaxiralash va Symlink o'rnatish
setup_configs() {
    echo -e "\n${BOLD}${BLUE}🔗 Konfiguratsiyalarni bog'lash (Symlink)...${NC}"
    BACKUP_DIR="$HOME/.config-backup/$(date +%Y-%m-%d_%H%M%S)"

    CONFIGS=(niri waybar wofi foot dunst swaylock wlogout)
    
    if [[ "$CHOSEN_MODULES" == *"GESTURES"* ]]; then
        CONFIGS+=(niri-gestures)
    fi
    if [[ "$CHOSEN_MODULES" == *"QUICK_AI"* ]]; then
        CONFIGS+=(quick-ai)
    fi

    for c in "${CONFIGS[@]}"; do
        SRC="$DOTFILES_DIR/.config/$c"
        DEST="$HOME/.config/$c"

        [ ! -d "$SRC" ] && continue

        if [ "$DRY_RUN" = "true" ]; then
            echo "  [Dry-run] $DEST -> $SRC ga bog'langan bo'lardi"
            continue
        fi

        # Agar mavjud bo'lsa va symlink bo'lmasa -> backup qilamiz
        if [ -e "$DEST" ] && [ ! -L "$DEST" ]; then
            mkdir -p "$BACKUP_DIR"
            echo -e "${YELLOW}  📦 Mavjud ~/.config/$c zaxiralanmoqda: $BACKUP_DIR/$c${NC}"
            mv "$DEST" "$BACKUP_DIR/$c"
        elif [ -L "$DEST" ]; then
            rm -f "$DEST"
        fi

        mkdir -p "$HOME/.config"
        ln -s "$SRC" "$DEST"
        echo -e "  ${GREEN}✓${NC} ~/.config/$c -> $SRC"
    done
}

setup_configs

# 5. Skriptlarni ~/.local/bin ga bog'lash
setup_binaries() {
    echo -e "\n${BOLD}${BLUE}⚙️  Skriptlarni ~/.local/bin ga sozlash...${NC}"
    mkdir -p "$HOME/.local/bin"

    if [ "$DRY_RUN" = "true" ]; then
        echo "  [Dry-run] $DOTFILES_DIR/.local/bin/* skriptlari ~/.local/bin ga bog'langan bo'lardi."
        return
    fi

    for bin in "$DOTFILES_DIR/.local/bin/"*; do
        [ ! -f "$bin" ] && continue
        name=$(basename "$bin")
        chmod +x "$bin"
        ln -sf "$bin" "$HOME/.local/bin/$name"
    done

    # niri-update va niri-doctor yorliqlarini qo'shish
    ln -sf "$DOTFILES_DIR/update.sh" "$HOME/.local/bin/niri-update"
    ln -sf "$DOTFILES_DIR/doctor.sh" "$HOME/.local/bin/niri-doctor"
    chmod +x "$HOME/.local/bin/niri-update" "$HOME/.local/bin/niri-doctor"

    echo -e "${GREEN}✓ Skriptlar muvaffaqiyatli bog'landi.${NC}"
}

setup_binaries

# 6. $PATH sozlamasi
ensure_path() {
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo -e "\n${YELLOW}💡 ~/.local/bin yo'li \$PATH ga qo'shilmoqda...${NC}"
        if [ "$DRY_RUN" = "false" ]; then
            for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
                if [ -f "$rc" ] && ! grep -q 'HOME/.local/bin' "$rc"; then
                    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
                fi
            done
        fi
    fi
}

ensure_path

# 7. Tanlangan modullarni ishga tushirish
run_modules() {
    echo -e "\n${BOLD}${BLUE}🧩 Tanlangan modullar o'rnatilmoqda...${NC}"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "  [Dry-run] Tanlangan modullar ishga tushgan bo'lardi."
        return
    fi

    if [[ "$CHOSEN_MODULES" == *"FONTS"* ]]; then
        bash "$DOTFILES_DIR/modules/fonts.sh"
    fi

    if [[ "$CHOSEN_MODULES" == *"AUDIO"* ]]; then
        bash "$DOTFILES_DIR/modules/audio.sh"
    fi

    if [[ "$CHOSEN_MODULES" == *"WALLPAPERS"* ]]; then
        bash "$DOTFILES_DIR/modules/wallpapers.sh"
    fi

    if [[ "$CHOSEN_MODULES" == *"GESTURES"* ]]; then
        bash "$DOTFILES_DIR/modules/gestures.sh"
    fi

    if [[ "$CHOSEN_MODULES" == *"QUICK_AI"* ]]; then
        bash "$DOTFILES_DIR/modules/quick-ai.sh"
    fi
}

run_modules

# 8. Hotcorner dasturini kompilatsiya qilish
compile_hotcorner() {
    if [ "$DRY_RUN" = "false" ] && [ -f "$DOTFILES_DIR/.config/niri/hotcorner.c" ]; then
        if command -v gcc >/dev/null 2>&1 && pkg-config --exists gtk+-3.0 gtk-layer-shell-0 2>/dev/null; then
            echo -e "${BLUE}🔨 Hotcorner moduli kompilatsiya qilinmoqda...${NC}"
            gcc -O2 "$DOTFILES_DIR/.config/niri/hotcorner.c" $(pkg-config --cflags --libs gtk+-3.0 gtk-layer-shell-0) -o "$DOTFILES_DIR/.config/niri/hotcorner" 2>/dev/null || true
            chmod +x "$DOTFILES_DIR/.config/niri/hotcorner" 2>/dev/null || true
        fi
    fi
}

compile_hotcorner

# 9. Diagnostika (Doctor) hisoboti
if [ "$DRY_RUN" = "false" ]; then
    bash "$DOTFILES_DIR/doctor.sh"
fi

echo -e "${BOLD}${GREEN}🎉 Niri Desktop Environment muvaffaqiyatli o'rnatildi!${NC}"
echo -e "${BLUE}Tizimdan chiqib, Display Manager'da (GDM/SDDM/LightDM/Greetd) 'Niri' sessiyasini tanlang.${NC}\n"
