

def test_health_summary_reports_rates_and_latency(tmp_path):
    from src.sites.betb2b.config import BetB2BSkinConfig
    from src.sites.betb2b.telemetry_integration import BetB2BTelemetry
    skin = BetB2BSkinConfig.from_yaml("src/sites/betb2b/skins/linebet.yaml")
    t = BetB2BTelemetry(skin, output_dir=str(tmp_path))
    for status, lat in [(200, 100.0), (200, 200.0), (200, 300.0), (403, 50.0)]:
        t.record_feed_poll(feed="game", root="line", status=status, body_bytes=10,
                           latency_ms=lat, decoded=status == 200)
    s = t.record_health()["line_game"]
    assert s["requests"] == 4 and s["success_rate"] == 0.75
    assert s["status"] == {"200": 3, "403": 1} and s["latency_ms"]["max"] == 300.0
    health = [e for e in t._events if e.phase == "health"]
    assert health and health[0].success is False
