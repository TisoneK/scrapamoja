"""
Storage adapter interface and implementations for Selector Engine.

Provides abstract storage interface with concrete implementations for
different storage backends as required by the modular architecture.
"""

import asyncio
import gzip
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import asdict

from src.models.selector_models import (
    DOMSnapshot, ConfidenceMetrics, SnapshotType, SnapshotMetadata
)
from src.observability.logger import get_logger
from src.utils.exceptions import StorageError


class IStorageAdapter(ABC):
    """Interface for storage operations."""
    
    @abstractmethod
    async def store_snapshot(self, snapshot: DOMSnapshot) -> str:
        """Store DOM snapshot."""
        pass
    
    @abstractmethod
    async def retrieve_snapshot(self, snapshot_id: str) -> Optional[DOMSnapshot]:
        """Retrieve DOM snapshot."""
        pass
    
    @abstractmethod
    async def store_metrics(self, metrics: ConfidenceMetrics) -> bool:
        """Store performance metrics."""
        pass
    
    @abstractmethod
    async def retrieve_metrics(self, selector_name: str,
                              time_range: Tuple[datetime, datetime]) -> List[ConfidenceMetrics]:
        """Retrieve performance metrics."""
        pass
    
    @abstractmethod
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete DOM snapshot."""
        pass
    
    @abstractmethod
    async def list_snapshots(self, selector_name: Optional[str] = None,
                           snapshot_type: Optional[SnapshotType] = None,
                           limit: Optional[int] = None) -> List[str]:
        """List snapshot IDs."""
        pass
    
    @abstractmethod
    async def cleanup_old_snapshots(self, older_than: datetime) -> int:
        """Clean up old snapshots."""
        pass


class FileSystemStorageAdapter(IStorageAdapter):
    """File system-based storage adapter."""
    
    def __init__(self, base_path: str = "data/storage", compression: bool = True):
        self.base_path = Path(base_path)
        self.compression = compression
        self._logger = get_logger("file_storage")
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.base_path / "snapshots").mkdir(exist_ok=True)
        (self.base_path / "metrics").mkdir(exist_ok=True)
        (self.base_path / "indexes").mkdir(exist_ok=True)
    
    async def store_snapshot(self, snapshot: DOMSnapshot) -> str:
        """Store DOM snapshot to file system."""
        try:
            # Create file path
            file_name = f"{snapshot.id}.json{'gz' if self.compression else ''}"
            file_path = self.base_path / "snapshots" / file_name
            
            # Prepare snapshot data
            snapshot_data = {
                "id": snapshot.id,
                "selector_name": snapshot.selector_name,
                "snapshot_type": snapshot.snapshot_type.value,
                "dom_content": snapshot.dom_content,
                "metadata": asdict(snapshot.metadata),
                "file_path": str(file_path),
                "created_at": snapshot.created_at.isoformat(),
                "file_size": snapshot.file_size
            }
            
            # Compress if enabled
            if self.compression:
                content = gzip.compress(json.dumps(snapshot_data).encode('utf-8'))
            else:
                content = json.dumps(snapshot_data, indent=2).encode('utf-8')
            
            # Write to file
            file_path.write_bytes(content)
            
            # Update index
            await self._update_snapshot_index(snapshot)
            
            self._logger.debug(
                "snapshot_stored",
                snapshot_id=snapshot.id,
                file_path=str(file_path),
                file_size=len(content)
            )
            
            return snapshot.id
            
        except Exception as e:
            raise StorageError(
                "store", "snapshot", snapshot.id, str(e)
            )
    
    async def retrieve_snapshot(self, snapshot_id: str) -> Optional[DOMSnapshot]:
        """Retrieve DOM snapshot from file system."""
        try:
            # Try compressed version first
            file_path = self.base_path / "snapshots" / f"{snapshot_id}.json.gz"
            if not file_path.exists():
                # Try uncompressed version
                file_path = self.base_path / "snapshots" / f"{snapshot_id}.json"
                if not file_path.exists():
                    return None
            
            # Read file content
            content = file_path.read_bytes()
            
            # Decompress if needed
            if file_path.suffix == '.gz':
                content = gzip.decompress(content).decode('utf-8')
            else:
                content = content.decode('utf-8')
            
            # Parse JSON
            data = json.loads(content)
            
            # Reconstruct metadata
            metadata = SnapshotMetadata(**data["metadata"])
            
            # Reconstruct snapshot
            snapshot = DOMSnapshot(
                id=data["id"],
                selector_name=data["selector_name"],
                snapshot_type=SnapshotType(data["snapshot_type"]),
                dom_content=data["dom_content"],
                metadata=metadata,
                file_path=data["file_path"],
                created_at=datetime.fromisoformat(data["created_at"]),
                file_size=data["file_size"]
            )
            
            self._logger.debug(
                "snapshot_retrieved",
                snapshot_id=snapshot_id,
                file_path=str(file_path)
            )
            
            return snapshot
            
        except Exception as e:
            self._logger.error(
                "snapshot_retrieval_failed",
                snapshot_id=snapshot_id,
                error=str(e)
            )
            raise StorageError(
                "retrieve", "snapshot", snapshot_id, str(e)
            )
    
    async def store_metrics(self, metrics: ConfidenceMetrics) -> bool:
        """Store performance metrics to file system."""
        try:
            # Create file path
            date_str = metrics.updated_at.strftime("%Y-%m-%d")
            file_path = self.base_path / "metrics" / f"{metrics.selector_name}_{date_str}.json"
            
            # Load existing metrics for the day
            existing_metrics = []
            if file_path.exists():
                try:
                    content = file_path.read_text()
                    existing_data = json.loads(content)
                    existing_metrics = existing_data.get("metrics", [])
                except Exception:
                    existing_metrics = []
            
            # Convert metrics to dict
            metrics_dict = asdict(metrics)
            metrics_dict["updated_at"] = metrics.updated_at.isoformat()
            metrics_dict["last_success"] = metrics.last_success.isoformat() if metrics.last_success else None
            metrics_dict["last_failure"] = metrics.last_failure.isoformat() if metrics.last_failure else None
            
            # Add new metrics
            existing_metrics.append(metrics_dict)
            
            # Keep only recent metrics (last 1000 per day)
            if len(existing_metrics) > 1000:
                existing_metrics = existing_metrics[-1000:]
            
            # Save to file
            data = {
                "selector_name": metrics.selector_name,
                "date": date_str,
                "metrics": existing_metrics
            }
            
            file_path.write_text(json.dumps(data, indent=2))
            
            self._logger.debug(
                "metrics_stored",
                selector_name=metrics.selector_name,
                file_path=str(file_path)
            )
            
            return True
            
        except Exception as e:
            raise StorageError(
                "store", "metrics", metrics.selector_name, str(e)
            )
    
    async def retrieve_metrics(self, selector_name: str,
                              time_range: Tuple[datetime, datetime]) -> List[ConfidenceMetrics]:
        """Retrieve performance metrics from file system."""
        try:
            start_date, end_date = time_range
            current_date = start_date.date()
            end_date = end_date.date()
            
            all_metrics = []
            
            # Iterate through dates in range
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                file_path = self.base_path / "metrics" / f"{selector_name}_{date_str}.json"
                
                if file_path.exists():
                    try:
                        content = file_path.read_text()
                        data = json.loads(content)
                        
                        for metrics_dict in data.get("metrics", []):
                            # Parse datetime fields
                            metrics_dict["updated_at"] = datetime.fromisoformat(metrics_dict["updated_at"])
                            if metrics_dict["last_success"]:
                                metrics_dict["last_success"] = datetime.fromisoformat(metrics_dict["last_success"])
                            if metrics_dict["last_failure"]:
                                metrics_dict["last_failure"] = datetime.fromisoformat(metrics_dict["last_failure"])
                            
                            # Create ConfidenceMetrics object
                            metrics = ConfidenceMetrics(**metrics_dict)
                            
                            # Filter by time range
                            if start_date <= metrics.updated_at <= end_date:
                                all_metrics.append(metrics)
                                
                    except Exception as e:
                        self._logger.warning(
                            "metrics_file_parse_error",
                            file_path=str(file_path),
                            error=str(e)
                        )
                
                current_date += timedelta(days=1)
            
            # Sort by timestamp
            all_metrics.sort(key=lambda m: m.updated_at)
            
            self._logger.debug(
                "metrics_retrieved",
                selector_name=selector_name,
                count=len(all_metrics),
                time_range_start=start_date.isoformat(),
                time_range_end=end_date.isoformat()
            )
            
            return all_metrics
            
        except Exception as e:
            raise StorageError(
                "retrieve", "metrics", selector_name, str(e)
            )
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete DOM snapshot from file system."""
        try:
            deleted = False
            
            # Try compressed version
            file_path = self.base_path / "snapshots" / f"{snapshot_id}.json.gz"
            if file_path.exists():
                file_path.unlink()
                deleted = True
            else:
                # Try uncompressed version
                file_path = self.base_path / "snapshots" / f"{snapshot_id}.json"
                if file_path.exists():
                    file_path.unlink()
                    deleted = True
            
            if deleted:
                # Remove from index
                await self._remove_from_snapshot_index(snapshot_id)
                
                self._logger.debug(
                    "snapshot_deleted",
                    snapshot_id=snapshot_id
                )
            
            return deleted
            
        except Exception as e:
            raise StorageError(
                "delete", "snapshot", snapshot_id, str(e)
            )
    
    async def list_snapshots(self, selector_name: Optional[str] = None,
                           snapshot_type: Optional[SnapshotType] = None,
                           limit: Optional[int] = None) -> List[str]:
        """List snapshot IDs."""
        try:
            # Load index
            index = await self._load_snapshot_index()
            
            # Filter results
            filtered_ids = []
            for snapshot_id, metadata in index.items():
                if selector_name and metadata.get("selector_name") != selector_name:
                    continue
                if snapshot_type and metadata.get("snapshot_type") != snapshot_type.value:
                    continue
                filtered_ids.append(snapshot_id)
            
            # Sort by creation time (newest first)
            filtered_ids.sort(key=lambda sid: index[sid].get("created_at", ""), reverse=True)
            
            # Apply limit
            if limit:
                filtered_ids = filtered_ids[:limit]
            
            return filtered_ids
            
        except Exception as e:
            raise StorageError(
                "list", "snapshots", "all", str(e)
            )
    
    async def cleanup_old_snapshots(self, older_than: datetime) -> int:
        """Clean up old snapshots."""
        try:
            # Get all snapshots
            all_snapshot_ids = await self.list_snapshots()
            
            deleted_count = 0
            for snapshot_id in all_snapshot_ids:
                # Get snapshot metadata
                index = await self._load_snapshot_index()
                metadata = index.get(snapshot_id, {})
                
                if "created_at" in metadata:
                    created_at = datetime.fromisoformat(metadata["created_at"])
                    if created_at < older_than:
                        if await self.delete_snapshot(snapshot_id):
                            deleted_count += 1
            
            self._logger.info(
                "snapshots_cleanup_completed",
                deleted_count=deleted_count,
                cutoff_date=older_than.isoformat()
            )
            
            return deleted_count
            
        except Exception as e:
            raise StorageError(
                "cleanup", "snapshots", "all", str(e)
            )
    
    async def _update_snapshot_index(self, snapshot: DOMSnapshot) -> None:
        """Update snapshot index."""
        try:
            index_file = self.base_path / "indexes" / "snapshots.json"
            
            # Load existing index
            index = {}
            if index_file.exists():
                try:
                    content = index_file.read_text()
                    index = json.loads(content)
                except Exception:
                    index = {}
            
            # Add/update entry
            index[snapshot.id] = {
                "selector_name": snapshot.selector_name,
                "snapshot_type": snapshot.snapshot_type.value,
                "created_at": snapshot.created_at.isoformat(),
                "file_size": snapshot.file_size,
                "file_path": snapshot.file_path
            }
            
            # Save index
            index_file.write_text(json.dumps(index, indent=2))
            
        except Exception as e:
            self._logger.warning(
                "snapshot_index_update_failed",
                snapshot_id=snapshot.id,
                error=str(e)
            )
    
    async def _remove_from_snapshot_index(self, snapshot_id: str) -> None:
        """Remove snapshot from index."""
        try:
            index_file = self.base_path / "indexes" / "snapshots.json"
            
            if not index_file.exists():
                return
            
            # Load existing index
            content = index_file.read_text()
            index = json.loads(content)
            
            # Remove entry
            if snapshot_id in index:
                del index[snapshot_id]
                
                # Save updated index
                index_file.write_text(json.dumps(index, indent=2))
            
        except Exception as e:
            self._logger.warning(
                "snapshot_index_removal_failed",
                snapshot_id=snapshot_id,
                error=str(e)
            )
    
    async def _load_snapshot_index(self) -> Dict[str, Dict[str, Any]]:
        """Load snapshot index."""
        try:
            index_file = self.base_path / "indexes" / "snapshots.json"
            
            if not index_file.exists():
                return {}
            
            content = index_file.read_text()
            return json.loads(content)
            
        except Exception as e:
            self._logger.warning(
                "snapshot_index_load_failed",
                error=str(e)
            )
            return {}


class MemoryStorageAdapter(IStorageAdapter):
    """In-memory storage adapter for testing and temporary storage."""
    
    def __init__(self, max_snapshots: int = 1000, max_metrics_per_selector: int = 1000):
        self.max_snapshots = max_snapshots
        self.max_metrics_per_selector = max_metrics_per_selector
        self._snapshots: Dict[str, DOMSnapshot] = {}
        self._metrics: Dict[str, List[ConfidenceMetrics]] = defaultdict(list)
        self._logger = get_logger("memory_storage")
    
    async def store_snapshot(self, snapshot: DOMSnapshot) -> str:
        """Store DOM snapshot in memory."""
        try:
            # Check capacity
            if len(self._snapshots) >= self.max_snapshots:
                # Remove oldest snapshot
                oldest_id = min(self._snapshots.keys(), 
                             key=lambda k: self._snapshots[k].created_at)
                del self._snapshots[oldest_id]
            
            self._snapshots[snapshot.id] = snapshot
            
            self._logger.debug(
                "snapshot_stored_memory",
                snapshot_id=snapshot.id,
                total_snapshots=len(self._snapshots)
            )
            
            return snapshot.id
            
        except Exception as e:
            raise StorageError(
                "store", "snapshot", snapshot.id, str(e)
            )
    
    async def retrieve_snapshot(self, snapshot_id: str) -> Optional[DOMSnapshot]:
        """Retrieve DOM snapshot from memory."""
        return self._snapshots.get(snapshot_id)
    
    async def store_metrics(self, metrics: ConfidenceMetrics) -> bool:
        """Store performance metrics in memory."""
        try:
            selector_metrics = self._metrics[metrics.selector_name]
            
            # Check capacity
            if len(selector_metrics) >= self.max_metrics_per_selector:
                # Remove oldest metrics
                selector_metrics.sort(key=lambda m: m.updated_at)
                selector_metrics.pop(0)
            
            selector_metrics.append(metrics)
            
            self._logger.debug(
                "metrics_stored_memory",
                selector_name=metrics.selector_name,
                total_metrics=len(selector_metrics)
            )
            
            return True
            
        except Exception as e:
            raise StorageError(
                "store", "metrics", metrics.selector_name, str(e)
            )
    
    async def retrieve_metrics(self, selector_name: str,
                              time_range: Tuple[datetime, datetime]) -> List[ConfidenceMetrics]:
        """Retrieve performance metrics from memory."""
        start_time, end_time = time_range
        
        return [
            metrics for metrics in self._metrics[selector_name]
            if start_time <= metrics.updated_at <= end_time
        ]
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete DOM snapshot from memory."""
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            return True
        return False
    
    async def list_snapshots(self, selector_name: Optional[str] = None,
                           snapshot_type: Optional[SnapshotType] = None,
                           limit: Optional[int] = None) -> List[str]:
        """List snapshot IDs in memory."""
        snapshot_ids = []
        
        for snapshot_id, snapshot in self._snapshots.items():
            if selector_name and snapshot.selector_name != selector_name:
                continue
            if snapshot_type and snapshot.snapshot_type != snapshot_type:
                continue
            snapshot_ids.append(snapshot_id)
        
        # Sort by creation time (newest first)
        snapshot_ids.sort(key=lambda sid: self._snapshots[sid].created_at, reverse=True)
        
        if limit:
            snapshot_ids = snapshot_ids[:limit]
        
        return snapshot_ids
    
    async def cleanup_old_snapshots(self, older_than: datetime) -> int:
        """Clean up old snapshots from memory."""
        old_ids = [
            snapshot_id for snapshot_id, snapshot in self._snapshots.items()
            if snapshot.created_at < older_than
        ]
        
        for snapshot_id in old_ids:
            del self._snapshots[snapshot_id]
        
        self._logger.info(
            "memory_snapshots_cleanup_completed",
            deleted_count=len(old_ids),
            cutoff_date=older_than.isoformat()
        )
        
        return len(old_ids)


# Storage adapter factory

def create_storage_adapter(adapter_type: str = "filesystem", **kwargs) -> IStorageAdapter:
    """Create storage adapter instance."""
    if adapter_type == "filesystem":
        return FileSystemStorageAdapter(**kwargs)
    elif adapter_type == "memory":
        return MemoryStorageAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown storage adapter type: {adapter_type}")


# Global storage adapter instance
_storage_adapter: Optional[IStorageAdapter] = None


def get_storage_adapter() -> IStorageAdapter:
    """Get global storage adapter instance."""
    global _storage_adapter
    if _storage_adapter is None:
        _storage_adapter = create_storage_adapter("filesystem")
    return _storage_adapter


def set_storage_adapter(adapter: IStorageAdapter) -> None:
    """Set global storage adapter instance."""
    global _storage_adapter
    _storage_adapter = adapter
