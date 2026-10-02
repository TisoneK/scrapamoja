"""``python -m src.security`` — inspect or reset per-site block state."""

from __future__ import annotations

import argparse
import datetime as dt
import time

from .ledger import BlockLedger
from .tiers import ALL_TIERS


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m src.security", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="show every site's block state")
    p = sub.add_parser("clear", help="forget a site's blocks, cooldown and escalation tier")
    p.add_argument("site")
    a = ap.parse_args(argv)
    led = BlockLedger()
    if a.cmd == "status":
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
        print(f"cleared {a.site}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
