"""Website security package: detect, classify and respond to blockages.

* :mod:`detector` — response/page → :class:`BlockVerdict` (geo, JS challenge,
  CAPTCHA, rate limit, ban, access denied, auth expired).
* :mod:`policy`   — per-type action ladders (wait → stronger browser → human →
  failover → cooldown).
* :mod:`ledger`   — persisted per-site cooldowns / escalation tier.
* :mod:`tiers`    — browser tiers (bundled Chromium → real Chrome → headed).
* :mod:`resolver` — wait out a JS challenge; human handoff.
* :mod:`guard`    — :class:`SecurityGuard`, the object scrapers use.

Browser identity that survives between runs lives in
:mod:`src.browser.profiles`.
"""

from .detector import BETB2B_RULES, DEFAULT_RULES, SiteRules, classify
from .guard import SecurityGuard
from .ledger import BlockLedger
from .pacer import Pacer
from .models import Action, BlockType, BlockVerdict, Decision, SiteBlocked, SiteInCooldown
from .policy import BlockPolicy
from .tiers import ALL_TIERS, BrowserTier, available_tiers

__all__ = [
    "SecurityGuard", "Pacer", "BlockLedger", "BlockPolicy", "SiteRules", "classify",
    "BETB2B_RULES", "DEFAULT_RULES", "BlockType", "BlockVerdict", "Action", "Decision",
    "SiteBlocked", "SiteInCooldown", "BrowserTier", "ALL_TIERS", "available_tiers",
]
