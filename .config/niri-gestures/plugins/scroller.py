import math
import time
import shutil
import subprocess
from .base import BasePlugin

class ScrollerPlugin(BasePlugin):
    name = "scroller"
    description = "Continuous smooth two-finger scrolling or page scrolling"

    def __init__(self, config=None):
        super().__init__(config)
        self.sensitivity = float(self.config.get("sensitivity", 28.0))
        self.waymouse_bin = shutil.which("waymouse") or os.path.expanduser("~/.local/bin/waymouse")
        self.proc = None
        self._init_proc()

        self.prev_y = None
        self.last_scroll_time = 0.0

    def _init_proc(self):
        try:
            self.proc = subprocess.Popen(
                [self.waymouse_bin],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            line = self.proc.stdout.readline()
        except Exception as e:
            self.proc = None

    def _send(self, cmd: str):
        if self.proc is None or self.proc.poll() is not None:
            self._init_proc()
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()
            except Exception:
                self.proc = None

    def _dist(self, p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def on_event(self, event: dict):
        if not self.enabled:
            return

        landmarks = event.get("landmarks")
        if not landmarks or len(landmarks) < 21:
            self.prev_y = None
            return

        lm = landmarks
        # Check two-finger scroll: Index + Middle extended, Ring + Pinky curled
        d_idx = self._dist(lm[0], lm[8]) > self._dist(lm[0], lm[6]) * 1.12
        d_mid = self._dist(lm[0], lm[12]) > self._dist(lm[0], lm[10]) * 1.12
        d_rng = self._dist(lm[0], lm[16]) < self._dist(lm[0], lm[14]) * 1.25
        d_pnk = self._dist(lm[0], lm[20]) < self._dist(lm[0], lm[18]) * 1.25

        gesture = event.get("gesture", "")
        is_two_finger_scroll = (d_idx and d_mid and d_rng and d_pnk) or (gesture == "Victory")

        if not is_two_finger_scroll:
            self.prev_y = None
            return

        curr_y = (lm[8][1] + lm[12][1]) / 2.0
        now = time.time()

        if self.prev_y is not None:
            dy = curr_y - self.prev_y
            if abs(dy) > 0.005:
                # Natural scrolling: moving fingers up scrolls document up (negative dy in screen coords)
                scroll_amount = -dy * self.sensitivity
                # Send smooth axis scroll to waymouse
                self._send(f"s {scroll_amount:.2f}")
                self.last_scroll_time = now

        self.prev_y = curr_y

    def __del__(self):
        if self.proc:
            try:
                self._send("q")
                self.proc.terminate()
            except Exception:
                pass
