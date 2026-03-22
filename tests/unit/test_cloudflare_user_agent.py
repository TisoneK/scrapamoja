"""Unit tests for Cloudflare user agent rotation module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.stealth.cloudflare.core.user_agent import UserAgentManager
from src.stealth.cloudflare.exceptions import UserAgentRotationError


class TestUserAgentManager:
    """Tests for UserAgentManager class."""

    def test_initialization_default(self) -> None:
        """Test that UserAgentManager initializes with correct defaults."""
        manager = UserAgentManager()
        assert manager.enabled is True
        assert manager.preferred_browser is None

    def test_initialization_with_options(self) -> None:
        """Test initialization with custom options."""
        manager = UserAgentManager(
            enabled=False,
            preferred_browser="chrome"
        )
        assert manager.enabled is False
        assert manager.preferred_browser == "chrome"

    def test_initialization_invalid_preferred_browser(self) -> None:
        """Test that invalid preferred browser raises error."""
        with pytest.raises(UserAgentRotationError) as exc_info:
            UserAgentManager(preferred_browser="invalid_browser")
        
        assert "Invalid preferred_browser" in str(exc_info.value)
        assert "invalid_browser" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_select_user_agent_enabled(self) -> None:
        """Test user agent selection when enabled."""
        manager = UserAgentManager(enabled=True)
        user_agent = await manager.select_user_agent()
        
        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        assert "Mozilla" in user_agent

    @pytest.mark.asyncio
    async def test_select_user_agent_disabled(self) -> None:
        """Test user agent selection when disabled."""
        manager = UserAgentManager(enabled=False)
        user_agent = await manager.select_user_agent()
        
        # Should return first user agent from pool
        from src.stealth.cloudflare.core.user_agent.manager import USER_AGENT_POOL
        assert user_agent == USER_AGENT_POOL[0]

    @pytest.mark.asyncio
    async def test_select_preferred_browser_chrome(self) -> None:
        """Test selecting user agent for preferred Chrome browser."""
        manager = UserAgentManager(preferred_browser="chrome")
        user_agent = await manager.select_user_agent()
        
        assert "Chrome" in user_agent
        assert "Safari" in user_agent  # Chrome UA also contains Safari

    @pytest.mark.asyncio
    async def test_select_preferred_browser_firefox(self) -> None:
        """Test selecting user agent for preferred Firefox browser."""
        manager = UserAgentManager(preferred_browser="firefox")
        user_agent = await manager.select_user_agent()
        
        assert "Firefox" in user_agent
        assert "Gecko" in user_agent

    @pytest.mark.asyncio
    async def test_select_preferred_browser_safari(self) -> None:
        """Test selecting user agent for preferred Safari browser."""
        manager = UserAgentManager(preferred_browser="safari")
        user_agent = await manager.select_user_agent()
        
        assert "Safari" in user_agent
        assert "Version/" in user_agent  # Safari specific identifier
        # Safari UA should not contain Chrome (but may contain AppleWebKit)
        assert "Chrome/" not in user_agent

    @pytest.mark.asyncio
    async def test_select_preferred_browser_edge(self) -> None:
        """Test selecting user agent for preferred Edge browser."""
        manager = UserAgentManager(preferred_browser="edge")
        user_agent = await manager.select_user_agent()
        
        assert "Edg/" in user_agent

    def test_detect_browser_family_chrome(self) -> None:
        """Test browser family detection for Chrome."""
        manager = UserAgentManager()
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        family = manager._detect_browser_family(ua)
        assert family == "chrome"

    def test_detect_browser_family_firefox(self) -> None:
        """Test browser family detection for Firefox."""
        manager = UserAgentManager()
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
        family = manager._detect_browser_family(ua)
        assert family == "firefox"

    def test_detect_browser_family_safari(self) -> None:
        """Test browser family detection for Safari."""
        manager = UserAgentManager()
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1.2 Safari/605.1.15"
        family = manager._detect_browser_family(ua)
        assert family == "safari"

    def test_detect_browser_family_edge(self) -> None:
        """Test browser family detection for Edge."""
        manager = UserAgentManager()
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        family = manager._detect_browser_family(ua)
        assert family == "edge"

    def test_detect_browser_family_unknown(self) -> None:
        """Test browser family detection for unknown user agent."""
        manager = UserAgentManager()
        ua = "Some Random User Agent String"
        family = manager._detect_browser_family(ua)
        assert family == "chrome"  # Should default to chrome

    def test_select_weighted_random_agent(self) -> None:
        """Test weighted random selection logic."""
        manager = UserAgentManager()
        
        # Test multiple selections to ensure variety
        selections = set()
        for _ in range(20):
            agent = manager._select_weighted_random_agent()
            selections.add(agent)
        
        # Should have selected different agents
        assert len(selections) > 1

    def test_select_preferred_browser_agent_no_match(self) -> None:
        """Test preferred browser selection with no matching agents."""
        # Create manager with valid preferred browser first
        manager = UserAgentManager(preferred_browser="chrome")
        
        # Manually set preferred_browser to test the selection logic
        manager.preferred_browser = "nonexistent"
        
        with pytest.raises(UserAgentRotationError) as exc_info:
            manager._select_preferred_browser_agent()
        
        assert "No user agents found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_apply_to_context_enabled(self) -> None:
        """Test applying user agent to context when enabled."""
        manager = UserAgentManager(enabled=True)
        mock_context = MagicMock()
        mock_context.set_extra_http_headers = AsyncMock()
        
        await manager.apply_to_context(mock_context)
        
        # Should call set_extra_http_headers
        mock_context.set_extra_http_headers.assert_called_once()
        call_args = mock_context.set_extra_http_headers.call_args[0][0]
        assert "User-Agent" in call_args
        assert len(call_args["User-Agent"]) > 0

    @pytest.mark.asyncio
    async def test_apply_to_context_disabled(self) -> None:
        """Test applying user agent to context when disabled."""
        manager = UserAgentManager(enabled=False)
        mock_context = MagicMock()
        mock_context.set_extra_http_headers = AsyncMock()
        
        await manager.apply_to_context(mock_context)
        
        # Should not call set_extra_http_headers
        mock_context.set_extra_http_headers.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_to_context_no_headers_method(self) -> None:
        """Test applying to context without headers method."""
        manager = UserAgentManager(enabled=True)
        mock_context = MagicMock()
        # Remove the set_extra_http_headers method
        del mock_context.set_extra_http_headers
        
        # Should not raise an error
        await manager.apply_to_context(mock_context)

    @pytest.mark.asyncio
    async def test_select_user_agent_exception_handling(self) -> None:
        """Test exception handling in select_user_agent."""
        manager = UserAgentManager()
        
        # Patch random.choice to raise an exception
        with patch('random.choice', side_effect=Exception("Test error")):
            with pytest.raises(UserAgentRotationError) as exc_info:
                await manager.select_user_agent()
            
            assert "Failed to select user agent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_apply_to_context_exception_handling(self) -> None:
        """Test exception handling in apply_to_context."""
        manager = UserAgentManager()
        mock_context = MagicMock()
        mock_context.set_extra_http_headers = AsyncMock(side_effect=Exception("Test error"))
        
        with pytest.raises(UserAgentRotationError) as exc_info:
            await manager.apply_to_context(mock_context)
        
        assert "Failed to apply user agent to context" in str(exc_info.value)

    def test_get_pool_size(self) -> None:
        """Test getting pool size."""
        manager = UserAgentManager()
        size = manager.get_pool_size()
        
        assert isinstance(size, int)
        assert size > 0
        from src.stealth.cloudflare.core.user_agent.manager import USER_AGENT_POOL
        assert size == len(USER_AGENT_POOL)

    def test_get_browser_distribution(self) -> None:
        """Test getting browser distribution."""
        manager = UserAgentManager()
        distribution = manager.get_browser_distribution()
        
        assert isinstance(distribution, dict)
        assert len(distribution) > 0
        
        # Check that all browser families are present
        expected_families = {"chrome", "firefox", "safari", "edge"}
        assert set(distribution.keys()).issubset(expected_families)
        
        # Check that counts are positive
        for count in distribution.values():
            assert isinstance(count, int)
            assert count > 0

    def test_user_agent_pool_constants(self) -> None:
        """Test that user agent pool constants are properly defined."""
        from src.stealth.cloudflare.core.user_agent.manager import (
            USER_AGENT_POOL,
            BROWSER_WEIGHTS
        )
        
        # Check that user agent pool is not empty
        assert len(USER_AGENT_POOL) > 0
        
        # Check that all user agents are strings and contain Mozilla
        for ua in USER_AGENT_POOL:
            assert isinstance(ua, str)
            assert "Mozilla" in ua
        
        # Check browser weights
        assert isinstance(BROWSER_WEIGHTS, dict)
        assert len(BROWSER_WEIGHTS) > 0
        
        # Check that weights sum to 1.0 (approximately)
        total_weight = sum(BROWSER_WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.01
