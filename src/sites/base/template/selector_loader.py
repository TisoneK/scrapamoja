"""
Selector loader base classes for the Site Template Integration Framework.

This module provides concrete implementations for loading YAML selectors into the existing
selector engine, enabling template-based selector management.
"""

import asyncio
import logging
import yaml
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from .interfaces import ISelectorLoader


logger = logging.getLogger(__name__)


class SelectorType(Enum):
    """Types of selectors."""
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"
    HYBRID = "hybrid"


class SelectorLoadStatus(Enum):
    """Selector loading status."""
    PENDING = "pending"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    VALIDATED = "validated"


class BaseSelectorLoader(ISelectorLoader):
    """
    Base implementation of ISelectorLoader that provides common functionality
    for loading YAML selectors into the existing selector engine.
    """
    
    def __init__(
        self,
        template_name: str,
        selector_engine: Any,
        selectors_directory: Optional[Union[str, Path]] = None,
        configuration: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the base selector loader.
        
        Args:
            template_name: Name of the associated template
            selector_engine: Framework selector engine instance
            selectors_directory: Directory containing YAML selector files
            configuration: Loader configuration
        """
        self.template_name = template_name
        self.selector_engine = selector_engine
        self.selectors_directory = Path(selectors_directory) if selectors_directory else None
        self.configuration = configuration or {}
        
        # Loading state
        self.loaded_selectors: List[str] = []
        self.selector_status: Dict[str, SelectorLoadStatus] = {}
        self.load_timestamps: Dict[str, datetime] = {}
        
        # Validation cache
        self.validation_cache: Dict[str, bool] = {}
        self.validation_errors: Dict[str, List[str]] = {}
        
        # Performance metrics
        self.load_times: Dict[str, float] = {}
        self.total_load_time = 0.0
        
        logger.info(f"BaseSelectorLoader initialized for {template_name}")
    
    async def load_site_selectors(self, site_name: str) -> bool:
        """
        Load selectors for a specific site.
        
        Args:
            site_name: Name of the site to load selectors for
            
        Returns:
            bool: True if selectors loaded successfully
        """
        try:
            logger.info(f"Loading selectors for site: {site_name}")
            
            # Validate selectors directory exists
            if not self.selectors_directory or not self.selectors_directory.exists():
                logger.warning(f"Selectors directory not found: {self.selectors_directory}")
                return False
            
            # Get all YAML selector files
            yaml_files = list(self.selectors_directory.glob("*.yaml")) + list(self.selectors_directory.glob("*.yml"))
            
            if not yaml_files:
                logger.warning(f"No YAML selector files found in {self.selectors_directory}")
                return True  # Not an error, just no selectors to load
            
            # Load each selector file
            success_count = 0
            total_files = len(yaml_files)
            
            for yaml_file in yaml_files:
                selector_name = yaml_file.stem
                self.selector_status[selector_name] = SelectorLoadStatus.LOADING
                
                try:
                    if await self._load_selector_from_file(yaml_file):
                        success_count += 1
                        self.selector_status[selector_name] = SelectorLoadStatus.LOADED
                        logger.debug(f"Successfully loaded selector: {selector_name}")
                    else:
                        self.selector_status[selector_name] = SelectorLoadStatus.FAILED
                        logger.warning(f"Failed to load selector: {selector_name}")
                        
                except Exception as e:
                    self.selector_status[selector_name] = SelectorLoadStatus.FAILED
                    logger.error(f"Error loading selector {selector_name}: {e}")
            
            logger.info(f"Loaded {success_count}/{total_files} selectors for site {site_name}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to load site selectors for {site_name}: {e}")
            return False
    
    async def register_selector(self, selector_name: str, selector_config: Dict[str, Any]) -> bool:
        """
        Register a single selector with selector engine.
        
        Args:
            selector_name: Name of the selector
            selector_config: Selector configuration dictionary
            
        Returns:
            bool: True if registration successful
        """
        # Generate correlation ID for this registration attempt
        correlation_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting registration for selector {selector_name}", 
                       extra={"correlation_id": correlation_id, "selector_name": selector_name})
            
            # Validate selector configuration
            if not selector_config:
                logger.error(f"Empty selector configuration for {selector_name}", 
                           extra={"correlation_id": correlation_id, "selector_name": selector_name})
                return False
            
            # Check if selector engine supports registration
            if not hasattr(self.selector_engine, 'register_selector'):
                logger.error(f"Selector engine does not support registration", 
                           extra={"correlation_id": correlation_id, "selector_name": selector_name})
                return False
            
            # Create SemanticSelector object from configuration
            from src.models.selector_models import SemanticSelector
            
            strategies = selector_config.get('strategies', [])
            if not strategies:
                logger.error(f"No strategies found in selector configuration for {selector_name}", 
                           extra={"correlation_id": correlation_id, "selector_name": selector_name})
                return False
            
            # Validate individual strategies before creating selector
            logger.info(f"Processing {len(strategies)} strategies for selector {selector_name}", 
                       extra={"correlation_id": correlation_id, "selector_name": selector_name, "strategy_count": len(strategies)})
            
            # Convert weight to priority for SemanticSelector compatibility
            processed_strategies = []
            for i, strategy in enumerate(strategies):
                try:
                    strategy_type = strategy.get('type')
                    if not strategy_type:
                        logger.warning(f"Strategy {i} missing type for selector {selector_name}", 
                                     extra={"correlation_id": correlation_id, "selector_name": selector_name, "strategy_index": i})
                        continue
                    
                    # Validate strategy type is supported
                    from src.selectors.models import StrategyType
                    try:
                        StrategyType(strategy_type)
                        logger.debug(f"Strategy {i} type '{strategy_type}' validated for selector {selector_name}", 
                                   extra={"correlation_id": correlation_id, "selector_name": selector_name, "strategy_index": i, "strategy_type": strategy_type})
                    except ValueError as ve:
                        logger.error(f"Unknown strategy type '{strategy_type}' in strategy {i} for selector {selector_name}: {ve}", 
                                       extra={"correlation_id": correlation_id, "selector_name": selector_name, "strategy_index": i, "strategy_type": strategy_type})
                        return False
                        
                except Exception as e:
                    logger.error(f"Error validating strategy {i} for selector {selector_name}: {e}", 
                               extra={"correlation_id": correlation_id, "selector_name": selector_name, "strategy_index": i})
                    continue
                
                # Convert weight to priority for SemanticSelector compatibility
                weight = strategy.get('weight', 1.0)
                priority = i + 1  # Use order as priority (lower = higher priority)
                
                processed_strategy = {
                    'type': strategy_type,
                    'selector': strategy.get('selector'),
                    'priority': priority,
                    'weight': weight,
                    'config': {k: v for k, v in strategy.items() if k != 'type' and k != 'selector' and k != 'weight'}
                }
                processed_strategies.append(processed_strategy)
            
            selector = SemanticSelector(
                name=selector_name,
                strategies=processed_strategies,
                confidence_threshold=selector_config.get('confidence_threshold', 0.7),
                validation_rules=selector_config.get('validation_rules', [])
            )
            
            logger.info(f"Created SemanticSelector for {selector_name} with {len(strategies)} strategies", 
                       extra={"correlation_id": correlation_id, "selector_name": selector_name, "strategy_count": len(strategies)})
            
            # Register with selector engine
            try:
                self.selector_engine.register_selector(selector_name, selector)
                logger.info(f"Successfully registered selector {selector_name} with engine", 
                           extra={"correlation_id": correlation_id, "selector_name": selector_name})
            except Exception as reg_error:
                logger.error(f"Failed to register selector {selector_name} with engine: {reg_error}", 
                           extra={"correlation_id": correlation_id, "selector_name": selector_name})
                self.selector_status[selector_name] = SelectorLoadStatus.FAILED
                return False
            
            # Update tracking
            self.loaded_selectors.append(selector_name)
            self.load_timestamps[selector_name] = datetime.now()
            self.selector_status[selector_name] = SelectorLoadStatus.LOADED
            
            # Record performance metrics
            load_time = (datetime.now() - start_time).total_seconds()
            self.load_times[selector_name] = load_time
            self.total_load_time += load_time
            
            logger.info(f"Successfully registered selector: {selector_name} (took {load_time:.3f}s)", 
                       extra={"correlation_id": correlation_id, "selector_name": selector_name, "load_time": load_time})
            return True
            
        except Exception as e:
            logger.error(f"Failed to register selector {selector_name}: {e}", 
                       extra={"correlation_id": correlation_id, "selector_name": selector_name})
            self.selector_status[selector_name] = SelectorLoadStatus.FAILED
            return False
    
    def get_loaded_selectors(self) -> List[str]:
        """
        Get list of loaded selector names.
        
        Returns:
            List[str]: List of selector names
        """
        return self.loaded_selectors.copy()
    
    def get_registry_state(self) -> Dict[str, Any]:
        """
        Get current registry state for debugging.
        
        Returns:
            Dict with registry information
        """
        if hasattr(self.selector_engine, 'list_selectors'):
            registered_selectors = self.selector_engine.list_selectors()
            return {
                'loaded_count': len(self.loaded_selectors),
                'registered_count': len(registered_selectors),
                'loaded_selectors': self.loaded_selectors,
                'registered_selectors': registered_selectors,
                'missing_selectors': [s for s in self.loaded_selectors if s not in registered_selectors]
            }
        return {'error': 'Registry does not support listing selectors'}
    
    async def validate_selector_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate selector configuration.
        
        Args:
            config: Selector configuration to validate
            
        Returns:
            bool: True if configuration is valid
        """
        try:
            # Create cache key for validation
            config_str = str(sorted(config.items()))
            
            # Check validation cache
            if config_str in self.validation_cache:
                return self.validation_cache[config_str]
            
            errors = []
            
            # Validate required fields
            required_fields = ['strategies']
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required field: {field}")
            
            # Validate strategies
            strategies = config.get('strategies', [])
            if not strategies:
                errors.append("At least one strategy must be specified")
            else:
                for i, strategy in enumerate(strategies):
                    if not isinstance(strategy, dict):
                        errors.append(f"Strategy {i} must be a dictionary")
                        continue
                    
                    if 'type' not in strategy:
                        errors.append(f"Strategy {i} missing required 'type' field")
                    
                    if 'weight' in strategy:
                        weight = strategy['weight']
                        if not isinstance(weight, (int, float)) or not 0 <= weight <= 1:
                            errors.append(f"Strategy {i} weight must be between 0 and 1")
            
            # Validate confidence threshold
            if 'confidence_threshold' in config:
                threshold = config['confidence_threshold']
                if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
                    errors.append("confidence_threshold must be between 0 and 1")
            
            # Validate selector type if specified
            if 'selector_type' in config:
                selector_type = config['selector_type']
                try:
                    SelectorType(selector_type)
                except ValueError:
                    errors.append(f"Invalid selector_type: {selector_type}")
            
            # Cache validation result
            is_valid = len(errors) == 0
            self.validation_cache[config_str] = is_valid
            
            if not is_valid:
                self.validation_errors[config_str] = errors
                logger.warning(f"Selector validation failed: {errors}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating selector configuration: {e}")
            return False
    
    async def _load_selector_from_file(self, yaml_file: Path) -> bool:
        """
        Load selector from YAML file.
        
        Args:
            yaml_file: Path to YAML file
            
        Returns:
            bool: True if loading successful
        """
        try:
            start_time = datetime.now()
            
            # Read YAML file
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                logger.error(f"Empty YAML file: {yaml_file}")
                return False
            
            # Extract selector name
            selector_name = config.get('name', yaml_file.stem)
            
            # Use full qualified name for registration to match scraper expectations
            full_selector_name = f"extraction.match_list.basketball.{yaml_file.stem}"
            
            # Register selector
            success = await self.register_selector(full_selector_name, config)
            
            # Record performance metrics
            load_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Loaded selector from {yaml_file.name} in {load_time:.3f}s")
            
            return success
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {yaml_file}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading selector from {yaml_file}: {e}")
            return False
    
    def get_selector_status(self, selector_name: str) -> Optional[SelectorLoadStatus]:
        """
        Get the loading status of a specific selector.
        
        Args:
            selector_name: Name of the selector
            
        Returns:
            Optional[SelectorLoadStatus]: Loading status
        """
        return self.selector_status.get(selector_name)
    
    def get_load_metrics(self) -> Dict[str, Any]:
        """
        Get loading performance metrics.
        
        Returns:
            Dict[str, Any]: Performance metrics
        """
        return {
            "total_selectors_loaded": len(self.loaded_selectors),
            "total_load_time": self.total_load_time,
            "average_load_time": self.total_load_time / max(len(self.loaded_selectors), 1),
            "load_times_by_selector": self.load_times.copy(),
            "selector_status_counts": self._get_status_counts()
        }
    
    def _get_status_counts(self) -> Dict[str, int]:
        """Get counts of selectors by status."""
        counts = {}
        for status in SelectorLoadStatus:
            counts[status.value] = sum(1 for s in self.selector_status.values() if s == status)
        return counts


class FileSystemSelectorLoader(BaseSelectorLoader):
    """
    Selector loader that loads from filesystem YAML files.
    """
    
    def __init__(
        self,
        template_name: str,
        selector_engine: Any,
        selectors_directory: Union[str, Path],
        **kwargs
    ):
        """
        Initialize filesystem selector loader.
        
        Args:
            template_name: Name of the associated template
            selector_engine: Framework selector engine instance
            selectors_directory: Directory containing YAML selector files
            **kwargs: Additional arguments
        """
        super().__init__(
            template_name=template_name,
            selector_engine=selector_engine,
            selectors_directory=selectors_directory,
            **kwargs
        )
    
    async def reload_selectors(self) -> bool:
        """
        Reload all selectors from filesystem.
        
        Returns:
            bool: True if reload successful
        """
        try:
            logger.info(f"Reloading selectors for {self.template_name}")
            
            # Clear current state
            self.loaded_selectors.clear()
            self.selector_status.clear()
            self.load_timestamps.clear()
            
            # Reload from site name (template name)
            return await self.load_site_selectors(self.template_name)
            
        except Exception as e:
            logger.error(f"Failed to reload selectors: {e}")
            return False


class ConfigurableSelectorLoader(BaseSelectorLoader):
    """
    Selector loader that loads from configuration dictionary.
    """
    
    def __init__(
        self,
        template_name: str,
        selector_engine: Any,
        selector_configs: Dict[str, Any],
        **kwargs
    ):
        """
        Initialize configurable selector loader.
        
        Args:
            template_name: Name of the associated template
            selector_engine: Framework selector engine instance
            selector_configs: Dictionary of selector configurations
            **kwargs: Additional arguments
        """
        super().__init__(
            template_name=template_name,
            selector_engine=selector_engine,
            **kwargs
        )
        
        self._selector_configs = selector_configs
    
    async def load_site_selectors(self, site_name: str) -> bool:
        """
        Load selectors from configuration dictionary.
        
        Args:
            site_name: Name of the site to load selectors for
            
        Returns:
            bool: True if selectors loaded successfully
        """
        try:
            logger.info(f"Loading selectors from configuration for site: {site_name}")
            
            if not self._selector_configs:
                logger.warning("No selector configurations provided")
                return True
            
            success_count = 0
            total_selectors = len(self._selector_configs)
            
            for selector_name, config in self._selector_configs.items():
                self.selector_status[selector_name] = SelectorLoadStatus.LOADING
                
                try:
                    if await self.register_selector(selector_name, config):
                        success_count += 1
                        self.selector_status[selector_name] = SelectorLoadStatus.LOADED
                    else:
                        self.selector_status[selector_name] = SelectorLoadStatus.FAILED
                        
                except Exception as e:
                    self.selector_status[selector_name] = SelectorLoadStatus.FAILED
                    logger.error(f"Error loading selector {selector_name}: {e}")
            
            logger.info(f"Loaded {success_count}/{total_selectors} selectors from configuration")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to load selectors from configuration: {e}")
            return False
