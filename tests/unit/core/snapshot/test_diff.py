"""Framework-level tests for the snapshot diff tool."""

from __future__ import annotations

import pytest

from src.core.snapshot.diff import diff_snapshots


def _snap(endpoints):
    return {"metadata": {"normalizer_version": "1.0.0"}, "endpoints": endpoints}


def _ep(path, method="GET", sha="abc", body_bytes=100, query=None):
    return {
        "path": path, "method": method, "status": 200,
        "query": query or {}, "content_type": "application/json",
        "request_header_keys": [], "body": {}, "body_sha256": sha,
        "body_bytes": body_bytes,
    }


class TestDiffSnapshots:
    def test_no_drift(self):
        old = _snap([_ep("https://x/a", sha="h1")])
        new = _snap([_ep("https://x/a", sha="h1")])
        d = diff_snapshots(old, new)
        assert d["added"] == []
        assert d["removed"] == []
        assert d["changed"] == []
        assert d["stable_count"] == 1

    def test_added_endpoint(self):
        old = _snap([])
        new = _snap([_ep("https://x/a")])
        d = diff_snapshots(old, new)
        assert len(d["added"]) == 1
        assert d["stable_count"] == 0

    def test_removed_endpoint(self):
        old = _snap([_ep("https://x/a")])
        new = _snap([])
        d = diff_snapshots(old, new)
        assert len(d["removed"]) == 1

    def test_changed_body(self):
        old = _snap([_ep("https://x/a", sha="old", body_bytes=100)])
        new = _snap([_ep("https://x/a", sha="new", body_bytes=150)])
        d = diff_snapshots(old, new)
        assert len(d["changed"]) == 1
        assert d["changed"][0]["old_sha"] == "old"
        assert d["changed"][0]["new_sha"] == "new"
        assert d["changed"][0]["old_body_bytes"] == 100
        assert d["changed"][0]["new_body_bytes"] == 150

    def test_different_query_treated_as_different_endpoint(self):
        old = _snap([_ep("https://x/a", query={"groups": "old"})])
        new = _snap([_ep("https://x/a", query={"groups": "new"})])
        d = diff_snapshots(old, new)
        # Same path, different query -> treated as removed + added
        assert len(d["removed"]) == 1
        assert len(d["added"]) == 1
        assert d["stable_count"] == 0

    def test_totals(self):
        old = _snap([_ep("https://x/a"), _ep("https://x/b")])
        new = _snap([_ep("https://x/b"), _ep("https://x/c")])
        d = diff_snapshots(old, new)
        assert d["old_total"] == 2
        assert d["new_total"] == 2
        assert d["stable_count"] == 1  # /x/b
        assert len(d["removed"]) == 1  # /x/a
        assert len(d["added"]) == 1    # /x/c
