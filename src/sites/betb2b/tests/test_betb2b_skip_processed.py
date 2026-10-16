"""--skip-processed: already-stored events are not re-fetched."""
import time
from datetime import datetime, timezone

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


def test_stored_match_with_failed_or_unattempted_totals_is_fetched_again(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    db = str(tmp_path / "o.db")
    long_ago = "2026-01-01T00:00:00+00:00"
    conn = store.init_db(db)
    conn.execute("INSERT INTO scrape_runs (skin, extracted_at) VALUES ('s', ?)", (long_ago,))
    for eid, status in (("failed", "fetch_failed"), ("untried", "not_attempted"),
                        ("complete", "offered"), ("none", None)):
        conn.execute("INSERT INTO events (event_id, first_seen, last_seen) VALUES (?,?,?)",
                     (eid, long_ago, long_ago))
        if status:
            conn.execute("INSERT INTO coverage (run_id,event_id,skin,dataset,subject,period,status,captured_at) "
                         "VALUES (1,?,?,?,?,?,?,?)", (eid, "s", "totals", "MATCH", "QUARTER_1", status, long_ago))
    conn.commit()
    conn.close()
    future = time.time() + 3 * 86400      # beyond the near-start horizon: only the retry rule applies
    pairs = [(e, future) for e in ("failed", "untried", "complete", "none", "new")]
    # stored long ago, so the incomplete ones come back; complete / unknown ones do not
    assert store.unprocessed_ids(pairs, db) == ["failed", "untried", "new"]
    # ...but not again straight away: a match just seen waits out the retry delay
    assert store.unprocessed_ids(pairs, db, retry_incomplete_after=10 ** 12) == ["new"]


def test_a_match_starting_soon_is_refetched_when_its_odds_are_an_hour_old(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    db = str(tmp_path / "o.db")
    seen = time.time() - 2 * 3600
    stamp = datetime.fromtimestamp(seen, timezone.utc).isoformat()
    conn = store.init_db(db)
    for eid in ("soon", "later"):
        conn.execute("INSERT INTO events (event_id, first_seen, last_seen) VALUES (?,?,?)", (eid, stamp, stamp))
    conn.commit()
    conn.close()
    now = time.time()
    pairs = [("soon", now + 5 * 3600), ("later", now + 3 * 86400)]
    # stored matches are otherwise never re-fetched; one that starts within the horizon is, once stale
    assert store.unprocessed_ids(pairs, db) == ["soon"]
    assert store.unprocessed_ids(pairs, db, near_refresh=10 ** 9) == []


# --------------------------------------------------------------------------- #
# per-skin basis (skin=): skip only what THIS skin stored
# --------------------------------------------------------------------------- #
def _seed_skin_event(db, event_id, skin, at):
    """Store ``event_id`` under ``skin``: events row + one event_states row."""
    conn = store.init_db(db)
    conn.execute("INSERT INTO events (event_id, first_seen, last_seen) VALUES (?,?,?)", (event_id, at, at))
    run_id = conn.execute("INSERT INTO scrape_runs (skin, extracted_at) VALUES (?,?)", (skin, at)).lastrowid
    conn.execute("INSERT INTO event_states (run_id, event_id, skin, captured_at) VALUES (?,?,?,?)",
                 (run_id, event_id, skin, at))
    conn.commit()
    conn.close()
    return run_id


def _persist_event(db, event_id, skin):
    """Persist one bare event under ``skin`` via the real persist path (either backend)."""
    at = datetime.now(timezone.utc).isoformat()   # fresh: otherwise the near-start rule re-fetches it
    conn = store.init_db(db)
    res = {"skin": skin, "action": "list_prematch", "url": "u", "extracted_at": at,
           "success": True, "event_count": 1, "scrape_duration_seconds": 1.0,
           "template_version": "1",
           "events": [{"event_id": event_id, "sport": "basketball", "sport_id": 3,
                       "competition": "L", "home": "A", "away": "B",
                       "status": "scheduled", "is_live": False}]}
    store.persist_result(res, db, conn=conn)
    conn.close()


def test_per_skin_basis_another_skins_match_is_still_fetched(tmp_path, monkeypatch):
    """Brands price their own odds: a match linebet stored is fetched for melbet;
    only linebet's own runs skip it."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    db = str(tmp_path / "o.db")
    now = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    _seed_skin_event(db, "stored_linebet", "linebet", now)
    future = time.time() + 3600
    pairs = [("stored_linebet", future), ("new", future)]
    # without skin: the match any skin stored is skipped (the raw cross-skin mode)
    assert store.unprocessed_ids(pairs, db) == ["new"]
    # with skin=melbet: melbet stored nothing → fetches it
    assert store.unprocessed_ids(pairs, db, skin="melbet") == ["stored_linebet", "new"]
    # with skin=linebet: still skipped for the skin that stored it
    assert store.unprocessed_ids(pairs, db, skin="linebet") == ["new"]


def test_per_skin_basis_on_the_orm_store(tmp_path, monkeypatch):
    """Same per-skin semantics through the ORM path (what Postgres runs)."""
    monkeypatch.delenv("BETB2B_STORE_MODE", raising=False)   # auto: DATABASE_URL resolves the store
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'orm.db'}")
    from src.sites.betb2b import store_orm

    store_orm._engines.clear()
    try:
        _persist_event(str(tmp_path / "ignored.db"), "stored_linebet", "linebet")
        future = time.time() + 3600
        pairs = [("stored_linebet", future), ("new", future)]
        local = str(tmp_path / "local.db")   # exists but empty: the ORM store holds the row
        assert store.unprocessed_ids(pairs, local) == ["new"]
        assert store.unprocessed_ids(pairs, local, skin="melbet") == ["stored_linebet", "new"]
        assert store.unprocessed_ids(pairs, local, skin="linebet") == ["new"]
    finally:
        store_orm._engines.clear()


def test_per_skin_incomplete_uses_this_skins_coverage(tmp_path, monkeypatch):
    """The incomplete-retry rule is per skin too: melbet re-fetches what MELBET's
    totals coverage shows failed; another skin's failed fetch is not melbet's."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    db = str(tmp_path / "o.db")
    long_ago = "2026-01-01T00:00:00+00:00"
    _seed_skin_event(db, "my_failed", "melbet", long_ago)
    _seed_skin_event(db, "other_failed", "melbet", long_ago)
    conn = store.init_db(db)
    conn.execute("INSERT INTO scrape_runs (skin, extracted_at) VALUES ('linebet', ?)", (long_ago,))
    linebet_run = conn.execute("SELECT MAX(run_id) FROM scrape_runs").fetchone()[0]
    conn.execute("INSERT INTO coverage (run_id,event_id,skin,dataset,subject,period,status,captured_at) "
                 "VALUES (1, 'my_failed', 'melbet', 'totals', 'MATCH', 'QUARTER_1', 'fetch_failed', ?)",
                 (long_ago,))
    conn.execute("INSERT INTO coverage (run_id,event_id,skin,dataset,subject,period,status,captured_at) "
                 "VALUES (?, 'other_failed', 'linebet', 'totals', 'MATCH', 'QUARTER_1', 'fetch_failed', ?)",
                 (linebet_run, long_ago))
    conn.commit()
    conn.close()
    future = time.time() + 3 * 86400      # beyond the near-start horizon: only the retry rule applies
    pairs = [(e, future) for e in ("my_failed", "other_failed", "new")]
    assert store.unprocessed_ids(pairs, db, skin="melbet") == ["my_failed", "new"]
    # without skin, the failed fetch by ANY skin keeps the event queued
    assert store.unprocessed_ids(pairs, db) == ["my_failed", "other_failed", "new"]
