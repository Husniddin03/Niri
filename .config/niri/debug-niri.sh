#!/bin/bash
# Debug script for Niri multi-monitor issues

echo "=== Niri Debug Information ==="
echo ""

echo "1. Current Niri outputs:"
niri msg outputs
echo ""

echo "2. DRM/KMS state:"
echo "HDMI-A-2 status: $(cat /sys/class/drm/card1-HDMI-A-2/status)"
echo "HDMI-A-2 enabled: $(cat /sys/class/drm/card1-HDMI-A-2/enabled)"
echo "eDP-1 enabled: $(cat /sys/class/drm/card0-eDP-1/enabled)"
echo ""

echo "3. Available DRM devices:"
ls -la /sys/class/drm/
echo ""

echo "4. NVIDIA module status:"
lsmod | grep nvidia
echo ""

echo "5. Kernel parameters:"
cat /proc/cmdline
echo ""

echo "6. GPU rendering devices:"
ls -la /dev/dri/
echo ""

echo "7. Try to force enable HDMI output:"
echo "You can try running: niri msg action power-on-monitors"
echo ""

echo "8. Check for VRAM allocation issues:"
nvidia-smi
echo ""

echo "=== End of debug information ==="