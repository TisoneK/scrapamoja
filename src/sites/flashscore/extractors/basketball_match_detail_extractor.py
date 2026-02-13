"""
Basketball match detail extractor implementing primary tab extraction.

Extends the base MatchDetailExtractor with basketball-specific implementations
for primary tabs: SUMMARY, H2H, ODDS, STATS.
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
        """Extract basic match information from the match detail page."""
        try:
            # Extract team names
            home_team_element = await self.page.query_selector('.participant__home .participant-name')
            away_team_element = await self.page.query_selector('.participant__away .participant-name')
            
            home_team = await home_team_element.text_content() if home_team_element else "Unknown"
            away_team = await away_team_element.text_content() if away_team_element else "Unknown"
            
            # Extract score
            score_elements = await self.page.query_selector_all('.scoreBox')
            home_score = None
            away_score = None
            if len(score_elements) >= 2:
                home_score = await score_elements[0].text_content()
                away_score = await score_elements[1].text_content()
            
            current_score = f"{home_score}-{away_score}" if home_score and away_score else None
            
            # Extract match time/status
            time_element = await self.page.query_selector('.mch__header__time')
            match_time = await time_element.text_content() if time_element else "Unknown"
            
            # Extract status
            status_element = await self.page.query_selector('.mch__header__status')
            status = await status_element.text_content() if status_element else "Unknown"
            
            return BasicMatchInfo(
                home_team=home_team.strip(),
                away_team=away_team.strip(),
                current_score=current_score,
                match_time=match_time.strip(),
                status=status.strip()
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
        """Extract data from tertiary tabs."""
        try:
            # For now, return empty tertiary data - will be implemented in tertiary extractor
            return TertiaryData(
                inc_ot=None,
                ft=None,
                q1=None
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting tertiary tabs: {e}")
            return None


class BasketballPrimaryTabExtractor(PrimaryTabExtractor):
    """Basketball-specific primary tab extractor."""
    
    async def _extract_summary_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from SUMMARY tab."""
        try:
            overview = {}
            team_statistics = {}
            match_events = []
            
            # Extract match overview information
            try:
                venue_element = await self.page.query_selector('.venueInfo')
                if venue_element:
                    overview['venue'] = await venue_element.text_content()
                
                date_element = await self.page.query_selector('.mch__header__date')
                if date_element:
                    overview['date'] = await date_element.text_content()
                
                competition_element = await self.page.query_selector('.tournamentHeader')
                if competition_element:
                    overview['competition'] = await competition_element.text_content()
            except:
                pass
            
            # Extract team statistics
            try:
                stat_elements = await self.page.query_selector_all('.statRow')
                for stat_element in stat_elements:
                    stat_name_element = await stat_element.query_selector('.statName')
                    home_value_element = await stat_element.query_selector('.statValue--home')
                    away_value_element = await stat_element.query_selector('.statValue--away')
                    
                    if stat_name_element and home_value_element and away_value_element:
                        stat_name = await stat_name_element.text_content()
                        home_value = await home_value_element.text_content()
                        away_value = await away_value_element.text_content()
                        
                        team_statistics[stat_name.strip()] = {
                            'home': home_value.strip(),
                            'away': away_value.strip()
                        }
            except:
                pass
            
            # Extract match events
            try:
                event_elements = await self.page.query_selector_all('.incident')
                for event_element in event_elements:
                    time_element = await event_element.query_selector('.incident__time')
                    type_element = await event_element.query_selector('.incident__type')
                    player_element = await event_element.query_selector('.incident__player')
                    
                    if time_element and type_element:
                        event = {
                            'time': await time_element.text_content(),
                            'type': await type_element.text_content(),
                            'player': await player_element.text_content() if player_element else None
                        }
                        match_events.append(event)
            except:
                pass
            
            return {
                'overview': overview,
                'team_statistics': team_statistics,
                'match_events': match_events
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting SUMMARY data: {e}")
            return None
    
    async def _extract_h2h_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from H2H tab."""
        try:
            previous_matches = []
            historical_statistics = {}
            win_loss_record = {}
            
            # Extract previous matches
            try:
                match_elements = await self.page.query_selector_all('.h2h__match')
                for match_element in match_elements:
                    date_element = await match_element.query_selector('.h2h__date')
                    home_team_element = await match_element.query_selector('.h2h__home')
                    away_team_element = await match_element.query_selector('.h2h__away')
                    score_element = await match_element.query_selector('.h2h__score')
                    
                    if date_element and home_team_element and away_team_element:
                        match = {
                            'date': await date_element.text_content(),
                            'home_team': await home_team_element.text_content(),
                            'away_team': await away_team_element.text_content(),
                            'score': await score_element.text_content() if score_element else None
                        }
                        previous_matches.append(match)
            except:
                pass
            
            # Extract win/loss record
            try:
                record_elements = await self.page.query_selector_all('.h2h__record')
                for record_element in record_elements:
                    team_element = await record_element.query_selector('.h2h__team')
                    wins_element = await record_element.query_selector('.h2h__wins')
                    losses_element = await record_element.query_selector('.h2h__losses')
                    
                    if team_element and wins_element and losses_element:
                        team = await team_element.text_content()
                        wins = await wins_element.text_content()
                        losses = await losses_element.text_content()
                        
                        win_loss_record[team.strip()] = {
                            'wins': wins.strip(),
                            'losses': losses.strip()
                        }
            except:
                pass
            
            return {
                'previous_matches': previous_matches,
                'historical_statistics': historical_statistics,
                'win_loss_record': win_loss_record
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting H2H data: {e}")
            return None
    
    async def _extract_odds_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from ODDS tab."""
        try:
            betting_odds = {}
            odds_history = []
            bookmaker_data = {}
            
            # Extract current betting odds
            try:
                odds_elements = await self.page.query_selector_all('.oddsRow')
                for odds_element in odds_elements:
                    bookmaker_element = await odds_element.query_selector('.oddsBookmaker')
                    home_odds_element = await odds_element.query_selector('.oddsHome')
                    draw_odds_element = await odds_element.query_selector('.oddsDraw')
                    away_odds_element = await odds_element.query_selector('.oddsAway')
                    
                    if bookmaker_element and home_odds_element and away_odds_element:
                        bookmaker = await bookmaker_element.text_content()
                        home_odds = await home_odds_element.text_content()
                        away_odds = await away_odds_element.text_content()
                        draw_odds = await draw_odds_element.text_content() if draw_odds_element else None
                        
                        betting_odds[bookmaker.strip()] = {
                            'home': home_odds.strip(),
                            'away': away_odds.strip(),
                            'draw': draw_odds.strip() if draw_odds else None
                        }
            except:
                pass
            
            return {
                'betting_odds': betting_odds,
                'odds_history': odds_history,
                'bookmaker_data': bookmaker_data
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting ODDS data: {e}")
            return None
    
    async def _extract_stats_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from STATS tab."""
        try:
            detailed_statistics = {}
            player_performance = []
            team_performance = {}
            
            # Extract detailed statistics
            try:
                stat_categories = await self.page.query_selector_all('.statsCategory')
                for category in stat_categories:
                    category_name_element = await category.query_selector('.statsCategoryName')
                    if category_name_element:
                        category_name = await category_name_element.text_content()
                        category_stats = {}
                        
                        stat_rows = await category.query_selector_all('.statRow')
                        for stat_row in stat_rows:
                            stat_name_element = await stat_row.query_selector('.statName')
                            home_value_element = await stat_row.query_selector('.statValue--home')
                            away_value_element = await stat_row.query_selector('.statValue--away')
                            
                            if stat_name_element and home_value_element and away_value_element:
                                stat_name = await stat_name_element.text_content()
                                home_value = await home_value_element.text_content()
                                away_value = await away_value_element.text_content()
                                
                                category_stats[stat_name.strip()] = {
                                    'home': home_value.strip(),
                                    'away': away_value.strip()
                                }
                        
                        detailed_statistics[category_name.strip()] = category_stats
            except:
                pass
            
            # Extract player performance
            try:
                player_tables = await self.page.query_selector_all('.statsTable')
                for table in player_tables:
                    team_element = await table.query_selector('.statsTeamName')
                    if team_element:
                        team_name = await team_element.text_content()
                        
                        player_rows = await table.query_selector_all('.statsPlayerRow')
                        for player_row in player_rows:
                            player_name_element = await player_row.query_selector('.statsPlayerName')
                            player_stats_element = await player_row.query_selector('.statsPlayerStats')
                            
                            if player_name_element and player_stats_element:
                                player_name = await player_name_element.text_content()
                                player_stats = await player_stats_element.text_content()
                                
                                player_performance.append({
                                    'team': team_name.strip(),
                                    'player': player_name.strip(),
                                    'stats': player_stats.strip()
                                })
            except:
                pass
            
            return {
                'detailed_statistics': detailed_statistics,
                'player_performance': player_performance,
                'team_performance': team_performance
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting STATS data: {e}")
            return None
