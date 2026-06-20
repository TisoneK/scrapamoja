"""
Basketball match detail extractor implementing primary tab extraction.

Extends the base MatchDetailExtractor with basketball-specific implementations
for primary tabs: SUMMARY, H2H, ODDS, STATS.

Uses real FlashScore DOM selectors discovered via live page inspection.
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
        """Extract data from tertiary tabs (quarter-by-quarter stats)."""
        try:
            ft_stats = None
            q1_stats = None
            inc_ot_stats = None
            
            # FlashScore Stats tab has sub-filters: Match, 1st Quarter, 2nd Quarter, etc.
            # We navigate via the primary extractor which clicks the Stats sub-tab
            # Then we use the period filter links to get quarter data
            
            # Navigate to Stats tab first
            if await self.primary_extractor.navigate_to_tab('stats'):
                await self.page.wait_for_timeout(2000)
                
                # Extract full-time (match) stats
                ft_stats = await self._extract_stats_rows()
                
                # Try to click "1st Quarter" filter
                q1_stats = await self._extract_period_stats('1st Quarter')
                
                # Click back to "Match" filter, then try OT periods
                inc_ot_stats = await self._extract_period_stats('Full Time')
            
            return TertiaryData(
                inc_ot=inc_ot_stats,
                ft=ft_stats,
                q1=q1_stats
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting tertiary tabs: {e}")
            return TertiaryData(inc_ot=None, ft=None, q1=None)
    
    async def _extract_stats_rows(self) -> Optional[Dict[str, Any]]:
        """Extract stats from the currently visible stats content using real FlashScore DOM."""
        try:
            statistics = {}
            
            # FlashScore uses .wcl-row_2oCpS for each stat row
            # with .wcl-category_6sT1J for name, .wcl-homeValue for home, .wcl-awayValue for away
            stat_rows = await self.page.query_selector_all('.wcl-row_2oCpS')
            for row in stat_rows:
                category_el = await row.query_selector('.wcl-category_6sT1J')
                home_el = await row.query_selector('.wcl-homeValue_3Q-7P')
                away_el = await row.query_selector('.wcl-awayValue_Y-QR1')
                
                # Fallback selectors if primary ones fail (FlashScore obfuscated class names may change)
                if not category_el:
                    category_el = await row.query_selector('[class*="category"]')
                if not home_el:
                    home_el = await row.query_selector('[class*="homeValue"]')
                if not away_el:
                    away_el = await row.query_selector('[class*="awayValue"]')
                
                if category_el and home_el and away_el:
                    name = (await category_el.text_content()).strip()
                    home_val = (await home_el.text_content()).strip()
                    away_val = (await away_el.text_content()).strip()
                    statistics[name] = {'home': home_val, 'away': away_val}
            
            return statistics if statistics else None
            
        except Exception as e:
            self.logger.error(f"Error extracting stats rows: {e}")
            return None
    
    async def _extract_period_stats(self, period_name: str) -> Optional[Dict[str, Any]]:
        """Click a period filter and extract stats for that period."""
        try:
            # Look for the period filter link
            period_filters = await self.page.query_selector_all('.subFilterOver a, .filterOver a')
            for filt in period_filters:
                text = (await filt.text_content()).strip()
                if text == period_name:
                    await filt.click()
                    await self.page.wait_for_timeout(2000)
                    return await self._extract_stats_rows()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting period stats for {period_name}: {e}")
            return None


class BasketballPrimaryTabExtractor(PrimaryTabExtractor):
    """Basketball-specific primary tab extractor using real FlashScore DOM selectors."""
    
    async def _extract_summary_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from SUMMARY tab using real FlashScore selectors."""
        try:
            overview = {}
            team_statistics = {}
            match_events = []
            
            # Extract match overview information
            try:
                # Competition / tournament info
                competition_elements = await self.page.query_selector_all('.wcl-scores-overline-03_Jdp91, [class*="scores-overline"]')
                for el in competition_elements:
                    text = (await el.text_content()).strip()
                    if text and len(text) < 100:
                        if 'competition' not in overview:
                            overview['competition'] = text
                
                # Match start time
                time_el = await self.page.query_selector('.duelParticipant__startTime')
                if time_el:
                    overview['date'] = (await time_el.text_content()).strip()
                
                # Match status
                status_el = await self.page.query_selector('.fixedHeaderDuel__detailStatus')
                if status_el:
                    overview['status'] = (await status_el.text_content()).strip()
            except Exception as e:
                self.logger.debug(f"Error extracting overview: {e}")
            
            # Extract quarter/period scores from summary header
            try:
                home_quarter_scores = []
                away_quarter_scores = []
                
                # Home quarter scores: .smh__part.smh__home (not current)
                home_parts = await self.page.query_selector_all('.smh__part.smh__home:not(.smh__score)')
                for part in home_parts:
                    text = (await part.text_content()).strip()
                    if text:
                        home_quarter_scores.append(text)
                
                # Away quarter scores: .smh__part.smh__away (not current)
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
        """Extract data from H2H tab using real FlashScore selectors."""
        try:
            previous_matches = []
            historical_statistics = {}
            win_loss_record = {}
            
            # Extract previous matches from H2H rows
            try:
                h2h_rows = await self.page.query_selector_all('.h2h__row')
                for row in h2h_rows:
                    row_text = (await row.text_content()).strip()
                    if not row_text:
                        continue
                    
                    # H2H rows contain: date, competition, home, away, home_score, away_score, result
                    # Try to extract structured data
                    match_data = {'raw': row_text}
                    
                    # Try individual cell extraction
                    cells = await row.query_selector_all('td, span, div')
                    cell_texts = []
                    for cell in cells:
                        text = (await cell.text_content()).strip()
                        if text and len(text) < 50:
                            cell_texts.append(text)
                    
                    if len(cell_texts) >= 4:
                        match_data['date'] = cell_texts[0] if len(cell_texts) > 0 else ''
                        match_data['competition'] = cell_texts[1] if len(cell_texts) > 1 else ''
                        match_data['home_team'] = cell_texts[2] if len(cell_texts) > 2 else ''
                        match_data['away_team'] = cell_texts[3] if len(cell_texts) > 3 else ''
                    
                    previous_matches.append(match_data)
            except Exception as e:
                self.logger.debug(f"Error extracting H2H matches: {e}")
            
            return {
                'previous_matches': previous_matches,
                'historical_statistics': historical_statistics,
                'win_loss_record': win_loss_record
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting H2H data: {e}")
            return None
    
    async def _extract_odds_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from ODDS tab using real FlashScore selectors."""
        try:
            betting_odds = {}
            odds_history = []
            bookmaker_data = {}
            
            # Extract odds from the odds table
            # FlashScore uses .ui-table__row for each bookmaker row
            # with odds cells inside
            try:
                odds_rows = await self.page.query_selector_all('.ui-table__row')
                for row in odds_rows:
                    cells = await row.query_selector_all('.ui-table__cell, .oddsCell__odds')
                    cell_texts = []
                    for cell in cells:
                        text = (await cell.text_content()).strip()
                        if text:
                            cell_texts.append(text)
                    
                    if len(cell_texts) >= 3:
                        # Typically: bookmaker_name, home_odds, away_odds (or 1, X, 2)
                        bookmaker = cell_texts[0]
                        home_odds = cell_texts[1]
                        away_odds = cell_texts[-1]  # Last cell is away odds
                        
                        betting_odds[bookmaker] = {
                            'home': home_odds,
                            'away': away_odds
                        }
                        if len(cell_texts) >= 4:
                            betting_odds[bookmaker]['draw'] = cell_texts[2]
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
        """Extract data from STATS tab using real FlashScore selectors."""
        try:
            detailed_statistics = {}
            player_performance = []
            team_performance = {}
            
            # FlashScore Stats tab uses .wcl-row for each stat row
            # with .wcl-category for name, .wcl-homeValue for home, .wcl-awayValue for away
            try:
                # Get section headers (e.g., "Scoring", "Rebounding")
                current_category = "General"
                stat_rows = await self.page.query_selector_all('.wcl-row_2oCpS, .stat__header, [class*="sectionHeader"]')
                
                for element in stat_rows:
                    cls = await element.get_attribute('class') or ''
                    
                    # Check if this is a section header
                    if 'sectionHeader' in cls or 'stat__header' in cls:
                        text = (await element.text_content()).strip()
                        if text:
                            current_category = text
                            if current_category not in detailed_statistics:
                                detailed_statistics[current_category] = {}
                        continue
                    
                    # This is a stat row
                    category_el = await element.query_selector('[class*="category"]')
                    home_el = await element.query_selector('[class*="homeValue"]')
                    away_el = await element.query_selector('[class*="awayValue"]')
                    
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
