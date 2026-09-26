import time
from .base import BasePlugin

class VolumeControlPlugin(BasePlugin):
    name = "volume_control"
    description = "Increases/decreases audio volume using Thumb_Up and Thumb_Down gestures"

    def __init__(self, config=None):
        super().__init__(config)
        self.step_interval = float(self.config.get("interval", 0.30))
        self.last_step_time = 0.0
        self.last_gesture = None
        self.consecutive_frames = 0

    def on_event(self, event: dict):
        if not self.enabled:
            return

        gesture = event.get("gesture")
        confidence = event.get("confidence", 0.0)

        if confidence < 0.72:
            self.consecutive_frames = 0
            self.last_gesture = None
            return

        if gesture in ("Thumb_Up", "Thumb_Down"):
            if gesture == self.last_gesture:
                self.consecutive_frames += 1
            else:
                self.last_gesture = gesture
                self.consecutive_frames = 1
        else:
            self.consecutive_frames = 0
            self.last_gesture = None
            return

        # At least 3 consecutive stable frames required
        if self.consecutive_frames < 3:
            return

        now = time.time()
        if now - self.last_step_time < self.step_interval:
            return

        if gesture == "Thumb_Up":
            self.run_cmd([os.path.expanduser("~/.config/niri/scripts/volume.sh"), "up"])
            self.last_step_time = now
        elif gesture == "Thumb_Down":
            self.run_cmd([os.path.expanduser("~/.config/niri/scripts/volume.sh"), "down"])
            self.last_step_time = now
