"""HAR exporter — record a browser session as a HAR file.

This is the **production** solution to WAF blocks (Cloudflare, nginx
edge blocks, datacenter-IP fingerprinting). The sandbox / datacenter
IPs are blocked, but a residential IP is not. The workflow is:

  1. Operator (with a residential IP) runs this exporter. It launches a
     real Playwright browser, navigates through the target site, and
     exports the full network trace as a HAR file (response bodies
     included).
  2. Operator ships the HAR file to the developer (or commits it to the
     repo under ``<site>/snapshots/raw/``).
  3. Developer runs ``python -m src.network.har.replay <input.har>
     <output.json>`` to extract events from the HAR — no live browser
     needed.

This module is **site-agnostic**. Site-specific configuration (entry
URL, scroll behaviour, headed mode, etc.) is passed as constructor
arguments to :class:`HarExporter` or as CLI flags.

Public API:

    from src.network.har import HarExporter, export_har

CLI:

    python -m src.network.har.export --url https://example.com --output my.har
    python -m src.network.har.export --url https://example.com --headed --live
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_VIEWPORT = {"width": 1536, "height": 864}
DEFAULT_LOCALE = "en-US"
DEFAULT_TIMEZONE = "Europe/London"
DEFAULT_SCROLL_COUNT = 5
DEFAULT_SETTLE_SECONDS = 15.0
DEFAULT_NAV_TIMEOUT_MS = 60000


@dataclass
class HarExporterConfig:
    """Configuration for :class:`HarExporter`.

    All fields have sensible defaults; only ``url`` and ``output`` are
    required for typical use.
    """
    url: str = "https://example.com/"
    output: Path = field(default_factory=lambda: Path("session.har"))
    live_url: Optional[str] = None        # if set, also visit this URL after the main one
    scroll_count: int = DEFAULT_SCROLL_COUNT
    settle_seconds: float = DEFAULT_SETTLE_SECONDS
    headless: bool = True
    nav_timeout_ms: int = DEFAULT_NAV_TIMEOUT_MS
    user_agent: str = DEFAULT_USER_AGENT
    viewport: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_VIEWPORT))
    locale: str = DEFAULT_LOCALE
    timezone: str = DEFAULT_TIMEZONE
    extra_http_headers: Dict[str, str] = field(default_factory=dict)


class HarExporter:
    """Record a Playwright browser session as a HAR file.

    Usage::

        exporter = HarExporter(HarExporterConfig(
            url="https://linebet.com/en",
            output=Path("linebet.har"),
            live_url="https://linebet.com/en/live",
        ))
        await exporter.run()
    """

    def __init__(self, config: HarExporterConfig) -> None:
        self.config = config
        if not self.config.output.is_absolute():
            # Resolve relative to cwd — caller can override.
            self.config.output = Path.cwd() / self.config.output

    async def run(self) -> Dict[str, Any]:
        """Run the export. Returns a summary dict.

        The summary includes the HAR file path, its size in bytes, and
        any WAF/block signals detected during the run.
        """
        cfg = self.config
        cfg.output.parent.mkdir(parents=True, exist_ok=True)

        summary: Dict[str, Any] = {
            "url": cfg.url,
            "output": str(cfg.output),
            "live_url": cfg.live_url,
            "headless": cfg.headless,
            "waf_block_detected": False,
        }

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=cfg.headless)
            context = await browser.new_context(
                user_agent=cfg.user_agent,
                viewport=cfg.viewport,
                locale=cfg.locale,
                timezone_id=cfg.timezone,
                record_har_path=str(cfg.output),
                record_har_content="embed",  # include response bodies in the HAR
                **({"extra_http_headers": cfg.extra_http_headers}
                   if cfg.extra_http_headers else {}),
            )
            page = await context.new_page()

            try:
                summary["home"] = await self._navigate_and_scroll(page, cfg.url, cfg)
                if summary["home"].get("waf_block"):
                    summary["waf_block_detected"] = True

                if cfg.live_url:
                    summary["live"] = await self._navigate_and_scroll(page, cfg.live_url, cfg)
                    if summary["live"].get("waf_block"):
                        summary["waf_block_detected"] = True
            finally:
                await context.close()  # flushes HAR to disk
                await browser.close()

        summary["har_bytes"] = cfg.output.stat().st_size if cfg.output.exists() else 0
        return summary

    async def _navigate_and_scroll(
        self, page: Any, url: str, cfg: HarExporterConfig,
    ) -> Dict[str, Any]:
        """Navigate to ``url``, scroll, wait for settle. Returns page-state info."""
        result: Dict[str, Any] = {"url": url}
        try:
            resp = await page.goto(
                url, wait_until="domcontentloaded", timeout=cfg.nav_timeout_ms,
            )
            result["status"] = resp.status if resp else None
            result["final_url"] = page.url
            # WAF-block heuristic: HTTP 203, /block path, or "blocked" in title
            title = await page.title()
            result["title"] = title
            result["waf_block"] = (
                (resp.status == 203 if resp else False)
                or page.url.endswith("/block")
                or "blocked" in title.lower()
            )
        except Exception as exc:
            result["error"] = str(exc)
            result["waf_block"] = False
            return result

        # Scroll to trigger lazy-loaded content
        for i in range(cfg.scroll_count):
            try:
                await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                await asyncio.sleep(1.5)
            except Exception:
                # Page may have navigated/closed mid-scroll; tolerate.
                break

        # Wait for the SPA's API burst to settle
        await asyncio.sleep(cfg.settle_seconds)
        return result


async def export_har(config: HarExporterConfig) -> Dict[str, Any]:
    """Convenience function: create an exporter and run it.

    Equivalent to::

        exporter = HarExporter(config)
        return await exporter.run()
    """
    return await HarExporter(config).run()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record a Playwright browser session as a HAR file. "
            "Use this from a residential IP when the sandbox is WAF-blocked."
        ),
    )
    parser.add_argument("--url", required=True, help="Entry URL")
    parser.add_argument("--output", type=Path, default=Path("session.har"),
                        help="Where to write the HAR file (default: session.har)")
    parser.add_argument("--live", type=str, default=None,
                        help="Optional second URL to visit (e.g. /live page)")
    parser.add_argument("--scroll", type=int, default=DEFAULT_SCROLL_COUNT,
                        help=f"Number of times to scroll (default: {DEFAULT_SCROLL_COUNT})")
    parser.add_argument("--settle", type=float, default=DEFAULT_SETTLE_SECONDS,
                        help=f"Seconds to wait after each navigation (default: {DEFAULT_SETTLE_SECONDS})")
    parser.add_argument("--headed", action="store_true",
                        help="Show the browser window (useful for manual CAPTCHA solving)")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT,
                        help="Override the User-Agent string")
    args = parser.parse_args()

    config = HarExporterConfig(
        url=args.url,
        output=args.output,
        live_url=args.live,
        scroll_count=args.scroll,
        settle_seconds=args.settle,
        headless=not args.headed,
        user_agent=args.user_agent,
    )

    summary = asyncio.run(HarExporter(config).run())

    print(f"\nHAR written: {summary['output']} ({summary['har_bytes']:,} bytes)")
    if summary.get("waf_block_detected"):
        print(
            "WARNING: WAF block detected during the session. The HAR will only "
            "contain the technical-pages / block-page API calls, not the actual "
            "site data. Re-run from a residential IP (or use --headed and solve "
            "the CAPTCHA if shown).",
            file=sys.stderr,
        )
    print(f"\nReplay with: python -m src.network.har.replay {summary['output']} <output.json>")
    return 0 if not summary.get("waf_block_detected") else 0  # 0 even on WAF — the HAR is still useful


if __name__ == "__main__":
    sys.exit(main())
