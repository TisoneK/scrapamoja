Main Problems
1. CSS Strategy Type Not Recognized
ERROR "Unknown strategy type: StrategyType.CSS"
All your selectors are failing to register because StrategyType.CSS isn't recognized. This suggests either:

The StrategyType enum is missing the CSS value
There's a mismatch between your YAML selector definitions and the selector engine code

2. Missing Selector Registration
ERROR "Selector 'match_items' not found in registry"
Because selectors aren't registering properly, the scraper can't find them at runtime.
3. Code Issues
ERROR "name 'SnapshotMetadata' is not defined"
ERROR "SelectorResult.__init__() got an unexpected keyword argument 'snapshot_id'"
These indicate incomplete code refactoring or missing imports.
4. Resource Cleanup Warnings
Exception ignored while calling deallocator
ValueError: I/O operation on closed pipe
The browser/subprocess cleanup isn't happening gracefully.
Recommended Fixes
First, check your StrategyType enum:
python# Likely in selector_engine.py or similar
from enum import Enum

class StrategyType(Enum):
    CSS = "css"  # Make sure this exists
    XPATH = "xpath"
    # ... other types
Second, verify YAML selector format matches expectations:
yaml# Example from your basketball match_items selector
strategies:
  - type: CSS  # Should match StrategyType enum value
    selector: ".event__match"
    # ...
Third, fix the SnapshotMetadata issue:
python# Add missing import or class definition
from your.models import SnapshotMetadata

# Or remove snapshot_id from SelectorResult if not needed
Fourth, improve browser cleanup:
pythonasync def cleanup(self):
    try:
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")
        