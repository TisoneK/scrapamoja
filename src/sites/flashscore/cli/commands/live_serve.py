"""Live-serve command — expose a live match's score as a JSON HTTP endpoint.

Runs the same scrape loop as ``live-poll`` but, instead of printing, keeps the
latest derived score state in memory and serves it at ``GET /score`` (and
``GET /health``). This is the Data Source a task2sms HTTP source polls: its
conditions key off a single field (e.g. ``q1_total`` gte N, ``status`` eq
``live``, ``q1_ended`` eq ``true``) and its templates fill ``{home}``/``{away}``/
``{stage}``.

The browser/poll loop runs in the asyncio main thread; a tiny stdlib HTTP
server runs in a daemon thread and just serializes the last snapshot (a single
dict swapped atomically each cycle). Score + staging only; no betting logic.
"""

import argparse
import json
import sys
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.sites.flashscore.scraper import FlashscoreScraper

# Latest snapshot, swapped (not mutated) each cycle so the HTTP thread always
# reads a complete dict under the GIL without a lock.
_STATE: dict[str, dict] = {
    "latest": {
        "found": False,
        "status": "",
        "match": None,
        "updated_at": datetime.now(UTC).isoformat(),
        "note": "starting up — no scrape yet",
    }
}


def _progress(msg: str) -> None:
    print(f"  {msg}", file=sys.stderr, flush=True)


def _make_handler():
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence default access logging
            pass

        def _send(self, code: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?", 1)[0].rstrip("/")
            if path in ("", "/score"):
                self._send(200, _STATE["latest"])
            elif path == "/health":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "not found", "paths": ["/score", "/health"]})

    return _Handler


class LiveServeCommand:
    """Serve a live match's derived score state as a JSON HTTP endpoint."""

    help_text = "Serve a live match's score as JSON at /score (for task2sms Data Source)"

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
            help="Sport whose live board to watch",
        )
        parser.add_argument("--match", type=str, default=None,
                            help="Case-insensitive team substring (either side).")
        parser.add_argument("--match-id", type=str, default=None,
                            help="Exact Flashscore match id.")
        parser.add_argument("--interval", type=float, default=20.0,
                            help="Seconds between scrapes (default: 20).")
        parser.add_argument("--port", type=int, default=8787,
                            help="HTTP port to serve /score on (default: 8787).")
        parser.add_argument("--host", type=str, default="127.0.0.1",
                            help="Bind address (default: 127.0.0.1).")
        parser.add_argument("--limit", type=int, default=None,
                            help="Cap live matches scanned per scrape.")
        parser.add_argument("--for", dest="for_seconds", type=float, default=0.0,
                            help="Stop after this many seconds (0 = unbounded).")
        parser.add_argument("--no-headless", action="store_true",
                            help="Show the browser window.")

    async def execute(self, args: argparse.Namespace) -> int:
        from src.browser.config import BrowserConfiguration
        from src.browser.manager import BrowserManager
        from src.selectors import get_selector_engine
        from src.sites.flashscore.orchestrator import FlashscoreOrchestrator
        from src.sites.flashscore.poll import (
            derive_score_state,
            poll_loop,
            select_live_matches,
        )

        session = None
        browser_manager = None
        httpd = None
        target = args.match or args.match_id or "ALL"

        try:
            # Start the HTTP server first so /health is up immediately.
            httpd = ThreadingHTTPServer((args.host, args.port), _make_handler())
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            _progress(f"Serving http://{args.host}:{args.port}/score  (target: {target})")

            browser_manager = BrowserManager(site_id="flashscore")
            browser_config = BrowserConfiguration(headless=not args.no_headless)
            _progress("Launching browser...")
            session = await browser_manager.create_session(browser_config)
            if self.shutdown_coordinator:
                session.register_shutdown_cleanup(self.shutdown_coordinator)

            selector_engine = get_selector_engine()
            scraper = FlashscoreScraper(page=await session.create_page(),
                                        selector_engine=selector_engine)
            await scraper.initialize_selectors()
            _progress("Selectors loaded — polling")
            orchestrator = FlashscoreOrchestrator(scraper)

            prev_holder: dict[str, dict] = {"prev": {}}

            async def _scrape_once():
                scrape_args = argparse.Namespace(
                    sport=args.sport, status="live", limit=args.limit,
                    full_workflow=False,
                )
                result = await scraper.scrape_with_interrupt_handling(
                    orchestrator.scrape_data, scrape_args
                )
                matches = result.get("matches", []) if isinstance(result, dict) else []
                selected = select_live_matches(matches, team=args.match,
                                               match_id=args.match_id)
                return selected[0] if selected else None

            def _persist(match):
                state = derive_score_state(match, prev_holder["prev"], target=target)
                prev_holder["prev"] = state
                _STATE["latest"] = state  # atomic swap
                return state

            def _on_cycle(n, _match, state):
                if state.get("found"):
                    _progress(
                        f"[{n}] {state['match']} {state['home']}-{state['away']} "
                        f"| {state['stage'] or state['status']} "
                        f"| q1_total={state['q1_total']} q1_final={state['q1_final']}"
                    )
                else:
                    _progress(f"[{n}] '{target}' not live yet")

            def _on_error(n, exc):
                _progress(f"[{n}] ERROR: {exc}")

            await poll_loop(
                scrape_once=_scrape_once, persist=_persist,
                interval=args.interval, max_seconds=args.for_seconds,
                on_cycle=_on_cycle, on_error=_on_error,
            )
            return 0

        except KeyboardInterrupt:
            print("\nServe interrupted — stopping cleanly.", file=sys.stderr)
            return 0
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        finally:
            if httpd:
                httpd.shutdown()
            if session and browser_manager:
                try:
                    await browser_manager.close_session(session.session_id)
                except Exception as e:  # noqa: BLE001
                    print(f"Warning: session cleanup: {e}", file=sys.stderr)
