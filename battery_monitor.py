#!/usr/bin/env python3
"""
Battery and CPU monitoring module for Linux systems.

This module provides classes to read battery and CPU information from
the Linux sysfs filesystem. It handles all system-level data collection
with robust error handling and type safety.
"""

# Standard library imports
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Battery sysfs paths
BATTERY_BASE_PATH: str = "/sys/class/power_supply/BAT1"
BATTERY_CAPACITY_PATH: str = f"{BATTERY_BASE_PATH}/capacity"
BATTERY_STATUS_PATH: str = f"{BATTERY_BASE_PATH}/status"
BATTERY_CYCLE_COUNT_PATH: str = f"{BATTERY_BASE_PATH}/cycle_count"
BATTERY_ENERGY_NOW_PATH: str = f"{BATTERY_BASE_PATH}/energy_now"
BATTERY_ENERGY_FULL_PATH: str = f"{BATTERY_BASE_PATH}/energy_full"
BATTERY_ENERGY_FULL_DESIGN_PATH: str = f"{BATTERY_BASE_PATH}/energy_full_design"
BATTERY_POWER_NOW_PATH: str = f"{BATTERY_BASE_PATH}/power_now"
BATTERY_VOLTAGE_NOW_PATH: str = f"{BATTERY_BASE_PATH}/voltage_now"
BATTERY_MANUFACTURER_PATH: str = f"{BATTERY_BASE_PATH}/manufacturer"
BATTERY_MODEL_NAME_PATH: str = f"{BATTERY_BASE_PATH}/model_name"

# Conservation mode path (Lenovo specific)
CONSERVATION_MODE_PATH: str = "/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/conservation_mode"

# CPU sysfs paths
CPU_BASE_PATH: str = "/sys/devices/system/cpu/cpu0/cpufreq"
CPU_GOVERNOR_PATH: str = f"{CPU_BASE_PATH}/scaling_governor"
CPU_MIN_FREQ_PATH: str = f"{CPU_BASE_PATH}/scaling_min_freq"
CPU_MAX_FREQ_PATH: str = f"{CPU_BASE_PATH}/scaling_max_freq"
CPU_CURRENT_FREQ_PATH: str = f"{CPU_BASE_PATH}/cpuinfo_cur_freq"
CPU_EPP_PATH: str = f"{CPU_BASE_PATH}/energy_performance_preference"

# Intel P-State paths
INTEL_PSTATE_BASE_PATH: str = "/sys/devices/system/cpu/intel_pstate"
INTEL_PSTATE_NO_TURBO_PATH: str = f"{INTEL_PSTATE_BASE_PATH}/no_turbo"
INTEL_PSTATE_STATUS_PATH: str = f"{INTEL_PSTATE_BASE_PATH}/status"

# Constants for calculations
MICROWATT_TO_WATT_DIVISOR: int = 1000000
MICROVOLT_TO_VOLT_DIVISOR: int = 1000000
MICROWATT_HOUR_TO_MILLIWATT_HOUR_DIVISOR: int = 1000
MINUTES_PER_HOUR: int = 60
PERCENTAGE_MULTIPLIER: int = 100
MIN_POWER_FOR_TIME_CALCULATION_MW: int = 100


@dataclass
class BatteryInfo:
    """Complete battery information snapshot.
    
    This dataclass holds all relevant battery information read from sysfs,
    along with computed properties for derived metrics like health percentage
    and time remaining estimates.
    
    Attributes:
        charge_percent: Current charge level (0-100%)
        status: Battery status (Charging/Discharging/Not charging/Full)
        capacity_percent: Current capacity relative to design (0-100%)
        cycle_count: Number of charge cycles completed
        energy_now_mwh: Current energy in milliwatt-hours
        energy_full_mwh: Current full capacity in milliwatt-hours
        energy_full_design_mwh: Design capacity in milliwatt-hours
        power_now_mw: Current power draw/input in milliwatts
        voltage_now_v: Current voltage in volts
        manufacturer: Battery manufacturer name
        model_name: Battery model identifier
        conservation_mode_enabled: Whether 60% charge limit is active
    """
    
    charge_percent: float
    status: str
    capacity_percent: float
    cycle_count: int
    energy_now_mwh: int
    energy_full_mwh: int
    energy_full_design_mwh: int
    power_now_mw: int
    voltage_now_v: float
    manufacturer: str
    model_name: str
    conservation_mode_enabled: bool
    
    @property
    def health_percent(self) -> float:
        """Calculate battery health as percentage of design capacity.
        
        Returns:
            Battery health percentage (0-100%). Returns 0 if design
            capacity is invalid to avoid division by zero.
        """
        if self.energy_full_design_mwh == 0:
            logger.warning("Design capacity is zero, cannot calculate health")
            return 0.0
        
        health = (self.energy_full_mwh / self.energy_full_design_mwh) * PERCENTAGE_MULTIPLIER
        return round(health, 1)
    
    @property
    def time_remaining_minutes(self) -> Optional[int]:
        """Calculate estimated time remaining for current operation.
        
        For discharging: calculates time until battery depletes.
        For charging: calculates time until battery is full.
        
        Returns:
            Estimated minutes remaining, or None if calculation is not
            possible (e.g., no power draw, invalid state, or battery full/empty).
        """
        if self.status not in ["Charging", "Discharging"]:
            return None
        
        if self.power_now_mw < MIN_POWER_FOR_TIME_CALCULATION_MW:
            logger.debug("Power draw too low for time estimation")
            return None
        
        if self.status == "Discharging":
            if self.energy_now_mwh == 0:
                return 0
            hours_remaining = self.energy_now_mwh / self.power_now_mw
        else:  # Charging
            energy_to_full = self.energy_full_mwh - self.energy_now_mwh
            if energy_to_full <= 0:
                return 0
            hours_remaining = energy_to_full / self.power_now_mw
        
        minutes = int(hours_remaining * MINUTES_PER_HOUR)
        return max(0, minutes)


@dataclass
class CPUInfo:
    """Complete CPU state information.
    
    This dataclass holds CPU frequency scaling and performance settings
    read from sysfs.
    
    Attributes:
        governor: Current CPU frequency governor (powersave/performance/etc.)
        turbo_enabled: Whether Intel Turbo Boost is enabled
        min_freq_khz: Minimum CPU frequency in kilohertz
        max_freq_khz: Maximum CPU frequency in kilohertz
        current_freq_khz: Current CPU frequency in kilohertz
        energy_performance_preference: Intel EPP setting for power/performance balance
    """
    
    governor: str
    turbo_enabled: bool
    min_freq_khz: int
    max_freq_khz: int
    current_freq_khz: int
    energy_performance_preference: str


class BatteryMonitor:
    """Reads and monitors battery and system information from Linux sysfs.
    
    This class provides methods to retrieve current battery and CPU state
    information by reading from the Linux kernel's sysfs virtual filesystem.
    All file operations include comprehensive error handling.
    """
    
    def __init__(self) -> None:
        """Initialize battery monitor with system paths validation.
        
        Logs warnings if critical system paths are not accessible.
        """
        self._validate_system_paths()
    
    def _validate_system_paths(self) -> None:
        """Validate that critical system paths exist and are readable.
        
        Logs warnings for missing paths but does not raise exceptions,
        allowing the application to start even if some features are unavailable.
        """
        critical_paths = [
            BATTERY_BASE_PATH,
            CPU_BASE_PATH,
        ]
        
        for path_str in critical_paths:
            path = Path(path_str)
            if not path.exists():
                logger.warning(f"Critical path not found: {path_str}")
            elif not path.is_dir():
                logger.warning(f"Path is not a directory: {path_str}")
    
    def _read_sysfs_file(self, file_path: str) -> Optional[str]:
        """Read and return content from a sysfs file.
        
        Args:
            file_path: Absolute path to the sysfs file
            
        Returns:
            File content as string with whitespace stripped, or None if
            the file cannot be read.
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.debug(f"File does not exist: {file_path}")
                return None
            
            content = path.read_text().strip()
            return content
        
        except PermissionError:
            logger.error(f"Permission denied reading: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
    
    def _read_sysfs_int(self, file_path: str, default: int = 0) -> int:
        """Read an integer value from a sysfs file.
        
        Args:
            file_path: Absolute path to the sysfs file
            default: Default value to return if reading fails
            
        Returns:
            Integer value from file, or default if reading fails.
        """
        content = self._read_sysfs_file(file_path)
        if content is None:
            return default
        
        try:
            return int(content)
        except ValueError:
            logger.error(f"Invalid integer in {file_path}: {content}")
            return default
    
    def _read_sysfs_float(self, file_path: str, default: float = 0.0) -> float:
        """Read a float value from a sysfs file.
        
        Args:
            file_path: Absolute path to the sysfs file
            default: Default value to return if reading fails
            
        Returns:
            Float value from file, or default if reading fails.
        """
        content = self._read_sysfs_file(file_path)
        if content is None:
            return default
        
        try:
            return float(content)
        except ValueError:
            logger.error(f"Invalid float in {file_path}: {content}")
            return default
    
    def get_battery_info(self) -> BatteryInfo:
        """Get current battery information snapshot.
        
        Reads all battery-related information from sysfs and returns it
        as a structured BatteryInfo object.
        
        Returns:
            BatteryInfo object with current battery state. Uses safe defaults
            if specific values cannot be read.
            
        Raises:
            RuntimeError: If battery device is not accessible at all.
        """
        battery_path = Path(BATTERY_BASE_PATH)
        if not battery_path.exists():
            raise RuntimeError(
                f"Battery device not found at {BATTERY_BASE_PATH}. "
                "This system may not have a battery or the path is incorrect."
            )
        
        # Read basic battery metrics
        charge_percent = self._read_sysfs_float(BATTERY_CAPACITY_PATH)
        status = self._read_sysfs_file(BATTERY_STATUS_PATH) or "Unknown"
        cycle_count = self._read_sysfs_int(BATTERY_CYCLE_COUNT_PATH)
        
        # Read energy values (in microWh, convert to mWh)
        energy_now_uwh = self._read_sysfs_int(BATTERY_ENERGY_NOW_PATH)
        energy_full_uwh = self._read_sysfs_int(BATTERY_ENERGY_FULL_PATH)
        energy_full_design_uwh = self._read_sysfs_int(BATTERY_ENERGY_FULL_DESIGN_PATH)
        
        energy_now_mwh = energy_now_uwh // MICROWATT_HOUR_TO_MILLIWATT_HOUR_DIVISOR
        energy_full_mwh = energy_full_uwh // MICROWATT_HOUR_TO_MILLIWATT_HOUR_DIVISOR
        energy_full_design_mwh = energy_full_design_uwh // MICROWATT_HOUR_TO_MILLIWATT_HOUR_DIVISOR
        
        # Read power and voltage
        power_now_uw = self._read_sysfs_int(BATTERY_POWER_NOW_PATH)
        power_now_mw = power_now_uw // MICROWATT_HOUR_TO_MILLIWATT_HOUR_DIVISOR
        
        voltage_now_uv = self._read_sysfs_int(BATTERY_VOLTAGE_NOW_PATH)
        voltage_now_v = voltage_now_uv / MICROVOLT_TO_VOLT_DIVISOR
        
        # Read battery identification
        manufacturer = self._read_sysfs_file(BATTERY_MANUFACTURER_PATH) or "Unknown"
        model_name = self._read_sysfs_file(BATTERY_MODEL_NAME_PATH) or "Unknown"
        
        # Read conservation mode status
        conservation_mode_enabled = self._is_conservation_mode_enabled()
        
        # Calculate capacity percentage
        if energy_full_design_mwh > 0:
            capacity_percent = (energy_full_mwh / energy_full_design_mwh) * PERCENTAGE_MULTIPLIER
        else:
            capacity_percent = 0.0
        
        return BatteryInfo(
            charge_percent=charge_percent,
            status=status,
            capacity_percent=round(capacity_percent, 1),
            cycle_count=cycle_count,
            energy_now_mwh=energy_now_mwh,
            energy_full_mwh=energy_full_mwh,
            energy_full_design_mwh=energy_full_design_mwh,
            power_now_mw=power_now_mw,
            voltage_now_v=round(voltage_now_v, 2),
            manufacturer=manufacturer,
            model_name=model_name,
            conservation_mode_enabled=conservation_mode_enabled
        )
    
    def _is_conservation_mode_enabled(self) -> bool:
        """Check if Lenovo conservation mode is enabled.
        
        Returns:
            True if conservation mode is enabled (value is 1), False otherwise.
        """
        if not self.is_conservation_mode_available():
            return False
        
        value = self._read_sysfs_int(CONSERVATION_MODE_PATH, default=-1)
        return value == 1
    
    def get_cpu_info(self) -> CPUInfo:
        """Get current CPU state information.
        
        Reads CPU frequency scaling information and Intel P-State settings
        from sysfs.
        
        Returns:
            CPUInfo object with current CPU state. Uses safe defaults if
            specific values cannot be read.
            
        Raises:
            RuntimeError: If CPU frequency scaling interface is not accessible.
        """
        cpu_path = Path(CPU_BASE_PATH)
        if not cpu_path.exists():
            raise RuntimeError(
                f"CPU frequency scaling not found at {CPU_BASE_PATH}. "
                "This system may not support cpufreq."
            )
        
        # Read CPU governor and frequencies
        governor = self._read_sysfs_file(CPU_GOVERNOR_PATH) or "unknown"
        min_freq_khz = self._read_sysfs_int(CPU_MIN_FREQ_PATH)
        max_freq_khz = self._read_sysfs_int(CPU_MAX_FREQ_PATH)
        current_freq_khz = self._read_sysfs_int(CPU_CURRENT_FREQ_PATH)
        
        # Read energy performance preference
        epp = self._read_sysfs_file(CPU_EPP_PATH) or "unknown"
        
        # Read turbo boost status (no_turbo: 0=enabled, 1=disabled)
        turbo_disabled = self._read_sysfs_int(INTEL_PSTATE_NO_TURBO_PATH, default=0)
        turbo_enabled = turbo_disabled == 0
        
        return CPUInfo(
            governor=governor,
            turbo_enabled=turbo_enabled,
            min_freq_khz=min_freq_khz,
            max_freq_khz=max_freq_khz,
            current_freq_khz=current_freq_khz,
            energy_performance_preference=epp
        )
    
    def is_conservation_mode_available(self) -> bool:
        """Check if conservation mode is supported on this system.
        
        Conservation mode is a Lenovo-specific feature that limits battery
        charge to 60% to extend battery lifespan when the laptop is primarily
        used plugged in.
        
        Returns:
            True if conservation mode sysfs file exists and is readable,
            False otherwise.
        """
        path = Path(CONSERVATION_MODE_PATH)
        if not path.exists():
            logger.debug("Conservation mode not available on this system")
            return False
        
        # Try to read to verify it's actually accessible
        content = self._read_sysfs_file(CONSERVATION_MODE_PATH)
        return content is not None


def main() -> None:
    """Example usage and manual testing of BatteryMonitor.
    
    This function demonstrates how to use the BatteryMonitor class and
    prints formatted battery and CPU information to the console.
    """
    print("=" * 70)
    print("Battery Manager - System Monitor Test")
    print("=" * 70)
    
    try:
        monitor = BatteryMonitor()
        
        # Test battery information
        print("\n📊 BATTERY INFORMATION")
        print("-" * 70)
        battery_info = monitor.get_battery_info()
        
        print(f"Manufacturer: {battery_info.manufacturer}")
        print(f"Model: {battery_info.model_name}")
        print(f"\nCharge: {battery_info.charge_percent}%")
        print(f"Status: {battery_info.status}")
        print(f"Health: {battery_info.health_percent}%")
        print(f"Cycles: {battery_info.cycle_count}")
        print(f"\nCapacity: {battery_info.energy_full_mwh} / {battery_info.energy_full_design_mwh} mWh")
        print(f"Current Energy: {battery_info.energy_now_mwh} mWh")
        print(f"Power Draw: {battery_info.power_now_mw} mW")
        print(f"Voltage: {battery_info.voltage_now_v} V")
        
        if battery_info.time_remaining_minutes is not None:
            hours = battery_info.time_remaining_minutes // MINUTES_PER_HOUR
            minutes = battery_info.time_remaining_minutes % MINUTES_PER_HOUR
            print(f"Time Remaining: {hours}h {minutes}min")
        else:
            print("Time Remaining: N/A")
        
        if monitor.is_conservation_mode_available():
            mode_status = "ON" if battery_info.conservation_mode_enabled else "OFF"
            print(f"\nConservation Mode: {mode_status}")
        else:
            print("\nConservation Mode: Not available on this system")
        
        # Test CPU information
        print("\n⚙️  CPU INFORMATION")
        print("-" * 70)
        cpu_info = monitor.get_cpu_info()
        
        print(f"Governor: {cpu_info.governor}")
        print(f"Turbo Boost: {'Enabled' if cpu_info.turbo_enabled else 'Disabled'}")
        print(f"Frequency Range: {cpu_info.min_freq_khz // 1000} - {cpu_info.max_freq_khz // 1000} MHz")
        print(f"Current Frequency: {cpu_info.current_freq_khz // 1000} MHz")
        print(f"Energy Performance Preference: {cpu_info.energy_performance_preference}")
        
        print("\n" + "=" * 70)
        print("✅ All tests completed successfully!")
        print("=" * 70)
        
    except RuntimeError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nThis application requires a Linux system with battery support.")
    except Exception as e:
        logger.exception("Unexpected error during testing")
        print(f"\n❌ UNEXPECTED ERROR: {e}")


if __name__ == "__main__":
    main()
