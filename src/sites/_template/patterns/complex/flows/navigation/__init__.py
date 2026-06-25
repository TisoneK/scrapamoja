"""
Navigation domain flows.

This package contains navigation-specific flows for complex sites.
Navigation flows handle page transitions, menu interactions, and
movement through different sections of a website.
"""

from .match_nav import MatchNavigationFlow
from .live_nav import LiveNavigationFlow
from .competition_nav import CompetitionNavigationFlow

__all__ = [
    'MatchNavigationFlow',
    'LiveNavigationFlow', 
    'CompetitionNavigationFlow'
]
