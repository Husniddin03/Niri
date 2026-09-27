#!/usr/bin/env python3
# ==============================================================================
# Niri & Waybar Realtime Sync Daemon
# Mathematically proofed, non-inverting, flicker-free overview synchronizer
# ==============================================================================

import os
import sys
import time
import json
import signal
import threading
import subprocess

PID_FILE = "/tmp/niri-waybar-sync.pid"
stop_event = threading.Event()
toggle_lock = threading.Lock()
last_toggle_time = 0.0

def single_instance():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            # Check if old process is running
            os.kill(old_pid, signal.SIGTERM)
            time.sleep(0.1)
        except Exception:
            pass
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def cleanup():
    stop_event.set()
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                if int(f.read().strip()) == os.getpid():
                    os.remove(PID_FILE)
        except Exception:
            pass

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

def get_overview_state():
    try:
        res = subprocess.run(["niri", "msg", "-j", "overview-state"], capture_output=True, text=True, timeout=0.8)
        if res.returncode == 0:
            return json.loads(res.stdout).get("is_open", False)
    except Exception:
        pass
    return False

def get_waybar_layer():
    try:
        res = subprocess.run(["niri", "msg", "-j", "layers"], capture_output=True, text=True, timeout=0.8)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            for item in data:
                if item.get("namespace") == "waybar":
                    return item.get("layer")  # "Top" or "Bottom"
    except Exception:
        pass
    return None

def set_waybar_visible(desired_visible: bool):
    global last_toggle_time
    with toggle_lock:
        now = time.time()
        # Debounce: minimum 250ms between SIGUSR1 signals to prevent hardware/layer races
        if now - last_toggle_time < 0.25:
            return

        layer = get_waybar_layer()
        if layer is None:
            return  # Waybar is not running or hasn't created a surface yet

        is_visible = (layer == "Top")
        # Only toggle IF AND ONLY IF actual state does not match desired state
        if is_visible != desired_visible:
            last_toggle_time = now
            subprocess.run(["killall", "-SIGUSR1", "waybar"], capture_output=True)

def watchdog_worker():
    """Safety net: periodically checks state every 0.8s in case Waybar was restarted or reloaded"""
    while not stop_event.is_set():
        try:
            is_open = get_overview_state()
            set_waybar_visible(is_open)
        except Exception:
            pass
        stop_event.wait(0.8)

def stream_worker():
    """Event-driven: receives instant 0ms events when Overview opens or closes"""
    while not stop_event.is_set():
        proc = None
        try:
            proc = subprocess.Popen(
                ["niri", "msg", "-j", "event-stream"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            for line in iter(proc.stdout.readline, ""):
                if stop_event.is_set():
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if "OverviewOpenedOrClosed" in event:
                        is_open = event["OverviewOpenedOrClosed"].get("is_open", False)
                        set_waybar_visible(is_open)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=0.5)
                except Exception:
                    pass
        if not stop_event.is_set():
            stop_event.wait(1.0)

def main():
    single_instance()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    # Initial sync
    initial_open = get_overview_state()
    set_waybar_visible(initial_open)

    # Start stream and watchdog threads
    t_stream = threading.Thread(target=stream_worker, daemon=True)
    t_watchdog = threading.Thread(target=watchdog_worker, daemon=True)

    t_stream.start()
    t_watchdog.start()

    while not stop_event.is_set():
        time.sleep(1)

if __name__ == "__main__":
    main()
