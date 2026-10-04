"""Page loads from a machine whose connection a site country-blocks.

Some betting sites refuse whole countries and answer a page request from one with a
redirect to a block page (HTTP 203 to ``/en/block``). The same sites serve their data feeds
to anyone, so a machine in a blocked country can still fetch data, but must not load the
site itself: every page load is a request the site classifies as a country block, and the
block is recorded against the machine.

The rule, enforced here for everything that opens a browser page (the bootstrap, the DOM
render, the profile warm-up, the probe scripts):

* A machine declared restricted (``SCRAPAMOJA_GEO_RESTRICTED=1``) never loads a page unless
  the traffic goes through an allowed-country proxy. Feed fetching without a page (the
  ``--direct`` path) is unaffected.
* A machine that has *seen* a page-level country block for a site, without a proxy, is
  treated as restricted for that site from then on (a marker beside the block ledger) until
  it is cleared (``python -m src.security clear <site>``) or a proxy is used.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict

from .ledger import default_dir

ENV = "SCRAPAMOJA_GEO_RESTRICTED"
_TRUE = {"1", "true", "yes", "on"}


class PageLoadsRefused(RuntimeError):
    """A page load was refused because this machine is geo-restricted and no proxy is in use."""

    def __init__(self, site: str, what: str, reason: str):
        self.site, self.what, self.reason = site, what, reason
        super().__init__(
            f"{what} for {site!r} refused: {reason}. This machine's connection is country-blocked "
            f"by the site, so loading its pages would be recorded as a block. Fetch data with the "
            f"direct path (scrape ... --direct, no page load), or route through an allowed-country "
            f"proxy (BETB2B_PROXY_URL). Run on an allowed-country machine for anything that needs "
            f"a browser."
        )


def declared_restricted() -> bool:
    return os.environ.get(ENV, "").strip().lower() in _TRUE


def _marker_path() -> Path:
    return default_dir() / "page_restricted.json"


def _read() -> Dict[str, float]:
    try:
        return {str(k): float(v) for k, v in json.loads(_marker_path().read_text()).items()}
    except (OSError, ValueError, TypeError):
        return {}


def learned_restricted(site: str) -> bool:
    return site in _read()


def mark_restricted(site: str) -> None:
    """Remember that a page load of ``site`` was country-blocked without a proxy."""
    data = _read()
    data[site] = time.time()
    try:
        p = _marker_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=1))
    except OSError:
        pass                      # a read-only home must not break scraping


def clear_restricted(site: str) -> bool:
    data = _read()
    if site not in data:
        return False
    del data[site]
    try:
        _marker_path().write_text(json.dumps(data, indent=1))
    except OSError:
        pass
    return True


def restricted_sites() -> Dict[str, float]:
    return _read()


def check_page_load(site: str, *, via_proxy: bool, what: str = "page load") -> None:
    """Raise :class:`PageLoadsRefused` unless a page load of ``site`` is allowed from here."""
    if via_proxy:
        return
    site = site.split("@", 1)[0]
    if declared_restricted():
        raise PageLoadsRefused(site, what, f"{ENV}=1 and no proxy is configured")
    if learned_restricted(site):
        raise PageLoadsRefused(site, what, "a page load of this site was already country-blocked "
                                           "from this machine without a proxy")
