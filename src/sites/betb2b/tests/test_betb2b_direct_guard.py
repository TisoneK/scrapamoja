"""The scraper's direct httpx calls (H2H, stats, result fetch, landing harvest) go through
the same security guard as the feed client: a challenge there is classified, rests the
skin, and stops the batch instead of being parsed as data once per match."""
import asyncio

import httpx
import pytest

from src.security import BETB2B_RULES, BlockLedger, SecurityGuard, SiteBlocked
from src.sites.betb2b.config import BetB2BSkinConfig
from src.sites.betb2b.extraction.models import Event, Sport
from src.sites.betb2b.scraper import BetB2BScraper

GCORE = "<html><head><title>Gcore</title></head><body>Browser Validation</body></html>"
REAL_CLIENT = httpx.AsyncClient


@pytest.fixture(autouse=True)
def _dirs(monkeypatch, tmp_path):
    monkeypatch.setenv("SCRAPAMOJA_SECURITY_DIR", str(tmp_path / "sec"))
    monkeypatch.setenv("SCRAPAMOJA_PROFILE_DIR", str(tmp_path / "prof"))


def make_scraper(tmp_path):
    skin = BetB2BSkinConfig.from_yaml("src/sites/betb2b/skins/linebet.yaml")
    s = BetB2BScraper(skin, direct=True)
    s.session_manager.guard = SecurityGuard(
        skin.name, rules=BETB2B_RULES, interactive=False, has_browser=False,
        ledger=BlockLedger(tmp_path / "ledger.json"))
    return s


def serve(monkeypatch, handler):
    """Make every direct httpx.AsyncClient in the scraper talk to ``handler`` (no network)."""
    def factory(**kw):
        kw.pop("proxy", None)
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **kw)
    monkeypatch.setattr(httpx, "AsyncClient", factory)


def events(n):
    return [Event(event_id=str(1000 + i), sport=Sport.BASKETBALL, competition="L",
                  home="A", away="B") for i in range(n)]


def test_challenge_on_h2h_stops_the_batch(monkeypatch, tmp_path):
    s, hits = make_scraper(tmp_path), []

    def handler(req):
        hits.append(1)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=GCORE)

    serve(monkeypatch, handler)
    asyncio.run(s._enrich_with_h2h(events(40)))
    assert len(hits) <= s.concurrency        # only the requests already in flight, never 40
    left, _ = s.session_manager.guard.ledger.cooldown_left(s.skin.name)
    assert left > 0                           # and the skin is resting


def test_challenge_on_stats_stops_the_batch(monkeypatch, tmp_path):
    s, hits = make_scraper(tmp_path), []

    def handler(req):
        hits.append(1)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=GCORE)

    serve(monkeypatch, handler)
    asyncio.run(s._enrich_with_stats(events(40)))
    assert len(hits) <= s.concurrency


def test_result_fetch_during_cooldown_never_touches_the_network(monkeypatch, tmp_path):
    s, hits = make_scraper(tmp_path), []
    s.session_manager.guard.ledger.start_cooldown(s.skin.name, 600)
    serve(monkeypatch, lambda req: hits.append(1) or httpx.Response(200, json={}))
    res, errored = asyncio.run(s.fetch_result_checked("12345"))
    assert (res, errored) == (None, True) and hits == []   # FAILED (trips the breaker), not "no data"


def test_challenge_on_result_fetch_is_a_failure_not_no_data(monkeypatch, tmp_path):
    s = make_scraper(tmp_path)
    serve(monkeypatch, lambda req: httpx.Response(
        200, headers={"content-type": "text/html"}, text=GCORE))
    res, errored = asyncio.run(s.fetch_result_checked("12345"))
    assert res is None and errored is True


def test_guard_check_raises_on_a_challenge_page(tmp_path):
    s = make_scraper(tmp_path)
    resp = httpx.Response(200, headers={"content-type": "text/html"}, text=GCORE,
                          request=httpx.Request("GET", "https://x/y"))
    with pytest.raises(SiteBlocked):
        s._guard_check(resp)
    ok = httpx.Response(200, json={"Success": True, "Value": []},
                        request=httpx.Request("GET", "https://x/y"))
    s._guard_check(ok)                        # a normal JSON answer passes untouched
