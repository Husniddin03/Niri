import time
from .base import BasePlugin

class MediaControlPlugin(BasePlugin):
    name = "media_control"
    description = "Controls media playback using Victory (Play/Pause) and ILoveYou (Next track) gestures"

    def __init__(self, config=None):
        super().__init__(config)
        self.cooldown = float(self.config.get("cooldown", 1.0))
        self.last_trigger_time = 0.0
        self.last_gesture = None
        self.consecutive_frames = 0

    def on_event(self, event: dict):
        if not self.enabled:
            return

        # Do not trigger media control if user is performing two-finger scroll
        if event.get("is_two_finger", False):
            self.consecutive_frames = 0
            self.last_gesture = None
            return

        gesture = event.get("gesture")
        confidence = event.get("confidence", 0.0)

        if confidence < 0.75:
            self.consecutive_frames = 0
            self.last_gesture = None
            return

        if gesture in ("Victory", "ILoveYou"):
            if gesture == self.last_gesture:
                self.consecutive_frames += 1
            else:
                self.last_gesture = gesture
                self.consecutive_frames = 1
        else:
            self.consecutive_frames = 0
            self.last_gesture = None
            return

        # Require at least 4 consecutive frames (~130ms) of clear gesture
        if self.consecutive_frames < 4:
            return

        now = time.time()
        if now - self.last_trigger_time < self.cooldown:
            return

        if gesture == "Victory":
            print("[media_control] VICTORY -> playerctl play-pause", flush=True)
            self.run_cmd(["playerctl", "play-pause"])
            self.last_trigger_time = now
            self.consecutive_frames = 0
        elif gesture == "ILoveYou":
            print("[media_control] ILOVEYOU -> playerctl next", flush=True)
            self.run_cmd(["playerctl", "next"])
            self.last_trigger_time = now
            self.consecutive_frames = 0
