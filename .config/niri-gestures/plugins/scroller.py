import math
import time
from .base import BasePlugin

class ScrollerPlugin(BasePlugin):
    name = "scroller"
    description = "Scrolls active window up or down when using 2 fingers (Victory) or open hand"

    def __init__(self, config=None):
        super().__init__(config)
        self.deadzone_top = float(self.config.get("deadzone_top", 0.42))
        self.deadzone_bottom = float(self.config.get("deadzone_bottom", 0.58))
        self.scroll_step_interval = float(self.config.get("interval", 0.15))
        self.use_page_scroll = bool(self.config.get("use_page_scroll", True))
        self.last_scroll_time = 0.0

    def _dist(self, p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def on_event(self, event: dict):
        if not self.enabled:
            return

        landmarks = event.get("landmarks")
        if not landmarks or len(landmarks) < 21:
            return

        lm = landmarks
        # Check if middle finger is extended (so 1-finger is reserved for AirMouse)
        d_mid_tip = self._dist(lm[0], lm[12])
        d_mid_pip = self._dist(lm[0], lm[10])
        mid_extended = d_mid_tip > d_mid_pip * 1.15

        gesture = event.get("gesture", "")

        # Scroll triggers if: 2 fingers extended (Victory / mid extended) or Open_Palm
        is_scroll_pose = mid_extended or gesture in ("Victory", "Open_Palm")
        if not is_scroll_pose:
            return

        index_tip = event.get("index_tip")
        if not index_tip:
            return

        y = index_tip[1]
        now = time.time()
        if now - self.last_scroll_time < self.scroll_step_interval:
            return

        if y < self.deadzone_top:
            key = "Page_Up" if self.use_page_scroll else "Up"
            self.send_key(key)
            self.last_scroll_time = now
            print(f"[scroller] Scroll UP (y={y:.2f}) -> {key}", flush=True)

        elif y > self.deadzone_bottom:
            key = "Page_Down" if self.use_page_scroll else "Down"
            self.send_key(key)
            self.last_scroll_time = now
            print(f"[scroller] Scroll DOWN (y={y:.2f}) -> {key}", flush=True)
