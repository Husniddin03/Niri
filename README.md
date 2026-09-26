# 🌌 Niri Scrollable Tiling Wayland Desktop Setup

Bu repository Linux (Wayland) muhitida **Niri** scrollable tiling oynalar menejeri uchun toʻliq sozlangan, professional, chiroyli va qulay ishchi muhit (dotfiles & desktop environment) toʻplamidir.

---

## 🚀 Tezkor O'rnatish (One-Liner Installation)

Istalgan yangi Linux tizimida (Debian/Ubuntu, Arch, Fedora) terminalni oching va quyidagi buyruqni bering:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Husniddin03/Niri/main/bootstrap.sh)
```

Yoki repozitoriyni klon qilib ishga tushiring:

```bash
git clone https://github.com/Husniddin03/Niri.git ~/.dotfiles-niri
cd ~/.dotfiles-niri
./install.sh
```

---

## 🛠️ Maxsus Buyruqlar va Utilitalar

O'rnatish yakunlangach, tizimingizda quyidagi qulay buyruqlar paydo bo'ladi:

| Buyruq | Vazifasi |
|---|---|
| `niri-doctor` | Muhit holati, paketlar, shriftlar va sintaksisni to'liq tekshirish (Diagnostika) |
| `niri-update` | Xavfsiz yangilash: lokal o'zgarishlarni zaxiralab, yangi dotfiles'larni tortadi va Niri/Waybar'ni qayta yuklaydi |
| `./install.sh --dry-run` | Tizimga tegmasdan, nimalar o'rnatilishi va bog'lanishini oldindan ko'rish |
| `./install.sh --uninstall` | Niri dotfiles'larini xavfsiz o'chirib, avvalgi zaxira nusxani qayta tiklash |

---

## 🎨 Asosiy Imkoniyatlar va Komponentlar

* **Oynalar boshqaruvi**: [Niri](https://github.com/YaLTeR/niri) — cheksiz gorizontal lenta (infinite scrollable tiling).
* **Yuqori panel**: [Waybar](https://github.com/Alexays/Waybar) — tarmoq tezligi, batareya, protsessor, xotira va boshqaruv indikatorlari. Overview bilan to'liq sinxronlangan (overview ochilgandagina paydo bo'ladi).
* **Bildirishnomalar (OSD)**: [Dunst](https://dunst-project.org/) — Catppuccin / Obsidian glass uslubida, ovoz va yorugʻlik sathi uchun toza progress-bar.
* **Ilovalarni ishga tushirish (Launcher)**: [Wofi](https://hg.sr.ht/~scoopta/wofi) & [Fuzzel](https://codeberg.org/dnkl/fuzzel).
* **Terminal**: [Foot](https://codeberg.org/dnkl/foot).
* **Ekran qulflash va chiqish**: [Swaylock](https://github.com/swaywm/swaylock) & [Wlogout](https://github.com/ArtsyMacaw/wlogout).
* **Sun'iy intellekt va foydali vositalar**:
  * 🎙️ **`quick-voice` (`Mod+Space`)**: Bosib turib ovoz yoziladi, qoʻyib yuborilganda Gemini orqali aniq matnga aylanib kursor turgan joyga yoziladi.
  * 👁️ **`quick-ocr` (`Mod+X`)**: Ekranning istalgan qismidagi matnni internetsiz tezkor ajratib olib clipboard'ga nusxalaydi.
  * 🎥 **`quick-recorder` (`Mod+Alt+R` / `Mod+Alt+G`)**: Ekran yoki tanlangan hududni video (MP4) yoki GIF qilib yozib olish.
  * 🎧 **`quick-audio-record` (`Mod+Alt+A`)**: Ovozni MP3 formatida yozib olish (burchakdagi ixcham vidjet orqali).
  * 📋 **`clip-menu` (`Mod+V`)**: Rasm va matnlar tarixi bilan bufer boshqaruvi.
  * 🌙 **`quick-nightlight` (`Mod+Shift+N`)**: Tungi rejim (koʻzni asrash uchun iliq tus).
  * 🖐️ **`niri-gestures` (`Mod+G`)**: Kamera orqali qoʻl harakatlari yordamida kursorni va tizimni boshqarish moduli (OpenCV / MediaPipe).

---

## ⌨️ Asosiy Tugmalar (Keybindings)

| Tugma | Vazifasi |
|---|---|
| `Mod + Return` | Terminalni ochish (`foot`) |
| `Mod + D` | Ilovalar menyusi (`wofi`) |
| `Mod + Tab` / `Mod + O` | Oynalarni umumiy koʻrish (Overview toggle) |
| `Mod + Shift + B` | Waybar'ni qo'lda ko'rsatish / yashirish |
| `Mod + Space` | 🎙️ Ovoz orqali yozish (Speech-to-Text) |
| `Mod + Alt + A` | 🎧 Ovoz yozish (MP3 audio recorder) |
| `Mod + Alt + R` | 🎥 Ekran videosini yozish (MP4) |
| `Mod + Alt + G` | 🎞️ Ekrandan GIF yozish |
| `Mod + V` | 📋 Nusxalar tarixi (Clipboard History) |
| `Mod + X` | 👁️ Ekranning qismini tanlab matn ajratib olish (OCR) |
| `Mod + Shift + N` | 🌙 Tungi rejimni yoqish / oʻchirish |
| `Mod + Shift + Q` | Oynani yopish |
| `Mod + Shift + V` | Suzuvchi (Floating) rejimga oʻtkazish |
| `Print` | Skrinshot olish (`screenshot.sh`) |
| `Mod + Shift + E` | Chiqish menyusi (`wlogout`) |
| `XF86Audio*` | Ovozni boshqarish (zamonaviy OSD bilan) |
| `XF86MonBrightness*` | Ekran yorugʻligini boshqarish |

---

## 📁 Arxitektura

```text
Niri/
├── bootstrap.sh            # curl one-liner uchun
├── install.sh              # Asosiy interaktiv installer (--dry-run, --doctor, --update, --uninstall)
├── update.sh               # Xavfsiz avto-yangilovchi (niri-update)
├── doctor.sh               # Muhit diagnostikasi (niri-doctor)
├── uninstall.sh            # O'chirish va zaxiradan tiklash
│
├── packages/               # Distro paket boshqaruvchilari
│   ├── debian.sh           # Debian / Ubuntu (apt + Niri binary fallback)
│   ├── arch.sh             # Arch Linux / Manjaro (pacman + yay)
│   └── fedora.sh           # Fedora (dnf + copr)
│
├── modules/                # Mustaqil modullar
│   ├── fonts.sh            # JetBrainsMono Nerd Font & FontAwesome
│   ├── audio.sh            # Wireplumber / Brightnessctl
│   ├── wallpapers.sh       # SWWW daemon & fon rasmlari
│   ├── gestures.sh         # OpenCV Hand Gestures
│   └── quick-ai.sh         # Quick AI yordamchi
│
├── .config/                # Universal dotfiles ($HOME va ~ yo'llari bilan)
│   ├── niri/
│   ├── waybar/
│   ├── wofi/
│   ├── foot/
│   ├── dunst/
│   ├── swaylock/
│   └── wlogout/
│
└── .local/
    └── bin/                # Universal yordamchi skriptlar
```

---
*Muallif: Husniddin.*
