"""
Complex pattern flows registry.

This module handles registration and discovery of flows organized by domain.
Each domain (navigation, extraction, filtering, authentication) has its own
subfolder with specialized flows for that domain.
"""

# Navigation flows
from .navigation.match_nav import MatchNavigationFlow
from .navigation.live_nav import LiveNavigationFlow
from .navigation.competition_nav import CompetitionNavigationFlow

# Extraction flows
from .extraction.match_extract import MatchExtractionFlow
from .extraction.odds_extract import OddsExtractionFlow
from .extraction.stats_extract import StatsExtractionFlow

# Filtering flows
from .filtering.date_filter import DateFilteringFlow
from .filtering.sport_filter import SportFilteringFlow
from .filtering.competition_filter import CompetitionFilteringFlow

# Authentication flows
from .authentication.login_flow import LoginAuthenticationFlow
from .authentication.oauth_flow import OAuthAuthenticationFlow

# Registry organized by domain
DOMAIN_FLOWS = {
    'navigation': {
        'match': MatchNavigationFlow,
        'live': LiveNavigationFlow,
        'competition': CompetitionNavigationFlow,
    },
    'extraction': {
        'match': MatchExtractionFlow,
        'odds': OddsExtractionFlow,
        'stats': StatsExtractionFlow,
    },
    'filtering': {
        'date': DateFilteringFlow,
        'sport': SportFilteringFlow,
        'competition': CompetitionFilteringFlow,
    },
    'authentication': {
        'login': LoginAuthenticationFlow,
        'oauth': OAuthAuthenticationFlow,
    },
}

def get_flow(domain: str, flow_name: str):
    """Get a flow class by domain and name."""
    return DOMAIN_FLOWS.get(domain, {}).get(flow_name)

def list_domains():
    """List all available domains."""
    return list(DOMAIN_FLOWS.keys())

def list_domain_flows(domain: str):
    """List all flows in a specific domain."""
    return list(DOMAIN_FLOWS.get(domain, {}).keys())

def list_all_flows():
    """List all available flows with their domains."""
    all_flows = {}
    for domain, flows in DOMAIN_FLOWS.items():
        for flow_name in flows:
            all_flows[f"{domain}.{flow_name}"] = flows[flow_name]
    return all_flows
