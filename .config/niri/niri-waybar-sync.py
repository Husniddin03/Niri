#!/usr/bin/env python3
# ==============================================================================
# Niri & Waybar Realtime Sync Daemon
# Strictly Idempotent, Zero-Flicker, Non-Inverting Event Synchronizer
# ==============================================================================

import os
import sys
import time
import json
import fcntl
import signal
import threading
import subprocess

LOCK_FILE = f"/run/user/{os.getuid()}/niri-waybar-sync.lock"
lock_fd = None
stop_event = threading.Event()
action_lock = threading.Lock()

def acquire_single_instance():
    global lock_fd
    try:
        lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
    except (IOError, OSError):
        # Another instance is already running
        sys.exit(0)

def cleanup():
    stop_event.set()
    global lock_fd
    if lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            os.remove(LOCK_FILE)
        except Exception:
            pass

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

def get_overview_state() -> bool:
    try:
        res = subprocess.run(["niri", "msg", "-j", "overview-state"], capture_output=True, text=True, timeout=0.4)
        if res.returncode == 0:
            return json.loads(res.stdout).get("is_open", False)
    except Exception:
        pass
    return False

def get_waybar_layer():
    try:
        res = subprocess.run(["niri", "msg", "-j", "layers"], capture_output=True, text=True, timeout=0.4)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            for item in data:
                if item.get("namespace") == "waybar":
                    return item.get("layer")  # "Top" or "Bottom"
    except Exception:
        pass
    return None

def enforce_target_layer(target_layer: str, max_wait: float = 0.5) -> bool:
    """
    STRICTLY IDEMPOTENT:
    If Waybar is already at target_layer, does NOTHING (sends 0 signals).
    If Waybar is not at target_layer, sends ONE SIGUSR1 and waits until
    niri reports the transition is complete.
    """
    with action_lock:
        current = get_waybar_layer()
        if current is None:
            return False  # Waybar not running or no surface yet
        if current == target_layer:
            return True   # Already in desired state, do nothing!

        # Send exactly one toggle signal
        subprocess.run(["killall", "-SIGUSR1", "waybar"], capture_output=True)

        # Wait until Waybar confirms new layer
        t0 = time.time()
        while time.time() - t0 < max_wait:
            if get_waybar_layer() == target_layer:
                return True
            time.sleep(0.015)

        return (get_waybar_layer() == target_layer)

def sync_with_overview(is_open: bool):
    target = "Top" if is_open else "Bottom"
    enforce_target_layer(target)

def stream_worker():
    """Event-driven: receives instant 0ms events from Niri IPC"""
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
                        sync_with_overview(is_open)
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
            # Reconnect sync
            sync_with_overview(get_overview_state())

def main():
    acquire_single_instance()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    # Initial wait for Waybar to launch and create surface (up to 3 seconds)
    for _ in range(30):
        if get_waybar_layer() is not None:
            break
        time.sleep(0.1)

    # Enforce initial state (Bottom if overview is closed)
    sync_with_overview(get_overview_state())

    # Start event stream
    t_stream = threading.Thread(target=stream_worker, daemon=True)
    t_stream.start()

    while not stop_event.is_set():
        time.sleep(1)

if __name__ == "__main__":
    main()
