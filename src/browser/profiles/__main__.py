"""``python -m src.browser.profiles`` — manage persistent browser profiles."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import sys

from .manager import ProfileError, ProfileManager


def _ts(t: float) -> str:
    return dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M") if t else "never"


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
            print(f"Opening {a.url} in profile {a.name!r}. Pass any check, then CLOSE the window.")
            asyncio.run(pm.warmup(a.name, a.url, channel=a.channel or None, timeout_s=a.timeout))
            print("profile saved")
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
