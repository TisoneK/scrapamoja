"""Geo-restricted machines: no page loads without a proxy; the feed path is untouched."""
import dataclasses

import pytest

from src.security import BlockType, BlockVerdict, SecurityGuard, egress
from src.security.egress import PageLoadsRefused
from src.security.ledger import BlockLedger


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRAPAMOJA_SECURITY_DIR", str(tmp_path / "sec"))
    monkeypatch.delenv(egress.ENV, raising=False)


def _guard(tmp_path, site="betwinner"):
    return SecurityGuard(site, ledger=BlockLedger(tmp_path / "sec" / "ledger.json"), has_browser=False)


def test_unrestricted_machine_may_load_pages(tmp_path):
    _guard(tmp_path).require_page_access(via_proxy=False)             # no error


def test_declared_restricted_machine_refuses_page_loads_without_a_proxy(tmp_path, monkeypatch):
    monkeypatch.setenv(egress.ENV, "1")
    with pytest.raises(PageLoadsRefused) as e:
        _guard(tmp_path).require_page_access(via_proxy=False, what="browser bootstrap")
    assert "--direct" in str(e.value) and "browser bootstrap" in str(e.value)


def test_a_proxy_lifts_the_restriction(tmp_path, monkeypatch):
    monkeypatch.setenv(egress.ENV, "1")
    _guard(tmp_path).require_page_access(via_proxy=True)              # allowed-country egress


def test_a_page_level_country_block_without_proxy_switches_page_loads_off_but_not_the_feed(tmp_path):
    g = _guard(tmp_path)
    page_block = BlockVerdict(type=BlockType.GEO_BLOCK, status=203, url="https://betwinner.com/en/block",
                              via_page=True)
    g.on_block(page_block)
    with pytest.raises(PageLoadsRefused):
        g.require_page_access(via_proxy=False)                        # learned: pages off
    g.preflight()                                                     # feed path: no cooldown was started
    g.require_page_access(via_proxy=True)                             # a proxy still works


def test_a_feed_level_geo_block_still_rests_the_site(tmp_path):
    from src.security import SiteInCooldown
    g = _guard(tmp_path)
    g.on_block(BlockVerdict(type=BlockType.GEO_BLOCK, status=203, url="https://x/feed", via_page=False))
    with pytest.raises(SiteInCooldown):
        g.preflight()


def test_clearing_a_site_lifts_the_learned_restriction(tmp_path):
    egress.mark_restricted("betwinner")
    assert egress.learned_restricted("betwinner")
    assert egress.clear_restricted("betwinner") and not egress.learned_restricted("betwinner")


def test_warmup_refuses_on_a_restricted_machine(monkeypatch, capsys):
    from src.browser.profiles.__main__ import main
    monkeypatch.setenv(egress.ENV, "1")
    assert main(["warmup", "betb2b-linebet", "https://linebet.com/en"]) == 2
    assert "refused" in capsys.readouterr().err


def test_scripts_exit_before_opening_a_browser(monkeypatch, capsys):
    from src.sites.betb2b.scripts._common import require_page_access
    monkeypatch.setenv(egress.ENV, "1")
    monkeypatch.delenv("BETB2B_PROXY_URL", raising=False)
    with pytest.raises(SystemExit) as e:
        require_page_access("linebet")
    assert e.value.code == 2
    monkeypatch.setenv("BETB2B_PROXY_URL", "http://proxy.example:1")   # a proxy is configured
    require_page_access("linebet")                                     # allowed


@pytest.mark.asyncio
async def test_hybrid_scrape_is_refused_before_any_request_on_a_restricted_machine(monkeypatch):
    from pathlib import Path
    from src.sites.betb2b import BetB2BScraper, BetB2BSkinConfig
    monkeypatch.setenv(egress.ENV, "1")
    skin = BetB2BSkinConfig.from_yaml(str(Path(__file__).resolve().parents[2] / "sites" / "betb2b" / "skins" / "linebet.yaml"))
    s = BetB2BScraper(skin, proxy_manager=None, telemetry_enabled=False)    # not --direct
    with pytest.raises(PageLoadsRefused):
        await s.scrape(action="list_prematch", timeout_seconds=1)
    # ...but the direct path is not touched by the rule
    assert BetB2BScraper(skin, direct=True, telemetry_enabled=False)._direct is True
