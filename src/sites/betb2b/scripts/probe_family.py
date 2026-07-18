"""BetB2B family generalization probe.

Reproduces the Session-11 family-wide probe documented in
`src/sites/linebet/RECON.md` "Generalizes to the 1xbet/BetB2B family":
through the operator's allowed-country proxy, hit
``/service-api/LineFeed/Get1x2_VZip`` on each candidate domain and
report whether the response looks like the shared feed microservice.

The "shared feed" signal is the 406 ``feed/NotAcceptableException``
envelope — the endpoint exists and behaves the same across skins; the
406 just means the bare probe lacked per-skin cookies/headers.

Usage::

    export BETB2B_PROXY_URL=http://bore.pub:1074
    export BETB2B_PROXY_USER=TisoneK
    export BETB2B_PROXY_PASS=Taalib01
    python -m src.sites.betb2b.scripts.probe_family
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


sys.path.insert(0, str(_repo_root()))


# Candidate domains. 1xbet.com (Cloudflare-fronted) + 1win.pro (different
# platform) are included for negative-test visibility.
CANDIDATE_DOMAINS = [
    "linebet.com",
    "melbet.com",
    "betwinner.com",
    "22bet.com",
    "megapari.com",
    "888starz.bet",
    "helabet.com",
    "paripesa.bet",
    "1xbet.com",     # Cloudflare-fronted — expect 403 challenge
    "1win.pro",      # Different platform — expect 200 HTML
]


async def probe_one(domain: str, proxy_url: str) -> dict:
    """Probe one domain's LineFeed endpoint."""
    import httpx

    url = (
        f"https://{domain}/service-api/LineFeed/Get1x2_VZip?"
        + urlencode({
            "count": "10", "lng": "en", "gr": "650", "mode": "4",
            "country": "87", "top": "true", "partner": "189",
            "virtualSports": "true",
        })
    )
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "is-srv": "false",
        "x-app-n": "__BETTING_APP__",
        "x-svc-source": "__BETTING_APP__",
        "x-requested-with": "XMLHttpRequest",
        "user-agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    }

    started = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(
            proxy=proxy_url, timeout=25.0, follow_redirects=True,
        ) as client:
            resp = await client.get(url, headers=headers)
            body_preview = resp.text[:600] if resp.text else ""
            # Sniff for the shared-feed 406 envelope.
            shared_feed_signal = (
                resp.status_code == 406
                and "NotAcceptableException" in body_preview
            )
            cloudflare_signal = (
                resp.status_code in (403, 503)
                and ("Just a moment" in body_preview or "cf-" in str(resp.headers))
            )
            return {
                "domain": domain,
                "status": resp.status_code,
                "bytes": len(resp.content),
                "content_type": resp.headers.get("content-type", ""),
                "shared_feed_signal": shared_feed_signal,
                "cloudflare_signal": cloudflare_signal,
                "latency_ms": (datetime.now(timezone.utc) - started).total_seconds() * 1000.0,
                "body_preview": body_preview[:300],
                "verdict": (
                    "shared_feed" if shared_feed_signal
                    else "cloudflare" if cloudflare_signal
                    else "different_platform" if resp.status_code == 200
                    else f"unhandled_{resp.status_code}"
                ),
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "domain": domain,
            "status": 0,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": (datetime.now(timezone.utc) - started).total_seconds() * 1000.0,
            "verdict": "unreachable",
        }


async def main() -> int:
    proxy_url = os.environ.get("BETB2B_PROXY_URL")
    user = os.environ.get("BETB2B_PROXY_USER", "")
    pw = os.environ.get("BETB2B_PROXY_PASS", "")
    if proxy_url and user and pw and "@" not in proxy_url:
        from urllib.parse import urlparse, urlunparse

        p = urlparse(proxy_url)
        netloc = f"{user}:{pw}@{p.hostname}"
        if p.port:
            netloc += f":{p.port}"
        proxy_url = urlunparse(p._replace(netloc=netloc))

    if not proxy_url:
        print("BETB2B_PROXY_URL not set — aborting.", file=sys.stderr)
        return 1

    print(f"Probing {len(CANDIDATE_DOMAINS)} candidate domains through proxy ...",
          flush=True)
    results = []
    for domain in CANDIDATE_DOMAINS:
        print(f"  → {domain} ...", flush=True, end=" ")
        r = await probe_one(domain, proxy_url)
        results.append(r)
        verdict = r.get("verdict", "?")
        status = r.get("status", "?")
        print(f"status={status} verdict={verdict}", flush=True)

    # Save full report.
    out_dir = Path("/home/z/my-project/download/betb2b_family_probe")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "family_probe.json"
    report = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "proxy": (proxy_url or "").split("@")[-1] if proxy_url else None,  # redact creds
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nReport: {report_path}", flush=True)

    # Summary.
    by_verdict: dict[str, list[str]] = {}
    for r in results:
        by_verdict.setdefault(r.get("verdict", "?"), []).append(r["domain"])
    print("\nSummary by verdict:")
    for v, ds in by_verdict.items():
        print(f"  {v}: {ds}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
