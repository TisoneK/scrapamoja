"""
Integration tests for browser session management.

This test suite validates the complete browser session lifecycle including
creation, context management, resource monitoring, and cleanup.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.browser import BrowserManager, BrowserSession, BrowserConfiguration
from src.browser.config import BrowserType, SessionStatus
from src.observability.events import EventTypes
from src.observability.metrics import get_browser_metrics_collector
from tests.fixtures.browser_configs import CHROMIUM_HEADLESS_CONFIG


class TestBrowserSessionManagement:
    """Integration tests for browser session management."""
    
    @pytest.fixture
    async def browser_manager(self):
        """Create a browser manager for testing."""
        manager = BrowserManager()
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_session_creation_and_lifecycle(self, browser_manager):
        """Test complete session lifecycle from creation to termination."""
        # Create session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        assert session is not None
        assert session.session_id is not None
        assert session.status == SessionStatus.ACTIVE
        assert session.configuration.browser_type == BrowserType.CHROMIUM
        
        # Create context
        context = await session.create_context()
        assert context is not None
        assert len(session.contexts) == 1
        
        # Create page
        page = await session.create_page(context)
        assert page is not None
        assert len(session.pages) == 1
        
        # Verify metrics tracking
        metrics_collector = get_browser_metrics_collector()
        session_metrics = metrics_collector.get_session_metrics(session.session_id)
        assert session_metrics is not None
        assert session_metrics.total_contexts_created == 1
        assert session_metrics.total_pages_created == 1
        
        # Close session
        await browser_manager.close_session(session.session_id)
        
        # Verify session is removed from manager
        assert session.session_id not in browser_manager._sessions
    
    @pytest.mark.asyncio
    async def test_concurrent_session_management(self, browser_manager):
        """Test managing multiple sessions concurrently."""
        sessions = []
        
        # Create multiple sessions
        for i in range(3):
            session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
            sessions.append(session)
        
        # Verify all sessions are active
        active_sessions = await browser_manager.get_active_sessions()
        assert len(active_sessions) == 3
        
        # Create contexts in each session
        for session in sessions:
            await session.create_context()
        
        # Verify metrics across all sessions
        metrics_collector = get_browser_metrics_collector()
        all_metrics = metrics_collector.get_all_session_metrics()
        assert len(all_metrics) == 3
        
        # Close all sessions
        for session in sessions:
            await browser_manager.close_session(session.session_id)
        
        # Verify all sessions are closed
        active_sessions = await browser_manager.get_active_sessions()
        assert len(active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_session_failure_handling(self, browser_manager):
        """Test session failure handling and cleanup."""
        # Mock Playwright to simulate failure
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            mock_playwright.return_value.start.return_value.chromium.launch.side_effect = Exception("Browser launch failed")
            
            # Session creation should fail
            with pytest.raises(Exception):
                await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
            
            # Verify no sessions are left in manager
            active_sessions = await browser_manager.get_active_sessions()
            assert len(active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_resource_monitoring_integration(self, browser_manager):
        """Test resource monitoring integration."""
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Update metrics
        await session.update_metrics()
        
        # Verify metrics are tracked
        metrics_collector = get_browser_metrics_collector()
        session_metrics = metrics_collector.get_session_metrics(session.session_id)
        assert session_metrics is not None
        
        # Record resource usage
        metrics_collector.record_resource_usage(session.session_id, 256.0, 45.5)
        
        # Finalize metrics
        final_metrics = metrics_collector.finalize_session_metrics(session.session_id)
        assert final_metrics is not None
        assert final_metrics.peak_memory_mb >= 256.0
        
        await browser_manager.close_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_event_publishing_integration(self, browser_manager):
        """Test event publishing during session lifecycle."""
        events_received = []
        
        # Subscribe to browser events
        from src.observability.events import get_event_bus
        event_bus = get_event_bus()
        
        def event_handler(event):
            events_received.append(event)
        
        # Subscribe to session events
        subscription_id = event_bus.subscribe(EventTypes.BROWSER_SESSION_CREATED, event_handler)
        
        try:
            # Create session (should publish event)
            session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
            
            # Wait for async event processing
            await asyncio.sleep(0.1)
            
            # Verify event was published
            session_created_events = [e for e in events_received if e.event_type == EventTypes.BROWSER_SESSION_CREATED]
            assert len(session_created_events) >= 1
            
            await browser_manager.close_session(session.session_id)
            
        finally:
            event_bus.unsubscribe(subscription_id)
    
    @pytest.mark.asyncio
    async def test_session_statistics(self, browser_manager):
        """Test session statistics collection."""
        # Create sessions with different statuses
        session1 = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        session2 = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Get statistics
        stats = await browser_manager.get_statistics()
        
        assert stats.total_sessions == 2
        assert stats.active_sessions == 2
        assert stats.failed_sessions == 0
        assert stats.terminated_sessions == 0
        
        # Close one session
        await browser_manager.close_session(session1.session_id)
        
        # Update statistics
        stats = await browser_manager.get_statistics()
        assert stats.active_sessions == 1
        assert stats.terminated_sessions == 0  # Session is removed from manager after close
        
        await browser_manager.close_session(session2.session_id)
    
    @pytest.mark.asyncio
    async def test_session_persistence(self, browser_manager):
        """Test session state persistence."""
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Session should be persisted automatically
        session_dict = session.to_dict()
        assert session_dict["session_id"] == session.session_id
        assert session_dict["status"] == SessionStatus.ACTIVE.value
        
        # Create context to test persistence
        context = await session.create_context()
        assert len(session.contexts) == 1
        
        await browser_manager.close_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_cleanup_automation(self, browser_manager):
        """Test automatic cleanup of inactive sessions."""
        # Create a session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Simulate inactive session by updating last_activity
        session.last_activity = datetime.utcnow().timestamp() - 3600  # 1 hour ago
        
        # Run cleanup
        cleaned_count = await browser_manager.cleanup_inactive_sessions()
        
        # Session should be cleaned up
        assert cleaned_count >= 1
        assert session.session_id not in browser_manager._sessions


class TestBrowserSessionResilience:
    """Test resilience patterns for browser sessions."""
    
    @pytest.mark.asyncio
    async def test_retry_on_session_creation_failure(self):
        """Test retry logic for session creation failures."""
        manager = BrowserManager()
        await manager.initialize()
        
        try:
            # Mock Playwright to fail initially then succeed
            call_count = 0
            original_launch = None
            
            async def mock_launch(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise Exception("Temporary failure")
                # Return mock browser on third attempt
                mock_browser = Mock()
                mock_browser.close = AsyncMock()
                return mock_browser
            
            with patch('playwright.async_api.async_playwright') as mock_playwright:
                mock_playwright.return_value.start.return_value.chromium.launch = mock_launch
                
                # Session should succeed after retries
                session = await manager.create_session(CHROMIUM_HEADLESS_CONFIG)
                assert session is not None
                assert call_count >= 2  # Should have retried
                
        finally:
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_on_repeated_failures(self):
        """Test circuit breaker pattern on repeated failures."""
        manager = BrowserManager()
        await manager.initialize()
        
        try:
            # Mock persistent failure
            with patch('playwright.async_api.async_playwright') as mock_playwright:
                mock_playwright.return_value.start.return_value.chromium.launch.side_effect = Exception("Persistent failure")
                
                # Multiple failures should trigger circuit breaker
                for i in range(6):  # Exceed failure threshold
                    try:
                        await manager.create_session(CHROMIUM_HEADLESS_CONFIG)
                    except Exception:
                        pass  # Expected to fail
                
                # Check circuit breaker status
                from src.browser.resilience import resilience_manager
                circuit_status = resilience_manager.get_circuit_status()
                assert "default" in circuit_status
                assert circuit_status["default"]["state"] in ["open", "half_open"]
                
        finally:
            await manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
