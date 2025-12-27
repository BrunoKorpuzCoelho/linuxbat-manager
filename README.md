# 🔋 Battery Manager Pro

<div align="center">

![Battery Manager Pro](resources/icons/icon.png)

**Advanced Battery and Performance Management for Linux Laptops**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://www.linux.org/)

</div>

## 📖 Overview

Battery Manager Pro is a comprehensive desktop application for managing battery health, performance profiles, and system power settings on Linux laptops. Built with Clean Code principles and a modern PyQt6 interface, it provides real-time monitoring and advanced control over your laptop's power management.

### ✨ Key Features

- **🔋 Real-time Battery Monitoring**

  - Live battery charge percentage with animated circular gauge
  - Remaining time estimation (charging/discharging)
  - Battery health metrics (cycles, capacity, wear level)
  - Detailed device information (manufacturer, model, technology)

- **📊 Historical Data Visualization**

  - Interactive 30-minute rolling charge history chart
  - Real-time graph updates every 5 seconds
  - Visual trend analysis for power consumption

- **⚙️ CPU Performance Control**

  - Current CPU governor display
  - Real-time frequency monitoring for all cores
  - Performance/Powersave/Ondemand governor switching

- **🎮 System Controls**

  - **Conservation Mode**: Limit battery charge to 60% (extends lifespan)
  - **Performance Profiles**: Battery Saver, Balanced, Performance presets
  - **Turbo Boost Toggle**: Enable/disable CPU turbo frequencies
  - Custom profile creation and management

- **🎨 Modern UI/UX**
  - Dark and Light theme support
  - Responsive maximized window layout
  - Single scroll interface (web-page style)
  - Clean, intuitive controls with visual feedback

## 🖼️ Screenshots

### Dark Theme

![Battery Manager Dark Theme](screenshots/dark-theme.png)

### Light Theme

![Battery Manager Light Theme](screenshots/light-theme.png)

## 🚀 Installation

### System Requirements

- **OS**: Ubuntu 24.04 LTS or compatible Linux distribution
- **Python**: 3.10 or higher
- **Hardware**: Laptop with battery and sysfs support
- **Privileges**: Sudo access for system-level changes

### Quick Install

1. **Clone the repository**:

```bash
git clone https://github.com/BrunoKorpuzCoelho/linuxbat-manager.git
cd linuxbat-manager
```

2. **Run the installation script**:

```bash
chmod +x install.sh
sudo ./install.sh
```

The installation script will:

- Install all system dependencies
- Set up a Python virtual environment
- Install Python packages (PyQt6, pyqtgraph, psutil)
- Create system-wide launcher
- Install desktop entry and icon

3. **Launch the application**:

- From application menu: Search for "Battery Manager Pro" in System/Settings
- From terminal: `linuxbat-manager`

### Manual Installation (Development)

If you prefer to run from source without system installation:

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv \
    libxcb-cursor0 libxcb-xinerama0 libxkbcommon-x11-0 \
    libgl1-mesa-glx policykit-1

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run application
sudo python3 main.py
```

## 📚 Usage

### Running the Application

**Important**: The application requires sudo privileges to modify system settings (CPU governor, turbo boost, conservation mode).

```bash
sudo python3 main.py
# or if installed system-wide
linuxbat-manager
```

### Features Guide

#### Conservation Mode

- **Purpose**: Limits battery charge to 60% to extend battery lifespan
- **Recommended**: Enable for laptops primarily used plugged in
- **Toggle**: Check/uncheck "Enable Conservation Mode (60% limit)"

#### Performance Profiles

**Battery Saver**:

- CPU Governor: Powersave
- Turbo Boost: Disabled
- Conservation Mode: ON
- Use case: Maximum battery life

**Balanced** (Recommended):

- CPU Governor: Ondemand
- Turbo Boost: Enabled
- Conservation Mode: OFF
- Use case: Balanced performance and efficiency

**Performance**:

- CPU Governor: Performance
- Turbo Boost: Enabled
- Conservation Mode: OFF
- Use case: Maximum performance (gaming, rendering)

#### Turbo Boost Control

- **Enable**: Allow CPU to exceed base frequency for short bursts
- **Disable**: Lock CPU to base frequency (saves power, reduces heat)
- Independent control separate from profiles

#### Theme Toggle

- Switch between Dark and Light themes
- Settings persist across sessions
- Access via "☀️ Light Theme" / "🌙 Dark Theme" button

### Keyboard Shortcuts

- `F5`: Refresh data
- `Ctrl+Q`: Quit application
- `Ctrl+T`: Toggle theme

## 🏗️ Architecture

The application follows Clean Code principles with strict separation of concerns:

```
linuxbat-manager/
├── battery_monitor.py      # Data layer - reads from sysfs
├── system_control.py       # Control layer - executes sudo commands
├── profiles.py             # Business logic - profile management
├── main.py                 # Presentation layer - PyQt6 GUI
├── resources/
│   ├── styles/
│   │   ├── dark.qss       # Dark theme stylesheet
│   │   └── light.qss      # Light theme stylesheet
│   └── icons/
│       ├── icon.svg       # Application icon (vector)
│       └── icon.png       # Application icon (raster)
├── requirements.txt        # Python dependencies
├── install.sh             # System installation script
├── uninstall.sh           # Uninstallation script
└── README.md              # This file
```

### Code Quality Standards

- ✅ **PEP 8 compliant** - All code follows Python style guide
- ✅ **Type hints** - Complete type annotations throughout
- ✅ **Docstrings** - Comprehensive documentation for all functions/classes
- ✅ **SOLID principles** - Single Responsibility, clean abstractions
- ✅ **Error handling** - Graceful failure with user-friendly messages
- ✅ **Logging** - Detailed logging for debugging and monitoring

## 🔧 Configuration

### Profile Storage

Profiles are stored in JSON format at:

```
~/.config/battery_manager_pro/profiles.json
```

### Logs

Application logs are written to:

```
~/.local/share/battery_manager_pro/battery_manager.log
```

### System Paths

The application interacts with these system paths:

- Battery: `/sys/class/power_supply/BAT*/`
- CPU: `/sys/devices/system/cpu/cpu*/`
- Conservation Mode: `/sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode`

## 🧪 Testing

### Backend Tests

Test battery monitor:

```bash
sudo python3 -c "from battery_monitor import BatteryMonitor; m = BatteryMonitor(); print(m.get_battery_info())"
```

Test system control:

```bash
sudo python3 test_system_control.py
```

Test profile manager:

```bash
sudo python3 test_profiles.py
```

### GUI Tests

Run the application and verify:

1. All widgets display correct real-time data
2. Theme toggle works correctly
3. Conservation mode can be toggled
4. Profiles apply successfully
5. Turbo boost toggle functions
6. Historical chart updates every 5 seconds

## 🐛 Troubleshooting

### Application won't start

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Verify dependencies
pip list | grep -E "PyQt6|pyqtgraph|psutil"

# Check logs
tail -f ~/.local/share/battery_manager_pro/battery_manager.log
```

### Conservation mode not working

```bash
# Check if your laptop supports it
ls -l /sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode

# Verify you're running with sudo
sudo python3 main.py
```

### CPU governor changes not applying

```bash
# Check available governors
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors

# Ensure you have write permissions (sudo)
sudo python3 main.py
```

## 🤝 Contributing

Contributions are welcome! Please ensure your code:

- Follows PEP 8 style guide
- Includes type hints
- Has comprehensive docstrings
- Maintains Clean Code principles
- Includes appropriate error handling

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Bruno Korpuz Coelho**

- GitHub: [@BrunoKorpuzCoelho](https://github.com/BrunoKorpuzCoelho)

## 🙏 Acknowledgments

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework
- Powered by [pyqtgraph](https://www.pyqtgraph.org/) for real-time plotting
- System monitoring via [psutil](https://github.com/giampaolo/psutil)

## 📝 Changelog

### Version 1.0.0 (2025-12-27)

- Initial release
- Real-time battery monitoring with circular gauge
- 30-minute historical charge chart
- CPU performance monitoring and control
- Conservation mode support
- Performance profile presets
- Turbo boost toggle
- Dark/Light theme support
- System-wide installation support

---

<div align="center">

**Made with ❤️ for the Linux community**

If you find this project useful, please consider giving it a ⭐!

</div>
Advanced battery management tool for Linux with PyQt6 GUI - Real-time monitoring, conservation mode control, and performance profiles
