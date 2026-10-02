"""Classify a response (or a rendered page) as content or a kind of block.

Signature-based and conservative: a body is only called a challenge when a
known marker is present, so ordinary 403/406 responses stay ``ACCESS_DENIED``
rather than being mislabelled. Rules are plain data so a site can add its own
(``SiteRules``) without touching code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence, Tuple

from .models import BlockType, BlockVerdict

# (vendor, regex) — matched case-insensitively against title + first ~40 KB of body.
_JS_CHALLENGE: Sequence[Tuple[str, str]] = (
    ("gcore", r"browser validation"),
    ("gcore", r"<title>\s*gcore\s*</title>"),
    ("gcore", r"/sbbi/"),
    ("cloudflare", r"just a moment\.\.\."),
    ("cloudflare", r"challenge-platform"),
    ("cloudflare", r"cf-chl-"),
    ("cloudflare", r"checking your browser before accessing"),
    ("ddos-guard", r"ddos-guard"),
    ("sucuri", r"sucuri website firewall"),
    ("akamai", r"akam/\d+/"),
)
_CAPTCHA: Sequence[Tuple[str, str]] = (
    ("cloudflare", r"cf-turnstile"),
    ("datadome", r"captcha-delivery\.com|datadome"),
    ("perimeterx", r"px-captcha|_pxhd|perimeterx"),
    ("recaptcha", r"g-recaptcha|google\.com/recaptcha"),
    ("hcaptcha", r"h-captcha|hcaptcha\.com"),
)
_GEO: Sequence[str] = (
    r"not available in your (country|region)",
    r"(restricted|unavailable) in your (country|region|location)",
    r"access (is )?denied.{0,40}your (country|region)",
)
_BAN: Sequence[Tuple[str, str]] = (
    ("cloudflare", r"error code:?\s*10(15|20)|you are being rate limited|has banned you"),
    ("akamai", r"errors\.edgesuite\.net|reference #\d+\.[0-9a-f]+"),
    ("imperva", r"incapsula incident|_incapsula_resource"),
    ("generic", r"your ip (address )?(has been|is) (blocked|banned)"),
)

_AUTH_STATUSES = frozenset({401, 419, 440})
_BODY_SCAN = 40_000


@dataclass(frozen=True)
class SiteRules:
    """Per-site additions to the generic signatures.

    ``geo_url_suffixes``: final-URL endings that mean a country block
    (betb2b skins redirect to ``/en/block``). ``geo_statuses``: statuses the
    site uses for it (betb2b answers HTTP 203). ``auth_statuses`` overrides
    the generic 401/419/440 set.
    """
    geo_url_suffixes: Tuple[str, ...] = ("/block", "/blocked")
    geo_statuses: Tuple[int, ...] = ()
    auth_statuses: Tuple[int, ...] = tuple(sorted(_AUTH_STATUSES))
    extra_challenge: Tuple[Tuple[str, str], ...] = ()


DEFAULT_RULES = SiteRules()
BETB2B_RULES = SiteRules(geo_url_suffixes=("/block", "/en/block"), geo_statuses=(203,))


def _first(patterns: Sequence[Tuple[str, str]], text: str) -> Optional[Tuple[str, str]]:
    for vendor, rx in patterns:
        if re.search(rx, text, re.IGNORECASE):
            return vendor, rx
    return None


def _retry_after(headers: Mapping[str, str]) -> Optional[float]:
    raw = headers.get("retry-after")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None          # HTTP-date form: let the policy's own backoff apply


def classify(
    status: Optional[int] = None,
    url: str = "",
    headers: Optional[Mapping[str, str]] = None,
    body: str | bytes | None = None,
    title: str = "",
    rules: SiteRules = DEFAULT_RULES,
) -> BlockVerdict:
    """Return the :class:`BlockVerdict` for one response or rendered page."""
    h = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    if isinstance(body, bytes):
        body = body[:_BODY_SCAN].decode("utf-8", "replace")
    text = f"<title>{title}</title>\n{(body or '')[:_BODY_SCAN]}"
    path = re.sub(r"[?#].*$", "", url or "").rstrip("/")

    def verdict(t: BlockType, vendor: Optional[str] = None, *evidence: str, **kw) -> BlockVerdict:
        return BlockVerdict(type=t, vendor=vendor, status=status, url=url,
                            evidence=list(evidence), **kw)

    # Country block first: it is the only layer a browser change cannot fix,
    # and a geo page often *also* carries challenge markup.
    if status in rules.geo_statuses:
        return verdict(BlockType.GEO_BLOCK, None, f"status {status} is this site's geo status")
    for suffix in rules.geo_url_suffixes:
        if path.endswith(suffix):
            return verdict(BlockType.GEO_BLOCK, None, f"redirected to {suffix}")
    if status == 451:
        return verdict(BlockType.GEO_BLOCK, None, "HTTP 451")
    for rx in _GEO:
        if re.search(rx, text, re.IGNORECASE):
            return verdict(BlockType.GEO_BLOCK, None, f"body matches /{rx}/")

    # Vendor challenge markup / headers.
    if h.get("cf-mitigated", "").lower() == "challenge":
        return verdict(BlockType.JS_CHALLENGE, "cloudflare", "cf-mitigated: challenge")
    if hit := _first(tuple(_CAPTCHA), text):
        return verdict(BlockType.CAPTCHA, hit[0], f"body matches /{hit[1]}/")
    if hit := _first(tuple(_JS_CHALLENGE) + rules.extra_challenge, text):
        return verdict(BlockType.JS_CHALLENGE, hit[0], f"body matches /{hit[1]}/")
    if hit := _first(_BAN, text):
        return verdict(BlockType.IP_BANNED, hit[0], f"body matches /{hit[1]}/")

    # Status-only signals.
    if status == 429 or (status == 503 and "retry-after" in h):
        return verdict(BlockType.RATE_LIMITED, None, f"HTTP {status}",
                       retry_after=_retry_after(h))
    if status in rules.auth_statuses:
        return verdict(BlockType.AUTH_EXPIRED, None, f"HTTP {status}")
    if status in (403, 406):
        return verdict(BlockType.ACCESS_DENIED, None, f"HTTP {status}, no vendor signature")

    return verdict(BlockType.OK)
