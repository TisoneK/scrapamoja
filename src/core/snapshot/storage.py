"""
Storage layer for the snapshot system with hierarchical organization.

This module handles the physical storage of snapshot bundles with atomic operations,
partitioning, and content management.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from .models import SnapshotBundle, SnapshotContext, BundleCorruptionError, SnapshotError, EnumEncoder
from .exceptions import PartialSnapshotBundle


class SnapshotStorage:
    """Manages hierarchical storage of snapshot bundles."""
    
    def __init__(self, base_path: str = "data/snapshots"):
        """Initialize storage with base path."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Storage configuration
        self.max_files_per_directory = 1000
        self.max_directory_size_mb = 100
        
    def get_bundle_path(self, context: SnapshotContext, timestamp: datetime) -> Path:
        """Generate hierarchical bundle path based on context and timestamp."""
        hierarchical_path = context.generate_hierarchical_path(timestamp)
        return self.base_path / hierarchical_path
    
    async def create_bundle_directory(self, bundle_path: Path) -> bool:
        """Create bundle directory atomically."""
        
        try:
            # Use temporary directory for atomic creation
            temp_path = bundle_path.parent / f".tmp_{bundle_path.name}"
            
            # Create temporary directory
            temp_path.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            (temp_path / "html").mkdir(exist_ok=True)
            (temp_path / "screenshots").mkdir(exist_ok=True)
            (temp_path / "logs").mkdir(exist_ok=True)
            
            # Atomic rename
            temp_path.rename(bundle_path)
            
            return True
            
        except Exception as e:
            # Cleanup on failure
            if temp_path.exists():
                shutil.rmtree(temp_path, ignore_errors=True)
            raise SnapshotError(f"Failed to create bundle directory: {e}")
    
    async def save_bundle_metadata(self, bundle: SnapshotBundle) -> bool:
        """Save bundle metadata atomically."""
        try:
            bundle_path = Path(bundle.bundle_path)
            metadata_path = bundle_path / "metadata.json"
            
            print(f"🔍 DIAGNOSTIC: Attempting to save metadata to {metadata_path}")
            print(f"🔍 DIAGNOSTIC: Bundle data: {bundle.to_dict()}")
            
            # Save to temporary file first
            temp_path = metadata_path.with_suffix(".tmp")
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(bundle.to_dict(), f, indent=2, ensure_ascii=False, cls=EnumEncoder)
            
            # Atomic rename
            temp_path.rename(metadata_path)
            
            print(f"🔍 DIAGNOSTIC: Successfully saved metadata to {metadata_path}")
            return True
            
        except Exception as e:
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            print(f"🔍 DIAGNOSTIC: Failed to save metadata: {e}")
            raise SnapshotError(f"Failed to save bundle metadata: {e}")
    
    async def save_bundle(self, bundle: SnapshotBundle) -> bool:
        """Save complete bundle with all artifacts."""
        try:
            bundle_path = Path(bundle.bundle_path)
            
            # Create bundle directory first
            await self.create_bundle_directory(bundle_path)
            
            # Save metadata
            await self.save_bundle_metadata(bundle)
            
            # Save artifacts - artifacts can be strings (file paths) or objects with content
            for artifact in bundle.artifacts:
                # Handle both string paths and artifact objects
                if isinstance(artifact, str):
                    # Artifact is already a file path string, nothing to save
                    # The actual file was saved by the capture method
                    print(f"🔍 DIAGNOSTIC: Artifact path (saved by capture): {artifact}")
                    continue
                else:
                    # Artifact is an object with filename/content
                    artifact_path = bundle_path / artifact.filename
                    await self._save_artifact(artifact, artifact_path)
            
            return True
            
        except Exception as e:
            print(f"🔍 DIAGNOSTIC: save_bundle failed: {e}")
            raise SnapshotError(f"Failed to save bundle: {e}")
    
    async def save_partial_bundle(self, partial_bundle: PartialSnapshotBundle) -> bool:
        """Save partial snapshot when some artifacts failed."""
        try:
            bundle_path = Path(partial_bundle.bundle_path)
            
            # Save metadata
            await self.save_bundle_metadata(partial_bundle)
            
            # Save successful artifacts
            for artifact in partial_bundle.artifacts:
                artifact_path = bundle_path / artifact.filename
                await self._save_artifact(artifact, artifact_path)
            
            return True
            
        except Exception as e:
            raise SnapshotError(f"Failed to save partial bundle: {e}")
    
    async def _save_artifact(self, artifact: Any, artifact_path: Path) -> None:
        """Save individual artifact to file."""
        try:
            if hasattr(artifact, 'save_to_file'):
                await artifact.save_to_file(artifact_path)
            elif hasattr(artifact, 'content'):
                with open(artifact_path, 'w', encoding='utf-8') as f:
                    f.write(artifact.content)
            elif hasattr(artifact, 'raw_content'):
                with open(artifact_path, 'wb') as f:
                    f.write(artifact.raw_content)
            else:
                raise SnapshotError(f"Unknown artifact type: {type(artifact)}")
        except Exception as e:
            raise SnapshotError(f"Failed to save artifact: {e}")
    
    async def load_bundle(self, bundle_path: str) -> Optional[SnapshotBundle]:
        """Load bundle from storage with validation."""
        try:
            bundle_path = Path(bundle_path)
            metadata_path = bundle_path / "metadata.json"
            
            if not metadata_path.exists():
                return None
            
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create bundle
            bundle = SnapshotBundle.from_dict(data)
            
            # Validate bundle integrity
            if not bundle.validate():
                raise BundleCorruptionError(f"Bundle validation failed: {bundle_path}")
            
            return bundle
            
        except Exception as e:
            if isinstance(e, BundleCorruptionError):
                raise
            raise SnapshotError(f"Failed to load bundle: {e}")
    
    async def delete_bundle(self, bundle_path: str) -> bool:
        """Delete bundle directory atomically."""
        try:
            bundle_path = Path(bundle_path)
            
            if not bundle_path.exists():
                return True
            
            # Use temporary rename for atomic deletion
            temp_path = bundle_path.parent / f".delete_{bundle_path.name}"
            bundle_path.rename(temp_path)
            
            # Delete temporary directory
            shutil.rmtree(temp_path, ignore_errors=True)
            
            return True
            
        except Exception as e:
            raise SnapshotError(f"Failed to delete bundle: {e}")
    
    async def list_bundles(self, 
                          site: Optional[str] = None,
                          module: Optional[str] = None,
                          component: Optional[str] = None,
                          limit: int = 100) -> List[SnapshotBundle]:
        """List bundles with optional filtering."""
        bundles = []
        
        try:
            # Build search path
            search_path = self.base_path
            if site:
                search_path = search_path / site
            if module:
                search_path = search_path / module
            if component:
                search_path = search_path / component
            
            if not search_path.exists():
                return bundles
            
            # Walk through directories
            for root, dirs, files in os.walk(search_path):
                if "metadata.json" in files:
                    try:
                        bundle = await self.load_bundle(root)
                        if bundle:
                            bundles.append(bundle)
                            if len(bundles) >= limit:
                                break
                    except Exception:
                        # Skip corrupted bundles
                        continue
            
            # Sort by timestamp (newest first)
            bundles.sort(key=lambda b: b.timestamp, reverse=True)
            
            return bundles
            
        except Exception as e:
            raise SnapshotError(f"Failed to list bundles: {e}")
    
    async def cleanup_old_bundles(self, 
                                 days_to_keep: int = 30,
                                 dry_run: bool = False) -> Dict[str, Any]:
        """Clean up old bundles and return statistics."""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            deleted_count = 0
            total_size_freed = 0
            errors = []
            
            for root, dirs, files in os.walk(self.base_path):
                if "metadata.json" in files:
                    try:
                        metadata_path = Path(root) / "metadata.json"
                        stat = metadata_path.stat()
                        
                        if stat.st_mtime < cutoff_date:
                            # Calculate directory size
                            dir_size = self._get_directory_size(root)
                            
                            if not dry_run:
                                await self.delete_bundle(root)
                            
                            deleted_count += 1
                            total_size_freed += dir_size
                            
                    except Exception as e:
                        errors.append(f"Error processing {root}: {e}")
            
            return {
                "deleted_count": deleted_count,
                "size_freed_bytes": total_size_freed,
                "size_freed_mb": total_size_freed / (1024 * 1024),
                "errors": errors,
                "dry_run": dry_run
            }
            
        except Exception as e:
            raise SnapshotError(f"Failed to cleanup old bundles: {e}")
    
    def _get_directory_size(self, path: str) -> int:
        """Calculate total size of directory."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    continue
        return total_size
    
    async def check_partitioning(self, directory_path: str) -> bool:
        """Check if directory needs partitioning."""
        try:
            path = Path(directory_path)
            
            if not path.exists():
                return False
            
            # Count files
            file_count = sum(1 for _ in path.rglob("*") if _.is_file())
            
            # Calculate directory size
            dir_size = self._get_directory_size(directory_path)
            dir_size_mb = dir_size / (1024 * 1024)
            
            return (file_count > self.max_files_per_directory or 
                   dir_size_mb > self.max_directory_size_mb)
            
        except Exception:
            return False
    
    async def create_partition(self, directory_path: str) -> bool:
        """Create partition for large directory."""
        try:
            path = Path(directory_path)
            
            if not path.exists():
                return False
            
            # Create partition subdirectory
            partition_name = f"partition_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            partition_path = path / partition_name
            
            # Move all subdirectories to partition
            for item in path.iterdir():
                if item.is_dir() and item.name != partition_name:
                    new_path = partition_path / item.name
                    item.rename(new_path)
            
            return True
            
        except Exception as e:
            raise SnapshotError(f"Failed to create partition: {e}")
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        try:
            total_bundles = 0
            total_size = 0
            site_stats = {}
            
            for site_dir in self.base_path.iterdir():
                if site_dir.is_dir():
                    site_size = self._get_directory_size(str(site_dir))
                    site_bundles = len(list(site_dir.rglob("metadata.json")))
                    
                    site_stats[site_dir.name] = {
                        "size_bytes": site_size,
                        "size_mb": site_size / (1024 * 1024),
                        "bundle_count": site_bundles
                    }
                    
                    total_bundles += site_bundles
                    total_size += site_size
            
            return {
                "total_bundles": total_bundles,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "total_size_gb": total_size / (1024 * 1024 * 1024),
                "site_statistics": site_stats,
                "base_path": str(self.base_path)
            }
            
        except Exception as e:
            raise SnapshotError(f"Failed to get storage statistics: {e}")


class AtomicFileWriter:
    """Helper class for atomic file operations."""
    
    @staticmethod
    async def write_text(file_path: Path, content: str) -> bool:
        """Write text content atomically."""
        try:
            temp_path = file_path.with_suffix(".tmp")
            
            # Write to temporary file
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Atomic rename
            temp_path.rename(file_path)
            
            return True
            
        except Exception as e:
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise SnapshotError(f"Failed to write file atomically: {e}")
    
    @staticmethod
    async def write_bytes(file_path: Path, content: bytes) -> bool:
        """Write binary content atomically."""
        try:
            temp_path = file_path.with_suffix(".tmp")
            
            # Write to temporary file
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            # Atomic rename
            temp_path.rename(file_path)
            
            return True
            
        except Exception as e:
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise SnapshotError(f"Failed to write file atomically: {e}")
