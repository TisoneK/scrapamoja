"""HAR (HTTP Archive) support for the scrapamoja network layer.

HAR is the standard format browsers use to export a recorded network
session (Chrome DevTools → "Save all as HAR", Firefox → Network tab →
"Save All As HAR", or Playwright's ``record_har_path`` context option).

This package provides three site-agnostic capabilities:

  * :mod:`export`  — launch a Playwright browser, navigate a site,
    record a HAR file with full response bodies. Operator runs this
    from a residential IP when the sandbox / datacenter IP is blocked.
  * :mod:`replay`  — load a HAR file, decode base64 bodies, run an
    optional extractor on each captured response, write a JSON result.
    No live browser needed — works from any IP.
  * :mod:`to_snapshot` — convert HAR entries into the framework's
    :class:`src.network.interception.CapturedResponse` shape and into
    :func:`src.core.snapshot.normalize.normalize_capture_list` shape.

Together they form the implementation of feature proposal
``docs/proposals/browser_api_hybrid/FEATURE_06_SESSION_HARVESTING.md``
(session harvesting) and partially
``FEATURE_02_NETWORK_INTERCEPTION.md`` (network interception replay).

Public API:

    from src.network.har import (
        HarExporter, HarReplayer, HarReplayResult,
        har_entries_to_captures,
    )

CLI:

    python -m src.network.har.export --url https://example.com --output my.har
    python -m src.network.har.replay my.har out.json --normalize snap.json
"""

from .export import HarExporter, export_har
from .replay import HarReplayer, HarReplayResult, har_entries_to_captures
from .to_snapshot import har_to_normalized_snapshot

__all__ = [
    "HarExporter",
    "export_har",
    "HarReplayer",
    "HarReplayResult",
    "har_entries_to_captures",
    "har_to_normalized_snapshot",
]

__version__ = "1.0.0"
