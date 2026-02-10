# Modular Template API Contracts

**Created**: 2025-01-29  
**Purpose**: API specifications for enhanced modular template system

## Component Management API

### Component Registration

**Endpoint**: `POST /api/components/register`

**Request**:
```json
{
  "component_id": "oauth_auth_v1",
  "name": "OAuth Authentication",
  "version": "1.0.0",
  "component_type": "flow",
  "description": "OAuth 2.0 authentication flow",
  "entry_point": "components.auth.oauth:OAuthFlow",
  "dependencies": ["rate_limiter_v1"],
  "metadata": {
    "author": "System",
    "tags": ["authentication", "oauth", "security"],
    "async_compatible": true
  }
}
```

**Response**:
```json
{
  "success": true,
  "component_id": "oauth_auth_v1",
  "registration_time": "2025-01-29T18:30:00Z",
  "validation_results": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  }
}
```

### Component Discovery

**Endpoint**: `GET /api/components/discover`

**Query Parameters**:
- `type`: Component type filter (flow, processor, validator)
- `tags`: Tag filter (comma-separated)
- `compatible_with`: Version compatibility filter

**Response**:
```json
{
  "components": [
    {
      "component_id": "oauth_auth_v1",
      "name": "OAuth Authentication",
      "version": "1.0.0",
      "component_type": "flow",
      "description": "OAuth 2.0 authentication flow",
      "tags": ["authentication", "oauth", "security"],
      "metadata": {
        "async_compatible": true,
        "dependencies": ["rate_limiter_v1"]
      }
    }
  ],
  "total_count": 1,
  "page": 1,
  "per_page": 20
}
```

### Component Loading

**Endpoint**: `POST /api/components/{component_id}/load`

**Request**:
```json
{
  "configuration": {
    "oauth_provider": "google",
    "client_id": "your-client-id",
    "redirect_uri": "https://example.com/callback"
  },
  "context": {
    "environment": "prod",
    "session_id": "session_123"
  }
}
```

**Response**:
```json
{
  "success": true,
  "instance_id": "oauth_auth_v1_instance_456",
  "load_time_ms": 45,
  "status": "loaded",
  "capabilities": [
    "oauth2_flow",
    "token_refresh",
    "session_management"
  ]
}
```

## Configuration Management API

### Configuration Loading

**Endpoint**: `GET /api/config/{site_id}/{environment}`

**Response**:
```json
{
  "site_id": "wikipedia",
  "environment": "prod",
  "configuration": {
    "base_url": "https://en.wikipedia.org",
    "rate_limit": {
      "requests_per_minute": 60,
      "burst_size": 10
    },
    "stealth": {
      "user_agent_rotation": true,
      "mouse_movement": true,
      "randomized_timing": true
    },
    "feature_flags": {
      "enable_search_suggestions": true,
      "enable_article_cache": false
    }
  },
  "schema_version": "1.2.0",
  "last_modified": "2025-01-29T17:00:00Z"
}
```

### Configuration Validation

**Endpoint**: `POST /api/config/validate`

**Request**:
```json
{
  "site_id": "wikipedia",
  "environment": "prod",
  "configuration": {
    "base_url": "https://en.wikipedia.org",
    "rate_limit": {
      "requests_per_minute": 60
    }
  }
}
```

**Response**:
```json
{
  "is_valid": true,
  "validation_time_ms": 12,
  "errors": [],
  "warnings": [
    {
      "path": "stealth.mouse_movement",
      "message": "Stealth setting not specified, using default"
    }
  ],
  "schema_version": "1.2.0"
}
```

### Configuration Update

**Endpoint**: `PUT /api/config/{site_id}/{environment}`

**Request**:
```json
{
  "configuration": {
    "rate_limit": {
      "requests_per_minute": 120
    },
    "feature_flags": {
      "enable_search_suggestions": false
    }
  },
  "update_reason": "Performance optimization"
}
```

**Response**:
```json
{
  "success": true,
  "updated_fields": ["rate_limit.requests_per_minute", "feature_flags.enable_search_suggestions"],
  "validation_results": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  },
  "applied_at": "2025-01-29T18:45:00Z"
}
```

## Plugin Management API

### Plugin Discovery

**Endpoint**: `GET /api/plugins/discover`

**Response**:
```json
{
  "plugins": [
    {
      "plugin_id": "advanced_data_validator",
      "name": "Advanced Data Validator",
      "version": "2.1.0",
      "description": "Enhanced data validation with custom rules",
      "entry_point": "plugins.validator.advanced:AdvancedValidator",
      "permissions": ["read_data", "write_logs"],
      "dependencies": ["pydantic>=2.0.0"],
      "author": "ThirdParty",
      "status": "available"
    }
  ],
  "total_count": 1
}
```

### Plugin Installation

**Endpoint**: `POST /api/plugins/{plugin_id}/install`

**Request**:
```json
{
  "configuration": {
    "validation_rules": "strict",
    "log_level": "INFO"
  },
  "permissions_granted": ["read_data", "write_logs"]
}
```

**Response**:
```json
{
  "success": true,
  "instance_id": "advanced_data_validator_instance_789",
  "installation_time_ms": 120,
  "status": "installed",
  "hooks_registered": [
    "pre_process",
    "post_process",
    "validation_failed"
  ]
}
```

### Plugin Execution Hook

**Endpoint**: `POST /api/plugins/{instance_id}/hook/{hook_name}`

**Request**:
```json
{
  "hook_name": "pre_process",
  "context": {
    "site_id": "wikipedia",
    "operation": "search",
    "data": {
      "query": "python programming"
    }
  },
  "metadata": {
    "correlation_id": "corr_123",
    "timestamp": "2025-01-29T18:50:00Z"
  }
}
```

**Response**:
```json
{
  "success": true,
  "hook_result": {
    "action": "continue",
    "modified_data": {
      "query": "python programming",
      "validated": true
    },
    "execution_time_ms": 15,
    "logs": [
      "Data validation passed",
      "Query sanitized successfully"
    ]
  }
}
```

## Template Management API

### Template Instantiation

**Endpoint**: `POST /api/templates/instantiate`

**Request**:
```json
{
  "template_name": "modular_site_template",
  "site_config": {
    "site_id": "new_site",
    "site_name": "New Website",
    "base_url": "https://example.com"
  },
  "components": [
    {
      "component_id": "oauth_auth_v1",
      "configuration": {
        "oauth_provider": "github"
      }
    },
    {
      "component_id": "pagination_flow_v1",
      "configuration": {
        "max_pages": 10,
        "page_size": 20
      }
    }
  ],
  "target_directory": "/tmp/new_site_scraper"
}
```

**Response**:
```json
{
  "success": true,
  "instance_id": "new_site_instance_001",
  "generated_files": [
    "scraper.py",
    "flows/search_flow.py",
    "flows/login_flow.py",
    "config/base.py",
    "config/prod.py",
    "processors/normalizer.py",
    "validators/config_validator.py"
  ],
  "components_loaded": 2,
  "instantiation_time_ms": 250,
  "validation_results": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  }
}
```

### Template Validation

**Endpoint**: `POST /api/templates/validate`

**Request**:
```json
{
  "template_directory": "/tmp/new_site_scraper",
  "validation_level": "strict"
}
```

**Response**:
```json
{
  "is_valid": true,
  "validation_time_ms": 85,
  "results": {
    "structure": {
      "valid": true,
      "errors": [],
      "warnings": []
    },
    "components": {
      "valid": true,
      "loaded": 2,
      "errors": [],
      "warnings": []
    },
    "configuration": {
      "valid": true,
      "errors": [],
      "warnings": [
        "No production configuration found"
      ]
    },
    "dependencies": {
      "valid": true,
      "satisfied": 2,
      "missing": [],
      "conflicts": []
    }
  }
}
```

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "COMPONENT_NOT_FOUND",
    "message": "Component 'invalid_component' not found in registry",
    "details": {
      "component_id": "invalid_component",
      "available_components": ["oauth_auth_v1", "pagination_flow_v1"]
    },
    "timestamp": "2025-01-29T18:55:00Z",
    "correlation_id": "corr_456"
  }
}
```

### Error Codes

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| COMPONENT_NOT_FOUND | Component not found in registry | 404 |
| COMPONENT_LOAD_FAILED | Failed to load component | 500 |
| CONFIG_VALIDATION_FAILED | Configuration validation failed | 400 |
| PLUGIN_INSTALL_FAILED | Plugin installation failed | 500 |
| PLUGIN_PERMISSION_DENIED | Insufficient permissions for plugin | 403 |
| TEMPLATE_INSTANTIATION_FAILED | Template instantiation failed | 500 |
| DEPENDENCY_NOT_SATISFIED | Component dependencies not satisfied | 400 |
| VERSION_INCOMPATIBLE | Component version incompatible | 400 |

## Performance Metrics

### Component Performance

**Endpoint**: `GET /api/components/{component_id}/metrics`

**Response**:
```json
{
  "component_id": "oauth_auth_v1",
  "metrics": {
    "load_time_ms": {
      "average": 45,
      "min": 32,
      "max": 78,
      "p95": 65
    },
    "execution_time_ms": {
      "average": 120,
      "min": 85,
      "max": 200,
      "p95": 165
    },
    "success_rate": 0.98,
    "error_rate": 0.02,
    "instances_active": 5,
    "total_executions": 1250
  },
  "period": "24h"
}
```

### System Performance

**Endpoint**: `GET /api/system/metrics`

**Response**:
```json
{
  "system_metrics": {
    "components_registered": 15,
    "components_loaded": 8,
    "plugins_installed": 3,
    "templates_created": 12,
    "active_scrapers": 5,
    "memory_usage_mb": 256,
    "cpu_usage_percent": 12.5
  },
  "performance": {
    "average_component_load_time_ms": 38,
    "average_configuration_load_time_ms": 12,
    "average_plugin_install_time_ms": 95,
    "system_response_time_ms": 25
  }
}
```

**Status**: ✅ API contracts complete, ready for implementation
