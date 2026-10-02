"""Page-level answers to a challenge: wait it out, or hand it to a person.

JavaScript browser-validation pages are written to resolve themselves in a
real browser: the injected script runs, sets a clearance cookie and redirects.
So the first and cheapest answer is patience on the same page. CAPTCHAs and
stubborn validations go to a human in a headed window; the persistent profile
keeps what they pass. No third-party solving service is involved.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Optional

from .detector import DEFAULT_RULES, SiteRules, classify
from .models import BlockType, BlockVerdict


@dataclass
class Clearance:
    cleared: bool
    verdict: BlockVerdict
    waited_s: float


async def inspect_page(page: Any, status: Optional[int] = None,
                       rules: SiteRules = DEFAULT_RULES) -> BlockVerdict:
    """Classify what a Playwright page is showing right now."""
    try:
        title = await page.title()
    except Exception:  # noqa: BLE001 — mid-navigation; treat as empty
        title = ""
    try:
        body = (await page.content())[:40_000]
    except Exception:  # noqa: BLE001
        body = ""
    return classify(status=status, url=page.url, body=body, title=title, rules=rules)


async def wait_for_clearance(page: Any, *, timeout_s: float = 30.0, poll_s: float = 1.5,
                             rules: SiteRules = DEFAULT_RULES) -> Clearance:
    """Poll the page until it stops showing a challenge (or the time runs out).

    A geo block never clears by waiting, so it returns immediately.
    """
    start = time.monotonic()
    verdict = await inspect_page(page, rules=rules)
    while verdict.blocked and verdict.type in (BlockType.JS_CHALLENGE, BlockType.CAPTCHA):
        if verdict.type is BlockType.CAPTCHA or time.monotonic() - start >= timeout_s:
            break
        await asyncio.sleep(poll_s)
        verdict = await inspect_page(page, rules=rules)
    return Clearance(not verdict.blocked, verdict, time.monotonic() - start)


def interactive_allowed() -> bool:
    """A human can be asked only when someone is at the keyboard."""
    flag = os.environ.get("SCRAPAMOJA_INTERACTIVE")
    if flag is not None:
        return flag.strip().lower() in ("1", "true", "yes", "on")
    return sys.stdin.isatty() and sys.stdout.isatty()


async def human_handoff(page: Any, *, site: str, timeout_s: float = 600.0,
                        rules: SiteRules = DEFAULT_RULES) -> Clearance:
    """Ask the operator to pass the check in the open (headed) window."""
    print(f"\n[security] {site}: a check needs a human. Complete it in the open browser window "
          f"(waiting up to {timeout_s:.0f}s)...", file=sys.stderr, flush=True)
    start = time.monotonic()
    verdict = await inspect_page(page, rules=rules)
    while verdict.blocked and time.monotonic() - start < timeout_s:
        await asyncio.sleep(2.0)
        verdict = await inspect_page(page, rules=rules)
    return Clearance(not verdict.blocked, verdict, time.monotonic() - start)
