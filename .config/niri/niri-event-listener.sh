#!/usr/bin/env bash
# ==============================================================================
# Niri & Waybar Event Listener Launcher
# Delegates to niri-waybar-sync.py for robust, non-inverting synchronization
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/niri-waybar-sync.py"