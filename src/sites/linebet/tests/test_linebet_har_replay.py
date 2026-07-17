"""End-to-end tests for the Linebet-specific HAR replay path.

These tests use the committed synthetic HAR fixture
(``snapshots/raw/synthetic_prematch.har``) to verify that the Linebet
extractor works correctly when fed via the framework's HAR replay
module (``src.network.har``). The framework-level HAR tests live in
``tests/unit/network/har/`` — this file only covers the Linebet-
specific integration.
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

# Framework imports (site-agnostic)
from src.network.har import HarReplayer  # noqa: E402
from src.network.har.to_snapshot import har_entries_to_captures  # noqa: E402
from src.core.snapshot.normalize import normalize_capture_list  # noqa: E402

# Linebet-specific imports
from src.sites.linebet.extraction.rules import LinebetExtractionRules  # noqa: E402
from src.sites.linebet.scripts.har_replay import _make_linebet_extractor  # noqa: E402


SNAPSHOTS_DIR = Path(__file__).parent.parent / "snapshots"
SYNTHETIC_HAR = SNAPSHOTS_DIR / "raw" / "synthetic_prematch.har"


@pytest.fixture
def synthetic_har() -> Dict[str, Any]:
    """Load the committed synthetic HAR fixture."""
    if not SYNTHETIC_HAR.exists():
        pytest.skip(f"synthetic HAR not present: {SYNTHETIC_HAR}")
    return json.loads(SYNTHETIC_HAR.read_text())


def _linebet_extractor():
    """Convenience: get the Linebet extractor callback."""
    return _make_linebet_extractor()


class TestLinebetHarReplayIntegration:
    def test_har_entries_to_captures_decodes_base64_body(self, synthetic_har):
        caps = har_entries_to_captures(synthetic_har)
        assert len(caps) == 2
        prematch_cap = next(c for c in caps if "/bff-api/sports/list/prematch" in c["url"])
        assert prematch_cap["status"] == 200
        body = json.loads(prematch_cap["body"])
        assert "Value" in body
        assert body["Value"][0]["Home"] == "Team Alpha"

    def test_linebet_extractor_via_har_replayer(self, synthetic_har, tmp_path):
        """End-to-end: HAR → HarReplayer → Linebet extractor → events."""
        har_path = tmp_path / "test.har"
        har_path.write_text(json.dumps(synthetic_har))

        replayer = HarReplayer(
            url_filter=["/bff-api/", "/fatman-api/", "/analytics-module-api/"],
        )
        result = replayer.replay(har_path, extractor=_linebet_extractor())

        # One event from the prematch entry; the fatman-api entry is noise.
        assert result.success
        assert result.total_har_entries == 2
        assert result.filtered_entries == 2
        assert result.event_count == 1

        ev = result.events[0]
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

    def test_har_replay_can_normalize_to_snapshot(self, synthetic_har, tmp_path):
        """The captures from a HAR can be normalized via the framework."""
        har_path = tmp_path / "test.har"
        har_path.write_text(json.dumps(synthetic_har))

        replayer = HarReplayer(
            url_filter=["/bff-api/", "/fatman-api/", "/analytics-module-api/"],
        )
        result, snapshot = replayer.replay_with_snapshot(har_path, extractor=_linebet_extractor())

        assert result.success
        assert snapshot is not None
        assert snapshot["metadata"]["normalizer_version"] == "1.0.0"
        assert snapshot["metadata"]["capture_count"] == 2
        # Two distinct endpoints (prematch + fatman event.json)
        assert snapshot["metadata"]["unique_endpoint_count"] == 2
        # Fatman hash should be redacted in the path (the synthetic HAR
        # uses the real 40-char fatman-api hash)
        paths = [e["path"] for e in snapshot["endpoints"]]
        assert any("<hash>" in p for p in paths), f"fatman hash not redacted in paths: {paths}"
        # Env-specific query params redacted
        prematch = next(e for e in snapshot["endpoints"] if "prematch" in e["path"])
        assert prematch["query"]["d"] == "<env>"
        assert prematch["query"]["g"] == "<env>"
        assert prematch["query"]["p"] == "<env>"
