import subprocess
import time
import shutil

class BasePlugin:
    """Base class for all niri-gestures action plugins."""
    name = "base"
    description = "Base plugin"

    def __init__(self, config=None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.last_trigger_time = 0.0
        self.cooldown = float(self.config.get("cooldown", 0.5))
        self.waykey_bin = shutil.which("waykey") or "/home/husniddin/.local/bin/waykey"

    def can_trigger(self, min_interval=None) -> bool:
        interval = min_interval if min_interval is not None else self.cooldown
        now = time.time()
        if now - self.last_trigger_time >= interval:
            self.last_trigger_time = now
            return True
        return False

    def niri_action(self, *actions):
        """Execute a Niri compositor action via `niri msg action ...`"""
        try:
            cmd = ["niri", "msg", "action"] + list(actions)
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[{self.name}] Error running niri action: {e}")

    def send_key(self, key_name: str):
        """Simulate a keyboard key press via native waykey."""
        try:
            subprocess.run([self.waykey_bin, key_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[{self.name}] Error sending key: {e}")

    def run_cmd(self, cmd_args):
        """Run an external command."""
        try:
            subprocess.run(cmd_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[{self.name}] Error running cmd: {e}")

    def on_event(self, event: dict):
        """
        Called on each frame where a hand or gesture is tracked.
        event contains:
          - gesture: str ("Pointing_Up", "Closed_Fist", "Open_Palm", "Victory", "Thumb_Up", "Thumb_Down", "None")
          - dynamic_action: str ("swipe_left", "swipe_right", "scroll_up", "scroll_down", "pinch")
          - confidence: float
          - landmarks: list of 21 (x, y, z)
          - palm_center: (x, y)
          - index_tip: (x, y)
          - thumb_tip: (x, y)
          - pinch_dist: float
          - handedness: "Left" or "Right"
        """
        pass
