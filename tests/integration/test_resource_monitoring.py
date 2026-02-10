"""
Resource Monitoring Integration Tests

Integration tests for browser resource monitoring functionality.
"""

import pytest
import asyncio
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import psutil

from src.browser.monitoring import ResourceMonitor, MonitoringSession
from src.browser.models.metrics import ResourceMetrics, AlertStatus
from src.browser.models.enums import CleanupLevel
from src.browser.monitoring_error_handler import MonitoringErrorHandler, MonitoringErrorType
from src.browser.resource_logger import ResourceOperation, get_resource_logger
from src.browser.authority import BrowserAuthority


class TestResourceMonitorIntegration:
    """Integration tests for ResourceMonitor."""
    
    @pytest.fixture
    async def resource_monitor(self):
        """Create ResourceMonitor instance."""
        monitor = ResourceMonitor(
            check_interval=1.0,  # Short interval for testing
            memory_threshold_mb=100.0,
            cpu_threshold_percent=50.0,
            disk_threshold_mb=500.0
        )
        await monitor.initialize()
        yield monitor
        await monitor.shutdown()
        
    @pytest.fixture
    def mock_process(self):
        """Create mock process for testing."""
        process = Mock()
        process.memory_info.return_value = Mock()
        process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
        process.cpu_percent.return_value = 25.0
        process.open_files.return_value = [Mock(), Mock(), Mock()]
        return process
        
    @pytest.mark.asyncio
    async def test_monitor_initialization(self, resource_monitor):
        """Test resource monitor initialization."""
        assert resource_monitor.lifecycle_state.is_healthy()
        assert resource_monitor.memory_threshold_mb == 100.0
        assert resource_monitor.cpu_threshold_percent == 50.0
        assert resource_monitor.disk_threshold_mb == 500.0
        
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, resource_monitor):
        """Test starting and stopping monitoring."""
        session_id = "test_session_1"
        
        # Start monitoring
        await resource_monitor.start_monitoring(session_id)
        
        assert session_id in resource_monitor.monitoring_sessions
        assert resource_monitor.is_monitoring is True
        assert len(resource_monitor.monitoring_sessions) == 1
        
        # Stop monitoring
        await resource_monitor.stop_monitoring(session_id)
        
        assert session_id not in resource_monitor.monitoring_sessions
        assert len(resource_monitor.monitoring_sessions) == 0
        
    @pytest.mark.asyncio
    async def test_multiple_sessions_monitoring(self, resource_monitor):
        """Test monitoring multiple sessions."""
        session_ids = ["session_1", "session_2", "session_3"]
        
        # Start monitoring multiple sessions
        for session_id in session_ids:
            await resource_monitor.start_monitoring(session_id)
            
        assert len(resource_monitor.monitoring_sessions) == 3
        assert all(sid in resource_monitor.monitoring_sessions for sid in session_ids)
        
        # Stop all monitoring
        for session_id in session_ids:
            await resource_monitor.stop_monitoring(session_id)
            
        assert len(resource_monitor.monitoring_sessions) == 0
        
    @pytest.mark.asyncio
    async def test_metrics_collection(self, resource_monitor, mock_process):
        """Test metrics collection."""
        session_id = "test_session_metrics"
        
        await resource_monitor.start_monitoring(session_id)
        
        with patch('psutil.Process', return_value=mock_process):
            metrics = await resource_monitor.get_metrics(session_id)
            
        assert metrics.session_id == session_id
        assert metrics.memory_usage_mb == 100.0
        assert metrics.cpu_usage_percent == 25.0
        assert metrics.process_handles_count == 3
        assert metrics.alert_status == AlertStatus.NORMAL
        
        await resource_monitor.stop_monitoring(session_id)
        
    @pytest.mark.asyncio
    async def test_threshold_checking_normal(self, resource_monitor, mock_process):
        """Test threshold checking with normal metrics."""
        session_id = "test_session_normal"
        
        # Set normal metrics
        mock_process.memory_info.return_value.rss = 50 * 1024 * 1024  # 50MB
        mock_process.cpu_percent.return_value = 25.0
        
        await resource_monitor.start_monitoring(session_id)
        
        with patch('psutil.Process', return_value=mock_process):
            alert_status = await resource_monitor.check_thresholds(session_id)
            
        assert alert_status == AlertStatus.NORMAL
        
        await resource_monitor.stop_monitoring(session_id)
        
    @pytest.mark.asyncio
    async def test_threshold_checking_warning(self, resource_monitor, mock_process):
        """Test threshold checking with warning metrics."""
        session_id = "test_session_warning"
        
        # Set warning metrics (above threshold but not critical)
        mock_process.memory_info.return_value.rss = 120 * 1024 * 1024  # 120MB (above 100MB threshold)
        mock_process.cpu_percent.return_value = 25.0
        
        await resource_monitor.start_monitoring(session_id)
        
        with patch('psutil.Process', return_value=mock_process):
            alert_status = await resource_monitor.check_thresholds(session_id)
            
        assert alert_status == AlertStatus.WARNING
        
        await resource_monitor.stop_monitoring(session_id)
        
    @pytest.mark.asyncio
    async def test_threshold_checking_critical(self, resource_monitor, mock_process):
        """Test threshold checking with critical metrics."""
        session_id = "test_session_critical"
        
        # Set critical metrics (well above threshold)
        mock_process.memory_info.return_value.rss = 200 * 1024 * 1024  # 200MB (2x 100MB threshold)
        mock_process.cpu_percent.return_value = 25.0
        
        await resource_monitor.start_monitoring(session_id)
        
        with patch('psutil.Process', return_value=mock_process):
            alert_status = await resource_monitor.check_thresholds(session_id)
            
        assert alert_status == AlertStatus.CRITICAL
        
        await resource_monitor.stop_monitoring(session_id)
        
    @pytest.mark.asyncio
    async def test_threshold_updates(self, resource_monitor):
        """Test updating monitoring thresholds."""
        old_thresholds = {
            "memory_mb": resource_monitor.memory_threshold_mb,
            "cpu_percent": resource_monitor.cpu_threshold_percent,
            "disk_mb": resource_monitor.disk_threshold_mb
        }
        
        # Update thresholds
        await resource_monitor.set_thresholds(200.0, 75.0, 1000.0)
        
        assert resource_monitor.memory_threshold_mb == 200.0
        assert resource_monitor.cpu_threshold_percent == 75.0
        assert resource_monitor.disk_threshold_mb == 1000.0
        
        # Verify old thresholds are different
        assert old_thresholds["memory_mb"] != resource_monitor.memory_threshold_mb
        assert old_thresholds["cpu_percent"] != resource_monitor.cpu_threshold_percent
        assert old_thresholds["disk_mb"] != resource_monitor.disk_threshold_mb
        
    @pytest.mark.asyncio
    async def test_cleanup_trigger_gentle(self, resource_monitor):
        """Test gentle cleanup trigger."""
        session_id = "test_cleanup_gentle"
        
        await resource_monitor.start_monitoring(session_id)
        
        # Trigger gentle cleanup
        success = await resource_monitor.trigger_cleanup(session_id, CleanupLevel.GENTLE)
        
        # Should succeed (mock implementation)
        assert success is True
        
        await resource_monitor.stop_monitoring(session_id)
        
    @pytest.mark.asyncio
    async def test_cleanup_trigger_moderate(self, resource_monitor):
        """Test moderate cleanup trigger."""
        session_id = "test_cleanup_moderate"
        
        await resource_monitor.start_monitoring(session_id)
        
        # Trigger moderate cleanup
        success = await resource_monitor.trigger_cleanup(session_id, CleanupLevel.MODERATE)
        
        # Should succeed (mock implementation)
        assert success is True
        
        await resource_monitor.stop_monitoring(session_id)
        
    @pytest.mark.asyncio
    async def test_monitoring_status(self, resource_monitor):
        """Test getting monitoring status."""
        session_id = "test_status_session"
        
        await resource_monitor.start_monitoring(session_id)
        
        status = await resource_monitor.get_monitoring_status()
        
        assert status["is_monitoring"] is True
        assert status["total_sessions"] == 1
        assert session_id in status["sessions"]
        assert "thresholds" in status
        assert status["thresholds"]["memory_mb"] == 100.0
        
        session_status = status["sessions"][session_id]
        assert session_status["session_id"] == session_id
        assert "start_time" in session_status
        assert "check_count" in session_status
        
        await resource_monitor.stop_monitoring(session_id)
        
    @pytest.mark.asyncio
    async def test_metrics_history(self, resource_monitor, mock_process):
        """Test metrics history tracking."""
        session_id = "test_history_session"
        
        await resource_monitor.start_monitoring(session_id)
        
        # Collect multiple metrics
        with patch('psutil.Process', return_value=mock_process):
            for i in range(5):
                metrics = await resource_monitor.get_metrics(session_id)
                assert metrics.session_id == session_id
                
        # Check history
        assert session_id in resource_monitor.metrics_history
        assert len(resource_monitor.metrics_history[session_id]) == 5
        
        await resource_monitor.stop_monitoring(session_id)


class TestMonitoringErrorHandlerIntegration:
    """Integration tests for MonitoringErrorHandler."""
    
    @pytest.fixture
    def error_handler(self):
        """Create MonitoringErrorHandler instance."""
        return MonitoringErrorHandler()
        
    @pytest.mark.asyncio
    async def test_metrics_collection_error_recovery(self, error_handler):
        """Test error recovery for metrics collection."""
        session_id = "test_error_session"
        
        # Test process not found error
        process_error = psutil.NoSuchProcess(99999)
        
        result = await error_handler.handle_metrics_collection_error(
            process_error,
            session_id
        )
        
        # Should return fallback metrics
        assert result is not None
        assert result.session_id == session_id
        assert result.memory_usage_mb == 0.0
        assert result.alert_status == AlertStatus.NORMAL
        
    @pytest.mark.asyncio
    async def test_threshold_check_error_recovery(self, error_handler):
        """Test error recovery for threshold checking."""
        session_id = "test_threshold_error"
        
        # Create metrics with high usage
        metrics = ResourceMetrics(
            session_id=session_id,
            memory_usage_mb=150.0,  # High memory
            cpu_usage_percent=60.0   # High CPU
        )
        
        # Test generic error
        generic_error = Exception("Threshold check failed")
        
        alert_status = await error_handler.handle_threshold_check_error(
            generic_error,
            session_id,
            metrics
        )
        
        # Should return WARNING due to high metrics
        assert alert_status == AlertStatus.WARNING
        
    @pytest.mark.asyncio
    async def test_cleanup_error_recovery(self, error_handler):
        """Test error recovery for cleanup operations."""
        session_id = "test_cleanup_error"
        
        # Test cleanup error
        cleanup_error = Exception("Cleanup failed")
        
        result = await error_handler.handle_cleanup_error(
            cleanup_error,
            session_id,
            CleanupLevel.MODERATE
        )
        
        # Should return False (cleanup failed)
        assert result is False
        
    def test_error_classification(self, error_handler):
        """Test error classification."""
        # Test process not found
        process_error = psutil.NoSuchProcess(99999)
        context = error_handler._create_error_context(
            process_error, "test_session", None
        )
        assert context.error_type == MonitoringErrorType.PROCESS_NOT_FOUND
        
        # Test access denied
        access_error = PermissionError("Access denied")
        context = error_handler._create_error_context(
            access_error, "test_session", None
        )
        assert context.error_type == MonitoringErrorType.ACCESS_DENIED
        
        # Test timeout
        timeout_error = TimeoutError("Operation timed out")
        context = error_handler._create_error_context(
            timeout_error, "test_session", None
        )
        assert context.error_type == MonitoringErrorType.TIMEOUT
        
        # Test unknown error
        unknown_error = ValueError("Unknown error")
        context = error_handler._create_error_context(
            unknown_error, "test_session", None
        )
        assert context.error_type == MonitoringErrorType.UNKNOWN_ERROR


class TestResourceLoggerIntegration:
    """Integration tests for ResourceLogger."""
    
    @pytest.fixture
    def resource_logger(self):
        """Create ResourceLogger instance."""
        return get_resource_logger()
        
    @pytest.mark.asyncio
    async def test_monitoring_operation_logging(self, resource_logger):
        """Test logging of monitoring operations."""
        session_id = "test_logging_session"
        correlation_id = "test_correlation_123"
        
        # Log monitoring start
        operation_id = resource_logger.log_monitoring_start(
            session_id=session_id,
            process_id=12345,
            correlation_id=correlation_id
        )
        
        assert operation_id is not None
        
        # Log monitoring stop
        resource_logger.log_monitoring_stop(
            session_id=session_id,
            success=True,
            session_duration_seconds=60.0,
            check_count=5,
            correlation_id=correlation_id
        )
        
        # Verify no active operations
        active_ops = resource_logger.get_active_operations()
        assert len(active_ops) == 0
        
    @pytest.mark.asyncio
    async def test_metrics_logging(self, resource_logger):
        """Test metrics collection logging."""
        session_id = "test_metrics_logging"
        
        metrics = {
            "memory_usage_mb": 100.0,
            "cpu_usage_percent": 25.0,
            "open_tabs_count": 3
        }
        
        # Log successful metrics collection
        resource_logger.log_metrics_collection(
            session_id=session_id,
            metrics=metrics,
            success=True,
            collection_time_ms=50.0
        )
        
        # Log failed metrics collection
        resource_logger.log_metrics_collection(
            session_id=session_id,
            metrics=metrics,
            success=False,
            error="Process not found"
        )
        
    @pytest.mark.asyncio
    async def test_threshold_check_logging(self, resource_logger):
        """Test threshold check logging."""
        session_id = "test_threshold_logging"
        
        metrics = {
            "memory_usage_mb": 150.0,
            "cpu_usage_percent": 60.0
        }
        
        thresholds = {
            "memory_threshold_mb": 100.0,
            "cpu_threshold_percent": 50.0
        }
        
        # Log warning threshold check
        resource_logger.log_threshold_check(
            session_id=session_id,
            alert_level=AlertStatus.WARNING,
            metrics=metrics,
            thresholds=thresholds,
            success=True
        )
        
        # Log critical threshold check
        resource_logger.log_threshold_check(
            session_id=session_id,
            alert_level=AlertStatus.CRITICAL,
            metrics=metrics,
            thresholds=thresholds,
            success=True
        )
        
    @pytest.mark.asyncio
    async def test_cleanup_logging(self, resource_logger):
        """Test cleanup operation logging."""
        session_id = "test_cleanup_logging"
        
        metrics = {
            "memory_usage_mb": 200.0,
            "cpu_usage_percent": 80.0
        }
        
        # Log cleanup trigger
        resource_logger.log_cleanup_trigger(
            session_id=session_id,
            cleanup_level="moderate",
            alert_level=AlertStatus.WARNING,
            metrics=metrics,
            success=True,
            cleanup_time_ms=100.0
        )
        
        # Log cleanup completion
        resource_logger.log_cleanup_completed(
            session_id=session_id,
            cleanup_level="moderate",
            success=True,
            cleanup_results={"tabs_closed": 2, "cache_cleared": True}
        )
        
    @pytest.mark.asyncio
    async def test_operation_context_tracking(self, resource_logger):
        """Test operation context tracking."""
        session_id = "test_context_tracking"
        
        # Start operation
        context = resource_logger.start_operation(
            ResourceOperation.COLLECT_METRICS,
            session_id=session_id,
            correlation_id="test_correlation_456"
        )
        
        assert context.operation_id is not None
        assert context.status.value == "started"
        
        # Update operation
        updated_context = resource_logger.complete_operation(
            context.operation_id,
            success=True,
            collection_time_ms=75.0
        )
        
        assert updated_context is not None
        assert updated_context.status.value == "completed"
        assert updated_context.duration_ms is not None


class TestBrowserAuthorityIntegration:
    """Integration tests for BrowserAuthority with resource monitoring."""
    
    @pytest.fixture
    async def browser_authority(self):
        """Create BrowserAuthority instance."""
        authority = BrowserAuthority()
        await authority.initialize()
        yield authority
        await authority.shutdown()
        
    @pytest.mark.asyncio
    async def test_session_creation_with_monitoring(self, browser_authority):
        """Test session creation with automatic monitoring."""
        from src.browser.models.session import BrowserConfiguration
        
        # Create session
        configuration = BrowserConfiguration(
            config_id="test_config",
            browser_type="chromium",
            headless=True
        )
        
        session = await browser_authority.create_session(configuration)
        
        assert session is not None
        assert session.session_id is not None
        assert session.status.value == "active"
        
        # Verify monitoring was started
        assert session.session_id in browser_authority.resource_monitor.monitoring_sessions
        
        # Terminate session
        success = await browser_authority.terminate_session(session.session_id)
        assert success is True
        
    @pytest.mark.asyncio
    async def test_resource_cleanup_integration(self, browser_authority):
        """Test resource cleanup integration."""
        from src.browser.models.session import BrowserConfiguration
        
        # Create session
        configuration = BrowserConfiguration(
            config_id="cleanup_test_config",
            browser_type="chromium",
            headless=True
        )
        
        session = await browser_authority.create_session(configuration)
        
        # Trigger resource cleanup
        success = await browser_authority.cleanup_resources(session.session_id)
        
        # Should succeed (mock implementation)
        assert success is True
        
        # Terminate session
        await browser_authority.terminate_session(session.session_id)
        
    @pytest.mark.asyncio
    async def test_system_metrics_aggregation(self, browser_authority):
        """Test system-wide metrics aggregation."""
        from src.browser.models.session import BrowserConfiguration
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            configuration = BrowserConfiguration(
                config_id=f"config_{i}",
                browser_type="chromium",
                headless=True
            )
            session = await browser_authority.create_session(configuration)
            sessions.append(session)
            
        # Get system metrics
        system_metrics = await browser_authority.get_system_metrics()
        
        assert system_metrics.session_id == "system"
        assert system_metrics.open_tabs_count >= 0  # Should aggregate from all sessions
        
        # Terminate all sessions
        for session in sessions:
            await browser_authority.terminate_session(session.session_id)
            
    @pytest.mark.asyncio
    async def test_authority_status_with_monitoring(self, browser_authority):
        """Test authority status including monitoring information."""
        from src.browser.models.session import BrowserConfiguration
        
        # Create session
        configuration = BrowserConfiguration(
            config_id="status_test_config",
            browser_type="chromium",
            headless=True
        )
        
        session = await browser_authority.create_session(configuration)
        
        # Get authority status
        status = await browser_authority.get_authority_status()
        
        assert "monitoring_status" in status
        assert "statistics" in status
        assert "sessions" in status
        assert session.session_id in status["sessions"]
        
        # Terminate session
        await browser_authority.terminate_session(session.session_id)
