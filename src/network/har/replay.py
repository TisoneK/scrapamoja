"""HAR replay — extract data from a recorded HAR file, no browser needed.

This is the **developer-side** half of the HAR export + replay pair.
Given a HAR file produced by :mod:`src.network.har.export` (or by a
real browser's DevTools "Save all as HAR"), this module:

  1. Filters entries to URLs matching ``url_filter`` (optional —
     defaults to "all entries").
  2. Decodes each response body (HAR bodies are base64-encoded).
  3. Optionally calls an extractor callback on each decoded response
     to produce structured events.
  4. Optionally normalizes the captures into a stable snapshot (via
     :func:`src.core.snapshot.normalize.normalize_capture_list`).
  5. Returns a :class:`HarReplayResult` with everything.

Site-agnostic. Site-specific behaviour comes from the ``extractor``
callback the caller provides.

Public API:

    from src.network.har import HarReplayer, HarReplayResult, har_entries_to_captures

CLI:

    python -m src.network.har.replay <input.har> <output.json> [options]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.core.snapshot.normalize import (
    NormalizerConfig,
    normalize_capture_list,
)
from .to_snapshot import har_entries_to_captures


# Type alias: an extractor takes a capture-dict and returns a list of
# arbitrary event dicts. The caller decides what an "event" is.
Extractor = Callable[[Dict[str, Any]], List[Dict[str, Any]]]


@dataclass
class HarReplayResult:
    """Result of replaying a HAR file."""
    input_path: str
    total_har_entries: int
    filtered_entries: int
    event_count: int
    events: List[Dict[str, Any]] = field(default_factory=list)
    captured_responses: List[Dict[str, Any]] = field(default_factory=list)
    extraction_source: str = "har_replay"
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": self.input_path,
            "total_har_entries": self.total_har_entries,
            "filtered_entries": self.filtered_entries,
            "event_count": self.event_count,
            "events": self.events,
            "captured_responses": self.captured_responses,
            "extraction_source": self.extraction_source,
            "error": self.error,
            "success": self.success,
        }


class HarReplayer:
    """Replay a HAR file through an optional extractor.

    Usage::

        replayer = HarReplayer(url_filter=["/bff-api/", "/fatman-api/"])
        result = replayer.replay("session.har", extractor=my_extractor)
        print(result.event_count)
    """

    def __init__(
        self,
        url_filter: Optional[List[str]] = None,
        normalizer_config: Optional[NormalizerConfig] = None,
    ) -> None:
        """
        Args:
            url_filter: Optional list of URL substrings — only entries
                whose URL contains at least one of these are kept.
                ``None`` means "keep all entries".
            normalizer_config: Optional config for the snapshot
                normalizer. Only used if :meth:`replay` is called with
                ``normalize=True``.
        """
        self.url_filter = url_filter
        self.normalizer_config = normalizer_config

    def replay(
        self,
        har_path: Path,
        extractor: Optional[Extractor] = None,
        normalize: bool = False,
    ) -> HarReplayResult:
        """Replay a HAR file.

        Args:
            har_path: Path to the HAR file.
            extractor: Optional callback that takes a capture-dict and
                returns a list of event dicts. If ``None``, no
                extraction is done — only the capture summaries are
                returned (useful for "raw_capture" mode).
            normalize: If ``True``, also produce a normalized snapshot
                accessible as ``result.captured_responses`` (which
                normally holds raw capture summaries). For the full
                normalized snapshot, use :meth:`replay_with_snapshot`.

        Returns:
            A :class:`HarReplayResult`.
        """
        if not har_path.exists():
            return HarReplayResult(
                input_path=str(har_path), total_har_entries=0,
                filtered_entries=0, event_count=0,
                error=f"input not found: {har_path}",
            )

        try:
            har = json.loads(har_path.read_text())
        except json.JSONDecodeError as exc:
            return HarReplayResult(
                input_path=str(har_path), total_har_entries=0,
                filtered_entries=0, event_count=0,
                error=f"invalid HAR JSON: {exc}",
            )

        captures = har_entries_to_captures(har)
        total = len(captures)

        # Apply URL filter
        if self.url_filter:
            captures = [
                c for c in captures
                if any(p in c["url"] for p in self.url_filter)
            ]
        filtered = len(captures)

        # Build capture summaries (always — caller may want them even
        # without an extractor)
        capture_summaries = [
            {
                "url": c["url"],
                "status": c["status"],
                "method": c["method"],
                "content_type": c["response_headers"].get("content-type", ""),
                "body_bytes": len(c["body"]) if c["body"] else 0,
            }
            for c in captures
        ]

        # Run extractor if provided
        events: List[Dict[str, Any]] = []
        if extractor:
            for cap in captures:
                try:
                    events.extend(extractor(cap))
                except Exception as exc:
                    # Defensive — one bad capture shouldn't kill the whole replay
                    print(f"  extractor error on {cap['url']}: {exc}", file=sys.stderr)

        if normalize:
            # Replace capture_summaries with normalized ones
            snapshot = normalize_capture_list(captures, config=self.normalizer_config)
            capture_summaries = snapshot["endpoints"]

        return HarReplayResult(
            input_path=str(har_path),
            total_har_entries=total,
            filtered_entries=filtered,
            event_count=len(events),
            events=events,
            captured_responses=capture_summaries,
        )

    def replay_with_snapshot(
        self,
        har_path: Path,
        extractor: Optional[Extractor] = None,
    ) -> tuple[HarReplayResult, Optional[Dict[str, Any]]]:
        """Replay a HAR file and also return a normalized snapshot.

        Returns a tuple of ``(result, snapshot)``. If the HAR can't be
        loaded, ``snapshot`` is ``None``.
        """
        result = self.replay(har_path, extractor=extractor)
        if result.error:
            return result, None

        # Re-load + normalize (cheap — files are small)
        try:
            har = json.loads(har_path.read_text())
            captures = har_entries_to_captures(har)
            if self.url_filter:
                captures = [
                    c for c in captures
                    if any(p in c["url"] for p in self.url_filter)
                ]
            snapshot = normalize_capture_list(captures, config=self.normalizer_config)
            return result, snapshot
        except Exception as exc:
            return result, None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Replay a HAR file through an optional extractor. Site-agnostic — "
            "for site-specific extraction, write a Python script that uses "
            "HarReplayer directly with a site-specific extractor callback."
        ),
    )
    parser.add_argument("input", type=Path, help="Path to the HAR file")
    parser.add_argument("output", type=Path, help="Path to write the JSON result")
    parser.add_argument(
        "--filter", "-f", action="append", default=[],
        help="URL substring filter (can be repeated). Only entries whose URL "
             "contains at least one filter are kept. Default: keep all.",
    )
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

    url_filter = args.filter if args.filter else None
    replayer = HarReplayer(url_filter=url_filter)
    result, snapshot = (
        replayer.replay_with_snapshot(args.input, extractor=None)
        if args.normalize else
        (replayer.replay(args.input, extractor=None), None)
    )

    if result.error:
        print(f"ERROR: {result.error}", file=sys.stderr)
        return 1

    indent = 2 if args.pretty else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result.to_dict(), indent=indent, default=str))
    print(f"Loaded {result.total_har_entries} HAR entries")
    print(f"Filtered to {result.filtered_entries} entries")
    print(f"Wrote: {args.output}")

    if args.normalize and snapshot:
        args.normalize.parent.mkdir(parents=True, exist_ok=True)
        args.normalize.write_text(json.dumps(snapshot, indent=2, default=str))
        print(
            f"Normalized snapshot: {args.normalize} "
            f"({snapshot['metadata']['capture_count']} captures -> "
            f"{snapshot['metadata']['unique_endpoint_count']} unique endpoints)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
