# Registry API Contract

**Feature**: 013-site-scraper-template  
**Date**: 2025-01-29  
**Purpose**: API specification for scraper registry and discovery system

## Registry Interface

### Core Registry Class

```python
from typing import Dict, List, Type, Optional
from .base.site_scraper import BaseSiteScraper
from .models import SiteConfiguration, ValidationResult

class ScraperRegistry:
    """Central registry for managing site scrapers."""
    
    def __init__(self):
        self._scrapers: Dict[str, Type[BaseSiteScraper]] = {}
        self._metadata: Dict[str, SiteConfiguration] = {}
        self._validation_cache: Dict[str, ValidationResult] = {}
    
    def register(self, site_id: str, scraper_class: Type[BaseSiteScraper]) -> None:
        """Register a scraper class with validation."""
        pass
    
    def get_scraper(self, site_id: str) -> Type[BaseSiteScraper]:
        """Get scraper class by site ID."""
        pass
    
    def list_scrapers(self) -> List[str]:
        """List all registered scraper IDs."""
        pass
    
    def get_metadata(self, site_id: str) -> SiteConfiguration:
        """Get site configuration metadata."""
        pass
    
    def validate_all(self) -> Dict[str, ValidationResult]:
        """Validate all registered scrapers."""
        pass
    
    def validate_scraper(self, site_id: str) -> ValidationResult:
        """Validate a specific scraper."""
        pass
    
    def unregister(self, site_id: str) -> None:
        """Remove a scraper from the registry."""
        pass
    
    def clear(self) -> None:
        """Clear all registered scrapers."""
        pass
```

### Registration Process

```python
def register(self, site_id: str, scraper_class: Type[BaseSiteScraper]) -> None:
    """
    Register a scraper class with comprehensive validation.
    
    Args:
        site_id: Unique identifier for the scraper
        scraper_class: Class implementing BaseSiteScraper interface
    
    Raises:
        RegistryError: If registration fails validation
    """
    # 1. Validate site_id uniqueness
    if site_id in self._scrapers:
        raise RegistryError(f"Site ID '{site_id}' already registered")
    
    # 2. Validate scraper class inheritance
    if not issubclass(scraper_class, BaseSiteScraper):
        raise RegistryError(f"Scraper class must inherit from BaseSiteScraper")
    
    # 3. Validate scraper implementation
    validation_result = self._validate_scraper_implementation(scraper_class)
    if not validation_result.is_valid():
        raise RegistryError(f"Scraper validation failed: {validation_result.errors}")
    
    # 4. Load and validate configuration
    config = self._load_site_configuration(scraper_class)
    if config.id != site_id:
        raise RegistryError(f"Site ID mismatch: config={config.id}, registered={site_id}")
    
    # 5. Register scraper
    self._scrapers[site_id] = scraper_class
    self._metadata[site_id] = config
    self._validation_cache[site_id] = validation_result
```

## Discovery API

### Auto-Discovery Interface

```python
class ScraperDiscovery:
    """Automatic discovery of site scrapers."""
    
    def __init__(self, registry: ScraperRegistry):
        self.registry = registry
    
    def discover_from_directory(self, sites_dir: str) -> None:
        """Discover scrapers from directory structure."""
        pass
    
    def discover_from_module(self, module_name: str) -> None:
        """Discover scrapers from Python module."""
        pass
    
    def discover_from_config(self, config_file: str) -> None:
        """Discover scrapers from configuration file."""
        pass
```

### Directory-Based Discovery

```python
def discover_from_directory(self, sites_dir: str) -> None:
    """
    Automatically discover and register scrapers from directory.
    
    Expected structure:
    sites_dir/
    ├── wikipedia/
    │   ├── __init__.py
    │   ├── scraper.py
    │   ├── flow.py
    │   ├── config.py
    │   └── selectors/
    │       └── *.yaml
    └── flashscore/
        └── ...
    """
    for site_dir in Path(sites_dir).iterdir():
        if site_dir.is_dir() and not site_dir.name.startswith('_'):
            try:
                scraper_module = self._load_site_module(site_dir.name)
                scraper_class = getattr(scraper_module, 'Scraper')
                site_id = scraper_class.site_id
                self.registry.register(site_id, scraper_class)
            except Exception as e:
                logger.warning(f"Failed to discover scraper in {site_dir}: {e}")
```

## Metadata API

### Site Configuration Access

```python
def get_metadata(self, site_id: str) -> SiteConfiguration:
    """
    Get site configuration metadata.
    
    Args:
        site_id: Unique identifier for the scraper
    
    Returns:
        SiteConfiguration object with site metadata
    
    Raises:
        RegistryError: If site_id is not registered
    """
    if site_id not in self._metadata:
        raise RegistryError(f"Site '{site_id}' not found in registry")
    return self._metadata[site_id]

def list_scrapers(self) -> List[str]:
    """
    List all registered scraper IDs.
    
    Returns:
        List of registered site IDs
    """
    return list(self._scrapers.keys())

def get_scraper_info(self, site_id: str) -> Dict[str, Any]:
    """
    Get comprehensive information about a scraper.
    
    Returns:
        Dictionary with scraper metadata and validation status
    """
    metadata = self.get_metadata(site_id)
    validation = self._validation_cache.get(site_id)
    scraper_class = self._scrapers[site_id]
    
    return {
        "site_id": metadata.id,
        "name": metadata.name,
        "base_url": metadata.base_url,
        "version": metadata.version,
        "maintainer": metadata.maintainer,
        "description": metadata.description,
        "tags": metadata.tags,
        "class_name": scraper_class.__name__,
        "module": scraper_class.__module__,
        "validation": {
            "valid": validation.is_valid() if validation else False,
            "errors": validation.errors if validation else [],
            "warnings": validation.warnings if validation else []
        }
    }
```

## Validation API

### Comprehensive Validation

```python
def validate_all(self) -> Dict[str, ValidationResult]:
    """
    Validate all registered scrapers.
    
    Returns:
        Dictionary mapping site_id to ValidationResult
    """
    results = {}
    for site_id in self._scrapers:
        results[site_id] = self.validate_scraper(site_id)
    return results

def validate_scraper(self, site_id: str) -> ValidationResult:
    """
    Validate a specific scraper implementation.
    
    Args:
        site_id: Unique identifier for the scraper
    
    Returns:
        ValidationResult with detailed validation status
    """
    if site_id not in self._scrapers:
        result = ValidationResult()
        result.add_error(f"Site '{site_id}' not found in registry")
        return result
    
    # Check cache first
    if site_id in self._validation_cache:
        return self._validation_cache[site_id]
    
    # Perform validation
    scraper_class = self._scrapers[site_id]
    result = self._validate_scraper_implementation(scraper_class)
    
    # Cache result
    self._validation_cache[site_id] = result
    return result
```

### Implementation Validation

```python
def _validate_scraper_implementation(self, scraper_class: Type[BaseSiteScraper]) -> ValidationResult:
    """Validate scraper class implementation."""
    result = ValidationResult()
    
    # Check required class attributes
    required_attrs = ['site_id', 'site_name', 'base_url']
    for attr in required_attrs:
        if not hasattr(scraper_class, attr):
            result.add_error(f"Missing required class attribute: {attr}")
        elif getattr(scraper_class, attr) is None:
            result.add_error(f"Required class attribute '{attr}' cannot be None")
    
    # Check required methods
    required_methods = ['navigate', 'scrape', 'normalize']
    for method in required_methods:
        if not hasattr(scraper_class, method):
            result.add_error(f"Missing required method: {method}")
        elif not callable(getattr(scraper_class, method)):
            result.add_error(f"Attribute '{method}' is not callable")
    
    # Check method signatures (basic)
    try:
        import inspect
        navigate_sig = inspect.signature(scraper_class.navigate)
        if navigate_sig.parameters:
            result.add_warning("navigate() method should take no parameters besides self")
    except Exception:
        result.add_warning("Could not validate navigate() method signature")
    
    return result
```

## Error Handling

### Registry Exceptions

```python
class RegistryError(Exception):
    """Base exception for registry errors."""
    pass

class DuplicateSiteError(RegistryError):
    """Raised when attempting to register duplicate site ID."""
    pass

class SiteNotFoundError(RegistryError):
    """Raised when requested site ID is not found."""
    pass

class ValidationError(RegistryError):
    """Raised when scraper validation fails."""
    pass

class ConfigurationError(RegistryError):
    """Raised when site configuration is invalid."""
    pass
```

### Error Response Format

```python
{
    "error_type": "RegistryError",
    "message": "Site 'wikipedia' not found in registry",
    "site_id": "wikipedia",
    "timestamp": "2025-01-29T10:30:00Z",
    "available_sites": ["flashscore", "example"],
    "suggestions": ["Check site ID spelling", "Verify site is registered"]
}
```

## Performance API

### Caching and Optimization

```python
class OptimizedRegistry(ScraperRegistry):
    """Registry with performance optimizations."""
    
    def __init__(self):
        super().__init__()
        self._lookup_cache: Dict[str, Type[BaseSiteScraper]] = {}
        self._metadata_cache: Dict[str, SiteConfiguration] = {}
    
    def get_scraper(self, site_id: str) -> Type[BaseSiteScraper]:
        """Get scraper class with caching."""
        if site_id in self._lookup_cache:
            return self._lookup_cache[site_id]
        
        scraper_class = super().get_scraper(site_id)
        self._lookup_cache[site_id] = scraper_class
        return scraper_class
    
    def clear_cache(self, site_id: Optional[str] = None) -> None:
        """Clear cache for specific site or all sites."""
        if site_id:
            self._lookup_cache.pop(site_id, None)
            self._metadata_cache.pop(site_id, None)
        else:
            self._lookup_cache.clear()
            self._metadata_cache.clear()
```

## Integration API

### External Integration Points

```python
class RegistryIntegration:
    """Integration helpers for external systems."""
    
    def __init__(self, registry: ScraperRegistry):
        self.registry = registry
    
    def export_config(self, output_file: str) -> None:
        """Export registry configuration to file."""
        pass
    
    def import_config(self, input_file: str) -> None:
        """Import registry configuration from file."""
        pass
    
    def generate_docs(self, output_dir: str) -> None:
        """Generate documentation for registered scrapers."""
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """Perform registry health check."""
        return {
            "total_scrapers": len(self.registry.list_scrapers()),
            "valid_scrapers": sum(1 for v in self.registry.validate_all().values() if v.is_valid()),
            "validation_errors": [
                f"{site_id}: {', '.join(result.errors)}"
                for site_id, result in self.registry.validate_all().items()
                if not result.is_valid()
            ]
        }
```
