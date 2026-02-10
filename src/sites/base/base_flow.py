"""
Base flow class for navigation logic in the modular site scraper template system.

This module provides the base class that all flow components must inherit from,
ensuring consistent navigation patterns and enabling proper lifecycle management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import asyncio

from .component_interface import BaseComponent, ComponentContext, ComponentResult


@dataclass
class FlowState:
    """State object for flow execution."""
    current_url: str
    navigation_history: List[str]
    form_data: Dict[str, Any]
    session_data: Dict[str, Any]
    error_count: int
    last_action: str
    timestamp: datetime
    
    def __post_init__(self):
        if self.navigation_history is None:
            self.navigation_history = []
        if self.form_data is None:
            self.form_data = {}
        if self.session_data is None:
            self.session_data = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def add_navigation_step(self, url: str, action: str):
        """Add a navigation step to the history."""
        self.navigation_history.append(url)
        self.last_action = action
        self.current_url = url
        self.timestamp = datetime.utcnow()
    
    def set_form_data(self, key: str, value: Any):
        """Set form data."""
        self.form_data[key] = value
    
    def get_form_data(self, key: str, default: Any = None) -> Any:
        """Get form data."""
        return self.form_data.get(key, default)
    
    def increment_error_count(self):
        """Increment error count."""
        self.error_count += 1


@dataclass
class FlowResult:
    """Result object for flow execution."""
    success: bool
    flow_state: FlowState
    data: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    execution_time_ms: float
    flow_type: str
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BaseFlow(BaseComponent):
    """Base class for all flow components in the modular template system."""
    
    def __init__(
        self,
        component_id: str,
        name: str,
        version: str,
        description: str,
        flow_type: str,
        page: Any = None,
        selector_engine: Any = None
    ):
        """
        Initialize the base flow.
        
        Args:
            component_id: Unique identifier for the flow
            name: Human-readable name for the flow
            version: Flow version following semantic versioning
            description: Flow description
            flow_type: Type of flow (SEARCH, LOGIN, PAGINATION, NAVIGATION)
            page: Playwright page object
            selector_engine: Selector engine instance
        """
        super().__init__(component_id, name, version, description)
        self.flow_type = flow_type
        self._page = page
        self._selector_engine = selector_engine
        self._flow_state: Optional[FlowState] = None
        self._base_url: Optional[str] = None
    
    @property
    def flow_type(self) -> str:
        """Get flow type."""
        return self._flow_type
    
    @property
    def page(self) -> Any:
        """Get Playwright page object."""
        return self._page
    
    @property
    def selector_engine(self) -> Any:
        """Get selector engine instance."""
        return self._selector_engine
    
    @property
    def flow_state(self) -> Optional[FlowState]:
        """Get current flow state."""
        return self._flow_state
    
    @property
    def base_url(self) -> Optional[str]:
        """Get base URL for the flow."""
        return self._base_url
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize the flow with given context.
        
        Args:
            context: Component execution context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._context = context
            self._page = context.page
            self._selector_engine = context.selector_engine
            
            # Initialize flow state
            self._flow_state = FlowState(
                current_url=context.page.url,
                navigation_history=[],
                form_data={},
                session_data={},
                error_count=0,
                last_action="initialized",
                timestamp=datetime.utcnow()
            )
            
            # Set base URL from context if available
            self._base_url = context.get_state("base_url")
            
            self._log_operation("initialize", f"Flow {self.component_id} initialized successfully")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Failed to initialize flow: {str(e)}", "error")
            return False
    
    @abstractmethod
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute the flow's main functionality.
        
        Args:
            **kwargs: Flow-specific arguments
            
        Returns:
            Flow execution result
        """
        pass
    
    async def navigate_to_url(self, url: str, wait_for: str = None) -> bool:
        """
        Navigate to a specific URL.
        
        Args:
            url: URL to navigate to
            wait_for: Selector to wait for before considering navigation complete
            
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            if not self._page:
                raise ValueError("Page object not initialized")
            
            self._log_operation("navigate", f"Navigating to: {url}")
            
            # Navigate to URL
            await self._page.goto(url)
            
            # Wait for specific selector if provided
            if wait_for and self._selector_engine:
                element = await self._selector_engine.find(self._page, wait_for)
                if not element:
                    self._log_operation("navigate", f"Wait selector not found: {wait_for}", "warning")
            
            # Update flow state
            if self._flow_state:
                self._flow_state.add_navigation_step(url, "navigate_to_url")
            
            return True
            
        except Exception as e:
            self._log_operation("navigate", f"Navigation failed: {str(e)}", "error")
            if self._flow_state:
                self._flow_state.increment_error_count()
            return False
    
    async def wait_for_element(self, selector_name: str, timeout_ms: int = 30000) -> Optional[Any]:
        """
        Wait for an element to be available.
        
        Args:
            selector_name: Name of the selector to find
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Element if found, None otherwise
        """
        try:
            if not self._selector_engine:
                self._log_operation("wait_for_element", "Selector engine not available", "error")
                return None
            
            self._log_operation("wait_for_element", f"Waiting for selector: {selector_name}")
            
            # Use selector engine to find element
            element = await self._selector_engine.find(self._page, selector_name)
            
            if element:
                self._log_operation("wait_for_element", f"Element found: {selector_name}")
            else:
                self._log_operation("wait_for_element", f"Element not found: {selector_name}", "warning")
            
            return element
            
        except Exception as e:
            self._log_operation("wait_for_element", f"Wait failed: {str(e)}", "error")
            return None
    
    async def fill_form(self, selector_name: str, value: str) -> bool:
        """
        Fill a form field.
        
        Args:
            selector_name: Name of the selector for the form field
            value: Value to fill
            
        Returns:
            True if successful, False otherwise
        """
        try:
            element = await self.wait_for_element(selector_name)
            if not element:
                return False
            
            self._log_operation("fill_form", f"Filling {selector_name} with value")
            
            await element.fill(value)
            
            # Update flow state
            if self._flow_state:
                self._flow_state.set_form_data(selector_name, value)
            
            return True
            
        except Exception as e:
            self._log_operation("fill_form", f"Form fill failed: {str(e)}", "error")
            if self._flow_state:
                self._flow_state.increment_error_count()
            return False
    
    async def click_element(self, selector_name: str) -> bool:
        """
        Click an element.
        
        Args:
            selector_name: Name of the selector for the element to click
            
        Returns:
            True if successful, False otherwise
        """
        try:
            element = await self.wait_for_element(selector_name)
            if not element:
                return False
            
            self._log_operation("click_element", f"Clicking element: {selector_name}")
            
            await element.click()
            
            # Update flow state
            if self._flow_state:
                self._flow_state.last_action = f"click_{selector_name}"
            
            return True
            
        except Exception as e:
            self._log_operation("click_element", f"Click failed: {str(e)}", "error")
            if self._flow_state:
                self._flow_state.increment_error_count()
            return False
    
    async def validate(self, **kwargs) -> bool:
        """
        Validate flow configuration and dependencies.
        
        Args:
            **kwargs: Validation parameters
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Check if page is available
            if not self._page:
                self._log_operation("validate", "Page object not available", "error")
                return False
            
            # Check if selector engine is available
            if not self._selector_engine:
                self._log_operation("validate", "Selector engine not available", "error")
                return False
            
            # Check flow state
            if not self._flow_state:
                self._log_operation("validate", "Flow state not initialized", "error")
                return False
            
            self._log_operation("validate", "Flow validation passed")
            return True
            
        except Exception as e:
            self._log_operation("validate", f"Validation failed: {str(e)}", "error")
            return False
    
    async def cleanup(self) -> None:
        """Clean up flow resources."""
        try:
            self._log_operation("cleanup", f"Cleaning up flow {self.component_id}")
            
            # Reset flow state
            self._flow_state = None
            
            # Clear references
            self._page = None
            self._selector_engine = None
            self._context = None
            
        except Exception as e:
            self._log_operation("cleanup", f"Cleanup failed: {str(e)}", "error")
    
    def _create_flow_result(
        self,
        success: bool,
        data: Dict[str, Any],
        errors: List[str] = None,
        warnings: List[str] = None,
        execution_time_ms: float = 0.0
    ) -> ComponentResult:
        """Create a flow result object."""
        flow_result = FlowResult(
            success=success,
            flow_state=self._flow_state or FlowState("", [], {}, {}, 0, "", datetime.utcnow()),
            data=data,
            errors=errors or [],
            warnings=warnings or [],
            execution_time_ms=execution_time_ms,
            flow_type=self.flow_type
        )
        
        return self._create_result(
            success=success,
            data=data,
            errors=errors,
            warnings=warnings,
            execution_time_ms=execution_time_ms
        )


class FlowError(Exception):
    """Exception raised when flow operations fail."""
    pass


class NavigationError(FlowError):
    """Exception raised when navigation operations fail."""
    pass


class ElementNotFoundError(FlowError):
    """Exception raised when required elements are not found."""
    pass
