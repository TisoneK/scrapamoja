"""
Data models for Flashscore structured match extraction.

Defines the hierarchical data structure for match detail extraction
including primary and tertiary tab data.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class MatchMetadata:
    """Metadata about match extraction."""
    extraction_time: datetime
    source_url: str
    sport: str
    completeness_score: float  # 0.0-1.0


@dataclass
class BasicMatchInfo:
    """Basic match information from listing."""
    home_team: str
    away_team: str
    current_score: Optional[str]
    match_time: str
    status: str


@dataclass
class SummaryData:
    """Data from SUMMARY tab."""
    overview: Dict[str, Any]
    team_statistics: Dict[str, Any]
    match_events: List[Dict[str, Any]]


@dataclass
class H2HData:
    """Data from H2H (Head-to-Head) tab."""
    previous_matches: List[Dict[str, Any]]
    historical_statistics: Dict[str, Any]
    win_loss_record: Dict[str, Any]


@dataclass
class OddsData:
    """Data from ODDS tab."""
    betting_odds: Dict[str, Any]
    odds_history: List[Dict[str, Any]]
    bookmaker_data: Dict[str, Any]


@dataclass
class StatsData:
    """Data from STATS tab."""
    detailed_statistics: Dict[str, Any]
    player_performance: List[Dict[str, Any]]
    team_performance: Dict[str, Any]


@dataclass
class TertiaryData:
    """Data from tertiary statistical filters."""
    inc_ot: Optional[Dict[str, Any]]  # Including overtime
    ft: Optional[Dict[str, Any]]      # Full time
    q1: Optional[Dict[str, Any]]     # First quarter


@dataclass
class ExtractionMetadata:
    """Metadata about the extraction process."""
    tabs_extracted: List[str]
    failed_tabs: List[str]
    extraction_duration_ms: int
    retry_count: int


@dataclass
class StructuredMatch:
    """Complete structured match data with all tab information."""
    match_id: str
    metadata: MatchMetadata
    basic_info: BasicMatchInfo
    summary_tab: Optional[SummaryData]
    h2h_tab: Optional[H2HData]
    odds_tab: Optional[OddsData]
    stats_tab: Optional[StatsData]
    tertiary_tabs: Optional[TertiaryData]
    extraction_metadata: ExtractionMetadata


@dataclass
class NavigationState:
    """State information for navigation operations."""
    url: str
    verified: bool
    elements_present: bool
    timestamp: datetime


@dataclass
class PageState:
    """State information for page-level operations."""
    match_id: str
    url: str
    tabs_available: List[str]
    verified: bool
    timestamp: datetime


@dataclass
class MatchListing:
    """Match information from listing page."""
    match_id: str
    teams: Dict[str, str]  # {home: str, away: str}
    time: str
    status: str
    score: Optional[str] = None
