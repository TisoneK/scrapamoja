"""Linebet-specific HAR replayer — thin wrapper around the framework module.

Uses :class:`src.network.har.HarReplayer` for the HAR loading/filtering/
normalization, and passes Linebet's own
:class:`src.sites.linebet.extraction.rules.LinebetExtractionRules` as
the extractor callback. This is the developer-side half of the HAR
export + replay pair — given a HAR recorded by ``har_export`` (from a
residential IP), extract events without a live browser.

    python -m src.sites.linebet.scripts.har_replay <input.har> <output.json> [options]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from ._common import ensure_repo_on_path
ensure_repo_on_path()

from src.network.har import HarReplayer  # noqa: E402
from src.sites.linebet.extraction.rules import LinebetExtractionRules  # noqa: E402


def _make_linebet_extractor() -> "callable":
    """Build an extractor callback compatible with HarReplayer.

    The callback takes a capture-dict (the shape produced by
    :func:`src.network.har.har_entries_to_captures`) and returns a list
    of event dicts.
    """
    rules = LinebetExtractionRules()

    def extractor(cap: Dict[str, Any]) -> List[Dict[str, Any]]:
        decoded = rules.decode_captured_response(
            url=cap["url"],
            status=cap["status"],
            content_type=cap["response_headers"].get("content-type", ""),
            raw_bytes=cap["body"].encode("utf-8", errors="replace") if cap["body"] else None,
        )
        return [event.to_dict() for event in rules.extract_from_captured(decoded)]

    return extractor


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Linebet HAR replayer. Extracts events from a recorded HAR file "
            "using the Linebet extractor. No live browser needed — works "
            "from any IP."
        ),
    )
    parser.add_argument("input", type=Path, help="Path to the HAR file")
    parser.add_argument("output", type=Path, help="Path to write the JSON result")
    parser.add_argument(
        "--normalize", type=Path, default=None,
        help="Also write a normalized snapshot to this path",
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1

    # Filter to Linebet API URLs only
    replayer = HarReplayer(url_filter=["/bff-api/", "/fatman-api/", "/analytics-module-api/"])
    extractor = _make_linebet_extractor()

    if args.normalize:
        result, snapshot = replayer.replay_with_snapshot(args.input, extractor=extractor)
    else:
        result = replayer.replay(args.input, extractor=extractor)
        snapshot = None

    if result.error:
        print(f"ERROR: {result.error}", file=sys.stderr)
        return 1

    print(f"Loaded {result.total_har_entries} HAR entries", file=sys.stderr)
    print(f"Filtered to {result.filtered_entries} Linebet API entries", file=sys.stderr)
    print(f"Extracted {result.event_count} events", file=sys.stderr)

    indent = 2 if args.pretty else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result.to_dict(), indent=indent, default=str))
    print(f"Wrote: {args.output}", file=sys.stderr)

    if args.normalize and snapshot:
        args.normalize.parent.mkdir(parents=True, exist_ok=True)
        args.normalize.write_text(json.dumps(snapshot, indent=2, default=str))
        print(
            f"Normalized snapshot: {args.normalize} "
            f"({snapshot['metadata']['capture_count']} captures -> "
            f"{snapshot['metadata']['unique_endpoint_count']} unique endpoints)",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
