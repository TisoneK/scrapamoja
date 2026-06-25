"""
Automatic selector registration via engine lifecycle hooks.

Story 7.4: Registration Automation
- Uses engine lifecycle hooks for automatic registration
- Integrates with native YAML loading from Story 7.2
- Connects with strategy format standardization from Story 7.3

AC #2: Registration happens automatically via engine hooks
AC #3: Selectors available immediately on scraper startup
"""

import asyncio
from pathlib import Path
from typing import List, Optional

from src.selectors.engine import SelectorEngine
from src.selectors.yaml_loader import get_yaml_loader, YAMLSelectorLoader
from src.selectors.unified_context import UnifiedContext
from src.observability.logger import get_logger


class RegistrationHook:
    """
    Automatic selector registration via engine lifecycle hooks.
    
    This class registers callbacks with the selector engine's lifecycle hooks
    to automatically load and register selectors when the engine initializes.
    """
    
    def __init__(self, engine: SelectorEngine, selectors_root: Optional[Path] = None, auto_load: bool = True):
        """
        Initialize the registration hook.
        
        Args:
            engine: The selector engine to register hooks with
            selectors_root: Root directory for selector YAML files (optional)
            auto_load: If True, selectors are loaded immediately on engine init
        """
        self.engine = engine
        self.logger = get_logger("selectors.registration_hook")
        self._selectors_root = selectors_root
        self._auto_load = auto_load and selectors_root is not None
        self._registered = False
        self._loading = False
        self._loaded = False
    
    def register_with_engine(self) -> None:
        """
        Register this hook with the engine's lifecycle hooks.
        
        This enables automatic selector loading when the engine initializes.
        """
        if self._registered:
            self.logger.debug("RegistrationHook already registered with engine")
            return
        
        # Register for init event - this triggers automatic loading
        self.engine.register_hook(
            SelectorEngine.HOOK_EVENT_INIT,
            self._on_engine_init
        )
        
        # Register for ready event - for any post-initialization tasks
        self.engine.register_hook(
            SelectorEngine.HOOK_EVENT_READY,
            self._on_engine_ready
        )
        
        self._registered = True
        self.logger.info("RegistrationHook registered with selector engine")
    
    async def _on_engine_init(self) -> None:
        """
        Callback for engine init event.
        
        Automatically loads and registers selectors when engine initializes.
        Only loads if auto_load is enabled and selectors_root is configured.
        """
        if self._loaded:
            self.logger.debug("Selectors already loaded, skipping")
            return
        
        if not self._auto_load:
            self.logger.debug("Auto-load disabled or no selectors_root configured")
            return
        
        if self._loading:
            return
        
        self._loading = True
        try:
            await self._auto_load_selectors()
            self._loaded = True
        finally:
            self._loading = False
    
    async def _on_engine_ready(self, selector_count: int) -> None:
        """
        Callback for engine ready event.
        
        Logs that selectors are now available.
        """
        self.logger.info(f"Selector engine ready with {selector_count} selectors registered")
    
    async def _auto_load_selectors(self) -> None:
        """
        Automatically load and register selectors using native YAML loading.
        
        This integrates with Story 7.2's YAMLSelectorLoader for native loading
        and Story 7.3's strategy format standardization.
        """
        if self._selectors_root is None:
            self.logger.debug("No selectors_root configured, skipping auto-loading")
            return
        
        try:
            self.logger.info(f"Auto-loading selectors from {self._selectors_root}")
            
            # Use native YAML loader from Story 7.2
            yaml_loader: YAMLSelectorLoader = get_yaml_loader()
            
            # Load all selectors from directory
            load_result = yaml_loader.load_selectors_from_directory(
                directory_path=str(self._selectors_root),
                recursive=True
            )
            
            if not load_result.success:
                self.logger.warning(f"Selector loading had issues: {load_result.errors}")
            
            # Get cached selectors and register them
            cache_stats = yaml_loader.get_cache_stats()
            cached_files = cache_stats.get('cached_files', [])
            
            registered_count = 0
            for file_path in cached_files:
                cached_selector = yaml_loader.get_cached_selector(file_path)
                if cached_selector:
                    # Convert to SemanticSelector (Story 7.3 compatibility)
                    semantic_selector = self._convert_yaml_to_semantic(cached_selector)
                    if semantic_selector:
                        # Register with engine - use single argument version
                        success = await self.engine.register_selector(
                            semantic_selector
                        )
                        if success:
                            registered_count += 1
            
            # Notify engine that loading is complete
            await self.engine.notify_selectors_loaded(registered_count)
            
            self.logger.info(
                f"Auto-registration complete: {registered_count} selectors registered "
                f"in {load_result.loading_time_ms:.2f}ms"
            )
            
        except Exception as e:
            self.logger.error(f"Auto-loading selectors failed: {e}")
    
    def _convert_yaml_to_semantic(self, yaml_selector) -> Optional[object]:
        """
        Convert a YAMLSelector to SemanticSelector for engine registration.
        
        This provides compatibility with Story 7.3's strategy format standardization.
        
        Args:
            yaml_selector: YAMLSelector from the engine's loader
            
        Returns:
            SemanticSelector compatible with the selector engine registry
        """
        try:
            from src.models.selector_models import (
                SemanticSelector,
                StrategyPattern,
                StrategyType,
            )
            
            # Convert YAMLSelector strategies to SemanticSelector strategies
            strategies = []
            for i, strategy in enumerate(yaml_selector.strategies or []):
                # Handle both dict and SelectorStrategy objects
                strategy_id = None
                if hasattr(strategy, 'id'):
                    strategy_id = strategy.id
                elif isinstance(strategy, dict):
                    strategy_id = strategy.get('id')
                
                strategy_pattern = StrategyPattern(
                    id=strategy_id or f"{yaml_selector.id}_strategy_{i}",
                    type=StrategyType(
                        strategy.type.value if hasattr(strategy.type, "value") else "css"
                    ),
                    priority=i + 1,
                    config={
                        "selector": strategy.config.get("selector") if hasattr(strategy, 'config') and strategy.config else None,
                        "weight": strategy.config.get("weight", 1.0) if hasattr(strategy, 'config') and strategy.config else 1.0,
                    },
                )
                strategies.append(strategy_pattern)
            
            # Create SemanticSelector from YAMLSelector
            semantic_selector = SemanticSelector(
                name=yaml_selector.id,
                description=yaml_selector.description or "",
                context=yaml_selector.name,
                strategies=strategies,
                validation_rules=yaml_selector.validation_rules or [],
                confidence_threshold=(
                    yaml_selector.metadata.get("confidence_threshold", 0.8)
                    if yaml_selector.metadata
                    else 0.8
                ),
                metadata={
                    "file_path": yaml_selector.file_path,
                    "original_yaml_id": yaml_selector.id,
                    **(yaml_selector.metadata or {}),
                },
            )
            
            return semantic_selector
            
        except Exception as e:
            self.logger.error(f"Failed to convert YAMLSelector to SemanticSelector: {e}")
            return None


def create_registration_hook(
    engine: SelectorEngine,
    selectors_root: Optional[Path] = None,
) -> RegistrationHook:
    """
    Create and register a RegistrationHook with the engine.
    
    This is the main entry point for automatic selector registration.
    
    Args:
        engine: The selector engine to register with
        selectors_root: Root directory for selector YAML files
        
    Returns:
        Configured RegistrationHook instance
    """
    hook = RegistrationHook(engine, selectors_root)
    hook.register_with_engine()
    return hook


async def auto_register_from_directory(
    engine: SelectorEngine,
    selectors_root: Path,
) -> int:
    """
    Utility function to manually trigger auto-registration from a directory.
    
    This can be used when you need to trigger registration manually rather than
    waiting for engine initialization.
    
    Args:
        engine: The selector engine to register with
        selectors_root: Root directory for selector YAML files
        
    Returns:
        Number of selectors registered
    """
    hook = RegistrationHook(engine, selectors_root)
    await hook._auto_load_selectors()
    
    # Get count from engine
    return len(engine.list_selectors())


# Export for hooks module
__all__ = [
    "RegistrationHook",
    "create_registration_hook",
    "auto_register_from_directory",
]
