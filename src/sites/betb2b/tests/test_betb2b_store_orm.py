"""ORM store path (ADR-13) exercised on SQLite via DATABASE_URL.

Setting ``DATABASE_URL`` routes ``store`` through :mod:`store_orm` (the same
code that writes Supabase Postgres in prod), so this verifies the ORM logic —
dialect upserts, change-only dedup, jobs, queries — without a Postgres server.
The Postgres dialect uses the identical statements and is verified live.
"""

from __future__ import annotations

import pytest

from src.sites.betb2b import store


@pytest.fixture
def orm_conn(tmp_path, monkeypatch):
    # Force the ORM path, but on SQLite so no server is needed. A fresh engine
    # per URL means the tmp file is isolated per test.
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'orm.db'}")
    import src.sites.betb2b.store_orm as som
    som._engines.clear()          # don't reuse an engine from another test's URL
    conn = store.init_db()
    yield conn
    conn.close()


def _rich_result(skin="linebet", at="2026-07-27T12:00:00+00:00"):
    return {
        "skin": skin, "action": "list_live", "url": "u", "extracted_at": at,
        "success": True, "event_count": 1, "scrape_duration_seconds": 1.0,
        "template_version": "1.0.0",
        "events": [{
            "event_id": "739052498", "sport": "basketball", "sport_id": 3,
            "competition": "PBA", "league_id": 850473, "home": "Nlex", "away": "San Miguel",
            "country": "Philippines", "start_time": "2026-07-27T13:00:00+00:00",
            "status": "live", "is_live": True, "score_home": 10, "score_away": 8,
            "period": "Q2", "home_team_feed_id": 51775, "away_team_feed_id": 7694,
            "home_team_image": "a.png", "away_team_image": "b.png",
            "home_team_country_id": 196, "away_team_country_id": 196,
            "venue": "Araneta", "stage": "Group A", "wp_home": 0.44, "wp_away": 0.56,
            "period_scores": [{"period_key": 18, "period_name": "Q1", "home_score": 22, "away_score": 20}],
            "markets": [{"name": "Total", "market_type": "total", "raw_g": 17, "scope": "FULL_MATCH",
                "selections": [
                    {"name": "Over", "price": 1.85, "line": 216.5, "is_suspended": False, "raw_t": 9},
                    {"name": "Under", "price": 1.95, "line": 216.5, "is_suspended": False, "raw_t": 10}]}],
            "h2h_data": {"sport_id": 3, "teams": [{"id": "abc", "title": "Nlex", "country": {"title": "Philippines"}}],
                "game_shorts": [{"game_id": "g1", "team1_id": "abc", "team2_id": "def",
                    "date_start": 1752183000, "score1": 81, "score2": 90,
                    "periods": [{"period_key": 18, "period_name": "Q1", "home_score": 15, "away_score": 22}]}]},
            "statistics": [{"rebounds": "40", "assists": "12"}],
        }],
    }


def test_init_db_returns_sqlalchemy_conn_when_database_url_set(orm_conn):
    assert type(orm_conn).__name__ == "Connection"  # SQLAlchemy, not sqlite3


def test_orm_persist_populates_all_tables(orm_conn):
    run_id = store.persist_result(_rich_result(), conn=orm_conn)
    assert run_id == 1
    c = store.counts(orm_conn)
    assert c == {
        "sports": 1, "countries": 1, "leagues": 1, "teams": 2, "events": 1,
        "markets": 1, "scrape_runs": 1, "event_states": 1, "period_scores": 1,
        "odds_snapshots": 2, "h2h_games": 1, "h2h_period_scores": 1, "statistics": 2,
    }


def test_orm_h2h_batch_links_periods_to_right_game(orm_conn):
    """Batched H2H insert must zip returned ids back to the correct game's
    periods. Two events, two distinct games with distinct period scores — each
    h2h_period_scores row must join to the game it belongs to."""
    def _ev(eid, gid, score1, ph):
        return {
            "event_id": eid, "sport": "basketball", "sport_id": 3,
            "competition": "PBA", "league_id": 850473, "home": f"H{eid}", "away": f"A{eid}",
            "h2h_data": {"sport_id": 3, "teams": [],
                "game_shorts": [{"game_id": gid, "team1_id": "t1", "team2_id": "t2",
                    "score1": score1, "score2": 0,
                    "periods": [{"period_key": 1, "period_name": "Q1",
                                 "home_score": ph, "away_score": 0}]}]},
        }
    result = {
        "skin": "linebet", "action": "list_live", "url": "u",
        "extracted_at": "2026-07-27T12:00:00+00:00", "success": True,
        "event_count": 2, "scrape_duration_seconds": 1.0, "template_version": "1.0.0",
        "events": [_ev("E1", "g1", 81, 15), _ev("E2", "g2", 90, 27)],
    }
    store.persist_result(result, conn=orm_conn)
    from sqlalchemy import text
    rows = orm_conn.execute(text(
        "SELECT g.score1, p.home_score FROM h2h_period_scores p "
        "JOIN h2h_games g ON g.id = p.h2h_game_id ORDER BY g.score1")).all()
    # game score1=81 → period home_score 15; score1=90 → 27 (not swapped)
    assert [(r[0], r[1]) for r in rows] == [(81, 15), (90, 27)]


def test_orm_change_only_dedup(orm_conn):
    store.persist_result(_rich_result(at="2026-07-27T12:00:00+00:00"), conn=orm_conn)
    store.persist_result(_rich_result(at="2026-07-27T12:00:05+00:00"), conn=orm_conn)
    # Identical odds → no new snapshot rows; two runs though.
    assert store.counts(orm_conn)["odds_snapshots"] == 2
    assert store.counts(orm_conn)["scrape_runs"] == 2


def test_orm_latest_odds(orm_conn):
    store.persist_result(_rich_result(), conn=orm_conn)
    rows = store.latest_odds(orm_conn, "739052498")
    assert {r["selection_name"] for r in rows} == {"Over", "Under"}
    over = next(r for r in rows if r["selection_name"] == "Over")
    assert over["price"] == 1.85 and over["line"] == 216.5


def test_orm_team_feed_fields_persisted(orm_conn):
    store.persist_result(_rich_result(), conn=orm_conn)
    from sqlalchemy import text
    row = orm_conn.execute(text(
        "SELECT feed_id, image, feed_country_id FROM teams WHERE name='Nlex'")).first()
    assert row[0] == 51775 and row[1] == "a.png" and row[2] == 196


def test_orm_job_lifecycle(orm_conn):
    jid = store.create_job(orm_conn, skin="linebet", action="list_live", sport="basketball")
    assert store.get_job(orm_conn, jid)["status"] == "queued"
    claimed = store.claim_next_job(orm_conn)
    assert claimed["status"] == "running" and claimed["phase"] == "starting"
    # single-flight
    store.create_job(orm_conn, skin="melbet", action="list_live")
    assert store.claim_next_job(orm_conn) is None
    store.update_job_phase(orm_conn, jid, "scraping events (3/10)")
    assert store.get_job(orm_conn, jid)["phase"] == "scraping events (3/10)"
    store.finish_job(orm_conn, jid, status="succeeded", run_id=1, event_count=1)
    done = store.get_job(orm_conn, jid)
    assert done["status"] == "succeeded" and done["phase"] == "done"


def test_orm_job_failure_keeps_phase(orm_conn):
    jid = store.create_job(orm_conn, skin="linebet", action="list_live")
    store.claim_next_job(orm_conn)
    store.update_job_phase(orm_conn, jid, "bootstrapping")
    store.finish_job(orm_conn, jid, status="failed", error="geo/WAF 203")
    row = store.get_job(orm_conn, jid)
    assert row["status"] == "failed" and row["phase"] == "bootstrapping"
