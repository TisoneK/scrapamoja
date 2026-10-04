"""``python -m src.security`` — inspect or reset per-site block state."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time

from . import egress
from .ledger import BlockLedger
from .tiers import ALL_TIERS


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m src.security", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="show every site's block state")
    p = sub.add_parser("clear", help="forget a site's blocks, cooldown and escalation tier")
    p.add_argument("site")
    e = sub.add_parser("evidence", help="what blocked/failed requests looked like (captured automatically)")
    e.add_argument("--days", type=float, default=1.0, help="how far back to look (default 1)")
    e.add_argument("--site", default=None)
    e.add_argument("--tail", type=int, default=0, help="also print the last N raw records")
    a = ap.parse_args(argv)
    if a.cmd == "evidence":
        return _evidence(a)
    led = BlockLedger()
    if a.cmd == "status":
        if egress.declared_restricted():
            print(f"this machine is declared geo-restricted ({egress.ENV}=1): page loads need a proxy")
        for site, at in sorted(egress.restricted_sites().items()):
            when = dt.datetime.fromtimestamp(at).strftime("%Y-%m-%d %H:%M")
            print(f"{site:<24} PAGE LOADS OFF without a proxy (country-blocked at {when}); feeds unaffected")
        if not led._sites:
            print(f"no blocks recorded ({led.path})")
        for site, st in sorted(led._sites.items()):
            left, _ = led.cooldown_left(site)
            when = dt.datetime.fromtimestamp(st.last_block_at).strftime("%Y-%m-%d %H:%M") if st.last_block_at else "-"
            tier = ALL_TIERS[min(st.browser_tier, len(ALL_TIERS) - 1)].name
            print(f"{site:<24} last={st.last_type or '-'}/{st.last_vendor or '-'} at {when}  "
                  f"streak={st.consecutive_blocks} total={st.total_blocks} tier={tier}  "
                  + (f"COOLDOWN {left / 60:.0f} min left" if left else "ready"))
    else:
        led.clear(a.site)
        lifted = egress.clear_restricted(a.site)
        print(f"cleared {a.site}" + (" (page loads allowed again)" if lifted else ""))
    return 0


def _evidence(a) -> int:
    from .evidence import EvidenceLog
    log = EvidenceLog()
    recs = log.read(days=a.days, site=a.site)
    if not recs:
        print(f"no evidence in the last {a.days:g} day(s) ({log.dir})")
        return 0
    print(f"{len(recs)} record(s) in the last {a.days:g} day(s)  ({log.dir})\n")
    for g in log.summarise(recs):
        what = g["type"] or g["error"] or g["kind"]
        vendor = f"/{g['vendor']}" if g["vendor"] else ""
        status = f" status={g['status']}" if g["status"] else ""
        print(f"{g['count']:>5}x  {g['site']:<12} {g['kind']:<12} {what}{vendor}{status}")
        print(f"        {g['first']} -> {g['last']}")
        ex = g["example"] or {}
        if ex.get("url") or ex.get("body"):
            print(f"        e.g. {ex.get('url') or ''}  {(ex.get('body') or '')[:110]!r}")
    if a.tail:
        print("\nlast raw records:")
        for r in recs[-a.tail:]:
            print(json.dumps(r, default=str)[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
