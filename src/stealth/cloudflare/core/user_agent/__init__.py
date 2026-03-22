"""User agent rotation module.

This module provides functionality to rotate user agent strings for Playwright
browser contexts, making each session appear to come from different browsers.

Module: src.stealth.cloudflare.core.user_agent

Classes:
    UserAgentManager: Manages user agent pool and selection logic.
"""

from src.stealth.cloudflare.core.user_agent.manager import UserAgentManager

__all__ = ["UserAgentManager"]
