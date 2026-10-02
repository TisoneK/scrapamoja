"""Skin fallback: ids the primary skin failed to fetch are recovered elsewhere."""
import argparse
import asyncio

import src.sites.betb2b as pkg
from src.sites.betb2b import store
from src.sites.betb2b.cli import main as cli
from src.sites.betb2b.extraction.models import Event, Sport


def _event(eid):
    return Event(event_id=eid, sport=Sport.BASKETBALL, competition="L", home="A", away="B")


def test_failed_ids_recovered_on_fallback_skin_in_order(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    served = {"melbet": {"1"}, "22bet": {"1", "2"}}        # melbet only has id 1
    asked = []

    class FakeScraper:
        def __init__(self, skin, **kw):
            self.skin = skin

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def fetch_events(self, ids):
            asked.append((self.skin.name, list(ids)))
            return [_event(i) for i in ids if i in served[self.skin.name]]

    monkeypatch.setattr(pkg, "BetB2BScraper", FakeScraper)
    db = str(tmp_path / "o.db")
    args = argparse.Namespace(sport="basketball", action="list_prematch")

    asyncio.run(cli._fallback_fetch(["1", "2", "3"], ["melbet", "22bet"], args, db, "betwinner"))

    # each fallback skin is asked only for what is still missing
    assert asked == [("melbet", ["1", "2", "3"]), ("22bet", ["2", "3"])]
    conn = store.init_db(db)
    ids = {r[0] for r in conn.execute("SELECT event_id FROM events")}
    assert ids == {"1", "2"}                               # "3" stays unstored → retried next run


def test_fallback_without_skins_only_reports(tmp_path, capsys):
    args = argparse.Namespace(sport="basketball", action="list_prematch")
    asyncio.run(cli._fallback_fetch(["9"], [], args, str(tmp_path / "o.db"), "betwinner"))
    assert "--fallback-skins" in capsys.readouterr().err
