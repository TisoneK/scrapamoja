"""Convert HAR entries into framework snapshot shapes.

This module is the glue between the HAR format (browser-standard, but
external) and the framework's own capture/snapshot shapes. It lets any
code that consumes :class:`src.network.interception.CapturedResponse`
or :func:`src.core.snapshot.normalize.normalize_capture_list` also
consume HAR files — so HAR replays work transparently with extractors
that were written for live interception.

Public API:

    from src.network.har.to_snapshot import (
        har_entries_to_captures,
        har_to_normalized_snapshot,
    )
"""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional

from src.core.snapshot.normalize import (
    NormalizerConfig,
    normalize_capture_list,
)
from src.network.interception.models import CapturedResponse


def _har_entry_to_capture_dict(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a single HAR entry into the capture-dict shape.

    The capture-dict shape is what
    :func:`src.core.snapshot.normalize.normalize_captured_response` and
    :func:`src.network.har.replay.har_entries_to_captures` both expect::

        {
            "url": str,
            "status": int,
            "method": str,
            "request_headers": Dict[str, str],
            "response_headers": Dict[str, str],
            "body": Optional[str],   # decoded body text (None if bodyless)
        }
    """
    req = entry.get("request", {})
    resp = entry.get("response", {})
    url = req.get("url", "")

    # Decode body. HAR stores it under response.content.text, with
    # encoding under response.content.encoding ("base64" typically).
    content = resp.get("content", {})
    body_text: Optional[str] = None
    if content.get("text"):
        if content.get("encoding") == "base64":
            try:
                raw = base64.b64decode(content["text"])
                body_text = raw.decode("utf-8", errors="replace")
            except Exception:
                body_text = "<base64 decode failed>"
        else:
            body_text = content["text"]

    # Flatten headers (HAR uses list of {name, value})
    req_headers = {h["name"].lower(): h["value"]
                   for h in req.get("headers", [])
                   if "name" in h and "value" in h}
    resp_headers = {h["name"].lower(): h["value"]
                    for h in resp.get("headers", [])
                    if "name" in h and "value" in h}

    return {
        "url": url,
        "status": resp.get("status", 0),
        "method": req.get("method", "GET"),
        "request_headers": req_headers,
        "response_headers": resp_headers,
        "body": body_text or "",
    }


def har_entries_to_captures(har: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert all entries in a HAR bundle into capture-dicts.

    Args:
        har: A parsed HAR dict (top-level shape ``{"log": {"entries": [...]}}``)

    Returns:
        List of capture-dicts, one per HAR entry. Empty bodies are
        preserved as ``""`` (so 204/304 responses still produce a capture).
    """
    entries = har.get("log", {}).get("entries", [])
    return [_har_entry_to_capture_dict(e) for e in entries]


def har_to_captured_responses(har: Dict[str, Any]) -> List[CapturedResponse]:
    """Convert a HAR bundle into a list of framework
    :class:`CapturedResponse` objects.

    Use this when you have code that consumes ``CapturedResponse``
    instances (e.g. an extractor written for live
    :class:`NetworkInterceptor` use) and you want to feed it a HAR
    replay instead.
    """
    captures = har_entries_to_captures(har)
    out: List[CapturedResponse] = []
    for cap in captures:
        body_bytes: Optional[bytes] = None
        if cap["body"]:
            body_bytes = cap["body"].encode("utf-8", errors="replace")
        out.append(CapturedResponse(
            url=cap["url"],
            status=cap["status"],
            headers=cap["response_headers"],
            raw_bytes=body_bytes,
        ))
    return out


def har_to_normalized_snapshot(
    har: Dict[str, Any],
    config: Optional[NormalizerConfig] = None,
    url_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Convert a HAR bundle directly into a normalized snapshot.

    This is the one-shot "give me a stable snapshot from a HAR file"
    helper. It chains :func:`har_entries_to_captures` →
    :func:`normalize_capture_list`.

    Args:
        har: A parsed HAR dict.
        config: Optional :class:`NormalizerConfig` override.
        url_filter: Optional list of URL substrings — only entries whose
            URL contains at least one of these are kept. Useful for
            filtering a HAR down to a specific site's API (e.g.
            ``url_filter=["/bff-api/", "/fatman-api/"]``).

    Returns:
        A normalized snapshot bundle (same shape as
        :func:`normalize_capture_list`).
    """
    captures = har_entries_to_captures(har)
    if url_filter:
        captures = [
            c for c in captures
            if any(p in c["url"] for p in url_filter)
        ]
    return normalize_capture_list(captures, config=config)
