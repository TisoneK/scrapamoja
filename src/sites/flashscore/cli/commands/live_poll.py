"""Live-poll command — follow a live match's score on an interval.

Unlike ``scrape`` (one shot), this launches the browser ONCE and then re-scrapes
the live board every ``--interval`` seconds, printing the running score for the
match(es) matching ``--match`` / ``--match-id``. The pure loop and the
pick/format helpers live in :mod:`src.sites.flashscore.poll` so they are
unit-tested without a browser; this command only wires the real scraper in.

Scope: score + stage/status only. No betting logic.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from src.sites.flashscore.scraper import FlashscoreScraper


def _progress(msg: str) -> None:
    """Progress/logs go to stderr so stdout stays clean for the score lines."""
    print(f"  {msg}", file=sys.stderr, flush=True)


class LivePollCommand:
    """Poll a live Flashscore match's score on an interval."""

    help_text = "Poll a live match's score on an interval (score + stage only)"

    def __init__(self):
        self.interrupt_handler = None
        self.shutdown_coordinator = None

    def set_interrupt_handler(self, interrupt_handler):
        self.interrupt_handler = interrupt_handler

    def set_shutdown_coordinator(self, shutdown_coordinator):
        self.shutdown_coordinator = shutdown_coordinator

    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "sport",
            choices=["basketball", "football", "tennis"],
            help="Sport whose live board to poll",
        )
        parser.add_argument(
            "--match",
            type=str,
            default=None,
            help="Case-insensitive team substring; matches either home or away "
            "(e.g. 'Beer Sheva'). Omit to report every live match.",
        )
        parser.add_argument(
            "--match-id",
            type=str,
            default=None,
            help="Exact Flashscore match id (most precise target).",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=30.0,
            help="Seconds between scrapes (default: 30).",
        )
        parser.add_argument(
            "--cycles",
            type=int,
            default=0,
            help="Stop after this many scrapes (0 = run until Ctrl-C).",
        )
        parser.add_argument(
            "--for",
            dest="for_seconds",
            type=float,
            default=0.0,
            help="Stop after this many seconds of wall-clock (0 = unbounded).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Cap live matches scanned per scrape (default: no cap).",
        )
        parser.add_argument(
            "--jsonl",
            type=str,
            default=None,
            help="Append each cycle's snapshot as one JSON line to this file.",
        )
        parser.add_argument(
            "--no-headless",
            action="store_true",
            help="Show the browser window.",
        )

    async def execute(self, args: argparse.Namespace) -> int:
        from src.browser.config import BrowserConfiguration
        from src.browser.manager import BrowserManager
        from src.selectors import get_selector_engine
        from src.sites.flashscore.orchestrator import FlashscoreOrchestrator
        from src.sites.flashscore.poll import (
            format_match_line,
            poll_loop,
            select_live_matches,
        )

        session = None
        browser_manager = None
        jsonl_fh = None
        target = args.match or args.match_id or "ALL"

        try:
            browser_manager = BrowserManager(site_id="flashscore")
            browser_config = BrowserConfiguration(headless=not args.no_headless)

            _progress("Launching browser...")
            session = await browser_manager.create_session(browser_config)
            if self.shutdown_coordinator:
                session.register_shutdown_cleanup(self.shutdown_coordinator)

            selector_engine = get_selector_engine()
            scraper = FlashscoreScraper(
                page=await session.create_page(),
                selector_engine=selector_engine,
            )
            await scraper.initialize_selectors()
            _progress("Selectors loaded")

            orchestrator = FlashscoreOrchestrator(scraper)

            if args.jsonl:
                Path(args.jsonl).parent.mkdir(parents=True, exist_ok=True)
                jsonl_fh = open(args.jsonl, "a", encoding="utf-8")

            async def _scrape_once():
                scrape_args = argparse.Namespace(
                    sport=args.sport,
                    status="live",
                    limit=args.limit,
                    full_workflow=False,
                )
                result = await scraper.scrape_with_interrupt_handling(
                    orchestrator.scrape_data, scrape_args
                )
                matches = (
                    result.get("matches", []) if isinstance(result, dict) else []
                )
                selected = select_live_matches(
                    matches, team=args.match, match_id=args.match_id
                )
                return {
                    "scraped_at": datetime.now(UTC).isoformat(),
                    "target": target,
                    "live_total": len(matches),
                    "selected": selected,
                }

            def _persist(snap):
                if jsonl_fh:
                    jsonl_fh.write(json.dumps(snap, ensure_ascii=False) + "\n")
                    jsonl_fh.flush()
                return None

            def _on_cycle(n, snap, _run_id):
                now = datetime.now(UTC)
                selected = snap["selected"]
                if selected:
                    for m in selected:
                        print(format_match_line(m, cycle=n, now=now), flush=True)
                else:
                    ts = now.strftime("%H:%M:%S")
                    print(
                        f"[cycle {n} {ts}] no live match for '{target}' yet "
                        f"({snap['live_total']} live on board)",
                        flush=True,
                    )

            def _on_error(n, exc):
                print(f"[cycle {n}] ERROR: {exc}", file=sys.stderr, flush=True)

            _progress(
                f"Polling {args.sport} live for '{target}' every "
                f"{args.interval:.0f}s (Ctrl-C to stop)"
            )
            done = await poll_loop(
                scrape_once=_scrape_once,
                persist=_persist,
                interval=args.interval,
                cycles=args.cycles,
                max_seconds=args.for_seconds,
                on_cycle=_on_cycle,
                on_error=_on_error,
            )
            _progress(f"Poll finished: {done} cycle(s)")
            return 0

        except KeyboardInterrupt:
            print("\nPoll interrupted — stopping cleanly.", file=sys.stderr)
            return 0
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        finally:
            if jsonl_fh:
                try:
                    jsonl_fh.close()
                except Exception:  # noqa: BLE001
                    pass
            if session and browser_manager:
                try:
                    await browser_manager.close_session(session.session_id)
                except Exception as e:  # noqa: BLE001
                    print(f"Warning: session cleanup: {e}", file=sys.stderr)
