"""
Storage extension for adaptive selector system.

This module extends the existing storage adapter to add adaptive-specific
functionality while preserving all existing behavior.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from ....storage.adapter import FileSystemStorageAdapter, IStorageAdapter
from ....models.selector_models import DOMSnapshot


class AdaptiveStorageExtension(IStorageAdapter):
    """
    Extension to existing FileSystemStorageAdapter for adaptive needs.
    
    This class wraps the existing storage adapter and adds adaptive-specific
    methods without changing the core storage behavior.
    """
    
    def __init__(self, base_adapter: Optional[FileSystemStorageAdapter] = None):
        """
        Initialize with existing storage adapter.
        
        Args:
            base_adapter: Existing storage adapter to extend
        """
        self.base_adapter = base_adapter or FileSystemStorageAdapter()
    
    # Delegate all existing interface methods to base adapter
    async def store_snapshot(self, snapshot: DOMSnapshot, screenshot: bytes = None) -> str:
        """Delegate to base adapter."""
        return await self.base_adapter.store_snapshot(snapshot, screenshot)
    
    async def retrieve_snapshot(self, snapshot_id: str) -> Optional[DOMSnapshot]:
        """Delegate to base adapter."""
        return await self.base_adapter.retrieve_snapshot(snapshot_id)
    
    async def store_metrics(self, metrics) -> bool:
        """Delegate to base adapter."""
        return await self.base_adapter.store_metrics(metrics)
    
    async def retrieve_metrics(self, selector_name: str,
                              time_range: tuple) -> List:
        """Delegate to base adapter."""
        return await self.base_adapter.retrieve_metrics(selector_name, time_range)
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delegate to base adapter."""
        return await self.base_adapter.delete_snapshot(snapshot_id)
    
    async def list_snapshots(self, selector_name: Optional[str] = None,
                           snapshot_type=None,
                           limit: Optional[int] = None) -> List[str]:
        """Delegate to base adapter."""
        return await self.base_adapter.list_snapshots(selector_name, snapshot_type, limit)
    
    async def cleanup_old_snapshots(self, older_than: datetime) -> int:
        """Delegate to base adapter."""
        return await self.base_adapter.cleanup_old_snapshots(older_than)
    
    # New adaptive-specific methods
    async def get_snapshots_by_failure_id(self, failure_id: str) -> List[DOMSnapshot]:
        """
        Get snapshots associated with a specific failure ID.
        
        Args:
            failure_id: Failure event identifier
            
        Returns:
            List of snapshots for the failure
        """
        # Use existing list_snapshots with failure_id filter
        all_snapshots = await self.list_snapshots()
        failure_snapshots = []
        
        for snapshot_id in all_snapshots:
            snapshot = await self.retrieve_snapshot(snapshot_id)
            if snapshot and hasattr(snapshot, 'metadata'):
                if snapshot.metadata.get('failure_id') == failure_id:
                    failure_snapshots.append(snapshot)
        
        return failure_snapshots
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics for adaptive system.
        
        Returns:
            Storage statistics dictionary
        """
        try:
            all_snapshots = await self.list_snapshots()
            
            # Calculate basic stats
            total_snapshots = len(all_snapshots)
            failure_snapshots = 0
            
            for snapshot_id in all_snapshots:
                snapshot = await self.retrieve_snapshot(snapshot_id)
                if snapshot and hasattr(snapshot, 'metadata'):
                    if snapshot.metadata.get('capture_reason') == 'selector_failure':
                        failure_snapshots += 1
            
            return {
                "total_snapshots": total_snapshots,
                "failure_snapshots": failure_snapshots,
                "storage_type": "filesystem",
                "adapter": "AdaptiveStorageExtension",
                "base_adapter": type(self.base_adapter).__name__
            }
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}
    
    async def cleanup_by_retention_policy(
        self, 
        retention_days: int = 30,
        max_snapshots: int = 1000
    ) -> Dict[str, int]:
        """
        Clean up snapshots based on retention policy.
        
        Args:
            retention_days: Days to keep snapshots
            max_snapshots: Maximum number of snapshots to keep
            
        Returns:
            Dictionary with cleanup results
        """
        try:
            # Clean up old snapshots
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            deleted_old = await self.cleanup_old_snapshots(cutoff_date)
            
            # Clean up excess snapshots (keep most recent)
            all_snapshots = await self.list_snapshots()
            deleted_excess = 0
            
            if len(all_snapshots) > max_snapshots:
                # Sort by creation time (newest first) and keep only max_snapshots
                snapshots_to_delete = all_snapshots[max_snapshots:]
                
                for snapshot_id in snapshots_to_delete:
                    if await self.delete_snapshot(snapshot_id):
                        deleted_excess += 1
            
            return {
                "deleted_old": deleted_old,
                "deleted_excess": deleted_excess,
                "total_deleted": deleted_old + deleted_excess
            }
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to run retention cleanup: {e}")
            return {"deleted_old": 0, "deleted_excess": 0, "total_deleted": 0}


def get_adaptive_storage() -> AdaptiveStorageExtension:
    """
    Get adaptive storage extension instance.
    
    Returns:
        AdaptiveStorageExtension instance
    """
    return AdaptiveStorageExtension()
