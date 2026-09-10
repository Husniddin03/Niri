import time
from .base import BasePlugin

class VolumeControlPlugin(BasePlugin):
    name = "volume_control"
    description = "Increases/decreases audio volume using Thumb_Up and Thumb_Down gestures"

    def __init__(self, config=None):
        super().__init__(config)
        self.step_interval = float(self.config.get("interval", 0.30))
        self.last_step_time = 0.0

    def on_event(self, event: dict):
        if not self.enabled:
            return

        gesture = event.get("gesture")
        confidence = event.get("confidence", 0.0)

        if confidence < 0.70:
            return

        now = time.time()
        if now - self.last_step_time < self.step_interval:
            return

        if gesture == "Thumb_Up":
            self.run_cmd(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"])
            self.last_step_time = now
        elif gesture == "Thumb_Down":
            self.run_cmd(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"])
            self.last_step_time = now
