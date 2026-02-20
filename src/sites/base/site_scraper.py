"""
Modular base site scraper with component support.

Defines the contract that all site scrapers must implement.
Provides common functionality and enforces required methods.
Integrates with the modular component system for flows, processors, and validators.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import inspect
from datetime import datetime
import asyncio
from playwright.async_api import Page

from src.observability.logger import get_logger
from .component_interface import BaseComponent, ComponentContext, ComponentResult
from .component_manager import ComponentManager
from .configuration_manager import ConfigurationManager, Environment
from .di_container import DIContainer
from .base_flow import BaseFlow, FlowState
from .base_processor import BaseProcessor
from .base_validator import BaseValidator

# Module logger
logger = get_logger(__name__)


class ModularSiteScraper(ABC):
    """Base class for site scrapers with modular component support."""
    
    # Class attributes (must be defined by implementation)
    site_id: str
    site_name: str
    base_url: str
    
    def __init__(
        self,
        page: Page,
        selector_engine,
        component_manager: Optional[ComponentManager] = None,
        config_manager: Optional[ConfigurationManager] = None,
        di_container: Optional[DIContainer] = None,
        environment: Environment = Environment.DEV
    ):
        """
        Initialize enhanced scraper with modular components.
        
        Args:
            page: Playwright page object
            selector_engine: Selector engine instance
            component_manager: Component manager for modular components
            config_manager: Configuration manager for multi-environment configs
            di_container: Dependency injection container
            environment: Target environment
        """
        self.page = page
        self.selector_engine = selector_engine
        self.component_manager = component_manager
        self.config_manager = config_manager
        self.di_container = di_container
        self.environment = environment
        
        # Component instances
        self._flows: Dict[str, BaseFlow] = {}
        self._processors: Dict[str, BaseProcessor] = {}
        self._validators: Dict[str, BaseValidator] = {}
        
        # Execution state
        self._execution_context: Optional[ComponentContext] = None
        self._flow_state: Optional[FlowState] = None
        self._execution_stats = {
            'total_scrapes': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'average_execution_time_ms': 0.0
        }
        
        # Validate class attributes at initialization
        self._validate_class_attributes()
        self._validate_method_signatures()
        
        # Initialize modular components
        asyncio.create_task(self._initialize_modular_components())
    
    async def _initialize_modular_components(self) -> None:
        """Initialize modular components."""
        try:
            # Initialize configuration manager
            if self.config_manager:
                await self.config_manager.initialize(self.environment)
            
            # Initialize component manager
            if self.component_manager:
                await self.component_manager.initialize()
            
            # Create execution context
            self._execution_context = ComponentContext(
                page=self.page,
                selector_engine=self.selector_engine,
                navigation_state={},
                session_data={},
                correlation_id=f"{self.site_id}_{datetime.utcnow().timestamp()}",
                environment=self.environment.value
            )
            
            # Register dependencies in DI container
            if self.di_container:
                self.di_container.register_instance("page", self.page)
                self.di_container.register_instance("selector_engine", self.selector_engine)
                self.di_container.register_instance("scraper", self)
                if self._execution_context:
                    self.di_container.register_instance("context", self._execution_context)
            
            # Modular components initialized successfully
            # The scraper is ready for use
            
        except Exception as e:
            logger.error("Failed to initialize modular components", error=str(e))
    
    async def register_flow(self, flow: BaseFlow) -> bool:
        """
        Register a flow component.
        
        Args:
            flow: Flow component to register
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.component_manager:
                logger.warning("Component manager not available")
                return False
            
            # Initialize flow
            if not await flow.initialize(self._execution_context):
                return False
            
            # Store flow
            self._flows[flow.component_id] = flow
            
            # Register in component manager
            instance_id = await self.component_manager.create_instance(
                flow.component_id,
                self._execution_context
            )
            
            logger.debug("Registered flow", flow_id=flow.component_id)
            return True
        
        except Exception as e:
            logger.error("Failed to register flow", flow_id=flow.component_id, error=str(e))
            return False
    
    async def register_processor(self, processor: BaseProcessor) -> bool:
        """
        Register a processor component.
        
        Args:
            processor: Processor component to register
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.component_manager:
                print("Component manager not available")
                return False
            
            # Initialize processor
            if not await processor.initialize(self._execution_context):
                return False
            
            # Store processor
            self._processors[processor.component_id] = processor
            
            # Register in component manager
            instance_id = await self.component_manager.create_instance(
                processor.component_id,
                self._execution_context
            )
            
            logger.debug("Registered processor", processor_id=processor.component_id)
            return True
        
        except Exception as e:
            logger.error("Failed to register processor", processor_id=processor.component_id, error=str(e))
            return False
    
    async def register_validator(self, validator: BaseValidator) -> bool:
        """
        Register a validator component.
        
        Args:
            validator: Validator component to register
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.component_manager:
                logger.warning("Component manager not available")
                return False
            
            # Initialize validator
            if not await validator.initialize(self._execution_context):
                return False
            
            # Store validator
            self._validators[validator.component_id] = validator
            
            # Register in component manager
            instance_id = await self.component_manager.create_instance(
                validator.component_id,
                self._execution_context
            )
            
            logger.debug("Registered validator", validator_id=validator.component_id)
            return True
        
        except Exception as e:
            logger.error("Failed to register validator", validator_id=validator.component_id, error=str(e))
            return False
    
    async def execute_flow(self, flow_id: str, **kwargs) -> ComponentResult:
        """
        Execute a registered flow.
        
        Args:
            flow_id: Flow component ID
            **kwargs: Flow execution arguments
            
        Returns:
            Flow execution result
        """
        try:
            if flow_id not in self._flows:
                raise ValueError(f"Flow {flow_id} not registered")
            
            flow = self._flows[flow_id]
            result = await flow.execute(**kwargs)
            
            # Update flow state
            if hasattr(result, 'data') and 'flow_state' in result.data:
                self._flow_state = result.data['flow_state']
            
            return result
            
        except Exception as e:
            logger.error("Failed to execute flow", flow_id=flow_id, error=str(e))
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def process_data(self, processor_id: str, data: Any) -> ComponentResult:
        """
        Process data using a registered processor.
        
        Args:
            processor_id: Processor component ID
            data: Data to process
            
        Returns:
            Processing result
        """
        try:
            if processor_id not in self._processors:
                raise ValueError(f"Processor {processor_id} not registered")
            
            processor = self._processors[processor_id]
            return await processor.execute(data=data)
            
        except Exception as e:
            logger.error("Failed to process data", processor_id=processor_id, error=str(e))
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def validate_data(self, validator_id: str, data: Any) -> ComponentResult:
        """
        Validate data using a registered validator.
        
        Args:
            validator_id: Validator component ID
            data: Data to validate
            
        Returns:
            Validation result
        """
        try:
            if validator_id not in self._validators:
                raise ValueError(f"Validator {validator_id} not registered")
            
            validator = self._validators[validator_id]
            return await validator.execute(target=data)
            
        except Exception as e:
            logger.error("Failed to validate data", validator_id=validator_id, error=str(e))
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def get_config(self, key: str = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (None for full config)
            
        Returns:
            Configuration value or full config
        """
        if not self.config_manager:
            return None
        
        config = await self.config_manager.get_config(self.environment)
        
        if key:
            return config.get(key)
        
        return config
    
    async def scrape_with_components(self, **kwargs) -> Dict[str, Any]:
        """
        Execute modular scraping using registered components.
        
        Args:
            **kwargs: Scraping arguments
            
        Returns:
            Scraped and processed data
        """
        try:
            start_time = datetime.utcnow()
            
            # Update execution stats
            self._execution_stats['total_scrapes'] += 1
            
            # Execute navigation flow if available
            if 'navigation_flow' in self._flows:
                nav_result = await self.execute_flow('navigation_flow')
                if not nav_result.success:
                    self._execution_stats['failed_scrapes'] += 1
                    return {'error': 'Navigation failed', 'details': nav_result.errors}
            
            # Perform base scraping
            raw_data = await self.scrape(**kwargs)
            
            # Process data through processors
            processed_data = raw_data
            for processor_id, processor in self._processors.items():
                process_result = await self.process_data(processor_id, processed_data)
                if process_result.success:
                    processed_data = process_result.data.get('transformation_result', {}).get('output_data', processed_data)
            
            # Validate data through validators
            validation_results = {}
            for validator_id, validator in self._validators.items():
                validation_result = await self.validate_data(validator_id, processed_data)
                validation_results[validator_id] = validation_result
            
            # Normalize final data
            normalized_data = self.normalize(processed_data)
            
            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Update stats
            self._execution_stats['successful_scrapes'] += 1
            total = self._execution_stats['total_scrapes']
            current_avg = self._execution_stats['average_execution_time_ms']
            self._execution_stats['average_execution_time_ms'] = (
                (current_avg * (total - 1) + execution_time) / total
            )
            
            return {
                'raw_data': raw_data,
                'processed_data': processed_data,
                'validation_results': validation_results,
                'normalized_data': normalized_data,
                'execution_time_ms': execution_time,
                'flow_state': self._flow_state.__dict__ if self._flow_state else None,
                'stats': self._execution_stats
            }
            
        except Exception as e:
            self._execution_stats['failed_scrapes'] += 1
            self.logger.error(f"Modular scraping failed: {str(e)}")
            return {
                'error': str(e),
                'stats': self._execution_stats
            }
    
    def _validate_class_attributes(self) -> None:
        """Validate that required class attributes are properly defined."""
        required_attrs = ['site_id', 'site_name', 'base_url']
        
        for attr in required_attrs:
            if not hasattr(self.__class__, attr):
                raise AttributeError(f"Missing required class attribute: {attr}")
            
            value = getattr(self.__class__, attr)
            if not isinstance(value, str):
                raise TypeError(f"Class attribute '{attr}' must be a string")
            
            if not value.strip():
                raise ValueError(f"Class attribute '{attr}' cannot be empty")
    
    def _validate_method_signatures(self) -> None:
        """Validate that required methods have correct signatures."""
        required_methods = ['navigate', 'scrape', 'normalize']
        
        for method_name in required_methods:
            if not hasattr(self, method_name):
                raise NotImplementedError(f"Missing required method: {method_name}")
            
            method = getattr(self, method_name)
            if not callable(method):
                raise TypeError(f"Attribute '{method_name}' is not callable")
            
            # Get unbound method from class for proper signature inspection
            unbound_method = getattr(self.__class__, method_name)
            
            # Validate method signature
            self._validate_method_signature(method_name, unbound_method)
    
    def _validate_method_signature(self, method_name: str, method) -> None:
        """Validate specific method signature requirements."""
        try:
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            if method_name == 'navigate':
                # navigate() should take only self
                if len(params) > 1:
                    raise ValueError(f"navigate() method should take no parameters besides self, got: {params}")
            
            elif method_name == 'scrape':
                # scrape() should take self and **kwargs
                if len(params) < 1:
                    raise ValueError(f"scrape() method must accept **kwargs")
                elif len(params) > 2:
                    raise ValueError(f"scrape() method should only take **kwargs beyond self, got: {params}")
                
                # Check if **kwargs is properly defined
                if len(params) == 2:
                    param = sig.parameters[params[1]]
                    if param.kind != inspect.Parameter.VAR_KEYWORD:
                        raise ValueError(f"scrape() method second parameter must be **kwargs")
            
            elif method_name == 'normalize':
                # normalize() should take self and raw_data
                if len(params) != 2:
                    raise ValueError(f"normalize() method must take exactly one parameter (raw_data), got: {params}")
                
                if 'raw_data' not in params:
                    raise ValueError(f"normalize() method must have 'raw_data' parameter")
                
                param = sig.parameters['raw_data']
                if param.kind == inspect.Parameter.VAR_POSITIONAL:
                    raise ValueError(f"normalize() method raw_data parameter should not be *args")
                elif param.kind == inspect.Parameter.VAR_KEYWORD:
                    raise ValueError(f"normalize() method raw_data parameter should not be **kwargs")
        
        except Exception as e:
            raise ValueError(f"Invalid method signature for {method_name}(): {str(e)}")
    
    @abstractmethod
    async def navigate(self) -> None:
        """Bring page to initial ready state for scraping."""
        pass
    
    @abstractmethod
    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """Perform scraping using configured selectors."""
        pass
    
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw scraped data into structured output."""
        pass
    
    def get_site_info(self) -> Dict[str, str]:
        """Get site information for debugging and logging."""
        return {
            "site_id": self.site_id,
            "site_name": self.site_name,
            "base_url": self.base_url,
            "class_name": self.__class__.__name__,
            "module": self.__class__.__module__
        }
    
    def validate_state(self) -> Dict[str, Any]:
        """Validate scraper state and return status information."""
        return {
            "initialized": True,
            "has_page": self.page is not None,
            "has_selector_engine": self.selector_engine is not None,
            "has_component_manager": self.component_manager is not None,
            "has_config_manager": self.config_manager is not None,
            "has_di_container": self.di_container is not None,
            "flows_count": len(self._flows),
            "processors_count": len(self._processors),
            "validators_count": len(self._validators),
            "environment": self.environment.value,
            "site_info": self.get_site_info(),
            "execution_stats": self._execution_stats
        }
    
    async def cleanup(self) -> None:
        """Clean up scraper resources."""
        try:
            # Clean up flows
            for flow_id, flow in self._flows.items():
                await flow.cleanup()
            
            # Clean up processors
            for processor_id, processor in self._processors.items():
                await processor.cleanup()
            
            # Clean up validators
            for validator_id, validator in self._validators.items():
                await validator.cleanup()
            
            # Clean up component manager
            if self.component_manager:
                await self.component_manager.cleanup()
            
            # Clean up config manager
            if self.config_manager:
                await self.config_manager.cleanup()
            
            # Clean up DI container
            if self.di_container:
                await self.di_container.cleanup()
            
            # Clear component references
            self._flows.clear()
            self._processors.clear()
            self._validators.clear()
            
            logger.info("Modular scraper cleanup completed", site_id=self.site_id)
        
        except Exception as e:
            logger.error("Error during scraper cleanup", error=str(e))


# Legacy compatibility
class BaseSiteScraper(ModularSiteScraper):
    """Legacy base class for backward compatibility."""
    
    def __init__(self, page: Page, selector_engine):
        """Initialize legacy scraper without modular components."""
        super().__init__(
            page=page,
            selector_engine=selector_engine,
            component_manager=None,
            config_manager=None,
            di_container=None,
            environment=Environment.DEV
        )
