#!/usr/bin/env python3
import os
import sys
import time
import signal
import argparse
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

from core.tracker import VisionTracker
from core.gesture_engine import GestureEngine
from core.plugin_manager import PluginManager

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

def signal_handler(signum, frame):
    cleanup()
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Niri Hand & Face Gestures Daemon")
    parser.add_argument("--preview", action="store_true", help="Show live camera preview window")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    hand_model_path = os.path.join(PROJECT_DIR, "models", "gesture_recognizer.task")
    face_model_path = os.path.join(PROJECT_DIR, "models", "face_landmarker.task")
    config_path = os.path.join(PROJECT_DIR, "config.json")
    plugins_dir = os.path.join(PROJECT_DIR, "plugins")

    plugin_manager = PluginManager(plugins_dir, config_path)
    plugin_manager.discover_and_load()

    mode = plugin_manager.config.get("tracking_mode", "head_eye")
    camera_cfg = plugin_manager.config.get("camera", {})
    cam_index = int(camera_cfg.get("index", 0))
    target_fps = int(camera_cfg.get("fps", 25))

    tracker = VisionTracker(hand_model_path, face_model_path, mode=mode, camera_index=cam_index, target_fps=target_fps)
    engine = GestureEngine()

    frame_delay = 1.0 / target_fps
    print(f"[Daemon] Niri Gestures running (Mode: '{mode}', PID: {os.getpid()}). Target FPS: {target_fps}", flush=True)

    try:
        while True:
            start_time = time.time()
            frame, event = tracker.read_frame()

            if frame is None:
                time.sleep(0.05)
                continue

            if event:
                event = engine.process(event)
                plugin_manager.dispatch(event)

            if args.preview:
                h, w, _ = frame.shape

                # 1. Face & Eye Overlay
                if event and "face" in event:
                    face = event["face"]
                    nose = face["nose_tip"]
                    nx, ny = int(nose[0] * w), int(nose[1] * h)
                    # Nose tracking pointer dot
                    cv2.circle(frame, (nx, ny), 7, (255, 100, 0), -1)
                    cv2.putText(frame, "Head Pointer", (nx + 10, ny), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1)

                    bl = face["blink_left"]
                    br = face["blink_right"]
                    col_l = (0, 0, 255) if bl > 0.55 else (0, 255, 0)
                    col_r = (0, 0, 255) if br > 0.55 else (0, 255, 0)
                    txt_l = f"L Eye: {bl:.2f} {'[WINK]' if (bl > 0.58 and br < 0.35) else ''}"
                    txt_r = f"R Eye: {br:.2f} {'[WINK]' if (br > 0.58 and bl < 0.35) else ''}"
                    cv2.putText(frame, txt_l, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col_l, 2)
                    cv2.putText(frame, txt_r, (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col_r, 2)

                # 2. Hand Overlay
                if event and "landmarks" in event:
                    g_text = f"Hand: {event.get('gesture', 'None')} ({event.get('confidence', 0.0):.2f})"
                    if event.get("dynamic_action"):
                        g_text += f" | {event['dynamic_action'].upper()}"
                    cv2.putText(frame, g_text, (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                    if "index_tip" in event:
                        ix, iy = int(event["index_tip"][0] * w), int(event["index_tip"][1] * h)
                        cv2.circle(frame, (ix, iy), 8, (0, 255, 0), -1)

                cv2.imshow("Niri Gestures Preview (Press 'q' to quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            elapsed = time.time() - start_time
            sleep_time = frame_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except Exception as e:
        print(f"[Daemon] Error: {e}", flush=True)
        traceback.print_exc()
    finally:
        tracker.stop_camera()
        if args.preview:
            cv2.destroyAllWindows()
        cleanup()
        print("[Daemon] Stopped cleanly.", flush=True)

if __name__ == "__main__":
    main()
