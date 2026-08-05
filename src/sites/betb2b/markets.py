"""BetB2B / 1xbet market-id lookup tables.

The 1xbet terse-key feed encodes markets with two integer keys:

* ``G`` — the market *group* (1 = 1x2, 2 = handicap, 17 = totals, …).
* ``T`` — the market *type* within a group (more granular — e.g.
  ``T=1`` is "W1" inside group 1, ``T=2`` is "X" inside group 1, …).

These tables map those ids to human-readable names so the extractor can
emit ``Market(name="Match Result 1x2")`` instead of
``Market(name="G=1 T=1")``. The values are the 1xbet-family constants
(partial — extended as we observe more ``T`` ids in live captures).

Per-skin YAML can extend/override these via the ``market_groups`` and
``market_types`` keys on the skin config.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class MarketGroup:
    """One ``G`` group: a coarse market family."""

    g_id: int
    name: str
    """Canonical name e.g. ``'1x2'``, ``'handicap'``, ``'totals'``."""


@dataclass(frozen=True)
class MarketTypeMap:
    """One ``T`` type within a group: a specific outcome line.

    The ``selection_label`` is what gets stamped on the
    :class:`~src.sites.betb2b.extraction.models.Selection.name` —
    e.g. ``'1'``, ``'X'``, ``'2'``, ``'Over'``, ``'Under'``,
    ``'W1 (+1.5)'`` (the ``P`` line is appended at extraction time).
    """

    t_id: int
    group: int
    market_name: str
    """Market display name, e.g. ``'Match Result 1x2'``, ``'Asian Handicap'``."""
    selection_label: str
    """Outcome label, e.g. ``'1'``, ``'X'``, ``'Over'``, ``'W1'``."""


# ---------------------------------------------------------------------------
# ``G`` groups — coarse market families
# ---------------------------------------------------------------------------
# Sourced from 1xbet-family captures + the linebet RECON. Extend as more
# groups are observed live.
DEFAULT_MARKET_GROUPS: Dict[int, MarketGroup] = {
    g.g_id: g
    for g in [
        MarketGroup(1, "1x2"),                # W1 / X / W2 (match result)
        MarketGroup(2, "handicap"),           # Asian handicap
        MarketGroup(3, "total"),              # Over/Under (totals)
        MarketGroup(4, "individual_total"),   # team totals
        MarketGroup(5, "correct_score"),
        MarketGroup(6, "double_chance"),      # 1X / 12 / X2
        MarketGroup(7, "ht_ft"),              # half-time / full-time
        MarketGroup(8, "odd_even"),
        MarketGroup(9, "both_teams_to_score"),
        MarketGroup(10, "next_goal"),
        MarketGroup(11, "exact_goals"),
        MarketGroup(12, "winner"),            # outright winner (2-way)
        MarketGroup(17, "totals"),            # alt totals group id seen live
        MarketGroup(101, "moneyline_3way"),   # 1x2 variant seen in live capture
        MarketGroup(102, "moneyline_2way"),
    ]
}


# ---------------------------------------------------------------------------
# ``T`` types — fine-grained outcomes within a group
# ---------------------------------------------------------------------------
# Common 1x2 outcomes (group 1 / 101):
_T_1X2 = [
    MarketTypeMap(1, 1, "Match Result 1x2", "1"),       # W1 (home)
    MarketTypeMap(2, 1, "Match Result 1x2", "X"),       # Draw
    MarketTypeMap(3, 1, "Match Result 1x2", "2"),       # W2 (away)
]

# Handicap (group 2):
_T_HANDICAP = [
    MarketTypeMap(4, 2, "Asian Handicap", "W1"),   # home +line
    MarketTypeMap(5, 2, "Asian Handicap", "W2"),   # away +line
    MarketTypeMap(7, 2, "Asian Handicap", "W1"),   # variant seen live (T=7 P=+7.5)
    MarketTypeMap(8, 2, "Asian Handicap", "W2"),   # variant seen live (T=8 P=-7.5)
]

# Totals (group 3 / 17):
_T_TOTALS = [
    MarketTypeMap(9, 3, "Total Over/Under", "Over"),
    MarketTypeMap(10, 3, "Total Over/Under", "Under"),
    MarketTypeMap(11, 17, "Total Over/Under", "Over"),
    MarketTypeMap(12, 17, "Total Over/Under", "Under"),
]

# Double chance (group 6):
_T_DOUBLE_CHANCE = [
    MarketTypeMap(13, 6, "Double Chance", "1X"),
    MarketTypeMap(14, 6, "Double Chance", "12"),
    MarketTypeMap(15, 6, "Double Chance", "X2"),
]

# Both teams to score (group 9):
_T_BTTS = [
    MarketTypeMap(16, 9, "Both Teams To Score", "Yes"),
    MarketTypeMap(17, 9, "Both Teams To Score", "No"),
]

# Odd/Even (group 8):
_T_ODD_EVEN = [
    MarketTypeMap(18, 8, "Odd/Even", "Odd"),
    MarketTypeMap(19, 8, "Odd/Even", "Even"),
]

# Moneyline 3-way (group 101) — seen in linebet live capture (T=401/402):
_T_MONEYLINE_3WAY = [
    MarketTypeMap(401, 101, "Moneyline 3-way", "1"),
    MarketTypeMap(402, 101, "Moneyline 3-way", "2"),
    MarketTypeMap(403, 101, "Moneyline 3-way", "X"),
]

# Moneyline 2-way (group 102) — for sports with no draw (basketball, tennis):
_T_MONEYLINE_2WAY = [
    MarketTypeMap(501, 102, "Moneyline 2-way", "1"),
    MarketTypeMap(502, 102, "Moneyline 2-way", "2"),
]

DEFAULT_MARKET_TYPES: Dict[int, MarketTypeMap] = {
    m.t_id: m
    for m in (
        _T_1X2
        + _T_HANDICAP
        + _T_TOTALS
        + _T_DOUBLE_CHANCE
        + _T_BTTS
        + _T_ODD_EVEN
        + _T_MONEYLINE_3WAY
        + _T_MONEYLINE_2WAY
    )
}


# ---------------------------------------------------------------------------
# (G, T) → (market_name, selection) — VERIFIED against a real PBA game
# (GetGameZip id=352961836, ADR-7 verified mapping). (G,T) is stable across
# every scope; the scope comes from which (sub-)game the market is in. This
# map takes precedence over the T-only table (which mislabels total variants
# across sports — e.g. T=13/14 is the AWAY individual total in basketball,
# not "Double Chance").
# ---------------------------------------------------------------------------
DEFAULT_MARKET_GT: Dict["tuple[int, int]", "tuple[str, str]"] = {
    # Combined total (both teams)
    (17, 9): ("Total", "Over"),
    (17, 10): ("Total", "Under"),
    # Individual totals — HOME (team 1) / AWAY (team 2)
    (15, 11): ("Individual Total Home", "Over"),
    (15, 12): ("Individual Total Home", "Under"),
    (62, 13): ("Individual Total Away", "Over"),
    (62, 14): ("Individual Total Away", "Under"),
    # Asian handicap
    (2, 7): ("Asian Handicap", "W1"),
    (2, 8): ("Asian Handicap", "W2"),
    # NOTE (2026-08-05, ADR-19): (14,182/183) is NOT "To Win Match" — the SPA
    # names GS=22 "Total Even" and the odds confirm Even/Odd (see DEFAULT_MARKET_GST
    # note). Removed; resolves via the GS name table instead.
    # 1x2 (3-way, seen in sub-games)
    (1, 1): ("Match Result 1x2", "1"),
    (1, 2): ("Match Result 1x2", "X"),
    (1, 3): ("Match Result 1x2", "2"),
    # Moneyline 3-way
    (101, 401): ("Moneyline 3-way", "1"),
    (101, 402): ("Moneyline 3-way", "2"),
    (101, 403): ("Moneyline 3-way", "X"),
}


# ---------------------------------------------------------------------------
# (G, GS, T) → (market_name, selection) — the ADR-7 addendum's market
# identity: the T-only table mislabels total variants across sports, and the
# ``GS`` group-specifier disambiguates (G,T) pairs that repeat in different
# scopes. GS values below are CONFIRMED from real captures — the betb2b
# fixture (Brazil LDB U22, GetGameZip) and the new-builder GE[] probe of a
# Euroleague game agree on G=17→GS=4, G=2→GS=3, and the rest match the
# ADR-7 verified mapping table (PBA game). GS is stable across builder
# variants (old E[] and new GE[]). Unknown (G,GS,T) triples fall through to
# the (G,T) map and then the honest G=<n> fallback — never guess.
# ---------------------------------------------------------------------------
DEFAULT_MARKET_GST: Dict["tuple[int, int, int]", "tuple[str, str]"] = {
    # Combined total (both teams) — G=17 GS=4
    (17, 4, 9): ("Total", "Over"),
    (17, 4, 10): ("Total", "Under"),
    # Individual total — HOME (team 1) — G=15 GS=5
    (15, 5, 11): ("Individual Total Home", "Over"),
    (15, 5, 12): ("Individual Total Home", "Under"),
    # Individual total — AWAY (team 2) — G=62 GS=6
    (62, 6, 13): ("Individual Total Away", "Over"),
    (62, 6, 14): ("Individual Total Away", "Under"),
    # Asian handicap — G=2 GS=3
    (2, 3, 7): ("Asian Handicap", "W1"),
    (2, 3, 8): ("Asian Handicap", "W2"),
    # NOTE (2026-08-05, ADR-19): the earlier (14,22,182/183) → "To Win Match"
    # rows were WRONG. The SPA's own naming table (bets_model, keyed by GS)
    # resolves GS=22 → "Total Even", and the fixture confirms it (T=182/183
    # odds 1.84/1.82, NO line, symmetric → an Even/Odd market, not a moneyline).
    # Removed so G=14/GS=22 falls through to the authoritative GS name table.
    # Moneyline 3-way — G=101 GS=38
    (101, 38, 401): ("Moneyline 3-way", "1"),
    (101, 38, 402): ("Moneyline 3-way", "2"),
    (101, 38, 403): ("Moneyline 3-way", "X"),
}


# ---------------------------------------------------------------------------
# GS → market-group name — the SPA's authoritative naming table (ADR-19).
# The 1xbet-family SPA composes group names client-side via
# ``name = groupNames[GS]`` where ``GS`` is the feed's *groupShortId*. That
# ``groupNames`` table is the union of the per-template bet-model files served
# at ``traincdn/genfiles/cms/betstemplates/bets_model_short_en_<0..77>.json``;
# indexed by GS the space is globally unique (~5.4k entries, 0 conflicts). This
# is what turns the exotic ``G=<n>`` fallbacks into real names — the whole
# group space, not just the hand-verified core. Regenerate with
# ``python -m src.sites.betb2b.scripts.fetch_market_names``.
# ---------------------------------------------------------------------------
_GROUP_NAMES_FILE = Path(__file__).with_name("data") / "market_group_names_en.json"


def _load_group_names() -> Dict[int, str]:
    try:
        raw = json.loads(_GROUP_NAMES_FILE.read_text(encoding="utf-8"))
        return {int(k): v for k, v in raw.items() if isinstance(v, str) and v.strip()}
    except (OSError, ValueError):
        return {}


DEFAULT_MARKET_GROUP_NAMES: Dict[int, str] = _load_group_names()


def lookup_market(
    g_id: int,
    t_id: int,
    market_groups: Dict[int, MarketGroup],
    market_types: Dict[int, MarketTypeMap],
    gs_id: Optional[int] = None,
    market_group_names: Optional[Dict[int, str]] = None,
) -> "tuple[str | None, str | None]":
    """Look up a market's (market_name, selection_label) from ``G`` + ``T``
    (and ``GS`` when the feed carries it).

    Market-name order: verified (G,GS,T) map → verified (G,T) map → the
    authoritative **GS → name** table (ADR-19; names every group the feed can
    carry) → T-only market name → G-only group name → ``f"G={g_id}"``.
    Selection label: the T-only table's label → ``f"T={t_id}"``. The verified
    maps take precedence because they carry a *confirmed selection side*
    (Over/Under, W1/W2) the GS table doesn't. ``gs_id`` is optional for
    backward compatibility (list feeds / older callers). ``market_group_names``
    defaults to the shipped GS table.
    """
    # 1. Verified maps — confirmed (name, selection side) for core markets.
    if gs_id is not None:
        gst = DEFAULT_MARKET_GST.get((g_id, gs_id, t_id))
        if gst is not None:
            return gst
    gt = DEFAULT_MARKET_GT.get((g_id, t_id))
    if gt is not None:
        return gt

    # 2. Resolve the group NAME and the SELECTION label independently.
    mt = market_types.get(t_id)
    selection = mt.selection_label if mt is not None else f"T={t_id}"

    names = market_group_names if market_group_names is not None else DEFAULT_MARKET_GROUP_NAMES
    name: Optional[str] = None
    if gs_id is not None:
        name = names.get(gs_id)          # authoritative SPA group name
    if name is None and mt is not None:
        name = mt.market_name            # T-only table (sport-ambiguous, last resort)
    if name is None:
        mg = market_groups.get(g_id)
        if mg is not None:
            name = mg.name.capitalize()
    if name is None:
        name = f"G={g_id}"
    return name, selection
