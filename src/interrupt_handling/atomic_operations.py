"""
Atomic file operations for safe data preservation.
"""

import os
import tempfile
import shutil
import hashlib
import json
import pickle
import logging
import time
from typing import Any, Dict, List, Optional, Union, Callable, BinaryIO, TextIO
from contextlib import contextmanager
from pathlib import Path

from .file_cleanup import FileCleanupManager


class AtomicFileOperation:
    """Base class for atomic file operations."""
    
    def __init__(self, file_path: Union[str, Path], cleanup_manager: Optional[FileCleanupManager] = None):
        self.file_path = Path(file_path)
        self.cleanup_manager = cleanup_manager
        self.logger = logging.getLogger(__name__)
        self.temp_path = None
        self.backup_path = None
        self.operation_id = f"atomic_{int(time.time() * 1000)}"
    
    def _create_temp_file(self, suffix: str = '.tmp') -> Path:
        """Create a temporary file in the same directory as the target."""
        temp_dir = self.file_path.parent
        temp_file = tempfile.NamedTemporaryFile(
            dir=temp_dir,
            prefix=f'.tmp_{self.operation_id}_',
            suffix=suffix,
            delete=False
        )
        temp_file.close()
        temp_path = Path(temp_file.name)
        
        # Register for cleanup
        if self.cleanup_manager:
            self.cleanup_manager.register_temp_file(f"{self.operation_id}_temp", str(temp_path))
        
        return temp_path
    
    def _create_backup(self) -> Optional[Path]:
        """Create a backup of the original file if it exists."""
        if not self.file_path.exists():
            return None
        
        backup_dir = self.file_path.parent / '.backups'
        backup_dir.mkdir(exist_ok=True)
        
        backup_path = backup_dir / f"{self.file_path.name}.backup_{self.operation_id}"
        
        try:
            shutil.copy2(self.file_path, backup_path)
            
            # Register backup for cleanup
            if self.cleanup_manager:
                self.cleanup_manager.register_temp_file(f"{self.operation_id}_backup", str(backup_path))
            
            self.logger.debug(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None
    
    def _atomic_move(self, source: Path, destination: Path) -> bool:
        """Atomically move a file."""
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Use os.replace for atomic operation
            os.replace(source, destination)
            self.logger.debug(f"Atomically moved: {source} -> {destination}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to atomically move {source} to {destination}: {e}")
            return False
    
    def _verify_file_integrity(self, file_path: Path, expected_hash: Optional[str] = None) -> bool:
        """Verify file integrity using hash."""
        if not expected_hash:
            return True  # Skip verification if no hash provided
        
        try:
            current_hash = self._calculate_file_hash(file_path)
            return current_hash == expected_hash
            
        except Exception as e:
            self.logger.error(f"Error verifying file integrity: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: Path, algorithm: str = 'sha256') -> str:
        """Calculate hash of a file."""
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()


class AtomicFileWriter(AtomicFileOperation):
    """Atomic file writer with data preservation."""
    
    def __init__(self, file_path: Union[str, Path], cleanup_manager: Optional[FileCleanupManager] = None,
                 create_backup: bool = True, verify_integrity: bool = True):
        super().__init__(file_path, cleanup_manager)
        self.create_backup = create_backup
        self.verify_integrity = verify_integrity
        self.temp_file = None
        self.file_hash = None
    
    def __enter__(self):
        """Enter context and prepare for atomic writing."""
        try:
            # Create backup if requested and file exists
            if self.create_backup:
                self.backup_path = self._create_backup()
            
            # Create temporary file
            self.temp_path = self._create_temp_file()
            self.temp_file = open(self.temp_path, 'wb')
            
            self.logger.debug(f"Atomic writer prepared: {self.file_path}")
            return self.temp_file
            
        except Exception as e:
            self.logger.error(f"Error preparing atomic writer: {e}")
            self._cleanup()
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and atomically commit or rollback."""
        try:
            # Close temp file
            if self.temp_file:
                self.temp_file.close()
            
            if exc_type is None:
                # Calculate hash if verification is enabled
                if self.verify_integrity and self.temp_path:
                    self.file_hash = self._calculate_file_hash(self.temp_path)
                
                # Atomically move temp file to target
                if self.temp_path and self._atomic_move(self.temp_path, self.file_path):
                    # Verify integrity if requested
                    if self.verify_integrity and self.file_hash:
                        if not self._verify_file_integrity(self.file_path, self.file_hash):
                            self.logger.error("File integrity verification failed")
                            # Restore backup if available
                            if self.backup_path:
                                self._atomic_move(self.backup_path, self.file_path)
                            raise RuntimeError("File integrity verification failed")
                    
                    self.logger.debug(f"Atomic write successful: {self.file_path}")
                else:
                    raise RuntimeError("Failed to atomically move file")
            else:
                self.logger.warning(f"Exception occurred, rolling back: {exc_val}")
                # Cleanup temp file but keep backup
                
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Cleanup temporary files."""
        if self.temp_file and not self.temp_file.closed:
            try:
                self.temp_file.close()
            except:
                pass
        
        if self.temp_path and self.temp_path.exists():
            try:
                self.temp_path.unlink()
                self.logger.debug(f"Cleaned up temp file: {self.temp_path}")
            except Exception as e:
                self.logger.error(f"Error cleaning up temp file: {e}")
        
        # Note: Backup files are kept for manual recovery


class AtomicJsonWriter(AtomicFileOperation):
    """Atomic JSON file writer."""
    
    def __init__(self, file_path: Union[str, Path], cleanup_manager: Optional[FileCleanupManager] = None,
                 create_backup: bool = True, indent: Optional[int] = 2):
        super().__init__(file_path, cleanup_manager)
        self.create_backup = create_backup
        self.indent = indent
    
    def write(self, data: Any) -> bool:
        """Atomically write JSON data."""
        try:
            # Create backup if requested
            if self.create_backup:
                self.backup_path = self._create_backup()
            
            # Write to temporary file
            self.temp_path = self._create_temp_file('.json')
            
            with open(self.temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=self.indent, ensure_ascii=False)
            
            # Verify JSON is valid
            with open(self.temp_path, 'r', encoding='utf-8') as f:
                json.load(f)  # This will raise if JSON is invalid
            
            # Atomically move to target
            success = self._atomic_move(self.temp_path, self.file_path)
            
            if success:
                self.logger.debug(f"Atomic JSON write successful: {self.file_path}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error in atomic JSON write: {e}")
            return False
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Cleanup temporary files."""
        if self.temp_path and self.temp_path.exists():
            try:
                self.temp_path.unlink()
            except Exception as e:
                self.logger.error(f"Error cleaning up temp file: {e}")


class AtomicPickleWriter(AtomicFileOperation):
    """Atomic pickle file writer."""
    
    def __init__(self, file_path: Union[str, Path], cleanup_manager: Optional[FileCleanupManager] = None,
                 create_backup: bool = True, protocol: int = pickle.HIGHEST_PROTOCOL):
        super().__init__(file_path, cleanup_manager)
        self.create_backup = create_backup
        self.protocol = protocol
    
    def write(self, data: Any) -> bool:
        """Atomically write pickled data."""
        try:
            # Create backup if requested
            if self.create_backup:
                self.backup_path = self._create_backup()
            
            # Write to temporary file
            self.temp_path = self._create_temp_file('.pkl')
            
            with open(self.temp_path, 'wb') as f:
                pickle.dump(data, f, protocol=self.protocol)
            
            # Verify pickle is valid
            with open(self.temp_path, 'rb') as f:
                pickle.load(f)  # This will raise if pickle is invalid
            
            # Atomically move to target
            success = self._atomic_move(self.temp_path, self.file_path)
            
            if success:
                self.logger.debug(f"Atomic pickle write successful: {self.file_path}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error in atomic pickle write: {e}")
            return False
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Cleanup temporary files."""
        if self.temp_path and self.temp_path.exists():
            try:
                self.temp_path.unlink()
            except Exception as e:
                self.logger.error(f"Error cleaning up temp file: {e}")


class AtomicAppendWriter(AtomicFileOperation):
    """Atomic file appender for log files and similar."""
    
    def __init__(self, file_path: Union[str, Path], cleanup_manager: Optional[FileCleanupManager] = None):
        super().__init__(file_path, cleanup_manager)
        self.buffer = []
    
    def append(self, data: Union[str, bytes]) -> bool:
        """Add data to append buffer."""
        self.buffer.append(data)
        return True
    
    def flush(self) -> bool:
        """Atomically flush buffered data to file."""
        if not self.buffer:
            return True
        
        try:
            # Read existing content if file exists
            existing_content = b""
            if self.file_path.exists():
                with open(self.file_path, 'rb') as f:
                    existing_content = f.read()
            
            # Create temporary file
            self.temp_path = self._create_temp_file()
            
            # Write existing content plus new data
            with open(self.temp_path, 'wb') as f:
                f.write(existing_content)
                for data in self.buffer:
                    if isinstance(data, str):
                        f.write(data.encode('utf-8'))
                    else:
                        f.write(data)
            
            # Atomically move to target
            success = self._atomic_move(self.temp_path, self.file_path)
            
            if success:
                self.buffer.clear()
                self.logger.debug(f"Atomic append successful: {self.file_path}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error in atomic append: {e}")
            return False
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Cleanup temporary files."""
        if self.temp_path and self.temp_path.exists():
            try:
                self.temp_path.unlink()
            except Exception as e:
                self.logger.error(f"Error cleaning up temp file: {e}")


class AtomicOperationManager:
    """Manager for atomic file operations."""
    
    def __init__(self, cleanup_manager: Optional[FileCleanupManager] = None):
        self.cleanup_manager = cleanup_manager
        self.logger = logging.getLogger(__name__)
        self._operations: Dict[str, AtomicFileOperation] = {}
    
    def create_writer(self, file_path: Union[str, Path], **kwargs) -> AtomicFileWriter:
        """Create an atomic file writer."""
        writer = AtomicFileWriter(file_path, self.cleanup_manager, **kwargs)
        self._operations[writer.operation_id] = writer
        return writer
    
    def create_json_writer(self, file_path: Union[str, Path], **kwargs) -> AtomicJsonWriter:
        """Create an atomic JSON writer."""
        writer = AtomicJsonWriter(file_path, self.cleanup_manager, **kwargs)
        self._operations[writer.operation_id] = writer
        return writer
    
    def create_pickle_writer(self, file_path: Union[str, Path], **kwargs) -> AtomicPickleWriter:
        """Create an atomic pickle writer."""
        writer = AtomicPickleWriter(file_path, self.cleanup_manager, **kwargs)
        self._operations[writer.operation_id] = writer
        return writer
    
    def create_append_writer(self, file_path: Union[str, Path], **kwargs) -> AtomicAppendWriter:
        """Create an atomic append writer."""
        writer = AtomicAppendWriter(file_path, self.cleanup_manager, **kwargs)
        self._operations[writer.operation_id] = writer
        return writer
    
    def cleanup_operation(self, operation_id: str):
        """Cleanup an operation."""
        if operation_id in self._operations:
            operation = self._operations[operation_id]
            operation._cleanup()
            del self._operations[operation_id]
    
    def cleanup_all_operations(self):
        """Cleanup all operations."""
        for operation_id in list(self._operations.keys()):
            self.cleanup_operation(operation_id)
    
    @contextmanager
    def atomic_json_context(self, file_path: Union[str, Path], **kwargs):
        """Context manager for atomic JSON operations."""
        writer = self.create_json_writer(file_path, **kwargs)
        try:
            yield writer
        finally:
            self.cleanup_operation(writer.operation_id)
    
    @contextmanager
    def atomic_pickle_context(self, file_path: Union[str, Path], **kwargs):
        """Context manager for atomic pickle operations."""
        writer = self.create_pickle_writer(file_path, **kwargs)
        try:
            yield writer
        finally:
            self.cleanup_operation(writer.operation_id)
    
    def get_operation_status(self) -> Dict[str, Any]:
        """Get status of all operations."""
        return {
            'active_operations': len(self._operations),
            'operation_ids': list(self._operations.keys())
        }
