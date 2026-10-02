"""The security guard wired into the betb2b client and session manager."""
import asyncio

import httpx
import pytest

from src.security import (
    BETB2B_RULES, Action, BlockLedger, BlockType, SecurityGuard, SiteBlocked, SiteInCooldown,
    resolver, tiers,
)
from src.security import guard as guard_mod
from src.sites.betb2b import session as session_mod
from src.sites.betb2b.client import BetB2BFeedClient
from src.sites.betb2b.config import BetB2BSkinConfig
from src.sites.betb2b.session import BetB2BSessionManager, _Retry, profile_name_for

GCORE = "<html><head><title>Gcore</title></head><body>Browser Validation</body></html>"


@pytest.fixture(autouse=True)
def _display(monkeypatch, tmp_path):
    monkeypatch.setattr(tiers, "has_display", lambda: True)
    monkeypatch.setattr(guard_mod, "has_display", lambda: True)
    monkeypatch.setenv("SCRAPAMOJA_SECURITY_DIR", str(tmp_path / "sec"))
    monkeypatch.setenv("SCRAPAMOJA_PROFILE_DIR", str(tmp_path / "prof"))


@pytest.fixture
def skin():
    return BetB2BSkinConfig.from_yaml("src/sites/betb2b/skins/linebet.yaml")


def manager(skin, tmp_path):
    guard = SecurityGuard(skin.name, rules=BETB2B_RULES, interactive=False,
                          ledger=BlockLedger(tmp_path / "l.json"))
    return BetB2BSessionManager(skin, security_guard=guard)


def client_for(skin, mgr, handler):
    c = BetB2BFeedClient(skin, mgr, direct=True, rate_limit_per_minute=0)
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c


# ------------------------------------------------------------------ client --
def test_repeated_challenge_responses_end_in_cooldown_not_a_request_storm(skin, tmp_path):
    mgr, hits = manager(skin, tmp_path), []

    def handler(req):
        hits.append(1)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=GCORE)

    async def go():
        c = client_for(skin, mgr, handler)
        with pytest.raises(SiteBlocked) as ei:
            for _ in range(20):
                await c.fetch("events_top")
        assert ei.value.verdict.type is BlockType.JS_CHALLENGE
        n = len(hits)
        with pytest.raises(SiteInCooldown):                  # the next call never reaches the network
            await c.fetch("events_top")
        assert len(hits) == n
    asyncio.run(go())
    assert len(hits) <= 5


def test_country_block_fails_fast(skin, tmp_path):
    mgr = manager(skin, tmp_path)

    def handler(req):
        return httpx.Response(203, headers={"content-type": "text/html"}, text="")

    async def go():
        with pytest.raises(SiteBlocked) as ei:
            await client_for(skin, mgr, handler).fetch("events_top")
        assert ei.value.verdict.type is BlockType.GEO_BLOCK
        assert ei.value.decision.action is Action.COOLDOWN
    asyncio.run(go())


def test_known_406_and_clean_json_do_not_trip_the_guard(skin, tmp_path):
    mgr = manager(skin, tmp_path)
    codes = iter([406, 200, 406])

    def handler(req):
        code = next(codes)
        return httpx.Response(code, headers={"content-type": "application/json"}, json={"Success": True})

    async def go():
        c = client_for(skin, mgr, handler)
        for _ in range(3):
            await c.fetch("events_top")
    asyncio.run(go())
    assert mgr.guard.ledger.cooldown_left(skin.name)[0] == 0
    assert mgr.guard.ledger.state(skin.name).total_blocks == 0


# ----------------------------------------------------------------- session --
class P:
    url = "https://m.linebet.com/en"

    async def title(self):
        return "Gcore"

    async def content(self):
        return ""


def test_unresolved_challenge_escalates_the_browser_tier(skin, tmp_path, monkeypatch):
    mgr = manager(skin, tmp_path)

    async def never_clears(page, **kw):
        return resolver.Clearance(False, await resolver.inspect_page(page), 0.0)
    monkeypatch.setattr(session_mod.sec_resolver, "wait_for_clearance", never_clears)

    async def go():
        verdict = await mgr.guard.inspect_page(P(), 200)
        with pytest.raises(_Retry):
            await mgr._resolve_block(P(), verdict, mgr.guard.tier)
    asyncio.run(go())
    assert mgr.guard.tier.name == "chrome-headless"        # next attempt opens real Chrome


def test_challenge_that_clears_by_waiting_is_accepted(skin, tmp_path, monkeypatch):
    mgr = manager(skin, tmp_path)

    async def clears(page, **kw):
        return resolver.Clearance(True, await resolver.inspect_page(page), 3.0)
    monkeypatch.setattr(session_mod.sec_resolver, "wait_for_clearance", clears)

    async def go():
        verdict = await mgr.guard.inspect_page(P(), 200)
        await mgr._resolve_block(P(), verdict, mgr.guard.tier)     # returns, no raise
    asyncio.run(go())
    assert mgr.guard.tier.name == "headless-chromium"


def test_geo_block_during_bootstrap_surfaces_as_site_blocked(skin, tmp_path):
    mgr = manager(skin, tmp_path)

    class GeoPage(P):
        url = "https://linebet.com/en/block"

        async def title(self):
            return ""

    async def go():
        verdict = await mgr.guard.inspect_page(GeoPage(), 203)
        with pytest.raises(SiteBlocked):
            await mgr._resolve_block(GeoPage(), verdict, mgr.guard.tier)
    asyncio.run(go())


def test_bootstrap_retries_at_stronger_tier_then_succeeds_and_cools_nothing(skin, tmp_path, monkeypatch):
    mgr, seen = manager(skin, tmp_path), []

    async def once(tier):
        seen.append(tier.name)
        if len(seen) == 1:
            mgr.guard.on_block(mgr.guard.inspect(200, "u", title="Gcore"))   # WAIT rung used up
            mgr.guard.on_block(mgr.guard.inspect(200, "u", title="Gcore"))   # → escalate
            raise _Retry()
        return "SESSION"
    monkeypatch.setattr(mgr, "_bootstrap_once", once)

    assert asyncio.run(mgr._bootstrap()) == "SESSION"
    assert seen == ["headless-chromium", "chrome-headless"]
    assert mgr.guard.ledger.state(skin.name).consecutive_blocks == 0     # success reset the streak


def test_bootstrap_refuses_a_site_in_cooldown(skin, tmp_path):
    mgr = manager(skin, tmp_path)
    mgr.guard.on_block(mgr.guard.inspect(203, "https://linebet.com/en/block"))
    with pytest.raises(SiteInCooldown):
        asyncio.run(mgr._bootstrap())


def test_profile_name_env(monkeypatch):
    monkeypatch.delenv("BETB2B_PROFILE", raising=False)
    assert profile_name_for("linebet") == "betb2b-linebet"
    monkeypatch.setenv("BETB2B_PROFILE", "off")
    assert profile_name_for("linebet") is None
    monkeypatch.setenv("BETB2B_PROFILE", "mine")
    assert profile_name_for("linebet") == "mine"


def test_cooldown_is_per_egress_so_a_direct_block_does_not_rest_the_proxied_route(skin):
    from src.network.proxy import ProxyEndpoint
    direct = BetB2BSessionManager(skin)
    direct.guard.on_block(direct.guard.inspect(203, "https://linebet.com/en/block"))
    with pytest.raises(SiteInCooldown):
        direct.guard.preflight()
    ep = ProxyEndpoint(id="allowed", scheme="http", host="h", port=1, country="KE")
    proxied = BetB2BSessionManager(skin, proxy=ep)
    proxied.guard.preflight()                                              # untouched
    assert proxied.guard.site == "linebet@allowed"


def test_block_through_a_configured_proxy_blames_the_proxy(skin, tmp_path, caplog):
    from src.network.proxy import ProxyEndpoint
    ep = ProxyEndpoint(id="allowed", scheme="http", host="h", port=1, country="KE")
    mgr = BetB2BSessionManager(skin, proxy=ep)
    caplog.set_level("WARNING")
    mgr._explain_block(mgr.guard.inspect(203, "https://linebet.com/en/block"))
    assert "the proxy is the problem" in caplog.text


def test_a_challenge_is_caught_even_when_the_navigation_errored(skin, tmp_path, monkeypatch):
    """goto can fail (connection reset) and still leave a challenge page: status is None."""
    mgr = manager(skin, tmp_path)

    async def never_clears(page, **kw):
        return resolver.Clearance(False, await resolver.inspect_page(page), 0.0)
    monkeypatch.setattr(session_mod.sec_resolver, "wait_for_clearance", never_clears)

    async def go():
        with pytest.raises(_Retry):
            await mgr._check_page(P(), None, mgr.guard.tier)

        class Clean(P):
            async def title(self):
                return "Linebet"
        await mgr._check_page(Clean(), None, mgr.guard.tier)          # clean page: no raise
    asyncio.run(go())
