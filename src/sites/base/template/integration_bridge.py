"""
Integration bridge base classes for the Site Template Integration Framework.

This module provides concrete implementations of the integration bridge interface,
enabling seamless connection between site-specific components and existing framework infrastructure.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from .interfaces import IIntegrationBridge, IntegrationStatus


logger = logging.getLogger(__name__)


class BridgeType(Enum):
    """Types of integration bridges."""
    SELECTOR_LOADER = "selector_loader"
    EXTRACTOR_BRIDGE = "extractor_bridge"
    LIFECYCLE_BRIDGE = "lifecycle_bridge"
    FULL_INTEGRATION = "full_integration"


class BridgeStatus(Enum):
    """Bridge status enumeration."""
    INITIALIZED = "initialized"
    CONFIGURED = "configured"
    ACTIVE = "active"
    ERROR = "error"
    RECOVERED = "recovered"


class BaseIntegrationBridge(IIntegrationBridge):
    """
    Base implementation of IIntegrationBridge that provides common functionality
    for all integration bridges.
    """
    
    def __init__(
        self,
        template_name: str,
        bridge_type: BridgeType,
        selector_engine: Any,
        page: Any,
        configuration: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the base integration bridge.
        
        Args:
            template_name: Name of the associated template
            bridge_type: Type of integration bridge
            selector_engine: Framework selector engine instance
            page: Playwright page instance
            configuration: Bridge-specific configuration
        """
        self.template_name = template_name
        self.bridge_type = bridge_type
        self.selector_engine = selector_engine
        self.page = page
        self.configuration = configuration or {}
        
        # Bridge state
        self.status = BridgeStatus.INITIALIZED
        self.enabled = True
        self.priority = 0
        self.last_updated = datetime.now()
        
        # Integration metrics
        self.selector_count = 0
        self.extraction_rule_count = 0
        self.integration_attempts = 0
        self.integration_successes = 0
        
        # Error tracking
        self.error_details: Optional[Dict[str, Any]] = None
        self.last_error: Optional[Exception] = None
        
        logger.info(f"BaseIntegrationBridge initialized for {template_name} ({bridge_type.value})")
    
    async def initialize(self) -> bool:
        """
        Initialize the integration bridge.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info(f"Initializing integration bridge for {self.template_name}")
            
            # Validate prerequisites
            if not await self._validate_prerequisites():
                logger.error("Prerequisites validation failed")
                return False
            
            # Auto-configure components
            await self._auto_configure_components()
            
            # Configure bridge
            if not await self._configure_bridge():
                logger.error("Bridge configuration failed")
                return False
            
            # Load selectors
            if not await self._load_selectors():
                logger.error("Selector loading failed")
                return False
            
            # Setup extraction rules
            if not await self._setup_extraction_rules():
                logger.error("Extraction rules setup failed")
                return False
            
            # Finalize integration
            if not await self._finalize_integration():
                logger.error("Integration finalization failed")
                return False
            
            self.initialized = True
            logger.info(f"Integration bridge initialized successfully for {self.template_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize integration bridge: {e}")
            return False
    
    async def _configure_bridge(self) -> bool:
        """
        Configure the bridge with template-specific settings.
        
        Returns:
            bool: True if configuration successful
        """
        try:
            # Apply configuration settings
            # This would typically load from template configuration
            # For now, use default settings
            
            logger.debug(f"Bridge {self.template_name} configured")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure bridge: {e}")
            return False
    
    async def initialize_complete_integration(self) -> bool:
        """
        Initialize complete framework integration.
        
        Returns:
            bool: True if integration successful
        """
        try:
            self.integration_attempts += 1
            
            logger.info(f"Initializing complete integration for {self.template_name}")
            
            # Validate prerequisites
            if not await self._validate_prerequisites():
                logger.error(f"Prerequisites validation failed for {self.template_name}")
                return False
            
            # Configure bridge
            if not await self._configure_bridge():
                logger.error(f"Bridge configuration failed for {self.template_name}")
                return False
            
            # Load selectors
            if not await self.load_selectors():
                logger.error(f"Selector loading failed for {self.template_name}")
                return False
            
            # Setup extraction rules
            if not await self.setup_extraction_rules():
                logger.error(f"Extraction rules setup failed for {self.template_name}")
                return False
            
            # Finalize integration
            if not await self._finalize_integration():
                logger.error(f"Integration finalization failed for {self.template_name}")
                return False
            
            self.status = BridgeStatus.ACTIVE
            self.integration_successes += 1
            self.last_updated = datetime.now()
            self.error_details = None
            self.last_error = None
            
            logger.info(f"Complete integration initialized successfully for {self.template_name}")
            return True
            
        except Exception as e:
            self.status = BridgeStatus.ERROR
            self.last_error = e
            self.error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat(),
                "integration_attempt": self.integration_attempts
            }
            
            logger.error(f"Failed to initialize complete integration for {self.template_name}: {e}")
            return False
    
    async def load_selectors(self) -> bool:
        """
        Load YAML selectors into existing selector engine.
        
        Returns:
            bool: True if selectors loaded successfully
        """
        try:
            logger.info(f"Loading selectors for {self.template_name}")
            
            # Get selector configurations
            selector_configs = await self._get_selector_configurations()
            
            if not selector_configs:
                logger.warning(f"No selector configurations found for {self.template_name}")
                return True  # Not an error, just no selectors to load
            
            # Register each selector
            loaded_count = 0
            for selector_name, config in selector_configs.items():
                if await self._register_single_selector(selector_name, config):
                    loaded_count += 1
                else:
                    logger.warning(f"Failed to register selector: {selector_name}")
            
            self.selector_count = loaded_count
            logger.info(f"Loaded {loaded_count} selectors for {self.template_name}")
            
            return loaded_count > 0 or len(selector_configs) == 0
            
        except Exception as e:
            logger.error(f"Failed to load selectors for {self.template_name}: {e}")
            return False
    
    async def setup_extraction_rules(self) -> bool:
        """
        Setup extraction rules using existing extractor module.
        
        Returns:
            bool: True if rules setup successful
        """
        try:
            logger.info(f"Setting up extraction rules for {self.template_name}")
            
            # Get extraction rule configurations
            rule_configs = await self._get_extraction_rule_configurations()
            
            if not rule_configs:
                logger.warning(f"No extraction rule configurations found for {self.template_name}")
                return True  # Not an error, just no rules to setup
            
            # Setup each rule set
            setup_count = 0
            for rule_set_name, config in rule_configs.items():
                if await self._setup_single_rule_set(rule_set_name, config):
                    setup_count += 1
                else:
                    logger.warning(f"Failed to setup rule set: {rule_set_name}")
            
            self.extraction_rule_count = setup_count
            logger.info(f"Setup {setup_count} extraction rule sets for {self.template_name}")
            
            return setup_count > 0 or len(rule_configs) == 0
            
        except Exception as e:
            logger.error(f"Failed to setup extraction rules for {self.template_name}: {e}")
            return False
    
    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get current integration status and health.
        
        Returns:
            Dict[str, Any]: Integration status information
        """
        return {
            "template_name": self.template_name,
            "bridge_type": self.bridge_type.value,
            "status": self.status.value,
            "enabled": self.enabled,
            "priority": self.priority,
            "is_integrated": self.status == BridgeStatus.ACTIVE,
            "selector_count": self.selector_count,
            "extraction_rule_count": self.extraction_rule_count,
            "bridge_status": self.status.value,
            "last_updated": self.last_updated.isoformat(),
            "integration_attempts": self.integration_attempts,
            "integration_successes": self.integration_successes,
            "success_rate": self.integration_successes / max(self.integration_attempts, 1),
            "health_metrics": self._get_health_metrics(),
            "error_details": self.error_details
        }
    
    async def _validate_prerequisites(self) -> bool:
        """
        Validate that prerequisites for integration are met.
        
        Returns:
            bool: True if prerequisites are valid
        """
        # Check if selector engine is available
        if not self.selector_engine:
            logger.error("Selector engine not available")
            return False
        
        # Check if page is available
        if not self.page:
            logger.error("Page not available")
            return False
        
        # Check if bridge is enabled
        if not self.enabled:
            logger.warning(f"Bridge {self.template_name} is disabled")
            return False
        
        # Auto-detect and validate framework components
        return await self._detect_framework_components()
    
    async def _detect_framework_components(self) -> bool:
        """
        Auto-detect available framework components.
        
        Returns:
            bool: True if core components are available
        """
        try:
            logger.debug("Auto-detecting framework components")
            
            self.available_components = {
                "selector_engine": self._detect_selector_engine(),
                "extractor_module": self._detect_extractor_module(),
                "browser_lifecycle": self._detect_browser_lifecycle(),
                "screenshot_capture": self._detect_screenshot_capture(),
                "html_capture": self._detect_html_capture(),
                "resource_monitoring": self._detect_resource_monitoring(),
                "stealth_features": self._detect_stealth_features(),
                "logging_framework": self._detect_logging_framework()
            }
            
            # Validate core required components
            required_components = ["selector_engine", "extractor_module"]
            missing_required = [comp for comp in required_components if not self.available_components.get(comp, {}).get("available", False)]
            
            if missing_required:
                logger.error(f"Missing required framework components: {missing_required}")
                return False
            
            logger.info(f"Framework components detected: {[comp for comp, info in self.available_components.items() if info.get('available')]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to detect framework components: {e}")
            return False
    
    def _detect_selector_engine(self) -> Dict[str, Any]:
        """Detect selector engine availability and capabilities."""
        try:
            if not self.selector_engine:
                return {"available": False, "error": "Not provided"}
            
            capabilities = {
                "available": True,
                "supports_registration": hasattr(self.selector_engine, 'register_selector'),
                "supports_find_all": hasattr(self.selector_engine, 'find_all'),
                "supports_validation": hasattr(self.selector_engine, 'validate_selector'),
                "supports_confidence_scoring": hasattr(self.selector_engine, 'get_confidence_score'),
                "version": getattr(self.selector_engine, '__version__', 'unknown')
            }
            
            return capabilities
            
        except Exception as e:
            logger.debug(f"Error detecting selector engine: {e}")
            return {"available": False, "error": str(e)}
    
    def _detect_extractor_module(self) -> Dict[str, Any]:
        """Detect extractor module availability and capabilities."""
        try:
            # Try to import extractor module
            from src.extractor import Extractor, ExtractionRule, ExtractionType, DataType, TransformationType
            
            capabilities = {
                "available": True,
                "supports_extraction_rules": True,
                "supports_transformations": True,
                "supports_validation": True,
                "version": "1.0.0",  # This could be extracted from the module
                "available_types": [t.value for t in ExtractionType],
                "available_data_types": [t.value for t in DataType],
                "available_transformations": [t.value for t in TransformationType]
            }
            
            return capabilities
            
        except ImportError:
            return {"available": False, "error": "Extractor module not found"}
        except Exception as e:
            logger.debug(f"Error detecting extractor module: {e}")
            return {"available": False, "error": str(e)}
    
    def _detect_browser_lifecycle(self) -> Dict[str, Any]:
        """Detect browser lifecycle management capabilities."""
        try:
            if not self.page:
                return {"available": False, "error": "Page not provided"}
            
            capabilities = {
                "available": True,
                "supports_screenshot": hasattr(self.page, 'screenshot'),
                "supports_pdf": hasattr(self.page, 'pdf'),
                "supports_video": hasattr(self.page, 'video'),
                "supports_navigation": hasattr(self.page, 'goto'),
                "supports_wait": hasattr(self.page, 'wait_for_selector'),
                "supports_evaluate": hasattr(self.page, 'evaluate'),
                "browser_type": getattr(self.page, '_browser_type', 'unknown')
            }
            
            return capabilities
            
        except Exception as e:
            logger.debug(f"Error detecting browser lifecycle: {e}")
            return {"available": False, "error": str(e)}
    
    def _detect_screenshot_capture(self) -> Dict[str, Any]:
        """Detect screenshot capture capabilities."""
        try:
            if not self.page:
                return {"available": False, "error": "Page not provided"}
            
            # Check if screenshot functionality is available
            screenshot_available = hasattr(self.page, 'screenshot')
            
            capabilities = {
                "available": screenshot_available,
                "supports_full_page": screenshot_available,
                "supports_viewport": screenshot_available,
                "supports_element": screenshot_available,
                "supports_multiple_formats": screenshot_available,  # PNG, JPEG, etc.
                "supports_quality_control": screenshot_available
            }
            
            return capabilities
            
        except Exception as e:
            logger.debug(f"Error detecting screenshot capture: {e}")
            return {"available": False, "error": str(e)}
    
    def _detect_html_capture(self) -> Dict[str, Any]:
        """Detect HTML capture capabilities."""
        try:
            if not self.page:
                return {"available": False, "error": "Page not provided"}
            
            # Check if HTML content can be captured
            html_available = hasattr(self.page, 'content') and hasattr(self.page, 'evaluate')
            
            capabilities = {
                "available": html_available,
                "supports_full_html": html_available,
                "supports_element_html": html_available,
                "supports_dynamic_content": html_available,
                "supports_clean_html": html_available
            }
            
            return capabilities
            
        except Exception as e:
            logger.debug(f"Error detecting HTML capture: {e}")
            return {"available": False, "error": str(e)}
    
    def _detect_resource_monitoring(self) -> Dict[str, Any]:
        """Detect resource monitoring capabilities."""
        try:
            # Try to import resource monitoring components
            monitoring_available = False
            monitoring_version = "unknown"
            
            try:
                from src.monitoring import ResourceMonitor
                monitoring_available = True
                monitoring_version = getattr(ResourceMonitor, '__version__', '1.0.0')
            except ImportError:
                pass
            
            capabilities = {
                "available": monitoring_available,
                "supports_memory_monitoring": monitoring_available,
                "supports_cpu_monitoring": monitoring_available,
                "supports_network_monitoring": monitoring_available,
                "supports_disk_monitoring": monitoring_available,
                "version": monitoring_version
            }
            
            return capabilities
            
        except Exception as e:
            logger.debug(f"Error detecting resource monitoring: {e}")
            return {"available": False, "error": str(e)}
    
    async def _detect_stealth_features(self) -> Dict[str, Any]:
        """Detect stealth and anti-bot detection features."""
        try:
            if not self.page:
                return {"available": False, "error": "Page not provided"}
            
            # Check for stealth capabilities
            stealth_available = hasattr(self.page, 'context') and hasattr(self.page, 'route')
            
            capabilities = {
                "available": stealth_available,
                "supports_user_agent_rotation": stealth_available,
                "supports_viewport_randomization": stealth_available,
                "supports_geolocation": stealth_available,
                "supports_permission_control": stealth_available,
                "supports_request_interception": stealth_available,
                "supports_cookie_management": stealth_available,
                "supports_header_modification": stealth_available,
                "supports_javascript_injection": stealth_available,
                "supports_proxy_routing": stealth_available
            }
            
            return capabilities
            
        except Exception as e:
            logger.debug(f"Error detecting stealth features: {e}")
            return {"available": False, "error": str(e)}
    
    def _detect_logging_framework(self) -> Dict[str, Any]:
        """Detect structured logging framework."""
        try:
            # Try to import logging components
            logging_available = False
            logging_version = "unknown"
            
            try:
                import structlog
                logging_available = True
                logging_version = getattr(structlog, '__version__', 'unknown')
            except ImportError:
                try:
                    import logging
                    logging_available = True
                    logging_version = "standard"
                except ImportError:
                    pass
            
            capabilities = {
                "available": logging_available,
                "supports_structured_logging": logging_available,
                "supports_correlation_ids": logging_available,
                "supports_performance_logging": logging_available,
                "version": logging_version
            }
            
            return capabilities
            
        except Exception as e:
            logger.debug(f"Error detecting logging framework: {e}")
            return {"available": False, "error": str(e)}
    
    def get_available_components(self) -> Dict[str, Any]:
        """
        Get information about available framework components.
        
        Returns:
            Dict[str, Any]: Available components information
        """
        return getattr(self, 'available_components', {})
    
    def is_component_available(self, component_name: str) -> bool:
        """
        Check if a specific component is available.
        
        Args:
            component_name: Name of the component to check
            
        Returns:
            bool: True if component is available
        """
        components = self.get_available_components()
        return components.get(component_name, {}).get("available", False)
    
    async def _auto_configure_components(self) -> None:
        """
        Auto-configure framework components based on detected capabilities.
        """
        try:
            logger.debug("Auto-configuring framework components")
            
            # Auto-configure browser lifecycle features
            await self._auto_configure_browser_lifecycle()
            
            # Auto-configure resource monitoring
            await self._auto_configure_resource_monitoring()
            
            # Auto-configure logging framework
            await self._auto_configure_logging_framework()
            
            # Auto-configure stealth features
            await self._auto_configure_stealth_features()
            
            logger.debug("Framework component auto-configuration completed")
            
        except Exception as e:
            logger.error(f"Failed to auto-configure components: {e}")
    
    async def _auto_configure_browser_lifecycle(self) -> None:
        """Auto-configure browser lifecycle features."""
        try:
            browser_capabilities = self.available_components.get("browser_lifecycle", {})
            screenshot_capabilities = self.available_components.get("screenshot_capture", {})
            html_capabilities = self.available_components.get("html_capture", {})
            
            if browser_capabilities.get("available", False):
                # Configure browser settings
                browser_config = {
                    "auto_screenshot": screenshot_capabilities.get("available", False),
                    "auto_html_capture": html_capabilities.get("available", False),
                    "screenshot_on_error": True,
                    "html_capture_on_error": True,
                    "screenshot_format": "png",
                    "screenshot_quality": 90,
                    "html_capture_clean": True
                }
                
                # Store configuration for browser lifecycle integration
                self.browser_lifecycle_config = browser_config
                
                logger.debug(f"Browser lifecycle auto-configured: {list(browser_config.keys())}")
            
        except Exception as e:
            logger.debug(f"Failed to auto-configure browser lifecycle: {e}")
    
    async def _auto_configure_resource_monitoring(self) -> None:
        """Auto-configure resource monitoring."""
        try:
            resource_capabilities = self.available_components.get("resource_monitoring", {})
            
            if resource_capabilities.get("available", False):
                # Configure resource monitoring settings
                monitoring_config = {
                    "auto_monitoring": True,
                    "monitoring_interval": 5.0,
                    "memory_threshold": 80.0,
                    "cpu_threshold": 80.0,
                    "disk_threshold": 90.0,
                    "network_threshold": 1000000,
                    "alert_on_threshold": True,
                    "cleanup_on_threshold": False,
                    "max_monitoring_time": 3600
                }
                
                # Store configuration for resource monitoring integration
                self.resource_monitoring_config = monitoring_config
                
                logger.debug(f"Resource monitoring auto-configured: {list(monitoring_config.keys())}")
            
        except Exception as e:
            logger.debug(f"Failed to auto-configure resource monitoring: {e}")
    
    async def _auto_configure_logging_framework(self) -> None:
        """Auto-configure logging framework."""
        try:
            logging_capabilities = self.available_components.get("logging_framework", {})
            
            if logging_capabilities.get("available", False):
                # Configure logging settings
                logging_config = {
                    "auto_logging": True,
                    "log_level": "INFO",
                    "log_format": "structured" if logging_capabilities.get("supports_structured_logging", False) else "standard",
                    "include_performance": logging_capabilities.get("supports_performance_logging", False),
                    "include_correlation": logging_capabilities.get("supports_correlation_ids", False),
                    "log_to_file": False,
                    "error_log_separate": True
                }
                
                # Store configuration for logging integration
                self.logging_config = logging_config
                
                logger.debug(f"Logging framework auto-configured: {list(logging_config.keys())}")
            
        except Exception as e:
            logger.debug(f"Failed to auto-configure logging framework: {e}")
    
    async def _auto_configure_stealth_features(self) -> None:
        """Auto-configure stealth features."""
        try:
            stealth_capabilities = self.available_components.get("stealth_features", {})
            
            if stealth_capabilities.get("available", False):
                # Configure stealth settings
                stealth_config = {
                    "user_agent_rotation": stealth_capabilities.get("supports_user_agent_rotation", False),
                    "viewport_randomization": stealth_capabilities.get("supports_viewport_randomization", False),
                    "geolocation": stealth_capabilities.get("supports_geolocation", False),
                    "permission_control": stealth_capabilities.get("supports_permission_control", False),
                    "request_interception": stealth_capabilities.get("supports_request_interception", False),
                    "cookie_management": stealth_capabilities.get("supports_cookie_management", False),
                    "header_modification": stealth_capabilities.get("supports_header_modification", False),
                    "javascript_injection": stealth_capabilities.get("supports_javascript_injection", False),
                    "proxy_routing": stealth_capabilities.get("supports_proxy_routing", False)
                }
                
                # Store configuration for stealth integration
                self.stealth_config = stealth_config
                
                logger.debug(f"Stealth features auto-configured: {list(stealth_config.keys())}")
            
        except Exception as e:
            logger.debug(f"Failed to auto-configure stealth features: {e}")
    
    def get_auto_configurations(self) -> Dict[str, Any]:
        """
        Get auto-configured component settings.
        
        Returns:
            Dict[str, Any]: Auto-configured settings
        """
        configurations = {}
        
        if hasattr(self, 'browser_lifecycle_config'):
            configurations["browser_lifecycle"] = self.browser_lifecycle_config
        
        if hasattr(self, 'resource_monitoring_config'):
            configurations["resource_monitoring"] = self.resource_monitoring_config
        
        if hasattr(self, 'logging_config'):
            configurations["logging"] = self.logging_config
        
        if hasattr(self, 'stealth_config'):
            configurations["stealth"] = self.stealth_config
        
        return configurations
    
    def get_component_configuration(self, component_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Dict[str, Any]: Component configuration
        """
        configurations = self.get_auto_configurations()
        return configurations.get(component_name, {})
    
    async def apply_component_configuration(self, component_name: str, integration_instance: Any) -> bool:
        """
        Apply auto-configuration to a component integration instance.
        
        Args:
            component_name: Name of the component
            integration_instance: Integration instance to configure
            
        Returns:
            bool: True if configuration applied successfully
        """
        try:
            config = self.get_component_configuration(component_name)
            
            if not config:
                logger.debug(f"No auto-configuration available for {component_name}")
                return False
            
            if hasattr(integration_instance, 'update_config'):
                integration_instance.update_config(config)
                logger.debug(f"Applied auto-configuration to {component_name}")
                return True
            else:
                logger.debug(f"Component {component_name} does not support configuration updates")
                return False
                
        except Exception as e:
            logger.error(f"Failed to apply configuration to {component_name}: {e}")
            return False
    
    async def _get_selector_configurations(self) -> Dict[str, Any]:
        """
        Get selector configurations for the template.
        
        Returns:
            Dict[str, Any]: Selector configurations
        """
        # Override in subclasses to provide selector configurations
        return {}
    
    async def _register_single_selector(self, selector_name: str, config: Dict[str, Any]) -> bool:
        """
        Register a single selector with the selector engine.
        
        Args:
            selector_name: Name of the selector
            config: Selector configuration
            
        Returns:
            bool: True if registration successful
        """
        try:
            # Check if selector engine has register_selector method
            if hasattr(self.selector_engine, 'register_selector'):
                # Create SemanticSelector object from configuration
                from src.models.selector_models import SemanticSelector
                
                selector = SemanticSelector(
                    name=selector_name,
                    strategies=config.get('strategies', []),
                    confidence_threshold=config.get('confidence_threshold', 0.7),
                    validation_rules=config.get('validation_rules', [])
                )
                
                self.selector_engine.register_selector(selector_name, selector)
                return True
            else:
                logger.warning(f"Selector engine does not support registration for {selector_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to register selector {selector_name}: {e}")
            return False
    
    async def _get_extraction_rule_configurations(self) -> Dict[str, Any]:
        """
        Get extraction rule configurations for the template.
        
        Returns:
            Dict[str, Any]: Extraction rule configurations
        """
        # Override in subclasses to provide extraction rule configurations
        return {}
    
    async def _setup_single_rule_set(self, rule_set_name: str, config: Dict[str, Any]) -> bool:
        """
        Setup a single extraction rule set.
        
        Args:
            rule_set_name: Name of the rule set
            config: Rule set configuration
            
        Returns:
            bool: True if setup successful
        """
        try:
            # Override in subclasses to implement rule set setup
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup rule set {rule_set_name}: {e}")
            return False
    
    async def _finalize_integration(self) -> bool:
        """
        Finalize the integration process.
        
        Returns:
            bool: True if finalization successful
        """
        try:
            # Perform any final integration steps
            return True
            
        except Exception as e:
            logger.error(f"Failed to finalize integration: {e}")
            return False
    
    def _get_health_metrics(self) -> Dict[str, Any]:
        """
        Get health metrics for the bridge.
        
        Returns:
            Dict[str, Any]: Health metrics
        """
        return {
            "uptime_seconds": (datetime.now() - self.last_updated).total_seconds(),
            "error_rate": 1.0 - (self.integration_successes / max(self.integration_attempts, 1)),
            "last_error_age": (datetime.now() - self.last_updated).total_seconds() if self.last_error else None,
            "configuration完整性": bool(self.configuration),
            "component_availability": {
                "selector_engine": self.selector_engine is not None,
                "page": self.page is not None
            }
        }


class SelectorLoaderBridge(BaseIntegrationBridge):
    """
    Specialized bridge for loading YAML selectors into the selector engine.
    """
    
    def __init__(
        self,
        template_name: str,
        selector_engine: Any,
        page: Any,
        selector_configs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize selector loader bridge.
        
        Args:
            template_name: Name of the associated template
            selector_engine: Framework selector engine instance
            page: Playwright page instance
            selector_configs: Selector configurations dictionary
            **kwargs: Additional arguments
        """
        super().__init__(
            template_name=template_name,
            bridge_type=BridgeType.SELECTOR_LOADER,
            selector_engine=selector_engine,
            page=page,
            **kwargs
        )
        
        self._selector_configs = selector_configs or {}
    
    async def _get_selector_configurations(self) -> Dict[str, Any]:
        """Get selector configurations."""
        return self._selector_configs


class ExtractorBridge(BaseIntegrationBridge):
    """
    Specialized bridge for integrating with the extractor module.
    """
    
    def __init__(
        self,
        template_name: str,
        selector_engine: Any,
        page: Any,
        extraction_configs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize extractor bridge.
        
        Args:
            template_name: Name of the associated template
            selector_engine: Framework selector engine instance
            page: Playwright page instance
            extraction_configs: Extraction configurations dictionary
            **kwargs: Additional arguments
        """
        super().__init__(
            template_name=template_name,
            bridge_type=BridgeType.EXTRACTOR_BRIDGE,
            selector_engine=selector_engine,
            page=page,
            **kwargs
        )
        
        self._extraction_configs = extraction_configs or {}
    
    async def _get_extraction_rule_configurations(self) -> Dict[str, Any]:
        """Get extraction rule configurations."""
        return self._extraction_configs


class FullIntegrationBridge(BaseIntegrationBridge):
    """
    Complete integration bridge that handles all aspects of template integration.
    """
    
    def __init__(
        self,
        template_name: str,
        selector_engine: Any,
        page: Any,
        selector_configs: Optional[Dict[str, Any]] = None,
        extraction_configs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize full integration bridge.
        
        Args:
            template_name: Name of the associated template
            selector_engine: Framework selector engine instance
            page: Playwright page instance
            selector_configs: Selector configurations dictionary
            extraction_configs: Extraction configurations dictionary
            **kwargs: Additional arguments
        """
        super().__init__(
            template_name=template_name,
            bridge_type=BridgeType.FULL_INTEGRATION,
            selector_engine=selector_engine,
            page=page,
            **kwargs
        )
        
        self._selector_configs = selector_configs or {}
        self._extraction_configs = extraction_configs or {}
    
    async def _get_selector_configurations(self) -> Dict[str, Any]:
        """Get selector configurations."""
        return self._selector_configs
    
    async def _get_extraction_rule_configurations(self) -> Dict[str, Any]:
        """Get extraction rule configurations."""
        return self._extraction_configs
