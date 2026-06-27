"""
Basketball tertiary tab extractor implementing statistical filter extraction.

DEPRECATED: This YAML-only extractor has been superseded by the Playwright-direct
implementation in BasketballMatchDetailExtractor._extract_tertiary_tabs().

The new implementation uses live-site-verified selectors:
  - Period filter tabs: button[data-testid="wcl-tab"] inside [data-type="tertiary"]
  - Stat rows: [data-testid="wcl-statistics"] with category/value test IDs
  - Quarter scores: smh__part elements in the match header

This module is kept for backward compatibility and potential YAML-only use cases.
"""

from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.extractors.tertiary_tab_extractor import TertiaryTabExtractor
from src.sites.flashscore.models import PageState, TertiaryData
from datetime import datetime


class BasketballTertiaryTabExtractor(TertiaryTabExtractor):
    """Basketball-specific tertiary tab extractor — 100% YAML-driven selectors.
    
    DEPRECATED: Use BasketballMatchDetailExtractor._extract_tertiary_tabs() instead,
    which uses Playwright-direct selectors verified against the live FlashScore site.
    """
    
    async def _extract_inc_ot_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from Inc OT (Including Overtime) filter."""
        try:
            overtime_stats = {}
            including_ot_totals = {}
            
            try:
                ot_elements = await self._resolve_elements('ot_stat_row')
                for ot_element in ot_elements:
                    stat_name = await self._resolve_text('tertiary_stat_name', parent=ot_element)
                    home_value = await self._resolve_text('tertiary_stat_home_value', parent=ot_element)
                    away_value = await self._resolve_text('tertiary_stat_away_value', parent=ot_element)
                    
                    if stat_name and home_value and away_value:
                        overtime_stats[stat_name] = {
                            'home': home_value,
                            'away': away_value
                        }
            except Exception as e:
                self.logger.warning(f"Error extracting OT stat rows: {e}")
            
            try:
                total_elements = await self._resolve_elements('total_stat_inc_ot')
                for total_element in total_elements:
                    total_name = await self._resolve_text('total_name', parent=total_element)
                    total_value = await self._resolve_text('total_value', parent=total_element)
                    
                    if total_name and total_value:
                        including_ot_totals[total_name] = total_value
            except Exception as e:
                self.logger.warning(f"Error extracting inc-ot total stats: {e}")
            
            try:
                period_breakdown = []
                period_elements = await self._resolve_elements('period_stat_ot')
                for period_element in period_elements:
                    period_name = await self._resolve_text('period_name', parent=period_element)
                    period_stats = await self._resolve_text('period_stats', parent=period_element)
                    
                    if period_name and period_stats:
                        period_breakdown.append({
                            'period': period_name,
                            'stats': period_stats
                        })
                
                if period_breakdown:
                    overtime_stats['period_breakdown'] = period_breakdown
            except Exception as e:
                self.logger.warning(f"Error extracting OT period breakdown: {e}")
            
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
            
            try:
                ft_elements = await self._resolve_elements('ft_stat_row')
                for ft_element in ft_elements:
                    stat_name = await self._resolve_text('tertiary_stat_name', parent=ft_element)
                    home_value = await self._resolve_text('tertiary_stat_home_value', parent=ft_element)
                    away_value = await self._resolve_text('tertiary_stat_away_value', parent=ft_element)
                    
                    if stat_name and home_value and away_value:
                        full_time_stats[stat_name] = {
                            'home': home_value,
                            'away': away_value
                        }
            except Exception as e:
                self.logger.warning(f"Error extracting FT stat rows: {e}")
            
            try:
                total_elements = await self._resolve_elements('total_stat_ft')
                for total_element in total_elements:
                    total_name = await self._resolve_text('total_name', parent=total_element)
                    total_value = await self._resolve_text('total_value', parent=total_element)
                    
                    if total_name and total_value:
                        match_totals[total_name] = total_value
            except Exception as e:
                self.logger.warning(f"Error extracting FT total stats: {e}")
            
            try:
                scoring_progression = []
                progression_elements = await self._resolve_elements('scoring_progression')
                for progression_element in progression_elements:
                    time = await self._resolve_text('progression_time', parent=progression_element)
                    score = await self._resolve_text('progression_score', parent=progression_element)
                    
                    if time and score:
                        scoring_progression.append({
                            'time': time,
                            'score': score
                        })
                
                if scoring_progression:
                    full_time_stats['scoring_progression'] = scoring_progression
            except Exception as e:
                self.logger.warning(f"Error extracting scoring progression: {e}")
            
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
            
            try:
                q1_elements = await self._resolve_elements('q1_stat_row')
                for q1_element in q1_elements:
                    stat_name = await self._resolve_text('tertiary_stat_name', parent=q1_element)
                    home_value = await self._resolve_text('tertiary_stat_home_value', parent=q1_element)
                    away_value = await self._resolve_text('tertiary_stat_away_value', parent=q1_element)
                    
                    if stat_name and home_value and away_value:
                        first_quarter_stats[stat_name] = {
                            'home': home_value,
                            'away': away_value
                        }
            except Exception as e:
                self.logger.warning(f"Error extracting Q1 stat rows: {e}")
            
            try:
                quarter_elements = await self._resolve_elements('quarter_breakdown')
                for quarter_element in quarter_elements:
                    quarter_name = await self._resolve_text('quarter_name', parent=quarter_element)
                    quarter_stats = await self._resolve_text('quarter_stats', parent=quarter_element)
                    
                    if quarter_name and quarter_stats:
                        q1_breakdown[quarter_name] = quarter_stats
            except Exception as e:
                self.logger.warning(f"Error extracting quarter breakdown: {e}")
            
            try:
                scoring_timeline = []
                timeline_elements = await self._resolve_elements('q1_scoring_event')
                for timeline_element in timeline_elements:
                    time = await self._resolve_text('event_time', parent=timeline_element)
                    team = await self._resolve_text('event_team', parent=timeline_element)
                    points = await self._resolve_text('event_points', parent=timeline_element)
                    
                    if time and team and points:
                        scoring_timeline.append({
                            'time': time,
                            'team': team,
                            'points': points
                        })
                
                if scoring_timeline:
                    first_quarter_stats['scoring_timeline'] = scoring_timeline
            except Exception as e:
                self.logger.warning(f"Error extracting Q1 scoring timeline: {e}")
            
            return {
                'first_quarter_stats': first_quarter_stats,
                'q1_breakdown': q1_breakdown
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting Q1 data: {e}")
            return None
