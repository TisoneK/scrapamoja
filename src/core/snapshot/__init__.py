"""
Snapshot System - Comprehensive browser state capture for web scraping.

This module provides a sophisticated context-aware system designed to capture,
organize, and manage browser state snapshots for web scraping operations.

Key Features:
- Context-Aware Organization: Hierarchical organization by site, module, component, and timestamp
- Dual HTML Capture: Full page and element-specific HTML capture
- Event-Driven Triggers: Automatic capture on failures, timeouts, and extraction mismatches
- Performance Optimized: Async parallel artifact saving with deduplication
- Simple Configuration: Clean settings without feature flag complexity
- Comprehensive Monitoring: Built-in metrics collection and performance tracking

Usage Example:
    from src.core.snapshot import SnapshotManager, SnapshotContext, SnapshotConfig, SnapshotMode
from src.core.snapshot.config import get_settings
    
    # Initialize manager
    snapshot_settings = get_settings()
    manager = SnapshotManager(snapshot_settings.base_path)
    
    # Create context
    context = SnapshotContext(
        site="flashscore",
        module="navigation",
        component="menu",
        session_id="session_123"
    )
    
    # Create config
    config = SnapshotConfig(
        mode=SnapshotMode.SELECTOR,
        capture_html=True,
        selector=".menu-item"
    )
    
    # Capture snapshot
    bundle = await manager.capture_snapshot(page, context, config)
"""

# Core exports
from .manager import SnapshotManager, get_snapshot_manager
from .models import (
    # Data models
    SnapshotContext,
    SnapshotConfig,
    SnapshotBundle,
    SnapshotMetrics,
    
    # Enums
    SnapshotMode,
    
    # Utility classes
    RateLimiter,
    ContentDeduplicator,
    
    # Exceptions
    SnapshotError,
    ArtifactCaptureError,
    ConfigurationError
)

from .exceptions import (
    StorageError,
    ValidationError,
    TriggerError,
    IntegrationError,
    MetricsError
)

from .storage import SnapshotStorage, AtomicFileWriter
from .capture import SnapshotCapture
from .triggers import (
    TriggerManager,
    SnapshotTrigger,
    SelectorFailureTrigger,
    RetryExhaustionTrigger,
    TimeoutTrigger,
    ExtractionMismatchTrigger,
    ManualTrigger
)
from .config import (
    SnapshotSettings,
    get_settings,
    get_development_settings,
    get_testing_settings,
    get_production_settings
)
from .metrics import (
    MetricsCollector,
    HealthMonitor,
    MonitoringDashboard,
    PerformanceMetric,
    HealthCheck
)
from .handlers import (
    BrowserSnapshot,
    SessionSnapshot,
    ScraperSnapshot,
    SelectorSnapshot,
    ErrorSnapshot,
    RetrySnapshot,
    MonitoringSnapshot,
    SnapshotCoordinator
)

# Version information
__version__ = "1.0.0"
__author__ = "Snapshot System Team"

# Public API
__all__ = [
    # Core classes
    "SnapshotManager",
    "get_snapshot_manager",
    
    # Data models
    "SnapshotContext",
    "SnapshotConfig",
    "SnapshotBundle",
    "SnapshotMetrics",
    
    # Enums
    "SnapshotMode",
    
    # Utility classes
    "RateLimiter",
    "ContentDeduplicator",
    
    # Exceptions
    "SnapshotError",
    "SnapshotValidationError",
    "SnapshotStorageError",
    "SnapshotCaptureError",
    "ArtifactCaptureError",
    "ConfigurationError",
    "StorageError",
    "DiskFullError",
    "PermissionError",
    "IntegrationError",
    "MetricsError",
    
    # Storage
    "SnapshotStorage",
    "AtomicFileWriter",
    
    # Capture
    "SnapshotCapture",
    
    # Triggers
    "TriggerManager",
    "SnapshotTrigger",
    "SelectorFailureTrigger",
    "RetryExhaustionTrigger",
    "TimeoutTrigger",
    "ExtractionMismatchTrigger",
    "ManualTrigger",
    
    # Configuration
    "SnapshotSettings",
    "get_settings",
    "get_development_settings",
    "get_testing_settings",
    "get_production_settings",
    
    # Monitoring
    "MetricsCollector",
    "HealthMonitor",
    "MonitoringDashboard",
    "PerformanceMetric",
    "HealthCheck",
    
    # Handlers
    "BrowserSnapshot",
    "SessionSnapshot", 
    "ScraperSnapshot",
    "SelectorSnapshot",
    "ErrorSnapshot",
    "RetrySnapshot",
    "MonitoringSnapshot",
    "SnapshotCoordinator",
    
    # Version
    "__version__",
    "__author__"
]

# Convenience functions for quick access
async def capture_quick_snapshot(page, 
                                site: str, 
                                module: str, 
                                component: str, 
                                session_id: str,
                                selector: Optional[str] = None,
                                mode: SnapshotMode = SnapshotMode.SELECTOR) -> Optional[SnapshotBundle]:
    """
    Quick snapshot capture function for common use cases.
    
    Args:
        page: Browser page object
        site: Website domain
        module: Functional module
        component: Specific component
        session_id: Session identifier
        selector: CSS selector for element capture (optional)
        mode: Snapshot capture mode
        
    Returns:
        SnapshotBundle if successful, None otherwise
    """
    manager = get_snapshot_manager()
    
    context = SnapshotContext(
        site=site,
        module=module,
        component=component,
        session_id=session_id
    )
    
    config = SnapshotConfig(
        mode=mode,
        capture_html=True,
        capture_screenshot=True,
        selector=selector
    )
    
    return await manager.capture_snapshot(page, context, config)

def is_snapshot_enabled(site: Optional[str] = None) -> bool:
    """
    Check if snapshot system is enabled for a site.
    
    Args:
        site: Site to check (optional)
        
    Returns:
        True if snapshots are enabled, False otherwise
    """
    settings = get_settings()
    return settings.enable_metrics

# Module initialization
def _initialize_module():
    """Initialize the snapshot module."""
    import os
    
    # Create default directories if they don't exist
    directories = [
        "data/snapshots",
        "config"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Initialize module on import
_initialize_module()
