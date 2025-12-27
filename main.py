#!/usr/bin/env python3
"""
Main application entry point for Battery Manager Pro.

This module provides the main window and application initialization
for the battery management desktop application.
"""

# Standard library imports
import logging
import sys
from pathlib import Path
from typing import Optional

# Third-party imports
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStatusBar,
    QMenuBar,
    QMenu,
    QGroupBox,
    QGridLayout,
    QProgressBar,
    QScrollArea,
    QRadioButton,
    QCheckBox,
    QButtonGroup,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QAction, QIcon, QPainter, QColor, QPen, QFont, QPainterPath, QScreen
import pyqtgraph as pg
from collections import deque
from datetime import datetime, timedelta

# Local imports
from battery_monitor import BatteryMonitor
from profiles import ProfileManager, PerformanceProfile
from system_control import SystemController, CPUGovernor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application constants
APP_NAME: str = "Battery Manager Pro"
APP_VERSION: str = "1.0.0"
WINDOW_MIN_WIDTH: int = 900
WINDOW_MIN_HEIGHT: int = 800
DEFAULT_THEME: str = "dark"
REFRESH_INTERVAL_MS: int = 5000
HISTORY_DURATION_MINUTES: int = 30
MAX_HISTORY_POINTS: int = 360  # 30 minutes * 60 seconds / 5 seconds

# Resource paths
RESOURCES_DIR: Path = Path(__file__).parent / "resources"
STYLES_DIR: Path = RESOURCES_DIR / "styles"
DARK_THEME_PATH: Path = STYLES_DIR / "dark.qss"
LIGHT_THEME_PATH: Path = STYLES_DIR / "light.qss"


class CircularGauge(QWidget):
    """Circular gauge widget for displaying battery percentage.
    
    A custom widget that draws a circular progress indicator with
    animated arc and centered percentage text.
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize circular gauge.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._value: float = 0.0
        self._max_value: float = 100.0
        self._color: QColor = QColor(13, 115, 119)  # #0d7377
        self._text: str = "0%"
        self.setMinimumSize(180, 180)
    
    def set_value(self, value: float, text: Optional[str] = None) -> None:
        """Set gauge value and update display.
        
        Args:
            value: Value to display (0-100)
            text: Optional custom text to display in center
        """
        self._value = max(0.0, min(value, self._max_value))
        if text is not None:
            self._text = text
        else:
            self._text = f"{self._value:.1f}%"
        self.update()
    
    def set_color(self, color: QColor) -> None:
        """Set gauge arc color.
        
        Args:
            color: QColor for the gauge arc
        """
        self._color = color
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the circular gauge.
        
        Args:
            event: Paint event
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        side = min(width, height)
        
        # Center the gauge
        painter.translate(width / 2, height / 2)
        painter.scale(side / 200.0, side / 200.0)
        
        # Draw background circle
        pen = QPen(QColor(60, 60, 60) if self._is_dark_theme() else QColor(220, 220, 220))
        pen.setWidth(12)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(-85, -85, 170, 170, 0, 360 * 16)
        
        # Draw value arc
        pen.setColor(self._get_gauge_color())
        painter.setPen(pen)
        span_angle = int(360 * 16 * (self._value / self._max_value))
        painter.drawArc(-85, -85, 170, 170, 90 * 16, -span_angle)
        
        # Draw center text
        painter.setPen(QColor(255, 255, 255) if self._is_dark_theme() else QColor(0, 0, 0))
        font = QFont("Ubuntu", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(-90, -20, 180, 40), Qt.AlignmentFlag.AlignCenter, self._text)
    
    def _is_dark_theme(self) -> bool:
        """Check if dark theme is active.
        
        Returns:
            True if background is dark, False otherwise
        """
        bg_color = self.palette().window().color()
        return bg_color.lightness() < 128
    
    def _get_gauge_color(self) -> QColor:
        """Get gauge color based on value.
        
        Returns:
            QColor for gauge arc (green/yellow/red based on battery level)
        """
        if self._value >= 60:
            return QColor(76, 175, 80)  # Green
        elif self._value >= 20:
            return QColor(255, 193, 7)  # Yellow
        else:
            return QColor(244, 67, 54)  # Red


class BatteryWidget(QWidget):
    """Battery information display widget.
    
    This widget shows comprehensive battery information including charge
    level with circular gauge, health, cycles, and current power statistics.
    """
    
    def __init__(self, monitor: BatteryMonitor) -> None:
        """Initialize battery widget.
        
        Args:
            monitor: BatteryMonitor instance for reading battery data
        """
        super().__init__()
        self.monitor = monitor
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup user interface components."""
        main_layout = QVBoxLayout()
        
        # Circular gauge
        self.gauge = CircularGauge()
        gauge_container = QHBoxLayout()
        gauge_container.addStretch()
        gauge_container.addWidget(self.gauge)
        gauge_container.addStretch()
        main_layout.addLayout(gauge_container)
        
        # Status info
        status_group = QGroupBox("Battery Status")
        status_layout = QGridLayout()
        
        # Status
        status_layout.addWidget(QLabel("Status:"), 0, 0)
        self.status_label = QLabel("---")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label, 0, 1)
        
        # Power
        status_layout.addWidget(QLabel("Power:"), 1, 0)
        self.power_label = QLabel("--- W")
        self.power_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.power_label, 1, 1)
        
        # Voltage
        status_layout.addWidget(QLabel("Voltage:"), 2, 0)
        self.voltage_label = QLabel("--- V")
        status_layout.addWidget(self.voltage_label, 2, 1)
        
        # Time remaining
        status_layout.addWidget(QLabel("Time Remaining:"), 3, 0)
        self.time_label = QLabel("---")
        status_layout.addWidget(self.time_label, 3, 1)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Health info
        health_group = QGroupBox("Battery Health")
        health_layout = QGridLayout()
        
        # Health percentage
        health_layout.addWidget(QLabel("Health:"), 0, 0)
        self.health_label = QLabel("---%")
        self.health_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        health_layout.addWidget(self.health_label, 0, 1)
        
        # Cycles
        health_layout.addWidget(QLabel("Cycles:"), 1, 0)
        self.cycles_label = QLabel("---")
        health_layout.addWidget(self.cycles_label, 1, 1)
        
        # Capacity bar
        health_layout.addWidget(QLabel("Capacity:"), 2, 0)
        capacity_container = QVBoxLayout()
        self.capacity_label = QLabel("--- / --- mWh")
        self.capacity_bar = QProgressBar()
        self.capacity_bar.setMaximum(100)
        self.capacity_bar.setTextVisible(False)
        capacity_container.addWidget(self.capacity_bar)
        capacity_container.addWidget(self.capacity_label)
        health_layout.addLayout(capacity_container, 2, 1)
        
        # Conservation mode
        health_layout.addWidget(QLabel("Conservation Mode:"), 3, 0)
        self.conservation_label = QLabel("---")
        health_layout.addWidget(self.conservation_label, 3, 1)
        
        health_group.setLayout(health_layout)
        main_layout.addWidget(health_group)
        
        # Device info
        device_group = QGroupBox("Device Information")
        device_layout = QGridLayout()
        
        device_layout.addWidget(QLabel("Manufacturer:"), 0, 0)
        self.manufacturer_label = QLabel("---")
        device_layout.addWidget(self.manufacturer_label, 0, 1)
        
        device_layout.addWidget(QLabel("Model:"), 1, 0)
        self.model_label = QLabel("---")
        device_layout.addWidget(self.model_label, 1, 1)
        
        device_group.setLayout(device_layout)
        main_layout.addWidget(device_group)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def update_data(self) -> None:
        """Update battery information display."""
        try:
            # Check if widget is still valid
            if not self.gauge or not hasattr(self, 'gauge'):
                return
            
            info = self.monitor.get_battery_info()
            
            # Update gauge
            self.gauge.set_value(info.charge_percent)
            
            # Update status
            self.status_label.setText(info.status)
            
            # Update power with icon
            power_w = info.power_now_mw / 1000
            if info.status == "Charging":
                self.power_label.setText(f"⚡ {power_w:.1f} W")
            elif info.status == "Discharging":
                self.power_label.setText(f"🔋 {power_w:.1f} W")
            else:
                self.power_label.setText(f"{power_w:.1f} W")
            
            # Update voltage
            self.voltage_label.setText(f"{info.voltage_now_v:.2f} V")
            
            # Update time remaining
            if info.time_remaining_minutes is not None:
                hours = info.time_remaining_minutes // 60
                minutes = info.time_remaining_minutes % 60
                self.time_label.setText(f"{hours}h {minutes}min")
            else:
                self.time_label.setText("N/A")
            
            # Update health
            health_color = "#4CAF50" if info.health_percent >= 80 else "#FF9800" if info.health_percent >= 60 else "#F44336"
            self.health_label.setText(f"{info.health_percent:.1f}%")
            self.health_label.setStyleSheet(f"font-weight: bold; color: {health_color};")
            
            # Update cycles
            self.cycles_label.setText(str(info.cycle_count))
            
            # Update capacity
            self.capacity_label.setText(f"{info.energy_full_mwh} / {info.energy_full_design_mwh} mWh")
            capacity_percent = int(info.capacity_percent)
            self.capacity_bar.setValue(capacity_percent)
            
            # Update conservation mode
            if info.conservation_mode_enabled:
                self.conservation_label.setText("🟢 ON (60% limit)")
                self.conservation_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.conservation_label.setText("⚪ OFF (Full charge)")
                self.conservation_label.setStyleSheet("color: #999;")
            
            # Update device info
            self.manufacturer_label.setText(info.manufacturer)
            self.model_label.setText(info.model_name)
            
        except RuntimeError:
            # Widget has been deleted, stop updates
            pass
        except Exception as e:
            logger.error(f"Failed to update battery data: {e}")


class CPUWidget(QWidget):
    """CPU information and control widget.
    
    This widget displays CPU frequency scaling information and provides
    controls for performance management.
    """
    
    def __init__(self, monitor: BatteryMonitor) -> None:
        """Initialize CPU widget.
        
        Args:
            monitor: BatteryMonitor instance for reading CPU data
        """
        super().__init__()
        self.monitor = monitor
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup user interface components."""
        main_layout = QVBoxLayout()
        
        # CPU Status
        status_group = QGroupBox("CPU Status")
        status_layout = QGridLayout()
        
        # Governor
        status_layout.addWidget(QLabel("Governor:"), 0, 0)
        self.governor_label = QLabel("---")
        self.governor_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.governor_label, 0, 1)
        
        # Current frequency
        status_layout.addWidget(QLabel("Current Freq:"), 1, 0)
        self.freq_label = QLabel("--- MHz")
        self.freq_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: #0d7377;")
        status_layout.addWidget(self.freq_label, 1, 1)
        
        # Frequency range
        status_layout.addWidget(QLabel("Frequency Range:"), 2, 0)
        self.freq_range_label = QLabel("--- - --- MHz")
        status_layout.addWidget(self.freq_range_label, 2, 1)
        
        # Turbo boost
        status_layout.addWidget(QLabel("Turbo Boost:"), 3, 0)
        self.turbo_label = QLabel("---")
        status_layout.addWidget(self.turbo_label, 3, 1)
        
        # EPP
        status_layout.addWidget(QLabel("EPP:"), 4, 0)
        self.epp_label = QLabel("---")
        status_layout.addWidget(self.epp_label, 4, 1)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Frequency bar
        freq_group = QGroupBox("Frequency Visualization")
        freq_layout = QVBoxLayout()
        
        self.freq_bar = QProgressBar()
        self.freq_bar.setTextVisible(True)
        self.freq_bar.setFormat("%v MHz")
        freq_layout.addWidget(self.freq_bar)
        
        freq_group.setLayout(freq_layout)
        main_layout.addWidget(freq_group)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def update_data(self) -> None:
        """Update CPU information display."""
        try:
            # Check if widget is still valid
            if not self.governor_label or not hasattr(self, 'governor_label'):
                return
            
            info = self.monitor.get_cpu_info()
            
            # Update governor
            governor_display = info.governor.upper()
            if info.governor == "powersave":
                self.governor_label.setText(f"🔋 {governor_display}")
                self.governor_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
            elif info.governor == "performance":
                self.governor_label.setText(f"⚡ {governor_display}")
                self.governor_label.setStyleSheet("font-weight: bold; color: #FF9800;")
            else:
                self.governor_label.setText(governor_display)
                self.governor_label.setStyleSheet("font-weight: bold;")
            
            # Update current frequency
            freq_mhz = info.current_freq_khz / 1000
            self.freq_label.setText(f"{freq_mhz:.0f} MHz")
            
            # Update frequency range
            min_freq_mhz = info.min_freq_khz / 1000
            max_freq_mhz = info.max_freq_khz / 1000
            self.freq_range_label.setText(f"{min_freq_mhz:.0f} - {max_freq_mhz:.0f} MHz")
            
            # Update frequency bar
            self.freq_bar.setMinimum(int(min_freq_mhz))
            self.freq_bar.setMaximum(int(max_freq_mhz))
            # If frequency is 0 (idle), show minimum frequency
            display_freq = int(freq_mhz) if freq_mhz > 0 else int(min_freq_mhz)
            self.freq_bar.setValue(display_freq)
            
            # Update turbo boost
            if info.turbo_enabled:
                self.turbo_label.setText("🚀 Enabled")
                self.turbo_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.turbo_label.setText("⚪ Disabled")
                self.turbo_label.setStyleSheet("color: #999;")
            
            # Update EPP
            self.epp_label.setText(info.energy_performance_preference)
            
        except RuntimeError:
            # Widget has been deleted, stop updates
            pass
        except Exception as e:
            logger.error(f"Failed to update CPU data: {e}")


class BatteryHistoryWidget(QWidget):
    """Battery charge history chart widget.
    
    This widget displays a line chart showing battery charge percentage
    over the last 30 minutes using pyqtgraph.
    """
    
    def __init__(self) -> None:
        """Initialize battery history widget."""
        super().__init__()
        
        # History data storage
        self.timestamps: deque = deque(maxlen=MAX_HISTORY_POINTS)
        self.charge_levels: deque = deque(maxlen=MAX_HISTORY_POINTS)
        self.start_time = datetime.now()
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup user interface components."""
        layout = QVBoxLayout()
        
        # Configure pyqtgraph
        pg.setConfigOptions(antialias=True)
        
        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#2d2d2d')
        self.plot_widget.setTitle(
            "Battery Charge History (Last 30 Minutes)",
            color='#0d7377',
            size='14pt'
        )
        
        # Configure axes
        self.plot_widget.setLabel('left', 'Charge (%)', color='#ffffff', size='11pt')
        self.plot_widget.setLabel('bottom', 'Time (minutes ago)', color='#ffffff', size='11pt')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setYRange(0, 100, padding=0)
        self.plot_widget.setXRange(-HISTORY_DURATION_MINUTES, 0, padding=0)
        
        # Style axes
        axis_color = '#ffffff'
        for axis in ['left', 'bottom']:
            ax = self.plot_widget.getAxis(axis)
            ax.setPen(pg.mkPen(color=axis_color, width=1))
            ax.setTextPen(pg.mkPen(color=axis_color))
        
        # Create curve
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#4CAF50', width=2),
            symbol='o',
            symbolSize=6,
            symbolBrush='#4CAF50',
            name='Battery %'
        )
        
        # Add legend
        self.plot_widget.addLegend()
        
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
    
    def add_data_point(self, charge_percent: float) -> None:
        """Add a new data point to the history.
        
        Args:
            charge_percent: Battery charge percentage (0-100)
        """
        current_time = datetime.now()
        elapsed_seconds = (current_time - self.start_time).total_seconds()
        
        # Store as negative minutes ago for x-axis
        minutes_ago = -elapsed_seconds / 60.0
        
        self.timestamps.append(minutes_ago)
        self.charge_levels.append(charge_percent)
        
        # Update plot
        self._update_plot()
    
    def _update_plot(self) -> None:
        """Update the plot with current data."""
        if len(self.timestamps) > 0:
            self.curve.setData(
                list(self.timestamps),
                list(self.charge_levels)
            )
    
    def update_theme(self, is_dark: bool) -> None:
        """Update plot colors based on theme.
        
        Args:
            is_dark: True for dark theme, False for light theme
        """
        if is_dark:
            bg_color = '#2d2d2d'
            text_color = '#ffffff'
            grid_alpha = 0.3
        else:
            bg_color = '#ffffff'
            text_color = '#000000'
            grid_alpha = 0.2
        
        self.plot_widget.setBackground(bg_color)
        
        # Update axis colors
        for axis in ['left', 'bottom']:
            ax = self.plot_widget.getAxis(axis)
            ax.setPen(pg.mkPen(color=text_color, width=1))
            ax.setTextPen(pg.mkPen(color=text_color))
        
        # Update title color
        self.plot_widget.setTitle(
            "Battery Charge History (Last 30 Minutes)",
            color='#0d7377',
            size='14pt'
        )
        
        # Update grid
        self.plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)


class ControlsWidget(QWidget):
    """Controls widget for system settings and profiles.
    
    This widget provides controls for conservation mode, performance
    profiles, and turbo boost management.
    """
    
    def __init__(
        self,
        monitor: BatteryMonitor,
        controller: SystemController,
        profile_manager: ProfileManager
    ) -> None:
        """Initialize controls widget.
        
        Args:
            monitor: BatteryMonitor instance
            controller: SystemController instance
            profile_manager: ProfileManager instance
        """
        super().__init__()
        self.monitor = monitor
        self.controller = controller
        self.profile_manager = profile_manager
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup user interface components."""
        main_layout = QVBoxLayout()
        
        # Conservation Mode Section
        conservation_group = QGroupBox("⚡ Conservation Mode")
        conservation_layout = QVBoxLayout()
        
        info_label = QLabel(
            "Limits battery charge to 60% to extend battery lifespan\n"
            "when laptop is primarily used plugged in."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #999; font-size: 10pt;")
        conservation_layout.addWidget(info_label)
        
        self.conservation_checkbox = QCheckBox("Enable Conservation Mode (60% limit)")
        self.conservation_checkbox.setStyleSheet("font-weight: bold;")
        self.conservation_checkbox.stateChanged.connect(self._on_conservation_changed)
        conservation_layout.addWidget(self.conservation_checkbox)
        
        conservation_group.setLayout(conservation_layout)
        main_layout.addWidget(conservation_group)
        
        # Performance Profiles Section
        profiles_group = QGroupBox("🎯 Performance Profiles")
        profiles_layout = QVBoxLayout()
        
        self.profile_buttons = QButtonGroup()
        
        # Get predefined profiles
        predefined = self.profile_manager.get_predefined_profiles()
        
        for idx, profile in enumerate(predefined):
            radio = QRadioButton(profile.name)
            radio.setProperty("profile", profile)
            
            # Add description as tooltip
            radio.setToolTip(profile.description)
            
            # Style based on profile
            if "Battery" in profile.name:
                radio.setStyleSheet("font-weight: bold;")
            elif "Performance" in profile.name:
                radio.setStyleSheet("font-weight: bold; color: #FF9800;")
            
            self.profile_buttons.addButton(radio, idx)
            profiles_layout.addWidget(radio)
            
            # Add description label
            desc_label = QLabel(f"  → {profile.description}")
            desc_label.setStyleSheet("color: #999; font-size: 9pt; margin-left: 20px;")
            desc_label.setWordWrap(True)
            profiles_layout.addWidget(desc_label)
        
        # Apply button
        apply_profile_btn = QPushButton("📌 Apply Selected Profile")
        apply_profile_btn.clicked.connect(self._on_apply_profile)
        profiles_layout.addWidget(apply_profile_btn)
        
        profiles_group.setLayout(profiles_layout)
        main_layout.addWidget(profiles_group)
        
        # Turbo Boost Section
        turbo_group = QGroupBox("🚀 Turbo Boost Control")
        turbo_layout = QVBoxLayout()
        
        turbo_info = QLabel(
            "Allows CPU to exceed base frequency for better performance.\n"
            "Disable to reduce power consumption and heat."
        )
        turbo_info.setWordWrap(True)
        turbo_info.setStyleSheet("color: #999; font-size: 10pt;")
        turbo_layout.addWidget(turbo_info)
        
        turbo_control_layout = QHBoxLayout()
        
        self.turbo_status_label = QLabel("Status: ---")
        self.turbo_status_label.setStyleSheet("font-weight: bold;")
        turbo_control_layout.addWidget(self.turbo_status_label)
        
        turbo_control_layout.addStretch()
        
        self.turbo_toggle_btn = QPushButton("Toggle Turbo Boost")
        self.turbo_toggle_btn.clicked.connect(self._on_turbo_toggle)
        turbo_control_layout.addWidget(self.turbo_toggle_btn)
        
        turbo_layout.addLayout(turbo_control_layout)
        
        turbo_group.setLayout(turbo_layout)
        main_layout.addWidget(turbo_group)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
        
        # Initial state update
        self._update_controls_state()
    
    def _update_controls_state(self) -> None:
        """Update controls to reflect current system state."""
        try:
            # Update conservation mode checkbox
            battery_info = self.monitor.get_battery_info()
            self.conservation_checkbox.blockSignals(True)
            self.conservation_checkbox.setChecked(battery_info.conservation_mode_enabled)
            self.conservation_checkbox.blockSignals(False)
            
            # Update turbo boost status
            cpu_info = self.monitor.get_cpu_info()
            if cpu_info.turbo_enabled:
                self.turbo_status_label.setText("Status: 🚀 Enabled")
                self.turbo_status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
            else:
                self.turbo_status_label.setText("Status: ⚪ Disabled")
                self.turbo_status_label.setStyleSheet("font-weight: bold; color: #999;")
            
        except Exception as e:
            logger.error(f"Failed to update controls state: {e}")
    
    def _on_conservation_changed(self, state: int) -> None:
        """Handle conservation mode checkbox change.
        
        Args:
            state: Checkbox state (Qt.Checked or Qt.Unchecked)
        """
        enabled = state == Qt.CheckState.Checked.value
        
        try:
            self.controller.set_conservation_mode(enabled)
            mode_str = "enabled (60% limit)" if enabled else "disabled (full charge)"
            QMessageBox.information(
                self,
                "Conservation Mode",
                f"Conservation mode {mode_str} successfully!"
            )
        except Exception as e:
            logger.error(f"Failed to set conservation mode: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to set conservation mode:\n{str(e)}\n\n"
                "Make sure you have sudo privileges."
            )
            # Revert checkbox
            self.conservation_checkbox.blockSignals(True)
            self.conservation_checkbox.setChecked(not enabled)
            self.conservation_checkbox.blockSignals(False)
    
    def _on_apply_profile(self) -> None:
        """Handle apply profile button click."""
        selected_button = self.profile_buttons.checkedButton()
        
        if not selected_button:
            QMessageBox.warning(
                self,
                "No Profile Selected",
                "Please select a performance profile first."
            )
            return
        
        profile = selected_button.property("profile")
        
        try:
            success = self.profile_manager.apply_profile(profile)
            
            if success:
                QMessageBox.information(
                    self,
                    "Profile Applied",
                    f"Profile '{profile.name}' applied successfully!\n\n"
                    f"Settings:\n"
                    f"• CPU Governor: {profile.cpu_governor}\n"
                    f"• Turbo Boost: {'Enabled' if profile.turbo_enabled else 'Disabled'}\n"
                    f"• Conservation Mode: {'ON' if profile.conservation_mode else 'OFF'}"
                )
                # Update controls to reflect new state
                self._update_controls_state()
            else:
                QMessageBox.warning(
                    self,
                    "Profile Applied with Warnings",
                    f"Profile '{profile.name}' was applied but some settings may have failed.\n"
                    "Check the logs for details."
                )
        except Exception as e:
            logger.error(f"Failed to apply profile: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to apply profile '{profile.name}':\n{str(e)}\n\n"
                "Make sure you have sudo privileges."
            )
    
    def _on_turbo_toggle(self) -> None:
        """Handle turbo boost toggle button click."""
        try:
            cpu_info = self.monitor.get_cpu_info()
            new_state = not cpu_info.turbo_enabled
            
            self.controller.set_turbo_boost(new_state)
            
            state_str = "enabled" if new_state else "disabled"
            QMessageBox.information(
                self,
                "Turbo Boost",
                f"Turbo Boost {state_str} successfully!"
            )
            
            # Update status
            self._update_controls_state()
            
        except Exception as e:
            logger.error(f"Failed to toggle turbo boost: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to toggle turbo boost:\n{str(e)}\n\n"
                "Make sure you have sudo privileges."
            )
    
    def refresh_state(self) -> None:
        """Public method to refresh controls state."""
        self._update_controls_state()


class MainWindow(QMainWindow):
    """Main application window.
    
    This is the primary window of the Battery Manager application,
    containing all widgets and providing the main user interface.
    """
    
    def __init__(self) -> None:
        """Initialize main window."""
        super().__init__()
        
        self.current_theme: str = DEFAULT_THEME
        self.monitor = BatteryMonitor()
        self.profile_manager = ProfileManager()
        self.controller = SystemController()
        
        # Initialize history widget
        self.history_widget = BatteryHistoryWidget()
        
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._setup_refresh_timer()
        self._load_theme(self.current_theme)
        
        # Show maximized
        self.showMaximized()
        
        # Initial data update
        self._refresh_data()
        
        logger.info(f"{APP_NAME} initialized successfully")
    
    def _setup_ui(self) -> None:
        """Setup user interface components."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # Content widget that will be placed inside scroll area
        content_widget = QWidget()
        main_container = QVBoxLayout(content_widget)
        main_container.setContentsMargins(15, 15, 15, 15)
        main_container.setSpacing(15)
        
        # Top controls (Refresh and Theme buttons)
        top_controls_layout = QHBoxLayout()
        top_controls_layout.addStretch()
        
        self.refresh_button = QPushButton("🔄 Refresh Now")
        self.refresh_button.clicked.connect(self._refresh_data)
        top_controls_layout.addWidget(self.refresh_button)
        
        self.theme_button = QPushButton("☀️ Light Theme")
        self.theme_button.clicked.connect(self.toggle_theme)
        top_controls_layout.addWidget(self.theme_button)
        
        main_container.addLayout(top_controls_layout)
        
        # Top section with battery and CPU info
        top_layout = QHBoxLayout()
        
        # Left column - Battery info
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        battery_label = QLabel("🔋 BATTERY INFO")
        battery_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #0d7377;")
        left_layout.addWidget(battery_label)
        
        self.battery_widget = BatteryWidget(self.monitor)
        left_layout.addWidget(self.battery_widget)
        
        top_layout.addWidget(left_widget, stretch=1)
        
        # Right column - CPU info
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        cpu_label = QLabel("⚙️  CPU INFO")
        cpu_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #0d7377;")
        right_layout.addWidget(cpu_label)
        
        self.cpu_widget = CPUWidget(self.monitor)
        right_layout.addWidget(self.cpu_widget)
        
        top_layout.addWidget(right_widget, stretch=1)
        
        # Add top layout to main container
        main_container.addLayout(top_layout)
        
        # Controls section
        controls_label = QLabel("🎮 SYSTEM CONTROLS")
        controls_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #0d7377; margin-top: 10px;")
        main_container.addWidget(controls_label)
        
        self.controls_widget = ControlsWidget(
            self.monitor,
            self.controller,
            self.profile_manager
        )
        main_container.addWidget(self.controls_widget)
        
        # Bottom section - Battery history chart
        history_label = QLabel("📊 CHARGE HISTORY")
        history_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #0d7377; margin-top: 10px;")
        main_container.addWidget(history_label)
        
        self.history_widget.setMinimumHeight(300)
        main_container.addWidget(self.history_widget)
        
        # Wrap entire content in a single scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setCentralWidget(scroll_area)
    
    def _setup_menu_bar(self) -> None:
        """Setup menu bar with application menus."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_data)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        theme_action = QAction("Toggle &Theme", self)
        theme_action.setShortcut("Ctrl+T")
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_status_bar(self) -> None:
        """Setup status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _setup_refresh_timer(self) -> None:
        """Setup automatic refresh timer."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_data)
        self.refresh_timer.start(REFRESH_INTERVAL_MS)
        
        logger.info(f"Auto-refresh enabled: every {REFRESH_INTERVAL_MS/1000:.0f} seconds")
    
    def _refresh_data(self) -> None:
        """Refresh all data displays."""
        try:
            battery_info = self.monitor.get_battery_info()
            
            # Update widgets
            self.battery_widget.update_data()
            self.cpu_widget.update_data()
            self.controls_widget.refresh_state()
            
            # Add data point to history
            self.history_widget.add_data_point(battery_info.charge_percent)
            
            self.status_bar.showMessage(
                f"Last updated: {self._get_current_time()}", 
                3000
            )
        except Exception as e:
            logger.error(f"Failed to refresh data: {e}")
            self.status_bar.showMessage("Error updating data", 3000)
    
    def _get_current_time(self) -> str:
        """Get current time as formatted string.
        
        Returns:
            Current time in HH:MM:SS format.
        """
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    def toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self._load_theme(self.current_theme)
        
        # Update history widget theme
        is_dark = self.current_theme == "dark"
        self.history_widget.update_theme(is_dark)
        
        # Update button text
        if self.current_theme == "dark":
            self.theme_button.setText("☀️ Light Theme")
        else:
            self.theme_button.setText("🌙 Dark Theme")
        
        logger.info(f"Theme changed to: {self.current_theme}")
    
    def _load_theme(self, theme: str) -> None:
        """Load and apply a theme stylesheet.
        
        Args:
            theme: Theme name ("dark" or "light")
        """
        if theme == "dark":
            theme_path = DARK_THEME_PATH
        else:
            theme_path = LIGHT_THEME_PATH
        
        if not theme_path.exists():
            logger.warning(f"Theme file not found: {theme_path}")
            return
        
        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            
            self.setStyleSheet(stylesheet)
            logger.info(f"Theme loaded: {theme}")
        
        except Exception as e:
            logger.error(f"Failed to load theme {theme}: {e}")
    
    def _show_about(self) -> None:
        """Show about dialog."""
        from PyQt6.QtWidgets import QMessageBox
        
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2>"
            f"<p>Version {APP_VERSION}</p>"
            f"<p>Advanced battery and performance management for Linux laptops.</p>"
            f"<p><b>Features:</b></p>"
            f"<ul>"
            f"<li>Real-time battery monitoring</li>"
            f"<li>CPU performance profiles</li>"
            f"<li>Conservation mode control</li>"
            f"<li>Custom performance profiles</li>"
            f"</ul>"
            f"<p>Built with PyQt6 and Python 3</p>"
        )


def main() -> int:
    """Main application entry point.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        
        window = MainWindow()
        window.show()
        
        return app.exec()
    
    except Exception as e:
        logger.exception(f"Application failed to start: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
