"""End-to-end tests for the HAR export + replay pipeline.

These tests use the committed synthetic HAR fixture
(``snapshots/raw/synthetic_prematch.har``) to verify that ``har_replay``
correctly decodes HAR bodies, runs the extractor, and produces a
normalized snapshot. They don't need a live browser or network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Make the scripts importable
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.sites.linebet.scripts.har_replay import _har_entries_to_captures  # noqa: E402
from src.sites.linebet.extraction.rules import LinebetExtractionRules  # noqa: E402
from src.sites.linebet.snapshots.normalize import normalize_capture_list  # noqa: E402


SNAPSHOTS_DIR = Path(__file__).parent.parent / "snapshots"
SYNTHETIC_HAR = SNAPSHOTS_DIR / "raw" / "synthetic_prematch.har"


@pytest.fixture
def synthetic_har() -> Dict[str, Any]:
    """Load the committed synthetic HAR fixture."""
    if not SYNTHETIC_HAR.exists():
        pytest.skip(f"synthetic HAR not present: {SYNTHETIC_HAR}")
    return json.loads(SYNTHETIC_HAR.read_text())


class TestHarReplayPipeline:
    def test_har_entries_to_captures_decodes_base64_body(self, synthetic_har):
        caps = _har_entries_to_captures(synthetic_har)
        # Synthetic HAR has 2 entries
        assert len(caps) == 2
        # First entry (prematch list) should have a decoded JSON body
        prematch_cap = next(c for c in caps if "/bff-api/sports/list/prematch" in c["url"])
        assert prematch_cap["status"] == 200
        assert prematch_cap["method"] == "GET"
        # Body should be valid JSON with a "Value" key
        body = json.loads(prematch_cap["body"])
        assert "Value" in body
        assert len(body["Value"]) == 1
        assert body["Value"][0]["Home"] == "Team Alpha"

    def test_har_replay_extracts_events(self, synthetic_har):
        """End-to-end: HAR entries -> captures -> extractor -> events."""
        caps = _har_entries_to_captures(synthetic_har)
        # Filter to Linebet API URLs (mirrors har_replay.main logic)
        api_caps = [
            c for c in caps
            if any(p in c["url"] for p in ("/bff-api/", "/fatman-api/", "/analytics-module-api/"))
        ]

        rules = LinebetExtractionRules()
        events: List[Dict[str, Any]] = []
        for cap in api_caps:
            decoded = rules.decode_captured_response(
                url=cap["url"],
                status=cap["status"],
                content_type=cap["response_headers"].get("content-type", ""),
                raw_bytes=cap["body"].encode("utf-8", errors="replace") if cap["body"] else None,
            )
            for event in rules.extract_from_captured(decoded):
                events.append(event.to_dict())

        # One event from the prematch entry; the fatman-api entry is noise.
        assert len(events) == 1
        ev = events[0]
        assert ev["home"] == "Team Alpha"
        assert ev["away"] == "Team Beta"
        assert ev["sport"] == "Football"
        assert ev["competition"] == "Synthetic Premier League"
        assert ev["event_id"] == "ev-har-001"
        # Flat 1X2 odds -> one market with 3 selections
        assert len(ev["markets"]) == 1
        assert ev["markets"][0]["market_type"] == "1x2"
        assert len(ev["markets"][0]["selections"]) == 3
        prices = {s["name"]: s["price"] for s in ev["markets"][0]["selections"]}
        assert prices == {"1": 2.10, "X": 3.30, "2": 3.50}

    def test_har_replay_can_normalize_to_snapshot(self, synthetic_har):
        """The captures from a HAR can be normalized into a stable snapshot."""
        caps = _har_entries_to_captures(synthetic_har)
        api_caps = [
            c for c in caps
            if any(p in c["url"] for p in ("/bff-api/", "/fatman-api/", "/analytics-module-api/"))
        ]
        snapshot = normalize_capture_list(api_caps)

        assert snapshot["metadata"]["normalizer_version"] == "1.0.0"
        assert snapshot["metadata"]["capture_count"] == 2
        # Two distinct endpoints (prematch + fatman event.json)
        assert snapshot["metadata"]["unique_endpoint_count"] == 2
        # Fatman hash should be redacted in the path (the synthetic HAR
        # uses a 40-char hex hash matching the real fatman-api shape)
        paths = [e["path"] for e in snapshot["endpoints"]]
        assert any("<hash>" in p for p in paths), f"fatman hash not redacted in paths: {paths}"
        # Env-specific query params redacted
        prematch = next(e for e in snapshot["endpoints"] if "prematch" in e["path"])
        assert prematch["query"]["d"] == "<env>"
        assert prematch["query"]["g"] == "<env>"
        assert prematch["query"]["p"] == "<env>"
