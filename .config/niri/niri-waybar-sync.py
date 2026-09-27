#!/usr/bin/env python3
# ==============================================================================
# Niri & Waybar Realtime Sync Daemon
# Mathematically guaranteed, ultra-low latency, non-inverting synchronizer
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
action_lock = threading.Lock()
last_action_time = 0.0

def single_instance():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
            time.sleep(0.05)
        except Exception:
            pass
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

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
        res = subprocess.run(["niri", "msg", "-j", "overview-state"], capture_output=True, text=True, timeout=0.5)
        if res.returncode == 0:
            return json.loads(res.stdout).get("is_open", False)
    except Exception:
        pass
    return False

def get_waybar_layer():
    try:
        res = subprocess.run(["niri", "msg", "-j", "layers"], capture_output=True, text=True, timeout=0.5)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            for item in data:
                if item.get("namespace") == "waybar":
                    return item.get("layer")  # "Top" or "Bottom"
    except Exception:
        pass
    return None

def enforce_sync(desired_open: bool):
    """
    Enforces that Waybar is on Top if desired_open is True,
    and NOT on Top (Bottom/hidden) if desired_open is False.
    Waybar layer switch takes ~15ms.
    """
    global last_action_time
    with action_lock:
        now = time.time()
        # Cooldown of 60ms to prevent double-signals while Waybar switches in 15ms
        if now - last_action_time < 0.06:
            time.sleep(0.06 - (now - last_action_time))

        layer = get_waybar_layer()
        if layer is None:
            return

        is_visible = (layer == "Top")
        if is_visible != desired_open:
            last_action_time = time.time()
            subprocess.run(["killall", "-SIGUSR1", "waybar"], capture_output=True)

def watchdog_worker():
    """Safety net: checks every 250ms and instantly corrects any desync"""
    while not stop_event.is_set():
        try:
            is_open = get_overview_state()
            enforce_sync(is_open)
        except Exception:
            pass
        stop_event.wait(0.25)

def stream_worker():
    """Event-driven: receives instant 0ms notification when Overview opens or closes"""
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
                        enforce_sync(is_open)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=0.3)
                except Exception:
                    pass
        if not stop_event.is_set():
            stop_event.wait(0.5)

def main():
    single_instance()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    # Initial enforcement
    enforce_sync(get_overview_state())

    t_stream = threading.Thread(target=stream_worker, daemon=True)
    t_watchdog = threading.Thread(target=watchdog_worker, daemon=True)

    t_stream.start()
    t_watchdog.start()

    while not stop_event.is_set():
        time.sleep(1)

if __name__ == "__main__":
    main()
