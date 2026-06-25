"""
Base flow template for the modular site scraper template.

This module provides a base template for creating navigation flows
with common functionality and best practices.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from src.sites.base.base_flow import BaseFlow, FlowState, FlowResult
from src.sites.base.component_interface import ComponentContext, ComponentResult


class BaseTemplateFlow(BaseFlow):
    """Base template flow with common navigation functionality."""
    
    def __init__(
        self,
        component_id: str,
        name: str,
        version: str,
        description: str,
        flow_type: str = "NAVIGATION",
        page: Any = None,
        selector_engine: Any = None
    ):
        """
        Initialize base template flow.
        
        Args:
            component_id: Unique identifier for the flow
            name: Human-readable name for the flow
            version: Flow version
            description: Flow description
            flow_type: Type of flow (NAVIGATION, SEARCH, LOGIN, etc.)
            page: Playwright page object
            selector_engine: Selector engine instance
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            flow_type=flow_type,
            page=page,
            selector_engine=selector_engine
        )
        
        # Flow-specific configuration
        self._timeout_ms: int = 30000
        self._retry_attempts: int = 3
        self._retry_delay_ms: int = 1000
        self._wait_for_selector: Optional[str] = None
        self._success_indicators: List[str] = []
        self._error_indicators: List[str] = []
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute the base flow with common pre/post processing.
        
        Args:
            **kwargs: Flow-specific arguments
            
        Returns:
            Flow execution result
        """
        try:
            start_time = datetime.utcnow()
            
            # Pre-execution validation
            if not await self.validate(**kwargs):
                return self._create_flow_result(
                    success=False,
                    data={'error': 'Flow validation failed'},
                    errors=['Validation failed']
                )
            
            # Execute the specific flow logic
            flow_result = await self._execute_flow_logic(**kwargs)
            
            # Post-execution validation
            if not await self._validate_execution_result(flow_result):
                return self._create_flow_result(
                    success=False,
                    data={'error': 'Flow execution validation failed'},
                    errors=['Execution validation failed']
                )
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return self._create_flow_result(
                success=True,
                data={
                    'flow_result': flow_result,
                    'execution_time_ms': execution_time,
                    'flow_type': self.flow_type
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Flow execution failed: {str(e)}", "error")
            return self._create_flow_result(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def _execute_flow_logic(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the specific flow logic.
        Override this method in subclasses.
        
        Args:
            **kwargs: Flow-specific arguments
            
        Returns:
            Flow execution result
        """
        # Default implementation - navigate to base URL
        base_url = kwargs.get('base_url', self._base_url)
        if base_url:
            await self.navigate_to_url(base_url, self._wait_for_selector)
        
        return {
            'success': True,
            'url': self._flow_state.current_url if self._flow_state else base_url,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _validate_execution_result(self, flow_result: Dict[str, Any]) -> bool:
        """
        Validate the execution result.
        
        Args:
            flow_result: Result from flow execution
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check for success indicators
            if self._success_indicators:
                current_url = self._flow_state.current_url if self._flow_state else ""
                page_content = await self._page.content() if self._page else ""
                
                for indicator in self._success_indicators:
                    if indicator in current_url or indicator in page_content:
                        return True
                
                return False
            
            # Check for error indicators
            if self._error_indicators:
                current_url = self._flow_state.current_url if self._flow_state else ""
                page_content = await self._page.content() if self._page else ""
                
                for indicator in self._error_indicators:
                    if indicator in current_url or indicator in page_content:
                        return False
            
            return True
            
        except Exception as e:
            self._log_operation("_validate_execution_result", f"Validation failed: {str(e)}", "error")
            return False
    
    async def wait_for_page_load(self, timeout_ms: Optional[int] = None) -> bool:
        """
        Wait for page to fully load.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            True if page loaded successfully, False otherwise
        """
        try:
            timeout = timeout_ms or self._timeout_ms
            
            # Wait for network idle
            await self._page.wait_for_load_state('networkidle', timeout=timeout)
            
            # Wait for a brief moment to ensure everything is loaded
            await asyncio.sleep(0.5)
            
            self._log_operation("wait_for_page_load", "Page loaded successfully")
            return True
            
        except Exception as e:
            self._log_operation("wait_for_page_load", f"Page load failed: {str(e)}", "error")
            if self._flow_state:
                self._flow_state.increment_error_count()
            return False
    
    async def wait_for_element_and_interact(
        self,
        selector_name: str,
        interaction: str = "click",
        value: Optional[str] = None,
        timeout_ms: Optional[int] = None
    ) -> bool:
        """
        Wait for element and perform interaction.
        
        Args:
            selector_name: Name of the selector
            interaction: Type of interaction ('click', 'fill', 'hover', 'wait')
            value: Value to fill (for 'fill' interaction)
            timeout_ms: Timeout in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Wait for element
            element = await self.wait_for_element(selector_name, timeout_ms)
            if not element:
                return False
            
            # Perform interaction
            if interaction == "click":
                success = await self.click_element(selector_name)
            elif interaction == "fill":
                if not value:
                    raise ValueError("Value is required for 'fill' interaction")
                success = await self.fill_form(selector_name, value)
            elif interaction == "hover":
                await element.hover()
                success = True
            elif interaction == "wait":
                success = True
            else:
                raise ValueError(f"Unknown interaction type: {interaction}")
            
            if success:
                self._log_operation(
                    "wait_for_element_and_interact",
                    f"Successfully performed {interaction} on {selector_name}"
                )
            else:
                self._log_operation(
                    "wait_for_element_and_interact",
                    f"Failed to perform {interaction} on {selector_name}",
                    "error"
                )
            
            return success
            
        except Exception as e:
            self._log_operation(
                "wait_for_element_and_interact",
                f"Interaction failed: {str(e)}",
                "error"
            )
            if self._flow_state:
                self._flow_state.increment_error_count()
            return False
    
    async def retry_operation(
        self,
        operation: callable,
        *args,
        max_attempts: Optional[int] = None,
        delay_ms: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Retry an operation with exponential backoff.
        
        Args:
            operation: Operation to retry
            *args: Operation arguments
            max_attempts: Maximum retry attempts
            delay_ms: Delay between retries in milliseconds
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
            
        Raises:
            Exception: If all retry attempts fail
        """
        max_attempts = max_attempts or self._retry_attempts
        delay_ms = delay_ms or self._retry_delay_ms
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                if attempt == max_attempts - 1:
                    break
                
                # Exponential backoff
                current_delay = delay_ms * (2 ** attempt)
                await asyncio.sleep(current_delay / 1000.0)
        
        raise last_exception
    
    def configure(
        self,
        timeout_ms: Optional[int] = None,
        retry_attempts: Optional[int] = None,
        retry_delay_ms: Optional[int] = None,
        wait_for_selector: Optional[str] = None,
        success_indicators: Optional[List[str]] = None,
        error_indicators: Optional[List[str]] = None
    ) -> None:
        """
        Configure flow parameters.
        
        Args:
            timeout_ms: Default timeout in milliseconds
            retry_attempts: Default retry attempts
            retry_delay_ms: Default retry delay in milliseconds
            wait_for_selector: Default selector to wait for
            success_indicators: List of success indicators
            error_indicators: List of error indicators
        """
        if timeout_ms is not None:
            self._timeout_ms = timeout_ms
        if retry_attempts is not None:
            self._retry_attempts = retry_attempts
        if retry_delay_ms is not None:
            self._retry_delay_ms = retry_delay_ms
        if wait_for_selector is not None:
            self._wait_for_selector = wait_for_selector
        if success_indicators is not None:
            self._success_indicators = success_indicators
        if error_indicators is not None:
            self._error_indicators = error_indicators
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current flow configuration."""
        return {
            'timeout_ms': self._timeout_ms,
            'retry_attempts': self._retry_attempts,
            'retry_delay_ms': self._retry_delay_ms,
            'wait_for_selector': self._wait_for_selector,
            'success_indicators': self._success_indicators,
            'error_indicators': self._error_indicators,
            'flow_type': self.flow_type,
            'base_url': self._base_url
        }
    
    async def validate(self, **kwargs) -> bool:
        """
        Validate flow configuration and dependencies.
        
        Args:
            **kwargs: Validation parameters
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Call parent validation
            if not await super().validate(**kwargs):
                return False
            
            # Validate flow-specific configuration
            if self._timeout_ms <= 0:
                self._log_operation("validate", "Timeout must be positive", "error")
                return False
            
            if self._retry_attempts < 0:
                self._log_operation("validate", "Retry attempts must be non-negative", "error")
                return False
            
            if self._retry_delay_ms < 0:
                self._log_operation("validate", "Retry delay must be non-negative", "error")
                return False
            
            return True
            
        except Exception as e:
            self._log_operation("validate", f"Validation failed: {str(e)}", "error")
            return False
