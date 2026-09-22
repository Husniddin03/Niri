# Niri Holographic Gestures (Butun Tizimni Qo'l Bilan Boshqarish)

Niri Wayland oynalar menejeri uchun veb-kamera orqali **shaffof gologramma qo'l (Apple Vision Pro / Iron Man HUD effekti)** bilan butun Linux tizimini havoda boshqarish tizimi.

Videodagi kabi ekranning ustida qo'lingiz to'liq **shaffof, neon oq/moviy nurli kontur, rentgen suyak chiziqlari va interaktiv nishon (reticle)** ko'rinishida paydo bo'ladi va barcha oynalarni, kursorni, skrollni va tizim funksiyalarini bevosita boshqaradi.

---

## 🚀 Qanday yoqiladi va o'chiriladi?

* **Klaviatura orqali (Tezkor):** **`Mod + G`** tugmasini bosing *(yoqiladi va bildirishnoma chiqadi, yana bir marta bossangiz o'chadi)*.
* **Terminal orqali:**
  ```bash
  niri-gestures-toggle
  ```
* **To'g'ridan-to'g'ri ishga tushirish:**
  ```bash
  ~/.config/niri-gestures/.venv/bin/python ~/.config/niri-gestures/daemon.py
  ```
* **Kamera va imo-ishoralarni debug oynada (Preview) ko'rish:**
  ```bash
  ~/.config/niri-gestures/.venv/bin/python ~/.config/niri-gestures/daemon.py --preview
  ```

---

## 🖐️ Tizimni Boshqarish Imo-ishoralari (Gestures)

| Harakat / Imo-ishora | Amal (Action) | Tavsifi va Ekranda Ko'rinishi |
| :--- | :--- | :--- |
| ☝️ **Ko'rsatkich barmoq (Pointing)** | **Air Mouse (Kursor)** | Ko'rsatkich barmog'ingiz uchida futuristik nishon paydo bo'lib, sichqoncha kursorini butun ekran bo'ylab silliq harakatlantiradi. |
| 🤏 **Chimchilash (Index + Thumb Pinch)** | **Left Click & Drag** | Bosh va ko'rsatkich barmoqni birlashtirganda elektr-moviy impuls bilan chap klik bosiladi; ushlab tursangiz oynalar yoki slayderlarni surish (drag-and-drop) mumkin. |
| 🤌 **Thumb + Middle Pinch** | **Right Click** | Bosh va o'rta barmoqni birlashtirganda kontekst menyusi (o'ng klik) ochiladi. |
| ✌️ **Ikki barmoq harakati (Two-Finger)** | **Smooth Scroll** | Ko'rsatkich va o'rta barmoqni tepaga/pastga sursangiz, sahifa yoki hujjat ravon skroll bo'ladi (`▲ SCROLL ▼` nishoni chiqadi). |
| 🖐️ **Ochiq kaft (Open Palm)** | **Niri Overview** | Kaftingizni ochib ko'rsatsangiz, kaft markazida aylanuvchi gologramma halqa chiqadi va Niri Overview rejimiga o'tadi. |
| 👈 **Chapga silkitish (Swipe Left)** | **Next Column / Window** | Niri lentasidagi keyingi oynaga o'tadi (`◀ WINDOW NEXT`). |
| 👉 **O'ngga silkitish (Swipe Right)** | **Prev Column / Window** | Niri lentasidagi oldingi oynaga o'tadi (`WINDOW PREV ▶`). |
| 👆 **Tepaga silkitish (Swipe Up)** | **Workspace Down** | Pastdagi ishchi stolga o'tadi (`▲ WORKSPACE UP`). |
| 👇 **Pastga silkitish (Swipe Down)** | **Workspace Up** | Yuqoridagi ishchi stolga o'tadi (`▼ WORKSPACE DOWN`). |
| 👍 **Bosh barmoq tepaga (Thumb Up)** | **Volume Up (+5%)** | Tizim ovozini oshiradi (`🔊 VOL +` HUD nishoni bilan). |
| 👎 **Bosh barmoq pastga (Thumb Down)** | **Volume Down (-5%)** | Tizim ovozini pasaytiradi (`🔉 VOL -` HUD nishoni bilan). |
| ✌️ **Peace / Victory (V belgisi)** | **Play / Pause** | YouTube / musiqa pleyerni to'xtatadi yoki davom ettiradi (`⏯ PLAY/PAUSE`). |
| 🤟 **Rock / ILoveYou** | **Next Track** | Keyingi trekka o'tkazadi (`⏭ NEXT TRACK`). |

---

## ✨ Shaffof Gologramma Vizual Xususiyatlari

1. **Shaffoflik (True Alpha Transparency):** `GtkLayerShell` orqali yaratilgan qatlam fonni to'liq shaffof qilib ushlab turadi, orqadagi brauzer, kod yoki matnlar bemalol o'qiladi.
2. **Neon Kontur va Rentgen nurlari:** Qo'lning barcha bo'g'inlari va suyaklari oq-moviy nurda ravon ulanadi, bilak qismidan pastga qarab gradient bilan yo'qoladi.
3. **Interaktiv Nishon (Active Reticle):** Chimchilaganda nishon siqilib yorishadi, bo'shatilganda ochiladi, barcha harakatlarda kichik va estetik HUD yorliqlari ko'rinadi.
4. **Har ikki qo'lni qo'llab-quvvatlash (Dual Hands):** Bir vaqtning o'zida ikkala qo'l ham kamerada ko'rinsa, ekranda ikkalasi ham shaffof holda aks etadi.
5. **60 FPS & Click-Through:** Qatlam orqali sichqoncha va klaviatura to'liq o'tadi (input passthrough), hech qanday qotish yoki kechikishsiz ishlaydi.
