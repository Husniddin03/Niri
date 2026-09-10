import math
import subprocess
import shutil
import time
from .base import BasePlugin

class AirMousePlugin(BasePlugin):
    name = "air_mouse"
    description = "Control mouse cursor with index finger; pinch thumb+index for left click/drag; pinch thumb+middle for right click"

    def __init__(self, config=None):
        super().__init__(config)
        # Tuned parameters for silky smooth, rock-solid cursor
        self.sensitivity = float(self.config.get("sensitivity", 1400.0))
        self.deadzone = float(self.config.get("deadzone", 0.0035)) # filters micro-tremors
        self.waymouse_bin = shutil.which("waymouse") or "/home/husniddin/.local/bin/waymouse"
        self.proc = None
        self._init_proc()

        # State tracking
        self.prev_x = None
        self.prev_y = None
        self.smooth_dx = 0.0
        self.smooth_dy = 0.0
        self.left_pressed = False
        self.right_pressed = False
        self.last_pointing_time = 0.0

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
                print(f"[air_mouse] Warning: unexpected waymouse output: {line}", flush=True)
        except Exception as e:
            print(f"[air_mouse] Failed to start waymouse: {e}", flush=True)
            self.proc = None

    def _send(self, cmd: str):
        if self.proc is None or self.proc.poll() is not None:
            self._init_proc()
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()
            except Exception as e:
                print(f"[air_mouse] Error sending to waymouse: {e}", flush=True)
                self.proc = None

    def _dist(self, p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def on_event(self, event: dict):
        if not self.enabled:
            return

        landmarks = event.get("landmarks")
        if not landmarks or len(landmarks) < 21:
            self._reset_tracking()
            return

        lm = landmarks
        hand_scale = self._dist(lm[0], lm[9])
        if hand_scale < 0.04:
            self._reset_tracking()
            return

        # Check if Index is extended
        d_idx_tip = self._dist(lm[0], lm[8])
        d_idx_pip = self._dist(lm[0], lm[6])
        idx_extended = d_idx_tip > d_idx_pip * 1.15

        # Check if other 3 fingers are curled
        mid_folded = self._dist(lm[0], lm[12]) < self._dist(lm[0], lm[10]) * 1.25
        rng_folded = self._dist(lm[0], lm[16]) < self._dist(lm[0], lm[14]) * 1.20
        pnk_folded = self._dist(lm[0], lm[20]) < self._dist(lm[0], lm[18]) * 1.20

        is_pointing_pose = idx_extended and mid_folded and rng_folded and pnk_folded

        # Pinch detection (normalized by hand_scale)
        thumb_idx_dist = self._dist(lm[4], lm[8]) / hand_scale
        thumb_mid_dist = self._dist(lm[4], lm[12]) / hand_scale

        now = time.time()

        # 1. Left Click & Hold (Thumb + Index)
        if thumb_idx_dist < 0.28:
            if not self.left_pressed:
                self._send("d left")
                self.left_pressed = True
        elif thumb_idx_dist > 0.38:
            if self.left_pressed:
                self._send("u left")
                self.left_pressed = False

        # 2. Right Click (Thumb + Middle)
        if thumb_mid_dist < 0.30:
            if not self.right_pressed:
                self._send("d right")
                self.right_pressed = True
        elif thumb_mid_dist > 0.40:
            if self.right_pressed:
                self._send("u right")
                self.right_pressed = False

        # 3. Smooth & Stabilized Motion Tracking
        if is_pointing_pose or self.left_pressed:
            self.last_pointing_time = now
            curr_x, curr_y = lm[8][0], lm[8][1]

            if self.prev_x is not None and self.prev_y is not None:
                dx_raw = curr_x - self.prev_x
                dy_raw = curr_y - self.prev_y
                dist_raw = math.hypot(dx_raw, dy_raw)

                if dist_raw <= self.deadzone:
                    # Tremor deadband: gradually decay momentum to completely freeze cursor
                    self.smooth_dx *= 0.4
                    self.smooth_dy *= 0.4
                    if abs(self.smooth_dx) < 0.05: self.smooth_dx = 0.0
                    if abs(self.smooth_dy) < 0.05: self.smooth_dy = 0.0
                else:
                    # Adaptive dynamic smoothing:
                    # Fast hand movements -> low smoothing (instant response)
                    # Slow hand movements -> high smoothing (surgical stability)
                    adaptive_alpha = min(max(dist_raw * 45.0, 0.20), 0.75)

                    target_dx = dx_raw * self.sensitivity
                    target_dy = dy_raw * self.sensitivity

                    self.smooth_dx = adaptive_alpha * target_dx + (1.0 - adaptive_alpha) * self.smooth_dx
                    self.smooth_dy = adaptive_alpha * target_dy + (1.0 - adaptive_alpha) * self.smooth_dy

                    # Precision curve: small motions remain gentle, fast motions accelerate
                    speed = math.hypot(self.smooth_dx, self.smooth_dy)
                    accel = 1.0 + min(speed / 60.0, 1.2)

                    dx_final = self.smooth_dx * accel
                    dy_final = self.smooth_dy * accel

                    if abs(dx_final) > 0.1 or abs(dy_final) > 0.1:
                        self._send(f"m {dx_final:.2f} {dy_final:.2f}")

            self.prev_x = curr_x
            self.prev_y = curr_y
        else:
            if now - self.last_pointing_time > 0.15:
                self.prev_x = None
                self.prev_y = None
                self.smooth_dx = 0.0
                self.smooth_dy = 0.0

    def _reset_tracking(self):
        if self.left_pressed:
            self._send("u left")
            self.left_pressed = False
        if self.right_pressed:
            self._send("u right")
            self.right_pressed = False
        self.prev_x = None
        self.prev_y = None
        self.smooth_dx = 0.0
        self.smooth_dy = 0.0

    def __del__(self):
        if self.proc:
            try:
                self._send("q")
                self.proc.terminate()
            except Exception:
                pass
