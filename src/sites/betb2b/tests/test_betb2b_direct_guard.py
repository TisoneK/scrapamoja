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


def test_probe_reports_zero_cookies_as_not_harvested(monkeypatch, tmp_path, capsys):
    """`probe` used to hard-code session_harvested=true even with 0 cookies."""
    import argparse
    from types import SimpleNamespace
    import src.sites.betb2b as pkg
    from src.sites.betb2b.cli.main import BetB2BCLI

    guard = SecurityGuard("linebet", rules=BETB2B_RULES, interactive=False,
                          ledger=BlockLedger(tmp_path / "l.json"))

    class FakeScraper:
        def __init__(self, skin, **kw):
            self.session_manager = SimpleNamespace(
                guard=guard, session_age=None,
                get_session=self._session)
            self.sport_scraper = SimpleNamespace(slug="basketball", sport_id=3)
            self.sport_ctx = SimpleNamespace(bootstrap_path="/en/line/basketball")

        async def _session(self):
            return SimpleNamespace(cookies=[], user_agent="UA")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def get_info(self):
            return {"proxy_endpoint": None}

    monkeypatch.setattr(pkg, "BetB2BScraper", FakeScraper)
    out = tmp_path / "probe.json"
    args = argparse.Namespace(skin="linebet", sport="basketball", settle=0.0, output=str(out))
    asyncio.run(BetB2BCLI()._cmd_probe(args))
    import json
    res = json.loads(out.read_text())
    assert res["cookie_count"] == 0 and res["session_harvested"] is False
    assert res["security"]["site"] == "linebet" and res["security"]["cooldown_seconds_left"] == 0


def test_timeouts_across_components_rest_the_skin_for_everyone(monkeypatch, tmp_path):
    """Timeouts seen by the direct calls count toward ONE shared cooldown, so after a few the
    feed client (a different component) refuses to touch the skin too."""
    from src.security import SiteInCooldown
    s = make_scraper(tmp_path)
    s.session_manager.guard.fail_threshold = 4
    hits = []

    def handler(req):
        hits.append(1)
        raise httpx.ConnectTimeout("dropped", request=req)

    serve(monkeypatch, handler)
    asyncio.run(s._enrich_with_h2h(events(40)))
    assert len(hits) <= 4 + s.concurrency            # not 40 doomed 15-second waits
    guard = s.session_manager.guard
    with pytest.raises(SiteInCooldown):              # every statistics caller sees the same rest...
        guard.preflight("stats")
    guard.preflight()                                # ...but the odds feed is NOT rested by an optional endpoint


def test_direct_calls_are_paced_per_second_not_just_limited_in_flight(monkeypatch, tmp_path):
    """Four workers on a fast site used to send ~20 requests/s. The skin's pacer now spaces
    request starts for the feed client and the direct calls alike."""
    import time
    from src.security import Pacer
    s = make_scraper(tmp_path)
    s.session_manager.pacer = Pacer(40)               # 25 ms apart
    starts = []

    def handler(req):
        starts.append(time.monotonic())
        return httpx.Response(204)                    # "no data": fast, valid

    serve(monkeypatch, handler)
    asyncio.run(s._enrich_with_h2h(events(12)))
    starts.sort()
    assert len(starts) == 12
    assert starts[-1] - starts[0] >= 11 * 0.02        # not 12 requests in the same instant


def test_direct_calls_share_one_pooled_client(monkeypatch, tmp_path):
    """A fresh client per call means a fresh TCP+TLS handshake per call — the pattern a
    per-source new-connection limit punishes. All direct calls reuse one pooled client."""
    s = make_scraper(tmp_path)
    s.session_manager.pacer.interval = 0
    built = []

    def factory(**kw):
        kw.pop("proxy", None)
        built.append(1)
        return REAL_CLIENT(transport=httpx.MockTransport(lambda req: httpx.Response(204)), **kw)

    monkeypatch.setattr(httpx, "AsyncClient", factory)

    async def go():
        await s._enrich_with_h2h(events(5))
        await s._enrich_with_stats(events(5))
        for i in range(6):
            await s.fetch_result_checked(str(100 + i))
        await s.close()                      # no-op when never started; must not raise
    asyncio.run(go())
    assert len(built) == 1                   # not 1 + 1 + 6


def test_a_challenge_on_a_direct_call_leaves_evidence_without_anyone_asking(monkeypatch, tmp_path):
    """The point of the evidence log: the Gcore page that stopped H2H is on disk afterwards, in the
    snapshot system's normalised form, with no curl probes needed to find out what happened."""
    s = make_scraper(tmp_path)
    serve(monkeypatch, lambda req: httpx.Response(
        200, headers={"content-type": "text/html", "server": "gcore"}, text=GCORE))
    asyncio.run(s._enrich_with_h2h(events(6)))
    recs = s.session_manager.guard.evidence.read(days=1)
    blocks = [r for r in recs if r["kind"] == "block"]
    assert blocks and blocks[0]["verdict"]["vendor"] == "gcore"
    assert "Browser Validation" in blocks[0]["response"]["body"]
    assert blocks[0]["url"].endswith("/statisticfeed/api/v1/Game/h2h")


def test_timeouts_on_direct_calls_are_recorded_by_exception_class(monkeypatch, tmp_path):
    s = make_scraper(tmp_path)

    def handler(req):
        raise httpx.ConnectTimeout("dropped", request=req)

    serve(monkeypatch, handler)
    asyncio.run(s._enrich_with_h2h(events(4)))
    rows = s.session_manager.guard.evidence.summarise(s.session_manager.guard.evidence.read(days=1))
    assert any(r["kind"] == "unreachable" and r["error"] == "ConnectTimeout" for r in rows)
