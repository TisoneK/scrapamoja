"""SecurityGuard — one object a scraper asks "may I?" and "what now?".

Typical use (see ``BetB2BSessionManager``)::

    guard = SecurityGuard("linebet", rules=BETB2B_RULES)
    guard.preflight()                       # raises SiteInCooldown while cooling down
    tier = guard.tier                       # which browser to open
    ...open page, goto...
    verdict = await guard.inspect_page(page, status)
    if verdict.blocked:
        decision = guard.on_block(verdict)  # records it, picks the next rung
        # act on decision.action: wait / escalate tier / human / failover / stop
    else:
        guard.on_success()
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from . import resolver
from .detector import DEFAULT_RULES, SiteRules, classify
from .ledger import BlockLedger
from .models import Action, BlockType, BlockVerdict, Decision, SiteBlocked, SiteInCooldown
from .policy import BlockPolicy
from .tiers import BrowserTier, has_display, max_tier, tier_at

logger = logging.getLogger(__name__)


class SecurityGuard:
    def __init__(
        self,
        site: str,
        *,
        rules: SiteRules = DEFAULT_RULES,
        policy: Optional[BlockPolicy] = None,
        ledger: Optional[BlockLedger] = None,
        interactive: Optional[bool] = None,
        has_failover: bool = False,
        has_proxy_pool: bool = False,
        has_browser: bool = True,
    ):
        self.site = site
        self.rules = rules
        self.ledger = ledger or BlockLedger()
        self.interactive = resolver.interactive_allowed() if interactive is None else interactive
        self.policy = policy or BlockPolicy()
        unavailable = set(self.policy.unavailable)
        if not self.interactive or not has_display():
            unavailable.add(Action.HUMAN_HANDOFF)
        if not has_failover:
            unavailable.add(Action.FAILOVER_SITE)
        if not has_proxy_pool:
            unavailable.add(Action.ROTATE_PROXY)
        if not has_browser:
            # Direct (browser-free) mode cannot wait on a page, open a stronger browser,
            # hand a window to a person, or re-bootstrap cookies: those rungs are skipped,
            # so a block goes straight to failover or cooldown instead of being retried
            # silently a few more times.
            unavailable.update({Action.WAIT_FOR_CLEARANCE, Action.ESCALATE_BROWSER,
                                Action.HUMAN_HANDOFF, Action.REFRESH_SESSION})
        self.policy.unavailable = frozenset(unavailable)

    # -- gate ----------------------------------------------------------- #
    def preflight(self) -> None:
        left, last = self.ledger.cooldown_left(self.site)
        if left > 0:
            raise SiteInCooldown(self.site, left, last)

    @property
    def tier(self) -> BrowserTier:
        return tier_at(self.ledger.state(self.site).browser_tier)

    # -- classification --------------------------------------------------- #
    def inspect(self, status: Optional[int] = None, url: str = "", headers=None,
                body=None, title: str = "") -> BlockVerdict:
        return classify(status, url, headers, body, title, self.rules)

    async def inspect_page(self, page: Any, status: Optional[int] = None) -> BlockVerdict:
        return await resolver.inspect_page(page, status, self.rules)

    # -- decisions -------------------------------------------------------- #
    def on_block(self, verdict: BlockVerdict) -> Decision:
        """Record a block and choose the next rung. Escalation is applied here."""
        attempt = self.ledger.record_block(self.site, verdict)
        consecutive = self.ledger.state(self.site).consecutive_blocks
        decision = self.policy.decide(verdict, attempt, consecutive)
        while decision.action is Action.ESCALATE_BROWSER:
            current = self.ledger.state(self.site).browser_tier
            if current < max_tier():
                self.ledger.set_tier(self.site, current + 1)
                break
            # Nothing stronger to open here: skip to the next rung.
            attempt += 1
            decision = self.policy.decide(verdict, attempt, consecutive)
        if decision.action in (Action.COOLDOWN, Action.FAILOVER_SITE):
            self.ledger.start_cooldown(self.site, decision.cooldown_seconds)
        logger.warning("site=%s block=%s -> %s (%s)", self.site, verdict.summary(),
                       decision.action.value, decision.reason)
        return decision

    def on_success(self) -> None:
        self.ledger.record_success(self.site)

    def blocked(self, verdict: BlockVerdict, decision: Optional[Decision] = None) -> SiteBlocked:
        return SiteBlocked(self.site, verdict, decision)
