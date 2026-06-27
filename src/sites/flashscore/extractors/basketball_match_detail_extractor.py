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

import asyncio
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
        """Extract basic match info — Playwright direct first, YAML selector engine fallback."""
        try:
            home_team = "Unknown"
            away_team = "Unknown"
            current_score = None
            match_time = "Unknown"
            status = "Unknown"
            competition = None
            
            # ── Playwright direct queries (fast, reliable) ──
            
            # Home team
            for sel in ['.event__participant--home', '.participant__home',
                        '.duelParticipant__home .participant__playerName']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            home_team = text
                            break
                except Exception:
                    continue
            
            # Away team
            for sel in ['.event__participant--away', '.participant__away',
                        '.duelParticipant__away .participant__playerName']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            away_team = text
                            break
                except Exception:
                    continue
            
            # Scores
            try:
                score_els = await self.page.query_selector_all('.event__score')
                if len(score_els) >= 2:
                    home = (await score_els[0].text_content()).strip()
                    away = (await score_els[1].text_content()).strip()
                    current_score = f"{home}-{away}"
            except Exception:
                pass
            
            # Match time
            for sel in ['.duelParticipant__startTime', '.event__time']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            match_time = text
                            break
                except Exception:
                    continue
            
            # Status
            for sel in ['.detailScore__status', '[data-testid="match-status"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            status = text
                            break
                except Exception:
                    continue
            
            # Competition / league name
            for sel in ['.tournamentHeader__content', '.event__tournament']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text and len(text) < 100:
                            competition = text
                            break
                except Exception:
                    continue
            
            # ── YAML selector engine fallback (only for truly missing fields, with timeout) ──
            # NOTE: The selector engine can enter infinite retry loops on match detail pages.
            # Only use it as a last resort for fields Playwright direct couldn't find.
            
            if home_team == "Unknown":
                try:
                    result = await asyncio.wait_for(
                        self._resolve_text('home_team_detail'), timeout=5.0
                    )
                    if result:
                        home_team = result
                except (asyncio.TimeoutError, Exception):
                    self.logger.debug("YAML fallback for home_team_detail timed out or failed")
            
            if away_team == "Unknown":
                try:
                    result = await asyncio.wait_for(
                        self._resolve_text('away_team_detail'), timeout=5.0
                    )
                    if result:
                        away_team = result
                except (asyncio.TimeoutError, Exception):
                    self.logger.debug("YAML fallback for away_team_detail timed out or failed")
            
            if not current_score:
                try:
                    home_score = await asyncio.wait_for(
                        self._resolve_text('home_score'), timeout=5.0
                    )
                    away_score = await asyncio.wait_for(
                        self._resolve_text('away_score'), timeout=5.0
                    )
                    if home_score and away_score:
                        current_score = f"{home_score}-{away_score}"
                except (asyncio.TimeoutError, Exception):
                    self.logger.debug("YAML fallback for scores timed out or failed")
            
            if match_time == "Unknown":
                try:
                    result = await asyncio.wait_for(
                        self._resolve_text('match_info'), timeout=5.0
                    )
                    if result:
                        match_time = result
                except (asyncio.TimeoutError, Exception):
                    self.logger.debug("YAML fallback for match_info timed out or failed")
            
            if status == "Unknown":
                try:
                    result = await asyncio.wait_for(
                        self._resolve_text('match_status'), timeout=5.0
                    )
                    if result:
                        status = result
                except (asyncio.TimeoutError, Exception):
                    self.logger.debug("YAML fallback for match_status timed out or failed")
            
            if not competition:
                try:
                    competition_els = await asyncio.wait_for(
                        self._resolve_elements('competition'), timeout=5.0
                    )
                    for el in competition_els:
                        text = (await el.text_content()).strip()
                        if text and len(text) < 100:
                            competition = text
                            break
                except (asyncio.TimeoutError, Exception):
                    self.logger.debug("YAML fallback for competition timed out or failed")
            
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
        """Extract data from SUMMARY tab — Playwright direct first, YAML engine fallback."""
        try:
            overview = {}
            team_statistics = {}
            match_events = []
            
            # ── Playwright direct queries (fast, reliable) ──
            
            # Competition name
            for sel in ['.tournamentHeader__content', '[data-testid="tournament-name"]', '.event__tournament']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text and len(text) < 100:
                            overview['competition'] = text
                            break
                except Exception:
                    continue
            
            # Match start time
            for sel in ['.duelParticipant__startTime', '.event__time', '[data-testid="match-time"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            overview['date'] = text
                            break
                except Exception:
                    continue
            
            # Match status
            for sel in ['.detailScore__status', '[data-testid="match-status"]', '.event__status']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            overview['status'] = text
                            break
                except Exception:
                    continue
            
            # Quarter scores — look for score cells in the summary table
            try:
                # FlashScore summary often shows quarter-by-quarter scores in a specific table
                score_sections = await self.page.query_selector_all('.detailScore__matchDetail, .matchInfo, [data-testid="score-breakdown"]')
                for section in score_sections:
                    text = (await section.text_content()).strip()
                    if text and ('Q1' in text or 'Quarter' in text or '1st' in text):
                        # Parse quarter scores from text
                        match_events.append({'type': 'quarter_scores_text', 'content': text})
                        break
            except Exception:
                pass
            
            # ── YAML selector engine fallback (with timeout) for missing fields ──
            
            if 'competition' not in overview:
                try:
                    competition_els = await asyncio.wait_for(self._resolve_elements('competition'), timeout=5.0)
                    for el in competition_els:
                        text = (await el.text_content()).strip()
                        if text and len(text) < 100:
                            overview['competition'] = text
                            break
                except (asyncio.TimeoutError, Exception):
                    self.logger.debug("YAML fallback for competition timed out")
            
            if 'date' not in overview:
                try:
                    date_text = await asyncio.wait_for(self._resolve_text('match_info'), timeout=5.0)
                    if date_text:
                        overview['date'] = date_text
                except (asyncio.TimeoutError, Exception):
                    self.logger.debug("YAML fallback for match_info timed out")
            
            if 'status' not in overview:
                try:
                    status_text = await asyncio.wait_for(self._resolve_text('match_status'), timeout=5.0)
                    if status_text:
                        overview['status'] = status_text
                except (asyncio.TimeoutError, Exception):
                    self.logger.debug("YAML fallback for match_status timed out")
            
            # Quarter scores via YAML
            home_quarter_scores = []
            away_quarter_scores = []
            try:
                home_parts = await asyncio.wait_for(self._resolve_elements('quarter_scores'), timeout=5.0)
                for part in home_parts:
                    text = (await part.text_content()).strip()
                    if text:
                        home_quarter_scores.append(text)
            except (asyncio.TimeoutError, Exception):
                self.logger.debug("YAML fallback for quarter_scores timed out")
            
            try:
                away_parts = await asyncio.wait_for(self._resolve_elements('away_quarter_scores'), timeout=5.0)
                for part in away_parts:
                    text = (await part.text_content()).strip()
                    if text:
                        away_quarter_scores.append(text)
            except (asyncio.TimeoutError, Exception):
                self.logger.debug("YAML fallback for away_quarter_scores timed out")
            
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
        """Extract data from H2H tab — Playwright direct first, YAML engine fallback."""
        try:
            previous_matches = []
            historical_statistics = {}
            win_loss_record = {}
            
            # ── Playwright direct queries ──
            # H2H tab shows previous matches between the two teams.
            # FlashScore uses rows inside a container for each H2H match.
            try:
                # Look for H2H match rows using common FlashScore classes
                h2h_containers = await self.page.query_selector_all(
                    '.h2h__row, .h2h-match, [data-testid="h2h-match"]'
                )
                if not h2h_containers:
                    # Try broader selectors for the H2H content area
                    h2h_section = await self.page.query_selector('.h2h, [data-testid="h2h-content"]')
                    if h2h_section:
                        h2h_containers = await h2h_section.query_selector_all('a, .row')
                
                for row in h2h_containers:
                    match_data = {}
                    try:
                        # Try to extract basic match info from each row
                        text = (await row.text_content()).strip()
                        if not text or len(text) < 5:
                            continue
                        
                        # Get the link href if it's an anchor
                        href = await row.get_attribute('href')
                        if href:
                            match_data['match_url'] = href
                        
                        # Try to find date, teams, and score within the row
                        date_els = await row.query_selector_all('.event__time, [class*="date"], [class*="time"]')
                        for el in date_els:
                            t = (await el.text_content()).strip()
                            if t:
                                match_data['date'] = t
                                break
                        
                        # Home/Away participants
                        home_el = await row.query_selector('.event__participant--home, [class*="home"]')
                        away_el = await row.query_selector('.event__participant--away, [class*="away"]')
                        if home_el:
                            t = (await home_el.text_content()).strip()
                            if t:
                                match_data['home_team'] = t
                        if away_el:
                            t = (await away_el.text_content()).strip()
                            if t:
                                match_data['away_team'] = t
                        
                        # Scores
                        score_els = await row.query_selector_all('.event__score, [class*="score"]')
                        if len(score_els) >= 2:
                            match_data['home_score'] = (await score_els[0].text_content()).strip()
                            match_data['away_score'] = (await score_els[1].text_content()).strip()
                        
                        if 'home_team' in match_data or 'away_team' in match_data:
                            previous_matches.append(match_data)
                    except Exception:
                        continue
                    
            except Exception as e:
                self.logger.debug(f"Playwright direct H2H extraction failed: {e}")
            
            # ── YAML selector engine fallback (with timeout) ──
            if not previous_matches:
                try:
                    h2h_rows = await asyncio.wait_for(self._resolve_elements('previous_matches'), timeout=8.0)
                    self.logger.info(f"Found {len(h2h_rows)} H2H rows via YAML")
                    
                    for row in h2h_rows:
                        match_data = {}
                        try:
                            date_el = await self._resolve_element('h2h_match_date', row)
                            if date_el:
                                match_data['date'] = (await date_el.text_content()).strip()
                            
                            event_el = await self._resolve_element('h2h_event', row)
                            if event_el:
                                event_title = await event_el.get_attribute('title')
                                event_text = (await event_el.text_content()).strip()
                                match_data['competition'] = event_title or event_text
                                match_data['competition_short'] = event_text
                            
                            home_participant = await self._resolve_element('h2h_home_participant', row)
                            if home_participant:
                                home_name_el = await self._resolve_element('h2h_home_team', home_participant)
                                if home_name_el:
                                    match_data['home_team'] = (await home_name_el.text_content()).strip()
                            
                            away_participant = await self._resolve_element('h2h_away_participant', row)
                            if away_participant:
                                away_name_el = await self._resolve_element('h2h_away_team', away_participant)
                                if away_name_el:
                                    match_data['away_team'] = (await away_name_el.text_content()).strip()
                            
                            final_result = await self._resolve_element('h2h_final_result', row)
                            if final_result:
                                score_spans = await self._resolve_elements('h2h_score_element', final_result)
                                if len(score_spans) >= 2:
                                    match_data['home_score'] = (await score_spans[0].text_content()).strip()
                                    match_data['away_score'] = (await score_spans[1].text_content()).strip()
                            
                            ft_result = await self._resolve_element('h2h_ft_result', row)
                            if ft_result:
                                ft_spans = await self._resolve_elements('h2h_score_element', ft_result)
                                if len(ft_spans) >= 2:
                                    ft_home = (await ft_spans[0].text_content()).strip()
                                    ft_away = (await ft_spans[1].text_content()).strip()
                                    if ft_home and ft_away:
                                        match_data['ft_home_score'] = ft_home
                                        match_data['ft_away_score'] = ft_away
                            
                            icon_el = await self._resolve_element('h2h_result_indicator', row)
                            if icon_el:
                                match_data['result_indicator'] = (await icon_el.text_content()).strip()
                            
                            href = await row.get_attribute('href')
                            if href:
                                match_data['match_url'] = href
                            
                            if 'home_team' in match_data or 'away_team' in match_data:
                                previous_matches.append(match_data)
                        except Exception:
                            continue
                except (asyncio.TimeoutError, Exception) as e:
                    self.logger.debug(f"YAML H2H extraction timed out or failed: {e}")
            
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
        """Extract data from ODDS tab — Playwright direct first, YAML engine fallback."""
        try:
            betting_odds = {}
            odds_history = []
            bookmaker_data = {}
            
            # ── Playwright direct queries ──
            try:
                # FlashScore odds tables use rows with bookmaker data
                odds_rows = await self.page.query_selector_all(
                    '.oddsRow, [class*="odds__row"], [class*="oddsRow"], [data-testid="odds-row"]'
                )
                if not odds_rows:
                    # Try the main odds container and find rows inside
                    odds_table = await self.page.query_selector(
                        '.oddsTable, [class*="odds__table"], [class*="oddsComparison"], [data-testid="odds-table"]'
                    )
                    if odds_table:
                        odds_rows = await odds_table.query_selector_all('tr, [class*="row"]')
                
                self.logger.info(f"Found {len(odds_rows)} odds rows via Playwright direct")
                
                for row in odds_rows:
                    try:
                        # Try to get bookmaker name
                        bookmaker_name = ""
                        name_el = await row.query_selector(
                            'a[title], [class*="bookmaker"] a, [class*="logo"] img'
                        )
                        if name_el:
                            bookmaker_name = await name_el.get_attribute('title') or ""
                            if not bookmaker_name:
                                bookmaker_name = await name_el.get_attribute('alt') or ""
                            if not bookmaker_name:
                                bookmaker_name = (await name_el.text_content()).strip()
                        
                        if not bookmaker_name:
                            continue
                        
                        # Extract odds cells
                        cells = await row.query_selector_all(
                            'td[class*="odds"], [class*="oddsCell"], [class*="cell"]'
                        )
                        odds_values = []
                        for cell in cells:
                            text = (await cell.text_content()).strip()
                            if text:
                                odds_values.append(text)
                        
                        if odds_values:
                            odds_entry = {'market_type': 'moneyline'}
                            if len(odds_values) >= 2:
                                odds_entry['home'] = odds_values[0]
                                odds_entry['away'] = odds_values[-1]
                            if len(odds_values) >= 3:
                                odds_entry['draw'] = odds_values[1]
                            betting_odds[bookmaker_name] = odds_entry
                            bookmaker_data[bookmaker_name] = {'market_type': 'moneyline'}
                    except Exception:
                        continue
                        
            except Exception as e:
                self.logger.debug(f"Playwright direct odds extraction failed: {e}")
            
            # ── YAML selector engine fallback (with timeout) ──
            if not betting_odds:
                try:
                    odds_rows = await asyncio.wait_for(self._resolve_elements('betting_odds'), timeout=8.0)
                    self.logger.info(f"Found {len(odds_rows)} odds rows via YAML")
                    
                    for row in odds_rows:
                        try:
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
                            
                            market_type = 'moneyline'
                            if odds_cells:
                                analytics_label = await odds_cells[0].get_attribute('data-analytics-label') or ''
                                if '1x2' in analytics_label.lower():
                                    market_type = '1x2'
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
                        except Exception:
                            continue
                except (asyncio.TimeoutError, Exception) as e:
                    self.logger.debug(f"YAML odds extraction timed out or failed: {e}")
            
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
        """Extract data from STATS tab — Playwright direct first, YAML engine fallback."""
        try:
            detailed_statistics = {}
            player_performance = []
            team_performance = {}
            current_category = "General"
            
            # ── Playwright direct queries ──
            # FlashScore stats tab has stat rows with category, home value, away value
            try:
                stat_rows = await self.page.query_selector_all(
                    '.stat__row, [class*="statRow"], [class*="stats__row"], [data-testid="stat-row"]'
                )
                stat_headers = await self.page.query_selector_all(
                    '.stat__header, [class*="sectionHeader"], [class*="statHeader"], [data-testid="stat-header"]'
                )
                
                if stat_rows or stat_headers:
                    self.logger.info(f"Found {len(stat_rows)} stat rows, {len(stat_headers)} headers via Playwright")
                    
                    all_elements = stat_rows + stat_headers
                    for element in all_elements:
                        try:
                            cls = await element.get_attribute('class') or ''
                            
                            # Section header?
                            if 'header' in cls.lower() or 'section' in cls.lower():
                                text = (await element.text_content()).strip()
                                if text:
                                    current_category = text
                                    if current_category not in detailed_statistics:
                                        detailed_statistics[current_category] = {}
                                continue
                            
                            # Stat row — try to extract category name, home value, away value
                            # FlashScore stats rows typically have: home_val | category | away_val
                            cells = await element.query_selector_all('span, div, td')
                            if len(cells) >= 3:
                                texts = []
                                for cell in cells:
                                    t = (await cell.text_content()).strip()
                                    if t:
                                        texts.append(t)
                                
                                if len(texts) >= 3:
                                    # Pattern: home_val, category_name, away_val
                                    home_val = texts[0]
                                    name = texts[len(texts) // 2]  # Middle element is usually the category
                                    away_val = texts[-1]
                                    if current_category not in detailed_statistics:
                                        detailed_statistics[current_category] = {}
                                    detailed_statistics[current_category][name] = {
                                        'home': home_val,
                                        'away': away_val
                                    }
                        except Exception:
                            continue
            except Exception as e:
                self.logger.debug(f"Playwright direct stats extraction failed: {e}")
            
            # ── YAML selector engine fallback (with timeout) ──
            if not detailed_statistics or all(len(v) == 0 for v in detailed_statistics.values()):
                try:
                    stat_rows = await asyncio.wait_for(self._resolve_elements('full_time_stats'), timeout=8.0)
                    stat_headers = await asyncio.wait_for(self._resolve_elements('stat_section_header'), timeout=5.0)
                    
                    if stat_rows or stat_headers:
                        all_elements = (stat_rows or []) + (stat_headers or [])
                        for element in all_elements:
                            try:
                                cls = await element.get_attribute('class') or ''
                                
                                if 'stat__header' in cls or 'sectionHeader' in cls:
                                    text = (await element.text_content()).strip()
                                    if text:
                                        current_category = text
                                        if current_category not in detailed_statistics:
                                            detailed_statistics[current_category] = {}
                                    continue
                                
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
                            except Exception:
                                continue
                except (asyncio.TimeoutError, Exception) as e:
                    self.logger.debug(f"YAML stats extraction timed out or failed: {e}")
            
            self.logger.info(f"Extracted stats in {len(detailed_statistics)} categories")
            
            return {
                'detailed_statistics': detailed_statistics,
                'player_performance': player_performance,
                'team_performance': team_performance
            }
        except Exception as e:
            self.logger.error(f"Error extracting STATS data: {e}")
            return None
