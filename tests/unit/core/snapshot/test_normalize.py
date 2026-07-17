"""Framework-level tests for the snapshot normalizer.

Site-agnostic — tests the normalizer in isolation, with no Linebet
imports. The same normalizer is used by all sites.
"""

from __future__ import annotations

import json

import pytest

from src.core.snapshot.normalize import (
    DEFAULT_NORMALIZER_CONFIG,
    NormalizerConfig,
    normalize_captured_response,
    normalize_capture_list,
)


def _make_cap(**overrides):
    defaults = {
        "url": "https://example.com/api/list?groups=b.core&lang=en&d=example.com&g=US&p=42&_t=12345",
        "status": 200,
        "method": "GET",
        "request_headers": {
            "x-svc-source": "__MAIN_APP__",
            "x-requested-with": "XMLHttpRequest",
            "is-srv": "false",
            "content-type": "application/json",
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 ...",
            "cookie": "session=abc123; csrf=xyz",
            "sec-ch-ua": '"Chromium";v="124"',
            "referer": "https://example.com/",
        },
        "response_headers": {"content-type": "application/json"},
        "body": '{"counters": [], "ts": 1700000000, "settings": {}}',
    }
    defaults.update(overrides)
    return defaults


class TestNormalizeCapturedResponse:
    def test_redacts_volatile_query_params(self):
        cap = _make_cap()
        norm = normalize_captured_response(**cap)
        assert norm["query"]["_t"] == "<redacted>"

    def test_redacts_env_query_params(self):
        cap = _make_cap()
        norm = normalize_captured_response(**cap)
        assert norm["query"]["d"] == "<env>"
        assert norm["query"]["g"] == "<env>"
        assert norm["query"]["p"] == "<env>"
        assert norm["query"]["lang"] == "<env>"

    def test_keeps_stable_query_params(self):
        cap = _make_cap()
        norm = normalize_captured_response(**cap)
        assert norm["query"]["groups"] == "b.core"

    def test_redacts_volatile_json_keys_top_level(self):
        cap = _make_cap(body='{"ts": 1700000000, "token": "abc", "data": [1,2,3]}')
        norm = normalize_captured_response(**cap)
        assert norm["body"]["ts"] == "<redacted>"
        assert norm["body"]["token"] == "<redacted>"
        assert norm["body"]["data"] == [1, 2, 3]

    def test_redacts_volatile_json_keys_nested(self):
        body = '{"user": {"sessionId": "abc", "name": "John"}, "events": [{"id": 1, "traceId": "x"}]}'
        cap = _make_cap(body=body)
        norm = normalize_captured_response(**cap)
        assert norm["body"]["user"]["sessionId"] == "<redacted>"
        assert norm["body"]["user"]["name"] == "John"
        assert norm["body"]["events"][0]["traceId"] == "<redacted>"
        assert norm["body"]["events"][0]["id"] == 1

    def test_request_header_keys_filtered(self):
        cap = _make_cap()
        norm = normalize_captured_response(**cap)
        # signal headers kept (as keys only, values not in output)
        assert "x-svc-source" in norm["request_header_keys"]
        assert "x-requested-with" in norm["request_header_keys"]
        # noise headers dropped
        assert "user-agent" not in norm["request_header_keys"]
        assert "cookie" not in norm["request_header_keys"]
        assert not any(k.startswith("sec-ch-ua") for k in norm["request_header_keys"])

    def test_path_hash_redacted_default_patterns(self):
        # /fatman-api/<32+ hex>/... should become /fatman-api/<hash>/...
        url = "https://example.com/fatman-api/a6f69e4388362d761ee5bb073edb23ae3d9341fb/event.json"
        cap = _make_cap(url=url)
        norm = normalize_captured_response(**cap)
        assert "<hash>" in norm["path"]
        assert "a6f69e43" not in norm["path"]

    def test_body_sha256_stable(self):
        cap = _make_cap()
        n1 = normalize_captured_response(**cap)
        n2 = normalize_captured_response(**cap)
        assert n1["body_sha256"] == n2["body_sha256"]

    def test_body_sha256_changes_when_body_changes(self):
        cap1 = _make_cap(body='{"a": 1}')
        cap2 = _make_cap(body='{"a": 2}')
        n1 = normalize_captured_response(**cap1)
        n2 = normalize_captured_response(**cap2)
        assert n1["body_sha256"] != n2["body_sha256"]

    def test_body_sha256_ignores_volatile_keys(self):
        cap1 = _make_cap(body='{"ts": 1700000000, "data": [1,2,3]}')
        cap2 = _make_cap(body='{"ts": 1800000000, "data": [1,2,3]}')
        n1 = normalize_captured_response(**cap1)
        n2 = normalize_captured_response(**cap2)
        assert n1["body_sha256"] == n2["body_sha256"]

    def test_non_json_body_kept_as_truncated_string(self):
        cap = _make_cap(
            body="<html><body>not json</body></html>",
            response_headers={"content-type": "text/html"},
        )
        norm = normalize_captured_response(**cap)
        assert isinstance(norm["body"], str)
        assert "not json" in norm["body"]

    def test_long_body_truncated(self):
        long_body = "x" * 20000
        cap = _make_cap(body=long_body, response_headers={"content-type": "text/plain"})
        norm = normalize_captured_response(**cap)
        assert len(norm["body"]) < 20000
        assert "truncated" in norm["body"]
        assert norm["body_bytes"] == 20000


class TestNormalizerConfig:
    def test_custom_volatile_query_params(self):
        cfg = NormalizerConfig(volatile_query_params={"my_token"})
        cap = _make_cap(url="https://example.com/api?my_token=secret&keep=me")
        norm = normalize_captured_response(**cap, config=cfg)
        assert norm["query"]["my_token"] == "<redacted>"
        assert norm["query"]["keep"] == "me"

    def test_custom_path_hash_pattern(self):
        cfg = NormalizerConfig(path_hash_patterns=[r"(/custom/)[0-9a-f]{20,}"])
        url = "https://example.com/custom/abcdef0123456789abcdef0123456789abcdef01/resource"
        cap = _make_cap(url=url)
        norm = normalize_captured_response(**cap, config=cfg)
        assert "<hash>" in norm["path"]

    def test_case_insensitive_json_keys(self):
        # JSON keys are matched case-insensitively
        cap = _make_cap(body='{"SessionId": "abc", "TOKEN": "xyz", "name": "John"}')
        norm = normalize_captured_response(**cap)
        assert norm["body"]["SessionId"] == "<redacted>"
        assert norm["body"]["TOKEN"] == "<redacted>"
        assert norm["body"]["name"] == "John"

    def test_default_config_singleton_exists(self):
        assert DEFAULT_NORMALIZER_CONFIG is not None
        assert isinstance(DEFAULT_NORMALIZER_CONFIG, NormalizerConfig)


class TestNormalizeCaptureList:
    def test_dedup_same_endpoint_called_multiple_times(self):
        cap = _make_cap()
        bundle = normalize_capture_list([cap] * 5)
        assert bundle["metadata"]["capture_count"] == 5
        assert bundle["metadata"]["unique_endpoint_count"] == 1
        assert len(bundle["endpoints"]) == 1

    def test_endpoints_sorted_by_path(self):
        caps = [
            _make_cap(url="https://example.com/api/zzz"),
            _make_cap(url="https://example.com/api/aaa"),
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

    def test_uses_custom_config(self):
        cfg = NormalizerConfig(volatile_query_params={"my_token"})
        cap = _make_cap(url="https://example.com/api?my_token=secret")
        bundle = normalize_capture_list([cap], config=cfg)
        assert bundle["endpoints"][0]["query"]["my_token"] == "<redacted>"
