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
        scrape = sub.add_parser("scrape", help="Live hybrid scrape through proxy")
        scrape.add_argument("--skin", "-s", default="linebet", help="Skin name (default: linebet)")
        scrape.add_argument("--action", "-a", choices=_VALID_ACTIONS, default="list_live",
                            help="Scrape action (default: list_live)")
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

    async def run(self, argv: Optional[List[str]] = None) -> int:
        args = self.parser.parse_args(argv)
        self._configure_logging(verbose=args.verbose, quiet=args.quiet)

        if args.command == "scrape":
            return await self._cmd_scrape(args)
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

        return self._emit(result, args)

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
