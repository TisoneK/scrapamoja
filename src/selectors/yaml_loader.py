"""
YAML selector loader for loading and parsing YAML selector configurations.

This module provides functionality to load YAML selector files, validate them,
and convert them into selector objects that can be used by the selector engine.
"""

import os
import yaml
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from glob import glob
import logging

from .models import (
    YAMLSelector, SelectorStrategy, LoadResult, SelectorValidationError,
    ValidationResult, ErrorType, Severity
)
from .exceptions import (
    SelectorLoadingError, SelectorValidationError as SelectorValidationException,
    SelectorFileError, create_file_error, create_loading_error
)
from .validator import SelectorValidator
from .config import get_config
from .performance_monitor import get_performance_monitor, record_metric

logger = logging.getLogger(__name__)


class YAMLSelectorLoader:
    """Loads and parses YAML selector configurations."""
    
    def __init__(self, config=None, validator=None, performance_monitor=None):
        """Initialize YAML selector loader."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.config = config or get_config()
        self.validator = validator or SelectorValidator()
        self.performance_monitor = performance_monitor or get_performance_monitor()
        
        # Cache for loaded selectors
        self._selector_cache: Dict[str, YAMLSelector] = {}
        self._file_timestamps: Dict[str, float] = {}
        
        self.logger.info("YAML selector loader initialized")
    
    def load_selector_from_file(self, file_path: str) -> YAMLSelector:
        """Load a single YAML selector from file."""
        start_time = time.time()
        selector_id = None
        
        try:
            # Validate file path
            if not self.config.validate_file_path(file_path):
                raise SelectorFileError(
                    message=f"File path validation failed: {file_path}",
                    file_path=file_path,
                    operation="load_selector_from_file"
                )
            
            # Check file extension
            if not self.config.is_file_extension_allowed(file_path):
                raise SelectorFileError(
                    message=f"File extension not allowed: {Path(file_path).suffix}",
                    file_path=file_path,
                    operation="load_selector_from_file"
                )
            
            # Check file size
            file_size = Path(file_path).stat().st_size
            if self.config.enforce_file_size_limits and file_size > self.config.max_selector_file_size:
                raise SelectorFileError(
                    message=f"File too large: {file_size} bytes (max: {self.config.max_selector_file_size})",
                    file_path=file_path,
                    operation="load_selector_from_file"
                )
            
            # Load YAML content
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            if not yaml_data:
                raise SelectorLoadingError(
                    message=f"Empty YAML file: {file_path}",
                    file_path=file_path
                )
            
            # Validate YAML structure
            if not isinstance(yaml_data, dict):
                raise SelectorLoadingError(
                    message=f"Invalid YAML structure: expected dictionary, got {type(yaml_data).__name__}",
                    file_path=file_path
                )
            
            # Extract required fields
            selector_id = yaml_data.get('id')
            if not selector_id:
                raise SelectorLoadingError(
                    message="Missing required field: id",
                    file_path=file_path
                )
            
            # Convert to YAMLSelector object
            selector = self._yaml_to_selector(yaml_data, file_path)
            
            # Validate selector
            validation_result = self.validator.validate_selector(selector)
            if not validation_result.is_valid:
                error_messages = [error.error_message for error in validation_result.errors]
                raise SelectorValidationException(
                    message=f"Selector validation failed: {'; '.join(error_messages)}",
                    selector_id=selector.id,
                    validation_errors=error_messages
                )
            
            # Cache the selector
            if self.config.cache_enabled:
                self._cache_selector(file_path, selector)
            
            duration_ms = (time.time() - start_time) * 1000
            record_metric(
                operation="selector_loading",
                duration_ms=duration_ms,
                selector_id=selector.id,
                metadata={"file_path": file_path, "file_size": file_size}
            )
            
            self.logger.info(f"Loaded selector: {selector.id} from {file_path}")
            return selector
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            record_metric(
                operation="selector_loading",
                duration_ms=duration_ms,
                selector_id=selector_id,
                success=False,
                error_message=str(e)
            )
            
            if isinstance(e, (SelectorLoadingError, SelectorFileError, SelectorValidationException)):
                raise
            else:
                raise SelectorLoadingError(
                    message=f"Failed to load selector from {file_path}: {str(e)}",
                    file_path=file_path,
                    loading_errors=[str(e)]
                ) from e
    
    def load_selectors_from_directory(self, directory_path: str, 
                                     recursive: bool = False) -> LoadResult:
        """Load all YAML selectors from a directory."""
        start_time = time.time()
        loaded_selectors = []
        failed_selectors = []
        errors = []
        warnings = []
        
        try:
            # Find YAML files
            yaml_files = self._find_yaml_files(directory_path, recursive)
            
            if not yaml_files:
                self.logger.warning(f"No YAML files found in directory: {directory_path}")
                return LoadResult(
                    success=True,
                    selectors_loaded=0,
                    selectors_failed=0,
                    errors=[f"No YAML files found in directory: {directory_path}"],
                    loading_time_ms=(time.time() - start_time) * 1000
                )
            
            self.logger.info(f"Found {len(yaml_files)} YAML files in {directory_path}")
            
            # Load each file
            for file_path in yaml_files:
                try:
                    selector = self.load_selector_from_file(file_path)
                    loaded_selectors.append(selector)
                    
                except Exception as e:
                    failed_selectors.append(file_path)
                    error_msg = f"Failed to load {file_path}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    
                    if not self.config.continue_on_error:
                        break
            
            # Create result
            total_files = len(yaml_files)
            success_count = len(loaded_selectors)
            failed_count = len(failed_selectors)
            success = success_count > 0 or failed_count == 0
            
            loading_time_ms = (time.time() - start_time) * 1000
            
            result = LoadResult(
                success=success,
                selectors_loaded=success_count,
                selectors_failed=failed_count,
                errors=errors,
                warnings=warnings,
                loading_time_ms=loading_time_ms
            )
            
            self.logger.info(f"Loading complete: {success_count}/{total_files} selectors loaded "
                           f"in {loading_time_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            loading_time_ms = (time.time() - start_time) * 1000
            return LoadResult(
                success=False,
                selectors_loaded=0,
                selectors_failed=0,
                errors=[f"Directory loading failed: {str(e)}"],
                loading_time_ms=loading_time_ms
            )
    
    def reload_selectors(self, selector_ids: Optional[List[str]] = None) -> LoadResult:
        """Reload selectors from their original files."""
        start_time = time.time()
        reloaded_selectors = []
        failed_reloads = []
        errors = []
        
        try:
            # Get selectors to reload
            if selector_ids:
                selectors_to_reload = [
                    (sid, selector) for sid, selector in self._selector_cache.items()
                    if sid in selector_ids
                ]
            else:
                selectors_to_reload = list(self._selector_cache.items())
            
            if not selectors_to_reload:
                self.logger.warning("No selectors to reload")
                return LoadResult(
                    success=True,
                    selectors_loaded=0,
                    selectors_failed=0,
                    loading_time_ms=(time.time() - start_time) * 1000
                )
            
            # Reload each selector
            for selector_id, old_selector in selectors_to_reload:
                try:
                    # Check if file has changed
                    file_path = old_selector.file_path
                    if not Path(file_path).exists():
                        error_msg = f"File no longer exists: {file_path}"
                        errors.append(error_msg)
                        failed_reloads.append(selector_id)
                        continue
                    
                    current_mtime = Path(file_path).stat().st_mtime
                    cached_mtime = self._file_timestamps.get(file_path, 0)
                    
                    if current_mtime <= cached_mtime:
                        # File hasn't changed, use cached selector
                        reloaded_selectors.append(old_selector)
                        continue
                    
                    # Reload from file
                    new_selector = self.load_selector_from_file(file_path)
                    reloaded_selectors.append(new_selector)
                    
                    self.logger.info(f"Reloaded selector: {selector_id}")
                    
                except Exception as e:
                    error_msg = f"Failed to reload {selector_id}: {str(e)}"
                    errors.append(error_msg)
                    failed_reloads.append(selector_id)
                    self.logger.error(error_msg)
            
            # Create result
            success_count = len(reloaded_selectors)
            failed_count = len(failed_reloads)
            loading_time_ms = (time.time() - start_time) * 1000
            
            result = LoadResult(
                success=success_count > 0,
                selectors_loaded=success_count,
                selectors_failed=failed_count,
                errors=errors,
                loading_time_ms=loading_time_ms
            )
            
            self.logger.info(f"Reload complete: {success_count} selectors reloaded")
            return result
            
        except Exception as e:
            loading_time_ms = (time.time() - start_time) * 1000
            return LoadResult(
                success=False,
                selectors_loaded=0,
                selectors_failed=0,
                errors=[f"Reload failed: {str(e)}"],
                loading_time_ms=loading_time_ms
            )
    
    def get_cached_selector(self, file_path: str) -> Optional[YAMLSelector]:
        """Get selector from cache if available and up-to-date."""
        if not self.config.cache_enabled:
            return None
        
        # Check if file has changed
        if not Path(file_path).exists():
            return None
        
        current_mtime = Path(file_path).stat().st_mtime
        cached_mtime = self._file_timestamps.get(file_path, 0)
        
        if current_mtime > cached_mtime:
            # File has changed, invalidate cache
            if file_path in self._selector_cache:
                del self._selector_cache[file_path]
            if file_path in self._file_timestamps:
                del self._file_timestamps[file_path]
            return None
        
        return self._selector_cache.get(file_path)
    
    def clear_cache(self, file_path: Optional[str] = None):
        """Clear selector cache."""
        if file_path:
            self._selector_cache.pop(file_path, None)
            self._file_timestamps.pop(file_path, None)
            self.logger.info(f"Cleared cache for: {file_path}")
        else:
            self._selector_cache.clear()
            self._file_timestamps.clear()
            self.logger.info("Cleared all selector cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_selectors": len(self._selector_cache),
            "cache_enabled": self.config.cache_enabled,
            "cache_ttl": self.config.cache_ttl,
            "cached_files": list(self._selector_cache.keys())
        }
    
    def _find_yaml_files(self, directory_path: str, recursive: bool = False) -> List[str]:
        """Find all YAML files in directory."""
        try:
            path = Path(directory_path)
            if not path.exists() or not path.is_dir():
                raise SelectorFileError(
                    message=f"Directory not found or not accessible: {directory_path}",
                    file_path=directory_path,
                    operation="find_yaml_files"
                )
            
            # Build glob pattern
            pattern = "**/*.yaml" if recursive else "*.yaml"
            yaml_files = list(path.glob(pattern))
            
            # Also check for .yml extension
            pattern_yml = "**/*.yml" if recursive else "*.yml"
            yaml_files.extend(list(path.glob(pattern_yml)))
            
            # Convert to strings and remove duplicates
            file_paths = list(set(str(f) for f in yaml_files))
            
            return sorted(file_paths)
            
        except Exception as e:
            raise SelectorFileError(
                message=f"Failed to find YAML files in {directory_path}: {str(e)}",
                file_path=directory_path,
                operation="find_yaml_files"
            ) from e
    
    def _yaml_to_selector(self, yaml_data: Dict[str, Any], file_path: str) -> YAMLSelector:
        """Convert YAML data to YAMLSelector object."""
        try:
            # Extract strategies
            strategies_data = yaml_data.get('strategies', [])
            strategies = []
            
            for strategy_data in strategies_data:
                strategy = SelectorStrategy.from_dict(strategy_data)
                strategies.append(strategy)
            
            # Create selector
            selector = YAMLSelector(
                id=yaml_data['id'],
                name=yaml_data['name'],
                description=yaml_data.get('description'),
                selector_type=SelectorType(yaml_data['selector_type']),
                pattern=yaml_data['pattern'],
                strategies=strategies,
                validation_rules=yaml_data.get('validation_rules'),
                metadata=yaml_data.get('metadata'),
                file_path=file_path,
                version=yaml_data.get('version', '1.0.0')
            )
            
            return selector
            
        except Exception as e:
            raise SelectorLoadingError(
                message=f"Failed to convert YAML to selector: {str(e)}",
                file_path=file_path,
                loading_errors=[str(e)]
            ) from e
    
    def _cache_selector(self, file_path: str, selector: YAMLSelector):
        """Cache selector with timestamp."""
        if not self.config.cache_enabled:
            return
        
        try:
            self._selector_cache[file_path] = selector
            self._file_timestamps[file_path] = Path(file_path).stat().st_mtime
        except Exception as e:
            self.logger.warning(f"Failed to cache selector {file_path}: {str(e)}")


# Global loader instance
_yaml_loader: Optional[YAMLSelectorLoader] = None


def get_yaml_loader() -> YAMLSelectorLoader:
    """Get global YAML selector loader instance."""
    global _yaml_loader
    if _yaml_loader is None:
        _yaml_loader = YAMLSelectorLoader()
    return _yaml_loader


def load_selector_from_file(file_path: str) -> YAMLSelector:
    """Load selector from file using global loader."""
    return get_yaml_loader().load_selector_from_file(file_path)


def load_selectors_from_directory(directory_path: str, recursive: bool = False) -> LoadResult:
    """Load selectors from directory using global loader."""
    return get_yaml_loader().load_selectors_from_directory(directory_path, recursive)
