import time
from collections import deque

class GestureEngine:
    """Analyzes continuous landmark motion across frames to detect dynamic gestures."""
    def __init__(self, history_len: int = 8):
        self.history = deque(maxlen=history_len)
        self.last_swipe_time = 0.0

    def process(self, event: dict) -> dict:
        if not event or "palm_center" not in event:
            self.history.clear()
            return event

        now = time.time()
        palm_x, palm_y = event["palm_center"]
        self.history.append((now, palm_x, palm_y))

        event["dynamic_action"] = None

        if len(self.history) >= 4 and (now - self.last_swipe_time > 0.6):
            t_old, x_old, y_old = self.history[0]
            dt = now - t_old
            dx = palm_x - x_old
            dy = palm_y - y_old

            if 0.08 < dt < 0.35 and abs(dx) > 0.18 and abs(dx) > abs(dy) * 1.5:
                if dx < 0:
                    event["dynamic_action"] = "swipe_left"
                    self.last_swipe_time = now
                    self.history.clear()
                else:
                    event["dynamic_action"] = "swipe_right"
                    self.last_swipe_time = now
                    self.history.clear()

        return event
