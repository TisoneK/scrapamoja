"""Snapshot capture that needs no browser page: a direct-HTTP response as a first-class bundle.

``SnapshotManager.capture_snapshot`` takes a Playwright page. In API mode there is none, but the
bundle layout (``site/module/component/date/time_session``), ``metadata.json`` and the
normaliser are all independent of a browser. This writes a bundle straight from
``(url, status, headers, body)``:

    response/response.json   the normalised response (volatile params redacted, body hash)
    response/body.txt        the raw body, truncated
    metadata.json            the same ``SnapshotBundle`` metadata a browser snapshot has

It is synchronous and never raises (a diagnostic must not break the scrape it describes), so any
module -- guard, scraper, extractor -- can call it from sync or async code.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

from .models import SnapshotBundle, SnapshotConfig, SnapshotContext, SnapshotMode
from .retention import sweep_once
from .normalize import NormalizerConfig, normalize_captured_response

RAW_BODY_CHARS = 20_000
_SAFE = re.compile(r"[^A-Za-z0-9_.@-]+")


def capture_response_bundle(
    *, site: str, module: str, component: str, url: str, status: Optional[int],
    method: str = "GET", request_headers: Optional[Mapping[str, str]] = None,
    response_headers: Optional[Mapping[str, str]] = None, body: Any = None,
    note: Optional[str] = None, extra: Optional[dict] = None,
    base_path: str = "data/snapshots", session_id: Optional[str] = None,
) -> Optional[Path]:
    """Write one response bundle; returns its directory, or None if it could not be written."""
    try:
        now = datetime.now()
        sweep_once(base_path)
        ctx = SnapshotContext(
            site=_SAFE.sub("_", site), module=_SAFE.sub("_", module),
            component=_SAFE.sub("_", component),
            session_id=session_id or uuid.uuid4().hex[:6],
            additional_metadata={"url": url.split("?")[0], "status": status, "note": note, **(extra or {})},
        )
        bundle_dir = Path(base_path) / ctx.generate_hierarchical_path(now)
        (bundle_dir / "response").mkdir(parents=True, exist_ok=True)

        text = body.decode("utf-8", "replace") if isinstance(body, bytes) else ("" if body is None else str(body))
        normalised = normalize_captured_response(
            url, int(status or 0), method, dict(request_headers or {}),
            {str(k).lower(): str(v) for k, v in (response_headers or {}).items()}, text,
            NormalizerConfig(max_body_chars=2000))
        (bundle_dir / "response" / "response.json").write_text(
            json.dumps(normalised, indent=2, default=str, sort_keys=True), encoding="utf-8")
        (bundle_dir / "response" / "body.txt").write_text(text[:RAW_BODY_CHARS], encoding="utf-8")

        cfg = SnapshotConfig(mode=SnapshotMode.FULL_PAGE, capture_html=False, capture_screenshot=False)
        bundle = SnapshotBundle(
            context=ctx, timestamp=now, config=cfg, bundle_path=str(bundle_dir),
            artifacts=["response/response.json", "response/body.txt"],
            metadata={"capture_method": "api_response", "status": status})
        (bundle_dir / "metadata.json").write_text(
            json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return bundle_dir
    except Exception:  # noqa: BLE001
        return None
