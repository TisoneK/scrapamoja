"""
Basketball match detail extractor implementing primary tab extraction.

Extends the base MatchDetailExtractor with basketball-specific implementations
for primary tabs: SUMMARY, H2H, ODDS, STATS.

Selector strategy:
1. Primary: YAML-driven selector engine with fallback chains (volatile-selector resilient)
2. Fallback: Hardcoded Playwright selectors (confirmed via live page inspection)

The YAML selectors live in src/sites/flashscore/selectors/extraction/ and define
ordered fallback chains: data-testid → obfuscated class → partial class → xpath.
When FlashScore rotates CSS hashes, only the obfuscated class entries need updating
in the YAML — no Python code changes required.
"""

from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.extractors.match_detail_extractor import MatchDetailExtractor
from src.sites.flashscore.extractors.primary_tab_extractor import PrimaryTabExtractor
from src.sites.flashscore.models import (
    PageState, SummaryData, H2HData, OddsData, StatsData, 
    BasicMatchInfo, TertiaryData
)
from datetime import datetime


class BasketballMatchDetailExtractor(MatchDetailExtractor):
    """Basketball-specific match detail extractor."""
    
    def __init__(self, scraper: FlashscoreScraper):
        super().__init__(scraper)
        self.primary_extractor = BasketballPrimaryTabExtractor(scraper)
        self._selector_engine = getattr(scraper, 'selector_engine', None)
    
    async def _extract_basic_info(self, page_state: PageState) -> Optional[BasicMatchInfo]:
        """Extract basic match information from the match detail page using real FlashScore selectors."""
        try:
            # Extract team names - FlashScore uses .duelParticipant__home/away
            # with .participant__participantNameWrapper inside
            home_team = "Unknown"
            away_team = "Unknown"
            
            home_el = await self.page.query_selector('.duelParticipant__home .participant__participantNameWrapper')
            if not home_el:
                home_el = await self.page.query_selector('.duelParticipant__home')
            if home_el:
                text = await home_el.text_content()
                if text:
                    home_team = text.strip()
            
            away_el = await self.page.query_selector('.duelParticipant__away .participant__participantNameWrapper')
            if not away_el:
                away_el = await self.page.query_selector('.duelParticipant__away')
            if away_el:
                text = await away_el.text_content()
                if text:
                    away_team = text.strip()
            
            # Extract scores - FlashScore uses .smh__score with smh__home/smh__away classes
            home_score = None
            away_score = None
            
            home_score_el = await self.page.query_selector('.smh__score.smh__home')
            if home_score_el:
                home_score = (await home_score_el.text_content()).strip()
            
            away_score_el = await self.page.query_selector('.smh__score.smh__away')
            if away_score_el:
                away_score = (await away_score_el.text_content()).strip()
            
            current_score = f"{home_score}-{away_score}" if home_score and away_score else None
            
            # Extract match time - FlashScore uses .duelParticipant__startTime
            match_time = "Unknown"
            time_el = await self.page.query_selector('.duelParticipant__startTime')
            if time_el:
                match_time = (await time_el.text_content()).strip()
            
            # Extract status - FlashScore uses .fixedHeaderDuel__detailStatus
            status = "Unknown"
            status_el = await self.page.query_selector('.fixedHeaderDuel__detailStatus')
            if status_el:
                status = (await status_el.text_content()).strip()
            
            return BasicMatchInfo(
                home_team=home_team,
                away_team=away_team,
                current_score=current_score,
                match_time=match_time,
                status=status
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting basic info: {e}")
            return None
    
    async def _extract_summary_tab(self, page_state: PageState) -> Optional[SummaryData]:
        """Extract data from SUMMARY tab."""
        try:
            summary_data = await self.primary_extractor.extract_tab_data('summary')
            if not summary_data:
                return None
            
            return SummaryData(
                overview=summary_data.get('overview', {}),
                team_statistics=summary_data.get('team_statistics', {}),
                match_events=summary_data.get('match_events', [])
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting SUMMARY tab: {e}")
            return None
    
    async def _extract_h2h_tab(self, page_state: PageState) -> Optional[H2HData]:
        """Extract data from H2H tab."""
        try:
            h2h_data = await self.primary_extractor.extract_tab_data('h2h')
            if not h2h_data:
                return None
            
            return H2HData(
                previous_matches=h2h_data.get('previous_matches', []),
                historical_statistics=h2h_data.get('historical_statistics', {}),
                win_loss_record=h2h_data.get('win_loss_record', {})
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting H2H tab: {e}")
            return None
    
    async def _extract_odds_tab(self, page_state: PageState) -> Optional[OddsData]:
        """Extract data from ODDS tab."""
        try:
            odds_data = await self.primary_extractor.extract_tab_data('odds')
            if not odds_data:
                return None
            
            return OddsData(
                betting_odds=odds_data.get('betting_odds', {}),
                odds_history=odds_data.get('odds_history', []),
                bookmaker_data=odds_data.get('bookmaker_data', {})
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting ODDS tab: {e}")
            return None
    
    async def _extract_stats_tab(self, page_state: PageState) -> Optional[StatsData]:
        """Extract data from STATS tab."""
        try:
            stats_data = await self.primary_extractor.extract_tab_data('stats')
            if not stats_data:
                return None
            
            return StatsData(
                detailed_statistics=stats_data.get('detailed_statistics', {}),
                player_performance=stats_data.get('player_performance', []),
                team_performance=stats_data.get('team_performance', {})
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting STATS tab: {e}")
            return None
    
    async def _extract_tertiary_tabs(self, page_state: PageState) -> Optional[TertiaryData]:
        """Extract data from tertiary tabs (quarter-by-quarter stats).
        
        FlashScore structure for basketball stats:
        - Primary tabs: Match, Odds, H2H, Draw, Video
        - Under "Match" sub-tabs: Summary, Player stats, Stats, Lineups, Match History
        - Under "Stats" period filters: Match, 1st Quarter, 2nd Quarter, 3rd Quarter, 4th Quarter
        
        All navigation uses .wcl-tab_GS7ig buttons matched by text content.
        """
        try:
            ft_stats = None
            q1_stats = None
            inc_ot_stats = None
            
            # Navigate: first click "Match" primary tab, then "Stats" sub-tab
            if await self.primary_extractor.navigate_to_tab('stats'):
                await self.page.wait_for_timeout(2000)
                
                # Extract full-time (Match) stats - this is the default view
                ft_stats = await self._extract_stats_rows()
                
                # Try to click "1st Quarter" period filter
                q1_stats = await self._extract_period_stats('1st Quarter')
                
                # Click back to "Match" filter
                await self._click_period_filter('Match')
                await self.page.wait_for_timeout(1000)
                
                # The "Match" view includes OT by default for basketball
                inc_ot_stats = ft_stats
            
            return TertiaryData(
                inc_ot=inc_ot_stats,
                ft=ft_stats,
                q1=q1_stats
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting tertiary tabs: {e}")
            return TertiaryData(inc_ot=None, ft=None, q1=None)
    
    async def _extract_stats_rows(self) -> Optional[Dict[str, Any]]:
        """Extract stats from the currently visible stats content using real FlashScore DOM.
        
        DOM structure confirmed via live inspection:
        - Each stat row: .wcl-row_2oCpS [data-testid="wcl-statistics"]
        - Category name: .wcl-category_6sT1J [data-testid="wcl-statistics-category"] > span
        - Home value: .wcl-homeValue_3Q-7P [data-testid="wcl-statistics-value"] > span
        - Away value: .wcl-awayValue_Y-QR1 [data-testid="wcl-statistics-value"] > span
        - Section headers: .stat__header.sectionHeader (text: "Scoring", "Rebounds", "Other")
        """
        try:
            statistics = {}
            current_section = "General"
            
            # Get both stat rows and section headers in document order
            all_elements = await self.page.query_selector_all(
                '.wcl-row_2oCpS, .stat__header'
            )
            
            for element in all_elements:
                cls = await element.get_attribute('class') or ''
                
                # Check if this is a section header (e.g., "Scoring", "Rebounds", "Other")
                if 'stat__header' in cls:
                    text = (await element.text_content()).strip()
                    if text:
                        current_section = text
                        if current_section not in statistics:
                            statistics[current_section] = {}
                    continue
                
                # This is a stat row - extract category name, home value, away value
                # DOM structure: .wcl-row_2oCpS > .wcl-category_Ydwqh > (.wcl-homeValue + .wcl-category_6sT1J + .wcl-awayValue)
                # The .wcl-category_Ydwqh parent contains all three, so we must use the specific child selectors
                
                # Category name: use data-testid for reliability (obfuscated class names may change)
                # Must NOT use [class*="category"] as it matches the parent wrapper .wcl-category_Ydwqh
                category_el = await element.query_selector(
                    '[data-testid="wcl-statistics-category"] > span'
                )
                if not category_el:
                    category_el = await element.query_selector(
                        '[data-testid="wcl-statistics-category"]'
                    )
                if not category_el:
                    category_el = await element.query_selector(
                        '.wcl-category_6sT1J > span'
                    )
                if not category_el:
                    category_el = await element.query_selector(
                        '.wcl-category_6sT1J'
                    )
                
                # Home value: use specific selector first, then fallback
                home_el = await element.query_selector(
                    '.wcl-homeValue_3Q-7P [data-testid="wcl-statistics-value"] > span'
                )
                if not home_el:
                    home_el = await element.query_selector(
                        '.wcl-homeValue_3Q-7P [data-testid="wcl-statistics-value"]'
                    )
                if not home_el:
                    home_el = await element.query_selector(
                        '.wcl-homeValue_3Q-7P > span'
                    )
                if not home_el:
                    home_el = await element.query_selector(
                        '[class*="homeValue"] > span'
                    )
                if not home_el:
                    home_el = await element.query_selector(
                        '.wcl-homeValue_3Q-7P'
                    )
                
                # Away value: use specific selector first, then fallback
                away_el = await element.query_selector(
                    '.wcl-awayValue_Y-QR1 [data-testid="wcl-statistics-value"] > span'
                )
                if not away_el:
                    away_el = await element.query_selector(
                        '.wcl-awayValue_Y-QR1 [data-testid="wcl-statistics-value"]'
                    )
                if not away_el:
                    away_el = await element.query_selector(
                        '.wcl-awayValue_Y-QR1 > span'
                    )
                if not away_el:
                    away_el = await element.query_selector(
                        '[class*="awayValue"] > span'
                    )
                if not away_el:
                    away_el = await element.query_selector(
                        '.wcl-awayValue_Y-QR1'
                    )
                
                if category_el and home_el and away_el:
                    name = (await category_el.text_content()).strip()
                    home_val = (await home_el.text_content()).strip()
                    away_val = (await away_el.text_content()).strip()
                    
                    if current_section not in statistics:
                        statistics[current_section] = {}
                    statistics[current_section][name] = {'home': home_val, 'away': away_val}
            
            return statistics if statistics else None
            
        except Exception as e:
            self.logger.error(f"Error extracting stats rows: {e}")
            return None
    
    async def _extract_period_stats(self, period_name: str) -> Optional[Dict[str, Any]]:
        """Click a period filter and extract stats for that period.
        
        FlashScore uses .wcl-tab_GS7ig buttons for period sub-filters:
        "Match", "1st Quarter", "2nd Quarter", "3rd Quarter", "4th Quarter"
        """
        try:
            if await self._click_period_filter(period_name):
                await self.page.wait_for_timeout(2000)
                return await self._extract_stats_rows()
            return None
        except Exception as e:
            self.logger.error(f"Error extracting period stats for {period_name}: {e}")
            return None
    
    async def _click_period_filter(self, period_name: str) -> bool:
        """Click a period filter tab by matching its button text.
        
        Period filter tabs are .wcl-tab_GS7ig buttons under the Stats sub-tab
        with text like "Match", "1st Quarter", "2nd Quarter", etc.
        """
        try:
            tab_buttons = await self.page.query_selector_all('.wcl-tab_GS7ig, [class*="wcl-tab"]')
            for btn in tab_buttons:
                text = (await btn.text_content()).strip()
                if text == period_name:
                    await btn.click()
                    await self.page.wait_for_timeout(1500)
                    self.logger.info(f"Clicked period filter: {period_name}")
                    return True
            self.logger.debug(f"Period filter not found: {period_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error clicking period filter {period_name}: {e}")
            return False


class BasketballPrimaryTabExtractor(PrimaryTabExtractor):
    """Basketball-specific primary tab extractor using real FlashScore DOM selectors.
    
    FlashScore tab hierarchy (confirmed via live inspection):
    - Primary tabs: Match, Odds, H2H, Draw, Video  (.wcl-tab_GS7ig)
    - Under "Match" sub-tabs: Summary, Player stats, Stats, Lineups, Match History
    - Under "Odds" sub-tabs: Home/Away, 1X2, Over/Under, Asian handicap, etc.
    - Under "Odds" period tabs: FT including OT, 1st Half, 1st Qrt
    - Under "Stats" period tabs: Match, 1st Quarter, 2nd Quarter, 3rd Quarter, 4th Quarter
    
    All navigation uses .wcl-tab_GS7ig buttons matched by text content.
    
    Selector strategy:
    - Primary: YAML-driven selector engine with fallback chains
    - Fallback: Hardcoded Playwright selectors (confirmed via live page inspection)
    
    The YAML selectors define ordered fallback chains:
    data-testid → obfuscated class → partial class match → xpath
    When FlashScore rotates CSS hashes, only the YAML entries need updating.
    """
    
    def __init__(self, scraper: FlashscoreScraper):
        super().__init__(scraper)
        self._selector_engine = getattr(scraper, 'selector_engine', None)
    
    async def _resolve_elements(self, selector_name: str, parent=None) -> List[Any]:
        """Resolve elements using YAML-driven selector engine with fallback to hardcoded selectors.
        
        Args:
            selector_name: YAML selector ID (e.g., 'full_time_stats', 'previous_matches')
            parent: Optional parent element to search within. If None, searches page.
            
        Returns:
            List of ElementHandle objects, or empty list if not found.
        """
        if self._selector_engine:
            try:
                search_target = parent or self.page
                elements = await self._selector_engine.find_all(search_target, selector_name)
                if elements:
                    self.logger.debug(f"YAML selector '{selector_name}' resolved: {len(elements)} elements")
                    return elements
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed, using fallback: {e}")
        return []
    
    async def _resolve_element(self, selector_name: str, parent=None) -> Optional[Any]:
        """Resolve a single element using YAML-driven selector engine with fallback.
        
        Args:
            selector_name: YAML selector ID
            parent: Optional parent element to search within
            
        Returns:
            ElementHandle or None
        """
        elements = await self._resolve_elements(selector_name, parent)
        return elements[0] if elements else None
    
    async def _resolve_text(self, selector_name: str, parent=None) -> Optional[str]:
        """Resolve element text using YAML-driven selector engine with fallback.
        
        Args:
            selector_name: YAML selector ID
            parent: Optional parent element to search within
            
        Returns:
            Text content string or None
        """
        if self._selector_engine:
            try:
                search_target = parent or self.page
                text = await self._selector_engine.get_text(search_target, selector_name)
                if text:
                    return text
            except Exception as e:
                self.logger.debug(f"YAML text resolution for '{selector_name}' failed: {e}")
        return None
    
    async def _extract_summary_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from SUMMARY tab using YAML selectors with hardcoded fallback."""
        try:
            overview = {}
            team_statistics = {}
            match_events = []
            
            # Extract match overview information
            try:
                # Competition / tournament info (YAML-first, then hardcoded)
                competition_elements = await self._resolve_elements('competition')
                if not competition_elements:
                    competition_elements = await self.page.query_selector_all(
                        '.wcl-scores-overline-03_Jdp91, [class*="scores-overline"]'
                    )
                for el in competition_elements:
                    text = (await el.text_content()).strip()
                    if text and len(text) < 100:
                        if 'competition' not in overview:
                            overview['competition'] = text
                
                # Match start time (YAML selector: match_info)
                time_text = await self._resolve_text('match_info')
                if time_text:
                    overview['date'] = time_text
                else:
                    time_el = await self.page.query_selector('.duelParticipant__startTime')
                    if time_el:
                        overview['date'] = (await time_el.text_content()).strip()
                
                # Match status (YAML selector: match_status)
                status_text = await self._resolve_text('match_status')
                if status_text:
                    overview['status'] = status_text
                else:
                    status_el = await self.page.query_selector('.fixedHeaderDuel__detailStatus')
                    if status_el:
                        overview['status'] = (await status_el.text_content()).strip()
            except Exception as e:
                self.logger.debug(f"Error extracting overview: {e}")
            
            # Extract quarter/period scores from summary header
            try:
                home_quarter_scores = []
                away_quarter_scores = []
                
                # Quarter scores (YAML selector: quarter_scores, then hardcoded)
                home_parts = await self._resolve_elements('quarter_scores')
                if not home_parts:
                    home_parts = await self.page.query_selector_all('.smh__part.smh__home:not(.smh__score)')
                for part in home_parts:
                    text = (await part.text_content()).strip()
                    if text:
                        home_quarter_scores.append(text)
                
                away_parts = await self.page.query_selector_all('.smh__part.smh__away:not(.smh__score)')
                for part in away_parts:
                    text = (await part.text_content()).strip()
                    if text:
                        away_quarter_scores.append(text)
                
                if home_quarter_scores or away_quarter_scores:
                    team_statistics['quarter_scores'] = {
                        'home': home_quarter_scores,
                        'away': away_quarter_scores
                    }
            except Exception as e:
                self.logger.debug(f"Error extracting quarter scores: {e}")
            
            return {
                'overview': overview,
                'team_statistics': team_statistics,
                'match_events': match_events
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting SUMMARY data: {e}")
            return None
    
    async def _extract_h2h_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from H2H tab using real FlashScore selectors.
        
        H2H DOM structure (confirmed via live inspection):
        - Rows: <a class="h2h__row"> elements
        - Date: span[data-testid="wcl-stageTime"] (class contains wclH2h__date)
        - Competition: span.h2h__event > inner <span> text; title attr on .h2h__event has full name
        - Home team: .h2h__homeParticipant .wcl-name_jjfMf (or [data-testid="wcl-scores-simple-text-01"] inside)
        - Away team: .h2h__awayParticipant .wcl-name_jjfMf
        - Scores: .h2h__result--final > span[data-testid="wcl-tableScore"] (two elements: home_score, away_score)
        - Win/loss: .h2h__icon (text: "W", "L", etc.)
        - Section headers: .wcl-headerSection_SGpOR (text: "Last matches: TeamName", "Head-to-head matches")
        """
        try:
            previous_matches = []
            historical_statistics = {}
            win_loss_record = {}
            
            # Extract section headers to determine which team's recent matches
            section_headers = await self.page.query_selector_all('.h2h__section .wcl-headerSection_SGpOR, [class*="headerSection"]')
            sections = []
            for header in section_headers:
                text = (await header.text_content()).strip()
                if text:
                    sections.append(text)
            
            # Extract previous matches from H2H rows (YAML selector: previous_matches, fallback: .h2h__row)
            try:
                h2h_rows = await self._resolve_elements('previous_matches')
                if not h2h_rows:
                    h2h_rows = await self.page.query_selector_all('.h2h__row')
                self.logger.info(f"Found {len(h2h_rows)} H2H rows")
                
                for row in h2h_rows:
                    match_data = {}
                    
                    # Date: span[data-testid="wcl-stageTime"] or .wclH2h__date
                    date_el = await row.query_selector('[data-testid="wcl-stageTime"], .wclH2h__date, [class*="stageTime"]')
                    if date_el:
                        match_data['date'] = (await date_el.text_content()).strip()
                    
                    # Competition: .h2h__event title attribute has full name (e.g., "ACB (Spain)")
                    # Inner span has short name (e.g., "ACB")
                    event_el = await row.query_selector('.h2h__event')
                    if event_el:
                        event_title = await event_el.get_attribute('title')
                        event_text = (await event_el.text_content()).strip()
                        match_data['competition'] = event_title or event_text
                        match_data['competition_short'] = event_text
                    
                    # Home team: .h2h__homeParticipant with team name inside
                    home_participant = await row.query_selector('.h2h__homeParticipant')
                    if home_participant:
                        # Try .wcl-name_jjfMf first (confirmed working), then data-testid
                        home_name_el = await home_participant.query_selector(
                            '.wcl-name_jjfMf, '
                            '[data-testid="wcl-scores-simple-text-01"]'
                        )
                        if not home_name_el:
                            # Fallback: any bold span inside participant
                            home_name_el = await home_participant.query_selector(
                                '.wcl-bold_NZXv6, span'
                            )
                        if home_name_el:
                            match_data['home_team'] = (await home_name_el.text_content()).strip()
                    
                    # Away team: .h2h__awayParticipant with team name inside
                    away_participant = await row.query_selector('.h2h__awayParticipant')
                    if away_participant:
                        away_name_el = await away_participant.query_selector(
                            '.wcl-name_jjfMf, '
                            '[data-testid="wcl-scores-simple-text-01"]'
                        )
                        if not away_name_el:
                            away_name_el = await away_participant.query_selector(
                                '.wcl-bold_NZXv6, span'
                            )
                        if away_name_el:
                            match_data['away_team'] = (await away_name_el.text_content()).strip()
                    
                    # Scores: .h2h__result--final > span[data-testid="wcl-tableScore"]
                    # There are two score elements: home_score and away_score
                    final_result = await row.query_selector('.h2h__result--final')
                    if final_result:
                        score_spans = await final_result.query_selector_all('[data-testid="wcl-tableScore"]')
                        if len(score_spans) >= 2:
                            match_data['home_score'] = (await score_spans[0].text_content()).strip()
                            match_data['away_score'] = (await score_spans[1].text_content()).strip()
                    
                    # Also extract full-time result if different from final (for OT games)
                    ft_result = await row.query_selector('.h2h__result--fulltime')
                    if ft_result:
                        ft_spans = await ft_result.query_selector_all('[data-testid="wcl-tableScore"]')
                        if len(ft_spans) >= 2:
                            ft_home = (await ft_spans[0].text_content()).strip()
                            ft_away = (await ft_spans[1].text_content()).strip()
                            if ft_home and ft_away:
                                match_data['ft_home_score'] = ft_home
                                match_data['ft_away_score'] = ft_away
                    
                    # Win/loss indicator: .h2h__icon
                    icon_el = await row.query_selector('.h2h__icon')
                    if icon_el:
                        match_data['result_indicator'] = (await icon_el.text_content()).strip()
                    
                    # Match URL from the anchor's href
                    href = await row.get_attribute('href')
                    if href:
                        match_data['match_url'] = href
                    
                    # Only add if we got at least home/away teams
                    if 'home_team' in match_data or 'away_team' in match_data:
                        previous_matches.append(match_data)
                
                self.logger.info(f"Extracted {len(previous_matches)} H2H matches")
                
            except Exception as e:
                self.logger.debug(f"Error extracting H2H matches: {e}")
            
            # Calculate win/loss record from extracted matches
            if previous_matches:
                home_wins = 0
                away_wins = 0
                draws = 0
                for m in previous_matches:
                    indicator = m.get('result_indicator', '')
                    if indicator == 'W':
                        home_wins += 1
                    elif indicator == 'L':
                        away_wins += 1
                    else:
                        draws += 1
                win_loss_record = {
                    'home_wins': home_wins,
                    'away_wins': away_wins,
                    'draws': draws,
                    'total': len(previous_matches)
                }
            
            return {
                'previous_matches': previous_matches,
                'historical_statistics': historical_statistics,
                'win_loss_record': win_loss_record
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting H2H data: {e}")
            return None
    
    async def _extract_odds_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from ODDS tab using real FlashScore selectors.
        
        Odds DOM structure (confirmed via live inspection):
        - Rows: .ui-table__row
        - Bookmaker name: .oddsCell__bookmakerPart a[title] attribute (e.g., "1xBet", "bet365")
        - Odds cells: .oddsCell__odd elements
          - Text content = current odds value
          - Title attribute = "opening » current" (e.g., "1.54 » 1.38")
          - data-analytics-label = "block-table-N-marketType_position"
        - Market sub-filters: Home/Away, 1X2, Over/Under, etc.
        - Period sub-filters: FT including OT, 1st Half, 1st Qrt
        
        Basketball typically has 2 odds per row (home/away moneyline),
        while football/soccer has 3 (1/X/2).
        """
        try:
            betting_odds = {}
            odds_history = []
            bookmaker_data = {}
            
            # Extract current market odds (YAML selector: betting_odds, fallback: .ui-table__row)
            try:
                odds_rows = await self._resolve_elements('betting_odds')
                if not odds_rows:
                    odds_rows = await self.page.query_selector_all('.ui-table__row')
                self.logger.info(f"Found {len(odds_rows)} odds rows")
                
                for row in odds_rows:
                    # Bookmaker name from the logo link's title attribute
                    bookmaker_link = await row.query_selector('.oddsCell__bookmakerPart a[title]')
                    bookmaker_name = ""
                    if bookmaker_link:
                        bookmaker_name = await bookmaker_link.get_attribute('title') or ""
                    if not bookmaker_name:
                        # Fallback: try alt attribute on the logo image
                        logo_img = await row.query_selector('.oddsCell__bookmakerPart img[alt]')
                        if logo_img:
                            bookmaker_name = await logo_img.get_attribute('alt') or ""
                    
                    if not bookmaker_name:
                        continue
                    
                    # Odds values from .oddsCell__odd elements
                    odds_cells = await row.query_selector_all('.oddsCell__odd')
                    odds_values = []
                    opening_values = []
                    
                    for cell in odds_cells:
                        current_text = (await cell.text_content()).strip()
                        title_attr = await cell.get_attribute('title') or ""
                        
                        # Parse opening odds from title (format: "1.54 » 1.38")
                        opening_val = None
                        if ' » ' in title_attr:
                            parts = title_attr.split(' » ')
                            if len(parts) == 2:
                                try:
                                    opening_val = parts[0].strip()
                                except:
                                    pass
                        
                        odds_values.append(current_text)
                        if opening_val:
                            opening_values.append(opening_val)
                    
                    # Determine market type from analytics label or cell count
                    # Basketball moneyline (Home/Away): 2 cells
                    # Football 1X2: 3 cells
                    market_type = 'moneyline'  # Default
                    
                    # Get analytics label from first odds cell for market type detection
                    if odds_cells:
                        analytics_label = await odds_cells[0].get_attribute('data-analytics-label') or ''
                        if '1x2' in analytics_label.lower():
                            market_type = '1x2'
                        elif 'moneyline' in analytics_label.lower():
                            market_type = 'moneyline'
                        elif 'over' in analytics_label.lower():
                            market_type = 'over_under'
                    
                    # Store odds data
                    odds_entry = {}
                    if len(odds_values) >= 2:
                        odds_entry['home'] = odds_values[0]
                        odds_entry['away'] = odds_values[-1]
                    if len(odds_values) >= 3:
                        odds_entry['draw'] = odds_values[1]
                    
                    # Store opening odds if available
                    if opening_values:
                        opening_entry = {}
                        if len(opening_values) >= 2:
                            opening_entry['home'] = opening_values[0]
                            opening_entry['away'] = opening_values[-1]
                        if len(opening_values) >= 3:
                            opening_entry['draw'] = opening_values[1]
                        odds_entry['opening'] = opening_entry
                    
                    odds_entry['market_type'] = market_type
                    
                    betting_odds[bookmaker_name] = odds_entry
                    bookmaker_data[bookmaker_name] = {
                        'market_type': market_type,
                        'cell_count': len(odds_values)
                    }
                
                self.logger.info(f"Extracted odds for {len(betting_odds)} bookmakers")
                
            except Exception as e:
                self.logger.debug(f"Error extracting odds rows: {e}")
            
            return {
                'betting_odds': betting_odds,
                'odds_history': odds_history,
                'bookmaker_data': bookmaker_data
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting ODDS data: {e}")
            return None
    
    async def _extract_stats_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from STATS tab using real FlashScore selectors.
        
        Stats DOM structure (confirmed via live inspection):
        - Navigation: Click "Match" primary tab → "Stats" sub-tab
        - Each stat row: .wcl-row_2oCpS [data-testid="wcl-statistics"]
        - Category name: .wcl-category_6sT1J [data-testid="wcl-statistics-category"] > span
          (e.g., "Field goals attempts", "Field goals made", "Field goals %")
        - Home value: .wcl-homeValue_3Q-7P [data-testid="wcl-statistics-value"] > span
        - Away value: .wcl-awayValue_Y-QR1 [data-testid="wcl-statistics-value"] > span
        - Section headers: .stat__header.sectionHeader (text: "Scoring", "Rebounds", "Other")
        - Period sub-filters: .wcl-tab_GS7ig with text "Match", "1st Quarter", etc.
        """
        try:
            detailed_statistics = {}
            player_performance = []
            team_performance = {}
            
            # Get all stat elements in document order (YAML selectors, then hardcoded fallback)
            try:
                current_category = "General"
                # Try YAML selectors for stat rows and headers
                stat_rows = await self._resolve_elements('full_time_stats')
                stat_headers = await self._resolve_elements('stat_section_header')
                
                if stat_rows or stat_headers:
                    # YAML-driven path: combine rows and headers, sort by DOM position
                    all_elements = stat_rows + stat_headers
                    # Simple merge: iterate YAML-resolved elements
                else:
                    # Hardcoded fallback: query page directly
                    all_elements = await self.page.query_selector_all(
                        '.wcl-row_2oCpS, .stat__header'
                    )
                
                for element in all_elements:
                    cls = await element.get_attribute('class') or ''
                    
                    # Check if this is a section header (e.g., "Scoring", "Rebounds", "Other")
                    if 'stat__header' in cls:
                        text = (await element.text_content()).strip()
                        if text:
                            current_category = text
                            if current_category not in detailed_statistics:
                                detailed_statistics[current_category] = {}
                        continue
                    
                    # This is a stat row - YAML sub-selectors first, then hardcoded fallback
                    # Must NOT use [class*="category"] as it matches parent wrapper .wcl-category_Ydwqh
                    category_el = await self._resolve_element('stat_category_name', element)
                    if not category_el:
                        category_el = await element.query_selector('[data-testid="wcl-statistics-category"] > span')
                    if not category_el:
                        category_el = await element.query_selector('[data-testid="wcl-statistics-category"]')
                    if not category_el:
                        category_el = await element.query_selector('.wcl-category_6sT1J > span')
                    if not category_el:
                        category_el = await element.query_selector('.wcl-category_6sT1J')
                    
                    home_el = await self._resolve_element('stat_home_value', element)
                    if not home_el:
                        home_el = await element.query_selector('.wcl-homeValue_3Q-7P [data-testid="wcl-statistics-value"] > span')
                    if not home_el:
                        home_el = await element.query_selector('.wcl-homeValue_3Q-7P')
                    
                    away_el = await self._resolve_element('stat_away_value', element)
                    if not away_el:
                        away_el = await element.query_selector('.wcl-awayValue_Y-QR1 [data-testid="wcl-statistics-value"] > span')
                    if not away_el:
                        away_el = await element.query_selector('.wcl-awayValue_Y-QR1')
                    
                    if category_el and home_el and away_el:
                        name = (await category_el.text_content()).strip()
                        home_val = (await home_el.text_content()).strip()
                        away_val = (await away_el.text_content()).strip()
                        
                        if current_category not in detailed_statistics:
                            detailed_statistics[current_category] = {}
                        detailed_statistics[current_category][name] = {
                            'home': home_val,
                            'away': away_val
                        }
                
                self.logger.info(f"Extracted stats in {len(detailed_statistics)} categories")
                
            except Exception as e:
                self.logger.debug(f"Error extracting stats data: {e}")
            
            return {
                'detailed_statistics': detailed_statistics,
                'player_performance': player_performance,
                'team_performance': team_performance
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting STATS data: {e}")
            return None
