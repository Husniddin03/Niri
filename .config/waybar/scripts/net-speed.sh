#!/usr/bin/env python3
import time
import os
import sys

CACHE = "/dev/shm/net_speed.cache"

def get_stats():
    try:
        with open("/proc/net/dev", "r") as f:
            lines = f.readlines()
        rx_total = 0
        tx_total = 0
        for line in lines[2:]:
            parts = line.split()
            if len(parts) >= 10:
                dev = parts[0].strip(":")
                if dev != "lo":
                    rx_total += int(parts[1])
                    tx_total += int(parts[9])
        return rx_total, tx_total, time.time()
    except Exception:
        return 0, 0, time.time()

def fmt(b_sec):
    if b_sec < 1024:
        return f"{int(b_sec)} B/s"
    elif b_sec < 1048576:
        return f"{b_sec/1024:.1f} KB/s"
    else:
        return f"{b_sec/1048576:.1f} MB/s"

rx2, tx2, t2 = get_stats()

if os.path.exists(CACHE):
    try:
        with open(CACHE, "r") as f:
            content = f.read().split()
            rx1, tx1, t1 = float(content[0]), float(content[1]), float(content[2])
        dt = max(0.2, t2 - t1)
        rx_speed = max(0.0, (rx2 - rx1) / dt)
        tx_speed = max(0.0, (tx2 - tx1) / dt)
    except Exception:
        rx_speed, tx_speed = 0.0, 0.0
else:
    rx_speed, tx_speed = 0.0, 0.0

try:
    with open(CACHE, "w") as f:
        f.write(f"{rx2} {tx2} {t2}\n")
except Exception:
    pass

print(f" {fmt(tx_speed)}  {fmt(rx_speed)}")