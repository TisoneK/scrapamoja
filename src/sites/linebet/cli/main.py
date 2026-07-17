"""Linebet CLI main class.

Provides a thin command-line interface around :class:`LinebetScraper`.
Three subcommands:

* ``scrape``  — run a live hybrid scrape (browser + interceptor)
* ``replay``  — re-extract events from a previously-saved captures file
* ``info``    — print the scraper's config + capabilities
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import (
    API_URL_PATTERNS,
    DEFAULT_API_SETTLE_SECONDS,
    DEFAULT_SCRAPE_TIMEOUT_SECONDS,
    MAX_CAPTURED_RESPONSES,
    SITE_CONFIG,
    SUPPORTED_DOMAINS,
    get_linebet_config,
)

logger = logging.getLogger(__name__)

_VALID_ACTIONS = ("list_prematch", "list_live", "list_all", "raw_capture")


class LinebetCLI:
    """Top-level CLI dispatcher for the Linebet scraper."""

    def __init__(self) -> None:
        self.parser = self._build_parser()

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------
    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="linebet",
            description=(
                "Hybrid browser+API scraper for linebet.com — Playwright "
                "bypasses anti-bot, NetworkInterceptor harvests JSON API "
                "responses."
            ),
        )
        parser.add_argument(
            "--verbose", "-v", action="store_true",
            help="Enable verbose (DEBUG) logging",
        )
        parser.add_argument(
            "--quiet", "-q", action="store_true",
            help="Suppress everything except errors",
        )

        sub = parser.add_subparsers(dest="command", required=True)

        # scrape
        scrape = sub.add_parser(
            "scrape", help="Run a live hybrid scrape (requires Playwright)",
        )
        scrape.add_argument(
            "--action", "-a", choices=_VALID_ACTIONS, default="list_prematch",
            help="Scrape action (default: list_prematch)",
        )
        scrape.add_argument(
            "--settle", type=float, default=DEFAULT_API_SETTLE_SECONDS,
            help=f"Seconds to wait for the SPA's API burst to settle "
                 f"(default: {DEFAULT_API_SETTLE_SECONDS})",
        )
        scrape.add_argument(
            "--scroll", type=int, default=3,
            help="Number of times to scroll the fixtures list (default: 3)",
        )
        scrape.add_argument(
            "--timeout", type=float, default=DEFAULT_SCRAPE_TIMEOUT_SECONDS,
            help=f"Hard cap on the scrape in seconds (default: {DEFAULT_SCRAPE_TIMEOUT_SECONDS})",
        )
        scrape.add_argument(
            "--headless", dest="headless", action="store_true", default=True,
            help="Run browser headless (default)",
        )
        scrape.add_argument(
            "--no-headless", dest="headless", action="store_false",
            help="Run browser with a visible window (useful for debugging "
                 "Cloudflare challenges)",
        )
        scrape.add_argument(
            "--output", "-o", type=str, default=None,
            help="Write JSON result to this file (default: stdout)",
        )
        scrape.add_argument(
            "--pretty", action="store_true",
            help="Pretty-print JSON output",
        )

        # replay
        replay = sub.add_parser(
            "replay",
            help="Re-extract events from a previously-saved captures file",
        )
        replay.add_argument(
            "--input", "-i", type=str, required=True,
            help="Path to a JSON file containing a list of captured-response "
                 "dicts (url, status, content_type, raw_bytes [base64])",
        )
        replay.add_argument(
            "--output", "-o", type=str, default=None,
            help="Write JSON result to this file (default: stdout)",
        )
        replay.add_argument(
            "--pretty", action="store_true",
            help="Pretty-print JSON output",
        )

        # info
        sub.add_parser(
            "info", help="Print the scraper's config + capabilities",
        )

        return parser

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    async def run(self, argv: Optional[List[str]] = None) -> int:
        args = self.parser.parse_args(argv)
        self._configure_logging(verbose=args.verbose, quiet=args.quiet)

        if args.command == "scrape":
            return await self._cmd_scrape(args)
        if args.command == "replay":
            return await self._cmd_replay(args)
        if args.command == "info":
            return self._cmd_info(args)
        # argparse already enforces this; defensive fallback.
        self.parser.print_help()
        return 2

    # ------------------------------------------------------------------
    # Subcommands
    # ------------------------------------------------------------------
    async def _cmd_scrape(self, args: argparse.Namespace) -> int:
        """Run a live scrape. Requires Playwright + chromium."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print(
                "ERROR: playwright is not installed. Install it with:\n"
                "  pip install playwright && playwright install chromium",
                file=sys.stderr,
            )
            return 1

        from src.selectors.engine import SelectorEngine
        from ..scraper import LinebetScraper

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=args.headless)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1536, "height": 864},
                locale="en-US",
                timezone_id="Europe/London",
            )
            page = await context.new_page()

            # Pre-flight WAF detection — give the user a clear message
            # instead of "captured 0 responses".
            try:
                pre_resp = await page.goto(
                    "https://linebet.com/en",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                pre_status = pre_resp.status if pre_resp else 0
                if pre_status == 203 or page.url.endswith("/block"):
                    print(
                        f"ERROR: Linebet WAF block detected "
                        f"(status={pre_status}, url={page.url}).\n"
                        "This scraper must run from a residential IP or "
                        "through a proxy. The 'replay' subcommand can be "
                        "used to validate the extractor against captures "
                        "made elsewhere.",
                        file=sys.stderr,
                    )
                    await browser.close()
                    return 3
                # Navigate back to about:blank so the scraper's flow can
                # do its own clean navigation.
                await page.goto("about:blank")
            except Exception as exc:
                print(f"ERROR: pre-flight navigation failed: {exc}", file=sys.stderr)
                await browser.close()
                return 1

            engine = SelectorEngine()
            scraper = LinebetScraper(page, engine)
            await scraper.initialize(page, engine)

            try:
                result = await scraper.scrape(
                    action=args.action,
                    settle_seconds=args.settle,
                    scroll_count=args.scroll,
                    timeout_seconds=args.timeout,
                )
            except Exception as exc:
                print(f"ERROR: scrape failed: {exc}", file=sys.stderr)
                await browser.close()
                return 1
            finally:
                await browser.close()

        return self._emit(result, args)

    async def _cmd_replay(self, args: argparse.Namespace) -> int:
        """Re-extract events from a captures file. No browser needed.

        The captures file is a JSON list of dicts with the shape:
            [{"url": "...", "status": 200, "content_type": "...",
              "raw_bytes": "<base64-encoded payload>"}, ...]
        """
        from ..extraction.rules import LinebetExtractionRules

        input_path = Path(args.input)
        if not input_path.exists():
            print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
            return 1

        try:
            payload = json.loads(input_path.read_text())
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON in {input_path}: {exc}", file=sys.stderr)
            return 1

        if not isinstance(payload, list):
            print(f"ERROR: expected a JSON list, got {type(payload).__name__}", file=sys.stderr)
            return 1

        # Decode + extract
        rules = LinebetExtractionRules()
        events: List[Dict[str, Any]] = []
        decoded_summaries: List[Dict[str, Any]] = []

        import base64
        for i, cap in enumerate(payload):
            if not isinstance(cap, dict):
                continue
            url = cap.get("url", "")
            status = int(cap.get("status", 0))
            content_type = cap.get("content_type", "")
            raw_b64 = cap.get("raw_bytes") or cap.get("body_b64")
            raw_bytes: Optional[bytes] = None
            if raw_b64:
                try:
                    raw_bytes = base64.b64decode(raw_b64)
                except Exception as exc:
                    logger.warning("capture %d: invalid base64 body: %s", i, exc)

            decoded = rules.decode_captured_response(
                url=url, status=status,
                content_type=content_type, raw_bytes=raw_bytes,
            )
            decoded_summaries.append(decoded.to_dict())
            events.extend(rules.extract_from_captured(decoded))

        # De-duplicate using the scraper's helper
        from ..scraper import LinebetScraper
        from ..extraction.models import Event
        # The events list contains plain dicts (from to_dict). The dedupe
        # helper expects Event instances; for the CLI we accept that the
        # replay path doesn't dedupe — the user can do it downstream if
        # needed. (Live scrape does dedupe via _dedupe_events inside
        # _execute_scrape_logic.)
        result: Dict[str, Any] = {
            "action": "replay",
            "input": str(input_path),
            "event_count": len(events),
            "captured_response_count": len(decoded_summaries),
            "events": events,
            "captured_responses": decoded_summaries,
            "extraction_source": "linebet_scraper_replay",
            "template_version": "1.0.0",
        }
        return self._emit(result, args)

    def _cmd_info(self, args: argparse.Namespace) -> int:
        """Print config + capabilities as JSON."""
        cfg = get_linebet_config()
        info = {
            "site": cfg["site"],
            "urls": cfg["urls"],
            "hybrid": cfg["hybrid"],
            "supported_domains": SUPPORTED_DOMAINS,
            "api_url_patterns": list(API_URL_PATTERNS),
            "max_captured_responses": MAX_CAPTURED_RESPONSES,
            "actions": list(_VALID_ACTIONS),
            "rate_limit": cfg["rate_limit"],
            "features": cfg["features"],
        }
        return self._emit(info, args, always_pretty=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _emit(
        self, payload: Dict[str, Any], args: argparse.Namespace,
        always_pretty: bool = False,
    ) -> int:
        indent = 2 if (args.pretty or always_pretty) else None
        text = json.dumps(payload, indent=indent, default=str)
        if args.output:
            Path(args.output).write_text(text)
            print(f"Wrote {len(text)} bytes to {args.output}", file=sys.stderr)
        else:
            print(text)
        return 0

    def _configure_logging(self, verbose: bool, quiet: bool) -> None:
        if quiet:
            level = logging.ERROR
        elif verbose:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stderr,
        )
