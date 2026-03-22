# Blind Hunter Review - User Agent Rotation

You are a cynical, jaded reviewer with zero patience for sloppy work. Review this diff with extreme skepticism and find at least 10 issues.

## Content to Review:

```diff
diff --git a/src/stealth/cloudflare/core/user_agent/__init__.py b/src/stealth/cloudflare/core/user_agent/__init__.py
new file mode 100644
index 0000000..0000000
--- /dev/null
+++ b/src/stealth/cloudflare/core/user_agent/__init__.py
@@ -0,0 +1,3 @@
+"""User agent rotation module for Cloudflare stealth."""
+
+from .manager import UserAgentManager
diff --git a/src/stealth/cloudflare/core/user_agent/manager.py b/src/stealth/cloudflare/core/user_agent/manager.py
new file mode 100644
index 0000000..0000000
--- /dev/null
+++ b/src/stealth/cloudflare/core/user_agent/manager.py
@@ -0,0 +1,285 @@
+"""User agent manager for Cloudflare stealth."""
+
+import random
+from typing import Any
+
+from structlog import get_logger
+
+from ...exceptions import UserAgentRotationError
+
+logger = get_logger(__name__)
+
+# User agent pool with realistic browser versions
+USER_AGENT_POOL = [
+    # Chrome (Windows)
+    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
+    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
+    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
+    # Chrome (macOS)
+    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
+    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
+    # Chrome (Linux)
+    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
+    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
+    # Firefox (Windows)
+    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
+    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
+    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
+    # Firefox (macOS)
+    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
+    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
+    # Firefox (Linux)
+    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
+    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
+    # Safari (macOS)
+    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
+    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
+    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
+    # Edge (Windows)
+    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
+    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
+    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
+]
+
+# Browser weights for selection (sum to 1.0)
+BROWSER_WEIGHTS = {
+    "chrome": 0.4,
+    "firefox": 0.3,
+    "safari": 0.2,
+    "edge": 0.1,
+}
+
+
+class UserAgentManager:
+    """Manages user agent rotation for stealth operations."""
+
+    def __init__(self, enabled: bool = True, preferred_browser: str | None = None) -> None:
+        """Initialize the user agent manager.
+
+        Args:
+            enabled: Whether user agent rotation is enabled.
+            preferred_browser: Optional preferred browser family.
+        """
+        self.enabled = enabled
+        self.preferred_browser = preferred_browser.lower() if preferred_browser else None
+
+        if preferred_browser and preferred_browser.lower() not in BROWSER_WEIGHTS:
+            raise UserAgentRotationError(
+                f"Invalid preferred browser: {preferred_browser}. "
+                f"Valid options: {', '.join(BROWSER_WEIGHTS.keys())}"
+            )
+
+        logger.info(
+            "UserAgentManager initialized",
+            extra={
+                "enabled": enabled,
+                "preferred_browser": preferred_browser,
+            },
+        )
+
+    async def select_user_agent(self) -> str:
+        """Select a user agent string from the pool.
+
+        Returns:
+            A randomly selected user agent string based on browser weights
+            and optional preferred browser preference.
+
+        Raises:
+            UserAgentRotationError: If user agent selection fails.
+        """
+        if not self.enabled:
+            logger.debug("User agent rotation disabled, returning default")
+            return USER_AGENT_POOL[0]  # Return first UA as default
+
+        try:
+            if self.preferred_browser:
+                user_agent = self._select_preferred_browser_agent()
+            else:
+                user_agent = self._select_weighted_random_agent()
+
+            logger.debug(
+                "User agent selected",
+                extra={
+                    "user_agent": user_agent[:100] + "...",  # Truncate for logging
+                    "preferred_browser": self.preferred_browser,
+                },
+            )
+            return user_agent
+
+        except Exception as e:
+            logger.error(
+                "Failed to select user agent",
+                extra={
+                    "error": str(e),
+                    "preferred_browser": self.preferred_browser,
+                },
+            )
+            raise UserAgentRotationError(f"Failed to select user agent: {e}") from e
+
+    def _select_preferred_browser_agent(self) -> str:
+        """Select a user agent from the preferred browser family.
+
+        Returns:
+            A user agent string from the preferred browser family.
+
+        Raises:
+            UserAgentRotationError: If no agents found for preferred browser.
+        """
+        preferred_agents = [
+            ua for ua in USER_AGENT_POOL
+            if self._detect_browser_family(ua) == self.preferred_browser.lower()
+        ]
+
+        if not preferred_agents:
+            raise UserAgentRotationError(
+                f"No user agents found for preferred browser: {self.preferred_browser}"
+            )
+
+        return random.choice(preferred_agents)
+
+    def _select_weighted_random_agent(self) -> str:
+        """Select a user agent using weighted random selection.
+
+        Returns:
+            A randomly selected user agent string based on browser weights.
+        """
+        # Group user agents by browser family
+        browser_agents: dict[str, list[str]] = {}
+        for ua in USER_AGENT_POOL:
+            browser_family = self._detect_browser_family(ua)
+            if browser_family not in browser_agents:
+                browser_agents[browser_family] = []
+            browser_agents[browser_family].append(ua)
+
+        # Select browser family based on weights
+        browser_families = list(browser_agents.keys())
+        weights = [BROWSER_WEIGHTS.get(family, 0.1) for family in browser_families]
+        selected_family = random.choices(browser_families, weights=weights)[0]
+
+        # Select random agent from chosen family
+        return random.choice(browser_agents[selected_family])
+
+    def _detect_browser_family(self, user_agent: str) -> str:
+        """Detect browser family from user agent string.
+
+        Args:
+            user_agent: The user agent string to analyze.
+
+        Returns:
+            The browser family ("chrome", "firefox", "safari", "edge").
+        """
+        user_agent_lower = user_agent.lower()
+
+        # Edge must be checked first since it also contains Chrome
+        if "edg/" in user_agent_lower:
+            return "edge"
+        elif "chrome/" in user_agent_lower and "safari/" in user_agent_lower:
+            return "chrome"
+        elif "firefox/" in user_agent_lower:
+            return "firefox"
+        elif "safari/" in user_agent_lower and "chrome/" not in user_agent_lower and "version/" in user_agent_lower:
+            return "safari"
+        else:
+            return "chrome"  # Default fallback
+
+    async def apply_to_context(self, context: Any) -> None:
+        """Apply user agent to a Playwright browser context.
+
+        Args:
+            context: The Playwright browser context to modify.
+
+        Raises:
+            UserAgentRotationError: If application fails.
+        """
+        if not self.enabled:
+            logger.debug("User agent rotation disabled, skipping application")
+            return
+
+        try:
+            user_agent = await self.select_user_agent()
+
+            # Note: Playwright contexts are created with user_agent parameter
+            # This method is for future compatibility with context modification
+            if hasattr(context, 'set_extra_http_headers'):
+                # Set User-Agent header as fallback
+                await context.set_extra_http_headers({
+                    "User-Agent": user_agent
+                })
+
+            logger.info(
+                "User agent applied to context",
+                extra={
+                    "user_agent": user_agent[:100] + "...",
+                },
+            )
+
+        except Exception as e:
+            logger.error(
+                "Failed to apply user agent to context",
+                extra={"error": str(e)},
+            )
+            raise UserAgentRotationError(f"Failed to apply user agent to context: {e}") from e
+
+    def get_pool_size(self) -> int:
+        """Get the size of the user agent pool.
+
+        Returns:
+            The number of user agents in the pool.
+        """
+        return len(USER_AGENT_POOL)
+
+    def get_browser_distribution(self) -> dict[str, int]:
+        """Get the distribution of browsers in the pool.
+
+        Returns:
+            A dictionary mapping browser families to their counts.
+        """
+        distribution: dict[str, int] = {}
+        for ua in USER_AGENT_POOL:
+            family = self._detect_browser_family(ua)
+            distribution[family] = distribution.get(family, 0) + 1
+        return distribution
diff --git a/src/stealth/cloudflare/exceptions/__init__.py b/src/stealth/cloudflare/exceptions/__init__.py
index 0000000..0000000 100644
--- a/src/stealth/cloudflare/exceptions/__init__.py
+++ b/src/stealth/cloudflare/exceptions/__init__.py
@@ -1,3 +1,6 @@
 """Cloudflare stealth exceptions."""
 
-class CloudflareStealthError(Exception):
+class CloudflareStealthError(Exception):
+    """Base exception for Cloudflare stealth operations."""
+
+class UserAgentRotationError(CloudflareStealthError):
+    """Exception raised when user agent rotation fails."""
diff --git a/src/stealth/cloudflare/core/__init__.py b/src/stealth/cloudflare/core/__init__.py
index 0000000..0000000 100644
--- a/src/stealth/cloudflare/core/__init__.py
+++ b/src/stealth/cloudflare/core/__init__.py
@@ -1,3 +1,7 @@
 """Cloudflare stealth core modules."""
 
-from .webdriver import WebDriverMask
+from .webdriver import WebDriverMask
+from .fingerprint import FingerprintManager
+from .user_agent import UserAgentManager
+
+__all__ = ["WebDriverMask", "FingerprintManager", "UserAgentManager"]
diff --git a/tests/unit/test_cloudflare_user_agent.py b/tests/unit/test_cloudflare_user_agent.py
new file mode 100644
index 0000000..0000000
--- /dev/null
+++ b/tests/unit/test_cloudflare_user_agent.py
@@ -0,0 +1,244 @@
+"""Unit tests for user agent rotation."""
+
+import pytest
+from unittest.mock import AsyncMock, MagicMock, patch
+
+from src.stealth.cloudflare.core.user_agent.manager import (
+    UserAgentManager,
+    USER_AGENT_POOL,
+    BROWSER_WEIGHTS,
+)
+from src.stealth.cloudflare.exceptions import UserAgentRotationError
+
+
+class TestUserAgentManager:
+    """Test cases for UserAgentManager."""
+
+    def test_init_default(self) -> None:
+        """Test default initialization."""
+        manager = UserAgentManager()
+        assert manager.enabled is True
+        assert manager.preferred_browser is None
+
+    def test_init_with_preferences(self) -> None:
+        """Test initialization with preferences."""
+        manager = UserAgentManager(enabled=False, preferred_browser="chrome")
+        assert manager.enabled is False
+        assert manager.preferred_browser == "chrome"
+
+    def test_init_invalid_preferred_browser(self) -> None:
+        """Test initialization with invalid preferred browser."""
+        with pytest.raises(UserAgentRotationError) as exc_info:
+            UserAgentManager(preferred_browser="invalid")
+        
+        assert "Invalid preferred browser" in str(exc_info.value)
+        assert "Valid options: chrome, firefox, safari, edge" in str(exc_info.value)
+
+    @pytest.mark.asyncio
+    async def test_select_user_agent_enabled(self) -> None:
+        """Test user agent selection when enabled."""
+        manager = UserAgentManager(enabled=True)
+        user_agent = await manager.select_user_agent()
+        
+        assert isinstance(user_agent, str)
+        assert user_agent in USER_AGENT_POOL
+        assert "Mozilla" in user_agent
+
+    @pytest.mark.asyncio
+    async def test_select_user_agent_disabled(self) -> None:
+        """Test user agent selection when disabled."""
+        manager = UserAgentManager(enabled=False)
+        user_agent = await manager.select_user_agent()
+        
+        assert user_agent == USER_AGENT_POOL[0]
+
+    @pytest.mark.asyncio
+    async def test_select_user_agent_preferred_browser(self) -> None:
+        """Test user agent selection with preferred browser."""
+        manager = UserAgentManager(preferred_browser="chrome")
+        user_agent = await manager.select_user_agent()
+        
+        assert isinstance(user_agent, str)
+        assert user_agent in USER_AGENT_POOL
+        # Should be a Chrome user agent
+        assert "Chrome/" in user_agent
+
+    def test_detect_browser_family_chrome(self) -> None:
+        """Test browser family detection for Chrome."""
+        manager = UserAgentManager()
+        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
+        family = manager._detect_browser_family(ua)
+        assert family == "chrome"
+
+    def test_detect_browser_family_firefox(self) -> None:
+        """Test browser family detection for Firefox."""
+        manager = UserAgentManager()
+        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
+        family = manager._detect_browser_family(ua)
+        assert family == "firefox"
+
+    def test_detect_browser_family_safari(self) -> None:
+        """Test browser family detection for Safari."""
+        manager = UserAgentManager()
+        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
+        family = manager._detect_browser_family(ua)
+        assert family == "safari"
+
+    def test_detect_browser_family_edge(self) -> None:
+        """Test browser family detection for Edge."""
+        manager = UserAgentManager()
+        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
+        family = manager._detect_browser_family(ua)
+        assert family == "edge"
+
+    def test_detect_browser_family_unknown(self) -> None:
+        """Test browser family detection for unknown user agent."""
+        manager = UserAgentManager()
+        ua = "Some Random User Agent String"
+        family = manager._detect_browser_family(ua)
+        assert family == "chrome"  # Should default to chrome
+
+    def test_select_weighted_random_agent(self) -> None:
+        """Test weighted random selection logic."""
+        manager = UserAgentManager()
+        
+        # Test multiple selections to ensure variety
+        selections = set()
+        for _ in range(20):
+            agent = manager._select_weighted_random_agent()
+            selections.add(agent)
+        
+        # Should have selected different agents
+        assert len(selections) > 1
+
+    def test_select_preferred_browser_agent_no_match(self) -> None:
+        """Test preferred browser selection with no matching agents."""
+        # Create manager with valid preferred browser first
+        manager = UserAgentManager(preferred_browser="chrome")
+        
+        # Manually set preferred_browser to test the selection logic
+        manager.preferred_browser = "nonexistent"
+
+        with pytest.raises(UserAgentRotationError) as exc_info:
+            manager._select_preferred_browser_agent()
+
+        assert "No user agents found" in str(exc_info.value)
+
+    @pytest.mark.asyncio
+    async def test_apply_to_context_enabled(self) -> None:
+        """Test applying user agent to context when enabled."""
+        manager = UserAgentManager(enabled=True)
+        mock_context = MagicMock()
+        mock_context.set_extra_http_headers = AsyncMock()
+
+        await manager.apply_to_context(mock_context)
+
+        # Should call set_extra_http_headers
+        mock_context.set_extra_http_headers.assert_called_once()
+        call_args = mock_context.set_extra_http_headers.call_args[0][0]
+        assert "User-Agent" in call_args
+        assert len(call_args["User-Agent"]) > 0
+
+    @pytest.mark.asyncio
+    async def test_apply_to_context_disabled(self) -> None:
+        """Test applying user agent to context when disabled."""
+        manager = UserAgentManager(enabled=False)
+        mock_context = MagicMock()
+        mock_context.set_extra_http_headers = AsyncMock()
+
+        await manager.apply_to_context(mock_context)
+
+        # Should not call set_extra_http_headers
+        mock_context.set_extra_http_headers.assert_not_called()
+
+    @pytest.mark.asyncio
+    async def test_apply_to_context_no_headers_method(self) -> None:
+        """Test applying to context without headers method."""
+        manager = UserAgentManager(enabled=True)
+        mock_context = MagicMock()
+        # Remove the set_extra_http_headers method
+        del mock_context.set_extra_http_headers
+
+        # Should not raise an error
+        await manager.apply_to_context(mock_context)
+
+    @pytest.mark.asyncio
+    async def test_select_user_agent_exception_handling(self) -> None:
+        """Test exception handling in select_user_agent."""
+        manager = UserAgentManager()
+
+        # Patch random.choice to raise an exception
+        with patch('random.choice', side_effect=Exception("Test error")):
+            with pytest.raises(UserAgentRotationError) as exc_info:
+                await manager.select_user_agent()
+
+            assert "Failed to select user agent" in str(exc_info.value)
+
+    @pytest.mark.asyncio
+    async def test_apply_to_context_exception_handling(self) -> None:
+        """Test exception handling in apply_to_context."""
+        manager = UserAgentManager()
+        mock_context = MagicMock()
+        mock_context.set_extra_http_headers = AsyncMock(side_effect=Exception("Test error"))
+
+        with pytest.raises(UserAgentRotationError) as exc_info:
+            await manager.apply_to_context(mock_context)
+
+        assert "Failed to apply user agent to context" in str(exc_info.value)
+
+    def test_get_pool_size(self) -> None:
+        """Test getting pool size."""
+        manager = UserAgentManager()
+        size = manager.get_pool_size()
+
+        assert isinstance(size, int)
+        assert size > 0
+        from src.stealth.cloudflare.core.user_agent.manager import USER_AGENT_POOL
+        assert size == len(USER_AGENT_POOL)
+
+    def test_get_browser_distribution(self) -> None:
+        """Test getting browser distribution."""
+        manager = UserAgentManager()
+        distribution = manager.get_browser_distribution()
+
+        assert isinstance(distribution, dict)
+        assert len(distribution) > 0
+
+        # Check that all browser families are present
+        expected_families = {"chrome", "firefox", "safari", "edge"}
+        assert set(distribution.keys()).issubset(expected_families)
+
+        # Check that counts are positive
+        for count in distribution.values():
+            assert isinstance(count, int)
+            assert count > 0
+
+    def test_user_agent_pool_constants(self) -> None:
+        """Test that user agent pool constants are properly defined."""
+        from src.stealth.cloudflare.core.user_agent.manager import (
+            USER_AGENT_POOL,
+            BROWSER_WEIGHTS
+        )
+
+        # Check that user agent pool is not empty
+        assert len(USER_AGENT_POOL) > 0
+
+        # Check that all user agents are strings and contain Mozilla
+        for ua in USER_AGENT_POOL:
+            assert isinstance(ua, str)
+            assert "Mozilla" in ua
+
+        # Check browser weights
+        assert isinstance(BROWSER_WEIGHTS, dict)
+        assert len(BROWSER_WEIGHTS) > 0
+
+        # Check that weights sum to 1.0 (approximately)
+        total_weight = sum(BROWSER_WEIGHTS.values())
+        assert abs(total_weight - 1.0) < 0.01
diff --git a/tests/integration/test_cloudflare_user_agent_integration.py b/tests/integration/test_cloudflare_user_agent_integration.py
new file mode 100644
index 0000000..0000000
--- /dev/null
+++ b/tests/integration/test_cloudflare_user_agent_integration.py
@@ -0,0 +1,67 @@
+"""Integration tests for user agent rotation."""
+
+import pytest
+from playwright.async_api import async_playwright
+
+from src.stealth.cloudflare.core.user_agent.manager import UserAgentManager
+from src.stealth.cloudflare.exceptions import UserAgentRotationError
+
+
+class TestUserAgentIntegration:
+    """Integration tests for UserAgentManager."""
+
+    @pytest.mark.asyncio
+    async def test_user_agent_selection_integration(self) -> None:
+        """Test user agent selection integration."""
+        manager = UserAgentManager()
+
+        # Test multiple selections
+        selections = set()
+        for _ in range(10):
+            user_agent = await manager.select_user_agent()
+            selections.add(user_agent)
+
+        # Should have variety in selections
+        assert len(selections) > 1
+
+        # All selections should be valid
+        for ua in selections:
+            assert isinstance(ua, str)
+            assert len(ua) > 0
+            assert "Mozilla" in ua
+
+    @pytest.mark.asyncio
+    async def test_preferred_browser_integration(self) -> None:
+        """Test preferred browser integration."""
+        # Test each browser family
+        for browser_family in ["chrome", "firefox", "safari", "edge"]:
+            manager = UserAgentManager(preferred_browser=browser_family)
+            user_agent = await manager.select_user_agent()
+
+            # Should match the preferred browser family
+            detected_family = manager._detect_browser_family(user_agent)
+            assert detected_family == browser_family
+
+    @pytest.mark.asyncio
+    async def test_playwright_context_integration(self) -> None:
+        """Test integration with Playwright context."""
+        async with async_playwright() as p:
+            browser = await p.chromium.launch()
+            context = await browser.new_context()
+
+            manager = UserAgentManager()
+            await manager.apply_to_context(context)
+
+            # Verify context was created (basic sanity check)
+            assert context is not None
+
+            await browser.close()
+
+    @pytest.mark.asyncio
+    async def test_disabled_manager_integration(self) -> None:
+        """Test disabled manager integration."""
+        manager = UserAgentManager(enabled=False)
+        user_agent = await manager.select_user_agent()
+
+        # Should return default user agent
+        assert user_agent is not None
+        assert len(user_agent) > 0
+
+    @pytest.mark.asyncio
+    async def test_error_recovery_integration(self) -> None:
+        """Test error recovery in integration scenarios."""
+        manager = UserAgentManager()
+
+        # Test with invalid preferred browser
+        with pytest.raises(UserAgentRotationError):
+            UserAgentManager(preferred_browser="invalid")
+
+    @pytest.mark.asyncio
+    async def test_weighted_distribution_integration(self) -> None:
+        """Test weighted distribution in integration."""
+        manager = UserAgentManager()
+
+        # Make many selections to test distribution
+        selections = []
+        for _ in random.randint(50, 100):
+            user_agent = await manager.select_user_agent()
+            selections.append(user_agent)
+
+        # Should have reasonable distribution
+        distribution = manager.get_browser_distribution()
+        assert len(distribution) > 0
+
+        # All browser families should be represented
+        expected_families = {"chrome", "firefox", "safari", "edge"}
+        assert set(distribution.keys()).issubset(expected_families)
```

Output findings as a Markdown list (descriptions only). Find at least 10 issues.
