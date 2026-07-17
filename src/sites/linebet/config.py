"""
Linebet scraper configuration.

Linebet (https://linebet.com/en) is a sports-bookmaker SPA. The UI is
rendered client-side and the data (sports, fixtures, live events,
markets, odds) is fetched by the browser from a private JSON API under
``/api/...`` (and a handful of related hosts). Rather than parse the
DOM, this scraper runs in *hybrid mode*:

  1. A real Playwright browser is launched against ``linebet.com/en`` so
     Cloudflare / anti-bot heuristics pass.
  2. A :class:`src.network.interception.NetworkInterceptor` is attached
     **before** navigation and captures every JSON response whose URL
     matches one of :data:`API_URL_PATTERNS`.
  3. The captured payloads are decoded, normalised and returned as
     structured data — no DOM scraping required.

This module exposes the configuration that drives that pipeline.
"""

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Site registration — picked up by ScraperRegistry.
# Required fields: id, name, base_url, version, maintainer.
# ---------------------------------------------------------------------------
SITE_CONFIG: Dict[str, Any] = {
    "id": "linebet",
    "name": "Linebet",
    "base_url": "https://linebet.com/en",
    "version": "1.0.0",
    "maintainer": "Tisone Kironget <tisonkironget@gmail.com>",
    "description": (
        "Hybrid browser+API scraper for linebet.com — Playwright is used "
        "to bypass anti-bot, while the data itself is harvested from the "
        "site's own JSON API responses via NetworkInterceptor."
    ),
    "tags": ["sportsbook", "odds", "betting", "hybrid", "api_interception"],
}


# ---------------------------------------------------------------------------
# URL surface
# ---------------------------------------------------------------------------
SITE_DOMAIN = "linebet.com"
SUPPORTED_DOMAINS: List[str] = [
    "linebet.com",
    "www.linebet.com",
    "m.linebet.com",          # mobile mirror — same API
    "linebet1.com",           # occasional mirror domain
]

BASE_URL = "https://linebet.com/en"
HOME_URL = "https://linebet.com/en"
LIVE_URL = "https://linebet.com/en/live"


# ---------------------------------------------------------------------------
# Hybrid mode: which network responses count as "Linebet API"?
# ---------------------------------------------------------------------------
# These patterns are matched against response URLs by
# ``src.network.interception.patterns.match_url``. Order matters only for
# readability — match_url is OR-semantics.
#
# Known Linebet API surfaces (verified by inspecting the SPA's network
# tab in a real browser session):
#
#   * /api/list/*           — pre-match fixture lists / sports tree
#   * /api/live/*           — live in-play events
#   * /api/bet/*            — bet slips, market details
#   * /api/menu/*           — left-nav sports menu
#   * /api/translations/*   — i18n strings (optional, large)
#   * /api/info/*           — bookmaker info / settings
#
# We deliberately keep the patterns broad (prefix matches) so that when
# Linebet ships a new endpoint under /api/, we automatically pick it up.
API_URL_PATTERNS: List[str] = [
    "https://linebet.com/api/",
    "https://www.linebet.com/api/",
    "https://m.linebet.com/api/",
    "https://linebet1.com/api/",
]

# When replaying captured requests directly with httpx (advanced use), we
# need to forward these request headers from the browser session —
# without them the API returns 403.
REPLAY_FORWARD_HEADERS: List[str] = [
    "accept",
    "accept-language",
    "referer",
    "origin",
    "user-agent",
    "x-requested-with",
    "x-csrf-token",
    "cookie",
]


# ---------------------------------------------------------------------------
# Pipeline behaviour
# ---------------------------------------------------------------------------
# How long to wait (seconds) after navigation for the SPA to finish its
# first burst of API calls. Linebet typically settles in 4–8s on a warm
# connection; 12s gives headroom on cold starts / proxy.
DEFAULT_API_SETTLE_SECONDS = 12.0

# Hard cap on a single scrape call. The hybrid mode is browser-bound, so
# be generous — Cloudflare challenges can add 5–10s.
DEFAULT_SCRAPE_TIMEOUT_SECONDS = 60.0

# Maximum captured responses to retain in memory per scrape. Each
# Linebet API response is a few KB to a few hundred KB; 200 is a safe
# ceiling for a single page load.
MAX_CAPTURED_RESPONSES = 200

# Only keep responses whose Content-Type looks like JSON or whose body
# successfully decodes as JSON. This filters out the marketing-page HTML
# and static assets that may match an /api/ prefix by accident.
JSON_CONTENT_TYPE_HINTS: List[str] = [
    "application/json",
    "application/javascript",   # some endpoints wrap JSON in JSONP
    "text/json",
    "text/plain",               # many betting APIs lie about content-type
]


# ---------------------------------------------------------------------------
# Rate limiting & politeness
# ---------------------------------------------------------------------------
RATE_LIMIT_ENABLED = True
# Linebet is a real bookmaker; be conservative. We are not making direct
# API calls — the browser is — but we should still pace our *scrape*
# invocations to avoid tripping behavioural heuristics.
RATE_LIMIT_REQUESTS_PER_MINUTE = 6
RATE_LIMIT_REQUESTS_PER_HOUR = 120
RATE_LIMIT_WAIT_TIME = 10  # seconds to back off if a request fails


# ---------------------------------------------------------------------------
# Stealth / browser context
# ---------------------------------------------------------------------------
STEALTH_ENABLED = True
STEALTH_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
STEALTH_VIEWPORT = {"width": 1536, "height": 864}
STEALTH_LOCALE = "en-US"
STEALTH_TIMEZONE = "Europe/London"

BROWSER_HEADLESS = True
BROWSER_SLOWMO = 0           # ms — keep 0 in prod
BROWSER_IGNORE_HTTPS_ERRORS = False


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
ENABLE_PREMATCH = True
ENABLE_LIVE = True
ENABLE_MARKETS = True
ENABLE_ODDS = True
ENABLE_REPLAY_MODE = False   # if True, replay captured requests via httpx


# ---------------------------------------------------------------------------
# Convenience aggregations
# ---------------------------------------------------------------------------
def get_linebet_config() -> Dict[str, Any]:
    """Return the full configuration as a single dict."""
    return {
        "site": SITE_CONFIG,
        "urls": {
            "base_url": BASE_URL,
            "home_url": HOME_URL,
            "live_url": LIVE_URL,
        },
        "hybrid": {
            "api_url_patterns": API_URL_PATTERNS,
            "replay_forward_headers": REPLAY_FORWARD_HEADERS,
            "default_api_settle_seconds": DEFAULT_API_SETTLE_SECONDS,
            "default_scrape_timeout_seconds": DEFAULT_SCRAPE_TIMEOUT_SECONDS,
            "max_captured_responses": MAX_CAPTURED_RESPONSES,
            "json_content_type_hints": JSON_CONTENT_TYPE_HINTS,
        },
        "rate_limit": {
            "enabled": RATE_LIMIT_ENABLED,
            "requests_per_minute": RATE_LIMIT_REQUESTS_PER_MINUTE,
            "requests_per_hour": RATE_LIMIT_REQUESTS_PER_HOUR,
            "wait_time": RATE_LIMIT_WAIT_TIME,
        },
        "stealth": {
            "enabled": STEALTH_ENABLED,
            "user_agent": STEALTH_USER_AGENT,
            "viewport": STEALTH_VIEWPORT,
            "locale": STEALTH_LOCALE,
            "timezone": STEALTH_TIMEZONE,
        },
        "browser": {
            "headless": BROWSER_HEADLESS,
            "slowmo": BROWSER_SLOWMO,
            "ignore_https_errors": BROWSER_IGNORE_HTTPS_ERRORS,
        },
        "features": {
            "prematch": ENABLE_PREMATCH,
            "live": ENABLE_LIVE,
            "markets": ENABLE_MARKETS,
            "odds": ENABLE_ODDS,
            "replay_mode": ENABLE_REPLAY_MODE,
        },
    }


def is_feature_enabled(feature: str) -> bool:
    """Check whether a feature flag is on."""
    flags = {
        "prematch": ENABLE_PREMATCH,
        "live": ENABLE_LIVE,
        "markets": ENABLE_MARKETS,
        "odds": ENABLE_ODDS,
        "replay_mode": ENABLE_REPLAY_MODE,
    }
    return flags.get(feature, False)


def get_config_value(key: str, default: Any = None) -> Any:
    """Lookup a config value by dot-notation key (e.g. ``hybrid.max_captured_responses``)."""
    current: Any = get_linebet_config()
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def validate_config() -> List[str]:
    """Validate the module-level constants. Returns a list of error strings (empty = OK)."""
    errors: List[str] = []

    if not SITE_CONFIG.get("id"):
        errors.append("SITE_CONFIG.id is required")
    if not SITE_CONFIG.get("base_url", "").startswith("https://"):
        errors.append("SITE_CONFIG.base_url must be an https:// URL")
    if not API_URL_PATTERNS:
        errors.append("API_URL_PATTERNS cannot be empty — hybrid mode needs at least one pattern")
    if DEFAULT_API_SETTLE_SECONDS <= 0:
        errors.append("DEFAULT_API_SETTLE_SECONDS must be positive")
    if MAX_CAPTURED_RESPONSES <= 0:
        errors.append("MAX_CAPTURED_RESPONSES must be positive")

    return errors
