"""Framework-level tests for the HAR module.

Site-agnostic — tests HAR loading, decoding, URL filtering, and
normalization. No Linebet imports.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from src.network.har import (
    HarReplayer,
    har_entries_to_captures,
    har_to_normalized_snapshot,
)
from src.network.har.to_snapshot import har_to_captured_responses


def _make_har(entries):
    """Build a minimal HAR dict with the given entries."""
    return {
        "log": {
            "version": "1.2",
            "creator": {"name": "test", "version": "0.1"},
            "entries": entries,
        }
    }


def _entry(url, body="", status=200, method="GET", content_type="application/json"):
    """Build a single HAR entry with a base64-encoded body."""
    body_b64 = base64.b64encode(body.encode()).decode() if body else ""
    return {
        "request": {
            "method": method,
            "url": url,
            "headers": [
                {"name": "x-svc-source", "value": "__MAIN_APP__"},
                {"name": "x-requested-with", "value": "XMLHttpRequest"},
                {"name": "cookie", "value": "session=abc"},
            ],
        },
        "response": {
            "status": status,
            "headers": [{"name": "content-type", "value": content_type}],
            "content": {
                "text": body_b64,
                "encoding": "base64" if body_b64 else "",
            },
        },
    }


class TestHarEntriesToCaptures:
    def test_decodes_base64_body(self):
        har = _make_har([_entry("https://x/api/list", body='{"a": 1}')])
        caps = har_entries_to_captures(har)
        assert len(caps) == 1
        assert caps[0]["body"] == '{"a": 1}'
        assert caps[0]["status"] == 200
        assert caps[0]["method"] == "GET"

    def test_flattens_headers_case_insensitively(self):
        har = _make_har([_entry("https://x/api/list")])
        caps = har_entries_to_captures(har)
        # Header names should be lowercased
        assert "x-svc-source" in caps[0]["request_headers"]
        assert "x-requested-with" in caps[0]["request_headers"]

    def test_handles_bodyless_responses(self):
        har = _make_har([_entry("https://x/api/noop", body="", status=204)])
        caps = har_entries_to_captures(har)
        assert caps[0]["body"] == ""
        assert caps[0]["status"] == 204

    def test_handles_plain_text_body(self):
        har = _make_har([_entry("https://x/api/text", body="hello world",
                                 content_type="text/plain")])
        caps = har_entries_to_captures(har)
        assert caps[0]["body"] == "hello world"


class TestHarToCapturedResponses:
    def test_produces_framework_captured_response_objects(self):
        har = _make_har([_entry("https://x/api/list", body='{"a": 1}')])
        resps = har_to_captured_responses(har)
        assert len(resps) == 1
        # Should be framework CapturedResponse instances
        assert hasattr(resps[0], "url")
        assert hasattr(resps[0], "status")
        assert hasattr(resps[0], "headers")
        assert hasattr(resps[0], "raw_bytes")
        assert resps[0].url == "https://x/api/list"
        assert resps[0].status == 200
        assert resps[0].raw_bytes == b'{"a": 1}'

    def test_bodyless_response_has_none_raw_bytes(self):
        har = _make_har([_entry("https://x/api/noop", body="", status=204)])
        resps = har_to_captured_responses(har)
        assert resps[0].raw_bytes is None


class TestHarToNormalizedSnapshot:
    def test_normalizes_without_url_filter(self):
        har = _make_har([
            _entry("https://x/api/list", body='{"a": 1}'),
            _entry("https://x/api/list", body='{"a": 1}'),  # duplicate -> deduped
        ])
        snap = har_to_normalized_snapshot(har)
        assert snap["metadata"]["capture_count"] == 2
        assert snap["metadata"]["unique_endpoint_count"] == 1

    def test_normalizes_with_url_filter(self):
        har = _make_har([
            _entry("https://x/api/list", body='{"a": 1}'),
            _entry("https://x/static/main.js", body="var x=1;"),
        ])
        snap = har_to_normalized_snapshot(har, url_filter=["/api/"])
        assert snap["metadata"]["capture_count"] == 1
        assert snap["metadata"]["unique_endpoint_count"] == 1
        assert "/api/list" in snap["endpoints"][0]["path"]

    def test_redacts_volatile_fields(self):
        har = _make_har([_entry(
            "https://x/api/list?_t=12345&lang=en",
            body='{"ts": 1700000000, "data": [1,2,3]}',
        )])
        snap = har_to_normalized_snapshot(har)
        ep = snap["endpoints"][0]
        assert ep["query"]["_t"] == "<redacted>"
        assert ep["body"]["ts"] == "<redacted>"
        assert ep["body"]["data"] == [1, 2, 3]
        # Cookie header should not appear in request_header_keys
        assert "cookie" not in ep["request_header_keys"]


class TestHarReplayer:
    def test_replay_no_filter_no_extractor(self):
        har = _make_har([_entry("https://x/api/list"), _entry("https://x/api/other")])
        path = Path("/tmp/test_har_replay.har")
        path.write_text(json.dumps(har))
        try:
            r = HarReplayer().replay(path)
            assert r.total_har_entries == 2
            assert r.filtered_entries == 2
            assert r.event_count == 0  # no extractor -> 0 events
            assert len(r.captured_responses) == 2
        finally:
            path.unlink()

    def test_replay_with_url_filter(self):
        har = _make_har([
            _entry("https://x/api/list"),
            _entry("https://x/static/main.js"),
        ])
        path = Path("/tmp/test_har_replay.har")
        path.write_text(json.dumps(har))
        try:
            r = HarReplayer(url_filter=["/api/"]).replay(path)
            assert r.total_har_entries == 2
            assert r.filtered_entries == 1
        finally:
            path.unlink()

    def test_replay_with_extractor(self):
        har = _make_har([_entry("https://x/api/list", body='{"a": 1}')])
        path = Path("/tmp/test_har_replay.har")
        path.write_text(json.dumps(har))
        try:
            def extractor(cap):
                return [{"url": cap["url"], "body_len": len(cap["body"])}]
            r = HarReplayer().replay(path, extractor=extractor)
            assert r.event_count == 1
            assert r.events[0]["url"] == "https://x/api/list"
            assert r.events[0]["body_len"] == 8  # '{"a": 1}'
        finally:
            path.unlink()

    def test_replay_missing_file_returns_error_result(self):
        r = HarReplayer().replay(Path("/tmp/does_not_exist.har"))
        assert r.error is not None
        assert "not found" in r.error
        assert r.success is False

    def test_replay_with_snapshot(self):
        har = _make_har([_entry("https://x/api/list", body='{"a": 1}')])
        path = Path("/tmp/test_har_replay.har")
        path.write_text(json.dumps(har))
        try:
            r, snap = HarReplayer().replay_with_snapshot(path)
            assert r.success
            assert snap is not None
            assert snap["metadata"]["unique_endpoint_count"] == 1
        finally:
            path.unlink()

    def test_extractor_exception_does_not_kill_replay(self):
        har = _make_har([_entry("https://x/api/list")])
        path = Path("/tmp/test_har_replay.har")
        path.write_text(json.dumps(har))
        try:
            def bad_extractor(cap):
                raise RuntimeError("intentional")
            r = HarReplayer().replay(path, extractor=bad_extractor)
            # Replay should complete; bad captures just produce 0 events
            assert r.success
            assert r.event_count == 0
        finally:
            path.unlink()
