"""
Basketball tertiary tab extractor implementing statistical filter extraction.

Extends the base TertiaryTabExtractor with basketball-specific implementations
for tertiary filters: Inc OT, FT, Q1.
"""

from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.extractors.tertiary_tab_extractor import TertiaryTabExtractor
from src.sites.flashscore.models import PageState, TertiaryData
from datetime import datetime


class BasketballTertiaryTabExtractor(TertiaryTabExtractor):
    """Basketball-specific tertiary tab extractor."""
    
    async def _extract_inc_ot_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from Inc OT (Including Overtime) filter."""
        try:
            overtime_stats = {}
            including_ot_totals = {}
            
            # Extract overtime-specific statistics
            try:
                # Look for overtime period statistics
                ot_elements = await self.page.query_selector_all('.statRow--ot, .overtimeStat')
                for ot_element in ot_elements:
                    stat_name_element = await ot_element.query_selector('.statName')
                    home_value_element = await ot_element.query_selector('.statValue--home')
                    away_value_element = await ot_element.query_selector('.statValue--away')
                    
                    if stat_name_element and home_value_element and away_value_element:
                        stat_name = await stat_name_element.text_content()
                        home_value = await home_value_element.text_content()
                        away_value = await away_value_element.text_content()
                        
                        overtime_stats[stat_name.strip()] = {
                            'home': home_value.strip(),
                            'away': away_value.strip()
                        }
            except:
                pass
            
            # Extract including overtime totals
            try:
                total_elements = await self.page.query_selector_all('.totalStat--inc-ot')
                for total_element in total_elements:
                    total_name_element = await total_element.query_selector('.totalName')
                    total_value_element = await total_element.query_selector('.totalValue')
                    
                    if total_name_element and total_value_element:
                        total_name = await total_name_element.text_content()
                        total_value = await total_value_element.text_content()
                        
                        including_ot_totals[total_name.strip()] = total_value.strip()
            except:
                pass
            
            # Extract overtime period breakdown
            try:
                period_breakdown = []
                period_elements = await self.page.query_selector_all('.periodStat--ot')
                for period_element in period_elements:
                    period_name_element = await period_element.query_selector('.periodName')
                    period_stats_element = await period_element.query_selector('.periodStats')
                    
                    if period_name_element and period_stats_element:
                        period_name = await period_name_element.text_content()
                        period_stats = await period_stats_element.text_content()
                        
                        period_breakdown.append({
                            'period': period_name.strip(),
                            'stats': period_stats.strip()
                        })
                
                if period_breakdown:
                    overtime_stats['period_breakdown'] = period_breakdown
            except:
                pass
            
            return {
                'overtime_stats': overtime_stats,
                'including_ot_totals': including_ot_totals
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting Inc OT data: {e}")
            return None
    
    async def _extract_ft_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from FT (Full Time) filter."""
        try:
            full_time_stats = {}
            match_totals = {}
            
            # Extract full-time statistics
            try:
                ft_elements = await self.page.query_selector_all('.statRow--ft, .fulltimeStat')
                for ft_element in ft_elements:
                    stat_name_element = await ft_element.query_selector('.statName')
                    home_value_element = await ft_element.query_selector('.statValue--home')
                    away_value_element = await ft_element.query_selector('.statValue--away')
                    
                    if stat_name_element and home_value_element and away_value_element:
                        stat_name = await stat_name_element.text_content()
                        home_value = await home_value_element.text_content()
                        away_value = await away_value_element.text_content()
                        
                        full_time_stats[stat_name.strip()] = {
                            'home': home_value.strip(),
                            'away': away_value.strip()
                        }
            except:
                pass
            
            # Extract match totals
            try:
                total_elements = await self.page.query_selector_all('.totalStat--ft')
                for total_element in total_elements:
                    total_name_element = await total_element.query_selector('.totalName')
                    total_value_element = await total_element.query_selector('.totalValue')
                    
                    if total_name_element and total_value_element:
                        total_name = await total_name_element.text_content()
                        total_value = await total_value_element.text_content()
                        
                        match_totals[total_name.strip()] = total_value.strip()
            except:
                pass
            
            # Extract scoring progression
            try:
                scoring_progression = []
                progression_elements = await self.page.query_selector_all('.scoringProgression')
                for progression_element in progression_elements:
                    time_element = await progression_element.query_selector('.progressionTime')
                    score_element = await progression_element.query_selector('.progressionScore')
                    
                    if time_element and score_element:
                        time = await time_element.text_content()
                        score = await score_element.text_content()
                        
                        scoring_progression.append({
                            'time': time.strip(),
                            'score': score.strip()
                        })
                
                if scoring_progression:
                    full_time_stats['scoring_progression'] = scoring_progression
            except:
                pass
            
            return {
                'full_time_stats': full_time_stats,
                'match_totals': match_totals
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting FT data: {e}")
            return None
    
    async def _extract_q1_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from Q1 (First Quarter) filter."""
        try:
            first_quarter_stats = {}
            q1_breakdown = {}
            
            # Extract first quarter specific statistics
            try:
                q1_elements = await self.page.query_selector_all('.statRow--q1, .quarterStat--q1')
                for q1_element in q1_elements:
                    stat_name_element = await q1_element.query_selector('.statName')
                    home_value_element = await q1_element.query_selector('.statValue--home')
                    away_value_element = await q1_element.query_selector('.statValue--away')
                    
                    if stat_name_element and home_value_element and away_value_element:
                        stat_name = await stat_name_element.text_content()
                        home_value = await home_value_element.text_content()
                        away_value = await away_value_element.text_content()
                        
                        first_quarter_stats[stat_name.strip()] = {
                            'home': home_value.strip(),
                            'away': away_value.strip()
                        }
            except:
                pass
            
            # Extract quarter breakdown
            try:
                quarter_elements = await self.page.query_selector_all('.quarterBreakdown')
                for quarter_element in quarter_elements:
                    quarter_name_element = await quarter_element.query_selector('.quarterName')
                    quarter_stats_element = await quarter_element.query_selector('.quarterStats')
                    
                    if quarter_name_element and quarter_stats_element:
                        quarter_name = await quarter_name_element.text_content()
                        quarter_stats = await quarter_stats_element.text_content()
                        
                        q1_breakdown[quarter_name.strip()] = quarter_stats.strip()
            except:
                pass
            
            # Extract first quarter scoring timeline
            try:
                scoring_timeline = []
                timeline_elements = await self.page.query_selector_all('.q1ScoringEvent')
                for timeline_element in timeline_elements:
                    time_element = await timeline_element.query_selector('.eventTime')
                    team_element = await timeline_element.query_selector('.eventTeam')
                    points_element = await timeline_element.query_selector('.eventPoints')
                    
                    if time_element and team_element and points_element:
                        time = await time_element.text_content()
                        team = await team_element.text_content()
                        points = await points_element.text_content()
                        
                        scoring_timeline.append({
                            'time': time.strip(),
                            'team': team.strip(),
                            'points': points.strip()
                        })
                
                if scoring_timeline:
                    first_quarter_stats['scoring_timeline'] = scoring_timeline
            except:
                pass
            
            return {
                'first_quarter_stats': first_quarter_stats,
                'q1_breakdown': q1_breakdown
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting Q1 data: {e}")
            return None
