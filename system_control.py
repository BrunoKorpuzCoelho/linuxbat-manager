#!/usr/bin/env python3
"""
System control module for managing battery and CPU settings.

This module provides classes to execute system-level changes that require
elevated privileges, such as toggling conservation mode, changing CPU
governors, and controlling turbo boost.
"""

# Standard library imports
import glob
import logging
import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Conservation mode path (Lenovo specific)
CONSERVATION_MODE_PATH: str = "/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/conservation_mode"

# CPU paths
CPU_GOVERNOR_PATTERN: str = "/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
INTEL_PSTATE_NO_TURBO_PATH: str = "/sys/devices/system/cpu/intel_pstate/no_turbo"

# Command execution settings
SUDO_COMMAND: str = "sudo"
TEE_COMMAND: str = "tee"
ECHO_COMMAND: str = "echo"
COMMAND_TIMEOUT_SECONDS: int = 10

# Conservation mode values
CONSERVATION_MODE_ENABLED_VALUE: str = "1"
CONSERVATION_MODE_DISABLED_VALUE: str = "0"

# Turbo boost values (note: inverted logic - no_turbo)
TURBO_BOOST_ENABLED_VALUE: str = "0"
TURBO_BOOST_DISABLED_VALUE: str = "1"


class CPUGovernor(Enum):
    """Available CPU frequency governors.
    
    Governors control how the CPU frequency scaling behaves:
    - POWERSAVE: Prioritizes power efficiency, lower frequencies
    - PERFORMANCE: Prioritizes performance, higher frequencies
    - ONDEMAND: Dynamically adjusts based on load (if available)
    - CONSERVATIVE: Similar to ondemand but more gradual changes
    - SCHEDUTIL: Uses scheduler information for frequency decisions
    """
    
    POWERSAVE = "powersave"
    PERFORMANCE = "performance"
    ONDEMAND = "ondemand"
    CONSERVATIVE = "conservative"
    SCHEDUTIL = "schedutil"


class SystemControlError(Exception):
    """Base exception for system control operations.
    
    Raised when system-level operations fail due to permissions,
    invalid paths, or command execution errors.
    """
    pass


class PermissionError(SystemControlError):
    """Raised when operation requires elevated privileges.
    
    This typically indicates that sudo access is needed but not available
    or the user declined the privilege escalation prompt.
    """
    pass


class SystemController:
    """Handles system-level changes requiring elevated privileges.
    
    This class provides methods to modify system settings that affect
    battery conservation, CPU performance, and power management. All
    operations that modify system files require sudo privileges.
    
    The class uses subprocess to execute commands with proper error
    handling and logging for all operations.
    """
    
    def __init__(self) -> None:
        """Initialize system controller.
        
        Validates that critical system paths exist and logs warnings
        if certain features are unavailable.
        """
        self._validate_paths()
    
    def _validate_paths(self) -> None:
        """Validate that system control paths exist.
        
        Checks for the existence of conservation mode and turbo boost
        control paths. Logs warnings if features are unavailable but
        does not raise exceptions.
        """
        if not Path(CONSERVATION_MODE_PATH).exists():
            logger.warning(
                "Conservation mode path not found. "
                "This feature may not be available on this system."
            )
        
        if not Path(INTEL_PSTATE_NO_TURBO_PATH).exists():
            logger.warning(
                "Intel P-State turbo control not found. "
                "Turbo boost control may not be available."
            )
    
    def _execute_sudo_command(
        self, 
        command: List[str],
        input_data: Optional[str] = None
    ) -> bool:
        """Safely execute a command with sudo privileges.
        
        Args:
            command: Command and arguments as a list
            input_data: Optional string to pipe to stdin
            
        Returns:
            True if command executed successfully, False otherwise.
            
        Raises:
            PermissionError: If sudo access is denied or unavailable.
            SystemControlError: If command execution fails.
        """
        try:
            logger.info(f"Executing sudo command: {' '.join(command)}")
            
            process = subprocess.run(
                command,
                input=input_data,
                text=True,
                capture_output=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                check=False
            )
            
            if process.returncode != 0:
                error_msg = process.stderr.strip()
                logger.error(f"Command failed: {error_msg}")
                
                # Check for permission-related errors
                if "permission denied" in error_msg.lower() or "not authorized" in error_msg.lower():
                    raise PermissionError(
                        f"Sudo access denied. Error: {error_msg}"
                    )
                
                raise SystemControlError(
                    f"Command execution failed: {error_msg}"
                )
            
            logger.info("Command executed successfully")
            return True
        
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {COMMAND_TIMEOUT_SECONDS} seconds")
            raise SystemControlError(
                f"Command execution timed out after {COMMAND_TIMEOUT_SECONDS} seconds"
            )
        
        except FileNotFoundError as e:
            logger.error(f"Command not found: {e}")
            raise SystemControlError(
                f"Required command not found on system: {e}"
            )
    
    def _write_to_sysfs(self, file_path: str, value: str) -> bool:
        """Write a value to a sysfs file using sudo.
        
        Args:
            file_path: Absolute path to the sysfs file
            value: Value to write to the file
            
        Returns:
            True if write was successful, False otherwise.
            
        Raises:
            SystemControlError: If the file path doesn't exist or write fails.
            PermissionError: If sudo access is denied.
        """
        path = Path(file_path)
        if not path.exists():
            raise SystemControlError(
                f"Cannot write to {file_path}: file does not exist"
            )
        
        # Check if already running as root
        if os.geteuid() == 0:
            # Running as root, write directly
            try:
                with open(file_path, 'w') as f:
                    f.write(f"{value}\n")
                logger.info(f"Wrote '{value}' to {file_path} (as root)")
                return True
            except Exception as e:
                logger.error(f"Failed to write to {file_path}: {e}")
                raise SystemControlError(f"Write failed: {e}")
        else:
            # Use echo + tee to write with sudo
            command = [SUDO_COMMAND, TEE_COMMAND, file_path]
            input_data = f"{value}\n"
            
            return self._execute_sudo_command(command, input_data)
    
    def set_conservation_mode(self, enabled: bool) -> bool:
        """Enable or disable battery conservation mode (60% limit).
        
        Conservation mode is a Lenovo-specific feature that limits battery
        charging to 60% to extend battery lifespan when the laptop is
        primarily used while plugged in.
        
        Args:
            enabled: True to enable 60% charge limit, False to allow full charge
            
        Returns:
            True if the mode was changed successfully, False otherwise.
            
        Raises:
            SystemControlError: If conservation mode is not available or
                operation fails.
            PermissionError: If sudo access is denied.
        """
        if not Path(CONSERVATION_MODE_PATH).exists():
            raise SystemControlError(
                "Conservation mode is not available on this system. "
                "This feature is specific to certain Lenovo laptops."
            )
        
        value = CONSERVATION_MODE_ENABLED_VALUE if enabled else CONSERVATION_MODE_DISABLED_VALUE
        mode_str = "enabled (60% limit)" if enabled else "disabled (full charge)"
        
        logger.info(f"Setting conservation mode to: {mode_str}")
        
        try:
            result = self._write_to_sysfs(CONSERVATION_MODE_PATH, value)
            if result:
                logger.info(f"Conservation mode successfully {mode_str}")
            return result
        
        except (SystemControlError, PermissionError) as e:
            logger.error(f"Failed to set conservation mode: {e}")
            raise
    
    def set_cpu_governor(self, governor: CPUGovernor) -> bool:
        """Set CPU frequency scaling governor for all cores.
        
        The governor controls how the CPU frequency scaling behaves:
        - powersave: Lower frequencies for power efficiency
        - performance: Higher frequencies for maximum performance
        
        Args:
            governor: CPUGovernor enum value specifying the desired governor
            
        Returns:
            True if the governor was set successfully, False otherwise.
            
        Raises:
            SystemControlError: If the governor cannot be set.
            PermissionError: If sudo access is denied.
        """
        logger.info(f"Setting CPU governor to: {governor.value}")
        
        # Find all CPU governor files using glob
        governor_files = glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor")
        
        if not governor_files:
            raise SystemControlError(
                "No CPU frequency scaling governors found. "
                "CPU frequency scaling may not be available."
            )
        
        logger.debug(f"Found {len(governor_files)} CPU cores to configure")
        
        # Write to each CPU core's governor file
        success_count = 0
        for governor_file in governor_files:
            try:
                self._write_to_sysfs(governor_file, governor.value)
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to set governor for {governor_file}: {e}")
        
        if success_count == 0:
            raise SystemControlError("Failed to set governor on any CPU core")
        
        logger.info(
            f"CPU governor successfully set to {governor.value} "
            f"on {success_count}/{len(governor_files)} cores"
        )
        return True
    
    def set_turbo_boost(self, enabled: bool) -> bool:
        """Enable or disable Intel Turbo Boost.
        
        Turbo Boost allows the CPU to run at higher frequencies than the
        base clock speed when thermal headroom is available. Disabling it
        can reduce power consumption and heat generation.
        
        Note: The sysfs file uses inverted logic (no_turbo):
        - 0 means turbo is enabled
        - 1 means turbo is disabled
        
        Args:
            enabled: True to enable turbo boost, False to disable it
            
        Returns:
            True if turbo boost state was changed successfully, False otherwise.
            
        Raises:
            SystemControlError: If turbo boost control is not available or
                operation fails.
            PermissionError: If sudo access is denied.
        """
        if not Path(INTEL_PSTATE_NO_TURBO_PATH).exists():
            raise SystemControlError(
                "Intel Turbo Boost control is not available on this system. "
                "This feature requires Intel P-State driver."
            )
        
        # Inverted logic: no_turbo=0 means enabled, no_turbo=1 means disabled
        value = TURBO_BOOST_ENABLED_VALUE if enabled else TURBO_BOOST_DISABLED_VALUE
        state_str = "enabled" if enabled else "disabled"
        
        logger.info(f"Setting turbo boost to: {state_str}")
        
        try:
            result = self._write_to_sysfs(INTEL_PSTATE_NO_TURBO_PATH, value)
            if result:
                logger.info(f"Turbo boost successfully {state_str}")
            return result
        
        except (SystemControlError, PermissionError) as e:
            logger.error(f"Failed to set turbo boost: {e}")
            raise
    
    def is_conservation_mode_available(self) -> bool:
        """Check if conservation mode is available on this system.
        
        Returns:
            True if conservation mode sysfs file exists, False otherwise.
        """
        return Path(CONSERVATION_MODE_PATH).exists()
    
    def is_turbo_boost_available(self) -> bool:
        """Check if turbo boost control is available on this system.
        
        Returns:
            True if Intel P-State turbo control exists, False otherwise.
        """
        return Path(INTEL_PSTATE_NO_TURBO_PATH).exists()


def main() -> None:
    """Example usage and manual testing of SystemController.
    
    This function demonstrates how to use the SystemController class.
    WARNING: This will actually modify system settings if run with sudo.
    """
    print("=" * 70)
    print("Battery Manager - System Controller Test")
    print("=" * 70)
    print("\n⚠️  WARNING: This test will modify system settings!")
    print("Make sure you understand what each operation does.\n")
    
    controller = SystemController()
    
    # Check available features
    print("📋 AVAILABLE FEATURES")
    print("-" * 70)
    print(f"Conservation Mode: {'✅ Available' if controller.is_conservation_mode_available() else '❌ Not available'}")
    print(f"Turbo Boost Control: {'✅ Available' if controller.is_turbo_boost_available() else '❌ Not available'}")
    
    # Example: Test conservation mode (commented out for safety)
    print("\n🔋 CONSERVATION MODE TEST (commented out for safety)")
    print("-" * 70)
    print("# To test, uncomment the following lines:")
    print("# controller.set_conservation_mode(True)   # Enable 60% limit")
    print("# controller.set_conservation_mode(False)  # Disable limit")
    
    # Example: Test CPU governor (commented out for safety)
    print("\n⚙️  CPU GOVERNOR TEST (commented out for safety)")
    print("-" * 70)
    print("# To test, uncomment the following lines:")
    print("# controller.set_cpu_governor(CPUGovernor.POWERSAVE)")
    print("# controller.set_cpu_governor(CPUGovernor.PERFORMANCE)")
    
    # Example: Test turbo boost (commented out for safety)
    print("\n🚀 TURBO BOOST TEST (commented out for safety)")
    print("-" * 70)
    print("# To test, uncomment the following lines:")
    print("# controller.set_turbo_boost(False)  # Disable turbo")
    print("# controller.set_turbo_boost(True)   # Enable turbo")
    
    print("\n" + "=" * 70)
    print("✅ System controller initialized successfully!")
    print("Uncomment test sections to try actual system modifications.")
    print("=" * 70)


if __name__ == "__main__":
    main()
