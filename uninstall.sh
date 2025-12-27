#!/bin/bash

# Battery Manager Pro - Uninstallation Script

set -e

echo "======================================"
echo "Battery Manager Pro - Uninstallation"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: Please run as root (use sudo)"
    exit 1
fi

echo "Removing Battery Manager Pro..."
echo ""

# Remove installation directory
echo "[1/4] Removing installation files..."
rm -rf /opt/linuxbat-manager

# Remove launcher script
echo "[2/4] Removing launcher..."
rm -f /usr/local/bin/linuxbat-manager

# Remove desktop entry
echo "[3/4] Removing desktop entry..."
rm -f /usr/share/applications/linuxbat-manager.desktop

# Remove icon
echo "[4/4] Removing icon..."
rm -f /usr/share/icons/hicolor/256x256/apps/linuxbat-manager.png

# Update caches
update-desktop-database /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true

echo ""
echo "======================================"
echo "Uninstallation completed successfully!"
echo "======================================"
echo ""
