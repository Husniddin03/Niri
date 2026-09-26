import math
import subprocess
import shutil
import time
from .base import BasePlugin

class HeadEyeMousePlugin(BasePlugin):
    name = "head_eye_mouse"
    description = "Control mouse cursor with head/nose movement; left eye wink = left click, right eye wink = right click"

    def __init__(self, config=None):
        super().__init__(config)
        self.sensitivity = float(self.config.get("sensitivity", 2800.0))
        self.deadzone = float(self.config.get("deadzone", 0.0018))
        self.blink_threshold = float(self.config.get("blink_threshold", 0.58))
        self.wink_cooldown = float(self.config.get("cooldown", 0.40))

        self.waymouse_bin = shutil.which("waymouse") or os.path.expanduser("~/.local/bin/waymouse"
        self.proc = None
        self._init_proc()

        # Motion state
        self.prev_x = None
        self.prev_y = None
        self.smooth_dx = 0.0
        self.smooth_dy = 0.0

        # Click state
        self.last_left_click = 0.0
        self.last_right_click = 0.0

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
            if "READY" not in line:
                print(f"[head_eye_mouse] Warning: unexpected waymouse output: {line}", flush=True)
        except Exception as e:
            print(f"[head_eye_mouse] Failed to start waymouse: {e}", flush=True)
            self.proc = None

    def _send(self, cmd: str):
        if self.proc is None or self.proc.poll() is not None:
            self._init_proc()
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()
            except Exception as e:
                print(f"[head_eye_mouse] Error sending to waymouse: {e}", flush=True)
                self.proc = None

    def on_event(self, event: dict):
        if not self.enabled:
            return

        face = event.get("face")
        if not face:
            self.prev_x = None
            self.prev_y = None
            self.smooth_dx = 0.0
            self.smooth_dy = 0.0
            return

        now = time.time()
        nose = face.get("nose_tip")
        blink_l = face.get("blink_left", 0.0)
        blink_r = face.get("blink_right", 0.0)

        # 1. Wink Detection (Left eye wink = Left click, Right eye wink = Right click)
        # Protect against natural simultaneous blinking of both eyes
        is_natural_blink = (blink_l > 0.45 and blink_r > 0.45)

        if not is_natural_blink:
            # Left Eye Wink -> Left Click
            if blink_l >= self.blink_threshold and blink_r < 0.32:
                if now - self.last_left_click >= self.wink_cooldown:
                    print(f"[head_eye_mouse] 😉 LEFT EYE WINK -> Click Left ({blink_l:.2f})", flush=True)
                    self._send("c left")
                    self.last_left_click = now

            # Right Eye Wink -> Right Click
            elif blink_r >= self.blink_threshold and blink_l < 0.32:
                if now - self.last_right_click >= self.wink_cooldown:
                    print(f"[head_eye_mouse] 😉 RIGHT EYE WINK -> Click Right ({blink_r:.2f})", flush=True)
                    self._send("c right")
                    self.last_right_click = now

        # 2. Head / Nose Pointer Motion Tracking
        if nose:
            curr_x, curr_y = nose[0], nose[1]
            if self.prev_x is not None and self.prev_y is not None:
                dx_raw = curr_x - self.prev_x
                dy_raw = curr_y - self.prev_y
                dist_raw = math.hypot(dx_raw, dy_raw)

                if dist_raw <= self.deadzone:
                    # Tremor deadband: freeze cursor when head is steady
                    self.smooth_dx *= 0.35
                    self.smooth_dy *= 0.35
                    if abs(self.smooth_dx) < 0.05: self.smooth_dx = 0.0
                    if abs(self.smooth_dy) < 0.05: self.smooth_dy = 0.0
                else:
                    # Dynamic adaptive smoothing:
                    # Subtle movements -> high stability
                    # Quick turns -> immediate responsiveness
                    adaptive_alpha = min(max(dist_raw * 60.0, 0.25), 0.80)

                    target_dx = dx_raw * self.sensitivity
                    target_dy = dy_raw * self.sensitivity

                    self.smooth_dx = adaptive_alpha * target_dx + (1.0 - adaptive_alpha) * self.smooth_dx
                    self.smooth_dy = adaptive_alpha * target_dy + (1.0 - adaptive_alpha) * self.smooth_dy

                    # Gentle acceleration
                    speed = math.hypot(self.smooth_dx, self.smooth_dy)
                    accel = 1.0 + min(speed / 50.0, 1.3)

                    dx_final = self.smooth_dx * accel
                    dy_final = self.smooth_dy * accel

                    if abs(dx_final) > 0.1 or abs(dy_final) > 0.1:
                        self._send(f"m {dx_final:.2f} {dy_final:.2f}")

            self.prev_x = curr_x
            self.prev_y = curr_y

    def __del__(self):
        if self.proc:
            try:
                self._send("q")
                self.proc.terminate()
            except Exception:
                pass
