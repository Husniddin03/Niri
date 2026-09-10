# Niri Gestures (Head & Eye Mouse + Hand Gestures)

Niri Wayland oynalar menejeri uchun veb-kamera orqali bosh va ko'z harakatlari (Head & Eye Pointer) hamda qo'l imo-ishoralari bilan boshqarish tizimi.

## 🚀 Ishga tushirish va Boshqarish

- **Tezkor yoqish / o'chirish:** Klaviaturada **`Mod + G`** tugmasini bosing.
- **Terminal orqali:**
  ```bash
  niri-gestures-toggle
  ```
- **Kamera, burun nuqtasi va ko'z holatini jonli oynada (Preview) ko'rish:**
  ```bash
  ~/.config/niri-gestures/.venv/bin/python ~/.config/niri-gestures/daemon.py --preview
  ```
  *(Oynani yopish uchun 'q' tugmasini bosing)*

---

## 🎯 1. Bosh va Ko'z orqali boshqaruv (Head & Eye Mouse) — Faol rejim

* **Kursor harakati (Head Pointer):**
  - Boshni yoki burunni yengil burish orqali kursor ekranda juda silliq va aniq harakatlanadi.
  - Mikro-titrash filtri va adaptiv silliqlash mavjud — bosh qimirlamay turganda kursor qotib turadi.
* **Sichqonchaning chap tugmasi (Left Click):**
  - **Chap ko'zni qisish (😉 Left Wink):** Sichqonchaning chap tugmasi bosiladi!
* **Sichqonchaning o'ng tugmasi (Right Click):**
  - **O'ng ko'zni qisish (😉 Right Wink):** Sichqonchaning o'ng tugmasi (kontekst menyusi) bosiladi!
* **Oddiy pirpirashdan himoya:**
  - Ikkala ko'z bir vaqtda tabiiy yumilib ochilganda hech qanday tugma bosilmaydi.

---

## 🖐️ 2. Rejimlarni almashtirish (`config.json`)

`~/.config/niri-gestures/config.json` fayli orqali rejimni o'zgartirishingiz mumkin:
* `"tracking_mode": "head_eye"` — Bosh va Ko'z orqali boshqaruv (hozir faol).
* `"tracking_mode": "hand"` — Qo'l barmoqlari orqali boshqaruv (Air Mouse & Gestures).
* `"tracking_mode": "both"` — Ikkala rejim birgalikda.
