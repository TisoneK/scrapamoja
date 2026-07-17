"""Linebet-specific HAR exporter — thin wrapper around the framework module.

The framework module :mod:`src.network.har.export` is site-agnostic.
This script just pre-fills the Linebet-specific defaults (URLs,
user-agent, scroll behaviour) so an operator can run:

    python -m src.sites.linebet.scripts.har_export --output linebet.har

For full options, use the framework CLI directly:

    python -m src.network.har.export --url https://linebet.com/en --output linebet.har
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._common import output_dir

# Ensure repo root is on sys.path when run as a script
from ._common import ensure_repo_on_path
ensure_repo_on_path()

from src.network.har import HarExporter, HarExporterConfig  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Linebet HAR exporter. Records a Playwright browser session "
            "against linebet.com as a HAR file. Run this from a RESIDENTIAL "
            "IP — the sandbox / datacenter IP is WAF-blocked."
        ),
    )
    parser.add_argument("--output", type=Path, default=Path("linebet.har"),
                        help="Where to write the HAR file (default: linebet.har)")
    parser.add_argument("--url", default="https://linebet.com/en",
                        help="Entry URL (default: https://linebet.com/en)")
    parser.add_argument("--live", action="store_true",
                        help="Also visit /en/live after the home page")
    parser.add_argument("--scroll", type=int, default=5,
                        help="Number of times to scroll the fixtures list (default: 5)")
    parser.add_argument("--settle", type=float, default=15.0,
                        help="Seconds to wait after each navigation (default: 15)")
    parser.add_argument("--headed", action="store_true",
                        help="Show the browser window (useful for manual CAPTCHA solving)")
    args = parser.parse_args()

    # Resolve output relative to the linebet output dir if not absolute
    if not args.output.is_absolute():
        args.output = output_dir("linebet_har") / args.output

    import asyncio
    config = HarExporterConfig(
        url=args.url,
        output=args.output,
        live_url="https://linebet.com/en/live" if args.live else None,
        scroll_count=args.scroll,
        settle_seconds=args.settle,
        headless=not args.headed,
    )
    summary = asyncio.run(HarExporter(config).run())

    print(f"\nHAR written: {summary['output']} ({summary['har_bytes']:,} bytes)")
    if summary.get("waf_block_detected"):
        print(
            "WARNING: WAF block detected during the session. The HAR will only "
            "contain the technical-pages / block-page API calls, not the actual "
            "sportsbook data. Re-run from a residential IP (or use --headed and "
            "solve the CAPTCHA if shown).",
            file=sys.stderr,
        )
    print(f"\nReplay with: python -m src.sites.linebet.scripts.har_replay "
          f"{summary['output']} <output.json>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
