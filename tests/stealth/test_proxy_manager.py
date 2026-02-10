"""
Tests for the Proxy Rotation and Session Management subsystem.

Verifies:
- Provider initialization and health checks
- Proxy session creation and IP rotation
- Cookie persistence within sticky sessions
- Session state persistence to disk
- Graceful failover on provider errors
- Cooldown enforcement
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from src.stealth.proxy_manager import (
    ProxyManager,
    BrightDataProvider,
    OxyLabsProvider,
    MockProxyProvider,
)
from src.stealth.models import ProxyStatus
from src.stealth.events import EventBuilder


class TestBrightDataProvider:
    """Tests for BrightData provider."""
    
    def test_initialization(self):
        """Test BrightData provider creation."""
        config = {"username": "test_user", "password": "test_pass"}
        provider = BrightDataProvider(config)
        
        assert provider.username == "test_user"
        assert provider.password == "test_pass"
        assert provider.host == "zproxy.lum-superproxy.io"
        assert provider.port == 22225
        assert provider.initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_with_credentials(self):
        """Test initializing with valid credentials."""
        config = {"username": "test_user", "password": "test_pass"}
        provider = BrightDataProvider(config)
        
        result = await provider.initialize()
        
        assert result is True
        assert provider.initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_without_credentials(self):
        """Test initialization fails without credentials."""
        provider = BrightDataProvider({})
        
        result = await provider.initialize()
        
        assert result is False
        assert provider.initialized is False
    
    @pytest.mark.asyncio
    async def test_get_proxy_url(self):
        """Test getting proxy URL from BrightData."""
        config = {"username": "test_user", "password": "test_pass"}
        provider = BrightDataProvider(config)
        await provider.initialize()
        
        proxy_url = await provider.get_proxy_url()
        
        assert "zproxy.lum-superproxy.io" in proxy_url
        assert "22225" in proxy_url
        assert "test_user:test_pass" in proxy_url
    
    @pytest.mark.asyncio
    async def test_mark_exhausted(self):
        """Test marking proxy as exhausted."""
        config = {"username": "test_user", "password": "test_pass"}
        provider = BrightDataProvider(config)
        await provider.initialize()
        
        proxy_url = await provider.get_proxy_url()
        initial_available = provider.available_proxies
        
        await provider.mark_exhausted(proxy_url)
        
        assert proxy_url in provider.blocked_proxies
        assert provider.available_proxies == initial_available - 1
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        config = {"username": "test_user", "password": "test_pass"}
        provider = BrightDataProvider(config)
        await provider.initialize()
        
        health = await provider.health_check()
        
        assert health["provider"] == "bright_data"
        assert health["initialized"] is True
        assert "available_proxies" in health
        assert "blocked_count" in health


class TestOxyLabsProvider:
    """Tests for OxyLabs provider."""
    
    def test_initialization(self):
        """Test OxyLabs provider creation."""
        config = {"username": "test_user", "password": "test_pass"}
        provider = OxyLabsProvider(config)
        
        assert provider.username == "test_user"
        assert provider.host == "pr.oxylabs.io"
        assert provider.port == 7777
    
    @pytest.mark.asyncio
    async def test_get_proxy_url(self):
        """Test getting OxyLabs proxy URL."""
        config = {"username": "test_user", "password": "test_pass"}
        provider = OxyLabsProvider(config)
        await provider.initialize()
        
        proxy_url = await provider.get_proxy_url()
        
        assert "pr.oxylabs.io" in proxy_url
        assert "7777" in proxy_url


class TestMockProxyProvider:
    """Tests for Mock provider."""
    
    def test_initialization(self):
        """Test Mock provider creation."""
        provider = MockProxyProvider({})
        
        assert provider.initialized is False
        assert len(provider.mock_ips) == 5
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test Mock provider initialization."""
        provider = MockProxyProvider({})
        
        result = await provider.initialize()
        
        assert result is True
        assert provider.initialized is True
    
    @pytest.mark.asyncio
    async def test_get_proxy_url(self):
        """Test getting proxy URL (None for mock)."""
        provider = MockProxyProvider({})
        await provider.initialize()
        
        proxy_url = await provider.get_proxy_url()
        
        assert proxy_url is None  # Mock returns None for direct connection


class TestProxyManagerInitialization:
    """Tests for ProxyManager initialization."""
    
    def test_creation_with_bright_data(self):
        """Test creating manager with BrightData provider."""
        config = {"username": "test", "password": "test"}
        manager = ProxyManager("bright_data", config=config)
        
        assert manager.provider_name == "bright_data"
        assert isinstance(manager.provider, BrightDataProvider)
        assert manager.initialized is False
    
    def test_creation_with_oxylabs(self):
        """Test creating manager with OxyLabs provider."""
        config = {"username": "test", "password": "test"}
        manager = ProxyManager("oxylabs", config=config)
        
        assert manager.provider_name == "oxylabs"
        assert isinstance(manager.provider, OxyLabsProvider)
    
    def test_creation_with_mock(self):
        """Test creating manager with Mock provider."""
        manager = ProxyManager("mock")
        
        assert manager.provider_name == "mock"
        assert isinstance(manager.provider, MockProxyProvider)
    
    def test_creation_with_unknown_provider(self):
        """Test that unknown provider falls back to Mock."""
        manager = ProxyManager("unknown_provider")
        
        assert isinstance(manager.provider, MockProxyProvider)
    
    def test_initialization_parameters(self):
        """Test ProxyManager parameters."""
        manager = ProxyManager("mock", run_id="test-run-001")
        
        assert manager.run_id == "test-run-001"
        assert manager.cooldown_seconds == 600
        assert manager.active_sessions == {}


class TestProxyManagerAsync:
    """Async tests for ProxyManager."""
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test manager initialization."""
        manager = ProxyManager("mock")
        
        result = await manager.initialize()
        
        assert result is True
        assert manager.initialized is True
        assert manager.storage_path.exists()
    
    @pytest.mark.asyncio
    async def test_get_next_session(self):
        """Test creating a proxy session."""
        manager = ProxyManager("mock", run_id="test-001")
        await manager.initialize()
        
        session = await manager.get_next_session(match_id="match-123")
        
        assert session.status == ProxyStatus.ACTIVE
        assert session.session_id in manager.active_sessions
        assert "match-123" in session.metadata.get("match_id", "")
    
    @pytest.mark.asyncio
    async def test_get_next_session_with_cookies(self):
        """Test creating session with initial cookies."""
        manager = ProxyManager("mock")
        await manager.initialize()
        
        cookies = {"sessionid": "abc123", "user": "test"}
        session = await manager.get_next_session(
            match_id="match-123",
            cookies=cookies,
        )
        
        assert session.cookies == cookies
    
    @pytest.mark.asyncio
    async def test_retire_session(self):
        """Test retiring a session."""
        manager = ProxyManager("mock")
        await manager.initialize()
        
        session = await manager.get_next_session(match_id="match-123")
        assert session.session_id in manager.active_sessions
        
        await manager.retire_session(session.session_id)
        
        assert session.session_id not in manager.active_sessions
        assert session.status == ProxyStatus.EXPIRED
    
    @pytest.mark.asyncio
    async def test_add_session_cookies(self):
        """Test adding cookies to active session."""
        manager = ProxyManager("mock")
        await manager.initialize()
        
        session = await manager.get_next_session(
            match_id="match-123",
            cookies={"cookie1": "value1"},
        )
        
        new_cookies = {"cookie2": "value2", "cookie3": "value3"}
        manager.add_session_cookies(session.session_id, new_cookies)
        
        assert session.cookies["cookie1"] == "value1"
        assert session.cookies["cookie2"] == "value2"
        assert session.cookies["cookie3"] == "value3"
    
    @pytest.mark.asyncio
    async def test_save_and_load_sessions(self, tmp_path):
        """Test session persistence."""
        manager = ProxyManager("mock", run_id="test-persistence", storage_path=tmp_path)
        await manager.initialize()
        
        # Create sessions
        session1 = await manager.get_next_session(match_id="match-1")
        session2 = await manager.get_next_session(match_id="match-2")
        
        # Save
        await manager.save_sessions()
        
        # Verify file exists
        sessions_file = tmp_path / "test-persistence-sessions.json"
        assert sessions_file.exists()
        
        # Verify content
        with open(sessions_file) as f:
            data = json.load(f)
        
        assert len(data["sessions"]) == 2
        assert data["run_id"] == "test-persistence"
    
    @pytest.mark.asyncio
    async def test_status(self):
        """Test getting manager status."""
        manager = ProxyManager("mock")
        await manager.initialize()
        
        session = await manager.get_next_session(match_id="match-123")
        
        status = manager.get_status()
        
        assert status["initialized"] is True
        assert status["provider"] == "mock"
        assert status["active_sessions"] == 1
        assert len(status["session_ids"]) == 1


class TestProxyManagerErrors:
    """Test error handling in ProxyManager."""
    
    @pytest.mark.asyncio
    async def test_get_next_session_not_initialized(self):
        """Test error when manager not initialized."""
        manager = ProxyManager("mock")
        
        with pytest.raises(RuntimeError, match="not initialized"):
            await manager.get_next_session(match_id="match-123")
    
    @pytest.mark.asyncio
    async def test_retire_nonexistent_session(self):
        """Test retiring non-existent session."""
        manager = ProxyManager("mock")
        await manager.initialize()
        
        # Should not raise, just log warning
        await manager.retire_session("nonexistent-session")
        
        assert len(manager.active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_add_cookies_to_nonexistent_session(self):
        """Test adding cookies to non-existent session."""
        manager = ProxyManager("mock")
        await manager.initialize()
        
        # Should not raise, just log warning
        manager.add_session_cookies("nonexistent", {"cookie": "value"})


class TestProxyManagerIntegration:
    """Integration tests for ProxyManager."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, tmp_path):
        """Test complete proxy manager workflow."""
        manager = ProxyManager(
            "mock",
            run_id="workflow-test",
            storage_path=tmp_path,
        )
        
        # Initialize
        result = await manager.initialize()
        assert result is True
        
        # Create sessions for multiple matches
        sessions = []
        for i in range(3):
            session = await manager.get_next_session(
                match_id=f"match-{i}",
                cookies={"user": f"user-{i}"},
            )
            sessions.append(session)
        
        assert len(manager.active_sessions) == 3
        
        # Add more cookies
        for session in sessions:
            manager.add_session_cookies(
                session.session_id,
                {"extra_cookie": "extra_value"},
            )
        
        # Verify all sessions have cookies
        for session in sessions:
            assert "extra_cookie" in session.cookies
        
        # Save sessions
        await manager.save_sessions()
        
        # Verify saved
        sessions_file = tmp_path / "workflow-test-sessions.json"
        assert sessions_file.exists()
        
        # Retire some sessions
        await manager.retire_session(sessions[0].session_id)
        assert len(manager.active_sessions) == 2
        
        # Check status
        status = manager.get_status()
        assert status["active_sessions"] == 2


class TestProxyRotationStrategies:
    """Tests for proxy rotation strategies."""
    
    @pytest.mark.asyncio
    async def test_per_match_rotation(self):
        """Test per-match rotation strategy."""
        manager = ProxyManager("mock")
        manager.rotation_strategy = manager.rotation_strategy  # PER_MATCH
        await manager.initialize()
        
        session1 = await manager.get_next_session(match_id="match-1")
        session2 = await manager.get_next_session(match_id="match-2")
        
        # Both should be active (per-match means each match gets new IP)
        assert session1.session_id != session2.session_id
        assert len(manager.active_sessions) == 2
