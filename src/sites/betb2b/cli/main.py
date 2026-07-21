"""BetB2B family CLI — drive the scraper from the command line.

Subcommands:

* ``scrape``  — live hybrid scrape (bootstrap browser through proxy + poll feeds)
* ``info``    — print skin config + scraper state
* ``skins``   — list available skins
* ``probe``   — quick connectivity probe (no extraction; verifies proxy + cookies)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_VALID_ACTIONS = ("list_live", "list_prematch", "list_all", "raw_capture", "sports_short", "top_champs")

# Friendly betting-vocabulary words → canonical action. Both the positional
# ``status`` and ``--action`` accept either form (e.g. ``scrape linebet live``
# or ``--action list_live``).
_STATUS_ALIASES = {
    "live": "list_live", "inplay": "list_live", "in-play": "list_live",
    "scheduled": "list_prematch", "prematch": "list_prematch", "pre": "list_prematch",
    "all": "list_all", "both": "list_all",
    # canonical forms pass straight through
    **{a: a for a in _VALID_ACTIONS},
}
# The words a positional first-arg could be if the user gave only a status
# (``scrape live``) rather than a skin.
_STATUS_WORDS = frozenset(_STATUS_ALIASES)


def _resolve_action(word: str) -> str:
    """Map a friendly/canonical status word to a canonical action, or raise."""
    key = (word or "").strip().lower()
    if key not in _STATUS_ALIASES:
        raise ValueError(
            f"unknown status {word!r} — use one of: "
            f"live, scheduled, all (or {', '.join(_VALID_ACTIONS)})"
        )
    return _STATUS_ALIASES[key]


def _reconcile_scrape_target(
    skin_pos: Optional[str], status_pos: Optional[str],
    skin_flag: str, action_flag: str,
) -> "tuple[str, str]":
    """Fold the easy positional form into effective (skin, action).

    Positionals win over flags. A lone status word (``scrape live``) lands in
    ``skin_pos`` — shift it to the status slot. Raises ``ValueError`` on an
    unknown status word.
    """
    if skin_pos and status_pos is None and skin_pos.lower() in _STATUS_WORDS:
        skin_pos, status_pos = None, skin_pos
    skin = skin_pos or skin_flag
    action = _resolve_action(status_pos if status_pos else action_flag)
    return skin, action


def _skins_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "skins"


def _list_skins() -> List[str]:
    skins_dir = _skins_dir()
    if not skins_dir.is_dir():
        return []
    return sorted(p.stem for p in skins_dir.glob("*.yaml"))


def _load_skin(name: str):
    from src.sites.betb2b.config import BetB2BSkinConfig

    skin_path = _skins_dir() / f"{name}.yaml"
    if not skin_path.exists():
        raise FileNotFoundError(
            f"No skin YAML for {name!r} at {skin_path}. "
            f"Available skins: {_list_skins()}"
        )
    return BetB2BSkinConfig.from_yaml(skin_path)


def _build_proxy_manager_from_env():
    """Build a ProxyManager from BETB2B_PROXY_URL + BETB2B_PROXY_USER/PASS env."""
    from src.network.proxy import build_proxy_manager

    proxy_url = os.environ.get("BETB2B_PROXY_URL")
    if not proxy_url:
        return None

    user = os.environ.get("BETB2B_PROXY_USER")
    pw = os.environ.get("BETB2B_PROXY_PASS")
    if user and pw and "@" not in proxy_url:
        # Inject creds into the URL.
        from urllib.parse import urlparse, urlunparse

        p = urlparse(proxy_url)
        netloc = f"{user}:{pw}@{p.hostname}"
        if p.port:
            netloc += f":{p.port}"
        proxy_url = urlunparse(p._replace(netloc=netloc))

    country = os.environ.get("BETB2B_PROXY_COUNTRY", "KE")
    endpoint_id = os.environ.get("BETB2B_PROXY_ID", "kenya")
    skin_domain_hint = os.environ.get("BETB2B_PROXY_DOMAIN", "*")

    return build_proxy_manager({
        "endpoints": [
            {"id": endpoint_id, "url": proxy_url,
             "country": country, "source": "ngrok"},
        ],
        "routing": [
            {"pattern": f"*.{skin_domain_hint}", "target": endpoint_id},
        ],
    }), endpoint_id


class BetB2BCLI:
    def __init__(self) -> None:
        self.parser = self._build_parser()

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="betb2b",
            description=(
                "Hybrid cookie-harvest + httpx-poll scraper for the "
                "BetB2B / 1xbet family of bookmakers."
            ),
        )
        parser.add_argument("--verbose", "-v", action="store_true", help="DEBUG logging")
        parser.add_argument("--quiet", "-q", action="store_true", help="ERROR-only logging")

        sub = parser.add_subparsers(dest="command", required=True)

        # scrape
        scrape = sub.add_parser(
            "scrape", help="Live hybrid scrape through proxy",
            description="Scrape a skin. Easy form: `scrape <skin> <live|scheduled|all>` "
                        "(e.g. `scrape linebet live`). The --skin/--action flags still work.",
        )
        # Easy positional form: `scrape linebet live`. Both optional; a lone
        # status word (`scrape live`) is understood too. These override the
        # --skin/--action flags below when given.
        scrape.add_argument("skin_pos", nargs="?", default=None, metavar="skin",
                            help="Skin name (positional). Default: linebet.")
        scrape.add_argument("status_pos", nargs="?", default=None, metavar="status",
                            help="live | scheduled | all (positional). Default: live.")
        scrape.add_argument("--skin", "-s", default="linebet", help="Skin name (default: linebet)")
        scrape.add_argument("--action", "-a", default="list_live",
                            help="Scrape action — live/scheduled/all or "
                                 f"{'/'.join(_VALID_ACTIONS)} (default: list_live)")
        scrape.add_argument("--sport", default=None,
                            help="Sport slug (e.g. basketball, football, ice-hockey, tennis, esports). "
                                 "Default: all sports.")
        scrape.add_argument("--sport-id", type=int, default=None,
                            help="Filter by sport SI id (Football=1, Basketball=3, …). "
                                 "Overrides --sport.")
        scrape.add_argument("--count", type=int, default=50,
                            help="`count=` query param — number of events (default: 50)")
        scrape.add_argument("--timeout", type=float, default=120.0,
                            help="Hard cap on the scrape in seconds (default: 120)")
        scrape.add_argument("--settle", type=float, default=12.0,
                            help="Bootstrap SPA settle seconds (default: 12)")
        scrape.add_argument("--rate", type=int, default=30,
                            help="Rate limit per minute (default: 30)")
        scrape.add_argument("--no-live", action="store_true",
                            help="Skip the live scrape; just print what we'd do")
        scrape.add_argument("--output", "-o", default=None,
                            help="Write JSON result to this file (default: stdout)")
        scrape.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
        scrape.add_argument("--compress", action="store_true",
                            help="gzip the --output file (a .gz suffix is added). "
                                 "Read it back with `betb2b view <file>`. Large "
                             "results (full odds) compress ~85-90%%.")
        scrape.add_argument("--db", default=None,
                            help="Also persist the result into a SQLite odds store "
                                 "at this path (events/odds_snapshots time-series). "
                                 "Opt-in; JSON output is unaffected. "
                                 "Default: data/betb2b/odds.db if flag given without value.",
                            nargs="?", const="data/betb2b/odds.db")

        # poll — scrape + persist on a loop so line-movement accumulates
        poll = sub.add_parser(
            "poll", help="Scrape + persist to the odds store on an interval",
            description="Repeatedly scrape a skin and persist to the SQLite odds "
                        "store so line movement accumulates. `poll linebet live` "
                        "is the easy form. Ctrl-C stops cleanly.",
        )
        poll.add_argument("skin_pos", nargs="?", default=None, metavar="skin",
                          help="Skin name (positional). Default: linebet.")
        poll.add_argument("status_pos", nargs="?", default=None, metavar="status",
                          help="live | scheduled | all (positional). Default: live.")
        poll.add_argument("--skin", "-s", default="linebet", help="Skin name (default: linebet)")
        poll.add_argument("--action", "-a", default="list_live",
                          help="live/scheduled/all or the canonical list_* action")
        poll.add_argument("--sport", default=None, help="Sport slug. Default: all sports.")
        poll.add_argument("--sport-id", type=int, default=None, help="Sport SI id (overrides --sport)")
        poll.add_argument("--interval", type=float, default=60.0,
                          help="Target seconds between cycle starts (default: 60). "
                               "If a scrape overruns it, the next starts immediately.")
        poll.add_argument("--cycles", type=int, default=0,
                          help="Stop after this many cycles (0 = unlimited)")
        poll.add_argument("--for", dest="for_seconds", type=float, default=0.0,
                          help="Stop after this many wall-clock seconds (0 = unlimited)")
        poll.add_argument("--db", default="data/betb2b/odds.db",
                          help="SQLite odds store path (default: data/betb2b/odds.db)")
        poll.add_argument("--count", type=int, default=50, help="events `count=` param")
        poll.add_argument("--timeout", type=float, default=120.0, help="per-scrape hard cap (s)")
        poll.add_argument("--settle", type=float, default=12.0, help="SPA settle seconds")
        poll.add_argument("--rate", type=int, default=30, help="feed rate limit per minute")

        # info
        info = sub.add_parser("info", help="Print skin config + scraper state")
        info.add_argument("--skin", "-s", default="linebet", help="Skin name")
        info.add_argument("--sport", default=None,
                          help="Sport slug (e.g. basketball). Default: all sports.")

        # skins
        sub.add_parser("skins", help="List available skins")

        # sports
        sports = sub.add_parser("sports", help="List available per-sport scrapers")
        sports.add_argument("--verbose", "-v", action="store_true",
                            help="Show full sport config (DOM selectors, market overrides)")

        # probe
        probe = sub.add_parser("probe", help="Connectivity probe — verify proxy + bootstrap")
        probe.add_argument("--skin", "-s", default="linebet", help="Skin name")
        probe.add_argument("--sport", default=None,
                           help="Sport slug to probe (e.g. basketball). Default: all sports.")
        probe.add_argument("--settle", type=float, default=12.0,
                           help="Bootstrap SPA settle seconds (default: 12)")
        probe.add_argument("--output", "-o", default=None,
                           help="Write JSON probe result to this file")

        # view
        view = sub.add_parser("view", help="Pretty-print a scrape output file (gzip or plain)")
        view.add_argument("path", help="Path to a JSON or JSON.gz output file")
        view.add_argument("--compact", action="store_true", help="Compact (unindented) JSON")
        view.add_argument("--decompress-to", default=None,
                          help="Instead of printing, write the decompressed JSON to this path")

        # compare-match
        cm = sub.add_parser("compare-match", help="Compare match page UI data vs API endpoints")
        cm.add_argument("--skin", "-s", default="linebet", help="Skin name (default: linebet)")
        cm.add_argument("--sport", default="basketball",
                        help="Sport slug (basketball, football, etc.)")
        cm.add_argument("--event-id", default=None,
                        help="Target event ID (numeric). Auto-discovers if not set.")
        cm.add_argument("--match-url", default=None,
                        help="Explicit match page URL (overrides auto-construction)")
        cm.add_argument("--live", action="store_true",
                        help="Use live path instead of prematch (line)")
        cm.add_argument("--settle", type=float, default=12.0,
                        help="SPA settle seconds (default: 12)")
        cm.add_argument("--output", default=None,
                        help="Output directory for report + artifacts")
        cm.add_argument("--headless", action="store_true", default=True,
                        help="Headless browser (default: True)")
        cm.add_argument("--hover", action="store_true", default=True,
                        help="Hover team names to trigger H2H popups")

        return parser

    def create_parser(self) -> argparse.ArgumentParser:
        """Return the argument parser (for the ``src.main`` dispatcher, which
        parses argv itself then calls :meth:`run_args`)."""
        return self.parser

    async def run(self, argv: Optional[List[str]] = None) -> int:
        """Parse ``argv`` and dispatch. Used by the standalone entry point
        (``python -m src.sites.betb2b.cli``)."""
        args = self.parser.parse_args(argv)
        return await self.run_args(args)

    async def run_args(self, args: argparse.Namespace) -> int:
        """Dispatch already-parsed args. Used by the ``src.main`` dispatcher
        (which calls ``create_parser().parse_args()`` before ``run_args``)."""
        self._configure_logging(verbose=args.verbose, quiet=args.quiet)

        if args.command == "scrape":
            return await self._cmd_scrape(args)
        if args.command == "poll":
            return await self._cmd_poll(args)
        if args.command == "info":
            return self._cmd_info(args)
        if args.command == "skins":
            return self._cmd_skins(args)
        if args.command == "sports":
            return self._cmd_sports(args)
        if args.command == "probe":
            return await self._cmd_probe(args)
        if args.command == "view":
            return self._cmd_view(args)
        if args.command == "compare-match":
            return await self._cmd_compare_match(args)

        self.parser.print_help()
        return 2

    # ------------------------------------------------------------------ #
    async def _cmd_scrape(self, args: argparse.Namespace) -> int:
        # Reconcile the easy positional form (`scrape linebet live`) with the
        # --skin/--action flags. Positionals win when given.
        try:
            args.skin, args.action = _reconcile_scrape_target(
                getattr(args, "skin_pos", None), getattr(args, "status_pos", None),
                args.skin, args.action,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

        skin = _load_skin(args.skin)
        pm_and_id = _build_proxy_manager_from_env()
        proxy_manager = pm_and_id[0] if pm_and_id else None
        proxy_endpoint_id = pm_and_id[1] if pm_and_id else None

        from src.sites.betb2b import BetB2BScraper

        if args.no_live:
            print(json.dumps({
                "skin": skin.to_dict(),
                "action": args.action,
                "sport": args.sport,
                "sport_id": args.sport_id,
                "count": args.count,
                "would_run": True,
                "note": "--no-live set; skipping the live scrape.",
            }, indent=2))
            return 0

        try:
            async with BetB2BScraper(
                skin,
                proxy_manager=proxy_manager,
                proxy_endpoint_id=proxy_endpoint_id,
                rate_limit_per_minute=args.rate,
                settle_seconds=args.settle,
                sport=args.sport,
            ) as scraper:
                result = await scraper.scrape(
                    action=args.action,
                    sport_id=args.sport_id,
                    count=args.count,
                    timeout_seconds=args.timeout,
                )
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: scrape failed: {exc}", file=sys.stderr)
            return 1

        # Opt-in structured persistence (JSON output is unaffected).
        if getattr(args, "db", None):
            try:
                from src.sites.betb2b.store import persist_result

                run_id = persist_result(result, args.db)
                print(
                    f"Persisted run {run_id} "
                    f"({result.get('event_count', 0)} events) to {args.db}",
                    file=sys.stderr,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: --db persist failed: {exc}", file=sys.stderr)

        return self._emit(result, args)

    # ------------------------------------------------------------------ #
    async def _cmd_poll(self, args: argparse.Namespace) -> int:
        # Same friendly grammar as scrape.
        try:
            args.skin, args.action = _reconcile_scrape_target(
                getattr(args, "skin_pos", None), getattr(args, "status_pos", None),
                args.skin, args.action,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

        skin = _load_skin(args.skin)
        pm_and_id = _build_proxy_manager_from_env()
        proxy_manager = pm_and_id[0] if pm_and_id else None
        proxy_endpoint_id = pm_and_id[1] if pm_and_id else None

        from src.sites.betb2b import BetB2BScraper
        from src.sites.betb2b.poll import poll_loop
        from src.sites.betb2b.store import counts, init_db, persist_result

        conn = init_db(args.db)
        stop = {"flag": False}

        def _on_cycle(n: int, result: Dict[str, Any], run_id: Any) -> None:
            odds = counts(conn)["odds_snapshots"]
            print(
                f"[cycle {n}] run {run_id}: {result.get('event_count', 0)} events, "
                f"{result.get('scrape_duration_seconds', 0):.0f}s | odds_snapshots total={odds}",
                file=sys.stderr, flush=True,
            )

        def _on_error(n: int, exc: Exception) -> None:
            print(f"[cycle {n}] ERROR: {exc}", file=sys.stderr, flush=True)

        print(
            f"Polling skin={args.skin} action={args.action} every {args.interval:.0f}s "
            f"→ {args.db}  (Ctrl-C to stop)",
            file=sys.stderr, flush=True,
        )
        try:
            async with BetB2BScraper(
                skin, proxy_manager=proxy_manager, proxy_endpoint_id=proxy_endpoint_id,
                rate_limit_per_minute=args.rate, settle_seconds=args.settle,
                sport=args.sport,
            ) as scraper:
                async def _scrape_once() -> Dict[str, Any]:
                    return await scraper.scrape(
                        action=args.action, sport_id=args.sport_id,
                        count=args.count, timeout_seconds=args.timeout,
                    )

                done = await poll_loop(
                    scrape_once=_scrape_once,
                    persist=lambda r: persist_result(r, args.db, conn=conn),
                    interval=args.interval, cycles=args.cycles,
                    max_seconds=args.for_seconds,
                    on_cycle=_on_cycle, on_error=_on_error,
                    should_stop=lambda: stop["flag"],
                )
            print(f"Poll finished: {done} cycle(s). Store: {args.db}", file=sys.stderr)
            return 0
        except KeyboardInterrupt:
            print("\nPoll interrupted — stopping cleanly.", file=sys.stderr)
            return 0
        finally:
            conn.close()

    def _cmd_info(self, args: argparse.Namespace) -> int:
        skin = _load_skin(args.skin)
        from src.sites.betb2b import BetB2BScraper
        # Instantiate the scraper just to read the resolved sport context.
        scraper = BetB2BScraper(skin, sport=getattr(args, "sport", None))
        info: Dict[str, Any] = {
            "skin": skin.to_dict(),
            "actions": sorted(_VALID_ACTIONS),
            "extraction_mode": "hybrid",
            "sport": scraper.sport_scraper.to_dict(),
            "sport_context": scraper.sport_ctx.to_dict(),
            "feed_urls": {
                "live_events_top": skin.feed_url("events_top", root="live"),
                "line_events_top": skin.feed_url("events_top", root="line"),
                "sports_short": skin.feed_url("sports_short", root="line"),
                "top_champs": skin.feed_url("top_champs", root="line"),
            },
            "bootstrap_urls": {
                "home": skin.bootstrap_url("home"),
                "live": skin.bootstrap_url("live"),
                "sport_line": (
                    f"{skin.base_url}{scraper.sport_ctx.bootstrap_path}"
                    if scraper.sport_ctx.slug else None
                ),
                "sport_live": (
                    f"{skin.base_url}{scraper.sport_ctx.live_bootstrap_path}"
                    if scraper.sport_ctx.slug else None
                ),
            },
            "validation_errors": skin.validate(),
        }
        return self._emit(info, args, always_pretty=True)

    def _cmd_skins(self, args: argparse.Namespace) -> int:
        skins = _list_skins()
        out = {"skins": skins, "count": len(skins), "skins_dir": str(_skins_dir())}
        return self._emit(out, args, always_pretty=True)

    def _cmd_sports(self, args: argparse.Namespace) -> int:
        from src.sites.betb2b.sports import list_sport_scraper_summaries

        summaries = list_sport_scraper_summaries()
        if getattr(args, "verbose", False):
            out: Dict[str, Any] = {
                "sports": [
                    {**s, "_full_config": (
                        # Re-instantiate to dump the full config (selectors, overrides).
                        # This is verbose but valuable for debugging selector drift.
                        __import__(
                            "src.sites.betb2b.sports", fromlist=["get_sport_scraper"]
                        ).get_sport_scraper(slug=s["slug"]).to_dict()
                    )}
                    for s in summaries
                ],
                "count": len(summaries),
            }
        else:
            out = {"sports": summaries, "count": len(summaries)}
        return self._emit(out, args, always_pretty=True)

    async def _cmd_probe(self, args: argparse.Namespace) -> int:
        skin = _load_skin(args.skin)
        pm_and_id = _build_proxy_manager_from_env()
        proxy_manager = pm_and_id[0] if pm_and_id else None
        proxy_endpoint_id = pm_and_id[1] if pm_and_id else None

        from src.sites.betb2b import BetB2BScraper

        try:
            async with BetB2BScraper(
                skin,
                proxy_manager=proxy_manager,
                proxy_endpoint_id=proxy_endpoint_id,
                settle_seconds=args.settle,
                sport=getattr(args, "sport", None),
            ) as scraper:
                # Bootstrap the session explicitly — proves the proxy +
                # cookie harvest path end-to-end without polling feeds.
                session = await scraper.session_manager.get_session()
                info = scraper.get_info()
                probe_result = {
                    "skin": skin.name,
                    "domain": skin.domain,
                    "sport": scraper.sport_scraper.slug or "all",
                    "sport_id": scraper.sport_scraper.sport_id,
                    "session_harvested": True,
                    "cookie_count": len(session.cookies),
                    "session_age_seconds": (
                        scraper.session_manager.session_age.total_seconds()
                        if scraper.session_manager.session_age else None
                    ),
                    "user_agent": (session.user_agent or "")[:80],
                    "proxy": info["proxy_endpoint"],
                    "would_call": {
                        "live_events_top": skin.feed_url("events_top", root="live"),
                        "line_events_top": skin.feed_url("events_top", root="line"),
                        "sport_bootstrap_path": scraper.sport_ctx.bootstrap_path,
                    },
                }
        except Exception as exc:  # noqa: BLE001
            probe_result = {
                "skin": skin.name,
                "domain": skin.domain,
                "session_harvested": False,
                "error": str(exc),
            }
            print(json.dumps(probe_result, indent=2), file=sys.stderr)
            return 1

        if args.output:
            Path(args.output).write_text(json.dumps(probe_result, indent=2))
            print(f"Wrote probe result to {args.output}", file=sys.stderr)
        else:
            print(json.dumps(probe_result, indent=2))
        return 0

    def _cmd_view(self, args: argparse.Namespace) -> int:
        from src.sites.betb2b.storage import decompress_file, load_json

        path = Path(args.path)
        if not path.exists():
            print(f"ERROR: no such file: {path}", file=sys.stderr)
            return 1

        if args.decompress_to:
            out = decompress_file(path, args.decompress_to)
            print(f"Decompressed {path} -> {out}", file=sys.stderr)
            return 0

        try:
            payload = load_json(path)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: could not read {path}: {exc}", file=sys.stderr)
            return 1
        indent = None if args.compact else 2
        print(json.dumps(payload, indent=indent, default=str, ensure_ascii=False))
        return 0

    async def _cmd_compare_match(self, args: argparse.Namespace) -> int:
        from src.sites.betb2b.scripts.compare_match import main as compare_main

        # Reconstruct sys.argv for the script's own parser.
        script_argv = [
            "--skin", args.skin,
            "--sport", args.sport,
            "--settle", str(args.settle),
        ]
        if args.event_id:
            script_argv += ["--event-id", args.event_id]
        if args.match_url:
            script_argv += ["--match-url", args.match_url]
        if args.live:
            script_argv.append("--live")
        if args.output:
            script_argv += ["--output", args.output]
        if args.hover:
            script_argv.append("--hover")
        if getattr(args, "verbose", False):
            script_argv.append("--verbose")

        import sys as _sys
        old_argv = _sys.argv
        try:
            _sys.argv = ["compare-match"] + script_argv
            return await compare_main()
        finally:
            _sys.argv = old_argv

    # ------------------------------------------------------------------ #
    def _emit(self, payload: Dict[str, Any], args: argparse.Namespace, always_pretty: bool = False) -> int:
        indent = 2 if (getattr(args, "pretty", False) or always_pretty) else None
        output = getattr(args, "output", None)
        if output:
            from src.sites.betb2b.storage import dump_json

            # --compress forces gzip; otherwise auto (large results compress anyway).
            compress = True if getattr(args, "compress", False) else None
            written = dump_json(payload, output, compress=compress, indent=indent)
            size = written.stat().st_size
            note = " (gzip)" if written.suffix == ".gz" else ""
            print(f"Wrote {size} bytes to {written}{note}", file=sys.stderr)
        else:
            print(json.dumps(payload, indent=indent, default=str))
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


class BetB2BMainCLI:
    """Adapter that exposes :class:`BetB2BCLI` through the ``src.main``
    dispatcher contract (``create_parser()`` + ``run(args, interrupt_handler=,
    shutdown_coordinator=)``), so betb2b runs via
    ``python -m src.main betb2b …`` alongside the other sites.

    betb2b's own flags are unchanged — only the invocation path differs.
    The interrupt/shutdown kwargs are accepted for signature compatibility;
    the scraper manages its own async lifecycle via ``async with``.
    """

    def __init__(self) -> None:
        self._cli = BetB2BCLI()

    def create_parser(self) -> argparse.ArgumentParser:
        return self._cli.create_parser()

    async def run(
        self,
        args: argparse.Namespace,
        interrupt_handler: Any = None,
        shutdown_coordinator: Any = None,
    ) -> int:
        return await self._cli.run_args(args)
