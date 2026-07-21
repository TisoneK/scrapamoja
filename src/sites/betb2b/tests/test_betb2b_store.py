"""Tests for the SQLite odds store (src/sites/betb2b/store.py).

Verifies the three things loose JSON couldn't do: event dedup (UPSERT),
cross-skin comparison (join on shared event_id), and line movement (a price
time-series across runs).
"""

from __future__ import annotations

import pytest

from src.sites.betb2b.store import (
    cross_skin_odds,
    init_db,
    latest_odds,
    line_movement,
    persist_result,
)


def _result(skin, *, price_1x2, score=(10, 8), at="2026-07-21T12:00:00+00:00"):
    """A minimal BetB2BScrapeResult.to_dict()-shaped payload, one event."""
    return {
        "skin": skin,
        "action": "list_live",
        "url": f"https://{skin}.com/en/live/basketball",
        "extracted_at": at,
        "scrape_duration_seconds": 1.0,
        "success": True,
        "event_count": 1,
        "events": [
            {
                "event_id": "738047045",
                "sport": "basketball",
                "sport_id": 3,
                "competition": "Test League",
                "league_id": 99,
                "home": "Phoenix",
                "away": "Rain or Shine",
                "country": "PH",
                "start_time": None,
                "status": "live",
                "is_live": True,
                "score_home": score[0],
                "score_away": score[1],
                "minute": None,
                "period": "Q2",
                "markets": [
                    {
                        "name": "To Win Match",
                        "market_type": "moneyline_h2h",
                        "raw_g": 1,
                        "selections": [
                            {"name": "1", "price": price_1x2[0], "line": None,
                             "is_suspended": False, "raw_t": 1, "raw_g": 1},
                            {"name": "2", "price": price_1x2[1], "line": None,
                             "is_suspended": False, "raw_t": 2, "raw_g": 1},
                        ],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def db(tmp_path):
    conn = init_db(tmp_path / "odds.db")
    yield conn
    conn.close()


def test_schema_created(db):
    tables = {
        r["name"]
        for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"scrape_runs", "events", "event_states", "odds_snapshots"} <= tables


def test_persist_one_result(db, tmp_path):
    run_id = persist_result(_result("linebet", price_1x2=(1.5, 2.5)),
                            tmp_path / "odds.db", conn=db)
    assert run_id == 1
    assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM odds_snapshots").fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM event_states").fetchone()[0] == 1


def test_event_is_deduped_across_skins(db, tmp_path):
    # Same event_id reported by 3 skins → ONE events row, 3 state rows.
    for skin, price in [("linebet", (1.5, 2.5)),
                        ("melbet", (1.6, 2.4)),
                        ("helabet", (1.45, 2.6))]:
        persist_result(_result(skin, price_1x2=price), tmp_path / "odds.db", conn=db)

    assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM event_states").fetchone()[0] == 3
    assert db.execute("SELECT COUNT(*) FROM odds_snapshots").fetchone()[0] == 6


def test_cross_skin_odds_sorted_by_price(db, tmp_path):
    persist_result(_result("linebet", price_1x2=(1.5, 2.5)), tmp_path / "odds.db", conn=db)
    persist_result(_result("melbet", price_1x2=(1.6, 2.4)), tmp_path / "odds.db", conn=db)
    persist_result(_result("helabet", price_1x2=(1.45, 2.6)), tmp_path / "odds.db", conn=db)

    rows = cross_skin_odds(db, "738047045", "To Win Match", "1")
    assert [r["skin"] for r in rows] == ["helabet", "linebet", "melbet"]  # ascending price
    assert [r["price"] for r in rows] == [1.45, 1.5, 1.6]
    # Best (highest) price is last → the value bet.
    assert rows[-1]["skin"] == "melbet"


def test_line_movement_is_a_time_series(db, tmp_path):
    persist_result(_result("linebet", price_1x2=(1.5, 2.5),
                           at="2026-07-21T12:00:00+00:00"), tmp_path / "odds.db", conn=db)
    persist_result(_result("linebet", price_1x2=(1.7, 2.2),
                           at="2026-07-21T12:05:00+00:00"), tmp_path / "odds.db", conn=db)

    moves = line_movement(db, "738047045", "linebet", "To Win Match", "1")
    assert [m["price"] for m in moves] == [1.5, 1.7]  # drift over time, ordered
    assert moves[0]["captured_at"] < moves[1]["captured_at"]


def test_latest_odds_takes_most_recent(db, tmp_path):
    persist_result(_result("linebet", price_1x2=(1.5, 2.5),
                           at="2026-07-21T12:00:00+00:00"), tmp_path / "odds.db", conn=db)
    persist_result(_result("linebet", price_1x2=(1.9, 2.0),
                           at="2026-07-21T12:10:00+00:00"), tmp_path / "odds.db", conn=db)

    rows = latest_odds(db, "738047045", skin="linebet")
    prices = {r["selection_name"]: r["price"] for r in rows}
    # The store keeps every snapshot; latest_odds surfaces the newest capture.
    assert rows  # two selections
    assert max(r["captured_at"] for r in rows) == "2026-07-21T12:10:00+00:00"


# ---------------------------------------------------------------------------
# Full-model coverage: dimensions, period scores, H2H (the non-odds data)
# ---------------------------------------------------------------------------
from src.sites.betb2b.store import counts


def _rich_result(skin="linebet", at="2026-07-21T12:00:00+00:00"):
    """A result exercising sport/country/league/team/period/h2h — not just odds."""
    return {
        "skin": skin, "action": "list_live", "extracted_at": at,
        "success": True, "event_count": 1,
        "events": [{
            "event_id": "738047045", "sport": "Basketball", "sport_id": 3,
            "competition": "Philippines. Governors Cup", "league_id": 850473,
            "home": "Phoenix", "away": "Rain or Shine", "country": "Philippines",
            "start_time": "2026-07-21T11:30:00+00:00", "status": "live",
            "is_live": True, "score_home": 62, "score_away": 78,
            "minute": 32, "period": "3rd quarter",
            "period_scores": [
                {"period_key": 1, "period_name": "1st quarter", "home_score": 25, "away_score": 30},
                {"period_key": 2, "period_name": "2nd quarter", "home_score": 12, "away_score": 18},
            ],
            "markets": [{
                "name": "To Win Match", "market_type": "moneyline_h2h", "raw_g": 1,
                "selections": [{"name": "1", "price": 1.5, "line": None,
                                "is_suspended": False, "raw_t": 1, "raw_g": 1}],
            }],
            "h2h_data": {
                "sport_id": 3,
                "teams": [{"id": "hash_phoenix", "title": "Phoenix",
                           "country": {"title": "Philippines"}}],
                "game_shorts": [{"game_id": "g1", "team1_id": "hash_phoenix",
                                 "team2_id": "hash_other", "date_start": "2026-01-01T00:00:00+00:00",
                                 "score1": 88, "score2": 90, "winner": 2, "status": 1}],
            },
        }],
    }


def test_dimensions_populated(db, tmp_path):
    persist_result(_rich_result(), tmp_path / "odds.db", conn=db)
    c = counts(db)
    assert c["sports"] == 1
    assert c["countries"] == 1
    assert c["leagues"] == 1
    assert c["teams"] >= 2            # home + away (+ h2h enrichment merges by name)
    assert c["events"] == 1
    assert c["period_scores"] == 2
    assert c["h2h_games"] == 1


def test_event_joins_to_dimension_names(db, tmp_path):
    persist_result(_rich_result(), tmp_path / "odds.db", conn=db)
    row = db.execute(
        "SELECT s.name AS sport, l.name AS league, c.name AS country, "
        "       e.home_name, e.away_name "
        "FROM events e "
        "LEFT JOIN sports s ON s.sport_id=e.sport_id "
        "LEFT JOIN leagues l ON l.league_id=e.league_id "
        "LEFT JOIN countries c ON c.country_id=e.country_id "
        "WHERE e.event_id='738047045'"
    ).fetchone()
    assert row["sport"] == "Basketball"
    assert row["league"] == "Philippines. Governors Cup"
    assert row["country"] == "Philippines"
    assert row["home_name"] == "Phoenix"


def test_h2h_team_backend_id_enriches_teams(db, tmp_path):
    persist_result(_rich_result(), tmp_path / "odds.db", conn=db)
    # The event's "Phoenix" (name-only) is enriched with the h2h backend id.
    row = db.execute("SELECT backend_id FROM teams WHERE name='Phoenix'").fetchone()
    assert row["backend_id"] == "hash_phoenix"


def test_league_shared_across_skins_is_one_row(db, tmp_path):
    for skin in ("linebet", "melbet", "helabet"):
        persist_result(_rich_result(skin=skin), tmp_path / "odds.db", conn=db)
    c = counts(db)
    assert c["leagues"] == 1          # shared backend LI → one row
    assert c["events"] == 1           # shared event_id → one row
    assert c["scrape_runs"] == 3      # three observations
    assert c["h2h_games"] == 3        # one per skin's observation
