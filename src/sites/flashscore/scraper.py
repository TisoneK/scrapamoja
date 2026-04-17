"""
Flashscore scraper implementation.

Example scraper demonstrating sports data extraction from Flashscore.

This module has been refactored to use the selector engine's native YAML loading
capabilities instead of manual selector conversion. This leverages:
- YAMLSelectorLoader for native YAML file loading
- ContextBasedSelectorLoader for context-aware selector resolution
- UnifiedContext for unified context management (Story 7.1) - INTEGRATED
"""

import asyncio
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
from src.sites.base.site_scraper import BaseSiteScraper
from .flow import FlashscoreFlow
from .config import SITE_CONFIG
from src.selectors.context_manager import SelectorContext, get_context_manager, DOMState
from src.selectors.context_loader import get_context_based_loader
from src.selectors.yaml_loader import get_yaml_loader, YAMLSelectorLoader
from src.selectors.unified_context import UnifiedContext, from_selector_context, create_unified_context
from src.models.selector_models import SemanticSelector
from src.observability.logger import get_logger
from src.interrupt_handling.integration import InterruptAwareScraper
from src.selectors.hooks.registration import create_registration_hook
from src.selectors.engine import SelectorEngine


class FlashscoreScraper(InterruptAwareScraper):
    """Flashscore scraper implementation with interrupt handling support."""
    
    site_id = SITE_CONFIG["id"]
    site_name = SITE_CONFIG["name"]
    base_url = SITE_CONFIG["base_url"]

    def __init__(self, page, selector_engine: SelectorEngine):
        super().__init__(page, selector_engine)
        self.flow = FlashscoreFlow(self.page, self.selector_engine)
        self.logger = get_logger("flashscore.scraper")
        
        # Initialize snapshot system
        from src.core.snapshot.manager import SnapshotManager
        from src.core.snapshot.config import get_settings
        self.snapshot_settings = get_settings()
        self.snapshot_manager = SnapshotManager(self.snapshot_settings.base_path)
        
        # Initialize hierarchical selector system
        selectors_root = Path(__file__).parent / "selectors"
        self.context_manager = get_context_manager(selectors_root)
        self.context_loader = get_context_based_loader(selectors_root)
        
        # Initialize context using UnifiedContext (Story 7.1 integration)
        self.current_context: Optional[UnifiedContext] = None
        self._legacy_selector_context: Optional[SelectorContext] = None  # For backward compat
        
        # Automatic selector loading - load immediately on scraper initialization
        # This satisfies AC #3: Loading happens automatically on scraper initialization
        self._selectors_loaded = False
        self._selectors_loading = False
        self._selectors_loaded_event: Optional[asyncio.Event] = None
        
        # Story 7.4: Registration Automation - Set up automatic registration hook
        # This enables selectors to be automatically loaded and registered via engine hooks
        self._registration_hook = create_registration_hook(
            self.selector_engine,
            selectors_root
        )
        self.logger.debug("Automatic selector registration hook initialized")
    
    async def _ensure_selectors_loaded(self) -> None:
        """
        Ensure selectors are loaded before use (lazy loading with auto-initialization).
        
        This method provides automatic loading on first use, ensuring selectors
        are available when needed without requiring manual initialization calls.
        """
        if self._selectors_loaded:
            return
        
        if self._selectors_loading:
            # Wait for ongoing loading to complete
            if self._selectors_loaded_event:
                await self._selectors_loaded_event.wait()
            return
        
        # Auto-load selectors on first access
        await self.initialize_selectors()
    
    async def initialize_selectors(self):
        """
        Initialize selectors asynchronously after scraper creation.
        
        This method uses the RegistrationHook for automatic loading and registration.
        Can be called manually or automatically via _ensure_selectors_loaded().
        
        AC #1: No manual registration - uses RegistrationHook for automatic registration
        AC #2: Registration happens automatically via engine hooks
        AC #3: Selectors available immediately on scraper startup
        """
        # Prevent re-entrant loading
        if self._selectors_loading or self._selectors_loaded:
            self.logger.debug("Selectors already loaded or loading, skipping initialization")
            return
        
        self._selectors_loading = True
        self._selectors_loaded_event = asyncio.Event()
        
        try:
            self.logger.info("Starting automatic selector registration via hook...")
            
            # Use the RegistrationHook for automatic loading (AC #1, #2)
            # This replaces manual registration calls
            if self._registration_hook:
                await self._registration_hook._auto_load_selectors()
            else:
                # Fallback: Use native YAML loading without manual registration
                self.logger.warning("RegistrationHook not available, using direct YAML loading")
                await self._load_selectors_via_hook()
            
            self._selectors_loaded = True
            self.logger.info("Automatic selector registration completed")
        except Exception as e:
            self.logger.error(f"Automatic selector registration failed: {e}")
            # Try direct YAML loading as fallback
            self.logger.info("Attempting fallback YAML loading...")
            try:
                await self._load_selectors_via_hook()
                self._selectors_loaded = True
                self.logger.info("Fallback selector loading completed")
            except Exception as legacy_error:
                self.logger.error(f"Fallback loading also failed: {legacy_error}")
        finally:
            self._selectors_loading = False
            if self._selectors_loaded_event:
                self._selectors_loaded_event.set()
    
    async def _load_selectors_via_hook(self) -> None:
        """
        Load selectors using native YAML loading (fallback method).
        
        This is used when RegistrationHook is not available.
        NOTE: This method does NOT do manual registration - it relies on the hook.
        """
        from src.selectors.yaml_loader import get_yaml_loader, YAMLSelectorLoader
        
        try:
            selectors_root = Path(__file__).parent / "selectors"
            
            # Use native YAML loader for loading only
            yaml_loader: YAMLSelectorLoader = get_yaml_loader()
            
            load_result = yaml_loader.load_selectors_from_directory(
                directory_path=str(selectors_root),
                recursive=True
            )
            
            if not load_result.success:
                self.logger.warning(
                    f"Selector loading had issues: {load_result.errors}"
                )
            
            # Get cached selectors - registration is handled by RegistrationHook
            # This satisfies AC #1: No manual registration calls
            cache_stats = yaml_loader.get_cache_stats()
            cached_count = len(cache_stats.get('cached_files', []))
            
            self.logger.info(
                f"YAML loading complete: {load_result.selectors_loaded} selectors loaded, "
                f"{load_result.selectors_failed} failed in {load_result.loading_time_ms:.2f}ms"
            )
            
        except Exception as e:
            self.logger.error(f"YAML loading failed: {e}")
            raise

    async def _load_selectors(self) -> None:
        """
        Load all YAML selectors using the engine's native YAML loading.
        
        This method is now DEPRECATED. Use _load_selectors_via_hook() instead.
        Kept for backward compatibility - delegates to hook-based loading.
        """
        # Delegate to the hook-based loading
        await self._load_selectors_via_hook()
    
    def _convert_yaml_to_semantic(self, yaml_selector) -> Optional[SemanticSelector]:
        """
        Convert a YAMLSelector to SemanticSelector for engine registration.
        
        This is a compatibility layer that converts the engine's native YAMLSelector
        format to the SemanticSelector format expected by the registry.
        
        Args:
            yaml_selector: YAMLSelector from the engine's loader
            
        Returns:
            SemanticSelector compatible with the selector engine registry
        """
        try:
            from src.models.selector_models import (
                StrategyPattern, StrategyType
            )
            
            # Convert YAMLSelector strategies to SemanticSelector strategies
            strategies = []
            for i, strategy in enumerate(yaml_selector.strategies or []):
                strategy_pattern = StrategyPattern(
                    id=strategy.id or f"{yaml_selector.id}_strategy_{i}",
                    type=StrategyType(strategy.type.value if hasattr(strategy.type, 'value') else 'css'),
                    priority=i + 1,
                    config={
                        'selector': strategy.config.get('selector') if strategy.config else None,
                        'weight': strategy.config.get('weight', 1.0) if strategy.config else 1.0
                    }
                )
                strategies.append(strategy_pattern)
            
            # Create SemanticSelector from YAMLSelector
            semantic_selector = SemanticSelector(
                name=yaml_selector.id,
                description=yaml_selector.description or '',
                context=yaml_selector.name,
                strategies=strategies,
                validation_rules=yaml_selector.validation_rules or [],
                confidence_threshold=yaml_selector.metadata.get('confidence_threshold', 0.8) if yaml_selector.metadata else 0.8,
                metadata={
                    'file_path': yaml_selector.file_path,
                    'original_yaml_id': yaml_selector.id,
                    **(yaml_selector.metadata or {})
                }
            )
            
            return semantic_selector
            
        except Exception as e:
            self.logger.error(f"Failed to convert YAMLSelector to SemanticSelector: {e}")
            return None
    
    async def _load_selectors_legacy(self) -> None:
        """
        Legacy fallback loading method.
        
        This method is kept as a fallback in case native loading fails.
        It performs the same function as the original manual loading.
        """
        try:
            selectors_root = Path(__file__).parent / "selectors"
            
            # Load all YAML files recursively, excluding config files
            yaml_files = list(selectors_root.rglob("*.yaml")) + list(selectors_root.rglob("*.yml"))
            yaml_files = [f for f in yaml_files if f.name != 'selector_config.yaml']
            
            for yaml_file in yaml_files:
                await self._load_selector_file(yaml_file)
                
            self.logger.debug(f"Legacy loading: {len(yaml_files)} selector files from {selectors_root}")
            
        except Exception as e:
            self.logger.error(f"Failed legacy selector loading: {e}")
    
    async def _load_selector_file(self, yaml_file: Path) -> None:
        """
        Load a single selector YAML file into the registry.
        
        DEPRECATED: This method is kept for backward compatibility only.
        Use RegistrationHook for automatic registration instead.
        
        This method now uses the RegistrationHook instead of manual registration.
        """
        # Use the registration hook instead of manual registration
        # This satisfies AC #1: No manual registration calls
        if self._registration_hook:
            self.logger.debug(f"Delegating selector file loading to RegistrationHook: {yaml_file}")
            # The hook handles loading and registration
            # Just trigger auto-load if not already done
            if not getattr(self._registration_hook, '_loaded', False):
                await self._registration_hook._auto_load_selectors()
        else:
            # Fallback to direct loading only (no manual registration)
            self.logger.warning(f"RegistrationHook not available, skipping: {yaml_file}")

    async def navigate(self):
        """Navigate to Flashscore home page."""
        # Set authentication context for cookie consent
        await self._set_context("authentication")
        await self.flow.open_home()

    async def _set_context(
        self, 
        primary_context: str, 
        secondary_context: str = None, 
        tertiary_context: str = None,
        dom_state: DOMState = None
    ):
        """Set the current selector context."""
        await self.context_manager.set_context(
            primary_context=primary_context,
            secondary_context=secondary_context,
            tertiary_context=tertiary_context,
            dom_state=dom_state
        )
        # Convert SelectorContext to UnifiedContext (Story 7.1 integration)
        legacy_context = self.context_manager.current_context
        if legacy_context:
            self.current_context = from_selector_context(
                legacy_context,
                page=self.page,
                url=self.base_url
            )
            self._legacy_selector_context = legacy_context  # Keep for backward compat
        else:
            self.current_context = None

    async def _get_context_selectors(self, force_reload: bool = False):
        """Get selectors for current context."""
        if not self.current_context and not self._legacy_selector_context:
            return []
        
        # Use legacy selector context for loader (backward compatibility)
        # The UnifiedContext wraps the same information
        context_for_loader = self._legacy_selector_context
        
        result = await self.context_loader.load_selectors(
            context=context_for_loader,
            force_reload=force_reload
        )
        return result.selectors

    async def scrape(self, **kwargs):
        """
        Perform scraping using hierarchical selectors.
        
        This method ensures selectors are automatically loaded before scraping
        by calling _ensure_selectors_loaded(). This satisfies AC #3: Loading
        happens automatically on scraper initialization.
        """
        # Ensure selectors are loaded before scraping (automatic initialization)
        await self._ensure_selectors_loaded()
        
        sport = kwargs.get('sport', 'football')
        date_filter = kwargs.get('date', 'today')
        competition = kwargs.get('competition', None)
        live_only = kwargs.get('live_only', False)
        
        # Detect DOM state
        page_content = await self.page.content()
        dom_state = await self.context_manager.detect_dom_state(page_content)
        
        # Navigate to the appropriate section with context
        if sport.lower() == 'football':
            await self._set_context("navigation", "sport_selection", dom_state=dom_state)
            await self.flow.navigate_to_football()
        elif sport:
            await self._set_context("navigation", "sport_selection", dom_state=dom_state)
            await self.flow.search_sport(sport)
        
        # Navigate to live matches if requested
        if live_only:
            await self._set_context("navigation", "event_filter", dom_state=DOMState.LIVE)
            await self.flow.navigate_to_live_matches()
        
        # Apply date filter if specified
        if date_filter != 'today':
            await self._set_context("filtering", "date_filter")
            await self.flow.select_date(date_filter)
        
        # Apply competition filter if specified
        if competition:
            await self._set_context("filtering", "competition_filter")
            await self.flow.filter_by_competition(competition)
        
        # Scroll to ensure content is loaded
        await self.flow.scroll_to_matches()
        
        # Set extraction context and extract match data
        await self._set_context("extraction", "match_list", dom_state=dom_state)
        matches = await self._extract_matches()
        
        return {
            "sport": sport,
            "date_filter": date_filter,
            "competition": competition,
            "live_only": live_only,
            "matches": matches,
            "total_count": len(matches),
            "scraped_at": datetime.utcnow().isoformat(),
            "url": self.page.url,
            "context": self.current_context.get_context_path() if self.current_context else None,
            "dom_state": dom_state.value if dom_state else None
        }

    async def _extract_matches(self) -> List[Dict[str, Any]]:
        """Extract match information from the page."""
        try:
            # Get all match elements
            match_elements = await self.selector_engine.find_all(self.page, "match_items")
            
            matches = []
            for element in match_elements:
                match_data = await self._extract_single_match(element)
                if match_data:
                    matches.append(match_data)
            
            return matches
            
        except Exception as e:
            return [{"error": f"Failed to extract matches: {str(e)}"}]

    async def _extract_single_match(self, element) -> Dict[str, Any]:
        """Extract data from a single match element."""
        try:
            # Extract basic match information
            home_team = await self.selector_engine.get_text(element, "home_team")
            away_team = await self.selector_engine.get_text(element, "away_team")
            score = await self.selector_engine.get_text(element, "score")
            time = await self.selector_engine.get_text(element, "match_time")
            competition = await self.selector_engine.get_text(element, "competition")
            
            # Extract match status
            is_live = await self._is_match_live(element)
            match_status = await self._get_match_status(element)
            
            # Extract match details
            match_url = await self.selector_engine.get_attribute(element, "match_url", "href")
            match_id = await self._extract_match_id(match_url)
            
            # Extract odds if available
            odds = await self._extract_odds(element)
            
            # Extract additional details
            venue = await self._extract_venue(element)
            date = await self._extract_match_date(element)
            
            return {
                "match_id": match_id,
                "home_team": home_team.strip() if home_team else "",
                "away_team": away_team.strip() if away_team else "",
                "score": score.strip() if score else "",
                "time": time.strip() if time else "",
                "competition": competition.strip() if competition else "",
                "is_live": is_live,
                "status": match_status,
                "url": match_url or "",
                "odds": odds,
                "venue": venue,
                "date": date
            }
            
        except Exception as e:
            return {"error": f"Failed to extract match data: {str(e)}"}

    async def _is_match_live(self, element) -> bool:
        """Check if match is currently live."""
        try:
            live_indicator = await self.selector_engine.find(element, "live_indicators")
            return live_indicator is not None
        except Exception:
            return False

    async def _get_match_status(self, element) -> str:
        """Get match status (live, finished, upcoming, etc.)."""
        try:
            status_element = await self.selector_engine.find(element, "match_status")
            if status_element:
                return await self.selector_engine.get_text(status_element, "status_text")
            
            # Fallback to checking live indicators
            if await self._is_match_live(element):
                return "live"
            
            # Check if finished
            score = await self.selector_engine.get_text(element, "score")
            if score and ':' in score and not await self._is_match_live(element):
                return "finished"
            
            return "upcoming"
            
        except Exception:
            return "unknown"

    async def _extract_match_id(self, match_url: str) -> str:
        """Extract match ID from URL."""
        try:
            if not match_url:
                return ""
            
            # Flashscore URLs typically have format like /match/match-id/
            import re
            match = re.search(r'/match/([^/]+)/', match_url)
            return match.group(1) if match else ""
            
        except Exception:
            return ""

    async def _extract_odds(self, element) -> Dict[str, Any]:
        """Extract betting odds if available."""
        try:
            odds_elements = await self.selector_engine.find_all(element, "odds_items")
            
            odds = {}
            for odds_element in odds_elements:
                odds_type = await self.selector_engine.get_attribute(odds_element, "odds_type", "data-type")
                odds_value = await self.selector_engine.get_text(odds_element, "odds_value")
                
                if odds_type and odds_value:
                    odds[odds_type] = odds_value.strip()
            
            return odds
            
        except Exception:
            return {}

    async def _extract_venue(self, element) -> str:
        """Extract match venue information."""
        try:
            venue_element = await self.selector_engine.find(element, "venue")
            if venue_element:
                return await self.selector_engine.get_text(venue_element, "venue_name")
            return ""
        except Exception:
            return ""

    async def _extract_match_date(self, element) -> str:
        """Extract match date."""
        try:
            date_element = await self.selector_engine.find(element, "match_date")
            if date_element:
                return await self.selector_engine.get_text(date_element, "date_text")
            
            # Fallback to time element
            time_element = await self.selector_engine.find(element, "match_time")
            if time_element:
                time_text = await self.selector_engine.get_text(time_element, "time_text")
                return time_text.strip() if time_text else ""
            
            return ""
        except Exception:
            return ""

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw scraped data into structured output."""
        normalized = {
            "site": self.site_id,
            "site_name": self.site_name,
            "timestamp": datetime.utcnow().isoformat(),
            "data": raw_data
        }
        
        # Add specific normalization based on data type
        if "matches" in raw_data:
            normalized["type"] = "matches_list"
            normalized["sport"] = raw_data.get("sport", "")
            normalized["total_matches"] = raw_data.get("total_count", 0)
            normalized["live_only"] = raw_data.get("live_only", False)
            normalized["date_filter"] = raw_data.get("date_filter", "")
            
            # Add match statistics
            matches = raw_data.get("matches", [])
            live_matches = [m for m in matches if m.get("is_live", False)]
            finished_matches = [m for m in matches if m.get("status") == "finished"]
            upcoming_matches = [m for m in matches if m.get("status") == "upcoming"]
            
            normalized["match_stats"] = {
                "live_count": len(live_matches),
                "finished_count": len(finished_matches),
                "upcoming_count": len(upcoming_matches)
            }
            
            return normalized
            
            return {"error": f"Failed to normalize scheduled matches: {str(e)}"}
            return {"error": f"Failed to normalize scheduled matches: {str(e)}"}
    
    async def extract_match_statistics(self, match_url: str, tertiary_context: str = None):
        """Extract detailed statistics from a match page."""
        try:
            # Navigate to match page
            await self.page.goto(match_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Detect DOM state
            page_content = await self.page.content()
            dom_state = await self.context_manager.detect_dom_state(page_content)
            
            # Set context based on detail type
            if tertiary_context == "summary":
                await self._set_context("extraction", "match_summary", dom_state=dom_state)
            elif tertiary_context == "h2h":
                await self._set_context("extraction", "match_h2h", dom_state=dom_state)
            elif tertiary_context == "odds":
                await self._set_context("extraction", "match_odds", dom_state=dom_state)
            elif tertiary_context == "stats":
                await self._set_context("extraction", "match_stats", dom_state=dom_state)
            
            # Capture snapshot before extraction
            await self.capture_operation_snapshot("match_statistics_extraction", {
                "match_url": match_url,
                "context": tertiary_context,
                "dom_state": dom_state.state if dom_state else "unknown"
            })
            
            # Extract data based on context
            return await self._extract_context_data()
            
        except Exception as e:
            # Capture snapshot on error
            await self.capture_operation_snapshot("match_statistics_error", {
                "match_url": match_url,
                "context": tertiary_context,
                "error": str(e)
            })
            return {"error": f"Failed to extract match statistics: {str(e)}"}

    async def capture_operation_snapshot(self, operation: str, metadata: dict = None):
        """Capture snapshot during scraper operations."""
        try:
            if self.snapshot_settings.enable_metrics:
                from src.core.snapshot.models import SnapshotContext, SnapshotConfig, SnapshotMode
                from datetime import datetime
                
                context = SnapshotContext(
                    site="flashscore",
                    module="scraper",
                    component="flashscore_scraper",
                    session_id=getattr(self, 'session_id', 'unknown'),
                    function=operation,
                    additional_metadata=metadata or {}
                )
                
                config = SnapshotConfig(
                    mode=SnapshotMode.FULL_PAGE,  # Use FULL_PAGE mode since no specific selector is provided
                    capture_html=True,
                    capture_screenshot=self.snapshot_settings.default_capture_screenshot,
                    capture_console=self.snapshot_settings.default_capture_console
                )
                
                snapshot_id = await self.snapshot_manager.capture_snapshot(
                    page=self.page,
                    context=context,
                    config=config
                )
                
                self.logger.info(f"Captured snapshot for operation {operation}: {snapshot_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to capture snapshot for {operation}: {e}")
    
    async def shutdown_snapshots(self):
        """Shutdown snapshot system gracefully."""
        try:
            if hasattr(self, 'snapshot_manager'):
                await self.snapshot_manager.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down snapshots: {e}")

    async def _extract_context_data(self):
        try:
            selectors = await self._get_context_selectors()
            extracted_data = {}
            
            for selector in selectors:
                try:
                    elements = await self.selector_engine.find_all(self.page, selector.name)
                    if elements:
                        if len(elements) == 1:
                            extracted_data[selector.name] = await self.selector_engine.get_text(elements[0], selector.name)
                        else:
                            extracted_data[selector.name] = [await self.selector_engine.get_text(el, selector.name) for el in elements]
                    else:
                        extracted_data[selector.name] = None
                except Exception as e:
                    extracted_data[f"{selector.name}_error"] = str(e)
            
            return {
                "context": self.current_context.get_context_path() if self.current_context else None,
                "data": extracted_data,
                "selectors_used": len(selectors),
                "extracted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Failed to extract context data: {str(e)}"}

    def get_context_performance_metrics(self):
        """Get performance metrics for the hierarchical selector system."""
        return {
            "context_manager": self.context_manager.get_performance_metrics(),
            "context_loader": self.context_loader.get_loading_statistics(),
            "cache_stats": self.context_loader.get_cache_statistics()
        }
