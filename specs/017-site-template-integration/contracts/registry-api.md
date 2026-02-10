# Registry API Contract

**Version**: 1.0  
**Feature**: 017-site-template-integration  
**Date**: 2025-01-29

## Overview

This contract defines the API interfaces for the Site Template Registry, providing centralized discovery, management, and orchestration of site scraper templates within the Scorewise framework.

## Core Interfaces

### IRegistryManager

Primary interface for registry operations and template management.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path

class IRegistryManager(ABC):
    """Primary interface for site template registry management."""
    
    @abstractmethod
    async def initialize_registry(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the registry with configuration.
        
        Args:
            config: Registry configuration
            
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    async def scan_and_register(self, scan_paths: List[str]) -> Dict[str, Any]:
        """
        Scan paths and automatically register discovered templates.
        
        Args:
            scan_paths: List of paths to scan for templates
            
        Returns:
            Dict[str, Any]: Scan results with registered templates
        """
        pass
    
    @abstractmethod
    async def get_registry_status(self) -> Dict[str, Any]:
        """
        Get current registry status and health.
        
        Returns:
            Dict[str, Any]: Registry status information
        """
        pass
    
    @abstractmethod
    async def refresh_registry(self) -> Dict[str, Any]:
        """
        Refresh registry by rescanning all discovery paths.
        
        Returns:
            Dict[str, Any]: Refresh results
        """
        pass
```

### ITemplateDiscovery

Interface for discovering templates in filesystem and other sources.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path

class ITemplateDiscovery(ABC):
    """Interface for discovering site templates."""
    
    @abstractmethod
    async def discover_templates_in_path(self, path: str) -> List[Dict[str, Any]]:
        """
        Discover templates in a specific path.
        
        Args:
            path: Filesystem path to search
            
        Returns:
            List[Dict[str, Any]]: List of discovered template metadata
        """
        pass
    
    @abstractmethod
    async def validate_template_structure(self, template_path: str) -> bool:
        """
        Validate template directory structure.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            bool: True if structure is valid
        """
        pass
    
    @abstractmethod
    async def extract_template_metadata(self, template_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from template directory.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Optional[Dict[str, Any]]: Template metadata or None if invalid
        """
        pass
    
    @abstractmethod
    async def watch_for_changes(self, paths: List[str]) -> None:
        """
        Watch paths for template changes and updates.
        
        Args:
            paths: List of paths to watch
        """
        pass
```

### ITemplateRegistry

Interface for storing and retrieving template information.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class ITemplateRegistry(ABC):
    """Interface for template storage and retrieval."""
    
    @abstractmethod
    async def register_template(self, template_metadata: Dict[str, Any]) -> bool:
        """
        Register a template in the registry.
        
        Args:
            template_metadata: Template metadata to register
            
        Returns:
            bool: True if registration successful
        """
        pass
    
    @abstractmethod
    async def unregister_template(self, template_name: str) -> bool:
        """
        Unregister a template from the registry.
        
        Args:
            template_name: Name of template to unregister
            
        Returns:
            bool: True if unregistration successful
        """
        pass
    
    @abstractmethod
    async def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get template metadata by name.
        
        Args:
            template_name: Name of template
            
        Returns:
            Optional[Dict[str, Any]]: Template metadata or None if not found
        """
        pass
    
    @abstractmethod
    async def list_templates(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List all registered templates with optional filters.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List[Dict[str, Any]]: List of template metadata
        """
        pass
    
    @abstractmethod
    async def search_templates(self, query: str, search_fields: List[str]) -> List[Dict[str, Any]]:
        """
        Search templates by query string.
        
        Args:
            query: Search query
            search_fields: Fields to search in
            
        Returns:
            List[Dict[str, Any]]: Matching templates
        """
        pass
    
    @abstractmethod
    async def get_templates_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get templates that support a specific domain.
        
        Args:
            domain: Domain to search for
            
        Returns:
            List[Dict[str, Any]]: Templates supporting the domain
        """
        pass
```

### ITemplateLoader

Interface for loading and instantiating templates.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.sites.base.site_scraper import BaseSiteScraper

class ITemplateLoader(ABC):
    """Interface for loading and instantiating templates."""
    
    @abstractmethod
    async def load_template(self, template_name: str, page: Any, selector_engine: Any) -> Optional[BaseSiteScraper]:
        """
        Load and instantiate a template.
        
        Args:
            template_name: Name of template to load
            page: Playwright page instance
            selector_engine: Selector engine instance
            
        Returns:
            Optional[BaseSiteScraper]: Loaded template instance or None if failed
        """
        pass
    
    @abstractmethod
    async def validate_template_dependencies(self, template_name: str) -> Dict[str, Any]:
        """
        Validate template dependencies.
        
        Args:
            template_name: Name of template to validate
            
        Returns:
            Dict[str, Any]: Dependency validation results
        """
        pass
    
    @abstractmethod
    async def get_template_instance_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about template instance requirements.
        
        Args:
            template_name: Name of template
            
        Returns:
            Optional[Dict[str, Any]]: Template instance information
        """
        pass
```

## Data Models

### RegistryMetadata

```python
from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime

@dataclass
class RegistryMetadata:
    """Registry metadata and status information."""
    registry_version: str
    total_templates: int
    active_templates: int
    last_updated: datetime
    discovery_paths: List[str]
    registry_config: Dict[str, Any]
    health_status: str
```

### TemplateMetadata

```python
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime

@dataclass
class TemplateMetadata:
    """Complete template metadata."""
    name: str
    version: str
    description: str
    author: str
    created_at: datetime
    updated_at: datetime
    framework_version: str
    site_domain: str
    supported_domains: List[str]
    template_path: str
    configuration_schema: Dict[str, Any]
    capabilities: List[str]
    dependencies: List[str]
    registration_date: datetime
    last_validated: Optional[datetime]
    validation_status: str
    health_status: str
```

### DiscoveryResult

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class DiscoveryResult:
    """Result of template discovery operation."""
    scanned_paths: List[str]
    discovered_templates: List[str]
    registered_templates: List[str]
    failed_registrations: List[Dict[str, Any]]
    discovery_errors: List[str]
    scan_duration: float
```

### RegistryStats

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class RegistryStats:
    """Registry statistics and metrics."""
    total_templates: int
    active_templates: int
    templates_by_domain: Dict[str, int]
    templates_by_version: Dict[str, int]
    validation_success_rate: float
    average_load_time: float
    registry_size_bytes: int
    last_scan_duration: float
```

## API Endpoints

### Registry Management

#### Initialize Registry
```http
POST /api/v1/registry/initialize
Content-Type: application/json

{
  "discovery_paths": ["/src/sites/github", "/src/sites/twitter"],
  "config": {
    "auto_refresh": true,
    "refresh_interval": 300,
    "validation_level": "strict"
  }
}

Response:
{
  "registry_id": "registry_123456789",
  "status": "initialized",
  "discovered_templates": 5,
  "registered_templates": 5
}
```

#### Get Registry Status
```http
GET /api/v1/registry/status

Response:
{
  "registry_metadata": {
    "registry_version": "1.0.0",
    "total_templates": 5,
    "active_templates": 4,
    "last_updated": "2025-01-29T23:38:00Z",
    "health_status": "healthy"
  },
  "registry_stats": {
    "validation_success_rate": 0.95,
    "average_load_time": 0.15,
    "templates_by_domain": {
      "github.com": 1,
      "twitter.com": 1,
      "wikipedia.org": 1
    }
  }
}
```

#### Refresh Registry
```http
POST /api/v1/registry/refresh

Response:
{
  "refresh_result": {
    "scanned_paths": ["/src/sites/github", "/src/sites/twitter"],
    "discovered_templates": 6,
    "registered_templates": 6,
    "failed_registrations": [],
    "scan_duration": 0.25
  }
}
```

### Template Discovery

#### Scan for Templates
```http
POST /api/v1/registry/discover
Content-Type: application/json

{
  "scan_paths": ["/src/sites/new_site"],
  "deep_scan": true,
  "validate_structure": true
}

Response:
{
  "discovery_result": {
    "scanned_paths": ["/src/sites/new_site"],
    "discovered_templates": ["new_site"],
    "registered_templates": ["new_site"],
    "failed_registrations": [],
    "discovery_errors": [],
    "scan_duration": 0.15
  }
}
```

#### Validate Template Structure
```http
POST /api/v1/registry/validate-structure
Content-Type: application/json

{
  "template_path": "/src/sites/github"
}

Response:
{
  "is_valid": true,
  "validation_errors": [],
  "structure_compliance": {
    "has_scraper_py": true,
    "has_selectors_dir": true,
    "has_config_py": true,
    "required_files_present": true
  }
}
```

### Template Registration

#### Register Template
```http
POST /api/v1/registry/templates
Content-Type: application/json

{
  "template_metadata": {
    "name": "github",
    "version": "1.0.0",
    "description": "GitHub repository scraper",
    "site_domain": "github.com",
    "template_path": "/src/sites/github"
  }
}

Response:
{
  "registration_id": "reg_123456789",
  "status": "registered",
  "template_name": "github",
  "registration_date": "2025-01-29T23:38:00Z"
}
```

#### Unregister Template
```http
DELETE /api/v1/registry/templates/{template_name}

Response:
{
  "status": "unregistered",
  "template_name": "github",
  "unregistration_date": "2025-01-29T23:38:00Z"
}
```

### Template Retrieval

#### Get Template
```http
GET /api/v1/registry/templates/{template_name}

Response:
{
  "template_metadata": {
    "name": "github",
    "version": "1.0.0",
    "description": "GitHub repository scraper",
    "author": "Scorewise Team",
    "site_domain": "github.com",
    "supported_domains": ["github.com", "api.github.com"],
    "capabilities": ["repository_extraction", "user_data", "search"],
    "validation_status": "valid",
    "health_status": "healthy"
  }
}
```

#### List Templates
```http
GET /api/v1/registry/templates?domain=github.com&status=active

Response:
{
  "templates": [
    {
      "name": "github",
      "version": "1.0.0",
      "site_domain": "github.com",
      "validation_status": "valid",
      "health_status": "healthy"
    }
  ],
  "total_count": 1,
  "page": 1,
  "per_page": 20
}
```

#### Search Templates
```http
POST /api/v1/registry/templates/search
Content-Type: application/json

{
  "query": "repository",
  "search_fields": ["name", "description", "capabilities"],
  "filters": {
    "validation_status": "valid",
    "health_status": "healthy"
  }
}

Response:
{
  "search_results": [
    {
      "name": "github",
      "version": "1.0.0",
      "relevance_score": 0.95,
      "matched_fields": ["description", "capabilities"]
    }
  ],
  "total_matches": 1,
  "search_duration": 0.05
}
```

#### Get Templates by Domain
```http
GET /api/v1/registry/templates/by-domain/{domain}

Response:
{
  "templates": [
    {
      "name": "github",
      "version": "1.0.0",
      "site_domain": "github.com",
      "supported_domains": ["github.com", "api.github.com"]
    }
  ],
  "domain": "github.com",
  "template_count": 1
}
```

### Template Loading

#### Load Template
```http
POST /api/v1/registry/templates/{template_name}/load
Content-Type: application/json

{
  "page_context": {
    "url": "https://github.com/scorewise/scraper"
  },
  "selector_engine_config": {
    "confidence_threshold": 0.8
  }
}

Response:
{
  "load_result": {
    "success": true,
    "template_instance_id": "instance_123456789",
    "load_time": 0.12,
    "integration_status": {
      "selectors_loaded": 15,
      "extraction_rules_loaded": 8,
      "bridge_status": "active"
    }
  }
}
```

#### Validate Template Dependencies
```http
GET /api/v1/registry/templates/{template_name}/dependencies

Response:
{
  "dependency_validation": {
    "all_dependencies_satisfied": true,
    "missing_dependencies": [],
    "version_conflicts": [],
    "dependency_details": {
      "framework_version": "1.0.0",
      "required_modules": ["playwright", "pyyaml"],
      "optional_modules": ["requests"]
    }
  }
}
```

## Event System

### Registry Events

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class RegistryEventType(Enum):
    REGISTRY_INITIALIZED = "registry_initialized"
    TEMPLATE_DISCOVERED = "template_discovered"
    TEMPLATE_REGISTERED = "template_registered"
    TEMPLATE_UNREGISTERED = "template_unregistered"
    TEMPLATE_VALIDATED = "template_validated"
    REGISTRY_REFRESHED = "registry_refreshed"
    REGISTRY_ERROR = "registry_error"

@dataclass
class RegistryEvent:
    """Registry lifecycle event."""
    event_type: RegistryEventType
    timestamp: datetime
    metadata: Dict[str, Any]
    template_name: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
```

### Discovery Events

```python
class DiscoveryEventType(Enum):
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    TEMPLATE_FOUND = "template_found"
    STRUCTURE_VALIDATED = "structure_validated"
    DISCOVERY_ERROR = "discovery_error"

@dataclass
class DiscoveryEvent:
    """Template discovery event."""
    event_type: DiscoveryEventType
    timestamp: datetime
    scan_path: str
    template_name: Optional[str] = None
    validation_result: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
```

## Configuration

### Registry Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "discovery": {
      "type": "object",
      "properties": {
        "scan_paths": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "default": ["/src/sites"]
        },
        "auto_refresh": {
          "type": "boolean",
          "default": true
        },
        "refresh_interval": {
          "type": "number",
          "default": 300,
          "minimum": 60
        },
        "deep_scan": {
          "type": "boolean",
          "default": false
        }
      }
    },
    "validation": {
      "type": "object",
      "properties": {
        "validation_level": {
          "enum": ["strict", "lenient", "disabled"],
          "default": "strict"
        },
        "auto_validate": {
          "type": "boolean",
          "default": true
        },
        "validation_timeout": {
          "type": "number",
          "default": 30
        }
      }
    },
    "storage": {
      "type": "object",
      "properties": {
        "storage_type": {
          "enum": ["memory", "file", "database"],
          "default": "memory"
        },
        "storage_path": {
          "type": "string",
          "default": "/data/registry"
        },
        "backup_enabled": {
          "type": "boolean",
          "default": true
        }
      }
    }
  }
}
```

## Error Handling

### Registry Error Types

```python
class RegistryError(Exception):
    """Base exception for registry-related errors."""
    pass

class TemplateNotFoundError(RegistryError):
    """Raised when template is not found in registry."""
    pass

class TemplateRegistrationError(RegistryError):
    """Raised when template registration fails."""
    pass

class DiscoveryError(RegistryError):
    """Raised when template discovery fails."""
    pass

class ValidationError(RegistryError):
    """Raised when template validation fails."""
    pass

class RegistryInitializationError(RegistryError):
    """Raised when registry initialization fails."""
    pass
```

### Error Response Format

```json
{
  "error": {
    "type": "TemplateRegistrationError",
    "message": "Failed to register template",
    "details": {
      "template_name": "github",
      "registration_errors": ["Invalid template structure"],
      "template_path": "/src/sites/github"
    },
    "timestamp": "2025-01-29T23:38:00Z",
    "request_id": "req_123456789"
  }
}
```

## Performance

### Caching Strategy

- Template metadata cached for 5 minutes
- Discovery results cached for 1 hour
- Validation results cached for 30 minutes
- Registry statistics cached for 1 minute

### Rate Limiting

- Registry operations: 100 requests per minute
- Template discovery: 10 scans per minute
- Template loading: 50 loads per minute

### Monitoring Metrics

- Registry initialization time
- Template discovery duration
- Registration success rate
- Template load performance
- Memory usage by registry
- Cache hit rates

## Security

### Access Control

- Registry read access: All authenticated users
- Registry write access: Administrators only
- Template registration: Authorized developers
- Template loading: Based on template permissions

### Input Validation

- All template paths validated against allowed directories
- Template metadata validated against schemas
- Search queries sanitized and limited
- File uploads restricted to allowed types

### Audit Logging

- All registry operations logged
- Template registration changes tracked
- Access attempts recorded
- Error events captured with context
