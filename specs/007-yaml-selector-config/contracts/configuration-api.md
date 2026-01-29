# Configuration API Contracts

**Date**: 2025-01-27  
**Feature**: YAML-Based Selector Configuration System  
**Phase**: 1 - Design & Contracts

## API Overview

This document defines the internal API contracts for the YAML-based selector configuration system. These contracts define the interfaces between configuration components and the existing Selector Engine.

## Core Interfaces

### IConfigurationLoader

Interface for loading and validating YAML configuration files.

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pathlib import Path

class IConfigurationLoader(ABC):
    """Interface for loading YAML selector configurations."""
    
    @abstractmethod
    async def load_configuration(self, file_path: Path) -> SelectorConfiguration:
        """Load and validate a single YAML configuration file."""
        pass
    
    @abstractmethod
    async def load_configurations_recursive(self, root_path: Path) -> Dict[str, SelectorConfiguration]:
        """Load all YAML configurations from directory tree."""
        pass
    
    @abstractmethod
    def validate_configuration(self, config: SelectorConfiguration) -> ValidationResult:
        """Validate a configuration against schema."""
        pass
    
    @abstractmethod
    async def reload_configuration(self, file_path: Path) -> Optional[SelectorConfiguration]:
        """Reload a configuration file if it has changed."""
        pass
```

### IInheritanceResolver

Interface for resolving configuration inheritance.

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class IInheritanceResolver(ABC):
    """Interface for resolving configuration inheritance."""
    
    @abstractmethod
    async def resolve_inheritance_chain(self, config_path: str) -> InheritanceChain:
        """Resolve the complete inheritance chain for a configuration."""
        pass
    
    @abstractmethod
    def merge_context_defaults(self, parents: List[ContextDefaults]) -> ContextDefaults:
        """Merge context defaults from parent configurations."""
        pass
    
    @abstractmethod
    def merge_validation_defaults(self, parents: List[ValidationDefaults]) -> ValidationDefaults:
        """Merge validation defaults from parent configurations."""
        pass
    
    @abstractmethod
    def resolve_strategy_template(self, template_name: str, chain: InheritanceChain) -> StrategyTemplate:
        """Resolve a strategy template from the inheritance chain."""
        pass
    
    @abstractmethod
    def detect_circular_references(self, config_path: str) -> List[str]:
        """Detect circular inheritance references."""
        pass
```

### ISemanticIndex

Interface for semantic selector indexing and lookup.

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class ISemanticIndex(ABC):
    """Interface for semantic selector indexing."""
    
    @abstractmethod
    async def build_index(self, configurations: Dict[str, SelectorConfiguration]) -> Dict[str, SemanticIndexEntry]:
        """Build semantic index from loaded configurations."""
        pass
    
    @abstractmethod
    def lookup_selector(self, semantic_name: str, context: Optional[str] = None) -> Optional[SemanticIndexEntry]:
        """Look up a selector by semantic name."""
        pass
    
    @abstractmethod
    def find_conflicts(self) -> Dict[str, List[SemanticIndexEntry]]:
        """Find conflicting selector names."""
        pass
    
    @abstractmethod
    async def update_index(self, file_path: str, config: SelectorConfiguration) -> None:
        """Update index for a specific configuration."""
        pass
    
    @abstractmethod
    async def remove_from_index(self, file_path: str) -> None:
        """Remove entries for a specific configuration."""
        pass
```

### IConfigurationWatcher

Interface for monitoring configuration file changes.

```python
from abc import ABC, abstractmethod
from typing import Callable, Set

class IConfigurationWatcher(ABC):
    """Interface for monitoring configuration file changes."""
    
    @abstractmethod
    async def start_watching(self, root_path: Path) -> None:
        """Start monitoring configuration files for changes."""
        pass
    
    @abstractmethod
    async def stop_watching(self) -> None:
        """Stop monitoring configuration files."""
        pass
    
    @abstractmethod
    def set_change_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for file change events."""
        pass
    
    @abstractmethod
    def get_watched_files(self) -> Set[str]:
        """Get set of currently watched files."""
        pass
```

## Enhanced Selector Engine Integration

### EnhancedSelectorRegistry

Extended registry with configuration system integration.

```python
class EnhancedSelectorRegistry:
    """Enhanced selector registry with YAML configuration support."""
    
    def __init__(self, 
                 config_loader: IConfigurationLoader,
                 inheritance_resolver: IInheritanceResolver,
                 semantic_index: ISemanticIndex,
                 config_watcher: IConfigurationWatcher):
        """Initialize enhanced registry with configuration components."""
        pass
    
    async def initialize_from_config(self, config_root: Path) -> None:
        """Initialize registry from YAML configuration files."""
        pass
    
    def get_selector_by_name(self, semantic_name: str, context: Optional[str] = None) -> Optional[SemanticSelector]:
        """Get selector by semantic name using configuration system."""
        pass
    
    async def reload_configurations(self) -> None:
        """Reload all configurations and update registry."""
        pass
    
    def get_configuration_stats(self) -> ConfigurationStats:
        """Get statistics about loaded configurations."""
        pass
```

### EnhancedSelectorResolver

Extended resolver with context awareness.

```python
class EnhancedSelectorResolver:
    """Enhanced selector resolver with configuration system integration."""
    
    def __init__(self, registry: EnhancedSelectorRegistry):
        """Initialize resolver with enhanced registry."""
        pass
    
    async def resolve_selector(self, 
                             semantic_name: str, 
                             context: ResolutionContext,
                             dom_context: Optional[DOMContext] = None) -> SelectorResult:
        """Resolve selector using configuration system."""
        pass
    
    def get_available_selectors(self, context: str) -> List[str]:
        """Get all available selectors for a context."""
        pass
    
    def validate_selector_context(self, semantic_name: str, context: str) -> bool:
        """Validate that selector is appropriate for context."""
        pass
```

## Data Transfer Objects

### ConfigurationStats

Statistics about the configuration system.

```python
@dataclass
class ConfigurationStats:
    """Statistics about loaded configurations."""
    total_configurations: int
    total_selectors: int
    total_templates: int
    inheritance_chains: int
    index_entries: int
    last_reload: str
    error_count: int
    loading_time_ms: float
```

### ValidationResult

Result of configuration validation.

```python
@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    schema_version: str
    validation_time_ms: float
```

### SelectorResult

Result of selector resolution.

```python
@dataclass
class SelectorResult:
    """Result of selector resolution."""
    selector: SemanticSelector
    resolved_strategies: List[StrategyDefinition]
    confidence_score: float
    resolution_time_ms: float
    context_used: str
    template_applied: Optional[str]
```

### ResolutionContext

Context for selector resolution.

```python
@dataclass
class ResolutionContext:
    """Context for selector resolution operations."""
    current_page: str
    current_section: str
    tab_context: Optional[str]
    navigation_history: List[str]
    correlation_id: str
```

## Event Contracts

### ConfigurationEvent

Base class for configuration events.

```python
@dataclass
class ConfigurationEvent:
    """Base class for configuration system events."""
    event_type: str
    timestamp: str
    file_path: str
    correlation_id: str
```

### ConfigurationLoadedEvent

Event fired when configuration is loaded.

```python
@dataclass
class ConfigurationLoadedEvent(ConfigurationEvent):
    """Event fired when configuration is successfully loaded."""
    selector_count: int
    template_count: int
    loading_time_ms: float
```

### ConfigurationErrorEvent

Event fired when configuration error occurs.

```python
@dataclass
class ConfigurationErrorEvent(ConfigurationEvent):
    """Event fired when configuration error occurs."""
    error_type: str
    error_message: str
    line_number: Optional[int]
    column_number: Optional[int]
```

### ConfigurationReloadedEvent

Event fired when configuration is reloaded.

```python
@dataclass
class ConfigurationReloadedEvent(ConfigurationEvent):
    """Event fired when configuration is reloaded."""
    selectors_added: List[str]
    selectors_removed: List[str]
    selectors_modified: List[str]
    reload_time_ms: float
```

## Error Contracts

### ConfigurationException

Base exception for configuration errors.

```python
class ConfigurationException(Exception):
    """Base exception for configuration system errors."""
    
    def __init__(self, message: str, file_path: str, correlation_id: str):
        self.message = message
        self.file_path = file_path
        self.correlation_id = correlation_id
        super().__init__(message)
```

### SchemaValidationException

Exception for schema validation errors.

```python
class SchemaValidationException(ConfigurationException):
    """Exception raised when YAML schema validation fails."""
    
    def __init__(self, message: str, file_path: str, validation_errors: List[str], correlation_id: str):
        self.validation_errors = validation_errors
        super().__init__(message, file_path, correlation_id)
```

### InheritanceException

Exception for inheritance resolution errors.

```python
class InheritanceException(ConfigurationException):
    """Exception raised when inheritance resolution fails."""
    
    def __init__(self, message: str, file_path: str, circular_refs: List[str], correlation_id: str):
        self.circular_references = circular_refs
        super().__init__(message, file_path, correlation_id)
```

### SemanticResolutionException

Exception for semantic resolution errors.

```python
class SemanticResolutionException(ConfigurationException):
    """Exception raised when semantic selector resolution fails."""
    
    def __init__(self, message: str, selector_name: str, context: str, correlation_id: str):
        self.selector_name = selector_name
        self.context = context
        super().__init__(message, "", correlation_id)
```

## Performance Contracts

### Performance Requirements

All API implementations must meet these performance requirements:

- Configuration loading: <100ms per file
- Inheritance resolution: <50ms per chain
- Semantic lookup: <10ms per query
- Index building: <500ms for 1000 selectors
- Hot-reload detection: <1s event latency
- Configuration validation: <20ms per file

### Monitoring Contracts

All implementations must provide performance monitoring:

```python
@dataclass
class PerformanceMetrics:
    """Performance metrics for configuration operations."""
    operation_type: str
    execution_time_ms: float
    memory_usage_mb: float
    cache_hit_rate: float
    error_rate: float
```

## Integration Contracts

### Selector Engine Integration

The configuration system must integrate with existing Selector Engine components:

1. **Strategy Pattern Integration**: Configuration strategies must be compatible with existing strategy implementations
2. **Confidence Scoring Integration**: Configuration confidence must integrate with existing scoring algorithms
3. **Validation Integration**: Configuration validation must extend existing validation framework
4. **Event Integration**: Configuration events must integrate with existing event bus

### Browser Lifecycle Integration

The configuration system must integrate with browser lifecycle management:

1. **Context Awareness**: Selectors must be context-aware for tab isolation
2. **State Persistence**: Configuration state must persist across browser sessions
3. **Resource Management**: Configuration loading must respect resource constraints
4. **Error Handling**: Configuration errors must not crash browser sessions

These contracts ensure the configuration system integrates seamlessly with existing components while maintaining the modular, testable, and resilient characteristics required by the constitution.
