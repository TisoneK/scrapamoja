"""
Snapshot Handlers Module

This module provides clean, consistent snapshot handlers for each
component of the scraping infrastructure.

Naming Convention: [Component]Snapshot
- BrowserSnapshot - Handles browser-related snapshots
- SessionSnapshot - Handles session-related snapshots  
- ScraperSnapshot - Handles scraper-related snapshots
- SelectorSnapshot - Handles selector-related snapshots
- ErrorSnapshot - Handles error-related snapshots
- RetrySnapshot - Handles retry-related snapshots
- MonitoringSnapshot - Handles monitoring-related snapshots
"""

from .browser import BrowserSnapshot
from .session import SessionSnapshot
from .scraper import ScraperSnapshot
from .selector import SelectorSnapshot
from .error import ErrorSnapshot
from .retry import RetrySnapshot
from .monitoring import MonitoringSnapshot
from .coordinator import SnapshotCoordinator

__all__ = [
    "BrowserSnapshot",
    "SessionSnapshot", 
    "ScraperSnapshot",
    "SelectorSnapshot",
    "ErrorSnapshot",
    "RetrySnapshot",
    "MonitoringSnapshot",
    "SnapshotCoordinator"
]
