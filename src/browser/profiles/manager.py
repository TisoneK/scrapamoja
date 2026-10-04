"""Named, persistent browser profiles.

A profile is a Chromium user-data directory kept between runs, so cookies,
local storage and — the point — a passed browser-validation survive. From a
site's side a profile looks like one long-lived browser instead of a new one
every run. Profiles are site-agnostic: name them after a site, a skin, an
operator or a purpose.

Layout (``$SCRAPAMOJA_PROFILE_DIR`` or ``~/.scrapamoja/profiles``)::

    <root>/<name>/profile.json   metadata (ProfileMeta)
    <root>/<name>/data/          Chromium user-data dir
    <root>/<name>/.lock          pid of the process using it
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from .models import ProfileMeta

ENV_DIR = "SCRAPAMOJA_PROFILE_DIR"
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_STEALTH_ARGS = ["--disable-blink-features=AutomationControlled"]


class ProfileError(RuntimeError):
    pass


class ProfileInUse(ProfileError):
    pass


def default_root() -> Path:
    return Path(os.environ.get(ENV_DIR) or Path.home() / ".scrapamoja" / "profiles")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class ProfileManager:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else default_root()

    # -- bookkeeping ------------------------------------------------------ #
    def _dir(self, name: str) -> Path:
        if not _NAME_RE.match(name or ""):
            raise ProfileError(f"invalid profile name {name!r} (letters, digits, . _ - ; max 64)")
        return self.root / name

    def data_dir(self, name: str) -> Path:
        return self._dir(name) / "data"

    def exists(self, name: str) -> bool:
        return (self._dir(name) / "profile.json").is_file()

    def get(self, name: str) -> ProfileMeta:
        try:
            return ProfileMeta(**json.loads((self._dir(name) / "profile.json").read_text()))
        except (OSError, ValueError, TypeError) as exc:
            raise ProfileError(f"profile {name!r} not found") from exc

    def _write(self, meta: ProfileMeta) -> None:
        d = self._dir(meta.name)
        d.mkdir(parents=True, exist_ok=True)
        (d / "profile.json").write_text(json.dumps(asdict(meta), indent=1))

    def get_or_create(self, name: str, identity: Optional[Dict[str, Any]] = None,
                      notes: str = "") -> ProfileMeta:
        if self.exists(name):
            return self.get(name)
        meta = ProfileMeta(name=name, created_at=time.time(),
                           identity=dict(identity or {}), notes=notes)
        self._write(meta)
        self.data_dir(name).mkdir(parents=True, exist_ok=True)
        return meta

    def list(self) -> List[ProfileMeta]:
        if not self.root.is_dir():
            return []
        out = []
        for d in sorted(self.root.iterdir()):
            if (d / "profile.json").is_file():
                try:
                    out.append(self.get(d.name))
                except ProfileError:
                    continue
        return out

    def delete(self, name: str) -> None:
        d = self._dir(name)
        if self._lock_holder(name) is not None:
            raise ProfileInUse(f"profile {name!r} is in use")
        if d.exists():
            shutil.rmtree(d)

    # -- locking ---------------------------------------------------------- #
    def _lock_holder(self, name: str) -> Optional[int]:
        try:
            pid = int((self._dir(name) / ".lock").read_text().strip())
        except (OSError, ValueError):
            return None
        return pid if _pid_alive(pid) and pid != os.getpid() else None

    def _acquire(self, name: str) -> None:
        pid = self._lock_holder(name)
        if pid is not None:
            raise ProfileInUse(f"profile {name!r} is open in pid {pid}; Chromium allows one process per profile")
        (self._dir(name) / ".lock").write_text(str(os.getpid()))

    def _release(self, name: str) -> None:
        try:
            (self._dir(name) / ".lock").unlink()
        except OSError:
            pass

    # -- launching -------------------------------------------------------- #
    @asynccontextmanager
    async def open_context(
        self,
        pw: Any,
        name: str,
        *,
        headless: bool = True,
        channel: Optional[str] = None,
        stealth_args: bool = False,
        proxy: Optional[Dict[str, Any]] = None,
        identity: Optional[Dict[str, Any]] = None,
        **launch_kwargs: Any,
    ) -> AsyncIterator[Any]:
        """Open the profile as a persistent Playwright context; always closed on exit.

        ``identity`` (if given) overrides the profile's stored identity (set via
        :meth:`get_or_create`) for this launch only. ``stealth_args`` drops the automation
        switches Chromium sets by default (needed for the stronger tiers).
        """
        meta = self.get_or_create(name)       # per-launch identity is never persisted
        self._acquire(name)
        ctx = None
        try:
            kwargs: Dict[str, Any] = {"headless": headless}
            if channel:
                kwargs["channel"] = channel
            if proxy:
                kwargs["proxy"] = proxy
            kwargs.update({k: v for k, v in {**meta.identity, **(identity or {})}.items()
                           if v is not None})
            if stealth_args:
                kwargs["args"] = list(launch_kwargs.pop("args", [])) + _STEALTH_ARGS
                kwargs["ignore_default_args"] = ["--enable-automation"]
            kwargs.update(launch_kwargs)
            ctx = await pw.chromium.launch_persistent_context(str(self.data_dir(name)), **kwargs)
            meta.last_used_at, meta.uses = time.time(), meta.uses + 1
            self._write(meta)
            yield ctx
        finally:
            try:
                if ctx is not None:
                    await ctx.close()
            finally:
                self._release(name)

    async def warmup(self, name: str, url: str, *, channel: Optional[str] = "chrome",
                     proxy: Optional[Dict[str, Any]] = None, timeout_s: float = 900.0) -> None:
        """Open the profile headed so a person can pass any check by hand.

        Returns when the window is closed (or on timeout). Cookies and storage
        are written into the profile, so later automated runs reuse the result.
        """
        from playwright.async_api import async_playwright
        from src.security import egress

        # A country-blocked machine must not load the site's pages without a proxy.
        egress.check_page_load(name.removeprefix("betb2b-"), via_proxy=bool(proxy), what="profile warm-up")

        async with async_playwright() as pw:
            async with self.open_context(pw, name, headless=False, channel=channel,
                                         stealth_args=True, proxy=proxy) as ctx:
                closed = asyncio.Event()
                ctx.on("close", lambda *_: closed.set())
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                try:
                    await page.goto(url, wait_until="commit", timeout=60_000)
                except Exception:  # noqa: BLE001 — the person can still navigate by hand
                    pass
                try:
                    await asyncio.wait_for(closed.wait(), timeout=timeout_s)
                except asyncio.TimeoutError:
                    pass
