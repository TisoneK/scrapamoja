#!/usr/bin/env python3
"""Probe whether a host (e.g. a Railway region) can reach betb2b unblocked.

Run it from wherever you're considering deploying:
    python scripts/railway_geo_probe.py            # local
    railway run python scripts/railway_geo_probe.py # on Railway (its egress IP)

Checks the two things the scraper needs:
  1. DISCOVERY  — the SPA page (200 = usable, 203/redirect to /en/block = flagged)
  2. DATA       — GetGameZip per-match endpoint (200 = works even from datacenters)

Prints a verdict: proxy-free / proxy-for-discovery-only / needs-residential-proxy.
"""
import json
import urllib.request
import urllib.error

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
BASE = "https://linebet.com"
DISCOVERY = f"{BASE}/en/live/basketball"
# A per-match data call — id doesn't need to exist; 200 vs block is what matters.
DATA = (f"{BASE}/service-api/LiveFeed/GetGameZip?id=1&isSubGames=true&grMode=4"
        "&lng=en&country=87&partner=189&gr=650")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.geturl(), r.read(200).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:  # noqa: BLE001
        return 0, url, str(e)[:80]


def main():
    # egress IP + country (best-effort)
    try:
        who = json.loads(_get("https://ipapi.co/json/")[2] or "{}")
        print(f"egress: {who.get('ip')} · {who.get('country_name')} · {who.get('org')}")
    except Exception:
        pass

    ds, durl, _ = _get(DISCOVERY)
    blocked = ds == 203 or "/en/block" in durl
    print(f"DISCOVERY (SPA page): HTTP {ds}  final={durl}  -> {'BLOCKED' if blocked else 'OK'}")

    xs, _, xbody = _get(DATA)
    data_ok = xs == 200 and ("Success" in xbody or "{" in xbody)
    print(f"DATA (GetGameZip):    HTTP {xs}  -> {'OK' if data_ok else 'blocked/none'}")

    print("\nVERDICT:")
    if not blocked and data_ok:
        print("  ✅ PROXY-FREE — this host reaches both discovery + data. Deploy here as-is.")
    elif blocked and data_ok:
        print("  🟡 PROXY-FOR-DISCOVERY-ONLY — data works direct; add a small residential")
        print("     proxy (any supported country) just for the HTML harvest step.")
    else:
        print("  🔴 NEEDS RESIDENTIAL PROXY — both paths flagged; route through a")
        print("     residential IP in a supported country (BETB2B_PROXY_URL).")


if __name__ == "__main__":
    main()
