"""
Temporary file management system for interrupt handling.
"""

import os
import tempfile
import shutil
import time
import logging
import threading
from typing import Dict, List, Optional, Union, Callable
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass, field

from .file_cleanup import FileCleanupManager


@dataclass
class TempFileInfo:
    """Information about a temporary file."""
    file_id: str
    file_path: Path
    original_path: Optional[Path] = None
    created_at: float = field(default_factory=time.time)
    purpose: str = ""
    auto_cleanup: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)
    
    @property
    def age(self) -> float:
        """Get age of temporary file in seconds."""
        return time.time() - self.created_at
    
    @property
    def size(self) -> int:
        """Get size of temporary file in bytes."""
        try:
            return self.file_path.stat().st_size if self.file_path.exists() else 0
        except OSError:
            return 0


class TempFileManager:
    """Manages temporary files with automatic cleanup."""
    
    def __init__(self, cleanup_manager: Optional[FileCleanupManager] = None, 
                 temp_dir: Optional[Union[str, Path]] = None):
        self.cleanup_manager = cleanup_manager
        self.logger = logging.getLogger(__name__)
        self._temp_files: Dict[str, TempFileInfo] = {}
        self._lock = threading.RLock()
        
        # Set up temporary directory
        if temp_dir:
            self.temp_dir = Path(temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.temp_dir = Path(tempfile.gettempdir())
        
        # Cleanup old files on startup
        self._cleanup_old_files()
        
        # Register for cleanup if cleanup manager provided
        if self.cleanup_manager:
            self.cleanup_manager.register_custom(
                "temp_file_manager",
                self.cleanup_all_temp_files,
                "Temporary file manager cleanup"
            )
    
    def create_temp_file(self, file_id: str, suffix: str = "", prefix: str = "scrapamoja_",
                       purpose: str = "", auto_cleanup: bool = True,
                       content: Optional[Union[str, bytes]] = None) -> Path:
        """
        Create a temporary file.
        
        Args:
            file_id: Unique identifier for the file
            suffix: File suffix (e.g., '.tmp')
            prefix: File prefix
            purpose: Description of file purpose
            auto_cleanup: Whether to auto-cleanup on exit
            content: Initial content for the file
            
        Returns:
            Path to the created temporary file
        """
        with self._lock:
            if file_id in self._temp_files:
                self.logger.warning(f"Temp file {file_id} already exists")
                return self._temp_files[file_id].file_path
            
            try:
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(
                    dir=self.temp_dir,
                    prefix=prefix,
                    suffix=suffix,
                    delete=False
                )
                temp_path = Path(temp_file.name)
                
                # Write initial content if provided
                if content is not None:
                    mode = 'w' if isinstance(content, str) else 'wb'
                    with open(temp_path, mode) as f:
                        f.write(content)
                
                # Store file info
                file_info = TempFileInfo(
                    file_id=file_id,
                    file_path=temp_path,
                    purpose=purpose,
                    auto_cleanup=auto_cleanup
                )
                
                self._temp_files[file_id] = file_info
                
                # Register for cleanup if auto_cleanup is True
                if auto_cleanup and self.cleanup_manager:
                    self.cleanup_manager.register_temp_file(f"temp_{file_id}", str(temp_path))
                
                self.logger.debug(f"Created temp file {file_id}: {temp_path}")
                return temp_path
                
            except Exception as e:
                self.logger.error(f"Error creating temp file {file_id}: {e}")
                raise
    
    def create_temp_dir(self, dir_id: str, prefix: str = "scrapamoja_",
                       purpose: str = "", auto_cleanup: bool = True) -> Path:
        """
        Create a temporary directory.
        
        Args:
            dir_id: Unique identifier for the directory
            prefix: Directory prefix
            purpose: Description of directory purpose
            auto_cleanup: Whether to auto-cleanup on exit
            
        Returns:
            Path to the created temporary directory
        """
        with self._lock:
            if dir_id in self._temp_files:
                self.logger.warning(f"Temp dir {dir_id} already exists")
                return self._temp_files[dir_id].file_path
            
            try:
                # Create temporary directory
                temp_path = Path(tempfile.mkdtemp(prefix=prefix, dir=self.temp_dir))
                
                # Store directory info
                file_info = TempFileInfo(
                    file_id=dir_id,
                    file_path=temp_path,
                    purpose=purpose,
                    auto_cleanup=auto_cleanup
                )
                
                self._temp_files[dir_id] = file_info
                
                self.logger.debug(f"Created temp dir {dir_id}: {temp_path}")
                return temp_path
                
            except Exception as e:
                self.logger.error(f"Error creating temp dir {dir_id}: {e}")
                raise
    
    def get_temp_file(self, file_id: str) -> Optional[TempFileInfo]:
        """Get information about a temporary file."""
        with self._lock:
            return self._temp_files.get(file_id)
    
    def get_temp_path(self, file_id: str) -> Optional[Path]:
        """Get path to a temporary file."""
        file_info = self.get_temp_file(file_id)
        return file_info.file_path if file_info else None
    
    def remove_temp_file(self, file_id: str) -> bool:
        """Remove a temporary file."""
        with self._lock:
            file_info = self._temp_files.get(file_id)
            if not file_info:
                self.logger.warning(f"Temp file {file_id} not found")
                return False
            
            try:
                # Remove file or directory
                if file_info.file_path.is_dir():
                    shutil.rmtree(file_info.file_path)
                    self.logger.debug(f"Removed temp dir {file_id}: {file_info.file_path}")
                else:
                    file_info.file_path.unlink(missing_ok=True)
                    self.logger.debug(f"Removed temp file {file_id}: {file_info.file_path}")
                
                # Unregister from cleanup manager
                if file_info.auto_cleanup and self.cleanup_manager:
                    self.cleanup_manager.unregister_resource(f"temp_{file_id}")
                
                # Remove from tracking
                del self._temp_files[file_id]
                return True
                
            except Exception as e:
                self.logger.error(f"Error removing temp file {file_id}: {e}")
                return False
    
    def move_temp_file(self, file_id: str, destination: Union[str, Path], 
                       keep_temp: bool = False) -> bool:
        """
        Move a temporary file to a permanent location.
        
        Args:
            file_id: ID of temporary file
            destination: Destination path
            keep_temp: Whether to keep the temporary file
            
        Returns:
            True if move successful, False otherwise
        """
        with self._lock:
            file_info = self._temp_files.get(file_id)
            if not file_info:
                self.logger.warning(f"Temp file {file_id} not found")
                return False
            
            try:
                dest_path = Path(destination)
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move file
                shutil.move(str(file_info.file_path), str(dest_path))
                
                # Update original path
                file_info.original_path = dest_path
                
                if not keep_temp:
                    # Remove from tracking
                    if file_info.auto_cleanup and self.cleanup_manager:
                        self.cleanup_manager.unregister_resource(f"temp_{file_id}")
                    del self._temp_files[file_id]
                
                self.logger.debug(f"Moved temp file {file_id} to {dest_path}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error moving temp file {file_id}: {e}")
                return False
    
    def cleanup_temp_file(self, file_id: str) -> bool:
        """Clean up a temporary file (alias for remove_temp_file)."""
        return self.remove_temp_file(file_id)
    
    def cleanup_all_temp_files(self) -> Dict[str, bool]:
        """Clean up all temporary files."""
        with self._lock:
            file_ids = list(self._temp_files.keys())
            results = {}
            
            for file_id in file_ids:
                results[file_id] = self.remove_temp_file(file_id)
            
            successful_count = sum(1 for success in results.values() if success)
            self.logger.info(f"Cleaned up {successful_count}/{len(results)} temp files")
            
            return results
    
    def cleanup_old_files(self, max_age_hours: float = 24.0) -> int:
        """Clean up temporary files older than max_age_hours."""
        with self._lock:
            old_files = [
                file_id for file_id, file_info in self._temp_files.items()
                if file_info.age > (max_age_hours * 3600)
            ]
            
            cleaned_count = 0
            for file_id in old_files:
                if self.remove_temp_file(file_id):
                    cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} old temp files")
            
            return cleaned_count
    
    def get_temp_file_status(self) -> Dict[str, any]:
        """Get status of all temporary files."""
        with self._lock:
            files_info = {}
            total_size = 0
            
            for file_id, file_info in self._temp_files.items():
                size = file_info.size
                total_size += size
                
                files_info[file_id] = {
                    'path': str(file_info.file_path),
                    'purpose': file_info.purpose,
                    'age_seconds': file_info.age,
                    'size_bytes': size,
                    'auto_cleanup': file_info.auto_cleanup,
                    'exists': file_info.file_path.exists(),
                    'is_dir': file_info.file_path.is_dir() if file_info.file_path.exists() else False
                }
            
            return {
                'total_files': len(self._temp_files),
                'total_size_bytes': total_size,
                'temp_directory': str(self.temp_dir),
                'files': files_info
            }
    
    @contextmanager
    def managed_temp_file(self, file_id: str, suffix: str = "", prefix: str = "scrapamoja_",
                           purpose: str = "", auto_cleanup: bool = True,
                           content: Optional[Union[str, bytes]] = None):
        """Context manager for temporary file management."""
        temp_path = None
        try:
            temp_path = self.create_temp_file(
                file_id, suffix, prefix, purpose, auto_cleanup, content
            )
            yield temp_path
        finally:
            if temp_path:
                self.remove_temp_file(file_id)
    
    @contextmanager
    def managed_temp_dir(self, dir_id: str, prefix: str = "scrapamoja_",
                       purpose: str = "", auto_cleanup: bool = True):
        """Context manager for temporary directory management."""
        temp_path = None
        try:
            temp_path = self.create_temp_dir(dir_id, prefix, purpose, auto_cleanup)
            yield temp_path
        finally:
            if temp_path:
                self.remove_temp_file(dir_id)
    
    def set_metadata(self, file_id: str, key: str, value: str):
        """Set metadata for a temporary file."""
        with self._lock:
            file_info = self._temp_files.get(file_id)
            if file_info:
                file_info.metadata[key] = value
            else:
                self.logger.warning(f"Temp file {file_id} not found for metadata")
    
    def get_metadata(self, file_id: str, key: str, default: str = "") -> str:
        """Get metadata for a temporary file."""
        with self._lock:
            file_info = self._temp_files.get(file_id)
            if file_info:
                return file_info.metadata.get(key, default)
            else:
                self.logger.warning(f"Temp file {file_id} not found for metadata")
                return default
    
    def find_temp_files_by_purpose(self, purpose: str) -> List[str]:
        """Find temporary files by purpose."""
        with self._lock:
            return [
                file_id for file_id, file_info in self._temp_files.items()
                if purpose.lower() in file_info.purpose.lower()
            ]
    
    def get_temp_directory(self) -> Path:
        """Get the temporary directory path."""
        return self.temp_dir
    
    def set_temp_directory(self, temp_dir: Union[str, Path]):
        """Set a new temporary directory."""
        with self._lock:
            # Clean up existing files first
            self.cleanup_all_temp_files()
            
            # Set new directory
            self.temp_dir = Path(temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Changed temp directory to: {self.temp_dir}")


# Global temporary file manager instance
_temp_file_manager = None


def get_temp_file_manager(cleanup_manager: Optional[FileCleanupManager] = None,
                         temp_dir: Optional[Union[str, Path]] = None) -> TempFileManager:
    """Get the global temporary file manager instance."""
    global _temp_file_manager
    if _temp_file_manager is None:
        _temp_file_manager = TempFileManager(cleanup_manager, temp_dir)
    return _temp_file_manager
