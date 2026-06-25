"""
Simple test to verify browser module functionality.

This test validates that the browser management components can be
instantiated and configured correctly.
"""

import asyncio
from src.browser import BrowserManager, BrowserSession, BrowserConfiguration
from tests.fixtures.browser_configs import CHROMIUM_HEADLESS_CONFIG


async def test_browser_manager():
    """Test browser manager instantiation and basic functionality."""
    print("Testing browser manager...")
    
    # Test configuration
    config = CHROMIUM_HEADLESS_CONFIG
    print(f"✓ Browser configuration loaded: {config.browser_type.value}")
    
    # Test session creation (without actual browser initialization)
    session = BrowserSession(configuration=config)
    print(f"✓ Browser session created: {session.session_id[:8]}...")
    
    # Test manager instantiation
    manager = BrowserManager()
    print("✓ Browser manager instantiated")
    
    # Test statistics
    stats = await manager.get_statistics()
    print(f"✓ Statistics retrieved: {stats.total_sessions} total sessions")
    
    print("✅ All browser module tests passed!")


if __name__ == "__main__":
    asyncio.run(test_browser_manager())
