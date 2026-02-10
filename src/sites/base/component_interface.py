"""
Base component interface for the modular site scraper template system.

This module defines the core interface that all components must implement,
ensuring consistency and enabling dependency injection and lifecycle management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio


@dataclass
class ComponentMetadata:
    """Metadata for components."""
    component_id: str
    name: str
    version: str
    description: str
    author: str = "System"
    dependencies: List[str] = None
    compatibility: Dict[str, str] = None
    tags: List[str] = None
    async_compatible: bool = True
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.compatibility is None:
            self.compatibility = {}
        if self.tags is None:
            self.tags = []


@dataclass
class ComponentContext:
    """Context object for component execution."""
    page: Any  # Playwright page object
    selector_engine: Any  # Selector engine instance
    navigation_state: Dict[str, Any]
    session_data: Dict[str, Any]
    correlation_id: str
    environment: str = "dev"
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from navigation state."""
        return self.navigation_state.get(key, default)
    
    def set_state(self, key: str, value: Any) -> None:
        """Set value in navigation state."""
        self.navigation_state[key] = value
    
    def get_session_data(self, key: str, default: Any = None) -> Any:
        """Get value from session data."""
        return self.session_data.get(key, default)
    
    def set_session_data(self, key: str, value: Any) -> None:
        """Set value in session data."""
        self.session_data[key] = value


@dataclass
class ComponentResult:
    """Result object for component execution."""
    success: bool
    data: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    execution_time_ms: float
    component_id: str
    timestamp: datetime
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BaseComponent(ABC):
    """Base class for all components in the modular template system."""
    
    def __init__(self, component_id: str, name: str, version: str, description: str):
        """
        Initialize the base component.
        
        Args:
            component_id: Unique identifier for the component
            name: Human-readable name for the component
            version: Component version following semantic versioning
            description: Component description
        """
        self.component_id = component_id
        self.name = name
        self.version = version
        self.description = description
        self._initialized = False
        self._context: Optional[ComponentContext] = None
        self._metadata = ComponentMetadata(
            component_id=component_id,
            name=name,
            version=version,
            description=description
        )
    
    @property
    def metadata(self) -> ComponentMetadata:
        """Get component metadata."""
        return self._metadata
    
    @property
    def is_initialized(self) -> bool:
        """Check if component is initialized."""
        return self._initialized
    
    @property
    def context(self) -> Optional[ComponentContext]:
        """Get current component context."""
        return self._context
    
    @abstractmethod
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize the component with given context.
        
        Args:
            context: Component execution context
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute the component's main functionality.
        
        Args:
            **kwargs: Component-specific arguments
            
        Returns:
            Component execution result
        """
        pass
    
    @abstractmethod
    async def validate(self, **kwargs) -> bool:
        """
        Validate component configuration and dependencies.
        
        Args:
            **kwargs: Validation parameters
            
        Returns:
            True if validation passes, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up component resources."""
        pass
    
    async def get_dependencies(self) -> List[str]:
        """
        Get list of component dependencies.
        
        Returns:
            List of component IDs this component depends on
        """
        return self.metadata.dependencies
    
    async def check_compatibility(self, required_version: str) -> bool:
        """
        Check compatibility with required version.
        
        Args:
            required_version: Required version string
            
        Returns:
            True if compatible, False otherwise
        """
        # Simple version comparison - can be enhanced with semantic versioning
        return self.version == required_version
    
    def _create_result(
        self,
        success: bool,
        data: Dict[str, Any],
        errors: List[str] = None,
        warnings: List[str] = None,
        execution_time_ms: float = 0.0
    ) -> ComponentResult:
        """Create a component result object."""
        return ComponentResult(
            success=success,
            data=data,
            errors=errors or [],
            warnings=warnings or [],
            execution_time_ms=execution_time_ms,
            component_id=self.component_id,
            timestamp=datetime.utcnow()
        )
    
    def _log_operation(self, operation: str, message: str, level: str = "info"):
        """Log component operation."""
        # This will be replaced with structured logging
        print(f"[{level.upper()}] {self.component_id}: {operation} - {message}")
    
    async def _measure_execution_time(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = datetime.utcnow()
        try:
            result = await func(*args, **kwargs)
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            if isinstance(result, ComponentResult):
                result.execution_time_ms = execution_time
            
            return result
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            self._log_operation("error", f"Execution failed after {execution_time:.2f}ms: {str(e)}", "error")
            raise


class ComponentLifecycleError(Exception):
    """Exception raised when component lifecycle operations fail."""
    pass


class ComponentValidationError(Exception):
    """Exception raised when component validation fails."""
    pass


class ComponentDependencyError(Exception):
    """Exception raised when component dependencies cannot be resolved."""
    pass
