"""--skip-processed: already-stored events are not re-fetched."""
import time

from src.sites.betb2b import store


def _seed(path, event_id):
    conn = store.init_db(path)
    conn.execute(
        "INSERT INTO events (event_id, first_seen, last_seen) VALUES (?,?,?)",
        (event_id, "2026-01-01T00:00:00+00:00",
         time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())),
    )
    conn.commit()
    conn.close()


def test_skips_fresh_and_started_keeps_new(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    db = str(tmp_path / "o.db")
    _seed(db, "seen")
    future = time.time() + 3600
    pairs = [("seen", future), ("new", future), ("started", time.time() - 60)]
    assert store.unprocessed_ids(pairs, db) == ["new"]
    # default (inf) → anything ever stored is never re-fetched; 0 → always re-fetch
    assert store.unprocessed_ids(pairs, db, refresh_window=0) == ["seen", "new"]


def test_cli_parses_flags():
    from src.sites.betb2b.cli.main import BetB2BCLI
    p = BetB2BCLI().parser
    a = p.parse_args(["scrape", "linebet", "scheduled", "--skip-processed", "--no-db"])
    assert a.skip_processed == float('inf') and a.no_db


def test_skipping_processed_matches_is_the_default():
    from src.sites.betb2b.cli.main import BetB2BCLI
    p = BetB2BCLI().parser
    a = p.parse_args(["scrape", "linebet", "scheduled"])
    assert a.skip_processed == float("inf") and a.refetch is False
    assert p.parse_args(["scrape", "linebet", "scheduled", "--refetch"]).refetch is True
    assert p.parse_args(["scrape", "linebet", "scheduled", "--no-skip-processed"]).refetch is True
    assert p.parse_args(["scrape", "linebet", "scheduled", "--skip-processed", "3600"]).skip_processed == 3600.0
