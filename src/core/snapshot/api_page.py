"""Let the snapshot system capture a direct-HTTP response (no browser page exists in API mode).

``SnapshotManager.capture_snapshot`` only needs a few things from a "page": ``content()`` for
the HTML artifact, plus ``on``/``remove_listener`` for the optional console/network listeners.
:class:`ApiResponsePage` supplies them from an already-fetched response body, so a blocked or
drifted API response is stored as an ordinary bundle (same layout, retention and tools as a
browser snapshot)::

    page = ApiResponsePage(url, body_text)
    await manager.capture_snapshot(page, SnapshotContext(site=..., module="api", ...),
                                   SnapshotConfig(mode=SnapshotMode.FULL_PAGE, capture_screenshot=False))
"""

from __future__ import annotations


class ApiResponsePage:
    def __init__(self, url: str, body: "str | bytes", status: int = 200):
        self.url = url
        self.status = status
        self._body = body.decode("utf-8", "replace") if isinstance(body, bytes) else body

    async def content(self) -> str:
        return self._body

    def on(self, *args, **kwargs) -> None:            # no console / network events without a browser
        pass

    def remove_listener(self, *args, **kwargs) -> None:
        pass
