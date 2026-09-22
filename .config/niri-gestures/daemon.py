#!/usr/bin/env python3
import os
import sys
import time
import signal
import argparse
import threading
import traceback
import cv2

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GLib

from core.tracker import VisionTracker
from core.gesture_engine import GestureEngine
from core.plugin_manager import PluginManager
from core.overlay import HolographicHandOverlay

PID_FILE = "/tmp/niri-gestures.pid"

def cleanup():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                saved_pid = int(f.read().strip())
            if saved_pid == os.getpid():
                os.remove(PID_FILE)
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="Niri Holographic Hand Gestures Daemon")
    parser.add_argument("--preview", action="store_true", help="Show OpenCV camera preview window")
    parser.add_argument("--no-overlay", action="store_true", help="Disable transparent on-screen hand overlay")
    args = parser.parse_args()

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    hand_model_path = os.path.join(PROJECT_DIR, "models", "gesture_recognizer.task")
    face_model_path = os.path.join(PROJECT_DIR, "models", "face_landmarker.task")
    config_path = os.path.join(PROJECT_DIR, "config.json")
    plugins_dir = os.path.join(PROJECT_DIR, "plugins")

    plugin_manager = PluginManager(plugins_dir, config_path)
    plugin_manager.discover_and_load()

    mode = plugin_manager.config.get("tracking_mode", "hand")
    camera_cfg = plugin_manager.config.get("camera", {})
    cam_index = int(camera_cfg.get("index", 0))
    target_fps = int(camera_cfg.get("fps", 30))

    overlay_cfg = plugin_manager.config.get("overlay", {})
    use_overlay = not args.no_overlay and overlay_cfg.get("enabled", True)

    tracker = VisionTracker(
        hand_model_path,
        face_model_path,
        mode=mode,
        camera_index=cam_index,
        target_fps=target_fps,
    )
    engine = GestureEngine()

    display = Gdk.Display.get_default()
    monitor = (display.get_primary_monitor() or (display.get_monitor(0) if display and display.get_n_monitors() > 0 else None)) if display else None
    if monitor:
        geom = monitor.get_geometry()
        screen_w, screen_h = geom.width, geom.height
    else:
        screen_w, screen_h = 1920, 1080

    overlay = None
    if use_overlay:
        try:
            overlay = HolographicHandOverlay(screen_w=screen_w, screen_h=screen_h)
            overlay.show()
            print(f"[Daemon] Transparent Holographic Hand Overlay active ({screen_w}x{screen_h})", flush=True)
        except Exception as e:
            print(f"[Daemon] Warning: Could not initialize GtkLayerShell overlay: {e}", flush=True)
            overlay = None

    stop_event = threading.Event()

    def signal_handler(signum, frame):
        stop_event.set()
        def quit_gtk():
            if worker_thread.is_alive():
                worker_thread.join(timeout=1.2)
            if overlay:
                overlay.close()
            tracker.close()
            cleanup()
            Gtk.main_quit()
            return False
        GLib.idle_add(quit_gtk)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    frame_delay = 1.0 / target_fps
    print(f"[Daemon] Niri Gestures running (Mode: '{mode}', PID: {os.getpid()}). Target FPS: {target_fps}", flush=True)

    def vision_loop():
        try:
            while not stop_event.is_set():
                t0 = time.time()
                try:
                    frame, event = tracker.read_frame()
                except Exception:
                    break

                if stop_event.is_set():
                    break

                if frame is None:
                    if overlay:
                        overlay.update_hands_data([])
                    time.sleep(0.04)
                    continue

                active_badges = {}
                if event:
                    event["screen_w"] = screen_w
                    event["screen_h"] = screen_h
                    event = engine.process(event)
                    plugin_manager.dispatch(event)

                    # Determine feedback badges for HUD
                    dyn = event.get("dynamic_action")
                    gest = event.get("gesture")
                    if dyn == "swipe_left":
                        active_badges["all"] = "◀ WINDOW NEXT"
                    elif dyn == "swipe_right":
                        active_badges["all"] = "WINDOW PREV ▶"
                    elif dyn == "swipe_up":
                        active_badges["all"] = "▲ WORKSPACE UP"
                    elif dyn == "swipe_down":
                        active_badges["all"] = "▼ WORKSPACE DOWN"
                    elif gest == "Thumb_Up":
                        active_badges["all"] = "🔊 VOL +"
                    elif gest == "Thumb_Down":
                        active_badges["all"] = "🔉 VOL -"
                    elif gest == "Victory":
                        active_badges["all"] = "⏯ PLAY/PAUSE"
                    elif gest == "ILoveYou":
                        active_badges["all"] = "⏭ NEXT TRACK"

                    hands_list = event.get("hands", [])
                    if overlay:
                        overlay.update_hands_data(hands_list, active_badges)
                else:
                    if overlay:
                        overlay.update_hands_data([])

                if args.preview:
                    h, w, _ = frame.shape
                    if event and "landmarks" in event:
                        g_text = f"Hand: {event.get('gesture', 'None')} ({event.get('confidence', 0.0):.2f})"
                        if event.get("dynamic_action"):
                            g_text += f" | {event['dynamic_action'].upper()}"
                        cv2.putText(frame, g_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                        if "index_tip" in event:
                            ix, iy = int(event["index_tip"][0] * w), int(event["index_tip"][1] * h)
                            cv2.circle(frame, (ix, iy), 8, (0, 255, 0), -1)

                    cv2.imshow("Niri Gestures Debug Preview", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        stop_event.set()
                        GLib.idle_add(Gtk.main_quit)
                        break

                elapsed = time.time() - t0
                sleep_time = frame_delay - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            if not stop_event.is_set():
                print(f"[Daemon] Vision thread error: {e}", flush=True)
                traceback.print_exc()
        finally:
            tracker.close()
            if args.preview:
                cv2.destroyAllWindows()

    worker_thread = threading.Thread(target=vision_loop, daemon=True)
    worker_thread.start()

    # GTK main event loop runs on main thread
    try:
        Gtk.main()
    except KeyboardInterrupt:
        stop_event.set()
        if worker_thread.is_alive():
            worker_thread.join(timeout=1.0)
        cleanup()
    finally:
        stop_event.set()
        cleanup()
        print("[Daemon] Stopped cleanly.", flush=True)

if __name__ == "__main__":
    main()
