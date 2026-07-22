"""Per-skin configuration for the BetB2B / 1xbet family scraper.

This module is the customization surface of the betb2b base scraper. Every
parameter that varies between skins (domain, partner/ref id, project group
id ``gr``, country code, …) and every parameter that *could* vary but is
shared family-wide (feed endpoints, base betting headers, query params,
market-id and sport-id lookup tables) is declared here, on
:class:`BetB2BSkinConfig`.

A skin is a thin YAML file in ``src/sites/betb2b/skins/<name>.yaml`` that
overrides only what differs from the family defaults. Anything omitted
falls back to :data:`DEFAULT_SKIN_CONFIG`. Operators add a new bookmaker
to the scraper by dropping a YAML file in — no Python changes needed.

Example skin YAML (``skins/linebet.yaml``)::

    name: linebet
    domain: linebet.com
    partner: 189            # the ``partner=`` / ``ref=`` query param
    gr: 650                 # the ``gr=`` project-group id
    country: 87             # the internal ``country=`` id (NOT the ISO code)
    geo: KE                 # ISO country for proxy routing / config API
    language: en
    enabled: true
    notes: a BetB2B/1xbet skin. Multi-country; direct mode works from any non-flagged IP.

See :data:`DEFAULT_SKIN_CONFIG` for the full field list and
:meth:`BetB2BSkinConfig.from_yaml` for the loader.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml

from .markets import DEFAULT_MARKET_GROUPS, DEFAULT_MARKET_TYPES, MarketGroup, MarketTypeMap
from .sport_ids import DEFAULT_SPORT_MAP, SportMap


# ---------------------------------------------------------------------------
# Defaults — shared family-wide, overridable per skin
# ---------------------------------------------------------------------------
DEFAULT_BASE_BETTING_HEADERS: Dict[str, str] = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "is-srv": "false",
    "x-app-n": "__BETTING_APP__",
    "x-svc-source": "__BETTING_APP__",
    "x-requested-with": "XMLHttpRequest",
    "x-mobile-project-id": "0",
}

# Stable query params on the feed endpoints. Per-skin overrides go into
# ``BetB2BSkinConfig.extra_query_params``.
DEFAULT_FEED_QUERY_PARAMS: Dict[str, str] = {
    "lng": "en",
    "mode": "4",
    "country": "87",
    "top": "true",
    "virtualSports": "true",
}

# The endpoints a BetB2B skin exposes. Path templates are formatted with
# the skin's params (``root``, ``name``). All live under ``/service-api``.
DEFAULT_FEED_PATHS: Dict[str, str] = {
    # The two feed roots — same endpoint names + schema under each.
    "live_feed_root": "/service-api/LiveFeed",
    "line_feed_root": "/service-api/LineFeed",
    # Per-root endpoints (relative to the chosen root).
    "events_top": "/Get1x2_VZip",           # events + odds (top=true)
    "events_by_sport": "/Get1x2_VZip",      # same endpoint with ?sports=<id>
    "game": "/GetGameZip",                   # per-match full markets by ?id=<eventId>
    "top_champs": "/WebGetTopChampsZip",
    "sports_short": "/GetSportsShortZip",
    "top_games_stat": "/GetTopGamesStatZip",
    "express_day": "/service-api/main-{root}-feed/v1/expressDay",
}

# Bootstrap URL templates — the pages a browser opens to harvest cookies.
DEFAULT_BOOTSTRAP_PATHS: Dict[str, str] = {
    "home": "/en",
    "live": "/en/live",
    "line": "/en/line",  # generic prematch landing
}

# Default browser stealth profile — Chrome 124 on Linux x86_64. Skins can
# override if a particular bookmaker's WAF demands a different fingerprint.
DEFAULT_STEALTH_PROFILE: Dict[str, Any] = {
    "user_agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "viewport": {"width": 1536, "height": 864},
    "locale": "en-US",
    "timezone": "Europe/London",
    "headless": True,
}

# Cookie TTL — re-bootstrap if the harvested session is older than this.
# BetB2B session cookies typically last hours; we default conservatively.
DEFAULT_SESSION_TTL_SECONDS: int = 2 * 60 * 60  # 2 hours


# ---------------------------------------------------------------------------
# The config dataclass
# ---------------------------------------------------------------------------
@dataclass
class BetB2BSkinConfig:
    """A single bookmaker's BetB2B skin configuration.

    Everything needed to drive the family scraper for one domain. Built
    from defaults (:data:`DEFAULT_SKIN_CONFIG`) + per-skin YAML overrides.

    Attributes:
        name: skin id, e.g. ``"linebet"``. Used in logs, output metadata,
            and as the registry key.
        domain: bare hostname, e.g. ``"linebet.com"``.
        partner: the ``partner=`` / ``ref=`` query param value
            (linebet = 189). Identifies the affiliate / brand.
        gr: the ``gr=`` project-group id (linebet = 650). Identifies the
            skin inside the shared BetB2B backend.
        country: the internal BetB2B country id used in the ``country=``
            query param (NOT an ISO code — linebet Kenya = 87). Defaults
            to 87 which is the value seen live for linebet KE.
        geo: ISO 3166-1 alpha-2 country code for proxy routing and the
            config-API ``g=`` param (e.g. ``"KE"``).
        language: the ``lng=`` query param value.
        enabled: if False, the scraper refuses to run this skin.
        notes: free-form operator notes shown in ``info`` output.
        base_url: ``https://<domain>``. Computed from ``domain``.
        bootstrap_paths: which site paths to visit during cookie harvest.
            Defaults to home + live.
        feed_paths: feed endpoint path templates. See
            :data:`DEFAULT_FEED_PATHS`.
        feed_query_params: query params merged into every feed request.
            Per-skin overrides ``partner``/``gr``/``country``/``lng`` here.
        base_headers: required betting headers (``is-srv``,
            ``x-app-n``, …). Almost always family-shared.
        extra_headers: per-skin additional headers merged on top of
            ``base_headers`` (e.g. a custom ``x-project-id``).
        stealth_profile: Playwright context options.
        session_ttl_seconds: re-bootstrap cadence for harvested cookies.
        market_groups: ``G`` (group id) → :class:`MarketGroup` mapping.
            See :mod:`betb2b.markets`.
        market_types: ``T`` (market-type id) → :class:`MarketTypeMap`.
        sport_map: ``SI`` (sport id) → :class:`SportMap`.
        proxy_endpoint_id: the ProxyManager endpoint id this skin should
            route through. The operator wires the endpoint into
            ProxyManager separately and only names it here.
        allowed_countries: OPTIONAL egress ISO-code allow-list. Empty (default)
            = allow any egress; direct mode works anywhere. list of ISO codes this skin accepts traffic
            from. Used to validate the proxy's egress country before
            bootstrapping.
    """

    # ----- identity -----
    name: str
    domain: str
    partner: int = 189
    gr: int = 650
    country: int = 87
    geo: str = "KE"
    language: str = "en"
    enabled: bool = True
    notes: str = ""

    # ----- url surface (derived) -----
    base_url: str = ""

    # ----- endpoints / params -----
    bootstrap_paths: Dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_BOOTSTRAP_PATHS)
    )
    feed_paths: Dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_FEED_PATHS)
    )
    feed_query_params: Dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_FEED_QUERY_PARAMS)
    )
    base_headers: Dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_BASE_BETTING_HEADERS)
    )
    extra_headers: Dict[str, str] = field(default_factory=dict)

    # ----- stealth / browser -----
    stealth_profile: Dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULT_STEALTH_PROFILE)
    )
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS

    # ----- lookups -----
    market_groups: Dict[int, MarketGroup] = field(
        default_factory=lambda: dict(DEFAULT_MARKET_GROUPS)
    )
    market_types: Dict[int, MarketTypeMap] = field(
        default_factory=lambda: dict(DEFAULT_MARKET_TYPES)
    )
    sport_map: Dict[int, SportMap] = field(
        default_factory=lambda: dict(DEFAULT_SPORT_MAP)
    )

    # ----- proxy -----
    proxy_endpoint_id: Optional[str] = None
    # Empty = allow any egress (the default): betb2b/1xbet is multi-country and
    # DIRECT mode works out of the box from any non-flagged IP — no proxy and no
    # country needed. Only set this to gate a proxy to specific ISO codes when a
    # deployment genuinely requires it; otherwise leave it empty.
    allowed_countries: List[str] = field(default_factory=list)

    # ----- feature flags -----
    features: Dict[str, bool] = field(
        default_factory=lambda: {
            "prematch": True,
            "live": True,
            "markets": True,
            "odds": True,
            "raw_capture": True,
            "h2h": True,
            "html_harvest": True,   # browser-free event-id discovery from page HTML
            "subgames": False,      # fetch per-quarter/half sub-games (ADR-7 scoped ingestion; costs extra requests)
        }
    )

    def __post_init__(self) -> None:
        if not self.base_url:
            self.base_url = f"https://{self.domain}"
        # Always reflect the canonical identity fields back into the query
        # params + headers so callers can override `feed_query_params`
        # freely without losing partner/gr/country.
        self.feed_query_params.setdefault("partner", str(self.partner))
        self.feed_query_params.setdefault("gr", str(self.gr))
        self.feed_query_params.setdefault("country", str(self.country))
        self.feed_query_params.setdefault("lng", self.language)

    # ------------------------------------------------------------------ #
    # Constructors
    # ------------------------------------------------------------------ #
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BetB2BSkinConfig":
        """Build a skin config from a plain dict (e.g. parsed YAML).

        Unknown keys are rejected loudly — a typo in a YAML field should
        fail fast, not silently fall back to the default.
        """
        data = dict(data)  # shallow copy so we can mutate

        # Allow YAML to omit `domain` if `base_url` is set (or vice versa).
        if not data.get("domain") and data.get("base_url"):
            from urllib.parse import urlparse

            data["domain"] = urlparse(data["base_url"]).hostname or ""

        # Nested lookup tables: convert raw dicts to the typed dataclasses.
        mgroups_raw = data.pop("market_groups", None) or {}
        mtypes_raw = data.pop("market_types", None) or {}
        sports_raw = data.pop("sport_map", None) or {}
        # Feature flags merge onto the family defaults, exactly like the lookup
        # tables above: a skin that names one flag keeps every other default.
        # (Assigning the dict wholesale would leave the rest to whatever
        # default each call site happens to pass to `features.get`.)
        features_raw = data.pop("features", None) or {}

        # Pull known field names so we can pass the rest as kwargs and
        # detect unknown keys cleanly.
        import dataclasses as _dc

        known = {f.name for f in _dc.fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(
                f"Unknown skin config keys for {data.get('name', '?')!r}: "
                f"{sorted(unknown)}"
            )

        kwargs: Dict[str, Any] = {}
        for k in known:
            if k in data:
                kwargs[k] = data[k]

        cfg = cls(**kwargs)

        if features_raw:
            cfg.features = {**cfg.features, **{str(k): bool(v) for k, v in features_raw.items()}}

        # Merge nested lookup overrides on top of the family defaults.
        if mgroups_raw:
            mg = dict(DEFAULT_MARKET_GROUPS)
            for k, v in mgroups_raw.items():
                mg[int(k)] = MarketGroup(**v) if isinstance(v, dict) else v
            cfg.market_groups = mg
        if mtypes_raw:
            mt = dict(DEFAULT_MARKET_TYPES)
            for k, v in mtypes_raw.items():
                mt[int(k)] = MarketTypeMap(**v) if isinstance(v, dict) else v
            cfg.market_types = mt
        if sports_raw:
            sm = dict(DEFAULT_SPORT_MAP)
            for k, v in sports_raw.items():
                sm[int(k)] = SportMap(**v) if isinstance(v, dict) else v
            cfg.sport_map = sm

        return cfg

    @classmethod
    def from_yaml(cls, path: str | Path) -> "BetB2BSkinConfig":
        """Load a skin config from a YAML file.

        Args:
            path: path to the skin YAML. See ``skins/linebet.yaml`` for
                the canonical example.
        """
        p = Path(path)
        with p.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, Mapping):
            raise ValueError(f"skin config must be a mapping, got {type(data).__name__}")
        return cls.from_dict(data)

    # ------------------------------------------------------------------ #
    # Rendering helpers — feed URLs + headers
    # ------------------------------------------------------------------ #
    def feed_url(self, feed: str, *, root: str = "live", extra_params: Optional[Mapping[str, str]] = None) -> str:
        """Render a full feed URL for this skin.

        Args:
            feed: key into :attr:`feed_paths` (e.g. ``"events_top"``).
            root: ``"live"`` → ``LiveFeed`` root, ``"line"`` → ``LineFeed``.
            extra_params: per-call query param overrides merged on top of
                :attr:`feed_query_params`.

        Returns:
            Absolute URL, e.g.
            ``https://linebet.com/service-api/LiveFeed/Get1x2_VZip?...``.
        """
        if root not in ("live", "line"):
            raise ValueError(f"root must be 'live' or 'line', got {root!r}")

        root_key = f"{root}_feed_root"
        root_path = self.feed_paths.get(root_key)
        if not root_path:
            raise KeyError(f"feed_paths[{root_key!r}] is missing")

        endpoint_path = self.feed_paths.get(feed)
        if not endpoint_path:
            raise KeyError(f"feed_paths[{feed!r}] is missing")

        # Some endpoints (expressDay) live under a different root path
        # template — interpolate `root` into them directly.
        if "{root}" in endpoint_path:
            path = endpoint_path.format(root=root)
        else:
            path = root_path + endpoint_path

        params: Dict[str, str] = dict(self.feed_query_params)
        if extra_params:
            params.update({k: str(v) for k, v in extra_params.items()})

        from urllib.parse import urlencode

        return f"{self.base_url}{path}?{urlencode(params)}"

    def merged_headers(self, *, session_cookies: Optional[str] = None) -> Dict[str, str]:
        """Return the full header set for a feed request.

        Args:
            session_cookies: harvested cookie header value (from
                :meth:`SessionPackage.to_cookie_header`). If provided,
                added as the ``cookie`` header.
        """
        h = dict(self.base_headers)
        h.update(self.extra_headers)
        if session_cookies:
            h["cookie"] = session_cookies
        return h

    def bootstrap_url(self, which: str = "home") -> str:
        """Render a bootstrap URL (home / live / line)."""
        path = self.bootstrap_paths.get(which)
        if not path:
            raise KeyError(f"bootstrap_paths[{which!r}] is missing")
        return f"{self.base_url}{path}"

    # ------------------------------------------------------------------ #
    # Validation + introspection
    # ------------------------------------------------------------------ #
    def validate(self) -> List[str]:
        """Return a list of validation errors (empty = OK)."""
        errors: List[str] = []
        if not self.name:
            errors.append("name is required")
        if not self.domain:
            errors.append("domain is required")
        if not (0 < self.partner):
            errors.append("partner must be positive")
        if not (0 < self.gr):
            errors.append("gr must be positive")
        if not (0 < self.country):
            errors.append("country must be positive")
        if not self.base_url.startswith("https://"):
            errors.append("base_url must be https://")
        if not self.feed_paths:
            errors.append("feed_paths cannot be empty")
        if not self.base_headers:
            errors.append("base_headers cannot be empty")
        return errors

    def to_dict(self, *, redact: bool = True) -> Dict[str, Any]:
        """Serialize for ``info`` output / logging. Never includes cookies."""
        return {
            "name": self.name,
            "domain": self.domain,
            "base_url": self.base_url,
            "partner": self.partner,
            "gr": self.gr,
            "country": self.country,
            "geo": self.geo,
            "language": self.language,
            "enabled": self.enabled,
            "notes": self.notes,
            "proxy_endpoint_id": self.proxy_endpoint_id,
            "allowed_countries": list(self.allowed_countries),
            "bootstrap_paths": dict(self.bootstrap_paths),
            "feed_paths": dict(self.feed_paths),
            "feed_query_params": dict(self.feed_query_params),
            "base_headers": dict(self.base_headers),
            "extra_headers": dict(self.extra_headers),
            "stealth_profile": dict(self.stealth_profile),
            "session_ttl_seconds": self.session_ttl_seconds,
            "market_groups_count": len(self.market_groups),
            "market_types_count": len(self.market_types),
            "sport_map_count": len(self.sport_map),
            "features": dict(self.features),
        }

    def with_overrides(self, **overrides: Any) -> "BetB2BSkinConfig":
        """Return a copy with the given fields overridden.

        Useful for tests and for "run this skin but with a different
        proxy endpoint" CLI flags.
        """
        return replace(self, **overrides)


# A ready-to-use default skin — linebet, the skin we reverse-engineered
# against. Operators can copy this and tweak the four identity fields.
DEFAULT_SKIN_CONFIG = BetB2BSkinConfig(
    name="linebet",
    domain="linebet.com",
    partner=189,
    gr=650,
    country=87,
    geo="KE",
    language="en",
    enabled=True,
    notes=(
        "Default skin — linebet.com. Multi-country; direct mode works out of the box. "
        "Same backend as melbet/betwinner/22bet/megapari/888starz/"
        "helabet/paripesa. See src/sites/linebet/RECON.md."
    ),
)
