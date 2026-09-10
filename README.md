# 🌌 Niri Scrollable Tiling Wayland Desktop Setup

Bu repository Linux (Wayland) muhitida **Niri** scrollable tiling oynalar menejeri uchun toʻliq sozlangan, zamonaviy, tezkor va qulay ishchi muhit (dotfiles) toʻplamidir.

---

## 🎨 Asosiy Imkoniyatlar va Komponentlar

* **Oynalar boshqaruvi**: [Niri](https://github.com/YaLTeR/niri) — cheksiz gorizontal lenta (infinite scrollable tiling).
* **Yuqori panel**: [Waybar](https://github.com/Alexays/Waybar) — tarmoq tezligi, batareya, protsessor, xotira va boshqaruv indikatorlari.
* **Bildirishnomalar (OSD)**: [Dunst](https://dunst-project.org/) — Catppuccin / Obsidian glass uslubida, ovoz va yorugʻlik sathi uchun toza progress-bar.
* **Ilovalarni ishga tushirish (Launcher)**: [Fuzzel](https://codeberg.org/dnkl/fuzzel).
* **Terminal**: [Foot](https://codeberg.org/dnkl/foot).
* **Ekran qulflash va chiqish**: [Swaylock](https://github.com/swaywm/swaylock) & [Wlogout](https://github.com/ArtsyMacaw/wlogout).
* **Sun'iy intellekt va foydali vositalar**:
  * 🎙️ **`quick-voice` (`Mod+Space`)**: Bosib turib ovoz yoziladi, qoʻyib yuborilganda 1 soniyada Gemini orqali aniq matnga aylanib avtomatik kursor joyiga yoziladi.
  * 👁️ **`quick-ocr` (`Mod+X`)**: Ekranning istalgan qismidagi matnni internetsiz tezkor ajratib olib clipboard'ga nusxalaydi.
  * 🎥 **`quick-recorder` (`Mod+Alt+R`)**: Ekran yoki tanlangan oynani yozib olish (taymer paneli bilan).
  * 📋 **`clip-menu` (`Mod+V`)**: Rasm va matnlar tarixi bilan bufer boshqaruvi.
  * 🌙 **`quick-nightlight` (`Mod+Shift+N`)**: Tungi rejim (koʻzni asrash uchun 3500K iliq tus).
  * 🖐️ **`niri-gestures`**: Kamera orqali qoʻl harakatlari yordamida kursorni va tizimni boshqarish moduli.

---

## ⌨️ Asosiy Tugmalar (Keybindings)

| Tugma | Vazifasi |
|---|---|
| `Mod + Return` | Terminalni ochish (`foot`) |
| `Mod + D` | Ilovalar menyusi (`fuzzel`) |
| `Mod + Space` | 🎙️ Ovoz orqali yozish (Diktant / Speech-to-Text) |
| `Mod + V` | 📋 Nusxalar tarixi (Clipboard History) |
| `Mod + X` | 👁️ Ekranning qismini tanlab matn ajratib olish (OCR) |
| `Mod + Shift + N` | 🌙 Tungi rejimni yoqish / oʻchirish (Night Light) |
| `Mod + O` | Oynalarni umumiy koʻrish (Overview toggle) |
| `Mod + Q` / `Mod + Shift + Q` | Oynani yopish |
| `Mod + Shift + V` | Suzuvchi (Floating) rejimga oʻtkazish |
| `Print` | Skrinshot olish (`screenshot.sh`) |
| `Mod + Escape` | Chiqish menyusi (`wlogout`) |
| `XF86Audio*` / `Fn+F*` | Ovozni boshqarish (zamonaviy OSD bilan) |
| `XF86MonBrightness*` | Ekran yorugʻligini boshqarish |

---

## 🚀 Oʻrnatish (Installation)

1. Reponi klon qiling:
```bash
git clone git@github.com:Husniddin03/Niri.git ~/.dotfiles-niri
cd ~/.dotfiles-niri
```

2. Oʻrnatish skriptini ishga tushiring:
```bash
chmod +x install.sh
./install.sh
```

3. Niri konfiguratsiyasini qayta yuklang yoki tizimga qayta kiring:
```bash
niri msg action load-config-file
```

---

## 📦 Kerakli Dasturlar (Dependencies)

Tizimda quyidagi paketlar oʻrnatilgan boʻlishi tavsiya etiladi (Debian/Ubuntu/Arch):
* `niri`, `waybar`, `dunst`, `swaybg`, `swayidle`, `swaylock`, `wlogout`, `fuzzel`, `foot`
* `grim`, `slurp`, `wl-clipboard`, `wf-recorder`, `brightnessctl`, `wireplumber` (`wpctl`)
* `tesseract-ocr`, `python3`, `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-gtklayershell-0.1`

---
*Created by Husniddin.*
