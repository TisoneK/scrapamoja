"""Tests for the Linebet snapshot normalizer + diff tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.sites.linebet.snapshots.normalize import (
    normalize_captured_response,
    normalize_capture_list,
)
from src.sites.linebet.snapshots.diff import diff_snapshots

SNAPSHOTS_DIR = Path(__file__).parent.parent / "snapshots"


# ---------------------------------------------------------------------------
# normalize_captured_response
# ---------------------------------------------------------------------------
class TestNormalizeCapturedResponse:
    def _make_cap(self, **overrides):
        defaults = {
            "url": "https://linebet.com/bff-api/config/group/get?groups=b.core&lang=en&d=linebet.com&g=HK&p=650&_t=12345",
            "status": 200,
            "method": "GET",
            "request_headers": {
                "x-svc-source": "__MAIN_APP__",
                "x-app-n": "__MAIN_APP__",
                "x-requested-with": "XMLHttpRequest",
                "is-srv": "false",
                "content-type": "application/json",
                "accept": "application/json",
                "accept-language": "en-US,en;q=0.9",
                "user-agent": "Mozilla/5.0 ...",
                "cookie": "session=abc123; csrf=xyz",
                "sec-ch-ua": '"Chromium";v="124"',
                "referer": "https://linebet.com/en",
            },
            "response_headers": {"content-type": "application/json"},
            "body": '{"counters": [], "ts": 1700000000, "settings": {}}',
        }
        defaults.update(overrides)
        return defaults

    def test_redacts_volatile_query_params(self):
        cap = self._make_cap()
        norm = normalize_captured_response(**cap)
        assert norm["query"]["_t"] == "<redacted>"
        # env-specific params also redacted
        assert norm["query"]["d"] == "<env>"
        assert norm["query"]["g"] == "<env>"
        assert norm["query"]["p"] == "<env>"
        assert norm["query"]["lang"] == "<env>"
        # Stable params kept
        assert norm["query"]["groups"] == "b.core"

    def test_redacts_volatile_json_keys(self):
        cap = self._make_cap(body='{"ts": 1700000000, "token": "abc", "data": [1,2,3]}')
        norm = normalize_captured_response(**cap)
        assert norm["body"]["ts"] == "<redacted>"
        assert norm["body"]["token"] == "<redacted>"
        assert norm["body"]["data"] == [1, 2, 3]

    def test_redacts_volatile_json_keys_nested(self):
        body = '{"user": {"sessionId": "abc", "name": "John"}, "events": [{"id": 1, "traceId": "x"}]}'
        cap = self._make_cap(body=body)
        norm = normalize_captured_response(**cap)
        assert norm["body"]["user"]["sessionId"] == "<redacted>"
        assert norm["body"]["user"]["name"] == "John"
        assert norm["body"]["events"][0]["traceId"] == "<redacted>"
        assert norm["body"]["events"][0]["id"] == 1

    def test_request_header_keys_filtered(self):
        cap = self._make_cap()
        norm = normalize_captured_response(**cap)
        # signal headers kept (as keys only, values not in output)
        assert "x-svc-source" in norm["request_header_keys"]
        assert "x-app-n" in norm["request_header_keys"]
        assert "x-requested-with" in norm["request_header_keys"]
        assert "is-srv" in norm["request_header_keys"]
        # noise headers dropped
        assert "user-agent" not in norm["request_header_keys"]
        assert "cookie" not in norm["request_header_keys"]
        assert not any(k.startswith("sec-ch-ua") for k in norm["request_header_keys"])

    def test_fatman_api_hash_stripped_from_path(self):
        url = "https://linebet.com/fatman-api/a6f69e4388362d761ee5bb073edb23ae3d9341fb/event.json"
        cap = self._make_cap(url=url)
        norm = normalize_captured_response(**cap)
        assert "<hash>" in norm["path"]
        assert "a6f69e43" not in norm["path"]

    def test_body_sha256_stable(self):
        cap = self._make_cap()
        n1 = normalize_captured_response(**cap)
        n2 = normalize_captured_response(**cap)
        assert n1["body_sha256"] == n2["body_sha256"]

    def test_body_sha256_changes_when_body_changes(self):
        cap1 = self._make_cap(body='{"a": 1}')
        cap2 = self._make_cap(body='{"a": 2}')
        n1 = normalize_captured_response(**cap1)
        n2 = normalize_captured_response(**cap2)
        assert n1["body_sha256"] != n2["body_sha256"]

    def test_body_sha256_ignores_volatile_keys(self):
        # Two bodies that differ only in their `ts` field should hash the same
        cap1 = self._make_cap(body='{"ts": 1700000000, "data": [1,2,3]}')
        cap2 = self._make_cap(body='{"ts": 1800000000, "data": [1,2,3]}')
        n1 = normalize_captured_response(**cap1)
        n2 = normalize_captured_response(**cap2)
        assert n1["body_sha256"] == n2["body_sha256"]

    def test_non_json_body_kept_as_truncated_string(self):
        cap = self._make_cap(
            body="<html><body>not json</body></html>",
            response_headers={"content-type": "text/html"},
        )
        norm = normalize_captured_response(**cap)
        assert isinstance(norm["body"], str)
        assert "not json" in norm["body"]

    def test_long_body_truncated(self):
        long_body = "x" * 20000
        cap = self._make_cap(body=long_body, response_headers={"content-type": "text/plain"})
        norm = normalize_captured_response(**cap)
        assert len(norm["body"]) < 20000
        assert "truncated" in norm["body"]
        assert norm["body_bytes"] == 20000


# ---------------------------------------------------------------------------
# normalize_capture_list
# ---------------------------------------------------------------------------
class TestNormalizeCaptureList:
    def test_dedup_same_endpoint_called_multiple_times(self):
        cap = {
            "url": "https://linebet.com/bff-api/config/group/get?groups=b.core",
            "status": 200,
            "method": "GET",
            "request_headers": {},
            "response_headers": {"content-type": "application/json"},
            "body": '{"a": 1}',
        }
        # Same endpoint called 5x — should dedup to 1
        bundle = normalize_capture_list([cap] * 5)
        assert bundle["metadata"]["capture_count"] == 5
        assert bundle["metadata"]["unique_endpoint_count"] == 1
        assert len(bundle["endpoints"]) == 1

    def test_endpoints_sorted_by_path(self):
        caps = [
            {"url": "https://linebet.com/bff-api/zzz", "status": 200, "method": "GET",
             "request_headers": {}, "response_headers": {}, "body": ""},
            {"url": "https://linebet.com/bff-api/aaa", "status": 200, "method": "GET",
             "request_headers": {}, "response_headers": {}, "body": ""},
        ]
        bundle = normalize_capture_list(caps)
        paths = [e["path"] for e in bundle["endpoints"]]
        assert paths == sorted(paths)

    def test_metadata_shape(self):
        bundle = normalize_capture_list([])
        assert "normalized_at" in bundle["metadata"]
        assert bundle["metadata"]["normalizer_version"] == "1.0.0"
        assert bundle["metadata"]["capture_count"] == 0
        assert bundle["metadata"]["unique_endpoint_count"] == 0
        assert bundle["endpoints"] == []


# ---------------------------------------------------------------------------
# diff_snapshots
# ---------------------------------------------------------------------------
class TestDiffSnapshots:
    def _snap(self, endpoints):
        return {
            "metadata": {"normalizer_version": "1.0.0"},
            "endpoints": endpoints,
        }

    def _ep(self, path, method="GET", sha="abc", body_bytes=100):
        return {"path": path, "method": method, "status": 200, "query": {},
                "content_type": "application/json", "request_header_keys": [],
                "body": {}, "body_sha256": sha, "body_bytes": body_bytes}

    def test_no_drift(self):
        old = self._snap([self._ep("https://x/a", sha="h1")])
        new = self._snap([self._ep("https://x/a", sha="h1")])
        d = diff_snapshots(old, new)
        assert d["added"] == []
        assert d["removed"] == []
        assert d["changed"] == []
        assert d["stable_count"] == 1

    def test_added_endpoint(self):
        old = self._snap([])
        new = self._snap([self._ep("https://x/a")])
        d = diff_snapshots(old, new)
        assert len(d["added"]) == 1
        assert d["stable_count"] == 0

    def test_removed_endpoint(self):
        old = self._snap([self._ep("https://x/a")])
        new = self._snap([])
        d = diff_snapshots(old, new)
        assert len(d["removed"]) == 1

    def test_changed_body(self):
        old = self._snap([self._ep("https://x/a", sha="old", body_bytes=100)])
        new = self._snap([self._ep("https://x/a", sha="new", body_bytes=150)])
        d = diff_snapshots(old, new)
        assert len(d["changed"]) == 1
        assert d["changed"][0]["old_sha"] == "old"
        assert d["changed"][0]["new_sha"] == "new"
        assert d["changed"][0]["old_body_bytes"] == 100
        assert d["changed"][0]["new_body_bytes"] == 150


# ---------------------------------------------------------------------------
# Committed-snapshot regression test
# ---------------------------------------------------------------------------
class TestCommittedSnapshotsAreValid:
    """Ensure the committed snapshots in snapshots/normalized/ are valid JSON
    in the expected shape. Catches accidentally-corrupted snapshot files."""

    @pytest.mark.parametrize("snapshot_name", [
        "waf_block_page_api_snapshot.json",
        "chrome_124_linux_full_capture.json",
    ])
    def test_snapshot_is_valid(self, snapshot_name: str):
        path = SNAPSHOTS_DIR / "normalized" / snapshot_name
        if not path.exists():
            pytest.skip(f"snapshot {snapshot_name} not present")
        data = json.loads(path.read_text())
        assert "metadata" in data
        assert "endpoints" in data
        assert data["metadata"]["normalizer_version"] == "1.0.0"
        for ep in data["endpoints"]:
            for required in ("path", "method", "status", "body_sha256"):
                assert required in ep, f"endpoint missing {required}: {ep}"

    def test_snapshot_endpoints_are_unique(self):
        """No duplicate endpoint keys in a committed snapshot."""
        path = SNAPSHOTS_DIR / "normalized" / "waf_block_page_api_snapshot.json"
        if not path.exists():
            pytest.skip("snapshot not present")
        data = json.loads(path.read_text())
        keys = []
        for ep in data["endpoints"]:
            keys.append(f"{ep['method']} {ep['path']}?{json.dumps(ep.get('query', {}), sort_keys=True)}")
        assert len(keys) == len(set(keys)), "duplicate endpoint keys in snapshot"
