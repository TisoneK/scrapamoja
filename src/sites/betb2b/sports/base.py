"""Sport-scraper base class — one sport's customization of the BetB2B scraper.

The BetB2B backend (1xbet family) tags every event with an integer ``SI``
sport id (1=Football, 3=Basketball, 4=Tennis, …). Per-sport differences
worth modeling:

* **URL slug.** ``/en/line/basketball`` vs ``/en/line/football``. The browser
  bootstrap navigates here so the SPA loads the right championship tree and
  the service worker injects the correct per-sport cookies.
* **Feed query param.** The ``/service-api/{Line,Live}Feed/Get1x2_VZip``
  endpoint accepts ``sports=<SI>`` to filter the feed to one sport. The
  per-sport scraper exposes this as ``feed_extra_params``.
* **Market-group name overrides.** ``G=1`` is "1x2" (home/draw/away) on
  football but "To Win Match" (home/away, no draw) on basketball. ``G=17``
  is "Total Goals" on football but "Total Points" on basketball. Each
  sport can ship its own ``market_group_overrides`` that merge on top of
  :data:`src.sites.betb2b.markets.DEFAULT_MARKET_GROUPS`.
* **DOM selectors.** The drift-tolerance DOM fallback extractor uses
  broad 1xbet-grid selectors by default, but sports with unusual layouts
  (e.g. esports with its separate `/esports` SPA) can override them.
* **Event enrichment.** A sport can implement :meth:`enrich_event` to
  add derived fields (e.g. basketball period → quarter number, tennis
  period → set number).

The :class:`SportScraper` is intentionally NOT a scraper in its own right
— it's a *strategy* object that the :class:`BetB2BScraper` consults.
This keeps the scraper composition root single and the per-sport code
trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ..extraction.models import Event, Market, MarketType, Sport


# ---------------------------------------------------------------------------
# DOM selector bundle — what the fallback extractor walks
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DOMSelectors:
    """CSS selector bundle for the BetB2B grid DOM extractor.

    Defaults match the 1xbet/BetB2B Vue grid shipped on linebet/melbet/betwinner.
    Override per-sport if a skin's SPA churns class names for one sport.
    """

    # Championship / league container that groups games under a header.
    # We walk these so each game knows its competition name.
    championship: str = ".dashboard-champ"

    # The championship-name label inside a championship container.
    championship_name: str = ".dashboard-champ-name__label"

    # One event/game row inside a championship container.
    game: str = ".dashboard-champ__game"

    # Team-name elements inside a game row. We expect exactly 2 (home + away).
    # Multiple selectors are tried in order; first non-empty match per slot wins.
    team_names: Tuple[str, ...] = (
        ".dashboard-game-block__team",
        ".dashboard-game-team-info__name",
        ".ui-team-score-name",
    )

    # Live-score elements. Optional — prematch games have none.
    # The in-play grid renders the running total as two adjacent
    # ``.ui-game-scores__num`` spans inside ``.ui-game-scores__item--total``
    # (home first, away second); per-quarter items follow. Targeting the
    # ``--total`` pair keeps us off the period scores. The legacy selectors
    # remain as fallbacks for older/other skins.
    team_scores: Tuple[str, ...] = (
        ".ui-game-scores__item--total .ui-game-scores__num",
        ".ui-team-scores__scores",
        ".dashboard-game-block__score",
    )

    # Odds/coefficient cells. Each cell is one selection (e.g. home / draw / away).
    odds: Tuple[str, ...] = (
        ".c-bets__bet",
        ".coupon-loading-component__coef",
        '[class*="bet"] [class*="coef"]',
    )

    # Live indicator: a class on the game row whose presence means "live".
    live_class_pattern: str = "is-live"

    # Time / start-time cell inside a game row (optional).
    start_time: Tuple[str, ...] = (
        ".dashboard-game-date",
        ".dashboard-champ-date",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "championship": self.championship,
            "championship_name": self.championship_name,
            "game": self.game,
            "team_names": list(self.team_names),
            "team_scores": list(self.team_scores),
            "odds": list(self.odds),
            "live_class_pattern": self.live_class_pattern,
            "start_time": list(self.start_time),
        }


# ---------------------------------------------------------------------------
# Market-group override — sport-specific market name/label hints
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MarketGroupOverride:
    """Override a ``G`` (market group) name for one sport.

    The BetB2B ``G`` id is family-shared, but the *display name* differs per
    sport. ``G=1`` is "1x2" on football (3-way) but "To Win Match" on
    basketball (2-way, no draw). This override lets each sport ship its own
    labels without touching the shared :data:`DEFAULT_MARKET_GROUPS`.
    """

    g_id: int
    name: str
    """Display name e.g. ``'To Win Match'``."""
    market_type: Optional[MarketType] = None
    """Optional MarketType override (e.g. MONEYLINE_H2H for 2-way basketball)."""


# ---------------------------------------------------------------------------
# SportScraper — the strategy object
# ---------------------------------------------------------------------------
class SportScraper:
    """Per-sport customization of the BetB2B scraper.

    Subclass and override the class attributes + any methods you need. The
    minimum customization is :attr:`sport_id`, :attr:`slug`, and
    :attr:`sport_enum`.

    The instance is stateless (no I/O) — safe to share across coroutines.
    """

    # ----- identity (override in subclasses) -----
    sport_id: int = 0
    """The BetB2B ``SI`` sport id (1=Football, 3=Basketball, …)."""

    slug: str = ""
    """URL slug for the line page: ``/en/line/<slug>``. Empty = all sports."""

    live_slug: str = ""
    """URL slug for the live page: ``/en/live/<slug>``. Empty = top-level live."""

    sport_enum: Sport = Sport.OTHER
    """The :class:`Sport` enum value events should be tagged with."""

    display_name: str = "Other"
    """Human-readable name for logs and CLI output."""

    # ----- behavior flags -----
    has_draw: bool = True
    """Whether the sport's main market is 3-way (1X2) or 2-way (H2H)."""

    period_name: str = "period"
    """Label for periods: 'half' (football), 'quarter' (basketball), 'set' (tennis)."""

    periods_count: Optional[int] = None
    """Number of periods in regulation, if known. None = no assumption."""

    # ----- customization points -----
    dom_selectors: DOMSelectors = DOMSelectors()
    """CSS selectors for the drift-tolerance DOM extractor."""

    market_group_overrides: List[MarketGroupOverride] = []
    """Per-sport market-group name overrides (merged on top of DEFAULT_MARKET_GROUPS)."""

    # ------------------------------------------------------------------ #
    # Computed properties
    # ------------------------------------------------------------------ #
    @property
    def bootstrap_path(self) -> str:
        """The path under the skin's base_url to bootstrap against for line."""
        if not self.slug:
            return "/en/line"
        return f"/en/line/{self.slug}"

    @property
    def live_bootstrap_path(self) -> str:
        """The path under the skin's base_url to bootstrap against for live."""
        if not self.live_slug and not self.slug:
            return "/en/live"
        return f"/en/live/{self.live_slug or self.slug}"

    def feed_extra_params(self, *, count: Optional[int] = None) -> Dict[str, str]:
        """Query params to add to feed requests for this sport.

        Returns the ``sports=<SI>`` filter plus an optional ``count=`` cap.
        Merged on top of the skin's :attr:`feed_query_params`.
        """
        params: Dict[str, str] = {"sports": str(self.sport_id)}
        if count is not None:
            params["count"] = str(count)
        return params

    def merged_market_group_overrides(self) -> Dict[int, MarketGroupOverride]:
        """Return the overrides as a dict keyed by ``G`` id."""
        return {o.g_id: o for o in self.market_group_overrides}

    # ------------------------------------------------------------------ #
    # Hooks — sport-specific enrichment (override in subclasses)
    # ------------------------------------------------------------------ #
    def enrich_event(self, event: Event) -> Event:
        """Hook to add sport-specific derived fields to an extracted event.

        Default: no-op. Subclasses can override to e.g. compute a basketball
        quarter number from ``event.period``, or map tennis set names.
        """
        return event

    def label_market(self, market: Market) -> str:
        """Return a display label for a market, applying sport overrides.

        Default: return the market's existing name.
        """
        if market.raw_g is not None:
            override = self.market_group_overrides_dict.get(market.raw_g)
            if override is not None:
                return override.name
        return market.name

    @property
    def market_group_overrides_dict(self) -> Dict[int, MarketGroupOverride]:
        """Cached dict view of :attr:`market_group_overrides`."""
        # Lazy-cached on the class to avoid recomputing per call.
        cache_attr = "_mgo_cache"
        cached = getattr(self, cache_attr, None)
        if cached is None:
            cached = self.merged_market_group_overrides()
            object.__setattr__(self, cache_attr, cached)
        return cached

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sport_id": self.sport_id,
            "slug": self.slug,
            "live_slug": self.live_slug,
            "bootstrap_path": self.bootstrap_path,
            "live_bootstrap_path": self.live_bootstrap_path,
            "sport_enum": self.sport_enum.value,
            "display_name": self.display_name,
            "has_draw": self.has_draw,
            "period_name": self.period_name,
            "periods_count": self.periods_count,
            "dom_selectors": self.dom_selectors.to_dict(),
            "market_group_overrides_count": len(self.market_group_overrides),
            "feed_extra_params": self.feed_extra_params(),
        }


# ---------------------------------------------------------------------------
# SportScraperContext — what the BetB2BScraper builds from a SportScraper
# ---------------------------------------------------------------------------
@dataclass
class SportScraperContext:
    """Bundle of resolved sport-scraper values consumed by BetB2BScraper.

    Built once per scrape from a :class:`SportScraper` instance and frozen
    for the scrape lifetime. The scraper reads from this instead of the
    SportScraper directly to keep the per-call surface tiny.
    """

    sport_scraper: SportScraper
    sport_id: int
    slug: str
    bootstrap_path: str
    live_bootstrap_path: str
    sport_enum: Sport
    feed_extra_params: Dict[str, str] = field(default_factory=dict)
    dom_selectors: DOMSelectors = field(default_factory=DOMSelectors)
    market_group_overrides: Dict[int, MarketGroupOverride] = field(default_factory=dict)

    @classmethod
    def from_sport_scraper(cls, sport_scraper: SportScraper) -> "SportScraperContext":
        return cls(
            sport_scraper=sport_scraper,
            sport_id=sport_scraper.sport_id,
            slug=sport_scraper.slug,
            bootstrap_path=sport_scraper.bootstrap_path,
            live_bootstrap_path=sport_scraper.live_bootstrap_path,
            sport_enum=sport_scraper.sport_enum,
            feed_extra_params=sport_scraper.feed_extra_params(),
            dom_selectors=sport_scraper.dom_selectors,
            market_group_overrides=sport_scraper.market_group_overrides_dict,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sport_id": self.sport_id,
            "slug": self.slug,
            "bootstrap_path": self.bootstrap_path,
            "live_bootstrap_path": self.live_bootstrap_path,
            "sport_enum": self.sport_enum.value,
            "feed_extra_params": dict(self.feed_extra_params),
            "dom_selectors": self.dom_selectors.to_dict(),
            "market_group_overrides": {
                str(g): {"name": o.name, "market_type": o.market_type.value if o.market_type else None}
                for g, o in self.market_group_overrides.items()
            },
        }


# ---------------------------------------------------------------------------
# Default "all sports" scraper — used when no sport is specified
# ---------------------------------------------------------------------------
class AllSportsScraper(SportScraper):
    """The "no sport filter" scraper — bootstraps against /en/line (no slug).

    Used when the caller wants the top games across all sports (the BetB2B
    feed's default behaviour when no ``sports=`` param is supplied).
    """

    sport_id = 0  # 0 = "no sport filter" — feed ignores sports= param
    slug = ""
    live_slug = ""
    sport_enum = Sport.OTHER
    display_name = "All Sports"
    has_draw = True
    period_name = "period"
    periods_count = None
