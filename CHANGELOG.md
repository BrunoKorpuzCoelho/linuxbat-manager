# Changelog

All notable changes to Battery Manager Pro will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-27

### Added

#### Core Features

- Real-time battery monitoring with circular gauge visualization
- 30-minute rolling historical charge chart with pyqtgraph
- CPU performance monitoring (governor, frequency)
- Conservation mode support (60% charge limit)
- Performance profile system with 3 presets:
  - Battery Saver (maximum battery life)
  - Balanced (recommended for most users)
  - Performance (maximum performance)
- Turbo boost toggle control
- Auto-refresh every 5 seconds
- Dark and Light theme support

#### GUI Components

- **CircularGauge**: Custom QPainter widget with dynamic colors
- **BatteryWidget**: Comprehensive battery information display
  - Status group (charge, voltage, power)
  - Health group (cycles, capacity, wear)
  - Device info group (manufacturer, model, technology)
- **CPUWidget**: CPU status and frequency monitoring
- **BatteryHistoryWidget**: Interactive historical chart
- **ControlsWidget**: System control interface
- **MainWindow**: Main application window with menu bar

#### Backend Modules

- **battery_monitor.py**: sysfs reading layer
  - BatteryInfo dataclass with computed properties
  - CPUInfo dataclass with frequency aggregation
  - Safe sysfs file reading with error handling
- **system_control.py**: System modification layer
  - Conservation mode toggle
  - CPU governor switching (powersave/ondemand/performance)
  - Turbo boost control
  - Sudo command execution with timeout
- **profiles.py**: Profile management
  - JSON persistence in user config directory
  - Custom profile creation
  - Profile validation

#### Installation & Distribution

- System-wide installation script (`install.sh`)
- Uninstallation script (`uninstall.sh`)
- Desktop entry for application launcher
- Application icon (SVG and PNG)
- Dependency management scripts

#### Documentation

- Comprehensive README with installation guide
- Contributing guidelines (CONTRIBUTING.md)
- MIT License
- Code documentation (docstrings for all public APIs)

#### Testing

- Backend test scripts for system control
- Backend test scripts for profile management
- Manual GUI testing procedures

### Design Decisions

- Clean Code architecture with strict separation of concerns
- PEP 8 compliance throughout codebase
- Comprehensive type hints for all functions
- SOLID principles adherence
- Single scroll interface (web-page style)
- Maximized window on startup for optimal space usage
- Graceful error handling with user-friendly dialogs

### Technical Details

- **Language**: Python 3.10+
- **GUI Framework**: PyQt6 6.6+
- **Plotting**: pyqtgraph 0.13.3+
- **System Info**: psutil 5.9.6+
- **Target OS**: Ubuntu 24.04 LTS (compatible with other Linux distros)
- **Hardware Support**: Lenovo IdeaPad (tested on LOQ 15IRX9)

## [Unreleased]

### Planned Features

- Multiple battery support
- Custom conservation mode thresholds
- Battery calibration assistant
- Power consumption statistics
- Export data to CSV
- System tray icon with quick controls
- Notification system for battery events
- Support for other laptop brands
- Wayland compatibility improvements
- AppImage distribution

---

[1.0.0]: https://github.com/BrunoKorpuzCoelho/linuxbat-manager/releases/tag/v1.0.0
