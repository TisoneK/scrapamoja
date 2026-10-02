"""Offline end-to-end: recorded feed responses -> the REAL scraper (discovery ->
fetch -> extract) -> persist -> relist linking -> second-pass skip -> engine export.

No network. The only fakes are the three feed calls (GetSportsZip / GetChampZip /
GetGameZip) and the statisticfeed enrichments, so nothing here touches the sites
(whose endpoints are costly to rediscover and shouldn't be burned by tests).
"""
import asyncio
import copy
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.sites.betb2b import store
from src.sites.betb2b.cli.main import _load_skin
from src.sites.betb2b.export.scorewise import build_ingest_matches
from src.sites.betb2b.scraper import BetB2BScraper

FIX = Path(__file__).parent / "fixtures" / "getgamezip_basketball.json"


class _Cap:
    """Stand-in for CapturedFeedResponse (only what the scraper/result touch)."""
    def __init__(self, decoded, status=200):
        self.status, self.decoded, self.url = status, decoded, "https://x/feed"

    def to_dict(self):
        return {"url": self.url, "status": self.status}


def _cap(decoded, status=200):
    return _Cap(decoded, status)


@pytest.fixture
def feed():
    """A tiny recorded 'site': one league, three listed games."""
    base = json.loads(FIX.read_text())["Value"]
    start = int(time.time()) + 7200

    def game(gid, **over):
        g = copy.deepcopy(base)
        g.update(I=gid, S=start, **over)
        return g

    real = game(900000001)
    real["SG"] = [{"I": 900000002, "PN": "1st quarter", "P": 1, "EC": 10, "SI": 3},
                  {"I": 900000003, "TG": "", "PN": "", "EC": 1, "SI": 3}]      # unlabelled special
    games = {
        "900000001": real,                              # the real match
        "900000003": game(900000003, SG=[]),            # the special group, ALSO listed as a "game"
    }
    games["900000003"]["O1"], games["900000003"]["O2"] = real["O1"], real["O2"]
    return games, start


def _q(conn):
    """Run raw SQL on either store flavour (sqlite3 connection or SQLAlchemy connection)."""
    def run(sql):
        if store._is_orm(conn):
            from sqlalchemy import text
            return [tuple(r) for r in conn.execute(text(sql))]
        return [tuple(r) for r in conn.execute(sql)]
    return run


def _patch(scraper, games, start):
    async def sports(root="line"):
        return _cap({"Success": True, "Value": [{"I": 3, "L": [{"LI": 1, "GC": len(games), "L": "League"}]}]})

    async def champ(li, root="line"):
        return _cap({"Success": True, "Value": {"G": [{"I": int(i), "S": start} for i in games]}})

    async def game(eid, root="line", **kw):
        return _cap({"Success": True, "Value": games[str(eid)]})

    async def blocked(*a, **k):
        return _cap(None, status=0)

    async def noop(*a, **k):
        return None

    scraper.feed_client.fetch_sports = sports
    scraper.feed_client.fetch_champ = champ
    scraper.feed_client.fetch_game = game
    scraper.feed_client.fetch = blocked              # list feed unusable -> direct discovery path
    scraper._enrich_with_h2h = scraper._enrich_with_stats = scraper._enrich_with_stat_ids = noop
    scraper._enrich_with_subgames = noop


@pytest.mark.parametrize("backend", ["sqlite-file", "orm"])   # raw SQLite store AND the Postgres-path ORM store
def test_pipeline_end_to_end(tmp_path, monkeypatch, feed, backend):
    games, start = feed
    db = str(tmp_path / "e2e.db")
    if backend == "orm":     # same code path Neon uses (store_orm), on a throwaway SQLite URL
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
        monkeypatch.setenv("BETB2B_STORE_MODE", "auto")
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("BETB2B_STORE_MODE", "local")

    # ---- run 1: discover -> fetch -> extract -> persist --------------------
    async def run(filter_):
        s = BetB2BScraper(_load_skin("betwinner"), sport="basketball", direct=True, id_filter=filter_)
        _patch(s, games, start)
        return await s.scrape(action="list_prematch")

    result = asyncio.run(run(None))
    assert result["success"] and not result.get("error")
    ids = {e["event_id"] for e in result["events"]}
    assert ids == {"900000001"}, ids                        # the special group is NOT stored as a match
    ev = result["events"][0]
    assert ev["home"] and ev["away"] and ev["markets"]      # teams + markets extracted

    store.persist_result(result, db)
    conn = store.init_db(db)
    q = _q(conn)
    assert q("SELECT COUNT(*) FROM events")[0][0] == 1
    assert q("SELECT COUNT(*) FROM odds_snapshots")[0][0] > 10
    sub = {r[0] for r in q("SELECT sub_game_id FROM sub_games")}
    assert sub == {"900000002", "900000003"}                # incl. the unlabelled one

    # ---- run 2: skip-processed fetches nothing (matches AND sub-games known) ----
    flt = lambda pairs: store.unprocessed_ids(pairs, db)
    result2 = asyncio.run(run(flt))
    assert result2["event_count"] == 0 and not result2.get("error")

    # ---- the bookmaker re-lists the match under a new id ------------------
    relist = copy.deepcopy(games["900000001"])
    relist["I"] = 900000010
    games2 = {"900000010": relist}
    s = BetB2BScraper(_load_skin("betwinner"), sport="basketball", direct=True)
    _patch(s, games2, start)
    result3 = asyncio.run(s.scrape(action="list_prematch"))
    store.persist_result(result3, db)
    rows = dict(map(tuple, q("SELECT event_id, superseded_by FROM events")))
    assert rows == {"900000001": "900000010", "900000010": None}   # linked, nothing deleted

    # ---- export: stored/extracted event -> engine PredictRequests ----------
    matches = build_ingest_matches(result["events"])
    assert matches and all(m["match_id"] == "900000001" for m in matches)
    assert all(m["odds"].get("match_total") is not None for m in matches)


def test_blocked_site_is_a_failed_run_not_an_empty_success(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    s = BetB2BScraper(_load_skin("betwinner"), sport="basketball", direct=True)

    async def blocked(*a, **k):
        return _cap(None)   # WAF challenge page: 200 but not JSON

    s.feed_client.fetch = s.feed_client.fetch_sports = blocked
    result = asyncio.run(s.scrape(action="list_prematch"))
    assert result["success"] is False and "blocked" in result["error"]
    db = str(tmp_path / "x.db")
    store.persist_result(result, db)
    ok = store.init_db(db).execute("SELECT success FROM scrape_runs").fetchone()[0]
    assert not ok
