"""Integration tests for Cloudflare user agent rotation module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.stealth.cloudflare.core.user_agent import UserAgentManager


@pytest.mark.integration
class TestUserAgentManagerIntegration:
    """Integration tests for UserAgentManager class."""

    @pytest.mark.asyncio
    async def test_user_agent_selection_integration(self) -> None:
        """Test complete user agent selection workflow."""
        manager = UserAgentManager(enabled=True)
        
        # Test multiple selections to ensure variety
        selected_agents = set()
        for _ in range(10):
            agent = await manager.select_user_agent()
            selected_agents.add(agent)
            
            # Verify agent format
            assert isinstance(agent, str)
            assert len(agent) > 0
            assert "Mozilla" in agent
        
        # Should have selected different agents
        assert len(selected_agents) > 1

    @pytest.mark.asyncio
    async def test_preferred_browser_integration(self) -> None:
        """Test preferred browser selection workflow."""
        # Test each browser family
        for browser in ["chrome", "firefox", "safari", "edge"]:
            manager = UserAgentManager(preferred_browser=browser)
            agent = await manager.select_user_agent()
            
            # Verify browser family detection
            detected_family = manager._detect_browser_family(agent)
            assert detected_family == browser

    @pytest.mark.asyncio
    async def test_context_application_integration(self) -> None:
        """Test applying user agent to browser context."""
        manager = UserAgentManager(enabled=True)
        
        # Create mock Playwright context
        mock_context = MagicMock()
        mock_context.set_extra_http_headers = AsyncMock()
        
        await manager.apply_to_context(mock_context)
        
        # Verify headers were set
        mock_context.set_extra_http_headers.assert_called_once()
        call_args = mock_context.set_extra_http_headers.call_args[0][0]
        
        assert "User-Agent" in call_args
        user_agent = call_args["User-Agent"]
        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        assert "Mozilla" in user_agent

    @pytest.mark.asyncio
    async def test_disabled_manager_integration(self) -> None:
        """Test disabled manager workflow."""
        manager = UserAgentManager(enabled=False)
        
        # Should return default user agent
        agent = await manager.select_user_agent()
        from src.stealth.cloudflare.core.user_agent.manager import USER_AGENT_POOL
        assert agent == USER_AGENT_POOL[0]
        
        # Should not apply to context
        mock_context = MagicMock()
        mock_context.set_extra_http_headers = AsyncMock()
        
        await manager.apply_to_context(mock_context)
        mock_context.set_extra_http_headers.assert_not_called()

    def test_browser_distribution_integration(self) -> None:
        """Test browser distribution statistics."""
        manager = UserAgentManager()
        distribution = manager.get_browser_distribution()
        
        # Verify all expected browsers are present
        expected_browsers = {"chrome", "firefox", "safari", "edge"}
        assert set(distribution.keys()).issubset(expected_browsers)
        
        # Verify counts are reasonable
        total_agents = sum(distribution.values())
        assert total_agents == manager.get_pool_size()
        assert total_agents > 0
        
        # Verify distribution makes sense
        for browser, count in distribution.items():
            assert isinstance(count, int)
            assert count > 0
            assert count <= total_agents

    @pytest.mark.asyncio
    async def test_weighted_selection_integration(self) -> None:
        """Test weighted random selection produces expected distribution."""
        manager = UserAgentManager()
        
        # Test many selections to verify distribution
        browser_counts = {"chrome": 0, "firefox": 0, "safari": 0, "edge": 0}
        total_selections = 1000
        
        for _ in range(total_selections):
            agent = manager._select_weighted_random_agent()
            family = manager._detect_browser_family(agent)
            browser_counts[family] += 1
        
        # Verify distribution roughly matches weights (within reasonable tolerance)
        from src.stealth.cloudflare.core.user_agent.manager import BROWSER_WEIGHTS
        
        for browser, expected_weight in BROWSER_WEIGHTS.items():
            actual_ratio = browser_counts[browser] / total_selections
            expected_ratio = expected_weight
            
            # Allow 10% tolerance for random variation
            assert abs(actual_ratio - expected_ratio) < 0.1, (
                f"Browser {browser}: expected {expected_ratio:.2f}, "
                f"got {actual_ratio:.2f}"
            )
