#!/usr/bin/env bash

# Disable accessibility bridge for instant startup (eliminates AT-SPI D-Bus delays)
export NO_AT_BRIDGE=1
export GTK_A11Y=none

# Toggle if running
if pgrep -f "smart_launcher.py" >/dev/null; then
    pkill -f "smart_launcher.py"
    rm -f /tmp/smart-launcher.pid
    exit 0
fi

# Ensure icons and data directories
export XDG_DATA_DIRS="/usr/share:/usr/local/share:$HOME/.local/share:$HOME/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:${XDG_DATA_DIRS}"

exec python3 /home/husniddin/.config/wofi/launcher/smart_launcher.py "$@"
