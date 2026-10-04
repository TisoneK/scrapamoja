"""Data types for the website-security package.

A *block* is any response that is not the content we asked for because the
site's defences intervened. Telling the kinds apart matters: a country block
is not fixed by a better browser, a JavaScript challenge is, and a rate limit
is fixed only by waiting. Treating them all as "re-bootstrap" turns one
challenge into a burst of requests that earns an IP ban.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class BlockType(str, Enum):
    OK = "ok"
    GEO_BLOCK = "geo_block"          # country/region denied — a browser change cannot fix it
    JS_CHALLENGE = "js_challenge"    # JavaScript browser-validation interstitial
    CAPTCHA = "captcha"              # interactive human check
    RATE_LIMITED = "rate_limited"    # 429 / 503 + Retry-After — only waiting helps
    IP_BANNED = "ip_banned"          # IP/ASN reputation or penalty block
    ACCESS_DENIED = "access_denied"  # bare 403/406 with no vendor signature
    AUTH_EXPIRED = "auth_expired"    # session cookies/tokens stale (401/419/440)
    UNREACHABLE = "unreachable"      # connect/read timeouts, dropped connections: the site is not answering


class Action(str, Enum):
    """One rung of a policy ladder."""
    REFRESH_SESSION = "refresh_session"          # re-bootstrap cookies once
    WAIT_FOR_CLEARANCE = "wait_for_clearance"    # stay on the page; JS challenges self-resolve
    ESCALATE_BROWSER = "escalate_browser"        # next browser tier (real Chrome, headed)
    HUMAN_HANDOFF = "human_handoff"              # operator passes the check in a headed browser
    ROTATE_PROXY = "rotate_proxy"                # different egress
    FAILOVER_SITE = "failover_site"              # serve from a sister site instead
    COOLDOWN = "cooldown"                        # stop touching this site for a while
    ABORT = "abort"


@dataclass(frozen=True)
class BlockVerdict:
    """What a response turned out to be."""
    type: BlockType
    vendor: Optional[str] = None             # gcore / cloudflare / datadome / ...
    status: Optional[int] = None
    url: str = ""
    evidence: List[str] = field(default_factory=list)
    retry_after: Optional[float] = None      # seconds, when the site told us
    via_page: bool = False                   # seen on a browser page load (not a data-feed response)

    @property
    def blocked(self) -> bool:
        return self.type is not BlockType.OK

    def summary(self) -> str:
        v = f"/{self.vendor}" if self.vendor else ""
        ev = "; ".join(self.evidence[:3])
        return f"{self.type.value}{v} (status={self.status}) {ev}".strip()


@dataclass(frozen=True)
class Decision:
    """The next move for a block, chosen by policy + history."""
    action: Action
    cooldown_seconds: float = 0.0
    reason: str = ""


class SiteBlocked(RuntimeError):
    """Raised when every rung the caller can take is exhausted."""

    def __init__(self, site: str, verdict: BlockVerdict, decision: Optional[Decision] = None):
        self.site = site
        self.verdict = verdict
        self.decision = decision
        super().__init__(f"site={site} blocked: {verdict.summary()}"
                         + (f" -> {decision.action.value}" if decision else ""))


class SiteInCooldown(RuntimeError):
    """Raised before any request when the site is cooling down after blocks."""

    def __init__(self, site: str, seconds_left: float, last: Optional[BlockType] = None):
        self.site = site
        self.seconds_left = seconds_left
        self.last = last
        super().__init__(f"site={site} in cooldown for {seconds_left:.0f}s more"
                         + (f" (last block: {last.value})" if last else ""))
