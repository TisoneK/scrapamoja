"""
Base flow classes for the advanced template architecture.

This module provides base classes for different flow domains with common utilities,
error handling patterns, and standardized interfaces.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class FlowStatus(Enum):
    """Flow execution status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class NavigationMode(Enum):
    """Navigation mode types."""
    PAGE_NAVIGATION = "page"
    DYNAMIC_NAVIGATION = "dynamic"
    SPA_NAVIGATION = "spa"
    HYBRID_NAVIGATION = "hybrid"


@dataclass
class NavigationResult:
    """Result of a navigation operation."""
    success: bool
    url: Optional[str]
    error: Optional[str]
    execution_time: float
    metadata: Dict[str, Any]


class BaseNavigationFlow(ABC):
    """Base class for all navigation flows."""
    
    def __init__(self, page, selector_engine, config=None):
        """
        Initialize base navigation flow.
        
        Args:
            page: Playwright page instance
            selector_engine: Selector engine instance
            config: Optional configuration dictionary
        """
        self.page = page
        self.selector_engine = selector_engine
        self.config = config or {}
        self.status = FlowStatus.IDLE
        self.start_time = None
        self.execution_history = []
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    @abstractmethod
    async def navigate_to_url(self, url: str, wait_for_load: bool = True) -> NavigationResult:
        """
        Navigate to a specific URL.
        
        Args:
            url: URL to navigate to
            wait_for_load: Whether to wait for page load
            
        Returns:
            Navigation result with success status and metadata
        """
        pass
    
    @abstractmethod
    async def wait_for_element(self, selector: str, timeout: float = 10.0) -> NavigationResult:
        """
        Wait for an element to appear on the page.
        
        Args:
            selector: CSS selector of the element to wait for
            timeout: Maximum wait time in seconds
            
        Returns:
            Navigation result with success status and metadata
        """
        pass
    
    @abstractmethod
    async def click_element(self, selector: str, wait_for_navigation: bool = True) -> NavigationResult:
        """
        Click an element on the page.
        
        Args:
            selector: CSS selector of the element to click
            wait_for_navigation: Whether to wait for navigation after click
            
        Returns:
            Navigation result with success status and metadata
        """
        pass
    
    @abstractmethod
    async def extract_navigation_links(self, container_selector: str) -> List[str]:
        """
        Extract navigation links from a container element.
        
        Args:
            container_selector: CSS selector of the container element
            
        Returns:
            List of URLs found in the container
        """
        pass
    
    async def _wait_for_page_load(self, timeout: float = 30.0) -> NavigationResult:
        """
        Wait for page to load completely.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            Navigation result indicating success/failure
        """
        try:
            self.logger.info(f"Waiting for page load (timeout: {timeout}s)")
            
            # Wait for network idle
            await self.page.wait_for_load_state('networkidle', timeout=timeout)
            
            # Additional check for specific elements
            await self.page.wait_for_timeout(2000)  # Give time for dynamic content
            
            self.logger.info("Page load completed")
            
            return NavigationResult(
                success=True,
                execution_time=timeout,
                metadata={'event': 'page_load'}
            )
            
        except asyncio.TimeoutError:
            self.logger.error("Page load timed out")
            return NavigationResult(
                success=False,
                error=f"Page load timed out after {timeout}s",
                execution_time=timeout,
                metadata={'event': 'page_load_timeout'}
            )
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def _log_navigation_event(self, event: str, details: Dict[str, Any]) -> None:
        """
        Log a navigation event for debugging.
        
        Args:
            event: Description of the navigation event
            details: Additional event details
        """
        log_entry = {
            'timestamp': time.time(),
            'event': event,
            'details': details,
            'status': self.status.value
        }
        
        self.execution_history.append(log_entry)
        self.logger.info(f"Navigation event: {event} - {details}")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get summary of navigation executions.
        
        Returns:
            Dictionary with execution statistics
        """
        if not self.execution_history:
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'average_execution_time': 0,
                'last_execution': None
            }
        
        total_executions = len(self.execution_history)
        successful_executions = len([
            entry for entry in self.execution_history
            if entry.get('status') == FlowStatus.SUCCESS.value
        ])
        failed_executions = len([
            entry for entry in self.execution_history
            if entry.get('status') == FlowStatus.ERROR.value
        ])
        
        execution_times = [
            entry.get('execution_time', 0) 
            for entry in self.execution_history
            if 'execution_time' in entry
        ]
        
        average_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'average_execution_time': average_execution_time,
            'last_execution': self.execution_history[-1] if self.execution_history else None
        }


class DynamicNavigationFlow(BaseNavigationFlow):
    """Navigation flow for dynamic sites with JavaScript interactions."""
    
    def __init__(self, page, selector_engine, config=None):
        super().__init__(page, selector_engine, config)
        self.navigation_mode = NavigationMode.DYNAMIC_NAVIGATION
        self.wait_timeout = self._get_config_value('wait_timeout', 10.0)
        self.retry_attempts = self._get_config_value('retry_attempts', 3)
    
    async def navigate_to_url(self, url: str, wait_for_load: bool = True) -> NavigationResult:
        """Navigate to URL with dynamic content handling."""
        return await self._execute_with_timeout(
            'navigate_to_url',
            self.wait_timeout * 2,  # Longer timeout for dynamic content
            url,
            wait_for_load=wait_for_load
        )
    
    async def wait_for_dynamic_content(self, selector: str, timeout: float = None) -> NavigationResult:
        """Wait for dynamic content to load."""
        timeout = timeout or self.wait_timeout
        
        try:
            self.logger.info(f"Waiting for dynamic content: {selector}")
            
            # Wait for element with content
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            
            # Check if element has meaningful content
            content = await element.inner_text()
            if content and content.strip():
                self.logger.info("Dynamic content loaded")
                return NavigationResult(
                    success=True,
                    execution_time=time.time() - (self.start_time or time.time()),
                    metadata={'element': selector, 'content_length': len(content)}
                )
            else:
                self.logger.warning(f"Element found but no content: {selector}")
                return NavigationResult(
                    success=False,
                    error="Element found but no content",
                    execution_time=time.time() - (self.start_time or time.time()),
                    metadata={'element': selector, 'content_length': 0}
                )
                
        except asyncio.TimeoutError:
            return NavigationResult(
                success=False,
                error=f"Timeout waiting for dynamic content: {selector}",
                execution_time=timeout,
                metadata={'timeout': timeout}
            )
    
    async def click_dynamic_element(self, selector: str, wait_for_navigation: bool = True) -> NavigationResult:
        """Click element with dynamic content handling."""
        for attempt in range(self.retry_attempts):
            result = await self._execute_with_timeout(
                'click_element',
                5.0,  # Short timeout for clicks
                selector,
                wait_for_navigation=wait_for_navigation
            )
            
            if result.success:
                self.logger.info(f"Successfully clicked element: {selector} (attempt {attempt + 1})")
                return result
            
            self.logger.warning(f"Click attempt {attempt + 1} failed for {selector}: {result.error}")
            
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(1)  # Wait before retry
        
        return NavigationResult(
            success=False,
            error=f"Failed to click element after {self.retry_attempts} attempts",
            execution_time=sum(r.execution_time for r in self.execution_history[-self.retry_attempts:]),
            metadata={'attempts': self.retry_attempts}
        )
    
    async def extract_dynamic_links(self, container_selector: str) -> List[str]:
        """Extract links from dynamic content."""
        try:
            self.logger.info(f"Extracting dynamic links from: {container_selector}")
            
            container = await self.page.query_selector(container_selector)
            if not container:
                return []
            
            links = []
            link_elements = await container.query_selector_all('a[href]')
            
            for link_element in link_elements:
                href = await link_element.get_attribute('href')
                if href:
                    links.append(href)
            
            self.logger.info(f"Extracted {len(links)} dynamic links")
            return links
            
        except Exception as e:
            self.logger.error(f"Failed to extract dynamic links: {e}")
            return []


class SPANavigationFlow(BaseNavigationFlow):
    """Navigation flow for Single Page Applications."""
    
    def __init__(self, page, selector_engine, config=None):
        super().__init__(page, selector_engine, config)
        self.navigation_mode = NavigationMode.SPA_NAVIGATION
        self.spa_timeout = self._get_config_value('spa_timeout', 15.0)
        self.route_change_timeout = self._get_config_value('route_change_timeout', 5.0)
    
    async def navigate_to_url(self, url: str, wait_for_load: bool = True) -> NavigationResult:
        """Navigate to URL with SPA handling."""
        return await self._execute_with_timeout(
            'navigate_to_url',
            self.spa_timeout,
            url,
            wait_for_load=wait_for_load
        )
    
    async def wait_for_spa_navigation(self, expected_route: str = None, timeout: float = None) -> NavigationResult:
        """Wait for SPA navigation to complete."""
        timeout = timeout or self.spa_timeout
        
        try:
            self.logger.info(f"Waiting for SPA navigation: {expected_route}")
            
            # Wait for URL to match expected route
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                current_url = self.page.url
                if expected_route and expected_route not in current_url:
                    await asyncio.sleep(0.5)
                    continue
                
                # Check if navigation is complete
                if await self._check_spa_navigation_complete():
                    self.logger.info("SPA navigation completed")
                    return NavigationResult(
                        success=True,
                        execution_time=time.time() - start_time,
                        metadata={'route': expected_route}
                    )
                
                await asyncio.sleep(0.1)
            
            return NavigationResult(
                success=False,
                error=f"SPA navigation timeout after {timeout}s",
                execution_time=timeout,
                metadata={'timeout': timeout, 'expected_route': expected_route}
            )
            
        except Exception as e:
            self.logger.error(f"SPA navigation wait failed: {e}")
            return NavigationResult(
                success=False,
                error=str(e),
                execution_time=0,
                metadata={'exception': str(e)}
            )
    
    async def _check_spa_navigation_complete(self) -> bool:
        """Check if SPA navigation is complete."""
        # This would be implemented based on specific SPA indicators
        # For now, use a simple check for loading completion
        try:
            # Check for common SPA completion indicators
            loading_indicators = [
                '.loading',  # Common loading class
                '[data-loading="false"]',  # Angular loading indicator
                '.spa-ready',  # Custom SPA ready indicator
            ]
            
            for indicator in loading_indicators:
                elements = await self.page.query_selector_all(indicator)
                if not elements:  # All indicators are gone
                    return True
                
                # Check if any indicator shows completion
                for element in elements:
                    if 'false' in await element.get_attribute('data-loading', ''):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"SPA navigation check failed: {e}")
            return False
    
    async def handle_spa_route_change(self, new_route: str) -> NavigationResult:
        """Handle SPA route changes."""
        return await self._execute_with_timeout(
            'handle_spa_route_change',
            self.route_change_timeout,
            new_route
        )


class HybridNavigationFlow(BaseNavigationFlow):
    """Navigation flow for hybrid sites with mixed static and dynamic content."""
    
    def __init__(self, page, selector_engine, config=None):
        super().__init__(page, selector_engine, config)
        self.navigation_mode = NavigationMode.HYBRID_NAVIGATION
        self.hybrid_wait_time = self._get_config_value('hybrid_wait_time', 8.0)
    
    async def navigate_to_url(self, url: str, wait_for_load: bool = True) -> NavigationResult:
        """Navigate to URL with hybrid handling."""
        # First try standard navigation
        result = await super().navigate_to_url(url, wait_for_load=False)
        
        if result.success:
            # Check if dynamic content is present
            dynamic_indicators = await self.page.query_selector_all('.dynamic-content, [data-dynamic]')
            
            if dynamic_indicators:
                self.logger.info("Dynamic content detected, switching to dynamic navigation")
                return await self.wait_for_dynamic_content('.dynamic-content', timeout=self.hybrid_wait_time)
            
            return result
        
        # Fallback to dynamic navigation
        self.logger.info("Using dynamic navigation for hybrid site")
        return await super().navigate_to_url(url, wait_for_load)


class NavigationFlowFactory:
    """Factory for creating appropriate navigation flows."""
    
    @staticmethod
    def create_navigation_flow(page, selector_engine, navigation_mode: NavigationMode, config=None) -> BaseNavigationFlow:
        """
        Create appropriate navigation flow based on mode.
        
        Args:
            page: Playwright page instance
            selector_engine: Selector engine instance
            navigation_mode: Navigation mode
            config: Optional configuration
            
        Returns:
            Appropriate navigation flow instance
        """
        if navigation_mode == NavigationMode.DYNAMIC_NAVIGATION:
            return DynamicNavigationFlow(page, selector_engine, config)
        elif navigation_mode == NavigationMode.SPA_NAVIGATION:
            return SPANavigationFlow(page, selector_engine, config)
        elif navigation_mode == NavigationMode.HYBRID_NAVIGATION:
            return HybridNavigationFlow(page, selector_engine, config)
        else:
            # Default to page navigation
            return BaseNavigationFlow(page, selector_engine, config)


def create_navigation_flow(page, selector_engine, mode: str = 'page', config=None):
    """
    Convenience function to create navigation flow.
    
    Args:
        page: Playwright page instance
        selector_engine: Selector engine instance
        mode: Navigation mode ('page', 'dynamic', 'spa', 'hybrid')
        config: Optional configuration
        
    Returns:
        Navigation flow instance
    """
    navigation_modes = {
        'page': NavigationMode.PAGE_NAVIGATION,
        'dynamic': NavigationMode.DYNAMIC_NAVIGATION,
        'spa': NavigationMode.SPA_NAVIGATION,
        'hybrid': NavigationMode.HYBRID_NAVIGATION
    }
    
    navigation_mode = navigation_modes.get(mode.lower(), NavigationMode.PAGE_NAVIGATION)
    
    return NavigationFlowFactory.create_navigation_flow(
        page, selector_engine, navigation_mode, config
    )


class ExtractionStatus(Enum):
    """Extraction flow status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_time: float
    metadata: Dict[str, Any]
    extracted_count: int = 0
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


class BaseExtractionFlow(ABC):
    """Base class for all extraction flows with comprehensive error handling."""
    
    def __init__(self, page, selector_engine, config=None):
        """
        Initialize base extraction flow.
        
        Args:
            page: Playwright page instance
            selector_engine: Selector engine instance
            config: Optional configuration dictionary
        """
        self.page = page
        self.selector_engine = selector_engine
        self.config = config or {}
        self.status = ExtractionStatus.IDLE
        self.start_time = None
        self.execution_history = []
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.extraction_stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'partial_extractions': 0
        }
    
    @abstractmethod
    async def extract_data(self, selectors: Dict[str, str], validation_rules: Dict[str, Any] = None) -> ExtractionResult:
        """
        Extract data using provided selectors.
        
        Args:
            selectors: Dictionary mapping field names to CSS selectors
            validation_rules: Optional validation rules for extracted data
            
        Returns:
            Extraction result with data and metadata
        """
        pass
    
    @abstractmethod
    async def extract_list_data(self, container_selector: str, item_selectors: Dict[str, str], 
                               validation_rules: Dict[str, Any] = None) -> ExtractionResult:
        """
        Extract list data from container elements.
        
        Args:
            container_selector: CSS selector for container elements
            item_selectors: Dictionary mapping field names to CSS selectors within items
            validation_rules: Optional validation rules for extracted data
            
        Returns:
            Extraction result with list data and metadata
        """
        pass
    
    @abstractmethod
    async def validate_extraction(self, data: Dict[str, Any], validation_rules: Dict[str, Any]) -> List[str]:
        """
        Validate extracted data against rules.
        
        Args:
            data: Extracted data to validate
            validation_rules: Validation rules to apply
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass
    
    async def _execute_with_error_handling(self, operation_name: str, timeout: float, *args, **kwargs) -> ExtractionResult:
        """
        Execute operation with comprehensive error handling.
        
        Args:
            operation_name: Name of the operation for logging
            timeout: Operation timeout in seconds
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Extraction result with error handling
        """
        self.start_time = time.time()
        self.status = ExtractionStatus.RUNNING
        
        try:
            self.logger.info(f"Starting extraction operation: {operation_name}")
            
            # Execute the operation with timeout
            result = await asyncio.wait_for(
                self._execute_operation(operation_name, *args, **kwargs),
                timeout=timeout
            )
            
            self.status = ExtractionStatus.SUCCESS
            self.extraction_stats['successful_extractions'] += 1
            
            self.logger.info(f"Extraction operation completed: {operation_name}")
            return result
            
        except asyncio.TimeoutError:
            self.status = ExtractionStatus.TIMEOUT
            self.extraction_stats['failed_extractions'] += 1
            
            error_msg = f"Extraction operation timed out after {timeout}s: {operation_name}"
            self.logger.error(error_msg)
            
            return ExtractionResult(
                success=False,
                data=None,
                error=error_msg,
                execution_time=time.time() - self.start_time,
                metadata={'operation': operation_name, 'timeout': timeout}
            )
            
        except Exception as e:
            self.status = ExtractionStatus.ERROR
            self.extraction_stats['failed_extractions'] += 1
            
            error_msg = f"Extraction operation failed: {operation_name} - {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ExtractionResult(
                success=False,
                data=None,
                error=error_msg,
                execution_time=time.time() - self.start_time,
                metadata={'operation': operation_name, 'exception': str(e)}
            )
            
        finally:
            self.extraction_stats['total_extractions'] += 1
            self._log_extraction_event(operation_name, {
                'status': self.status.value,
                'execution_time': time.time() - self.start_time
            })
    
    async def _execute_operation(self, operation_name: str, *args, **kwargs) -> ExtractionResult:
        """
        Execute the actual extraction operation.
        
        Args:
            operation_name: Name of the operation
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Extraction result
        """
        # This method should be overridden by subclasses for specific operations
        if operation_name == 'extract_data':
            return await self.extract_data(*args, **kwargs)
        elif operation_name == 'extract_list_data':
            return await self.extract_list_data(*args, **kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation_name}")
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def _log_extraction_event(self, event: str, details: Dict[str, Any]) -> None:
        """Log an extraction event for debugging."""
        log_entry = {
            'timestamp': time.time(),
            'event': event,
            'details': details,
            'status': self.status.value
        }
        
        self.execution_history.append(log_entry)
        self.logger.info(f"Extraction event: {event} - {details}")
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get summary of extraction executions."""
        return {
            'stats': self.extraction_stats.copy(),
            'success_rate': (
                self.extraction_stats['successful_extractions'] / 
                max(self.extraction_stats['total_extractions'], 1)
            ),
            'last_execution': self.execution_history[-1] if self.execution_history else None,
            'total_executions': len(self.execution_history)
        }
    
    def reset_stats(self) -> None:
        """Reset extraction statistics."""
        self.extraction_stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'partial_extractions': 0
        }
        self.execution_history.clear()


class FilteringStatus(Enum):
    """Filtering flow status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class FilteringResult:
    """Result of a filtering operation."""
    success: bool
    filtered_data: Optional[List[Dict[str, Any]]]
    original_count: int
    filtered_count: int
    error: Optional[str]
    execution_time: float
    metadata: Dict[str, Any]
    validation_errors: List[str] = None
    filter_summary: Dict[str, int] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.filter_summary is None:
            self.filter_summary = {}


class BaseFilteringFlow(ABC):
    """Base class for all filtering flows with validation patterns."""
    
    def __init__(self, page, selector_engine, config=None):
        """
        Initialize base filtering flow.
        
        Args:
            page: Playwright page instance
            selector_engine: Selector engine instance
            config: Optional configuration dictionary
        """
        self.page = page
        self.selector_engine = selector_engine
        self.config = config or {}
        self.status = FilteringStatus.IDLE
        self.start_time = None
        self.execution_history = []
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.filtering_stats = {
            'total_filterings': 0,
            'successful_filterings': 0,
            'failed_filterings': 0,
            'total_items_processed': 0,
            'total_items_filtered': 0
        }
    
    @abstractmethod
    async def filter_data(self, data: List[Dict[str, Any]], filter_rules: Dict[str, Any]) -> FilteringResult:
        """
        Filter data based on provided rules.
        
        Args:
            data: List of data items to filter
            filter_rules: Dictionary containing filter criteria and rules
            
        Returns:
            Filtering result with filtered data and statistics
        """
        pass
    
    @abstractmethod
    async def validate_filter_rules(self, filter_rules: Dict[str, Any]) -> List[str]:
        """
        Validate filter rules before applying them.
        
        Args:
            filter_rules: Filter rules to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass
    
    @abstractmethod
    async def apply_advanced_filters(self, data: List[Dict[str, Any]], 
                                   filters: List[Dict[str, Any]]) -> FilteringResult:
        """
        Apply multiple advanced filters to data.
        
        Args:
            data: List of data items to filter
            filters: List of advanced filter configurations
            
        Returns:
            Filtering result with filtered data and detailed statistics
        """
        pass
    
    async def _execute_with_validation(self, operation_name: str, timeout: float, *args, **kwargs) -> FilteringResult:
        """
        Execute filtering operation with validation patterns.
        
        Args:
            operation_name: Name of the operation for logging
            timeout: Operation timeout in seconds
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Filtering result with validation and error handling
        """
        self.start_time = time.time()
        self.status = FilteringStatus.RUNNING
        
        try:
            self.logger.info(f"Starting filtering operation: {operation_name}")
            
            # Validate input parameters
            validation_errors = await self._validate_operation_input(operation_name, *args, **kwargs)
            if validation_errors:
                self.status = FilteringStatus.ERROR
                self.filtering_stats['failed_filterings'] += 1
                
                return FilteringResult(
                    success=False,
                    filtered_data=None,
                    original_count=0,
                    filtered_count=0,
                    error=f"Validation failed: {'; '.join(validation_errors)}",
                    execution_time=time.time() - self.start_time,
                    metadata={'operation': operation_name, 'validation_errors': validation_errors},
                    validation_errors=validation_errors
                )
            
            # Execute the operation with timeout
            result = await asyncio.wait_for(
                self._execute_filtering_operation(operation_name, *args, **kwargs),
                timeout=timeout
            )
            
            self.status = FilteringStatus.SUCCESS
            self.filtering_stats['successful_filterings'] += 1
            self.filtering_stats['total_items_processed'] += result.original_count
            self.filtering_stats['total_items_filtered'] += result.filtered_count
            
            self.logger.info(f"Filtering operation completed: {operation_name}")
            return result
            
        except asyncio.TimeoutError:
            self.status = FilteringStatus.TIMEOUT
            self.filtering_stats['failed_filterings'] += 1
            
            error_msg = f"Filtering operation timed out after {timeout}s: {operation_name}"
            self.logger.error(error_msg)
            
            return FilteringResult(
                success=False,
                filtered_data=None,
                original_count=0,
                filtered_count=0,
                error=error_msg,
                execution_time=time.time() - self.start_time,
                metadata={'operation': operation_name, 'timeout': timeout}
            )
            
        except Exception as e:
            self.status = FilteringStatus.ERROR
            self.filtering_stats['failed_filterings'] += 1
            
            error_msg = f"Filtering operation failed: {operation_name} - {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return FilteringResult(
                success=False,
                filtered_data=None,
                original_count=0,
                filtered_count=0,
                error=error_msg,
                execution_time=time.time() - self.start_time,
                metadata={'operation': operation_name, 'exception': str(e)}
            )
            
        finally:
            self.filtering_stats['total_filterings'] += 1
            self._log_filtering_event(operation_name, {
                'status': self.status.value,
                'execution_time': time.time() - self.start_time
            })
    
    async def _validate_operation_input(self, operation_name: str, *args, **kwargs) -> List[str]:
        """
        Validate input parameters for filtering operations.
        
        Args:
            operation_name: Name of the operation
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if operation_name == 'filter_data':
            data = args[0] if args else kwargs.get('data')
            filter_rules = args[1] if len(args) > 1 else kwargs.get('filter_rules')
            
            if not data:
                errors.append("Data cannot be empty")
            elif not isinstance(data, list):
                errors.append("Data must be a list")
            
            if not filter_rules:
                errors.append("Filter rules cannot be empty")
            elif not isinstance(filter_rules, dict):
                errors.append("Filter rules must be a dictionary")
            else:
                # Validate filter rules using the abstract method
                rule_errors = await self.validate_filter_rules(filter_rules)
                errors.extend(rule_errors)
        
        elif operation_name == 'apply_advanced_filters':
            data = args[0] if args else kwargs.get('data')
            filters = args[1] if len(args) > 1 else kwargs.get('filters')
            
            if not data:
                errors.append("Data cannot be empty")
            elif not isinstance(data, list):
                errors.append("Data must be a list")
            
            if not filters:
                errors.append("Filters cannot be empty")
            elif not isinstance(filters, list):
                errors.append("Filters must be a list")
        
        return errors
    
    async def _execute_filtering_operation(self, operation_name: str, *args, **kwargs) -> FilteringResult:
        """
        Execute the actual filtering operation.
        
        Args:
            operation_name: Name of the operation
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Filtering result
        """
        if operation_name == 'filter_data':
            return await self.filter_data(*args, **kwargs)
        elif operation_name == 'apply_advanced_filters':
            return await self.apply_advanced_filters(*args, **kwargs)
        else:
            raise ValueError(f"Unknown filtering operation: {operation_name}")
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def _log_filtering_event(self, event: str, details: Dict[str, Any]) -> None:
        """Log a filtering event for debugging."""
        log_entry = {
            'timestamp': time.time(),
            'event': event,
            'details': details,
            'status': self.status.value
        }
        
        self.execution_history.append(log_entry)
        self.logger.info(f"Filtering event: {event} - {details}")
    
    def get_filtering_summary(self) -> Dict[str, Any]:
        """Get summary of filtering executions."""
        return {
            'stats': self.filtering_stats.copy(),
            'success_rate': (
                self.filtering_stats['successful_filterings'] / 
                max(self.filtering_stats['total_filterings'], 1)
            ),
            'average_filter_ratio': (
                self.filtering_stats['total_items_filtered'] / 
                max(self.filtering_stats['total_items_processed'], 1)
            ) if self.filtering_stats['total_items_processed'] > 0 else 0,
            'last_execution': self.execution_history[-1] if self.execution_history else None,
            'total_executions': len(self.execution_history)
        }
    
    def reset_stats(self) -> None:
        """Reset filtering statistics."""
        self.filtering_stats = {
            'total_filterings': 0,
            'successful_filterings': 0,
            'failed_filterings': 0,
            'total_items_processed': 0,
            'total_items_filtered': 0
        }
        self.execution_history.clear()


class AuthenticationStatus(Enum):
    """Authentication flow status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    LOCKED = "locked"
    REQUIRES_2FA = "requires_2fa"
    RATE_LIMITED = "rate_limited"


@dataclass
class AuthenticationResult:
    """Result of an authentication operation."""
    success: bool
    authenticated: bool
    session_data: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_time: float
    metadata: Dict[str, Any]
    security_warnings: List[str] = None
    retry_after: Optional[float] = None
    
    def __post_init__(self):
        if self.security_warnings is None:
            self.security_warnings = []


class BaseAuthenticationFlow(ABC):
    """Base class for all authentication flows with security utilities."""
    
    def __init__(self, page, selector_engine, config=None):
        """
        Initialize base authentication flow.
        
        Args:
            page: Playwright page instance
            selector_engine: Selector engine instance
            config: Optional configuration dictionary
        """
        self.page = page
        self.selector_engine = selector_engine
        self.config = config or {}
        self.status = AuthenticationStatus.IDLE
        self.start_time = None
        self.execution_history = []
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.auth_stats = {
            'total_attempts': 0,
            'successful_auths': 0,
            'failed_auths': 0,
            'rate_limit_hits': 0,
            'security_warnings': 0
        }
        self.session_data = {}
        self.security_context = {
            'max_retries': self._get_config_value('max_retries', 3),
            'retry_delay': self._get_config_value('retry_delay', 1.0),
            'timeout_multiplier': self._get_config_value('timeout_multiplier', 1.5),
            'security_headers': self._get_config_value('security_headers', True),
            'csrf_protection': self._get_config_value('csrf_protection', True)
        }
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str], auth_method: str = 'password') -> AuthenticationResult:
        """
        Perform authentication with provided credentials.
        
        Args:
            credentials: Dictionary containing authentication credentials
            auth_method: Authentication method ('password', 'oauth', 'api_key', etc.)
            
        Returns:
            Authentication result with session data
        """
        pass
    
    @abstractmethod
    async def validate_session(self, session_data: Dict[str, Any]) -> AuthenticationResult:
        """
        Validate existing session data.
        
        Args:
            session_data: Session data to validate
            
        Returns:
            Authentication result indicating session validity
        """
        pass
    
    @abstractmethod
    async def refresh_session(self, refresh_token: str = None) -> AuthenticationResult:
        """
        Refresh authentication session.
        
        Args:
            refresh_token: Optional refresh token
            
        Returns:
            Authentication result with updated session data
        """
        pass
    
    async def _execute_with_security(self, operation_name: str, timeout: float, *args, **kwargs) -> AuthenticationResult:
        """
        Execute authentication operation with security utilities.
        
        Args:
            operation_name: Name of the operation for logging
            timeout: Operation timeout in seconds
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Authentication result with security handling
        """
        self.start_time = time.time()
        self.status = AuthenticationStatus.RUNNING
        
        try:
            self.logger.info(f"Starting authentication operation: {operation_name}")
            
            # Apply security measures
            await self._apply_security_measures()
            
            # Validate security context
            security_warnings = await self._validate_security_context()
            if security_warnings:
                self.auth_stats['security_warnings'] += len(security_warnings)
                self.logger.warning(f"Security warnings: {'; '.join(security_warnings)}")
            
            # Execute operation with timeout and retry logic
            result = await self._execute_with_retry(operation_name, timeout, *args, **kwargs)
            
            if result.success:
                self.status = AuthenticationStatus.SUCCESS
                self.auth_stats['successful_auths'] += 1
                
                # Store session data securely
                if result.session_data:
                    await self._store_session_data(result.session_data)
                
                self.logger.info(f"Authentication operation completed: {operation_name}")
            else:
                self.status = AuthenticationStatus.ERROR
                self.auth_stats['failed_auths'] += 1
            
            # Add security warnings to result
            result.security_warnings.extend(security_warnings)
            
            return result
            
        except asyncio.TimeoutError:
            self.status = AuthenticationStatus.TIMEOUT
            self.auth_stats['failed_auths'] += 1
            
            error_msg = f"Authentication operation timed out after {timeout}s: {operation_name}"
            self.logger.error(error_msg)
            
            return AuthenticationResult(
                success=False,
                authenticated=False,
                session_data=None,
                error=error_msg,
                execution_time=time.time() - self.start_time,
                metadata={'operation': operation_name, 'timeout': timeout}
            )
            
        except Exception as e:
            self.status = AuthenticationStatus.ERROR
            self.auth_stats['failed_auths'] += 1
            
            error_msg = f"Authentication operation failed: {operation_name} - {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return AuthenticationResult(
                success=False,
                authenticated=False,
                session_data=None,
                error=error_msg,
                execution_time=time.time() - self.start_time,
                metadata={'operation': operation_name, 'exception': str(e)}
            )
            
        finally:
            self.auth_stats['total_attempts'] += 1
            self._log_authentication_event(operation_name, {
                'status': self.status.value,
                'execution_time': time.time() - self.start_time
            })
    
    async def _apply_security_measures(self) -> None:
        """Apply security measures before authentication."""
        # Set security headers if enabled
        if self.security_context['security_headers']:
            await self.page.set_extra_http_headers({
                'User-Agent': self._get_secure_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
        
        # Clear potentially sensitive cookies
        if self.security_context['csrf_protection']:
            await self.page.context.clear_cookies()
    
    async def _validate_security_context(self) -> List[str]:
        """Validate security context and return warnings."""
        warnings = []
        
        # Check for insecure configurations
        if not self.security_context['csrf_protection']:
            warnings.append("CSRF protection is disabled")
        
        if not self.security_context['security_headers']:
            warnings.append("Security headers are disabled")
        
        if self.security_context['max_retries'] > 5:
            warnings.append("High retry limit may trigger rate limiting")
        
        return warnings
    
    async def _execute_with_retry(self, operation_name: str, timeout: float, *args, **kwargs) -> AuthenticationResult:
        """Execute operation with retry logic."""
        max_retries = self.security_context['max_retries']
        retry_delay = self.security_context['retry_delay']
        
        for attempt in range(max_retries + 1):
            try:
                # Execute the operation
                result = await asyncio.wait_for(
                    self._execute_authentication_operation(operation_name, *args, **kwargs),
                    timeout=timeout
                )
                
                # Check for rate limiting
                if result.retry_after:
                    self.auth_stats['rate_limit_hits'] += 1
                    self.status = AuthenticationStatus.RATE_LIMITED
                    
                    if attempt < max_retries:
                        wait_time = result.retry_after + retry_delay * attempt
                        self.logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                        await asyncio.sleep(wait_time)
                        continue
                
                return result
                
            except Exception as e:
                if attempt == max_retries:
                    raise
                
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}, retrying...")
                await asyncio.sleep(retry_delay * (attempt + 1))
        
        raise Exception(f"All {max_retries + 1} attempts failed")
    
    async def _execute_authentication_operation(self, operation_name: str, *args, **kwargs) -> AuthenticationResult:
        """Execute the actual authentication operation."""
        if operation_name == 'authenticate':
            return await self.authenticate(*args, **kwargs)
        elif operation_name == 'validate_session':
            return await self.validate_session(*args, **kwargs)
        elif operation_name == 'refresh_session':
            return await self.refresh_session(*args, **kwargs)
        else:
            raise ValueError(f"Unknown authentication operation: {operation_name}")
    
    async def _store_session_data(self, session_data: Dict[str, Any]) -> None:
        """Store session data securely."""
        # In a real implementation, this would use secure storage
        # For now, store in memory with basic security
        self.session_data.update(session_data)
        
        # Log session storage (without sensitive data)
        safe_session_data = {k: v for k, v in session_data.items() 
                           if not any(sensitive in k.lower() 
                                     for sensitive in ['password', 'token', 'secret', 'key'])}
        self.logger.info(f"Session data stored: {list(safe_session_data.keys())}")
    
    def _get_secure_user_agent(self) -> str:
        """Generate a secure user agent string."""
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def _log_authentication_event(self, event: str, details: Dict[str, Any]) -> None:
        """Log an authentication event for debugging."""
        log_entry = {
            'timestamp': time.time(),
            'event': event,
            'details': details,
            'status': self.status.value
        }
        
        self.execution_history.append(log_entry)
        self.logger.info(f"Authentication event: {event} - {details}")
    
    def get_authentication_summary(self) -> Dict[str, Any]:
        """Get summary of authentication executions."""
        return {
            'stats': self.auth_stats.copy(),
            'success_rate': (
                self.auth_stats['successful_auths'] / 
                max(self.auth_stats['total_attempts'], 1)
            ),
            'rate_limit_rate': (
                self.auth_stats['rate_limit_hits'] / 
                max(self.auth_stats['total_attempts'], 1)
            ),
            'last_execution': self.execution_history[-1] if self.execution_history else None,
            'total_executions': len(self.execution_history),
            'session_active': bool(self.session_data)
        }
    
    def reset_stats(self) -> None:
        """Reset authentication statistics."""
        self.auth_stats = {
            'total_attempts': 0,
            'successful_auths': 0,
            'failed_auths': 0,
            'rate_limit_hits': 0,
            'security_warnings': 0
        }
        self.execution_history.clear()
        self.session_data.clear()
    
    async def logout(self) -> AuthenticationResult:
        """Logout and clear session data."""
        try:
            self.logger.info("Logging out and clearing session")
            
            # Clear cookies and session data
            await self.page.context.clear_cookies()
            self.session_data.clear()
            self.status = AuthenticationStatus.IDLE
            
            return AuthenticationResult(
                success=True,
                authenticated=False,
                session_data=None,
                error=None,
                execution_time=0,
                metadata={'action': 'logout'}
            )
            
        except Exception as e:
            self.logger.error(f"Logout failed: {str(e)}")
            return AuthenticationResult(
                success=False,
                authenticated=False,
                session_data=None,
                error=str(e),
                execution_time=0,
                metadata={'action': 'logout', 'error': str(e)}
            )
