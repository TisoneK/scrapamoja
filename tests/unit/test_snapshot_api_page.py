"""The snapshot manager can store a direct-HTTP response through ApiResponsePage, and its logger
no longer crashes on `exc_info` (it did, turning every snapshot error into a KeyError)."""
import asyncio
import pytest

from src.core.snapshot.api_page import ApiResponsePage
from src.core.snapshot.manager import SnapshotManager
from src.core.snapshot.models import SnapshotConfig, SnapshotContext, SnapshotMode


def test_api_response_is_stored_as_a_bundle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)                              # bundles go under ./data/snapshots
    ctx = SnapshotContext(site="s", module="api", component="GetGameZip", session_id="t")
    cfg = SnapshotConfig(mode=SnapshotMode.FULL_PAGE, capture_html=True, capture_screenshot=False,
                         capture_console=False, capture_network=False, async_save=False)
    bundle = asyncio.run(SnapshotManager().capture_snapshot(
        ApiResponsePage("https://x/service-api/GetGameZip?id=1", '{"Success": true}'), ctx, cfg))
    assert bundle is not None
    html = list(tmp_path.rglob("fullpage_*.html"))
    assert html and '"Success"' in html[0].read_text()


def test_logger_accepts_exc_info_and_reserved_names(caplog):
    from src.observability.logger import get_logger
    log = get_logger("t")
    log.error("boom", error="x", exc_info=True, name="reserved", args="x")   # must not raise
