#!/usr/bin/env python3
import math
import time
import threading
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib
import cairo

class HandState:
    def __init__(self, handedness="Right"):
        self.handedness = handedness
        self.raw_landmarks = None
        self.smooth_landmarks = None
        self.opacity = 0.0
        self.target_opacity = 0.0
        self.is_pinch = False
        self.is_two_finger = False
        self.is_open_palm = False
        self.action_badge = None
        self.badge_time = 0.0
        self.pulse_phase = 0.0

class HolographicHandOverlay:
    def __init__(self, screen_w=1920, screen_h=1080):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.lock = threading.Lock()

        # Tracked hands: Left and Right
        self.hands = {
            "Right": HandState("Right"),
            "Left": HandState("Left"),
        }

        self.last_active_time = time.time()
        self.is_running = True

        # Setup GTK Window
        self.win = Gtk.Window()
        GtkLayerShell.init_for_window(self.win)
        GtkLayerShell.set_layer(self.win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self.win, "niri-holographic-hand")

        # Fullscreen overlay anchor
        for edge in [
            GtkLayerShell.Edge.TOP,
            GtkLayerShell.Edge.BOTTOM,
            GtkLayerShell.Edge.LEFT,
            GtkLayerShell.Edge.RIGHT,
        ]:
            GtkLayerShell.set_anchor(self.win, edge, True)

        GtkLayerShell.set_keyboard_mode(self.win, GtkLayerShell.KeyboardMode.NONE)

        # Transparent RGBA visual
        screen = self.win.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.win.set_visual(visual)
        self.win.set_app_paintable(True)

        # Click-through: empty input shape
        empty_region = cairo.Region()
        self.win.input_shape_combine_region(empty_region)

        self.win.connect("draw", self.on_draw)
        self.win.connect("destroy", self.on_destroy)

        # 60 FPS animation timer (16ms)
        GLib.timeout_add(16, self.on_tick)

    def show(self):
        self.win.show_all()

    def update_hands_data(self, hands_list, active_badges=None):
        """Thread-safe update from vision tracker"""
        now = time.time()
        with self.lock:
            detected_handedness = set()
            for h in hands_list:
                h_name = h.get("handedness", "Right")
                detected_handedness.add(h_name)
                state = self.hands.get(h_name)
                if not state:
                    state = HandState(h_name)
                    self.hands[h_name] = state

                # Map normalized landmarks (0..1) to screen coordinates
                raw_lms = h.get("landmarks", [])
                screen_lms = []
                for lm in raw_lms:
                    # Gentle margin expansion for comfortable range of motion
                    # Camera center [0.10, 0.90] maps to full screen
                    sx = min(max(0.0, (lm[0] - 0.08) / 0.84), 1.0) * self.screen_w
                    sy = min(max(0.0, (lm[1] - 0.08) / 0.84), 1.0) * self.screen_h
                    screen_lms.append((sx, sy))

                state.raw_landmarks = screen_lms
                state.target_opacity = 1.0
                state.is_pinch = h.get("pinch_dist", 1.0) < 0.32
                state.is_two_finger = h.get("is_two_finger", False)
                state.is_open_palm = h.get("is_open_palm", False)

                if active_badges and h_name in active_badges:
                    state.action_badge = active_badges[h_name]
                    state.badge_time = now
                elif active_badges and "all" in active_badges:
                    state.action_badge = active_badges["all"]
                    state.badge_time = now

            # Hands not detected fade out
            for h_name, state in self.hands.items():
                if h_name not in detected_handedness:
                    state.target_opacity = 0.0

            self.last_active_time = now

    def on_tick(self):
        if not self.is_running:
            return False

        needs_redraw = False
        with self.lock:
            for state in self.hands.values():
                # Smooth opacity transition (Fade In / Fade Out)
                if state.target_opacity > state.opacity:
                    state.opacity = min(1.0, state.opacity + 0.12)
                    needs_redraw = True
                elif state.target_opacity < state.opacity:
                    state.opacity = max(0.0, state.opacity - 0.08)
                    if state.opacity > 0.01:
                        needs_redraw = True

                # Smooth landmarks with EMA filter
                if state.raw_landmarks and state.opacity > 0.01:
                    needs_redraw = True
                    if state.smooth_landmarks is None or len(state.smooth_landmarks) != len(state.raw_landmarks):
                        state.smooth_landmarks = list(state.raw_landmarks)
                    else:
                        alpha = 0.42 # smooth responsiveness
                        smoothed = []
                        for i in range(len(state.raw_landmarks)):
                            rx, ry = state.raw_landmarks[i]
                            sx, sy = state.smooth_landmarks[i]
                            nx = alpha * rx + (1.0 - alpha) * sx
                            ny = alpha * ry + (1.0 - alpha) * sy
                            smoothed.append((nx, ny))
                        state.smooth_landmarks = smoothed

                state.pulse_phase = (state.pulse_phase + 0.08) % (2 * math.pi)

        if needs_redraw:
            self.win.queue_draw()

        return True

    def on_draw(self, widget, cr):
        # 1. Clear transparent background
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()

        # 2. Draw holographic hands with OVER operator
        cr.set_operator(cairo.OPERATOR_OVER)

        with self.lock:
            for state in self.hands.values():
                if state.opacity > 0.02 and state.smooth_landmarks and len(state.smooth_landmarks) >= 21:
                    self._draw_hologram_hand(cr, state)

        return False

    def _draw_hologram_hand(self, cr, state: HandState):
        lm = state.smooth_landmarks
        op = state.opacity

        # Dynamic scale based on wrist-to-middle distance
        wrist = lm[0]
        middle_mcp = lm[9]
        hand_scale = math.hypot(wrist[0] - middle_mcp[0], wrist[1] - middle_mcp[1])
        base_w = max(hand_scale * 0.13, 14.0)

        fingers_data = [
            ([1, 2, 3, 4], [base_w * 1.10, base_w * 0.95, base_w * 0.85, base_w * 0.70]), # Thumb
            ([5, 6, 7, 8], [base_w * 1.05, base_w * 0.90, base_w * 0.80, base_w * 0.65]), # Index
            ([9, 10, 11, 12], [base_w * 1.05, base_w * 0.90, base_w * 0.80, base_w * 0.65]), # Middle
            ([13, 14, 15, 16], [base_w * 0.95, base_w * 0.85, base_w * 0.75, base_w * 0.60]), # Ring
            ([17, 18, 19, 20], [base_w * 0.85, base_w * 0.75, base_w * 0.65, base_w * 0.55]), # Pinky
        ]

        # ── 1. Forearm Fade Gradient ─────────────────────────────────
        if wrist[1] < self.screen_h:
            cr.new_path()
            fw = base_w * 2.2
            cr.move_to(wrist[0] - fw, wrist[1] + 5)
            cr.line_to(wrist[0] + fw, wrist[1] + 5)
            cr.line_to(wrist[0] + fw * 1.8, self.screen_h)
            cr.line_to(wrist[0] - fw * 1.8, self.screen_h)
            cr.close_path()

            pat = cairo.LinearGradient(wrist[0], wrist[1], wrist[0], self.screen_h)
            pat.add_color_stop_rgba(0.0, 0.85, 0.93, 1.0, 0.20 * op)
            pat.add_color_stop_rgba(1.0, 0.85, 0.93, 1.0, 0.0)
            cr.set_source(pat)
            cr.fill_preserve()

            pat_stroke = cairo.LinearGradient(wrist[0], wrist[1], wrist[0], self.screen_h)
            pat_stroke.add_color_stop_rgba(0.0, 0.95, 0.98, 1.0, 0.80 * op)
            pat_stroke.add_color_stop_rgba(1.0, 0.95, 0.98, 1.0, 0.0)
            cr.set_source(pat_stroke)
            cr.set_line_width(2.0)
            cr.stroke()

        # ── 2. Helper to trace smooth finger ribbon ─────────────────
        def draw_finger_smooth(pts, widths):
            # Extend base slightly towards wrist lm[0] for seamless palm blend
            p_base = pts[0]
            to_wrist = (wrist[0] - p_base[0], wrist[1] - p_base[1])
            d_w = math.hypot(*to_wrist) or 1.0
            extended_base = (p_base[0] + to_wrist[0] / d_w * (base_w * 0.7), p_base[1] + to_wrist[1] / d_w * (base_w * 0.7))
            all_pts = [extended_base] + pts
            all_widths = [widths[0] * 1.08] + widths

            n = len(all_pts)
            left_pts, right_pts = [], []
            for i in range(n):
                if i == 0:
                    dx = all_pts[1][0] - all_pts[0][0]
                    dy = all_pts[1][1] - all_pts[0][1]
                elif i == n - 1:
                    dx = all_pts[n-1][0] - all_pts[n-2][0]
                    dy = all_pts[n-1][1] - all_pts[n-2][1]
                else:
                    dx = all_pts[i+1][0] - all_pts[i-1][0]
                    dy = all_pts[i+1][1] - all_pts[i-1][1]
                dist = math.hypot(dx, dy) or 1e-4
                nx = -dy / dist
                ny = dx / dist
                w = all_widths[i]
                left_pts.append((all_pts[i][0] + nx * w, all_pts[i][1] + ny * w))
                right_pts.append((all_pts[i][0] - nx * w, all_pts[i][1] - ny * w))

            cr.new_path()
            cr.move_to(left_pts[0][0], left_pts[0][1])
            for p in left_pts[1:]:
                cr.line_to(p[0], p[1])

            tip = all_pts[-1]
            dx = all_pts[-1][0] - all_pts[-2][0]
            dy = all_pts[-1][1] - all_pts[-2][1]
            ang = math.atan2(dy, dx)
            w_tip = all_widths[-1]
            cr.arc_negative(tip[0], tip[1], w_tip, ang + math.pi / 2, ang - math.pi / 2)

            for p in reversed(right_pts):
                cr.line_to(p[0], p[1])
            cr.close_path()

        def trace_palm():
            palm_pts = [0, 1, 5, 9, 13, 17]
            cr.new_path()
            cr.move_to(lm[palm_pts[0]][0], lm[palm_pts[0]][1])
            for idx in palm_pts[1:]:
                cr.line_to(lm[idx][0], lm[idx][1])
            cr.close_path()

        # ── 3. Translucent Body Fill (X-ray Frosted Glass) ─────────────
        cr.set_source_rgba(0.85, 0.93, 1.0, 0.20 * op)
        trace_palm()
        cr.fill()
        for f_lms, widths in fingers_data:
            draw_finger_smooth([lm[i] for i in f_lms], widths)
            cr.fill()

        # ── 4. Outer Soft Neon Glow (Cyan/Blue Aura) ───────────────────
        cr.set_source_rgba(0.55, 0.85, 1.0, 0.32 * op)
        cr.set_line_width(6.5)
        trace_palm()
        cr.stroke()
        for f_lms, widths in fingers_data:
            draw_finger_smooth([lm[i] for i in f_lms], widths)
            cr.stroke()

        # ── 5. Crisp Luminous White Silhouette Border ─────────────────
        cr.set_source_rgba(0.96, 0.98, 1.0, 0.95 * op)
        cr.set_line_width(2.2)
        trace_palm()
        cr.stroke()
        for f_lms, widths in fingers_data:
            draw_finger_smooth([lm[i] for i in f_lms], widths)
            cr.stroke()

        # ── 6. Internal Skeletal Rays (Bone Marrow Glow) ──────────────
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.50 * op)
        cr.set_line_width(1.6)
        for f_lms, _ in fingers_data:
            cr.new_path()
            cr.move_to(lm[f_lms[0]][0], lm[f_lms[0]][1])
            for idx in f_lms[1:]:
                cr.line_to(lm[idx][0], lm[idx][1])
            cr.stroke()

        # Joint Nodes
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.70 * op)
        for i in range(21):
            cr.arc(lm[i][0], lm[i][1], 2.8, 0, 2 * math.pi)
            cr.fill()

        # ── 7. Interactive Reticle & HUD Badges ─────────────────────────
        ix, iy = lm[8] # Index tip
        tx, ty = lm[4] # Thumb tip

        # If pinching (Index + Thumb)
        if state.is_pinch:
            # Electric cyan arc linking thumb and index
            cr.set_source_rgba(0.0, 0.95, 1.0, 0.90 * op)
            cr.set_line_width(2.5)
            cr.new_path()
            cr.move_to(tx, ty)
            cr.line_to(ix, iy)
            cr.stroke()

            # Contracted active ring
            pinch_cx = (ix + tx) / 2.0
            pinch_cy = (iy + ty) / 2.0
            pulse_r = 10.0 + 2.0 * math.sin(state.pulse_phase * 2)

            cr.set_source_rgba(0.0, 0.95, 1.0, 0.95 * op)
            cr.set_line_width(2.5)
            cr.arc(pinch_cx, pinch_cy, pulse_r, 0, 2 * math.pi)
            cr.stroke()

            # Solid glowing core
            cr.arc(pinch_cx, pinch_cy, 4.5, 0, 2 * math.pi)
            cr.fill()

            self._draw_hud_badge(cr, pinch_cx, pinch_cy - 24, "CLICK / DRAG", (0.0, 0.95, 1.0), op)

        elif state.is_two_finger:
            # Two finger scroll reticle
            mx, my = lm[12]
            sc_x = (ix + mx) / 2.0
            sc_y = (iy + my) / 2.0
            cr.set_source_rgba(0.2, 0.85, 1.0, 0.85 * op)
            cr.set_line_width(2.0)
            cr.arc(sc_x, sc_y, 16.0, 0, 2 * math.pi)
            cr.stroke()
            self._draw_hud_badge(cr, sc_x, sc_y - 24, "▲ SCROLL ▼", (0.2, 0.85, 1.0), op)

        elif state.is_open_palm:
            # Ethereal holographic ring in palm center
            px, py = ((lm[0][0] + lm[5][0] + lm[17][0]) / 3.0, (lm[0][1] + lm[5][1] + lm[17][1]) / 3.0)
            pr = hand_scale * 0.45
            cr.set_source_rgba(0.1, 0.9, 0.5, 0.75 * op)
            cr.set_line_width(2.0)
            cr.arc(px, py, pr, 0, 2 * math.pi)
            cr.stroke()

            # Animated rotating dashed arc
            cr.set_dash([8, 8], state.pulse_phase * 15)
            cr.arc(px, py, pr * 0.80, 0, 2 * math.pi)
            cr.stroke()
            cr.set_dash([], 0)

            self._draw_hud_badge(cr, px, py - pr - 14, "🖐 OVERVIEW", (0.2, 1.0, 0.6), op)

        else:
            # Sleek Air Mouse Hover Reticle
            reticle_r = 16.0 + 1.5 * math.sin(state.pulse_phase)
            cr.set_source_rgba(0.15, 0.90, 1.0, 0.85 * op)
            cr.set_line_width(2.0)
            cr.arc(ix, iy, reticle_r, 0, 2 * math.pi)
            cr.stroke()

            cr.set_line_width(1.2)
            cr.arc(ix, iy, 9.0, 0, 2 * math.pi)
            cr.stroke()

            # Crosshair pips
            for ang in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
                a = ang + state.pulse_phase * 0.5
                x1 = ix + 12 * math.cos(a)
                y1 = iy + 12 * math.sin(a)
                x2 = ix + 20 * math.cos(a)
                y2 = iy + 20 * math.sin(a)
                cr.move_to(x1, y1)
                cr.line_to(x2, y2)
            cr.stroke()

            # Center target pip
            cr.arc(ix, iy, 3.2, 0, 2 * math.pi)
            cr.fill()

        # Dynamic action badge if triggered recently (e.g. SWIPE, VOLUME, MEDIA)
        now = time.time()
        if state.action_badge and (now - state.badge_time < 0.85):
            badge_fade = min(1.0, (0.85 - (now - state.badge_time)) / 0.3)
            self._draw_hud_badge(cr, ix + 40, iy - 10, state.action_badge, (1.0, 0.85, 0.2), op * badge_fade)

    def _draw_hud_badge(self, cr, x, y, text, color, alpha):
        """Draws a sleek frosted pill badge with glowing text"""
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(12)
        ext = cr.text_extents(text)

        pw = ext.width + 16
        ph = ext.height + 10
        px = x - pw / 2
        py = y - ph / 2

        # Frosted pill background
        cr.new_path()
        cr.arc(px + ph/2, py + ph/2, ph/2, math.pi/2, 3*math.pi/2)
        cr.arc(px + pw - ph/2, py + ph/2, ph/2, -math.pi/2, math.pi/2)
        cr.close_path()

        cr.set_source_rgba(0.05, 0.08, 0.12, 0.65 * alpha)
        cr.fill_preserve()
        cr.set_source_rgba(color[0], color[1], color[2], 0.70 * alpha)
        cr.set_line_width(1.4)
        cr.stroke()

        # Luminous text
        cr.set_source_rgba(color[0], color[1], color[2], 0.95 * alpha)
        cr.move_to(px + 8, py + ph/2 + ext.height/2 - 1)
        cr.show_text(text)

    def on_destroy(self, widget):
        self.is_running = False

    def close(self):
        self.is_running = False
        GLib.idle_add(self.win.destroy)
