"""Evidence: blocked / unreachable requests leave a compact, normalised record automatically."""
import json
import os
import time

import pytest

from src.security import BETB2B_RULES, BlockLedger, EvidenceLog, SecurityGuard

GCORE = "<html><head><title>Gcore</title></head><body>Browser Validation Page</body></html>"


def guard(tmp_path):
    return SecurityGuard("betwinner", rules=BETB2B_RULES, interactive=False,
                         ledger=BlockLedger(tmp_path / "ledger.json"))


def records(g):
    return g.evidence.read(days=1)


def test_a_block_is_recorded_with_the_normalised_response(tmp_path):
    g = guard(tmp_path)
    v = g.inspect(200, "https://betwinner.com/service-api/LineFeed/GetSportsZip?lng=en&partner=1",
                  {"content-type": "text/html", "server": "gcore"}, GCORE)
    assert v.blocked
    (rec,) = records(g)
    assert rec["kind"] == "block" and rec["site"] == "betwinner"
    assert rec["verdict"]["type"] == "js_challenge" and rec["verdict"]["vendor"] == "gcore"
    assert rec["url"].endswith("/GetSportsZip") and "?" not in rec["url"]        # query not stored
    resp = rec["response"]                                                       # snapshot-system form
    assert resp["status"] == 200 and "Browser Validation" in resp["body"]
    assert len(resp["body_sha256"]) >= 16 and resp["body_bytes"] == len(GCORE)


def test_a_clean_response_leaves_no_evidence(tmp_path):
    g = guard(tmp_path)
    g.inspect(200, "https://x/feed", {"content-type": "application/json"}, '{"Success": true}')
    assert records(g) == []


def test_an_unreachable_request_records_the_error_and_url(tmp_path):
    g = guard(tmp_path)

    class ConnectTimeout(Exception):
        pass
    g.note_failure("stats", error=ConnectTimeout("timed out"), url="https://betwinner.com/a/b?id=1")
    (rec,) = records(g)
    assert rec["kind"] == "unreachable" and rec["scope"] == "stats"
    assert rec["error"].startswith("ConnectTimeout: timed out") and rec["url"] == "https://betwinner.com/a/b"


def test_identical_failures_are_stored_a_few_times_then_only_counted(tmp_path):
    g = guard(tmp_path)
    for _ in range(50):
        g.inspect(200, "https://x/feed", {"content-type": "text/html"}, GCORE)
    full = [r for r in records(g) if r["kind"] == "block"]
    assert len(full) == 3                                        # not 50 copies of the same page
    g.evidence.flush()
    summary = [r for r in records(g) if r["kind"] == "summary"]
    assert sum(summary[0]["repeats_not_stored"].values()) == 47  # nothing lost, just counted


def test_old_days_are_swept(tmp_path):
    d = tmp_path / "ev"
    d.mkdir()
    old = d / "evidence-20200101.jsonl"
    old.write_text("{}\n")
    os.utime(old, (time.time() - 30 * 86400,) * 2)
    EvidenceLog(d, keep_days=7).record("block", "s", url="u", status=403, body="x")
    assert not old.exists()


def test_summary_groups_what_is_going_wrong(tmp_path):
    g = guard(tmp_path)
    for _ in range(2):
        g.inspect(200, "https://x/a", {"content-type": "text/html"}, GCORE)
    g.note_failure(error=TimeoutError("t"), url="https://x/b")
    rows = EvidenceLog.summarise(records(g))
    kinds = {(r["kind"], r["type"] or r["error"]): r["count"] for r in rows}
    assert kinds[("block", "js_challenge")] == 2 and kinds[("unreachable", "TimeoutError")] == 1


def test_recording_never_raises(tmp_path):
    bad = EvidenceLog(tmp_path / "a-file")
    (tmp_path / "a-file").write_text("not a directory")           # mkdir will fail
    bad.record("block", "s", url="u", status=200, body=GCORE)      # must not raise
    bad.flush()


def test_cli_prints_the_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SCRAPAMOJA_EVIDENCE_DIR", str(tmp_path / "ev"))
    EvidenceLog(tmp_path / "ev").record("block", "betwinner", url="https://x/y", status=200, body=GCORE,
                                         verdict=SecurityGuard("betwinner", rules=BETB2B_RULES, interactive=False,
                                                               ledger=BlockLedger(tmp_path / "l.json"))
                                         .inspect(200, "https://x/y", {"content-type": "text/html"}, GCORE))
    from src.security.__main__ import main
    assert main(["evidence"]) == 0
    out = capsys.readouterr().out
    assert "betwinner" in out and "block" in out
