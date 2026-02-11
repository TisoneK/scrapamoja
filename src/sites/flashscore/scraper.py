"""
Flashscore scraper implementation.

Example scraper demonstrating sports data extraction from Flashscore.
"""

from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from src.sites.base.site_scraper import BaseSiteScraper
from .flow import FlashscoreFlow
from .config import SITE_CONFIG
from src.selectors.context_manager import SelectorContext, get_context_manager, DOMState
from src.selectors.context_loader import get_context_based_loader
from src.observability.logger import get_logger


class FlashscoreScraper(BaseSiteScraper):
    """Flashscore scraper implementation."""
    
    site_id = SITE_CONFIG["id"]
    site_name = SITE_CONFIG["name"]
    base_url = SITE_CONFIG["base_url"]

    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.flow = FlashscoreFlow(page, selector_engine)
        self.logger = get_logger("flashscore.scraper")
        
        # Initialize hierarchical selector system
        selectors_root = Path(__file__).parent / "selectors"
        self.context_manager = get_context_manager(selectors_root)
        self.context_loader = get_context_based_loader(selectors_root)
        
        # Initialize context
        self.current_context: SelectorContext = None
        
        # Load selectors into registry will be done asynchronously after init
    
    async def initialize_selectors(self):
        """Initialize selectors asynchronously after scraper creation."""
        self.logger.info("Starting selector initialization...")
        await self._load_selectors()
        self.logger.info("Selector initialization completed")

    async def _load_selectors(self):
        """Load all YAML selectors into the selector engine registry."""
        try:
            selectors_root = Path(__file__).parent / "selectors"
            
            # Load all YAML files recursively
            yaml_files = list(selectors_root.rglob("*.yaml")) + list(selectors_root.rglob("*.yml"))
            
            for yaml_file in yaml_files:
                await self._load_selector_file(yaml_file)
                
            self.logger.info(f"Loaded {len(yaml_files)} selector files from {selectors_root}")
            
            # Log registry state for debugging
            if hasattr(self.context_loader, 'get_registry_state'):
                registry_state = self.context_loader.get_registry_state()
                self.logger.info(f"Registry state: {registry_state}", extra=registry_state)
            else:
                self.logger.warning("Context loader does not support registry state debugging")
            
        except Exception as e:
            self.logger.error(f"Failed to load selectors: {e}")
    
    async def _load_selector_file(self, yaml_file: Path):
        """Load a single selector YAML file into the registry."""
        try:
            import yaml
            
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return
            
            # Create selector name from file path
            selectors_root = Path(__file__).parent / "selectors"
            relative_path = yaml_file.relative_to(selectors_root)
            selector_name = str(relative_path.with_suffix('')).replace('\\', '.').replace('/', '.')
            
            self.logger.info(f"Loading selector file: {yaml_file} -> {selector_name}")
            
            # Create SemanticSelector from YAML data
            from src.models.selector_models import SemanticSelector
            
            # Convert strategies to proper format
            from src.models.selector_models import StrategyPattern, StrategyType
            strategies = []
            for i, strategy in enumerate(data.get('strategies', [])):
                strategy_pattern = StrategyPattern(
                    id=f"{selector_name}_strategy_{i}",
                    type=StrategyType(strategy.get('type', 'css')),
                    priority=len(strategies) + 1,  # Use order as priority
                    config={
                        'selector': strategy.get('selector'),
                        'weight': strategy.get('weight', 1.0)
                    }
                )
                strategies.append(strategy_pattern)
            
            selector = SemanticSelector(
                name=selector_name,
                description=data.get('description', ''),
                context=data.get('context', selector_name),
                strategies=strategies,
                validation_rules=data.get('validation_rules', []),
                confidence_threshold=data.get('confidence_threshold', 0.8),
                metadata={
                    'file_path': str(yaml_file),
                    **data.get('metadata', {})
                }
            )
            
            # Register with selector engine (only pass the selector object)
            success = await self.selector_engine.register_selector(selector)
            self.logger.info(f"Registered selector {selector_name}: {success}")
            
        except Exception as e:
            self.logger.error(f"Failed to load selector file {yaml_file}: {e}")

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
        self.current_context = self.context_manager.current_context

    async def _get_context_selectors(self, force_reload: bool = False):
        """Get selectors for current context."""
        if not self.current_context:
            return []
        
        result = await self.context_loader.load_selectors(
            context=self.current_context,
            force_reload=force_reload
        )
        return result.selectors

    async def scrape(self, **kwargs):
        """Perform scraping using hierarchical selectors."""
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

    async def extract_match_details(self, match_url: str, detail_type: str = "summary"):
        """Extract detailed data from a specific match page."""
        try:
            # Navigate to match page
            await self.page.goto(match_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Detect DOM state
            page_content = await self.page.content()
            dom_state = await self.context_manager.detect_dom_state(page_content)
            
            # Set context based on detail type
            if detail_type == "summary":
                await self._set_context("extraction", "match_summary", dom_state=dom_state)
            elif detail_type == "h2h":
                await self._set_context("extraction", "match_h2h", dom_state=dom_state)
            elif detail_type == "odds":
                await self._set_context("extraction", "match_odds", dom_state=dom_state)
            elif detail_type == "stats":
                await self._set_context("extraction", "match_stats", dom_state=dom_state)
            
            # Extract data based on context
            return await self._extract_context_data()
            
        except Exception as e:
            return {"error": f"Failed to extract match details: {str(e)}"}

    async def extract_match_statistics(self, match_url: str, tertiary_context: str = None):
        """Extract detailed statistics from a match page."""
        try:
            # Navigate to match page
            await self.page.goto(match_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Navigate to stats tab first
            await self._set_context("navigation", "tab_switching")
            stats_tab = await self.selector_engine.find(self.page, "stats_tab")
            if stats_tab:
                await stats_tab.click()
                await self.page.wait_for_timeout(2000)
            
            # Detect DOM state
            page_content = await self.page.content()
            dom_state = await self.context_manager.detect_dom_state(page_content)
            
            # Set tertiary context if specified
            if tertiary_context:
                await self._set_context("extraction", "match_stats", tertiary_context, dom_state=dom_state)
            else:
                await self._set_context("extraction", "match_stats", dom_state=dom_state)
            
            # Extract statistics data
            return await self._extract_context_data()
            
        except Exception as e:
            return {"error": f"Failed to extract match statistics: {str(e)}"}

    async def _extract_context_data(self):
        """Extract data using current context selectors."""
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
