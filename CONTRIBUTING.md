# Contributing to Battery Manager Pro

First off, thank you for considering contributing to Battery Manager Pro! 🎉

## Code of Conduct

This project adheres to Clean Code principles and Python best practices. By participating, you are expected to uphold these standards.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (code snippets, screenshots)
- **Describe the behavior you observed** and what you expected
- **Include your environment details**:
  - OS version (e.g., Ubuntu 24.04 LTS)
  - Python version
  - Laptop model
  - Battery information

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a step-by-step description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **Include mockups or examples** if applicable

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the coding standards** (see below)
3. **Test your changes thoroughly**
4. **Update documentation** if needed
5. **Write a clear commit message**
6. **Submit a pull request**

## Coding Standards

### Python Style Guide (PEP 8)

All code must follow PEP 8 standards:

```python
# Good
def calculate_battery_health(
    design_capacity: int,
    current_capacity: int
) -> float:
    """Calculate battery health percentage.

    Args:
        design_capacity: Original battery capacity in mWh
        current_capacity: Current battery capacity in mWh

    Returns:
        Battery health as percentage (0.0-100.0)
    """
    if design_capacity <= 0:
        return 0.0

    return (current_capacity / design_capacity) * 100.0

# Bad
def calc(d,c):
    return (c/d)*100
```

### Type Hints

**Required** for all function signatures:

```python
# Good
def get_cpu_frequency(cpu_id: int) -> float:
    """Get current CPU frequency for specific core."""
    ...

# Bad
def get_cpu_frequency(cpu_id):
    """Get current CPU frequency for specific core."""
    ...
```

### Docstrings

**Required** for all public functions, classes, and methods:

```python
# Good
def apply_profile(self, profile: PerformanceProfile) -> bool:
    """Apply a performance profile to the system.

    This method applies all settings defined in the profile,
    including CPU governor, turbo boost, and conservation mode.

    Args:
        profile: The PerformanceProfile to apply

    Returns:
        True if all settings applied successfully, False otherwise

    Raises:
        PermissionError: If sudo privileges are not available
        ValueError: If profile contains invalid settings
    """
    ...

# Bad
def apply_profile(self, profile: PerformanceProfile) -> bool:
    # Apply profile
    ...
```

### Clean Code Principles

#### Single Responsibility Principle

Each class/function should have one clear purpose:

```python
# Good - Separate responsibilities
class BatteryMonitor:
    """Reads battery data from sysfs."""

class BatteryWidget(QWidget):
    """Displays battery data in the UI."""

# Bad - Mixed responsibilities
class BatteryManager:
    """Reads battery data AND displays it."""
```

#### Descriptive Names

Use clear, meaningful names:

```python
# Good
battery_charge_percentage: int = 85
is_conservation_mode_enabled: bool = True

# Bad
bcp: int = 85
cm: bool = True
```

#### Error Handling

Handle errors gracefully with user-friendly messages:

```python
# Good
try:
    self.controller.set_conservation_mode(enabled)
except PermissionError:
    logger.error("Failed to set conservation mode: insufficient privileges")
    QMessageBox.critical(
        self,
        "Permission Error",
        "Failed to enable conservation mode.\n"
        "Please run the application with sudo privileges."
    )
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{str(e)}")

# Bad
try:
    self.controller.set_conservation_mode(enabled)
except:
    pass
```

### Testing

Test your changes before submitting:

```bash
# Test battery monitor
sudo python3 -c "from battery_monitor import BatteryMonitor; m = BatteryMonitor(); print(m.get_battery_info())"

# Test system control
sudo python3 test_system_control.py

# Test profiles
sudo python3 test_profiles.py

# Test GUI
sudo python3 main.py
```

### Commit Messages

Follow conventional commit format:

```
feat: add support for multiple batteries
fix: correct CPU frequency calculation for hybrid CPUs
docs: update installation instructions for Fedora
style: format code according to PEP 8
refactor: extract battery health calculation into separate method
test: add unit tests for ProfileManager
```

## Project Structure

```
linuxbat-manager/
├── battery_monitor.py    # Data layer - read-only sysfs access
├── system_control.py     # Control layer - write operations (sudo)
├── profiles.py          # Business logic - profile management
├── main.py              # Presentation layer - PyQt6 GUI
├── resources/
│   ├── styles/          # QSS stylesheets
│   └── icons/           # Application icons
├── tests/               # Test files
└── docs/               # Documentation
```

### Adding New Features

1. **Data Layer** (`battery_monitor.py`):

   - Add new sysfs reading methods
   - Return dataclasses or simple types
   - No state modification

2. **Control Layer** (`system_control.py`):

   - Add methods that modify system state
   - Require sudo privileges
   - Include proper error handling

3. **Business Logic** (`profiles.py`):

   - Add profile-related functionality
   - Maintain JSON persistence
   - Validate inputs

4. **GUI** (`main.py`):
   - Create new widgets as separate classes
   - Follow existing styling patterns
   - Connect to backend through clear interfaces

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.

Thank you for contributing! 🚀
