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
from ..core.snapshot.storage import SnapshotStorage
from ..core.snapshot.models import SnapshotBundle, SnapshotContext, SnapshotConfig, SnapshotMode, EnumEncoder

# Module logger
logger = get_logger("storage_adapter")


class IStorageAdapter(ABC):
    """Interface for storage operations."""
    
    @abstractmethod
    async def store_snapshot(self, snapshot: DOMSnapshot, screenshot: bytes = None) -> str:
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
    """File system-based storage adapter using core snapshot system."""
    
    def __init__(self, base_path: str = None, compression: bool = True):
        # Use core snapshot storage with base path
        self.base_path = Path(base_path or "data/snapshots")
        self.snapshot_storage = SnapshotStorage(base_path or "data/snapshots")
        self.compression = False  # Set to False to match expected .json file extension
        self._logger = get_logger("file_storage")
        
        # Don't create duplicate directories - let core snapshot system handle it
        # self.snapshot_storage.base_path.mkdir(parents=True, exist_ok=True)
        
        # Don't create duplicate subdirectories - core snapshot system handles this
        # (self.snapshot_storage.base_path / "metrics").mkdir(exist_ok=True)
        # (self.snapshot_storage.base_path / "indexes").mkdir(exist_ok=True)
    
    def _get_hierarchical_path(self, snapshot: DOMSnapshot) -> Path:
        """Generate hierarchical path based on selector_name and timestamp.
        
        Structure: {site}/{module}/{component}/{YYYYMMDD}/{HHMMSS}_{session_id}/
        """
        # Parse selector_name to get module and component
        # e.g., "navigation.sport_selection.basketball_link" -> module="navigation", component="sport_selection.basketball_link"
        selector_parts = snapshot.selector_name.split(".")
        
        # Default to "unknown" if parsing fails
        if len(selector_parts) >= 2:
            module = selector_parts[0]
            component = ".".join(selector_parts[1:])
        else:
            module = "default"
            component = snapshot.selector_name
        
        # Get site from metadata or default
        site = "flashscore"  # Could be extracted from page_url in metadata
        
        # Generate timestamp-based path
        timestamp = snapshot.created_at
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        
        # Extract session_id from snapshot id (last part after last underscore)
        snapshot_id_parts = snapshot.id.split("_")
        session_id = snapshot_id_parts[-1] if snapshot_id_parts else "unknown"
        
        # Build hierarchical path
        hierarchical_path = (
            self.base_path / "snapshots" /
            site / module / component /
            f"{date_str}" /
            f"{time_str}_{session_id}"
        )
        
        return hierarchical_path
    
    async def store_snapshot(self, snapshot: DOMSnapshot, screenshot: bytes = None) -> str:
        """Store DOM snapshot using core snapshot system."""
        try:
            # Convert DOMSnapshot to SnapshotContext
            context = SnapshotContext(
                site="flashscore",  # Could be extracted from URL or metadata
                module="selector_engine",
                component="snapshot_storage",
                session_id=snapshot.id or f"snapshot_{datetime.now().strftime('%H%M%S')}",  # Use snapshot ID or timestamp
                function="store_snapshot",
                additional_metadata={
                    "original_selector": snapshot.selector_name,
                    "snapshot_type": snapshot.snapshot_type.value,
                    "file_size": snapshot.file_size
                }
            )
            
            # Create SnapshotConfig for full page capture
            config = SnapshotConfig(
                mode=SnapshotMode.FULL_PAGE,
                capture_html=True,
                capture_screenshot=bool(screenshot),
                capture_console=False,
                capture_network=False,
                async_save=True,  # Enable async save
                deduplication_enabled=True
            )
            
            # Generate proper bundle path using core snapshot system
            timestamp = datetime.now()
            bundle_path = self.snapshot_storage.get_bundle_path(context, timestamp)
            
            # Create SnapshotBundle with actual artifacts
            artifacts = []
            
            # Create bundle directory and subdirectories first
            bundle_path.mkdir(parents=True, exist_ok=True)
            (bundle_path / "html").mkdir(exist_ok=True)
            (bundle_path / "screenshots").mkdir(exist_ok=True)
            (bundle_path / "logs").mkdir(exist_ok=True)
            
            # Capture HTML content
            if snapshot.dom_content:
                logger.debug("Creating HTML artifact for snapshot", extra={"snapshot_id": snapshot.id})
                html_filename = f"fullpage_{snapshot.id[:8]}.html"
                html_path = bundle_path / "html" / html_filename
                
                logger.debug("HTML path resolved", extra={"html_path": str(html_path), "dom_content_length": len(snapshot.dom_content) if snapshot.dom_content else 0})
                
                # Write HTML content
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(snapshot.dom_content)
                
                logger.debug("HTML file written", extra={"html_path": str(html_path), "exists": html_path.exists()})
                artifacts.append(f"html/{html_filename}")
            else:
                logger.debug("No DOM content found in snapshot", extra={"snapshot_id": snapshot.id})
            
            # Capture screenshot if provided
            if screenshot:
                screenshots_dir = bundle_path / "screenshots"
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                screenshot_filename = f"viewport_{datetime.now().strftime('%H%M%S')}.png"
                screenshot_path = screenshots_dir / screenshot_filename
                
                # Write screenshot content
                with open(screenshot_path, 'wb') as f:
                    f.write(screenshot)
                artifacts.append(f"screenshots/{screenshot_filename}")
            
            bundle = SnapshotBundle(
                context=context,
                config=config,
                timestamp=timestamp,
                bundle_path=str(bundle_path),  # Use proper path from snapshot storage
                artifacts=artifacts,  # Add actual captured artifacts
            )
            
            # Store bundle using core snapshot storage
            await self.snapshot_storage.save_bundle(bundle)
            
            # Update snapshot with bundle path
            snapshot.file_path = str(bundle.bundle_path)
            
            self._logger.debug(
                "snapshot_stored",
                snapshot_id=snapshot.id,
                bundle_path=str(bundle.bundle_path),
                file_size=snapshot.file_size,
                has_screenshot=bool(screenshot)
            )
            
            return snapshot.id
            
        except Exception as e:
            self._logger.error(
                "snapshot_storage_failed",
                snapshot_id=snapshot.id,
                error=str(e)
            )
            raise StorageError(
                "store", "snapshot", snapshot.id, str(e)
            )
    
    async def retrieve_snapshot(self, snapshot_id: str) -> Optional[DOMSnapshot]:
        """Retrieve DOM snapshot from core snapshot system."""
        try:
            # Try to load bundle from core storage
            bundle = await self.snapshot_storage.load_bundle(snapshot_id)
            
            if not bundle:
                self._logger.warning(
                    "snapshot_not_found",
                    snapshot_id=snapshot_id
                )
                return None
            
            # Convert SnapshotBundle back to DOMSnapshot
            snapshot = DOMSnapshot(
                id=bundle.content_hash[:8] if bundle.content_hash else snapshot_id,
                selector_name=bundle.context.selector_name,
                snapshot_type=bundle.config.mode.value if bundle.config else SnapshotType.MANUAL,
                dom_content=bundle.html_content,
                metadata=SnapshotMetadata(**bundle.metadata),
                file_path=bundle.bundle_path,
                created_at=bundle.context.timestamp,
                file_size=bundle.content_size if hasattr(bundle, 'content_size') else 0
            )
            
            self._logger.debug(
                "snapshot_retrieved",
                snapshot_id=snapshot_id,
                file_path=snapshot.file_path
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
            
            file_path.write_text(json.dumps(data, indent=2, cls=EnumEncoder))
            
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
        """Delete DOM snapshot using core snapshot system."""
        try:
            # Delete snapshot bundle from core storage
            success = await self.snapshot_storage.delete_bundle(snapshot_id)
            
            if success:
                # Remove from index
                index = await self._load_snapshot_index()
                if snapshot_id in index:
                    del index[snapshot_id]
                
                # Save updated index
                await self._update_snapshot_index(None)
                
                self._logger.info(
                    "snapshot_deleted",
                    snapshot_id=snapshot_id
                )
            
            return success
            
        except Exception as e:
            self._logger.error(
                "snapshot_deletion_failed",
                snapshot_id=snapshot_id,
                error=str(e)
            )
            raise StorageError(
                "delete", "snapshot", snapshot_id, str(e)
            )

    async def list_snapshots(self, selector_name: Optional[str] = None,
                           snapshot_type: Optional[SnapshotType] = None,
                           limit: Optional[int] = None) -> List[str]:
        """List snapshot IDs using core snapshot system."""
        try:
            # Get snapshot IDs from core storage index
            snapshot_ids = await self.snapshot_storage.list_snapshots()
            
            # Filter results if criteria provided
            if selector_name:
                snapshot_ids = [sid for sid in snapshot_ids 
                              if self._matches_selector_name(sid, selector_name)]
            
            if snapshot_type:
                snapshot_ids = [sid for sid in snapshot_ids 
                              if self._matches_snapshot_type(sid, snapshot_type)]
            
            # Apply limit
            if limit:
                snapshot_ids = snapshot_ids[:limit]
            
            self._logger.debug(
                "snapshots_listed",
                count=len(snapshot_ids),
                selector_name=selector_name,
                snapshot_type=snapshot_type,
                limit=limit
            )
            
            return snapshot_ids
            
        except Exception as e:
            self._logger.error(
                "snapshot_list_failed",
                error=str(e)
            )
            raise StorageError(
                "list", "snapshots", "all", str(e)
            )
    
    async def list_files(self, pattern: str = "*") -> List[str]:
        """List files matching pattern in storage directory."""
        try:
            storage_path = self.base_path
            if not storage_path.exists():
                return []
            
            files = []
            for file_path in storage_path.glob(pattern):
                if file_path.is_file():
                    files.append(str(file_path.relative_to(storage_path)))
            return files
            
        except Exception as e:
            self._logger.error(
                "list_files_failed",
                pattern=pattern,
                error=str(e)
            )
            raise StorageError(
                "list", "files", pattern, str(e)
            )

    async def store(self, key: str, value: Any) -> None:
        """Store data with given key using JSON serialization."""
        try:
            # Handle keys that already have .json extension
            if key.endswith('.json'):
                file_path = self.base_path / key
            else:
                file_path = self.base_path / f"{key}.json"
            
            # Special handling for browser sessions - put them in hierarchical structure
            if key.startswith('browser_sessions/'):
                # Check if this is a site-specific browser session (e.g., "flashscore/browser_sessions/")
                if '/' in key[:-5]:  # Has site prefix
                    # Already in correct format: site/browser_sessions/session_id.json
                    file_path = self.base_path / key
                else:
                    # Legacy format - use hierarchical structure
                    session_id = key.split('/')[-1].replace('.json', '')
                    timestamp = datetime.now()
                    
                    # Create context for browser session
                    context = SnapshotContext(
                        site='browser_sessions',
                        module='session_management',
                        component='browser_session',
                        session_id=session_id
                    )
                    
                    # Use hierarchical path generation
                    hierarchical_dir = Path(self.snapshot_storage.base_path) / context.generate_hierarchical_path(timestamp)
                    hierarchical_dir.mkdir(parents=True, exist_ok=True)
                    file_path = hierarchical_dir / f"{session_id}.json"
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(value, f, indent=2, cls=EnumEncoder)
            
            self._logger.info(
                "data_stored",
                key=key,
                file_path=str(file_path)
            )
            
        except Exception as e:
            self._logger.error(
                "store_failed",
                key=key,
                error=str(e)
            )
            raise StorageError("store", "data", key, str(e))

    async def delete(self, key: str) -> None:
        """Delete data file for given key."""
        try:
            # Handle keys that already have .json extension
            if key.endswith('.json'):
                file_path = self.base_path / key
            else:
                file_path = self.base_path / f"{key}.json"
                
            # Special handling for browser sessions - check for site-specific paths
            if key.startswith('browser_sessions/') and '/' in key[:-5]:
                # Site-specific browser session - check hierarchical location
                site = key.split('/')[0]
                session_id = key.split('/')[-1].replace('.json', '')
                timestamp = datetime.now()
                
                # Create context to find hierarchical path
                context = SnapshotContext(
                    site=site,
                    module='session_management',
                    component='browser_session',
                    session_id=session_id
                )
                
                # Check both old and new locations
                hierarchical_path = Path(self.snapshot_storage.base_path) / context.generate_hierarchical_path(timestamp)
                old_path = self.base_path / key
                
                # Delete from both locations if they exist
                deleted_files = []
                if old_path.exists():
                    old_path.unlink()
                    deleted_files.append(str(old_path))
                if hierarchical_path.exists():
                    for json_file in hierarchical_path.glob("*.json"):
                        json_file.unlink()
                        deleted_files.append(str(json_file))
                        
                # Log deletion from hierarchical path (preferred location)
                if deleted_files:
                    self._logger.info(
                        "data_deleted",
                        key=key,
                        file_path=str(hierarchical_path),
                        deleted_files=deleted_files
                    )
                    return
                    
            if file_path.exists():
                file_path.unlink()
                
                self._logger.info(
                    "data_deleted",
                    key=key,
                    file_path=str(file_path)
                )
            else:
                self._logger.debug(
                    "data_not_found",
                    key=key
                )
                
        except Exception as e:
            self._logger.error(
                "delete_failed",
                key=key,
                error=str(e)
            )
            raise StorageError("delete", "data", key, str(e))
    
    async def cleanup_old_snapshots(self, older_than: datetime) -> int:
        """Clean up old snapshots using core snapshot system."""
        try:
            # Get all snapshot IDs from core storage
            snapshot_ids = await self.snapshot_storage.list_snapshots()
            
            deleted_count = 0
            
            for snapshot_id in snapshot_ids:
                # Get snapshot metadata to check creation time
                index = await self._load_snapshot_index()
                metadata = index.get(snapshot_id, {})
                
                if metadata:
                    created_at = datetime.fromisoformat(metadata.get("created_at", ""))
                    if created_at < older_than:
                        # Delete snapshot bundle
                        await self.snapshot_storage.delete_bundle(snapshot_id)
                        deleted_count += 1
                        
                        # Remove from index
                        if snapshot_id in index:
                            del index[snapshot_id]
            
            # Save updated index
            if deleted_count > 0:
                await self._update_snapshot_index(None)
            
            self._logger.info(
                "old_snapshots_cleaned",
                deleted_count=deleted_count,
                cutoff_date=older_than.isoformat()
            )
            
            return deleted_count
            
        except Exception as e:
            self._logger.error(
                "cleanup_failed",
                error=str(e)
            )
            raise StorageError(
                "cleanup", "snapshots", "all", str(e)
            )
    
    async def _update_snapshot_index(self, snapshot: DOMSnapshot) -> None:
        """Update snapshot index."""
        try:
            index_file = self.base_path / "indexes" / "snapshots.json"
            
            index = {}
            if index_file.exists():
                try:
                    content = index_file.read_text()
                    index = json.loads(content)
                except Exception:
                    index = {}
            else:
                index = {}
            if not index_file.exists():
                return
            
            # Load existing index
            content = index_file.read_text()
            index = json.loads(content)
            
            # Remove entry
            if snapshot_id in index:
                del index[snapshot_id]
                
                # Save updated index
                index_file.write_text(json.dumps(index, indent=2, cls=EnumEncoder))
            
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
    
    async def store_snapshot(self, snapshot: DOMSnapshot, screenshot: bytes = None) -> str:
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
                total_snapshots=len(self._snapshots),
                has_screenshot=bool(screenshot)
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
        # Use the new context-aware snapshot system directly
        _storage_adapter = create_storage_adapter("filesystem")
    return _storage_adapter


def set_storage_adapter(adapter: IStorageAdapter) -> None:
    """Set global storage adapter instance."""
    global _storage_adapter
    _storage_adapter = adapter
