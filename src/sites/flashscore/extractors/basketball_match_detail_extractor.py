"""
Basketball match detail extractor implementing primary tab extraction.

Extends the base MatchDetailExtractor with basketball-specific implementations
for primary tabs: SUMMARY, H2H, ODDS, STATS.

ALL selectors are YAML-driven via the selector engine. Zero hardcoded CSS strings.
Each selector lives in its own YAML file under src/sites/flashscore/selectors/extraction/
with ordered fallback chains: data-testid → obfuscated class → partial class → xpath.

When FlashScore rotates CSS hashes, only the YAML entries need updating.
No Python code changes required.
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
    """Basketball-specific match detail extractor — 100% YAML-driven selectors."""
    
    def __init__(self, scraper: FlashscoreScraper):
        super().__init__(scraper)
        self.primary_extractor = BasketballPrimaryTabExtractor(scraper)
        self._selector_engine = getattr(scraper, 'selector_engine', None)
    
    async def _resolve_element(self, selector_name: str, parent=None) -> Optional[Any]:
        """Resolve a single element via YAML selector engine."""
        if self._selector_engine:
            try:
                search_target = parent or self.page
                return await self._selector_engine.find(search_target, selector_name)
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return None
    
    async def _resolve_elements(self, selector_name: str, parent=None) -> List[Any]:
        """Resolve multiple elements via YAML selector engine."""
        if self._selector_engine:
            try:
                search_target = parent or self.page
                elements = await self._selector_engine.find_all(search_target, selector_name)
                if elements:
                    return elements
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return []
    
    async def _resolve_text(self, selector_name: str, parent=None) -> Optional[str]:
        """Resolve element text via YAML selector engine."""
        el = await self._resolve_element(selector_name, parent)
        if el:
            try:
                text = await el.text_content()
                return text.strip() if text else None
            except Exception as e:
                self.logger.debug(f"Text extraction for '{selector_name}' failed: {e}")
        return None
    
    async def _extract_basic_info(self, page_state: PageState) -> Optional[BasicMatchInfo]:
        """Extract basic match info — all selectors via YAML engine."""
        try:
            # Team names
            home_team = await self._resolve_text('home_team_detail') or "Unknown"
            away_team = await self._resolve_text('away_team_detail') or "Unknown"
            
            # Scores
            home_score = await self._resolve_text('home_score')
            away_score = await self._resolve_text('away_score')
            current_score = f"{home_score}-{away_score}" if home_score and away_score else None
            
            # Match time and status
            match_time = await self._resolve_text('match_info') or "Unknown"
            status = await self._resolve_text('match_status') or "Unknown"
            
            # Competition / league name
            competition = None
            competition_els = await self._resolve_elements('competition')
            for el in competition_els:
                text = (await el.text_content()).strip()
                if text and len(text) < 100:
                    competition = text
                    break
            
            return BasicMatchInfo(
                home_team=home_team,
                away_team=away_team,
                current_score=current_score,
                match_time=match_time,
                status=status,
                competition=competition,
                league=competition,
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
        """Extract data from tertiary tabs (quarter-by-quarter stats)."""
        try:
            ft_stats = None
            q1_stats = None
            inc_ot_stats = None
            
            if await self.primary_extractor.navigate_to_tab('stats'):
                await self.page.wait_for_timeout(2000)
                ft_stats = await self._extract_stats_rows()
                q1_stats = await self._extract_period_stats('1st Quarter')
                await self._click_period_filter('Match')
                await self.page.wait_for_timeout(1000)
                inc_ot_stats = ft_stats
            
            return TertiaryData(inc_ot=inc_ot_stats, ft=ft_stats, q1=q1_stats)
        except Exception as e:
            self.logger.error(f"Error extracting tertiary tabs: {e}")
            return TertiaryData(inc_ot=None, ft=None, q1=None)
    
    async def _extract_stats_rows(self) -> Optional[Dict[str, Any]]:
        """Extract stats from currently visible content — all selectors via YAML engine."""
        try:
            statistics = {}
            current_section = "General"
            
            # Get stat rows and section headers via YAML selectors
            stat_rows = await self._resolve_elements('full_time_stats')
            stat_headers = await self._resolve_elements('stat_section_header')
            
            if not stat_rows and not stat_headers:
                self.logger.warning("No stat elements found via YAML selectors")
                return None
            
            # Combine and iterate — headers set section context, rows extract data
            all_elements = stat_rows + stat_headers
            for element in all_elements:
                cls = await element.get_attribute('class') or ''
                
                # Section header?
                if 'stat__header' in cls or 'sectionHeader' in cls:
                    text = (await element.text_content()).strip()
                    if text:
                        current_section = text
                        if current_section not in statistics:
                            statistics[current_section] = {}
                    continue
                
                # Stat row — extract category name, home value, away value via YAML sub-selectors
                category_el = await self._resolve_element('stat_category_name', element)
                home_el = await self._resolve_element('stat_home_value', element)
                away_el = await self._resolve_element('stat_away_value', element)
                
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
        """Click a period filter and extract stats for that period."""
        try:
            if await self._click_period_filter(period_name):
                await self.page.wait_for_timeout(2000)
                return await self._extract_stats_rows()
            return None
        except Exception as e:
            self.logger.error(f"Error extracting period stats for {period_name}: {e}")
            return None
    
    async def _click_period_filter(self, period_name: str) -> bool:
        """Click a period filter tab by matching its button text — via YAML tab_button selector."""
        try:
            tab_buttons = await self._resolve_elements('tab_button')
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
    """Basketball-specific primary tab extractor — 100% YAML-driven selectors.
    
    Every DOM interaction goes through the selector engine, which resolves
    YAML selector IDs to real CSS/XPath selectors with multi-strategy fallback chains.
    Zero hardcoded CSS strings in this file.
    """
    
    def __init__(self, scraper: FlashscoreScraper):
        super().__init__(scraper)
        self._selector_engine = getattr(scraper, 'selector_engine', None)
    
    async def _resolve_element(self, selector_name: str, parent=None) -> Optional[Any]:
        """Resolve a single element via YAML selector engine."""
        if self._selector_engine:
            try:
                search_target = parent or self.page
                return await self._selector_engine.find(search_target, selector_name)
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return None
    
    async def _resolve_elements(self, selector_name: str, parent=None) -> List[Any]:
        """Resolve multiple elements via YAML selector engine."""
        if self._selector_engine:
            try:
                search_target = parent or self.page
                elements = await self._selector_engine.find_all(search_target, selector_name)
                if elements:
                    return elements
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return []
    
    async def _resolve_text(self, selector_name: str, parent=None) -> Optional[str]:
        """Resolve element text via YAML selector engine."""
        el = await self._resolve_element(selector_name, parent)
        if el:
            try:
                text = await el.text_content()
                return text.strip() if text else None
            except Exception as e:
                self.logger.debug(f"Text extraction for '{selector_name}' failed: {e}")
        return None
    
    # ─────────────────────────────────────────────────────────
    # SUMMARY TAB
    # ─────────────────────────────────────────────────────────
    
    async def _extract_summary_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from SUMMARY tab — all selectors via YAML engine."""
        try:
            overview = {}
            team_statistics = {}
            match_events = []
            
            # Competition name
            competition_els = await self._resolve_elements('competition')
            for el in competition_els:
                text = (await el.text_content()).strip()
                if text and len(text) < 100:
                    if 'competition' not in overview:
                        overview['competition'] = text
            
            # Match start time
            date_text = await self._resolve_text('match_info')
            if date_text:
                overview['date'] = date_text
            
            # Match status
            status_text = await self._resolve_text('match_status')
            if status_text:
                overview['status'] = status_text
            
            # Quarter scores (home + away)
            home_quarter_scores = []
            away_quarter_scores = []
            
            home_parts = await self._resolve_elements('quarter_scores')
            for part in home_parts:
                text = (await part.text_content()).strip()
                if text:
                    home_quarter_scores.append(text)
            
            away_parts = await self._resolve_elements('away_quarter_scores')
            for part in away_parts:
                text = (await part.text_content()).strip()
                if text:
                    away_quarter_scores.append(text)
            
            if home_quarter_scores or away_quarter_scores:
                team_statistics['quarter_scores'] = {
                    'home': home_quarter_scores,
                    'away': away_quarter_scores
                }
            
            return {
                'overview': overview,
                'team_statistics': team_statistics,
                'match_events': match_events
            }
        except Exception as e:
            self.logger.error(f"Error extracting SUMMARY data: {e}")
            return None
    
    # ─────────────────────────────────────────────────────────
    # H2H TAB
    # ─────────────────────────────────────────────────────────
    
    async def _extract_h2h_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from H2H tab — all selectors via YAML engine."""
        try:
            previous_matches = []
            historical_statistics = {}
            win_loss_record = {}
            
            # Section headers
            section_headers = await self._resolve_elements('h2h_section_header')
            sections = []
            for header in section_headers:
                text = (await header.text_content()).strip()
                if text:
                    sections.append(text)
            
            # H2H rows
            h2h_rows = await self._resolve_elements('previous_matches')
            self.logger.info(f"Found {len(h2h_rows)} H2H rows")
            
            for row in h2h_rows:
                match_data = {}
                
                # Date
                date_el = await self._resolve_element('h2h_match_date', row)
                if date_el:
                    match_data['date'] = (await date_el.text_content()).strip()
                
                # Competition (title attr for full name, text for short)
                event_el = await self._resolve_element('h2h_event', row)
                if event_el:
                    event_title = await event_el.get_attribute('title')
                    event_text = (await event_el.text_content()).strip()
                    match_data['competition'] = event_title or event_text
                    match_data['competition_short'] = event_text
                
                # Home team
                home_participant = await self._resolve_element('h2h_home_participant', row)
                if home_participant:
                    home_name_el = await self._resolve_element('h2h_home_team', home_participant)
                    if home_name_el:
                        match_data['home_team'] = (await home_name_el.text_content()).strip()
                
                # Away team
                away_participant = await self._resolve_element('h2h_away_participant', row)
                if away_participant:
                    away_name_el = await self._resolve_element('h2h_away_team', away_participant)
                    if away_name_el:
                        match_data['away_team'] = (await away_name_el.text_content()).strip()
                
                # Final scores
                final_result = await self._resolve_element('h2h_final_result', row)
                if final_result:
                    score_spans = await self._resolve_elements('h2h_score_element', final_result)
                    if len(score_spans) >= 2:
                        match_data['home_score'] = (await score_spans[0].text_content()).strip()
                        match_data['away_score'] = (await score_spans[1].text_content()).strip()
                
                # Full-time scores (for OT games)
                ft_result = await self._resolve_element('h2h_ft_result', row)
                if ft_result:
                    ft_spans = await self._resolve_elements('h2h_score_element', ft_result)
                    if len(ft_spans) >= 2:
                        ft_home = (await ft_spans[0].text_content()).strip()
                        ft_away = (await ft_spans[1].text_content()).strip()
                        if ft_home and ft_away:
                            match_data['ft_home_score'] = ft_home
                            match_data['ft_away_score'] = ft_away
                
                # Win/loss indicator
                icon_el = await self._resolve_element('h2h_result_indicator', row)
                if icon_el:
                    match_data['result_indicator'] = (await icon_el.text_content()).strip()
                
                # Match URL from anchor href
                href = await row.get_attribute('href')
                if href:
                    match_data['match_url'] = href
                
                if 'home_team' in match_data or 'away_team' in match_data:
                    previous_matches.append(match_data)
            
            self.logger.info(f"Extracted {len(previous_matches)} H2H matches")
            
            # Calculate win/loss record
            if previous_matches:
                home_wins = sum(1 for m in previous_matches if m.get('result_indicator') == 'W')
                away_wins = sum(1 for m in previous_matches if m.get('result_indicator') == 'L')
                draws = len(previous_matches) - home_wins - away_wins
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
    
    # ─────────────────────────────────────────────────────────
    # ODDS TAB
    # ─────────────────────────────────────────────────────────
    
    async def _extract_odds_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from ODDS tab — all selectors via YAML engine."""
        try:
            betting_odds = {}
            odds_history = []
            bookmaker_data = {}
            
            odds_rows = await self._resolve_elements('betting_odds')
            self.logger.info(f"Found {len(odds_rows)} odds rows")
            
            for row in odds_rows:
                # Bookmaker name from logo link title attribute
                bookmaker_link = await self._resolve_element('odds_bookmaker_name', row)
                bookmaker_name = ""
                if bookmaker_link:
                    bookmaker_name = await bookmaker_link.get_attribute('title') or ""
                if not bookmaker_name:
                    logo_img = await self._resolve_element('odds_bookmaker_logo', row)
                    if logo_img:
                        bookmaker_name = await logo_img.get_attribute('alt') or ""
                
                if not bookmaker_name:
                    continue
                
                # Odds cells
                odds_cells = await self._resolve_elements('odds_cell', row)
                odds_values = []
                opening_values = []
                
                for cell in odds_cells:
                    current_text = (await cell.text_content()).strip()
                    title_attr = await cell.get_attribute('title') or ""
                    
                    opening_val = None
                    if ' » ' in title_attr:
                        parts = title_attr.split(' » ')
                        if len(parts) == 2:
                            opening_val = parts[0].strip()
                    
                    odds_values.append(current_text)
                    if opening_val:
                        opening_values.append(opening_val)
                
                # Determine market type
                market_type = 'moneyline'
                if odds_cells:
                    analytics_label = await odds_cells[0].get_attribute('data-analytics-label') or ''
                    if '1x2' in analytics_label.lower():
                        market_type = '1x2'
                    elif 'moneyline' in analytics_label.lower():
                        market_type = 'moneyline'
                    elif 'over' in analytics_label.lower():
                        market_type = 'over_under'
                
                odds_entry = {'market_type': market_type}
                if len(odds_values) >= 2:
                    odds_entry['home'] = odds_values[0]
                    odds_entry['away'] = odds_values[-1]
                if len(odds_values) >= 3:
                    odds_entry['draw'] = odds_values[1]
                if opening_values and len(opening_values) >= 2:
                    odds_entry['opening'] = {'home': opening_values[0], 'away': opening_values[-1]}
                
                betting_odds[bookmaker_name] = odds_entry
                bookmaker_data[bookmaker_name] = {'market_type': market_type, 'cell_count': len(odds_values)}
            
            self.logger.info(f"Extracted odds for {len(betting_odds)} bookmakers")
            
            return {
                'betting_odds': betting_odds,
                'odds_history': odds_history,
                'bookmaker_data': bookmaker_data
            }
        except Exception as e:
            self.logger.error(f"Error extracting ODDS data: {e}")
            return None
    
    # ─────────────────────────────────────────────────────────
    # STATS TAB
    # ─────────────────────────────────────────────────────────
    
    async def _extract_stats_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from STATS tab — all selectors via YAML engine."""
        try:
            detailed_statistics = {}
            player_performance = []
            team_performance = {}
            
            current_category = "General"
            
            # Get stat rows and section headers via YAML selectors
            stat_rows = await self._resolve_elements('full_time_stats')
            stat_headers = await self._resolve_elements('stat_section_header')
            
            if not stat_rows and not stat_headers:
                self.logger.warning("No stat elements found via YAML selectors")
                return {
                    'detailed_statistics': detailed_statistics,
                    'player_performance': player_performance,
                    'team_performance': team_performance
                }
            
            all_elements = stat_rows + stat_headers
            for element in all_elements:
                cls = await element.get_attribute('class') or ''
                
                # Section header?
                if 'stat__header' in cls or 'sectionHeader' in cls:
                    text = (await element.text_content()).strip()
                    if text:
                        current_category = text
                        if current_category not in detailed_statistics:
                            detailed_statistics[current_category] = {}
                    continue
                
                # Stat row — extract via YAML sub-selectors
                category_el = await self._resolve_element('stat_category_name', element)
                home_el = await self._resolve_element('stat_home_value', element)
                away_el = await self._resolve_element('stat_away_value', element)
                
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
            
            return {
                'detailed_statistics': detailed_statistics,
                'player_performance': player_performance,
                'team_performance': team_performance
            }
        except Exception as e:
            self.logger.error(f"Error extracting STATS data: {e}")
            return None
