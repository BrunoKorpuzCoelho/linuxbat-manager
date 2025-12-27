#!/bin/bash

# Battery Manager Pro - Installation Script
# This script installs the application system-wide

set -e

echo "======================================"
echo "Battery Manager Pro - Installation"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: Please run as root (use sudo)"
    exit 1
fi

# Get the actual user who ran sudo
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing Battery Manager Pro..."
echo ""

# 1. Install system dependencies
echo "[1/6] Installing system dependencies..."
apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libxcb-cursor0 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    libgl1-mesa-glx \
    policykit-1

# 2. Create installation directory
echo "[2/6] Creating installation directory..."
mkdir -p /opt/linuxbat-manager
cp -r ./* /opt/linuxbat-manager/
cd /opt/linuxbat-manager

# 3. Create virtual environment and install Python dependencies
echo "[3/6] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create launcher script
echo "[4/6] Creating launcher script..."
cat > /usr/local/bin/linuxbat-manager << 'EOF'
#!/bin/bash
cd /opt/linuxbat-manager
source venv/bin/activate
python3 main.py
EOF
chmod +x /usr/local/bin/linuxbat-manager

# 5. Install desktop entry and icon
echo "[5/6] Installing desktop entry..."
mkdir -p /usr/share/applications
cp linuxbat-manager.desktop /usr/share/applications/

# Install icon (if exists)
if [ -f "resources/icons/icon.png" ]; then
    mkdir -p /usr/share/icons/hicolor/256x256/apps
    cp resources/icons/icon.png /usr/share/icons/hicolor/256x256/apps/linuxbat-manager.png
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# 6. Set correct permissions
echo "[6/6] Setting permissions..."
chown -R root:root /opt/linuxbat-manager
chmod -R 755 /opt/linuxbat-manager

# Update desktop database
update-desktop-database /usr/share/applications 2>/dev/null || true

echo ""
echo "======================================"
echo "Installation completed successfully!"
echo "======================================"
echo ""
echo "You can now launch Battery Manager Pro from:"
echo "  • Application menu (System/Settings category)"
echo "  • Command line: linuxbat-manager"
echo ""
echo "Note: The application requires sudo privileges to"
echo "      modify system settings (CPU, battery, etc.)"
echo ""
