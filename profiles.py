#!/usr/bin/env python3
"""
Performance profile management module.

This module provides classes to define, store, load, and apply system
performance profiles that combine battery conservation, CPU governor,
and turbo boost settings for different use cases.
"""

# Standard library imports
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any

# Local imports
from system_control import SystemController, CPUGovernor, SystemControlError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default profile configuration file location
DEFAULT_CONFIG_DIR: str = str(Path.home() / ".config" / "linuxbat-manager")
DEFAULT_CONFIG_FILE: str = "profiles.json"
CONFIG_FILE_ENCODING: str = "utf-8"
JSON_INDENT_SPACES: int = 4


@dataclass
class PerformanceProfile:
    """Performance profile configuration.
    
    A profile defines a complete system configuration including CPU
    governor, turbo boost state, and battery conservation mode. Profiles
    can be predefined or custom-created by users.
    
    Attributes:
        name: Unique profile name
        cpu_governor: CPU frequency scaling governor (powersave/performance/etc.)
        turbo_enabled: Whether Intel Turbo Boost should be enabled
        conservation_mode: Whether battery conservation mode (60% limit) is active
        description: Human-readable description of the profile's purpose
    """
    
    name: str
    cpu_governor: str
    turbo_enabled: bool
    conservation_mode: bool
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the profile.
        """
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PerformanceProfile':
        """Create profile from dictionary.
        
        Args:
            data: Dictionary containing profile data
            
        Returns:
            PerformanceProfile instance created from the dictionary.
            
        Raises:
            KeyError: If required fields are missing.
            TypeError: If field types are incorrect.
        """
        return PerformanceProfile(
            name=str(data['name']),
            cpu_governor=str(data['cpu_governor']),
            turbo_enabled=bool(data['turbo_enabled']),
            conservation_mode=bool(data['conservation_mode']),
            description=str(data['description'])
        )


class ProfileManager:
    """Manages performance profiles and applies them to the system.
    
    This class handles predefined and custom profiles, providing methods
    to create, save, load, delete, and apply profiles. Custom profiles
    are persisted to a JSON configuration file.
    """
    
    # Predefined profiles
    BATTERY_SAVER = PerformanceProfile(
        name="Battery Saver",
        cpu_governor=CPUGovernor.POWERSAVE.value,
        turbo_enabled=False,
        conservation_mode=True,
        description="Maximum battery life - low performance, 60% charge limit"
    )
    
    BALANCED = PerformanceProfile(
        name="Balanced",
        cpu_governor=CPUGovernor.PERFORMANCE.value,
        turbo_enabled=False,  # Performance sem turbo = balanced
        conservation_mode=False,
        description="Balanced performance and efficiency - recommended for most users"
    )
    
    PERFORMANCE = PerformanceProfile(
        name="Performance",
        cpu_governor=CPUGovernor.PERFORMANCE.value,
        turbo_enabled=True,
        conservation_mode=False,
        description="Maximum performance - high power consumption, no charge limits"
    )
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize profile manager.
        
        Args:
            config_path: Optional custom path to configuration directory.
                        If None, uses default (~/.config/linuxbat-manager).
        """
        if config_path is None:
            config_path = DEFAULT_CONFIG_DIR
        
        self.config_dir = Path(config_path)
        self.config_file = self.config_dir / DEFAULT_CONFIG_FILE
        self.controller = SystemController()
        self._custom_profiles: Dict[str, PerformanceProfile] = {}
        
        self._ensure_config_directory()
        self._load_custom_profiles()
    
    def _ensure_config_directory(self) -> None:
        """Create configuration directory if it doesn't exist.
        
        Creates the directory with appropriate permissions (0o755).
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Configuration directory ready: {self.config_dir}")
        except Exception as e:
            logger.error(f"Failed to create config directory {self.config_dir}: {e}")
            raise SystemControlError(
                f"Cannot create configuration directory: {e}"
            )
    
    def _load_custom_profiles(self) -> None:
        """Load custom profiles from JSON configuration file.
        
        If the file doesn't exist or is invalid, starts with an empty
        custom profile list. Logs warnings for invalid profiles but
        doesn't fail.
        """
        if not self.config_file.exists():
            logger.info("No custom profiles file found, starting fresh")
            return
        
        try:
            with open(self.config_file, 'r', encoding=CONFIG_FILE_ENCODING) as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'profiles' not in data:
                logger.warning("Invalid profiles file format, ignoring")
                return
            
            for profile_data in data['profiles']:
                try:
                    profile = PerformanceProfile.from_dict(profile_data)
                    self._custom_profiles[profile.name] = profile
                    logger.debug(f"Loaded custom profile: {profile.name}")
                except (KeyError, TypeError) as e:
                    logger.warning(f"Skipping invalid profile: {e}")
            
            logger.info(f"Loaded {len(self._custom_profiles)} custom profile(s)")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse profiles file: {e}")
        except Exception as e:
            logger.error(f"Error loading custom profiles: {e}")
    
    def _save_custom_profiles(self) -> bool:
        """Save custom profiles to JSON configuration file.
        
        Returns:
            True if profiles were saved successfully, False otherwise.
        """
        try:
            data = {
                'profiles': [profile.to_dict() for profile in self._custom_profiles.values()]
            }
            
            with open(self.config_file, 'w', encoding=CONFIG_FILE_ENCODING) as f:
                json.dump(data, f, indent=JSON_INDENT_SPACES)
            
            logger.info(f"Saved {len(self._custom_profiles)} custom profile(s)")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save custom profiles: {e}")
            return False
    
    def get_predefined_profiles(self) -> List[PerformanceProfile]:
        """Get list of predefined profiles.
        
        Returns:
            List of built-in performance profiles.
        """
        return [
            self.BATTERY_SAVER,
            self.BALANCED,
            self.PERFORMANCE
        ]
    
    def get_custom_profiles(self) -> List[PerformanceProfile]:
        """Get list of custom user-created profiles.
        
        Returns:
            List of custom performance profiles.
        """
        return list(self._custom_profiles.values())
    
    def get_all_profiles(self) -> List[PerformanceProfile]:
        """Get list of all available profiles (predefined + custom).
        
        Returns:
            Combined list of predefined and custom profiles.
        """
        return self.get_predefined_profiles() + self.get_custom_profiles()
    
    def get_profile_by_name(self, name: str) -> Optional[PerformanceProfile]:
        """Find a profile by its name.
        
        Args:
            name: Profile name to search for (case-sensitive)
            
        Returns:
            PerformanceProfile if found, None otherwise.
        """
        for profile in self.get_all_profiles():
            if profile.name == name:
                return profile
        return None
    
    def apply_profile(self, profile: PerformanceProfile) -> bool:
        """Apply a profile to the system.
        
        Applies all settings defined in the profile: CPU governor,
        turbo boost, and conservation mode. If any setting fails,
        continues to apply others and logs the errors.
        
        Args:
            profile: Performance profile to apply
            
        Returns:
            True if all settings were applied successfully, False if
            any setting failed to apply.
        """
        logger.info(f"Applying profile: {profile.name}")
        success = True
        
        # Apply CPU governor
        try:
            governor = CPUGovernor(profile.cpu_governor)
            self.controller.set_cpu_governor(governor)
            logger.info(f"✓ CPU governor set to: {profile.cpu_governor}")
        except (ValueError, SystemControlError) as e:
            logger.error(f"✗ Failed to set CPU governor: {e}")
            success = False
        
        # Apply turbo boost
        try:
            if self.controller.is_turbo_boost_available():
                self.controller.set_turbo_boost(profile.turbo_enabled)
                state = "enabled" if profile.turbo_enabled else "disabled"
                logger.info(f"✓ Turbo boost {state}")
            else:
                logger.warning("Turbo boost control not available on this system")
        except SystemControlError as e:
            logger.error(f"✗ Failed to set turbo boost: {e}")
            success = False
        
        # Apply conservation mode
        try:
            if self.controller.is_conservation_mode_available():
                self.controller.set_conservation_mode(profile.conservation_mode)
                state = "enabled (60% limit)" if profile.conservation_mode else "disabled"
                logger.info(f"✓ Conservation mode {state}")
            else:
                logger.warning("Conservation mode not available on this system")
        except SystemControlError as e:
            logger.error(f"✗ Failed to set conservation mode: {e}")
            success = False
        
        if success:
            logger.info(f"Profile '{profile.name}' applied successfully")
        else:
            logger.warning(f"Profile '{profile.name}' applied with some errors")
        
        return success
    
    def create_custom_profile(self, profile: PerformanceProfile) -> bool:
        """Create and save a custom profile.
        
        Args:
            profile: Performance profile to create
            
        Returns:
            True if profile was created and saved successfully, False otherwise.
            
        Raises:
            ValueError: If a profile with the same name already exists or
                       if the profile name matches a predefined profile.
        """
        # Check for duplicate names (including predefined profiles)
        if self.get_profile_by_name(profile.name) is not None:
            raise ValueError(
                f"Profile '{profile.name}' already exists. "
                "Choose a different name."
            )
        
        # Validate governor value
        try:
            CPUGovernor(profile.cpu_governor)
        except ValueError:
            valid_governors = [g.value for g in CPUGovernor]
            raise ValueError(
                f"Invalid CPU governor '{profile.cpu_governor}'. "
                f"Valid options: {', '.join(valid_governors)}"
            )
        
        logger.info(f"Creating custom profile: {profile.name}")
        self._custom_profiles[profile.name] = profile
        
        if self._save_custom_profiles():
            logger.info(f"Custom profile '{profile.name}' created successfully")
            return True
        else:
            # Rollback on save failure
            del self._custom_profiles[profile.name]
            logger.error(f"Failed to save custom profile '{profile.name}'")
            return False
    
    def delete_custom_profile(self, name: str) -> bool:
        """Delete a custom profile.
        
        Predefined profiles cannot be deleted.
        
        Args:
            name: Name of the custom profile to delete
            
        Returns:
            True if profile was deleted successfully, False otherwise.
            
        Raises:
            ValueError: If trying to delete a predefined profile or if
                       the profile doesn't exist.
        """
        # Check if it's a predefined profile
        predefined_names = [p.name for p in self.get_predefined_profiles()]
        if name in predefined_names:
            raise ValueError(
                f"Cannot delete predefined profile '{name}'. "
                "Only custom profiles can be deleted."
            )
        
        # Check if profile exists
        if name not in self._custom_profiles:
            raise ValueError(
                f"Custom profile '{name}' not found."
            )
        
        logger.info(f"Deleting custom profile: {name}")
        del self._custom_profiles[name]
        
        if self._save_custom_profiles():
            logger.info(f"Custom profile '{name}' deleted successfully")
            return True
        else:
            logger.error(f"Failed to save after deleting profile '{name}'")
            return False


def main() -> None:
    """Example usage and manual testing of ProfileManager.
    
    This function demonstrates profile management operations including
    listing, creating, and applying profiles.
    """
    print("=" * 70)
    print("Battery Manager - Profile Manager Test")
    print("=" * 70)
    
    manager = ProfileManager()
    
    # Show predefined profiles
    print("\n📋 PREDEFINED PROFILES")
    print("-" * 70)
    for profile in manager.get_predefined_profiles():
        print(f"\n{profile.name}")
        print(f"  CPU Governor: {profile.cpu_governor}")
        print(f"  Turbo Boost: {'Enabled' if profile.turbo_enabled else 'Disabled'}")
        print(f"  Conservation Mode: {'ON (60%)' if profile.conservation_mode else 'OFF'}")
        print(f"  Description: {profile.description}")
    
    # Show custom profiles
    print("\n📋 CUSTOM PROFILES")
    print("-" * 70)
    custom = manager.get_custom_profiles()
    if custom:
        for profile in custom:
            print(f"\n{profile.name}")
            print(f"  CPU Governor: {profile.cpu_governor}")
            print(f"  Turbo Boost: {'Enabled' if profile.turbo_enabled else 'Disabled'}")
            print(f"  Conservation Mode: {'ON (60%)' if profile.conservation_mode else 'OFF'}")
            print(f"  Description: {profile.description}")
    else:
        print("No custom profiles found")
    
    # Example: Create a custom profile (commented for safety)
    print("\n🔧 CREATE CUSTOM PROFILE (commented out for safety)")
    print("-" * 70)
    print("# Example:")
    print("# custom_profile = PerformanceProfile(")
    print("#     name='Gaming',")
    print("#     cpu_governor='performance',")
    print("#     turbo_enabled=True,")
    print("#     conservation_mode=False,")
    print("#     description='Optimized for gaming performance'")
    print("# )")
    print("# manager.create_custom_profile(custom_profile)")
    
    # Example: Apply a profile (commented for safety)
    print("\n⚡ APPLY PROFILE (commented out for safety)")
    print("-" * 70)
    print("# To apply a profile:")
    print("# manager.apply_profile(manager.BALANCED)")
    print("# manager.apply_profile(manager.BATTERY_SAVER)")
    print("# manager.apply_profile(manager.PERFORMANCE)")
    
    print("\n" + "=" * 70)
    print(f"✅ Profile manager initialized successfully!")
    print(f"Configuration: {manager.config_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
