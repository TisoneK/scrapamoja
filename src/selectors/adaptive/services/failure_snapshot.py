"""
Failure Snapshot Service - Integrates adaptive system with existing core snapshot system.

This service extends the existing core snapshot system to capture snapshots
when selector failures occur, using the established SnapshotManager and storage.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ...core.snapshot import (
    SnapshotManager, 
    SnapshotContext, 
    SnapshotConfig, 
    SnapshotMode,
    get_snapshot_manager
)
from ...core.snapshot.triggers import SelectorFailureTrigger
from ...storage.adapter import FileSystemStorageAdapter


class FailureSnapshotService:
    """
    Service for capturing snapshots at failure time using existing core snapshot system.
    
    This service integrates with:
    - Core SnapshotManager for capture operations
    - Existing FileSystemStorageAdapter for storage
    - SelectorFailureTrigger for automatic capture
    """
    
    def __init__(self):
        """Initialize using existing snapshot manager."""
        self.snapshot_manager = get_snapshot_manager()
        self.storage_adapter = FileSystemStorageAdapter()
    
    async def capture_on_failure(
        self,
        selector_name: str,
        site: str,
        page: Any,
        failure_context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Capture snapshot when selector fails using existing core snapshot system.
        
        Args:
            selector_name: Name of the failed selector
            site: Website/domain
            page: Playwright page object
            failure_context: Additional failure context
            session_id: Session identifier
            
        Returns:
            Snapshot bundle ID if successful, None otherwise
        """
        try:
            # Create context using existing core snapshot model
            context = SnapshotContext(
                site=site,
                module="selectors",
                component="adaptive",
                session_id=session_id or f"failure_{datetime.utcnow().timestamp()}"
            )
            
            # Create config for selector-focused capture
            config = SnapshotConfig(
                mode=SnapshotMode.SELECTOR,
                capture_html=True,
                capture_screenshot=True,
                selector=selector_name,
                metadata={
                    "failure_context": failure_context,
                    "capture_reason": "selector_failure",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Use existing SnapshotManager to capture
            bundle = await self.snapshot_manager.capture_snapshot(page, context, config)
            
            if bundle:
                # Store using existing storage adapter
                await self.storage_adapter.store_snapshot(bundle.dom_snapshot)
                return bundle.bundle_id
            
            return None
            
        except Exception as e:
            # Log error but don't fail the failure detection
            import logging
            logging.getLogger(__name__).error(
                f"Failed to capture snapshot for selector {selector_name}: {e}"
            )
            return None
    
    def setup_failure_trigger(self) -> SelectorFailureTrigger:
        """
        Set up automatic failure trigger using existing core snapshot system.
        
        Returns:
            Configured SelectorFailureTrigger
        """
        # Use existing SelectorFailureTrigger from core system
        trigger = SelectorFailureTrigger(
            snapshot_manager=self.snapshot_manager,
            capture_config=SnapshotConfig(
                mode=SnapshotMode.SELECTOR,
                capture_html=True,
                capture_screenshot=True
            )
        )
        
        return trigger
    
    async def get_failure_snapshot(self, snapshot_id: str) -> Optional[Any]:
        """
        Retrieve snapshot by ID using existing storage adapter.
        
        Args:
            snapshot_id: Snapshot bundle ID
            
        Returns:
            DOMSnapshot if found, None otherwise
        """
        try:
            return await self.storage_adapter.retrieve_snapshot(snapshot_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            return None
    
    async def cleanup_old_snapshots(self, days_old: int = 30) -> int:
        """
        Clean up old snapshots using existing storage adapter.
        
        Args:
            days_old: Number of days to keep snapshots
            
        Returns:
            Number of snapshots deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            return await self.storage_adapter.cleanup_old_snapshots(cutoff_date)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to cleanup old snapshots: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics from existing storage adapter.
        
        Returns:
            Storage statistics dictionary
        """
        try:
            # This would need to be implemented in the storage adapter
            # For now, return basic info
            return {
                "storage_type": "filesystem",
                "adapter": "FileSystemStorageAdapter",
                "integration": "core_snapshot_system"
            }
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to get storage stats: {e}")
            return {}
