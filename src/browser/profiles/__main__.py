"""``python -m src.browser.profiles`` — manage persistent browser profiles."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import os
import sys
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

from .manager import ProfileError, ProfileManager


def _ts(t: float) -> str:
    return dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M") if t else "never"


def proxy_from_env(name: str) -> Optional[Dict[str, Any]]:
    """Playwright proxy dict from env var ``name`` (a proxy URL).

    Credentials may be embedded in the URL or supplied in ``<name>`` with
    ``_URL`` replaced by ``_USER`` / ``_PASS`` (e.g. ``BETB2B_PROXY_URL`` →
    ``BETB2B_PROXY_USER``). Read from env so they never appear in argv.
    """
    raw = os.environ.get(name)
    if not raw:
        raise ValueError(f"${name} is not set")
    u = urlparse(raw if "://" in raw else f"http://{raw}")
    if not u.hostname:
        raise ValueError(f"${name} is not a proxy URL")
    base = name[:-4] if name.endswith("_URL") else name
    proxy: Dict[str, Any] = {"server": f"{u.scheme}://{u.hostname}" + (f":{u.port}" if u.port else "")}
    user = unquote(u.username) if u.username else os.environ.get(f"{base}_USER")
    pw = unquote(u.password) if u.password else os.environ.get(f"{base}_PASS")
    if user:
        proxy["username"] = user
    if pw:
        proxy["password"] = pw
    return proxy


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m src.browser.profiles", description=__doc__)
    ap.add_argument("--root", help="profile root (default: $SCRAPAMOJA_PROFILE_DIR or ~/.scrapamoja/profiles)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list profiles")
    p = sub.add_parser("create", help="create an empty profile")
    p.add_argument("name"); p.add_argument("--notes", default="")
    p = sub.add_parser("path", help="print a profile's user-data dir")
    p.add_argument("name")
    p = sub.add_parser("delete", help="delete a profile and everything it stored")
    p.add_argument("name"); p.add_argument("--force", action="store_true", help="skip the confirmation")
    p = sub.add_parser("warmup", help="open the profile headed so you can pass a browser check by hand")
    p.add_argument("name"); p.add_argument("url")
    p.add_argument("--channel", default="chrome", help="'chrome' (installed Google Chrome) or '' for bundled Chromium")
    p.add_argument("--timeout", type=float, default=900.0, help="seconds before it closes itself")
    p.add_argument("--proxy-env", metavar="NAME",
                   help="env var holding a proxy URL to browse through (e.g. BETB2B_PROXY_URL for the "
                        "allowed-country tunnel; <NAME minus _URL>_USER/_PASS supply credentials)")
    a = ap.parse_args(argv)
    pm = ProfileManager(a.root)
    try:
        if a.cmd == "list":
            rows = pm.list()
            if not rows:
                print(f"no profiles under {pm.root}")
            for m in rows:
                print(f"{m.name:<28} uses={m.uses:<4} last={_ts(m.last_used_at)}  {m.notes}")
        elif a.cmd == "create":
            pm.get_or_create(a.name, notes=a.notes); print(pm.data_dir(a.name))
        elif a.cmd == "path":
            pm.get(a.name); print(pm.data_dir(a.name))
        elif a.cmd == "delete":
            if not a.force and input(f"delete profile {a.name!r} and its cookies? [y/N] ").lower() != "y":
                return 1
            pm.delete(a.name); print("deleted")
        elif a.cmd == "warmup":
            proxy = proxy_from_env(a.proxy_env) if a.proxy_env else None
            print(f"Opening {a.url} in profile {a.name!r}"
                  + (f" via proxy {proxy['server']}" if proxy else " (direct)")
                  + ". Pass any check, then CLOSE the window.")
            asyncio.run(pm.warmup(a.name, a.url, channel=a.channel or None, proxy=proxy,
                                  timeout_s=a.timeout))
            print("profile saved")
    except (ProfileError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
