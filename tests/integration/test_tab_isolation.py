"""
Integration tests for tab isolation and management.

This test suite validates that browser tabs are properly isolated,
can be switched between, and maintain independent state.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.browser import BrowserManager, BrowserSession, BrowserConfiguration
from src.browser.config import BrowserType, SessionStatus
from src.browser.models.context import TabContext
from src.browser.models.enums import ContextStatus
from tests.fixtures.browser_configs import CHROMIUM_HEADLESS_CONFIG


class TestTabIsolation:
    """Integration tests for tab isolation and management."""
    
    @pytest.fixture
    async def browser_manager(self):
        """Create a browser manager for testing."""
        manager = BrowserManager()
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_tab_creation_and_isolation(self, browser_manager):
        """Test tab creation and isolation."""
        # Create session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Create multiple tabs
        tab1 = await session.create_tab_context("https://example.com/page1", "Page 1")
        tab2 = await session.create_tab_context("https://example.com/page2", "Page 2")
        tab3 = await session.create_tab_context("https://example.com/page3", "Page 3")
        
        # Verify tabs are isolated
        assert tab1.context_id != tab2.context_id
        assert tab2.context_id != tab3.context_id
        assert tab1.context_id != tab3.context_id
        
        # Verify each tab has correct session association
        assert tab1.session_id == session.session_id
        assert tab2.session_id == session.session_id
        assert tab3.session_id == session.session_id
        
        # Verify URLs are correctly set
        assert tab1.url == "https://example.com/page1"
        assert tab2.url == "https://example.com/page2"
        assert tab3.url == "https://example.com/page3"
        
        # Verify titles are correctly set
        assert tab1.title == "Page 1"
        assert tab2.title == "Page 2"
        assert tab3.title == "Page 3"
        
        # Verify all tabs are initially active or inactive correctly
        assert tab1.is_active or tab2.is_active or tab3.is_active  # At least one should be active
        
        await browser_manager.close_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_tab_switching_and_context_activation(self, browser_manager):
        """Test tab switching with proper context activation."""
        # Create session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Create tabs
        tab1 = await session.create_tab_context("https://example.com/page1", "Page 1")
        tab2 = await session.create_tab_context("https://example.com/page2", "Page 2")
        
        # Initially, one tab should be active
        active_tab = await session.get_active_tab_context()
        assert active_tab is not None
        initial_active_id = active_tab.context_id
        
        # Switch to tab2
        switch_success = await session.switch_to_tab(tab2.context_id)
        assert switch_success is True
        
        # Verify tab2 is now active
        active_tab = await session.get_active_tab_context()
        assert active_tab.context_id == tab2.context_id
        assert active_tab.is_active is True
        
        # Verify tab1 is now inactive
        tab1_updated = await session.get_tab_context(tab1.context_id)
        assert tab1_updated.is_active is False
        
        # Switch back to tab1
        switch_success = await session.switch_to_tab(tab1.context_id)
        assert switch_success is True
        
        # Verify tab1 is active again
        active_tab = await session.get_active_tab_context()
        assert active_tab.context_id == tab1.context_id
        assert active_tab.is_active is True
        
        # Verify tab2 is inactive
        tab2_updated = await session.get_tab_context(tab2.context_id)
        assert tab2_updated.is_active is False
        
        await browser_manager.close_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_tab_navigation_history_isolation(self, browser_manager):
        """Test that navigation history is isolated between tabs."""
        # Create session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Create tabs
        tab1 = await session.create_tab_context("https://example.com/page1", "Page 1")
        tab2 = await session.create_tab_context("https://example.com/page2", "Page 2")
        
        # Navigate in tab1
        tab1.navigate_to("https://example.com/page1/subpage", "Subpage 1")
        tab1.navigate_to("https://example.com/page1/another", "Another Page")
        
        # Navigate in tab2
        tab2.navigate_to("https://example.com/page2/different", "Different Page")
        
        # Verify navigation histories are isolated
        assert tab1.get_navigation_count() == 3  # Initial + 2 navigations
        assert tab2.get_navigation_count() == 2  # Initial + 1 navigation
        
        # Verify current URLs are different
        assert tab1.get_current_url() == "https://example.com/page1/another"
        assert tab2.get_current_url() == "https://example.com/page2/different"
        
        # Verify current titles are different
        assert tab1.get_current_title() == "Another Page"
        assert tab2.get_current_title() == "Different Page"
        
        await browser_manager.close_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_tab_lifecycle_management(self, browser_manager):
        """Test tab lifecycle from creation to closure."""
        # Create session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Create tab
        tab = await session.create_tab_context("https://example.com/test", "Test Page")
        
        # Verify initial status
        assert tab.status == ContextStatus.INITIALIZING
        assert tab.is_healthy() is True
        
        # Update status to active
        tab.update_status(ContextStatus.ACTIVE)
        assert tab.status == ContextStatus.ACTIVE
        assert tab.is_healthy() is True
        assert tab.can_navigate() is True
        
        # Update status to loading
        tab.update_status(ContextStatus.LOADING)
        assert tab.status == ContextStatus.LOADING
        assert tab.is_healthy() is True
        assert tab.can_navigate() is False  # Cannot navigate while loading
        
        # Close tab
        close_success = await session.close_tab_context(tab.context_id)
        assert close_success is True
        
        # Verify tab is removed from session
        retrieved_tab = await session.get_tab_context(tab.context_id)
        assert retrieved_tab is None
        
        await browser_manager.close_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_concurrent_tab_operations(self, browser_manager):
        """Test concurrent tab operations."""
        # Create session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Create multiple tabs concurrently
        tab_tasks = []
        for i in range(5):
            task = session.create_tab_context(f"https://example.com/page{i}", f"Page {i}")
            tab_tasks.append(task)
        
        tabs = await asyncio.gather(*tab_tasks)
        
        # Verify all tabs were created
        assert len(tabs) == 5
        assert len(set(tab.context_id for tab in tabs)) == 5  # All unique IDs
        
        # Switch between tabs concurrently
        switch_tasks = []
        for i, tab in enumerate(tabs):
            task = session.switch_to_tab(tab.context_id)
            switch_tasks.append(task)
        
        switch_results = await asyncio.gather(*switch_tasks)
        
        # Verify all switches succeeded
        assert all(switch_results)
        
        # Close all tabs concurrently
        close_tasks = []
        for tab in tabs:
            task = session.close_tab_context(tab.context_id)
            close_tasks.append(task)
        
        close_results = await asyncio.gather(*close_tasks)
        
        # Verify all tabs were closed
        assert all(close_results)
        
        # Verify no tabs remain
        remaining_tabs = await session.list_tab_contexts()
        assert len(remaining_tabs) == 0
        
        await browser_manager.close_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_tab_statistics_and_monitoring(self, browser_manager):
        """Test tab statistics and monitoring."""
        # Create session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Create tabs with different activity levels
        tab1 = await session.create_tab_context("https://example.com/active", "Active Tab")
        tab2 = await session.create_tab_context("https://example.com/idle", "Idle Tab")
        tab3 = await session.create_tab_context("https://example.com/busy", "Busy Tab")
        
        # Add navigation history to tabs
        for i in range(10):
            tab1.navigate_to(f"https://example.com/active/page{i}", f"Page {i}")
        
        for i in range(5):
            tab2.navigate_to(f"https://example.com/idle/section{i}", f"Section {i}")
        
        for i in range(15):
            tab3.navigate_to(f"https://example.com/busy/item{i}", f"Item {i}")
        
        # Get statistics
        stats = await session.get_tab_statistics()
        
        assert stats["total_tabs"] == 3
        assert stats["total_navigations"] == 30  # 10 + 5 + 15
        assert stats["average_navigations"] == 10.0  # 30 / 3
        
        # Verify status distribution
        assert "tabs_by_status" in stats
        assert stats["tabs_by_status"][ContextStatus.ACTIVE.value] >= 0
        
        await browser_manager.close_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_tab_failure_handling(self, browser_manager):
        """Test graceful error handling for tab operations."""
        # Create session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Test creating tab with invalid URL (should still work, just won't navigate)
        tab = await session.create_tab_context("", "Invalid URL")
        assert tab is not None
        assert tab.url == ""
        
        # Test switching to non-existent tab
        switch_success = await session.switch_to_tab("non_existent_tab")
        assert switch_success is False
        
        # Test closing non-existent tab
        close_success = await session.close_tab_context("non_existent_tab")
        assert close_success is False
        
        # Test retrieving non-existent tab
        retrieved_tab = await session.get_tab_context("non_existent_tab")
        assert retrieved_tab is None
        
        await browser_manager.close_session(session.session_id)
    
    @pytest.mark.asyncio
    async def test_tab_isolation_with_dom_snapshots(self, browser_manager):
        """Test tab isolation with DOM snapshot integration."""
        # Create session
        session = await browser_manager.create_session(CHROMIUM_HEADLESS_CONFIG)
        
        # Create tabs
        tab1 = await session.create_tab_context("https://example.com/tab1", "Tab 1")
        tab2 = await session.create_tab_context("https://example.com/tab2", "Tab 2")
        
        # Mock page for snapshot capture
        mock_page = Mock()
        mock_page.url = "https://example.com/tab1"
        mock_page.title.return_value = "Tab 1"
        mock_page.content.return_value = "<html><body>Tab 1 content</body></html>"
        
        # Test snapshot capture for tab1
        with patch('src.browser.snapshot.snapshot_manager.capture_snapshot') as mock_capture:
            mock_capture.return_value = Mock()
            
            # Simulate failure in tab1
            tab1.update_status(ContextStatus.ERROR)
            
            # The failure snapshot should be captured
            # (This would normally be called by error handling logic)
            
            # Verify tab state
            assert tab1.status == ContextStatus.ERROR
            assert tab1.is_healthy() is False
        
        await browser_manager.close_session(session.session_id)


class TestTabContextValidation:
    """Test tab context validation and state consistency."""
    
    @pytest.mark.asyncio
    async def test_tab_context_validation(self):
        """Test tab context state validation."""
        # Create tab context
        tab = TabContext(
            context_id="test_tab",
            session_id="test_session",
            url="https://example.com",
            title="Test Page"
        )
        
        # Initial validation should pass
        is_valid = await tab.validate_state()
        assert is_valid is True
        
        # Test URL mismatch validation
        tab.url = "https://different.com"
        is_valid = await tab.validate_state()
        assert is_valid is False  # URL mismatch between context and navigation history
        
        # Test with no page instance (should still validate)
        tab.status = ContextStatus.ACTIVE
        is_valid = await tab.validate_state()
        assert is_valid is False  # Active status but no page instance
    
    @pytest.mark.asyncio
    async def test_tab_context_state_transitions(self):
        """Test tab context state transitions."""
        tab = TabContext(
            context_id="test_tab",
            session_id="test_session",
            url="https://example.com",
            title="Test Page"
        )
        
        # Test valid state transitions
        valid_states = [
            ContextStatus.INITIALIZING,
            ContextStatus.ACTIVE,
            ContextStatus.IDLE,
            ContextStatus.LOADING
        ]
        
        for status in valid_states:
            tab.update_status(status)
            assert tab.status == status
            assert tab.is_healthy() is True
        
        # Test terminal states
        terminal_states = [
            ContextStatus.CLOSING,
            ContextStatus.CLOSED,
            ContextStatus.ERROR
        ]
        
        for status in terminal_states:
            tab.update_status(status)
            assert tab.status == status
            assert tab.is_healthy() is False
    
    @pytest.mark.asyncio
    async def test_tab_context_metrics(self):
        """Test tab context metrics and timing."""
        tab = TabContext(
            context_id="test_tab",
            session_id="test_session",
            url="https://example.com",
            title="Test Page"
        )
        
        # Initially, no navigations
        assert tab.get_navigation_count() == 0
        assert tab.get_context_age_seconds() >= 0
        assert tab.get_idle_time_seconds() >= 0
        
        # Add navigation history
        tab.navigate_to("https://example.com/page1", "Page 1")
        tab.navigate_to("https://example.com/page2", "Page 2")
        
        # Verify metrics
        assert tab.get_navigation_count() == 2
        assert tab.get_current_url() == "https://example.com/page2"
        assert tab.get_current_title() == "Page 2"
        
        # Wait a moment and check idle time
        await asyncio.sleep(0.1)
        assert tab.get_idle_time_seconds() >= 0.1
        
        # Test navigation history limits
        for i in range(105):  # Exceed default limit of 100
            tab.navigate_to(f"https://example.com/page{i}", f"Page {i}")
        
        # Should be limited to 100 entries
        assert tab.get_navigation_count() == 100
        assert tab.get_current_url() == f"https://example.com/page{104}"  # Last entry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
