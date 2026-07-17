"""HAR replay — extract events from a recorded HAR file, no browser needed.

This is the **developer-side** half of the HAR export + replay pair.
Given a HAR file produced by ``har_export`` (or by a real browser's
DevTools "Save all as HAR"), this script:

  1. Filters entries to Linebet API URLs (``/bff-api/``, ``/fatman-api/``,
     ``/analytics-module-api/``).
  2. Decodes each response body (HAR bodies are base64-encoded).
  3. Runs the Linebet extractor against each decoded response.
  4. Optionally normalizes the captures into a stable snapshot.
  5. Writes a JSON result with events + capture summaries.

Run as:
    python -m src.sites.linebet.scripts.har_replay <input.har> <output.json> [options]

Options:
    --normalize PATH    Also write a normalized snapshot to PATH
    --pretty            Pretty-print the output JSON
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._common import ensure_repo_on_path

ensure_repo_on_path()

from src.sites.linebet.extraction.rules import LinebetExtractionRules  # noqa: E402
from src.sites.linebet.snapshots.normalize import normalize_capture_list  # noqa: E402


def _har_entries_to_captures(har: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert HAR entries into the capture-dict shape the extractor expects."""
    out: List[Dict[str, Any]] = []
    for entry in har.get("log", {}).get("entries", []):
        req = entry.get("request", {})
        resp = entry.get("response", {})
        url = req.get("url", "")

        # Decode body. HAR stores it under response.content.text, with
        # encoding under response.content.encoding ("base64" typically).
        content = resp.get("content", {})
        body_text: Optional[str] = None
        if content.get("text"):
            if content.get("encoding") == "base64":
                try:
                    raw = base64.b64decode(content["text"])
                    body_text = raw.decode("utf-8", errors="replace")
                except Exception:
                    body_text = "<base64 decode failed>"
            else:
                body_text = content["text"]

        # Flatten headers (HAR uses list of {name, value})
        req_headers = {h["name"].lower(): h["value"] for h in req.get("headers", [])}
        resp_headers = {h["name"].lower(): h["value"] for h in resp.get("headers", [])}

        out.append({
            "url": url,
            "status": resp.get("status", 0),
            "method": req.get("method", "GET"),
            "request_headers": req_headers,
            "response_headers": resp_headers,
            "body": body_text or "",
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", type=Path, help="Path to the HAR file")
    parser.add_argument("output", type=Path, help="Path to write the JSON result")
    parser.add_argument("--normalize", type=Path, default=None,
                        help="Also write a normalized snapshot to this path")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty-print JSON output")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1

    try:
        har = json.loads(args.input.read_text())
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid HAR JSON: {exc}", file=sys.stderr)
        return 1

    captures = _har_entries_to_captures(har)
    print(f"Loaded {len(captures)} entries from HAR", flush=True)

    # Filter to Linebet API URLs only
    api_captures = [
        c for c in captures
        if any(p in c["url"] for p in ("/bff-api/", "/fatman-api/", "/analytics-module-api/"))
    ]
    print(f"Filtered to {len(api_captures)} Linebet API entries", flush=True)

    # Run the extractor
    rules = LinebetExtractionRules()
    events: List[Dict[str, Any]] = []
    decoded_summaries: List[Dict[str, Any]] = []
    for cap in api_captures:
        decoded = rules.decode_captured_response(
            url=cap["url"],
            status=cap["status"],
            content_type=cap["response_headers"].get("content-type", ""),
            raw_bytes=cap["body"].encode("utf-8", errors="replace") if cap["body"] else None,
        )
        decoded_summaries.append(decoded.to_dict())
        # extract_from_captured returns Event dataclass instances —
        # serialize them to dicts for JSON output.
        for event in rules.extract_from_captured(decoded):
            events.append(event.to_dict())

    print(f"Extracted {len(events)} events from {len(decoded_summaries)} captures", flush=True)

    result: Dict[str, Any] = {
        "action": "har_replay",
        "input": str(args.input),
        "total_har_entries": len(captures),
        "linebet_api_entries": len(api_captures),
        "event_count": len(events),
        "captured_response_count": len(decoded_summaries),
        "events": events,
        "captured_responses": decoded_summaries,
        "extraction_source": "linebet_scraper_har_replay",
        "template_version": "1.0.0",
    }

    indent = 2 if args.pretty else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=indent, default=str))
    print(f"\nWrote: {args.output}", flush=True)

    if args.normalize:
        snapshot = normalize_capture_list(api_captures)
        args.normalize.parent.mkdir(parents=True, exist_ok=True)
        args.normalize.write_text(json.dumps(snapshot, indent=2, default=str))
        print(f"Normalized snapshot: {args.normalize}", flush=True)
        print(
            f"  {snapshot['metadata']['capture_count']} captures -> "
            f"{snapshot['metadata']['unique_endpoint_count']} unique endpoints",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
