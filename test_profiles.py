#!/usr/bin/env python3
"""
Test script to validate ProfileManager with real profile application.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from profiles import ProfileManager, PerformanceProfile
from battery_monitor import BatteryMonitor

def test_apply_balanced_profile() -> None:
    """Test applying the Balanced profile."""
    print("\n⚡ Testing BALANCED Profile Application")
    print("-" * 70)
    
    manager = ProfileManager()
    monitor = BatteryMonitor()
    
    print("Applying Balanced profile...")
    print("  - CPU Governor: powersave")
    print("  - Turbo Boost: enabled")
    print("  - Conservation Mode: OFF\n")
    
    try:
        success = manager.apply_profile(manager.BALANCED)
        
        if success:
            print("\n✅ Profile applied successfully!")
            
            # Verify settings
            import time
            time.sleep(0.5)
            
            cpu_info = monitor.get_cpu_info()
            battery_info = monitor.get_battery_info()
            
            print("\nVerifying system state:")
            print(f"  CPU Governor: {cpu_info.governor}")
            print(f"  Turbo Boost: {'Enabled' if cpu_info.turbo_enabled else 'Disabled'}")
            print(f"  Conservation Mode: {'ON' if battery_info.conservation_mode_enabled else 'OFF'}")
        else:
            print("\n⚠️  Profile applied with some errors (check logs)")
    
    except Exception as e:
        print(f"\n❌ Failed to apply profile: {e}")

def test_create_custom_profile() -> None:
    """Test creating a custom profile."""
    print("\n🔧 Testing Custom Profile Creation")
    print("-" * 70)
    
    manager = ProfileManager()
    
    custom = PerformanceProfile(
        name="Test Gaming",
        cpu_governor="performance",
        turbo_enabled=True,
        conservation_mode=False,
        description="Test profile for gaming - max performance"
    )
    
    try:
        print(f"Creating custom profile: {custom.name}")
        success = manager.create_custom_profile(custom)
        
        if success:
            print("✅ Custom profile created successfully!")
            
            # Verify it's in the list
            all_profiles = manager.get_all_profiles()
            names = [p.name for p in all_profiles]
            print(f"\nAll available profiles: {', '.join(names)}")
            
            # Clean up - delete the test profile
            print(f"\nCleaning up - deleting test profile...")
            manager.delete_custom_profile("Test Gaming")
            print("✅ Test profile deleted")
        else:
            print("❌ Failed to create custom profile")
    
    except ValueError as e:
        print(f"❌ Validation error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main() -> None:
    """Run all profile tests."""
    print("=" * 70)
    print("Profile Manager - Real Test (requires sudo)")
    print("=" * 70)
    print("\n⚠️  This will modify system settings temporarily\n")
    
    input("Press ENTER to continue or Ctrl+C to cancel...")
    
    test_apply_balanced_profile()
    test_create_custom_profile()
    
    print("\n" + "=" * 70)
    print("✅ All profile tests completed!")
    print("=" * 70)

if __name__ == "__main__":
    main()
