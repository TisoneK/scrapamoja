"""Block detection, policy ladders, cooldown ledger and the guard."""
import asyncio

import pytest

from src.security import (
    BETB2B_RULES, Action, BlockLedger, BlockType, SecurityGuard, SiteInCooldown, classify,
)
from src.security import guard as guard_mod
from src.security import resolver, tiers


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


# --------------------------------------------------------------- detector --
def test_gcore_browser_validation_page_is_a_js_challenge():
    v = classify(200, "https://m.linebet.com/en", title="Gcore")
    assert (v.type, v.vendor) == (BlockType.JS_CHALLENGE, "gcore")
    v = classify(200, "https://x/", body="<h1>Browser Validation Page</h1>")
    assert v.type is BlockType.JS_CHALLENGE


def test_betb2b_country_block_is_geo_not_challenge():
    assert classify(203, "https://linebet.com/en/block", rules=BETB2B_RULES).type is BlockType.GEO_BLOCK
    assert classify(200, "https://linebet.com/en/block?x=1", rules=BETB2B_RULES).type is BlockType.GEO_BLOCK
    v = classify(200, "https://x/", body="Access denied! This website is not available in your country")
    assert v.type is BlockType.GEO_BLOCK


def test_geo_wins_over_challenge_markup():
    v = classify(203, "https://linebet.com/en/block", body="<title>Gcore</title>", rules=BETB2B_RULES)
    assert v.type is BlockType.GEO_BLOCK


def test_cloudflare_and_captcha_and_ban_signatures():
    assert classify(403, "u", headers={"cf-mitigated": "challenge"}).type is BlockType.JS_CHALLENGE
    assert classify(200, "u", body="<div class='cf-turnstile'>").type is BlockType.CAPTCHA
    assert classify(200, "u", body="<div class='g-recaptcha'>").vendor == "recaptcha"
    assert classify(403, "u", body="Error code: 1020").type is BlockType.IP_BANNED


def test_rate_limit_reads_retry_after():
    v = classify(429, "u", headers={"Retry-After": "30"})
    assert (v.type, v.retry_after) == (BlockType.RATE_LIMITED, 30.0)
    assert classify(429, "u").retry_after is None


def test_plain_statuses_and_clean_pages():
    assert classify(403, "u").type is BlockType.ACCESS_DENIED
    assert classify(406, "u").type is BlockType.ACCESS_DENIED
    assert classify(419, "u").type is BlockType.AUTH_EXPIRED
    assert classify(200, "u", body='{"Success": true}').type is BlockType.OK
    assert not classify(200, "u", body="<html>odds</html>").blocked


# ------------------------------------------------------------ guard/ledger --
@pytest.fixture
def clock():
    return Clock()


def make_guard(tmp_path, clock, monkeypatch, *, display=True, **kw):
    monkeypatch.setattr(tiers, "has_display", lambda: display)
    monkeypatch.setattr(guard_mod, "has_display", lambda: display)
    ledger = BlockLedger(tmp_path / "ledger.json", clock=clock)
    kw.setdefault("interactive", False)
    return SecurityGuard("linebet", rules=BETB2B_RULES, ledger=ledger, **kw)


def challenge(g):
    return g.inspect(200, "https://m.linebet.com/en", title="Gcore")


def test_js_challenge_ladder_waits_then_escalates_then_cools_down(tmp_path, clock, monkeypatch):
    g = make_guard(tmp_path, clock, monkeypatch)
    assert g.tier.name == "headless-chromium"
    seq = []
    for _ in range(4):
        seq.append(g.on_block(challenge(g)).action)
    # interactive=False drops HUMAN_HANDOFF; no failover/proxy configured either
    assert seq == [Action.WAIT_FOR_CLEARANCE, Action.ESCALATE_BROWSER, Action.ESCALATE_BROWSER,
                   Action.COOLDOWN]
    assert g.tier.name == "chrome-headed"
    with pytest.raises(SiteInCooldown):
        g.preflight()


def test_escalation_stops_at_the_strongest_available_tier(tmp_path, clock, monkeypatch):
    g = make_guard(tmp_path, clock, monkeypatch, display=False)   # no headed tier on a server
    assert tiers.max_tier() == 1
    seq = [g.on_block(challenge(g)).action for _ in range(3)]
    assert seq == [Action.WAIT_FOR_CLEARANCE, Action.ESCALATE_BROWSER, Action.COOLDOWN]
    assert g.tier.name == "chrome-headless"


def test_human_handoff_only_when_interactive(tmp_path, clock, monkeypatch):
    g = make_guard(tmp_path, clock, monkeypatch, interactive=True)
    seq = [g.on_block(challenge(g)).action for _ in range(4)]
    assert seq[-1] is Action.HUMAN_HANDOFF


def test_geo_block_never_escalates_the_browser(tmp_path, clock, monkeypatch):
    g = make_guard(tmp_path, clock, monkeypatch)
    d = g.on_block(g.inspect(203, "https://linebet.com/en/block"))
    assert d.action is Action.COOLDOWN and d.cooldown_seconds == 3600
    assert g.tier.name == "headless-chromium"
    g2 = make_guard(tmp_path / "b", clock, monkeypatch, has_failover=True)
    assert g2.on_block(g2.inspect(203, "https://linebet.com/en/block")).action is Action.FAILOVER_SITE


def test_cooldown_expires_backs_off_and_resets_on_success(tmp_path, clock, monkeypatch):
    g = make_guard(tmp_path, clock, monkeypatch)
    geo = lambda: g.inspect(203, "https://linebet.com/en/block")
    assert g.on_block(geo()).cooldown_seconds == 3600
    clock.t += 3601
    g.preflight()                                   # cooldown over: allowed again
    assert g.on_block(geo()).cooldown_seconds == 7200   # doubled for the second consecutive block
    clock.t += 7201
    g.on_success()
    assert g.on_block(geo()).cooldown_seconds == 3600   # a clean response reset the streak


def test_rate_limit_honours_retry_after_and_caps(tmp_path, clock, monkeypatch):
    g = make_guard(tmp_path, clock, monkeypatch)
    v = g.inspect(429, "u", {"retry-after": "120"})
    assert g.on_block(v).cooldown_seconds == 120
    for _ in range(10):
        d = g.on_block(v)
    assert d.cooldown_seconds == g.policy.max_cooldown


def test_cooldown_and_tier_survive_a_new_process(tmp_path, clock, monkeypatch):
    g = make_guard(tmp_path, clock, monkeypatch)
    for _ in range(4):
        g.on_block(challenge(g))
    g2 = make_guard(tmp_path, clock, monkeypatch)       # same file, fresh objects
    assert g2.tier.name == "chrome-headed"
    with pytest.raises(SiteInCooldown) as ei:
        g2.preflight()
    assert ei.value.last is BlockType.JS_CHALLENGE


def test_corrupt_or_missing_ledger_never_blocks_a_scrape(tmp_path, clock):
    p = tmp_path / "ledger.json"
    p.write_text("{not json")
    BlockLedger(p, clock=clock).record_success("x")
    assert BlockLedger(tmp_path / "nope" / "l.json", clock=clock).cooldown_left("x")[0] == 0


# ---------------------------------------------------------------- resolver --
class FakePage:
    """Shows a Gcore page for ``clears_after`` inspections, then real content."""
    def __init__(self, clears_after, url="https://m.linebet.com/en"):
        self.n, self.clears_after, self.url = 0, clears_after, url

    async def title(self):
        self.n += 1
        return "Gcore" if self.n <= self.clears_after else "Linebet"

    async def content(self):
        return "<html></html>"


def test_wait_for_clearance_resolves_a_self_clearing_challenge():
    c = asyncio.run(resolver.wait_for_clearance(FakePage(2), timeout_s=10, poll_s=0.01))
    assert c.cleared and c.verdict.type is BlockType.OK


def test_wait_for_clearance_gives_up_and_skips_geo_and_captcha():
    c = asyncio.run(resolver.wait_for_clearance(FakePage(10 ** 6), timeout_s=0.05, poll_s=0.01))
    assert not c.cleared and c.verdict.type is BlockType.JS_CHALLENGE
    geo = FakePage(0, url="https://linebet.com/en/block")
    c = asyncio.run(resolver.wait_for_clearance(geo, timeout_s=5, poll_s=5, rules=BETB2B_RULES))
    assert c.verdict.type is BlockType.GEO_BLOCK and c.waited_s < 1   # returned immediately


def test_failing_over_also_rests_the_site(tmp_path, clock, monkeypatch):
    g = make_guard(tmp_path, clock, monkeypatch, has_failover=True)
    d = g.on_block(g.inspect(203, "https://linebet.com/en/block"))
    assert d.action is Action.FAILOVER_SITE
    with pytest.raises(SiteInCooldown):
        g.preflight()


def test_guard_without_a_browser_skips_the_browser_rungs():
    """Direct mode has no page: a JS challenge must not get 'wait' / 'stronger browser' /
    'human' rungs it cannot act on — it goes straight to failover or cooldown."""
    import tempfile, pathlib
    from src.security import Action, BETB2B_RULES, BlockLedger, SecurityGuard
    tmp = pathlib.Path(tempfile.mkdtemp())
    for failover, expected in ((False, Action.COOLDOWN), (True, Action.FAILOVER_SITE)):
        g = SecurityGuard("x", rules=BETB2B_RULES, interactive=True, has_browser=False,
                          has_failover=failover, ledger=BlockLedger(tmp / f"{failover}.json"))
        v = g.inspect(200, "https://x/feed", {"content-type": "text/html"},
                      "<html><head><title>Gcore</title></head><body>Browser Validation</body></html>")
        assert g.on_block(v).action is expected                     # first challenge, no retries
    # with a browser the same first challenge still gets patience first
    g = SecurityGuard("y", rules=BETB2B_RULES, interactive=True, has_browser=True,
                      ledger=BlockLedger(tmp / "b.json"))
    v = g.inspect(200, "https://y/feed", {"content-type": "text/html"},
                  "<html><head><title>Gcore</title></head><body>Browser Validation</body></html>")
    assert g.on_block(v).action is Action.WAIT_FOR_CLEARANCE
