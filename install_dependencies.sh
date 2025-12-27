#!/bin/bash
# Battery Manager Pro - System Dependencies Installation Script
# Run with: sudo bash install_dependencies.sh

echo "======================================"
echo "Battery Manager Pro - Dependencies"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run with sudo: sudo bash install_dependencies.sh"
    exit 1
fi

echo "📦 Installing system packages..."
apt-get update
apt-get install -y \
    python3-pip \
    python3-pyqt6 \
    libxcb-cursor0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0

echo ""
echo "✅ System packages installed successfully!"
echo ""
echo "📦 Installing Python packages..."
sudo -u $SUDO_USER pip3 install --break-system-packages PyQt6 pyqtgraph psutil

echo ""
echo "======================================"
echo "✅ Installation complete!"
echo "======================================"
echo ""
echo "You can now run: python3 main.py"
echo ""
