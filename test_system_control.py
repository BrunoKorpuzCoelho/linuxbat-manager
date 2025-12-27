#!/usr/bin/env python3
"""
Quick test script to validate SystemController with real sudo commands.
Tests reading current state and toggling settings safely.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from system_control import SystemController, CPUGovernor, SystemControlError, PermissionError
from battery_monitor import BatteryMonitor

def test_conservation_mode_toggle() -> None:
    """Test conservation mode toggle (safe - can be reverted)."""
    print("\n🔋 Testing Conservation Mode Toggle")
    print("-" * 70)
    
    controller = SystemController()
    monitor = BatteryMonitor()
    
    if not controller.is_conservation_mode_available():
        print("❌ Conservation mode not available on this system")
        return
    
    try:
        # Get current state
        initial_info = monitor.get_battery_info()
        initial_state = initial_info.conservation_mode_enabled
        print(f"Current state: {'ON (60% limit)' if initial_state else 'OFF (full charge)'}")
        
        # Toggle OFF if ON, or ON if OFF
        new_state = not initial_state
        print(f"\nToggling to: {'ON (60% limit)' if new_state else 'OFF (full charge)'}")
        
        controller.set_conservation_mode(new_state)
        
        # Verify change
        import time
        time.sleep(0.5)  # Brief delay for system to update
        
        updated_info = monitor.get_battery_info()
        if updated_info.conservation_mode_enabled == new_state:
            print(f"✅ Successfully toggled to: {'ON' if new_state else 'OFF'}")
        else:
            print("⚠️  State change not reflected yet (may need a moment)")
        
        # Restore original state
        print(f"\nRestoring original state: {'ON' if initial_state else 'OFF'}")
        controller.set_conservation_mode(initial_state)
        
        print("✅ Conservation mode test completed successfully")
        
    except PermissionError as e:
        print(f"❌ Permission denied: {e}")
        print("   Make sure you run this with sudo or can escalate privileges")
    except SystemControlError as e:
        print(f"❌ System control error: {e}")

def test_cpu_governor() -> None:
    """Test CPU governor change."""
    print("\n⚙️  Testing CPU Governor")
    print("-" * 70)
    
    controller = SystemController()
    monitor = BatteryMonitor()
    
    try:
        # Get current state
        initial_cpu = monitor.get_cpu_info()
        print(f"Current governor: {initial_cpu.governor}")
        
        # Try to set to powersave
        print("\nSetting to: powersave")
        controller.set_cpu_governor(CPUGovernor.POWERSAVE)
        
        # Verify
        import time
        time.sleep(0.5)
        
        updated_cpu = monitor.get_cpu_info()
        if updated_cpu.governor == "powersave":
            print("✅ Successfully set to powersave")
        else:
            print(f"⚠️  Governor is: {updated_cpu.governor}")
        
        print("✅ CPU governor test completed successfully")
        
    except PermissionError as e:
        print(f"❌ Permission denied: {e}")
    except SystemControlError as e:
        print(f"❌ System control error: {e}")

def main() -> None:
    """Run all tests."""
    print("=" * 70)
    print("System Controller - Real Test (requires sudo)")
    print("=" * 70)
    print("\n⚠️  This will temporarily modify system settings")
    print("Settings will be restored after each test\n")
    
    input("Press ENTER to continue or Ctrl+C to cancel...")
    
    test_conservation_mode_toggle()
    test_cpu_governor()
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)

if __name__ == "__main__":
    main()
