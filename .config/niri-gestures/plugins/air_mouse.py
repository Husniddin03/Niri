import math
import subprocess
import shutil
import time
from .base import BasePlugin

class AirMousePlugin(BasePlugin):
    name = "air_mouse"
    description = "Index fingertip directly acts as the system mouse cursor (1:1 Absolute Tracking); pinch thumb+index for left click/drag; pinch thumb+middle for right click"

    def __init__(self, config=None):
        super().__init__(config)
        self.waymouse_bin = shutil.which("waymouse") or "/home/husniddin/.local/bin/waymouse"
        self.proc = None
        self._init_proc()

        # Margins to allow comfortable full-screen reach without overstretching hand
        self.margin_x = float(self.config.get("margin_x", 0.08))
        self.margin_y = float(self.config.get("margin_y", 0.08))

        # Absolute coordinates & smoothing
        self.smooth_x = None
        self.smooth_y = None
        self.left_pressed = False
        self.right_pressed = False
        self.last_pointing_time = 0.0
        self.pinch_start_time = 0.0
        self.is_dragging = False
        self.freeze_pos = None

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

        screen_w = float(event.get("screen_w", 1920))
        screen_h = float(event.get("screen_h", 1080))

        # Natural pointing detection: Index extended, not a full open palm
        d_idx_tip = self._dist(lm[0], lm[8])
        d_idx_pip = self._dist(lm[0], lm[6])
        idx_extended = d_idx_tip > d_idx_pip * 1.12

        mid_folded = self._dist(lm[0], lm[12]) < self._dist(lm[0], lm[10]) * 1.28
        rng_folded = self._dist(lm[0], lm[16]) < self._dist(lm[0], lm[14]) * 1.25
        pnk_folded = self._dist(lm[0], lm[20]) < self._dist(lm[0], lm[18]) * 1.25

        gesture = event.get("gesture", "")
        is_open_palm = gesture == "Open_Palm" or (idx_extended and not mid_folded and not rng_folded and not pnk_folded)
        is_two_finger = idx_extended and not mid_folded and rng_folded and pnk_folded

        is_pointing_pose = idx_extended and not is_open_palm and not is_two_finger

        # Pinch detection (normalized by hand_scale)
        thumb_idx_dist = self._dist(lm[4], lm[8]) / hand_scale
        thumb_mid_dist = self._dist(lm[4], lm[12]) / hand_scale

        now = time.time()

        # 1. Left Click & Hold / Drag (Thumb + Index pinch with Click-Freeze)
        if thumb_idx_dist < 0.32:
            if not self.left_pressed:
                self.left_pressed = True
                self.pinch_start_time = now
                self.is_dragging = False
                if self.smooth_x is not None and self.smooth_y is not None:
                    self.freeze_pos = (self.smooth_x, self.smooth_y)
                self._send("d left")
        elif thumb_idx_dist > 0.38:
            if self.left_pressed:
                self._send("u left")
                self.left_pressed = False
                self.is_dragging = False
                self.freeze_pos = None

        # 2. Right Click (Thumb + Middle pinch)
        if thumb_mid_dist < 0.30:
            if not self.right_pressed:
                self._send("d right")
                self.right_pressed = True
        elif thumb_mid_dist > 0.42:
            if self.right_pressed:
                self._send("u right")
                self.right_pressed = False

        # 3. Direct Fingertip Cursor (Absolute 1:1 Positioning)
        if (is_pointing_pose or self.left_pressed) and not is_open_palm:
            self.last_pointing_time = now
            raw_x, raw_y = lm[8][0], lm[8][1] # Index fingertip landmark

            # Map from camera frame to screen coordinates
            target_sx = min(max(0.0, (raw_x - self.margin_x) / (1.0 - 2.0 * self.margin_x)), 1.0) * screen_w
            target_sy = min(max(0.0, (raw_y - self.margin_y) / (1.0 - 2.0 * self.margin_y)), 1.0) * screen_h

            # Click-Freeze protection: If pinch just started, freeze cursor to avoid misclicks
            if self.left_pressed and self.freeze_pos is not None:
                if not self.is_dragging:
                    dist_from_freeze = math.hypot(target_sx - self.freeze_pos[0], target_sy - self.freeze_pos[1])
                    if (now - self.pinch_start_time > 0.25) and (dist_from_freeze > 28.0):
                        self.is_dragging = True
                    else:
                        target_sx, target_sy = self.freeze_pos

            if self.smooth_x is None or self.smooth_y is None:
                self.smooth_x = target_sx
                self.smooth_y = target_sy
            else:
                dist = math.hypot(target_sx - self.smooth_x, target_sy - self.smooth_y)
                if dist > 1.2:
                    alpha = min(max(dist / 38.0, 0.45), 0.90)
                    self.smooth_x = alpha * target_sx + (1.0 - alpha) * self.smooth_x
                    self.smooth_y = alpha * target_sy + (1.0 - alpha) * self.smooth_y

            # Move system cursor
            ix_int = int(round(self.smooth_x))
            iy_int = int(round(self.smooth_y))
            self._send(f"a {ix_int} {iy_int} {int(screen_w)} {int(screen_h)}")
        else:
            if now - self.last_pointing_time > 0.15:
                self.smooth_x = None
                self.smooth_y = None
                self.freeze_pos = None

    def _reset_tracking(self):
        if self.left_pressed:
            self._send("u left")
            self.left_pressed = False
        if self.right_pressed:
            self._send("u right")
            self.right_pressed = False
        self.smooth_x = None
        self.smooth_y = None

    def __del__(self):
        if self.proc:
            try:
                self._send("q")
                self.proc.terminate()
            except Exception:
                pass
