"""
Context-based selector loading logic for hierarchical selector management.

This module provides intelligent selector loading based on navigation context,
DOM state, and caching strategies.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
import yaml
import json

from .context_manager import (
    SelectorContext, 
    SelectorContextManager, 
    DOMState,
    get_context_manager
)
from .context_detectors import (
    ContextDetectionEngine,
    ContextDetectionResult,
    get_context_detection_engine
)
from ..models.selector_models import SemanticSelector, SelectorResult


logger = logging.getLogger(__name__)


@dataclass
class SelectorLoadRequest:
    """Request for loading selectors."""
    context: SelectorContext
    force_reload: bool = False
    include_inactive: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SelectorLoadResult:
    """Result of selector loading operation."""
    selectors: List[SemanticSelector]
    load_time_ms: float
    cache_hit: bool
    context_path: str
    selector_count: int
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextBasedSelectorLoader:
    """
    Loads selectors based on context with intelligent caching and fallback strategies.
    """
    
    def __init__(self, selectors_root: Path):
        """
        Initialize context-based selector loader.
        
        Args:
            selectors_root: Root directory of hierarchical selectors
        """
        self.selectors_root = Path(selectors_root)
        
        # Get managers
        self.context_manager = get_context_manager(selectors_root)
        self.detection_engine = get_context_detection_engine()
        
        # Loading cache
        self.load_cache: Dict[str, SelectorLoadResult] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Performance tracking
        self.load_history: List[SelectorLoadResult] = []
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0
        }
        
        # Configuration
        self.cache_ttl_seconds = 300  # 5 minutes
        self.max_cache_size = 100
        self.enable_fallback_loading = True
        self.max_concurrent_loads = 5
        
        # Fallback selectors (for when context-specific loading fails)
        self.fallback_selectors: Dict[str, List[SemanticSelector]] = {}
        
        logger.info(f"ContextBasedSelectorLoader initialized for {selectors_root}")
    
    async def load_selectors(
        self,
        context: Optional[SelectorContext] = None,
        url: Optional[str] = None,
        html_content: Optional[str] = None,
        page_title: Optional[str] = None,
        force_reload: bool = False,
        include_inactive: bool = False
    ) -> SelectorLoadResult:
        """
        Load selectors for the given context.
        
        Args:
            context: Specific context (auto-detected if None)
            url: Current page URL (for auto-detection)
            html_content: HTML content (for auto-detection)
            page_title: Page title (for auto-detection)
            force_reload: Force reload from disk
            include_inactive: Include inactive selectors in results
            
        Returns:
            SelectorLoadResult: Loading result with selectors and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            # Auto-detect context if not provided
            if context is None:
                context = await self._auto_detect_context(url, html_content, page_title)
                if not context:
                    return SelectorLoadResult(
                        selectors=[],
                        load_time_ms=0,
                        cache_hit=False,
                        context_path="unknown",
                        selector_count=0,
                        errors=["Failed to detect context"],
                        metadata={"auto_detection": True}
                    )
            
            context_path = context.get_context_path()
            
            # Check cache first
            if not force_reload:
                cached_result = self._get_from_cache(context_path, context)
                if cached_result:
                    self.cache_stats["hits"] += 1
                    load_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    logger.debug(f"Cache hit for context: {context_path}")
                    return SelectorLoadResult(
                        selectors=cached_result.selectors,
                        load_time_ms=load_time,
                        cache_hit=True,
                        context_path=context_path,
                        selector_count=len(cached_result.selectors),
                        metadata={"cache_hit": True, "auto_detected": context is None}
                    )
            
            self.cache_stats["misses"] += 1
            
            # Load selectors from disk
            selectors = await self._load_selectors_from_disk(context, include_inactive)
            
            # Apply context-specific filtering and processing
            processed_selectors = await self._process_selectors_for_context(
                selectors, context, html_content
            )
            
            # Cache the result
            load_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            result = SelectorLoadResult(
                selectors=processed_selectors,
                load_time_ms=load_time,
                cache_hit=False,
                context_path=context_path,
                selector_count=len(processed_selectors),
                metadata={"auto_detected": context is None}
            )
            
            self._cache_result(context_path, context, result)
            self.load_history.append(result)
            
            # Limit history size
            if len(self.load_history) > 1000:
                self.load_history = self.load_history[-1000:]
            
            logger.info(
                f"Loaded {len(processed_selectors)} selectors for context: {context_path} "
                f"in {load_time:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            load_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            error_msg = f"Failed to load selectors: {str(e)}"
            logger.error(error_msg)
            
            # Try fallback loading if enabled
            if self.enable_fallback_loading:
                fallback_selectors = await self._load_fallback_selectors(context)
                if fallback_selectors:
                    return SelectorLoadResult(
                        selectors=fallback_selectors,
                        load_time_ms=load_time,
                        cache_hit=False,
                        context_path=context.get_context_path() if context else "unknown",
                        selector_count=len(fallback_selectors),
                        errors=[error_msg],
                        metadata={"fallback_used": True, "auto_detected": context is None}
                    )
            
            return SelectorLoadResult(
                selectors=[],
                load_time_ms=load_time,
                cache_hit=False,
                context_path=context.get_context_path() if context else "unknown",
                selector_count=0,
                errors=[error_msg],
                metadata={"auto_detected": context is None}
            )
    
    async def _auto_detect_context(
        self,
        url: Optional[str],
        html_content: Optional[str],
        page_title: Optional[str]
    ) -> Optional[SelectorContext]:
        """
        Auto-detect context from available information.
        
        Args:
            url: Page URL
            html_content: HTML content
            page_title: Page title
            
        Returns:
            Optional[SelectorContext]: Detected context
        """
        try:
            detection_result = await self.detection_engine.detect_context(
                url, html_content, page_title
            )
            
            if detection_result.primary_context:
                # Create context from detection result
                context = SelectorContext(
                    primary_context=detection_result.primary_context,
                    secondary_context=detection_result.secondary_context,
                    tertiary_context=detection_result.tertiary_context,
                    is_active=True,
                    metadata={
                        "auto_detected": True,
                        "confidence": detection_result.confidence,
                        "evidence": detection_result.evidence
                    }
                )
                
                # Set as current context in manager
                await self.context_manager.set_context(
                    primary_context=context.primary_context,
                    secondary_context=context.secondary_context,
                    tertiary_context=context.tertiary_context
                )
                
                logger.info(
                    f"Auto-detected context: {context.get_context_path()} "
                    f"(confidence: {detection_result.confidence:.2f})"
                )
                
                return context
            
            return None
            
        except Exception as e:
            logger.error(f"Context auto-detection failed: {e}")
            return None
    
    async def _load_selectors_from_disk(
        self,
        context: SelectorContext,
        include_inactive: bool = False
    ) -> List[SemanticSelector]:
        """
        Load selectors from disk for the given context.
        
        Args:
            context: Context to load selectors for
            include_inactive: Whether to include inactive selectors
            
        Returns:
            List[SemanticSelector]: Loaded selectors
        """
        selectors = []
        
        try:
            # Get the directory for this context
            context_dir = self.selectors_root / context.primary_context
            if context.secondary_context:
                context_dir = context_dir / context.secondary_context
            if context.tertiary_context:
                context_dir = context_dir / context.tertiary_context
            
            if not context_dir.exists():
                logger.warning(f"Context directory does not exist: {context_dir}")
                return []
            
            # Load all YAML files in the context directory
            yaml_files = list(context_dir.glob("*.yaml")) + list(context_dir.glob("*.yml"))
            
            # Load files concurrently with semaphore
            semaphore = asyncio.Semaphore(self.max_concurrent_loads)
            
            async def load_single_file(file_path: Path) -> Optional[SemanticSelector]:
                async with semaphore:
                    return await self._load_selector_file(file_path, context)
            
            tasks = [load_single_file(file_path) for file_path in yaml_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error loading selector file: {result}")
                elif result:
                    if include_inactive or result.strategies:  # Only include if has strategies
                        selectors.append(result)
            
            logger.debug(f"Loaded {len(selectors)} selectors from {len(yaml_files)} files")
            
        except Exception as e:
            logger.error(f"Failed to load selectors from disk: {e}")
        
        return selectors
    
    async def _load_selector_file(
        self,
        file_path: Path,
        context: SelectorContext
    ) -> Optional[SemanticSelector]:
        """
        Load a single selector file.
        
        Args:
            file_path: Path to selector file
            context: Context for the selector
            
        Returns:
            Optional[SemanticSelector]: Loaded selector
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            # Create SemanticSelector from YAML data
            selector = SemanticSelector(
                name=data.get('name', file_path.stem),
                description=data.get('description', ''),
                context=context.get_context_path(),
                strategies=data.get('strategies', []),
                validation_rules=data.get('validation_rules', []),
                confidence_threshold=data.get('confidence_threshold', 0.8),
                metadata={
                    'file_path': str(file_path),
                    'context': context.get_context_path(),
                    'dom_state': context.dom_state.value if context.dom_state else None,
                    'loaded_at': datetime.utcnow().isoformat(),
                    **data.get('metadata', {})
                }
            )
            
            return selector
            
        except Exception as e:
            logger.error(f"Error loading selector file {file_path}: {e}")
            return None
    
    async def _process_selectors_for_context(
        self,
        selectors: List[SemanticSelector],
        context: SelectorContext,
        html_content: Optional[str] = None
    ) -> List[SemanticSelector]:
        """
        Process selectors based on context and DOM state.
        
        Args:
            selectors: Raw loaded selectors
            context: Current context
            html_content: HTML content for DOM analysis
            
        Returns:
            List[SemanticSelector]: Processed selectors
        """
        processed_selectors = []
        
        for selector in selectors:
            try:
                # Filter by DOM state if specified
                if context.dom_state and self._should_filter_by_dom_state(selector, context.dom_state):
                    if not self._is_selector_valid_for_dom_state(selector, context.dom_state, html_content):
                        continue
                
                # Apply context-specific modifications
                modified_selector = await self._apply_context_modifications(selector, context)
                
                if modified_selector:
                    processed_selectors.append(modified_selector)
                    
            except Exception as e:
                logger.error(f"Error processing selector {selector.name}: {e}")
        
        return processed_selectors
    
    def _should_filter_by_dom_state(self, selector: SemanticSelector, dom_state: DOMState) -> bool:
        """Check if selector should be filtered by DOM state."""
        # Check if selector has DOM state restrictions
        valid_states = selector.metadata.get('valid_dom_states')
        if valid_states:
            return dom_state.value not in valid_states
        
        # Check if selector has DOM state preferences
        preferred_states = selector.metadata.get('preferred_dom_states')
        if preferred_states:
            return dom_state.value not in preferred_states
        
        return False
    
    def _is_selector_valid_for_dom_state(
        self,
        selector: SemanticSelector,
        dom_state: DOMState,
        html_content: Optional[str] = None
    ) -> bool:
        """
        Check if selector is valid for the given DOM state.
        
        Args:
            selector: Selector to check
            dom_state: Current DOM state
            html_content: HTML content for validation
            
        Returns:
            bool: True if selector is valid for this DOM state
        """
        # If no HTML content, assume valid
        if not html_content:
            return True
        
        content_lower = html_content.lower()
        
        # Check for DOM state indicators in selector metadata
        state_indicators = selector.metadata.get('dom_state_indicators', {})
        
        if dom_state.value in state_indicators:
            required_indicators = state_indicators[dom_state.value]
            for indicator in required_indicators:
                if indicator.lower() not in content_lower:
                    return False
        
        return True
    
    async def _apply_context_modifications(
        self,
        selector: SemanticSelector,
        context: SelectorContext
    ) -> Optional[SemanticSelector]:
        """
        Apply context-specific modifications to a selector.
        
        Args:
            selector: Original selector
            context: Current context
            
        Returns:
            Optional[SemanticSelector]: Modified selector
        """
        try:
            # Create a copy to modify
            modified_selector = SemanticSelector(
                name=selector.name,
                description=selector.description,
                context=context.get_context_path(),
                strategies=selector.strategies.copy(),
                validation_rules=selector.validation_rules.copy(),
                confidence_threshold=selector.confidence_threshold,
                metadata=selector.metadata.copy()
            )
            
            # Apply context-specific modifications
            modifications = selector.metadata.get('context_modifications', {})
            
            # Primary context modifications
            if context.primary_context in modifications:
                primary_mods = modifications[context.primary_context]
                modified_selector = self._apply_selector_modifications(
                    modified_selector, primary_mods
                )
            
            # Secondary context modifications
            if (context.secondary_context and 
                context.secondary_context in modifications):
                secondary_mods = modifications[context.secondary_context]
                modified_selector = self._apply_selector_modifications(
                    modified_selector, secondary_mods
                )
            
            # Tertiary context modifications
            if (context.tertiary_context and 
                context.tertiary_context in modifications):
                tertiary_mods = modifications[context.tertiary_context]
                modified_selector = self._apply_selector_modifications(
                    modified_selector, tertiary_mods
                )
            
            return modified_selector
            
        except Exception as e:
            logger.error(f"Error applying context modifications to {selector.name}: {e}")
            return selector  # Return original if modification fails
    
    def _apply_selector_modifications(
        self,
        selector: SemanticSelector,
        modifications: Dict[str, Any]
    ) -> SemanticSelector:
        """
        Apply specific modifications to a selector.
        
        Args:
            selector: Selector to modify
            modifications: Modifications to apply
            
        Returns:
            SemanticSelector: Modified selector
        """
        # Apply confidence threshold modification
        if 'confidence_threshold' in modifications:
            selector.confidence_threshold = modifications['confidence_threshold']
        
        # Apply strategy modifications
        if 'strategies' in modifications:
            strategy_mods = modifications['strategies']
            
            # Add new strategies
            if 'add' in strategy_mods:
                selector.strategies.extend(strategy_mods['add'])
            
            # Remove strategies
            if 'remove' in strategy_mods:
                selector.strategies = [
                    s for s in selector.strategies 
                    if s.get('id') not in strategy_mods['remove']
                ]
            
            # Modify existing strategies
            if 'modify' in strategy_mods:
                for strategy_id, mod_data in strategy_mods['modify'].items():
                    for strategy in selector.strategies:
                        if strategy.get('id') == strategy_id:
                            strategy.update(mod_data)
        
        # Apply metadata modifications
        if 'metadata' in modifications:
            selector.metadata.update(modifications['metadata'])
        
        return selector
    
    async def _load_fallback_selectors(
        self,
        context: SelectorContext
    ) -> List[SemanticSelector]:
        """
        Load fallback selectors when context-specific loading fails.
        
        Args:
            context: Context that failed to load
            
        Returns:
            List[SemanticSelector]: Fallback selectors
        """
        fallback_key = context.primary_context
        
        # Load fallback selectors if not cached
        if fallback_key not in self.fallback_selectors:
            try:
                fallback_dir = self.selectors_root / context.primary_context
                
                if not fallback_dir.exists():
                    return []
                
                # Load generic selectors from primary context directory
                fallback_selectors = []
                yaml_files = list(fallback_dir.glob("*.yaml")) + list(fallback_dir.glob("*.yml"))
                
                for file_path in yaml_files:
                    selector = await self._load_selector_file(file_path, context)
                    if selector:
                        fallback_selectors.append(selector)
                
                self.fallback_selectors[fallback_key] = fallback_selectors
                
            except Exception as e:
                logger.error(f"Failed to load fallback selectors: {e}")
                return []
        
        return self.fallback_selectors.get(fallback_key, [])
    
    def _get_from_cache(
        self,
        context_path: str,
        context: SelectorContext
    ) -> Optional[SelectorLoadResult]:
        """
        Get result from cache if valid.
        
        Args:
            context_path: Context path
            context: Current context
            
        Returns:
            Optional[SelectorLoadResult]: Cached result
        """
        cache_key = f"{context_path}_{context.dom_state or 'unknown'}"
        
        if cache_key not in self.load_cache:
            return None
        
        # Check if cache is still valid
        if cache_key not in self.cache_timestamps:
            return None
        
        age = datetime.utcnow() - self.cache_timestamps[cache_key]
        if age.total_seconds() > self.cache_ttl_seconds:
            # Cache expired
            del self.load_cache[cache_key]
            del self.cache_timestamps[cache_key]
            self.cache_stats["invalidations"] += 1
            return None
        
        return self.load_cache[cache_key]
    
    def _cache_result(
        self,
        context_path: str,
        context: SelectorContext,
        result: SelectorLoadResult
    ) -> None:
        """
        Cache a loading result.
        
        Args:
            context_path: Context path
            context: Current context
            result: Result to cache
        """
        cache_key = f"{context_path}_{context.dom_state or 'unknown'}"
        
        self.load_cache[cache_key] = result
        self.cache_timestamps[cache_key] = datetime.utcnow()
        
        # Limit cache size
        if len(self.load_cache) > self.max_cache_size:
            # Remove oldest entries
            oldest_keys = sorted(
                self.cache_timestamps.keys(),
                key=lambda k: self.cache_timestamps[k]
            )[:10]  # Remove 10 oldest
            
            for key in oldest_keys:
                del self.load_cache[key]
                del self.cache_timestamps[key]
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / max(total_requests, 1)
        
        return {
            "cache_size": len(self.load_cache),
            "max_cache_size": self.max_cache_size,
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "invalidations": self.cache_stats["invalidations"],
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }
    
    def get_loading_statistics(self) -> Dict[str, Any]:
        """
        Get loading performance statistics.
        
        Returns:
            Dict[str, Any]: Loading statistics
        """
        if not self.load_history:
            return {
                "total_loads": 0,
                "average_load_time_ms": 0,
                "cache_hit_rate": 0,
                "error_rate": 0
            }
        
        total_loads = len(self.load_history)
        cache_hits = sum(1 for result in self.load_history if result.cache_hit)
        total_load_time = sum(result.load_time_ms for result in self.load_history)
        total_errors = sum(len(result.errors) for result in self.load_history)
        total_selectors = sum(result.selector_count for result in self.load_history)
        
        return {
            "total_loads": total_loads,
            "average_load_time_ms": total_load_time / total_loads,
            "cache_hit_rate": cache_hits / total_loads,
            "error_rate": total_errors / total_loads,
            "average_selectors_per_load": total_selectors / total_loads,
            "recent_loads": [
                {
                    "context": result.context_path,
                    "selector_count": result.selector_count,
                    "load_time_ms": result.load_time_ms,
                    "cache_hit": result.cache_hit,
                    "timestamp": result.metadata.get("timestamp")
                }
                for result in self.load_history[-10:]  # Last 10 loads
            ]
        }
    
    def clear_cache(self, context_path: Optional[str] = None) -> None:
        """
        Clear the loading cache.
        
        Args:
            context_path: Specific context path to clear (clears all if None)
        """
        if context_path:
            # Clear specific context
            keys_to_remove = [
                key for key in self.load_cache.keys() 
                if key.startswith(context_path)
            ]
            for key in keys_to_remove:
                del self.load_cache[key]
                if key in self.cache_timestamps:
                    del self.cache_timestamps[key]
            
            logger.info(f"Cleared cache for context: {context_path}")
        else:
            # Clear all cache
            self.load_cache.clear()
            self.cache_timestamps.clear()
            self.fallback_selectors.clear()
            logger.info("Cleared all selector loading cache")
    
    async def preload_contexts(self, contexts: List[str]) -> Dict[str, SelectorLoadResult]:
        """
        Preload selectors for multiple contexts.
        
        Args:
            contexts: List of context paths to preload
            
        Returns:
            Dict[str, SelectorLoadResult]: Loading results by context
        """
        results = {}
        
        # Create basic contexts for preloading
        semaphore = asyncio.Semaphore(self.max_concurrent_loads)
        
        async def preload_single_context(context_path: str) -> Tuple[str, SelectorLoadResult]:
            async with semaphore:
                # Parse context path to create SelectorContext
                parts = context_path.split('/')
                primary = parts[0] if len(parts) > 0 else None
                secondary = parts[1] if len(parts) > 1 else None
                tertiary = parts[2] if len(parts) > 2 else None
                
                context = SelectorContext(
                    primary_context=primary,
                    secondary_context=secondary,
                    tertiary_context=tertiary
                )
                
                result = await self.load_selectors(context=context, force_reload=True)
                return context_path, result
        
        # Load all contexts concurrently
        tasks = [preload_single_context(ctx) for ctx in contexts]
        load_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in load_results:
            if isinstance(result, Exception):
                logger.error(f"Error during preload: {result}")
            else:
                context_path, load_result = result
                results[context_path] = load_result
        
        logger.info(f"Preloaded {len(results)} contexts")
        return results


# Global loader instance
_context_loader: Optional[ContextBasedSelectorLoader] = None


def get_context_based_loader(selectors_root: Path) -> ContextBasedSelectorLoader:
    """
    Get or create the global context-based selector loader.
    
    Args:
        selectors_root: Root directory for selectors
        
    Returns:
        ContextBasedSelectorLoader: Global loader instance
    """
    global _context_loader
    
    if _context_loader is None:
        _context_loader = ContextBasedSelectorLoader(selectors_root)
    
    return _context_loader
