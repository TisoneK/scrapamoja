"""Browser profile applier module.

This module provides functionality to apply all stealth configurations
to Playwright browser contexts in a unified manner.

Module: src.stealth.cloudflare.core.applier

Classes:
    StealthProfileApplier: Applies all stealth configurations to browser contexts.
"""

from src.stealth.cloudflare.core.applier.apply import StealthProfileApplier

__all__ = ["StealthProfileApplier"]
