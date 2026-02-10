# Template API Contract

**Version**: 1.0  
**Feature**: 017-site-template-integration  
**Date**: 2025-01-29

## Overview

This contract defines the API interfaces for the Site Template Integration Framework, enabling standardized creation and management of site scrapers that leverage existing Scorewise framework components.

## Core Interfaces

### ISiteTemplate

Interface for site template implementations.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.sites.base.site_scraper import BaseSiteScraper
from src.selectors.context import DOMContext

class ISiteTemplate(ABC):
    """Base interface for site scraper templates."""
    
    @abstractmethod
    async def initialize(self, page: Any, selector_engine: Any) -> bool:
        """
        Initialize the template with framework components.
        
        Args:
            page: Playwright page instance
            selector_engine: Framework selector engine instance
            
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """
        Execute scraping using template configuration.
        
        Args:
            **kwargs: Scraping parameters
            
        Returns:
            Dict[str, Any]: Scraped data
        """
        pass
    
    @abstractmethod
    def get_template_info(self) -> Dict[str, Any]:
        """
        Get template metadata and capabilities.
        
        Returns:
            Dict[str, Any]: Template information
        """
        pass
```

### IIntegrationBridge

Interface for framework integration bridges.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class IIntegrationBridge(ABC):
    """Interface for connecting site components with framework infrastructure."""
    
    @abstractmethod
    async def initialize_complete_integration(self) -> bool:
        """
        Initialize complete framework integration.
        
        Returns:
            bool: True if integration successful
        """
        pass
    
    @abstractmethod
    async def load_selectors(self) -> bool:
        """
        Load YAML selectors into existing selector engine.
        
        Returns:
            bool: True if selectors loaded successfully
        """
        pass
    
    @abstractmethod
    async def setup_extraction_rules(self) -> bool:
        """
        Setup extraction rules using existing extractor module.
        
        Returns:
            bool: True if rules setup successful
        """
        pass
    
    @abstractmethod
    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get current integration status and health.
        
        Returns:
            Dict[str, Any]: Integration status information
        """
        pass
```

### ISelectorLoader

Interface for YAML selector loading and management.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path

class ISelectorLoader(ABC):
    """Interface for loading YAML selectors into existing selector engine."""
    
    @abstractmethod
    async def load_site_selectors(self, site_name: str) -> bool:
        """
        Load selectors for a specific site.
        
        Args:
            site_name: Name of the site to load selectors for
            
        Returns:
            bool: True if selectors loaded successfully
        """
        pass
    
    @abstractmethod
    async def register_selector(self, selector_name: str, selector_config: Dict[str, Any]) -> bool:
        """
        Register a single selector with the selector engine.
        
        Args:
            selector_name: Name of the selector
            selector_config: Selector configuration from YAML
            
        Returns:
            bool: True if registration successful
        """
        pass
    
    @abstractmethod
    def get_loaded_selectors(self) -> List[str]:
        """
        Get list of loaded selector names.
        
        Returns:
            List[str]: List of selector names
        """
        pass
    
    @abstractmethod
    async def validate_selector_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate selector configuration.
        
        Args:
            config: Selector configuration to validate
            
        Returns:
            bool: True if configuration is valid
        """
        pass
```

### ISiteRegistry

Interface for site template registry and discovery.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class ISiteRegistry(ABC):
    """Interface for discovering and managing site templates."""
    
    @abstractmethod
    async def discover_templates(self, discovery_paths: List[str]) -> List[str]:
        """
        Discover available site templates.
        
        Args:
            discovery_paths: List of paths to search for templates
            
        Returns:
            List[str]: List of discovered template names
        """
        pass
    
    @abstractmethod
    async def register_template(self, template_name: str, template_path: str) -> bool:
        """
        Register a site template in the registry.
        
        Args:
            template_name: Name of the template
            template_path: Path to template implementation
            
        Returns:
            bool: True if registration successful
        """
        pass
    
    @abstractmethod
    async def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get template metadata by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Optional[Dict[str, Any]]: Template metadata or None if not found
        """
        pass
    
    @abstractmethod
    async def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all registered templates.
        
        Returns:
            List[Dict[str, Any]]: List of template metadata
        """
        pass
    
    @abstractmethod
    async def get_template_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get template by supported domain.
        
        Args:
            domain: Domain to search for
            
        Returns:
            Optional[Dict[str, Any]]: Template metadata or None if not found
        """
        pass
```

### IValidationFramework

Interface for template validation and compliance checking.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class IValidationFramework(ABC):
    """Interface for validating templates and framework compliance."""
    
    @abstractmethod
    async def validate_template(self, template_path: str) -> Dict[str, Any]:
        """
        Validate a complete template.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Validation results
        """
        pass
    
    @abstractmethod
    async def validate_selectors(self, selector_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate YAML selector configurations.
        
        Args:
            selector_configs: List of selector configurations
            
        Returns:
            Dict[str, Any]: Validation results
        """
        pass
    
    @abstractmethod
    async def validate_extraction_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate extraction rule configurations.
        
        Args:
            rules: List of extraction rules
            
        Returns:
            Dict[str, Any]: Validation results
        """
        pass
    
    @abstractmethod
    async def check_framework_compliance(self, template_path: str) -> Dict[str, Any]:
        """
        Check template compliance with framework constitution.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Compliance check results
        """
        pass
```

## Data Transfer Objects

### TemplateInfo

```python
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime

@dataclass
class TemplateInfo:
    """Template metadata and capabilities."""
    name: str
    version: str
    description: str
    author: str
    created_at: datetime
    updated_at: datetime
    framework_version: str
    site_domain: str
    supported_domains: List[str]
    configuration_schema: Dict[str, Any]
    capabilities: List[str]
    dependencies: List[str]
```

### ValidationResult

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ValidationResult:
    """Validation result for templates and components."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    compliance_score: float
    validation_details: Dict[str, Any]
```

### IntegrationStatus

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class IntegrationStatus:
    """Status of framework integration."""
    is_integrated: bool
    selector_count: int
    extraction_rule_count: int
    bridge_status: str
    last_updated: datetime
    health_metrics: Dict[str, Any]
    error_details: Optional[Dict[str, Any]]
```

## API Endpoints

### Template Management

#### Create Template
```http
POST /api/v1/templates
Content-Type: application/json

{
  "name": "github",
  "version": "1.0.0",
  "description": "GitHub repository scraper",
  "site_domain": "github.com",
  "configuration": {}
}

Response:
{
  "template_id": "github-1.0.0",
  "status": "created",
  "validation_result": {...}
}
```

#### Get Template
```http
GET /api/v1/templates/{template_name}

Response:
{
  "template_info": {...},
  "integration_status": {...},
  "validation_result": {...}
}
```

#### List Templates
```http
GET /api/v1/templates

Response:
{
  "templates": [...],
  "total_count": 10,
  "page": 1,
  "per_page": 20
}
```

### Registry Operations

#### Discover Templates
```http
POST /api/v1/registry/discover
Content-Type: application/json

{
  "discovery_paths": ["/src/sites/github", "/src/sites/twitter"]
}

Response:
{
  "discovered_templates": ["github", "twitter"],
  "discovery_errors": []
}
```

#### Register Template
```http
POST /api/v1/registry/register
Content-Type: application/json

{
  "template_name": "github",
  "template_path": "/src/sites/github"
}

Response:
{
  "registration_status": "success",
  "template_id": "github-1.0.0"
}
```

### Validation Operations

#### Validate Template
```http
POST /api/v1/validation/template
Content-Type: application/json

{
  "template_path": "/src/sites/github"
}

Response:
{
  "validation_result": {
    "is_valid": true,
    "errors": [],
    "warnings": ["Consider adding more selectors"],
    "compliance_score": 0.95
  }
}
```

#### Check Compliance
```http
POST /api/v1/validation/compliance
Content-Type: application/json

{
  "template_path": "/src/sites/github"
}

Response:
{
  "compliance_result": {
    "constitutional_compliance": true,
    "violations": [],
    "recommendations": []
  }
}
```

## Event System

### Template Events

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class TemplateEventType(Enum):
    TEMPLATE_CREATED = "template_created"
    TEMPLATE_UPDATED = "template_updated"
    TEMPLATE_VALIDATED = "template_validated"
    TEMPLATE_REGISTERED = "template_registered"
    TEMPLATE_ERROR = "template_error"

@dataclass
class TemplateEvent:
    """Template lifecycle event."""
    event_type: TemplateEventType
    template_name: str
    timestamp: datetime
    metadata: Dict[str, Any]
    error_details: Optional[Dict[str, Any]] = None
```

### Integration Events

```python
class IntegrationEventType(Enum):
    BRIDGE_INITIALIZED = "bridge_initialized"
    SELECTORS_LOADED = "selectors_loaded"
    EXTRACTION_RULES_SETUP = "extraction_rules_setup"
    INTEGRATION_ERROR = "integration_error"

@dataclass
class IntegrationEvent:
    """Framework integration event."""
    event_type: IntegrationEventType
    template_name: str
    timestamp: datetime
    integration_details: Dict[str, Any]
    error_details: Optional[Dict[str, Any]] = None
```

## Error Handling

### Error Types

```python
class TemplateError(Exception):
    """Base exception for template-related errors."""
    pass

class TemplateNotFoundError(TemplateError):
    """Raised when template is not found."""
    pass

class TemplateValidationError(TemplateError):
    """Raised when template validation fails."""
    pass

class IntegrationError(TemplateError):
    """Raised when framework integration fails."""
    pass

class RegistryError(TemplateError):
    """Raised when registry operations fail."""
    pass
```

### Error Response Format

```json
{
  "error": {
    "type": "TemplateValidationError",
    "message": "Template validation failed",
    "details": {
      "validation_errors": ["Invalid YAML syntax"],
      "template_path": "/src/sites/github"
    },
    "timestamp": "2025-01-29T23:38:00Z",
    "request_id": "req_123456789"
  }
}
```

## Configuration

### Template Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "template_settings": {
      "type": "object",
      "properties": {
        "auto_load_selectors": {
          "type": "boolean",
          "default": true
        },
        "validation_level": {
          "enum": ["strict", "lenient", "disabled"],
          "default": "strict"
        },
        "performance_mode": {
          "enum": ["development", "production"],
          "default": "development"
        }
      }
    },
    "integration_settings": {
      "type": "object",
      "properties": {
        "bridge_timeout": {
          "type": "number",
          "default": 30
        },
        "retry_attempts": {
          "type": "integer",
          "default": 3
        },
        "health_check_interval": {
          "type": "number",
          "default": 60
        }
      }
    }
  }
}
```

## Versioning

### API Versioning

- Current version: v1.0
- Version format: semantic versioning (major.minor.patch)
- Backward compatibility maintained within major versions
- Breaking changes require major version increment

### Template Versioning

- Template versions follow semantic versioning
- Framework compatibility specified in template metadata
- Migration paths provided for major version changes

## Security

### Authentication

- API key authentication for management endpoints
- Template-specific access controls
- Audit logging for all operations

### Authorization

- Role-based access control (RBAC)
- Template creation and modification permissions
- Registry operation restrictions

### Input Validation

- All inputs validated against schemas
- YAML content sanitized before parsing
- File path validation for security

## Performance

### Rate Limiting

- API rate limiting: 100 requests per minute
- Template validation: 10 validations per minute
- Registry operations: 50 operations per minute

### Caching

- Template metadata cached for 5 minutes
- Validation results cached for 1 hour
- Registry state cached until changes detected

### Monitoring

- API response time monitoring
- Template performance metrics
- Integration health checks
