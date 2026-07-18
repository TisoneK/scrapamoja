"""Registry of per-sport scrapers.

Resolves a sport (by slug, SI id, or :class:`Sport` enum) to a
:class:`SportScraper` subclass. The default registry ships with the
family's most-trafficked sports; callers add their own via
:func:`register_sport_scraper`.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type, Union

from ..extraction.models import Sport
from .base import AllSportsScraper, SportScraper
from .basketball import BasketballScraper
from .esports import EsportsScraper
from .football import FootballScraper
from .hockey import HockeyScraper
from .tennis import TennisScraper


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
_REGISTRY: Dict[str, Type[SportScraper]] = {}
"""slug → SportScraper subclass (slug is lower-case, e.g. ``"basketball"``)."""

_REGISTRY_BY_SI: Dict[int, Type[SportScraper]] = {}
"""SI id → SportScraper subclass (e.g. ``3 → BasketballScraper``)."""

_REGISTRY_BY_ENUM: Dict[Sport, Type[SportScraper]] = {}
"""Sport enum → SportScraper subclass."""


def register_sport_scraper(scraper_cls: Type[SportScraper]) -> Type[SportScraper]:
    """Register a :class:`SportScraper` subclass.

    Idempotent — re-registering the same class overwrites the prior entry.
    Used both for the defaults (below) and for caller-supplied sports.

    Args:
        scraper_cls: the subclass to register. Must have non-zero ``sport_id``
            and a non-empty ``slug`` (unless it's the AllSportsScraper).
    """
    slug = (scraper_cls.slug or "").lower().strip()
    sid = scraper_cls.sport_id
    enum = scraper_cls.sport_enum

    if sid == 0 and slug == "":
        # The AllSportsScraper sentinel — register under the "all" slug.
        _REGISTRY["all"] = scraper_cls
        return scraper_cls

    if not slug:
        raise ValueError(
            f"SportScraper {scraper_cls.__name__} has empty slug — "
            f"cannot register (sport_id={sid})"
        )
    if sid <= 0:
        raise ValueError(
            f"SportScraper {scraper_cls.__name__} has invalid sport_id={sid}"
        )

    _REGISTRY[slug] = scraper_cls
    _REGISTRY_BY_SI[sid] = scraper_cls
    if enum is not None and enum != Sport.OTHER:
        _REGISTRY_BY_ENUM[enum] = scraper_cls
    return scraper_cls


# Register the defaults.
DEFAULT_SPORT_SCRAPERS: Dict[str, Type[SportScraper]] = {
    "all": AllSportsScraper,
    "football": FootballScraper,
    "basketball": BasketballScraper,
    "ice-hockey": HockeyScraper,
    "tennis": TennisScraper,
    "esports": EsportsScraper,
}
for _cls in DEFAULT_SPORT_SCRAPERS.values():
    register_sport_scraper(_cls)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------
def get_sport_scraper(
    *,
    slug: Optional[str] = None,
    sport_id: Optional[int] = None,
    sport_enum: Optional[Union[Sport, str]] = None,
) -> SportScraper:
    """Resolve a sport to a :class:`SportScraper` instance.

    Pass any one of ``slug``, ``sport_id``, ``sport_enum``. Falls back to
    :class:`AllSportsScraper` if nothing matches.

    Args:
        slug: URL slug (e.g. ``"basketball"``, ``"ice-hockey"``).
        sport_id: the BetB2B ``SI`` id (e.g. ``3``).
        sport_enum: a :class:`Sport` enum value or its string name
            (e.g. ``Sport.BASKETBALL`` or ``"Basketball"``).
    """
    if slug is not None:
        s = slug.lower().strip()
        cls = _REGISTRY.get(s)
        if cls is not None:
            return cls()
        # Allow "all" or empty as the AllSports sentinel.
        if s in ("", "all", "all-sports", "any"):
            return AllSportsScraper()

    if sport_id is not None:
        cls = _REGISTRY_BY_SI.get(sport_id)
        if cls is not None:
            return cls()

    if sport_enum is not None:
        if isinstance(sport_enum, str):
            try:
                sport_enum = Sport(sport_enum)
            except ValueError:
                # Try case-insensitive match.
                for se in Sport:
                    if se.value.lower() == sport_enum.lower():
                        sport_enum = se
                        break
                else:
                    return AllSportsScraper()
        cls = _REGISTRY_BY_ENUM.get(sport_enum)
        if cls is not None:
            return cls()

    return AllSportsScraper()


def resolve_sport(
    sport: Optional[Union[str, int, Sport, SportScraper]] = None,
) -> SportScraper:
    """Resolve any sport-like input to a :class:`SportScraper` instance.

    Accepts:
    - ``None`` → :class:`AllSportsScraper`
    - :class:`SportScraper` instance → returned as-is
    - :class:`SportScraper` subclass → instantiated
    - ``str`` → treated as slug (or "all"/"" for all-sports)
    - ``int`` → treated as SI id
    - :class:`Sport` enum → looked up by enum
    """
    if sport is None:
        return AllSportsScraper()
    if isinstance(sport, SportScraper):
        return sport
    if isinstance(sport, type) and issubclass(sport, SportScraper):
        return sport()
    if isinstance(sport, str):
        return get_sport_scraper(slug=sport)
    if isinstance(sport, int):
        return get_sport_scraper(sport_id=sport)
    if isinstance(sport, Sport):
        return get_sport_scraper(sport_enum=sport)
    raise TypeError(
        f"Cannot resolve sport from {sport!r} (type={type(sport).__name__})"
    )


def list_sport_slugs() -> List[str]:
    """Return all registered sport slugs (sorted)."""
    return sorted(_REGISTRY.keys())


def list_sport_scraper_summaries() -> List[Dict[str, object]]:
    """Return a list of {slug, sport_id, display_name, bootstrap_path} for each registered sport."""
    out: List[Dict[str, object]] = []
    for slug in sorted(_REGISTRY.keys()):
        cls = _REGISTRY[slug]
        instance = cls()
        out.append({
            "slug": slug,
            "sport_id": instance.sport_id,
            "display_name": instance.display_name,
            "bootstrap_path": instance.bootstrap_path,
            "live_bootstrap_path": instance.live_bootstrap_path,
            "sport_enum": instance.sport_enum.value,
            "has_draw": instance.has_draw,
            "period_name": instance.period_name,
        })
    return out


# Need Dict here for the type hint above.
from typing import Dict  # noqa: E402  (placed late to keep the public API on top)
