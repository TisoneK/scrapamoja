"""
Central registry for managing site scrapers.

Provides discovery, registration, and validation of site scrapers.
Enforces unique site IDs and maintains metadata for all registered scrapers.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Type
from .base.site_scraper import BaseSiteScraper
from .base.validation import ValidationResult, FileValidator, ConfigurationValidator, InterfaceValidator
from .base.error_formatter import ErrorFormatter
from .exceptions import RegistryError, ValidationError
from .logging import get_logger


class ScraperRegistry:
    """Central registry for managing site scrapers."""
    
    def __init__(self):
        self._scrapers: Dict[str, Type[BaseSiteScraper]] = {}
        self._metadata: Dict[str, dict] = {}
        self._validation_cache: Dict[str, ValidationResult] = {}
        self._validation_timestamps: Dict[str, float] = {}
        self._cache_ttl: float = 300.0  # 5 minutes cache TTL
        self._logger = get_logger()
    
    def register(self, site_id: str, scraper_class: Type[BaseSiteScraper]) -> None:
        """Register a scraper class with validation."""
        self._logger.info("Registering scraper", site_id=site_id, scraper_class=scraper_class.__name__)
        
        try:
            # Validate site_id uniqueness
            if site_id in self._scrapers:
                error_msg = f"Site ID '{site_id}' already registered"
                self._logger.error("Registration failed", site_id=site_id, error="duplicate_id")
                raise RegistryError(error_msg)
            
            # Validate scraper class inheritance
            if not issubclass(scraper_class, BaseSiteScraper):
                error_msg = f"Scraper class must inherit from BaseSiteScraper"
                self._logger.error("Registration failed", site_id=site_id, error="invalid_inheritance")
                raise RegistryError(error_msg)
            
            # Validate scraper implementation
            validation_result = self.validate_scraper_class(scraper_class)
            if not validation_result.is_valid():
                self._logger.error("Scraper validation failed", site_id=site_id, errors=validation_result.errors)
                raise RegistryError(f"Scraper validation failed: {validation_result.errors}")
            
            # Load and validate configuration
            config = self._load_site_configuration(scraper_class)
            if config.get("id") != site_id:
                error_msg = f"Site ID mismatch: config={config.get('id')}, registered={site_id}"
                self._logger.error("Configuration mismatch", site_id=site_id, config_id=config.get('id'))
                raise RegistryError(error_msg)
            
            # Register scraper
            self._scrapers[site_id] = scraper_class
            self._metadata[site_id] = config
            self._validation_cache[site_id] = validation_result
            self._validation_timestamps[site_id] = self._get_current_timestamp()
            
            self._logger.info("Scraper registered successfully", site_id=site_id, site_name=config.get('name'))
            
        except Exception as e:
            self._logger.error("Unexpected error during registration", site_id=site_id, error=str(e))
            raise
    
    def get_scraper(self, site_id: str) -> Type[BaseSiteScraper]:
        """Get scraper class by site ID."""
        if site_id not in self._scrapers:
            error_msg = f"Site '{site_id}' not found in registry"
            self._logger.error("Scraper not found", site_id=site_id, available_sites=list(self._scrapers.keys()))
            raise RegistryError(error_msg)
        
        self._logger.debug("Retrieved scraper", site_id=site_id)
        return self._scrapers[site_id]
    
    def list_scrapers(self) -> List[str]:
        """List all registered scraper IDs."""
        scrapers = list(self._scrapers.keys())
        self._logger.debug("Listed scrapers", count=len(scrapers), scrapers=scrapers)
        return scrapers
    
    def get_metadata(self, site_id: str) -> dict:
        """Get site configuration metadata."""
        if site_id not in self._metadata:
            error_msg = f"Site '{site_id}' not found in registry"
            self._logger.error("Metadata not found", site_id=site_id)
            raise RegistryError(error_msg)
        
        self._logger.debug("Retrieved metadata", site_id=site_id)
        return self._metadata[site_id]
    
    def validate_all(self) -> Dict[str, ValidationResult]:
        """Validate all registered scrapers with comprehensive startup validation."""
        self._logger.info("Performing comprehensive startup validation", count=len(self._scrapers))
        
        results = {}
        total_errors = 0
        total_warnings = 0
        
        for site_id in self._scrapers:
            self._logger.debug("Validating scraper", site_id=site_id)
            result = self.validate_scraper(site_id)
            results[site_id] = result
            
            if not result.is_valid():
                total_errors += len(result.errors)
                self._logger.error("Scraper validation failed", site_id=site_id, errors=result.errors)
            else:
                self._logger.info("Scraper validation passed", site_id=site_id)
            
            total_warnings += len(result.warnings)
            if result.warnings:
                self._logger.warning("Scraper validation warnings", site_id=site_id, warnings=result.warnings)
        
        # Summary logging
        valid_count = sum(1 for result in results.values() if result.is_valid())
        self._logger.info("Startup validation complete", 
                         total=len(results), 
                         valid=valid_count, 
                         invalid=len(results)-valid_count,
                         total_errors=total_errors,
                         total_warnings=total_warnings)
        
        # Provide actionable summary for failed validations
        if total_errors > 0:
            failed_scrapers = [site_id for site_id, result in results.items() if not result.is_valid()]
            self._logger.error("Validation summary - failed scrapers", 
                             failed_scrapers=failed_scrapers,
                             total_errors=total_errors)
            
            # Log specific guidance for each failed scraper
            for site_id in failed_scrapers:
                result = results[site_id]
                guidance = self._generate_validation_guidance(site_id, result)
                self._logger.error("Validation guidance", site_id=site_id, guidance=guidance)
        
        return results
    
    def _generate_validation_guidance(self, site_id: str, result: ValidationResult) -> Dict[str, Any]:
        """Generate actionable guidance for validation failures."""
        guidance = {
            "site_id": site_id,
            "status": "failed" if not result.is_valid() else "passed",
            "actions": []
        }
        
        # File-related issues
        if result.missing_files:
            guidance["actions"].append({
                "type": "missing_files",
                "message": f"Create missing files: {', '.join(result.missing_files)}",
                "files": result.missing_files
            })
        
        # Selector-related issues
        if result.invalid_selectors:
            guidance["actions"].append({
                "type": "invalid_selectors",
                "message": f"Fix invalid selector files: {', '.join(result.invalid_selectors)}",
                "files": result.invalid_selectors
            })
        
        # General errors
        for error in result.errors:
            if "Missing required class attribute" in error:
                attr = error.split(":")[1].strip() if ":" in error else "unknown"
                guidance["actions"].append({
                    "type": "missing_attribute",
                    "message": f"Add class attribute: {attr}",
                    "attribute": attr
                })
            elif "Missing required method" in error:
                method = error.split(":")[1].strip() if ":" in error else "unknown"
                guidance["actions"].append({
                    "type": "missing_method",
                    "message": f"Implement method: {method}()",
                    "method": method
                })
            elif "Configuration field" in error:
                field = error.split("'")[1] if "'" in error else "unknown"
                guidance["actions"].append({
                    "type": "missing_config_field",
                    "message": f"Add configuration field: {field}",
                    "field": field
                })
        
        return guidance
    
    def validate_scraper(self, site_id: str) -> ValidationResult:
        """Validate a specific scraper with caching."""
        if site_id not in self._scrapers:
            result = ValidationResult()
            result.add_error(f"Site '{site_id}' not found in registry")
            self._logger.error("Validation failed - scraper not found", site_id=site_id)
            return result
        
        # Check cache validity
        if self._is_cache_valid(site_id):
            result = self._validation_cache[site_id]
            self._logger.debug("Using cached validation result", site_id=site_id, valid=result.is_valid(), 
                             cache_age=self._get_cache_age(site_id))
            return result
        
        # Perform validation
        self._logger.debug("Performing validation", site_id=site_id)
        scraper_class = self._scrapers[site_id]
        result = self.validate_scraper_class(scraper_class)
        
        # Cache result
        self._validation_cache[site_id] = result
        self._validation_timestamps[site_id] = self._get_current_timestamp()
        
        self._logger.info("Validation completed", site_id=site_id, valid=result.is_valid(), 
                         errors=len(result.errors), warnings=len(result.warnings))
        
        return result
    
    def _is_cache_valid(self, site_id: str) -> bool:
        """Check if cached validation result is still valid."""
        if site_id not in self._validation_cache:
            return False
        
        if site_id not in self._validation_timestamps:
            return False
        
        cache_age = self._get_cache_age(site_id)
        return cache_age < self._cache_ttl
    
    def _get_cache_age(self, site_id: str) -> float:
        """Get age of cached validation result in seconds."""
        if site_id not in self._validation_timestamps:
            return float('inf')
        
        return self._get_current_timestamp() - self._validation_timestamps[site_id]
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp as float."""
        import time
        return time.time()
    
    def clear_validation_cache(self, site_id: str = None) -> None:
        """Clear validation cache for specific site or all sites."""
        if site_id:
            if site_id in self._validation_cache:
                del self._validation_cache[site_id]
            if site_id in self._validation_timestamps:
                del self._validation_timestamps[site_id]
            self._logger.debug("Cleared validation cache", site_id=site_id)
        else:
            self._validation_cache.clear()
            self._validation_timestamps.clear()
            self._logger.debug("Cleared all validation cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get validation cache statistics."""
        current_time = self._get_current_timestamp()
        
        cache_stats = {
            "total_cached": len(self._validation_cache),
            "cache_ttl": self._cache_ttl,
            "sites": {}
        }
        
        for site_id in self._validation_cache:
            cache_stats["sites"][site_id] = {
                "cached": True,
                "age_seconds": self._get_cache_age(site_id),
                "is_valid": self._validation_cache[site_id].is_valid(),
                "expires_in": max(0, self._cache_ttl - self._get_cache_age(site_id))
            }
        
        return cache_stats
    
    def validate_scraper_class(self, scraper_class: Type[BaseSiteScraper]) -> ValidationResult:
        """Validate a scraper class implementation using comprehensive validation."""
        result = ValidationResult()
        
        # Use InterfaceValidator for interface compliance
        interface_result = InterfaceValidator.validate_scraper_interface(scraper_class)
        result.errors.extend(interface_result.errors)
        result.warnings.extend(interface_result.warnings)
        
        # Validate required files exist
        self._validate_required_files(scraper_class, result)
        
        # Load and validate configuration
        try:
            config = self._load_site_configuration(scraper_class)
            config_result = ConfigurationValidator.validate_site_config(config)
            result.errors.extend(config_result.errors)
            result.warnings.extend(config_result.warnings)
        except Exception as e:
            result.add_error(f"Configuration validation failed: {str(e)}")
        
        # Update overall validity
        if result.errors:
            result.valid = False
        
        return result
    
    def _validate_required_files(self, scraper_class: Type[BaseSiteScraper], result: ValidationResult) -> None:
        """Validate that required scraper files exist using FileValidator."""
        try:
            # Get the module path from the class
            module_path = scraper_class.__module__
            if not module_path:
                result.add_error("Cannot determine module path for scraper")
                return
            
            # Get the directory path
            import importlib
            module = importlib.import_module(module_path)
            scraper_dir = Path(module.__file__).parent
            
            # Use FileValidator for comprehensive file validation
            file_result = FileValidator.validate_required_files(scraper_dir)
            result.errors.extend(file_result.errors)
            result.warnings.extend(file_result.warnings)
            result.missing_files.extend(file_result.missing_files)
            result.invalid_selectors.extend(file_result.invalid_selectors)
        
        except Exception as e:
            result.add_error(f"Failed to validate required files: {str(e)}")
    
    def _load_site_configuration(self, scraper_class: Type[BaseSiteScraper]) -> dict:
        """Load site configuration from scraper module."""
        try:
            # Get the module path from the class
            module_path = scraper_class.__module__
            if not module_path:
                raise ValidationError("Cannot determine module path for scraper")
            
            # Import the module and get SITE_CONFIG
            import importlib
            module = importlib.import_module(module_path)
            
            if not hasattr(module, 'SITE_CONFIG'):
                raise ValidationError("SITE_CONFIG not found in scraper module")
            
            config = getattr(module, 'SITE_CONFIG')
            
            # Validate configuration structure
            return self._validate_site_configuration(config)
            
        except Exception as e:
            raise ValidationError(f"Failed to load site configuration: {str(e)}")
    
    def _validate_site_configuration(self, config: dict) -> dict:
        """Validate site configuration structure."""
        result = ValidationResult()
        
        # Check required fields
        required_fields = ['id', 'name', 'base_url', 'version', 'maintainer']
        for field in required_fields:
            if field not in config:
                result.add_error(f"Missing required configuration field: {field}")
            elif not config[field]:
                result.add_error(f"Configuration field '{field}' cannot be empty")
        
        # Validate field formats
        if 'id' in config:
            if not isinstance(config['id'], str):
                result.add_error("Site ID must be a string")
            elif not re.match(r'^[a-z0-9_]+$', config['id']):
                result.add_error("Site ID must contain only lowercase letters, numbers, and underscores")
        
        if 'name' in config:
            if not isinstance(config['name'], str):
                result.add_error("Site name must be a string")
            elif len(config['name'].strip()) == 0:
                result.add_error("Site name cannot be empty")
        
        if 'base_url' in config:
            if not isinstance(config['base_url'], str):
                result.add_error("Base URL must be a string")
            elif not (config['base_url'].startswith('http://') or config['base_url'].startswith('https://')):
                result.add_error("Base URL must start with http:// or https://")
        
        if 'version' in config:
            if not isinstance(config['version'], str):
                result.add_error("Version must be a string")
            elif not re.match(r'^\d+\.\d+\.\d+$', config['version']):
                result.add_error("Version must follow semantic versioning (e.g., 1.0.0)")
        
        if 'maintainer' in config:
            if not isinstance(config['maintainer'], str):
                result.add_error("Maintainer must be a string")
            elif len(config['maintainer'].strip()) == 0:
                result.add_error("Maintainer cannot be empty")
        
        # Validate optional fields
        if 'description' in config and config['description'] is not None:
            if not isinstance(config['description'], str):
                result.add_error("Description must be a string")
        
        if 'tags' in config and config['tags'] is not None:
            if not isinstance(config['tags'], list):
                result.add_error("Tags must be a list")
            else:
                for tag in config['tags']:
                    if not isinstance(tag, str):
                        result.add_error("All tags must be strings")
        
        if not result.is_valid():
            raise ValidationError(f"Configuration validation failed: {result.errors}")
        
        return config
