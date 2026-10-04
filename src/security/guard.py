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

import dataclasses
import logging
from typing import Any, Callable, Optional

from . import egress, resolver
from .detector import DEFAULT_RULES, SiteRules, classify
from .evidence import EvidenceLog
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
        fail_threshold: int = 6,
        fail_cooldown: float = 300.0,
        hourly_budget: int = 0,
        evidence: Optional[EvidenceLog] = None,
    ):
        self.site = site
        self.rules = rules
        self.fail_threshold, self.fail_cooldown = fail_threshold, fail_cooldown
        self.hourly_budget = hourly_budget      # requests per hour per site; 0 = unlimited
        self.ledger = ledger or BlockLedger()
        # Evidence of every block / unreachable request, captured here because every request
        # passes through this guard (see evidence.py). Defaults to a directory beside the ledger.
        self.evidence = evidence or EvidenceLog(self.ledger.path.parent / "evidence")
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
    def _key(self, scope: Optional[str]) -> str:
        return f"{self.site}:{scope}" if scope else self.site

    def preflight(self, scope: Optional[str] = None) -> None:
        """Call before every request: raises :class:`SiteInCooldown` while the site is
        resting (after blocks, or a run of timeouts) or its hourly budget is spent.
        ``scope`` names a separate endpoint group (e.g. an optional statistics service)
        whose timeouts rest only that group, not the whole site."""
        left, last = self.ledger.cooldown_left(self.site)
        if left > 0:
            raise SiteInCooldown(self.site, left, last)
        if scope:
            left, last = self.ledger.cooldown_left(self._key(scope))
            if left > 0:
                raise SiteInCooldown(self._key(scope), left, last)
        over = self.ledger.charge(self.site, self.hourly_budget)
        if over > 0:
            raise SiteInCooldown(self.site, over, BlockType.RATE_LIMITED)

    def note_failure(self, scope: Optional[str] = None, *, error: Optional[BaseException] = None,
                     url: str = "") -> bool:
        """A request FAILED to get any answer (timeout / dropped connection). After a run
        of them the site (or just the ``scope`` endpoint group) is rested for everyone
        sharing this guard. True if that began."""
        key = self._key(scope)
        self.evidence.record("unreachable", self.site, url=url, error=error, scope=scope)
        seconds = self.ledger.record_failure(key, self.fail_threshold, self.fail_cooldown)
        if seconds:
            logger.warning("site=%s unreachable (%d failures in a row) -> resting %.0fs", key,
                           self.ledger.state(key).consecutive_failures, seconds)
        return bool(seconds)

    def note_ok(self, scope: Optional[str] = None) -> None:
        """An answer arrived for this endpoint group: its failure streak is over."""
        self.ledger.record_success(self._key(scope))

    @property
    def tier(self) -> BrowserTier:
        return tier_at(self.ledger.state(self.site).browser_tier)

    # -- classification --------------------------------------------------- #
    def inspect(self, status: Optional[int] = None, url: str = "", headers=None,
                body=None, title: str = "") -> BlockVerdict:
        verdict = classify(status, url, headers, body, title, self.rules)
        if verdict.blocked:
            self.evidence.record("block", self.site, url=url, status=status,
                                 response_headers=headers, body=body, verdict=verdict,
                                 extra={"title": title} if title else None)
        return verdict

    async def inspect_page(self, page: Any, status: Optional[int] = None) -> BlockVerdict:
        verdict = await resolver.inspect_page(page, status, self.rules)
        if verdict.blocked:
            verdict = dataclasses.replace(verdict, via_page=True)
            self.evidence.record("block", self.site, url=verdict.url, status=status,
                                 verdict=verdict, extra={"via": "browser page"})
        return verdict

    # -- decisions -------------------------------------------------------- #
    def require_page_access(self, *, via_proxy: bool, what: str = "page load") -> None:
        """Raise :class:`egress.PageLoadsRefused` if this machine must not load the site's pages
        (declared restricted, or it already saw a page-level country block without a proxy)."""
        egress.check_page_load(self.site, via_proxy=via_proxy, what=what)

    def on_block(self, verdict: BlockVerdict) -> Decision:
        """Record a block and choose the next rung. Escalation is applied here."""
        if (verdict.type is BlockType.GEO_BLOCK and verdict.via_page and "@" not in self.site):
            # A PAGE was country-blocked with no proxy: stop loading pages of this site from here.
            # The data feeds are not country-gated, so this must not rest the feed path (a
            # cooldown is per site); the restriction is a page-load marker, not a cooldown.
            egress.mark_restricted(self.site)
            decision = self.policy.decide(verdict, 1, 1)
            logger.warning("site=%s page load country-blocked without a proxy -> page loads off for "
                           "this machine (feeds unaffected); clear with `python -m src.security clear %s`",
                           self.site, self.site)
            self.evidence.record("block", self.site, url=verdict.url, status=verdict.status,
                                 verdict=verdict, extra={"note": "page loads switched off"})
            return decision
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
