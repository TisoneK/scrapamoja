"""Snapshot normalizer for Linebet captured API responses.

The goal: turn a raw captured response (which contains tons of volatile
data — timestamps, cookies, request IDs, geolocation codes, long hash
paths) into a STABLE JSON shape that can be:

  1. Committed to git as a fixture
  2. Diffed between runs to detect API schema drift
  3. Used as a regression-test input

The normalizer is intentionally lossy — it keeps only the fields that
matter for understanding the API contract:

  * The endpoint path (stripped of volatile query params)
  * The HTTP method + status
  * The response content-type
  * The DECODED JSON body, with volatile values redacted
  * The set of request headers that affect the response (auth, app
    headers) — values are NOT kept, only their presence

Volatile things we strip:
  * Query params: ``_t``, ``ts``, ``timestamp``, ``csrf``,
    ``d=linebet.com``, ``g=<geo>``, ``p=<project>`` (kept structurally,
    values redacted)
  * Cookies (always)
  * Hashes in fatman-api paths
  * Per-request IDs in headers (``x-request-id``, ``traceparent``)
  * Timestamps inside JSON bodies (``ts``, ``timestamp``, ``updatedAt``)
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union


# Query params whose VALUES are volatile (redact to "<value>")
_VOLATILE_QUERY_PARAMS: Set[str] = {
    "_t", "ts", "timestamp", "t", "csrf", "token", "csrfToken",
    "sessionId", "requestId", "nonce",
}

# Query params that we keep the NAME of but redact the value of because
# they are environment-specific (geo code, project ID, etc.)
_ENV_QUERY_PARAMS: Set[str] = {
    "d",    # domain
    "g",    # geo code
    "p",    # project ID
    "country",
    "lang",  # actually stable but redact for consistency
}

# Request header names that affect the response — we record their
# PRESENCE but not their values (values often contain cookies/tokens).
_SIGNAL_REQUEST_HEADERS: Set[str] = {
    "x-svc-source",
    "x-app-n",
    "x-requested-with",
    "is-srv",
    "content-type",
    "accept",
    "accept-language",
    "origin",
    "referer",
    "sec-fetch-dest",
    "sec-fetch-mode",
    "sec-fetch-site",
}

# Headers we never keep (even the name) — pure noise
_NOISE_HEADER_PREFIXES = (
    "sec-ch-ua",          # client hint, browser-version-specific
    "accept-encoding",    # always same
    "upgrade-insecure-requests",
    "user-agent",         # logged separately
)

# JSON keys (top-level + nested) whose values are volatile.
# Keys are compared case-insensitively (every entry here is lowercase).
_VOLATILE_JSON_KEYS: Set[str] = {
    "ts", "timestamp", "updatedat", "createdat", "expiresat",
    "sessionid", "token", "csrf", "csrftoken", "nonce",
    "requestid", "traceid", "spanid",
    "ip", "ipaddress",
}

# Max body size to keep in a normalized snapshot (chars). Larger bodies
# are truncated with a marker — keeps the repo small.
_MAX_BODY_CHARS = 8000


def normalize_captured_response(
    url: str,
    status: int,
    method: str,
    request_headers: Dict[str, str],
    response_headers: Dict[str, str],
    body: Optional[Union[str, bytes]],
) -> Dict[str, Any]:
    """Normalize a single captured response into a stable, diffable dict.

    Args:
        url: Full response URL (query string included)
        status: HTTP status code
        method: HTTP method (GET / POST / ...)
        request_headers: Request headers as a dict
        response_headers: Response headers as a dict
        body: Response body (text or bytes). If bytes, decoded as UTF-8
            with errors="replace".

    Returns:
        A stable dict suitable for committing to git. Same input always
        produces the same output (modulo non-deterministic dict ordering
        in the source JSON, which we sort).
    """
    # Decode body if needed
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    body = body or ""

    # Parse the URL into path + redacted query
    path, query = _split_url(url)
    redacted_query = _redact_query(query)

    # Try to parse the body as JSON. If it parses, walk it and redact
    # volatile keys; otherwise keep it as a (truncated) string.
    parsed_body: Any
    if body and _looks_like_json(body, response_headers):
        try:
            parsed_body = json.loads(body)
            parsed_body = _redact_volatile_json_keys(parsed_body)
        except (json.JSONDecodeError, ValueError):
            parsed_body = _truncate_str(body, _MAX_BODY_CHARS)
    else:
        parsed_body = _truncate_str(body, _MAX_BODY_CHARS)

    return {
        "path": path,
        "query": redacted_query,
        "method": method.upper(),
        "status": status,
        "content_type": response_headers.get("content-type", ""),
        "request_header_keys": sorted(
            k for k in request_headers
            if k.lower() in _SIGNAL_REQUEST_HEADERS
            and not any(k.lower().startswith(p) for p in _NOISE_HEADER_PREFIXES)
        ),
        "body": parsed_body,
        "body_sha256": _sha256(_stable_serialize(parsed_body)),
        "body_bytes": len(body),
    }


def normalize_capture_list(captures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize a list of raw captures into a snapshot bundle.

    The bundle has:
      * ``metadata`` — when/how the snapshot was made, count of captures
      * ``endpoints`` — list of normalized captures, deduplicated by
        ``(path, method, status, body_sha256)`` and sorted by path

    Dedup matters because the same endpoint is often called multiple
    times in one page load (e.g. /fatman-api/event.json fires 5x). The
    dedup key keeps only the first occurrence so the snapshot is stable.
    """
    normalized: List[Dict[str, Any]] = []
    seen_keys: Set[str] = set()

    for cap in captures:
        norm = normalize_captured_response(
            url=cap.get("url", ""),
            status=cap.get("status", 0),
            method=cap.get("method", "GET"),
            request_headers=cap.get("request_headers", {}),
            response_headers=cap.get("response_headers", {}),
            body=cap.get("body") or cap.get("raw_bytes"),
        )
        dedup_key = f"{norm['path']}|{norm['method']}|{norm['status']}|{norm['body_sha256']}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        normalized.append(norm)

    normalized.sort(key=lambda n: (n["path"], n["method"], n["status"]))

    return {
        "metadata": {
            "normalized_at": datetime.now(timezone.utc).isoformat(),
            "normalizer_version": "1.0.0",
            "capture_count": len(captures),
            "unique_endpoint_count": len(normalized),
        },
        "endpoints": normalized,
    }


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _split_url(url: str) -> tuple[str, str]:
    """Split a URL into (path_without_query, query_string)."""
    if "?" in url:
        path, query = url.split("?", 1)
    else:
        path, query = url, ""
    # Strip the long hash out of fatman-api paths so the same endpoint
    # doesn't look different across deployments.
    path = re.sub(
        r"(/fatman-api/)[0-9a-f]{32,}",
        r"\1<hash>",
        path,
    )
    return path, query


def _redact_query(query: str) -> Dict[str, str]:
    """Turn a query string into a sorted dict with volatile values redacted."""
    if not query:
        return {}
    out: Dict[str, str] = {}
    for pair in query.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
        else:
            k, v = pair, ""
        kl = k.lower()
        if kl in _VOLATILE_QUERY_PARAMS:
            out[k] = "<redacted>"
        elif kl in _ENV_QUERY_PARAMS:
            out[k] = "<env>"
        else:
            # Keep the value but URL-decode it for readability
            from urllib.parse import unquote
            out[k] = unquote(v)
    return dict(sorted(out.items()))


def _looks_like_json(body: str, response_headers: Dict[str, str]) -> bool:
    """Heuristic: does this body look like JSON?"""
    ct = response_headers.get("content-type", "").lower()
    if "json" in ct:
        return True
    stripped = body.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _redact_volatile_json_keys(obj: Any) -> Any:
    """Recursively walk a JSON-ish structure and redact volatile keys."""
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in _VOLATILE_JSON_KEYS:
                out[k] = "<redacted>"
            else:
                out[k] = _redact_volatile_json_keys(v)
        return out
    if isinstance(obj, list):
        return [_redact_volatile_json_keys(v) for v in obj]
    return obj


def _truncate_str(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + f"... <truncated, {len(s)} bytes total>"


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:16]


def _stable_serialize(obj: Any) -> str:
    """Serialize obj to a stable string (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


# ---------------------------------------------------------------------------
# CLI entry: python -m src.sites.linebet.snapshots.normalize <input> <output>
# ---------------------------------------------------------------------------
def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Normalize a captures JSON file into a stable snapshot."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to a captures JSON file (list of {url, status, method, request_headers, response_headers, body}).",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Path to write the normalized snapshot to.",
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="Pretty-print JSON output (default: compact).",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=__import__("sys").stderr)
        return 1

    raw = json.loads(args.input.read_text())
    if not isinstance(raw, list):
        print(f"ERROR: expected a JSON list, got {type(raw).__name__}", file=__import__("sys").stderr)
        return 1

    snapshot = normalize_capture_list(raw)
    indent = 2 if args.pretty else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=indent, default=str))
    print(
        f"Normalized {snapshot['metadata']['capture_count']} captures "
        f"into {snapshot['metadata']['unique_endpoint_count']} unique endpoints."
    )
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
