"""Snapshot normalizer for captured network responses.

The existing :class:`src.core.snapshot.SnapshotManager` captures browser
state (HTML, screenshots, network metadata) into :class:`SnapshotBundle`s
on triggers (errors, retries, etc.). Its ``_capture_network_logs`` helper
records URL/status/method/response-headers but NOT response bodies or
request headers, and it doesn't dedupe or normalize.

This module is the **post-processing layer** that turns a list of raw
network captures (however they were made — NetworkInterceptor, HAR
replay, snapshot system's own capture, etc.) into a STABLE, DIFFABLE
JSON shape. Stable means: same input always produces the same output,
so two snapshots taken days apart can be diffed to detect API schema
drift.

Volatile things this module redacts:
  * Query params: ``_t``, ``ts``, ``timestamp``, ``csrf``, ``token``,
    ``csrfToken``, ``sessionId``, ``requestId``, ``nonce`` — values
    replaced with ``"<redacted>"``
  * Env-specific query params (``d``, ``g``, ``p``, ``country``, ``lang``)
    — values replaced with ``"<env>"`` because they vary by deployment
    but the param NAME is structurally meaningful
  * Long hashes in URL paths (e.g. ``/fatman-api/<40-char-hex>/...``)
    — replaced with ``<hash>`` so the same endpoint doesn't look
    different across deployments
  * Cookies (always dropped — never appear in normalized output)
  * Per-request IDs in headers (``x-request-id``, ``traceparent``)
  * Volatile JSON keys recursively (``ts``, ``sessionId``, ``token``,
    ``traceId``, ``ip``, etc.) — values replaced with ``"<redacted>"``

What this module KEEPS:
  * The endpoint path (with hashes stripped)
  * The HTTP method + status
  * The response content-type
  * The set of request-header NAMES that affect the response (auth, app
    headers) — values are NOT kept, only their presence
  * The decoded JSON body, with volatile values redacted
  * A ``body_sha256`` hash for drift detection

Public API:

    from src.core.snapshot.normalize import (
        normalize_captured_response,
        normalize_capture_list,
        NormalizerConfig,
    )

CLI:

    python -m src.core.snapshot.normalize <input.json> <output.json>
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import unquote


# ---------------------------------------------------------------------------
# Default redaction rules
# ---------------------------------------------------------------------------
# These are sensible defaults that work for most sportsbook / SPA APIs.
# Sites with unusual schemes can override via ``NormalizerConfig``.

DEFAULT_VOLATILE_QUERY_PARAMS: Set[str] = {
    "_t", "ts", "timestamp", "t", "csrf", "token", "csrfToken",
    "sessionId", "requestId", "nonce",
}

DEFAULT_ENV_QUERY_PARAMS: Set[str] = {
    "d", "g", "p", "country", "lang", "region", "locale",
}

DEFAULT_SIGNAL_REQUEST_HEADERS: Set[str] = {
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
    "authorization",         # bearer tokens — presence only, never value
    "x-csrf-token",
    "x-auth-token",
}

DEFAULT_NOISE_HEADER_PREFIXES: tuple[str, ...] = (
    "sec-ch-ua",                      # client hints, browser-version-specific
    "accept-encoding",                # always same
    "upgrade-insecure-requests",
    "user-agent",                     # logged separately if needed
    "cookie",                         # never keep cookies in snapshots
    "set-cookie",
)

# JSON keys (top-level + nested) whose values are volatile.
# Keys are compared case-insensitively (every entry here is lowercase).
DEFAULT_VOLATILE_JSON_KEYS: Set[str] = {
    "ts", "timestamp", "updatedat", "createdat", "expiresat",
    "sessionid", "token", "csrf", "csrftoken", "nonce",
    "requestid", "traceid", "spanid",
    "ip", "ipaddress",
    "x-request-id", "traceparent",
}

# Default regex for hashes in URL paths. Matches 32+ hex chars (MD5/SHA1/SHA256)
# or 20+ base64 chars. Override or extend via ``NormalizerConfig.path_hash_patterns``.
DEFAULT_PATH_HASH_PATTERNS: List[str] = [
    r"(/fatman-api/)[0-9a-f]{32,}",          # Linebet fatman-api
    r"(/api/)[0-9a-f]{32,}",                 # generic /api/<hash>
    r"(/[a-z0-9-]+/)[0-9a-f]{40,}",          # generic /<resource>/<40+hex>
]

DEFAULT_MAX_BODY_CHARS = 8000


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
@dataclass
class NormalizerConfig:
    """Configuration for the snapshot normalizer.

    All fields have sensible defaults that work for most sportsbook / SPA
    APIs. Sites with unusual schemes can override individual fields without
    having to re-implement the normalizer.
    """

    volatile_query_params: Set[str] = field(
        default_factory=lambda: set(DEFAULT_VOLATILE_QUERY_PARAMS)
    )
    env_query_params: Set[str] = field(
        default_factory=lambda: set(DEFAULT_ENV_QUERY_PARAMS)
    )
    signal_request_headers: Set[str] = field(
        default_factory=lambda: set(DEFAULT_SIGNAL_REQUEST_HEADERS)
    )
    noise_header_prefixes: tuple[str, ...] = field(
        default_factory=lambda: DEFAULT_NOISE_HEADER_PREFIXES
    )
    volatile_json_keys: Set[str] = field(
        default_factory=lambda: set(DEFAULT_VOLATILE_JSON_KEYS)
    )
    path_hash_patterns: List[str] = field(
        default_factory=lambda: list(DEFAULT_PATH_HASH_PATTERNS)
    )
    max_body_chars: int = DEFAULT_MAX_BODY_CHARS
    normalizer_version: str = "1.0.0"

    def __post_init__(self) -> None:
        # All string sets must be lowercase for case-insensitive comparison.
        self.volatile_query_params = {k.lower() for k in self.volatile_query_params}
        self.env_query_params = {k.lower() for k in self.env_query_params}
        self.signal_request_headers = {k.lower() for k in self.signal_request_headers}
        self.volatile_json_keys = {k.lower() for k in self.volatile_json_keys}
        # Pre-compile path-hash patterns for speed.
        self._compiled_path_patterns: List[re.Pattern[str]] = [
            re.compile(p) for p in self.path_hash_patterns
        ]

    def strip_path_hashes(self, path: str) -> str:
        """Apply all path-hash patterns to redact hashes in a URL path."""
        for pat in self._compiled_path_patterns:
            path = pat.sub(
                lambda m: m.group(1) + "<hash>",
                path,
            )
        return path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def normalize_captured_response(
    url: str,
    status: int,
    method: str,
    request_headers: Dict[str, str],
    response_headers: Dict[str, str],
    body: Optional[Union[str, bytes]],
    config: Optional[NormalizerConfig] = None,
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
        config: Optional :class:`NormalizerConfig` override. Defaults to
            :data:`DEFAULT_NORMALIZER_CONFIG`.

    Returns:
        A stable dict suitable for committing to git. Same input always
        produces the same output (modulo non-deterministic dict ordering
        in the source JSON, which we sort).
    """
    cfg = config or DEFAULT_NORMALIZER_CONFIG

    # Decode body if needed
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    body = body or ""

    # Parse the URL into path + redacted query
    path, query = _split_url(url, cfg)
    redacted_query = _redact_query(query, cfg)

    # Try to parse the body as JSON. If it parses, walk it and redact
    # volatile keys; otherwise keep it as a (truncated) string.
    if body and _looks_like_json(body, response_headers):
        try:
            parsed_body = json.loads(body)
            parsed_body = _redact_volatile_json_keys(parsed_body, cfg)
        except (json.JSONDecodeError, ValueError):
            parsed_body = _truncate_str(body, cfg.max_body_chars)
    else:
        parsed_body = _truncate_str(body, cfg.max_body_chars)

    return {
        "path": path,
        "query": redacted_query,
        "method": method.upper(),
        "status": status,
        "content_type": response_headers.get("content-type", ""),
        "request_header_keys": sorted(
            k for k in request_headers
            if k.lower() in cfg.signal_request_headers
            and not any(k.lower().startswith(p) for p in cfg.noise_header_prefixes)
        ),
        "body": parsed_body,
        "body_sha256": _sha256(_stable_serialize(parsed_body)),
        "body_bytes": len(body),
    }


def normalize_capture_list(
    captures: List[Dict[str, Any]],
    config: Optional[NormalizerConfig] = None,
) -> Dict[str, Any]:
    """Normalize a list of raw captures into a snapshot bundle.

    The bundle has:
      * ``metadata`` — when/how the snapshot was made, count of captures
      * ``endpoints`` — list of normalized captures, deduplicated by
        ``(path, method, status, body_sha256)`` and sorted by path

    Dedup matters because the same endpoint is often called multiple
    times in one page load (e.g. analytics endpoints fire 5x). The
    dedup key keeps only the first occurrence so the snapshot is stable.
    """
    cfg = config or DEFAULT_NORMALIZER_CONFIG
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
            config=cfg,
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
            "normalizer_version": cfg.normalizer_version,
            "capture_count": len(captures),
            "unique_endpoint_count": len(normalized),
        },
        "endpoints": normalized,
    }


# Singleton default config — created once at import time.
DEFAULT_NORMALIZER_CONFIG = NormalizerConfig()


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _split_url(url: str, cfg: NormalizerConfig) -> tuple[str, str]:
    """Split a URL into (path_without_query, query_string), with hashes redacted."""
    if "?" in url:
        path, query = url.split("?", 1)
    else:
        path, query = url, ""
    path = cfg.strip_path_hashes(path)
    return path, query


def _redact_query(query: str, cfg: NormalizerConfig) -> Dict[str, str]:
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
        if kl in cfg.volatile_query_params:
            out[k] = "<redacted>"
        elif kl in cfg.env_query_params:
            out[k] = "<env>"
        else:
            out[k] = unquote(v)
    return dict(sorted(out.items()))


def _looks_like_json(body: str, response_headers: Dict[str, str]) -> bool:
    """Heuristic: does this body look like JSON?"""
    ct = response_headers.get("content-type", "").lower()
    if "json" in ct:
        return True
    stripped = body.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _redact_volatile_json_keys(obj: Any, cfg: NormalizerConfig) -> Any:
    """Recursively walk a JSON-ish structure and redact volatile keys."""
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in cfg.volatile_json_keys:
                out[k] = "<redacted>"
            else:
                out[k] = _redact_volatile_json_keys(v, cfg)
        return out
    if isinstance(obj, list):
        return [_redact_volatile_json_keys(v, cfg) for v in obj]
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
# CLI entry: python -m src.core.snapshot.normalize <input> <output>
# ---------------------------------------------------------------------------
def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Normalize a captures JSON file into a stable snapshot."
    )
    parser.add_argument(
        "input", type=Path,
        help="Path to a captures JSON file (list of {url, status, method, request_headers, response_headers, body}).",
    )
    parser.add_argument(
        "output", type=Path,
        help="Path to write the normalized snapshot to.",
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="Pretty-print JSON output (default: compact).",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1

    try:
        raw = json.loads(args.input.read_text())
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {args.input}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(raw, list):
        print(f"ERROR: expected a JSON list, got {type(raw).__name__}", file=sys.stderr)
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
