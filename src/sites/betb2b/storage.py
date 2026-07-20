"""JSON persistence for BetB2B scrape output — optional gzip, transparent read.

The BetB2B feeds are terse-key JSON (``T``/``E``/``C``/``O1``…) and a full
card's ``GetGameZip`` odds run to hundreds of markets/selections per event.
Raw captures and full scrape results are therefore **large and highly
compressible** — gzip typically shrinks them ~85–90% because the key set
repeats on every object. Small human-facing files (a run summary, an events
preview) stay uncompressed so they're greppable and openable at a glance.

Design:

* :func:`dump_json` — write a JSON-serializable object. ``compress`` defaults
  to *auto*: gzip when the path ends in ``.gz`` **or** the serialized payload
  exceeds :data:`COMPRESS_THRESHOLD_BYTES`; otherwise plain text. Pass
  ``compress=True``/``False`` to force it. A ``.gz`` suffix is added when
  compressing a path that lacks one, and the *actual* path written is returned.
* :func:`load_json` — read back **transparently**: gzip is detected by magic
  bytes (``1f 8b``), not just the extension, so a mis-named file still loads.
* :func:`compress_file` / :func:`decompress_file` — convert an existing file
  in place-adjacent (``x.json`` ↔ ``x.json.gz``).

This keeps ``gzip`` (stdlib, universal, streamable) as the wire format — no
brotli dependency — and makes ``compress`` an output detail the rest of the
scraper never has to think about: everything reads through :func:`load_json`.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

__all__ = [
    "COMPRESS_THRESHOLD_BYTES",
    "GZIP_MAGIC",
    "dump_json",
    "load_json",
    "compress_file",
    "decompress_file",
    "is_gzipped",
]

PathLike = str | Path

# Serialized payloads larger than this auto-compress under ``compress=None``.
# 64 KiB: below it the gzip header + loss of grep-ability isn't worth ~a few KB;
# above it the feeds' repetitive keys compress dramatically.
COMPRESS_THRESHOLD_BYTES = 64 * 1024

# gzip files start with 0x1f 0x8b — the reliable "is this compressed?" signal.
GZIP_MAGIC = b"\x1f\x8b"


def _serialize(obj: Any, *, indent: int | None) -> bytes:
    """JSON-encode ``obj`` to UTF-8 bytes. ``default=str`` mirrors the CLI so
    datetimes / dataclasses that slipped through still serialize."""
    return json.dumps(obj, indent=indent, default=str, ensure_ascii=False).encode("utf-8")


def dump_json(
    obj: Any,
    path: PathLike,
    *,
    compress: bool | None = None,
    indent: int | None = 2,
    gzip_level: int = 6,
) -> Path:
    """Write ``obj`` as JSON to ``path``; return the path actually written.

    Args:
        obj: any JSON-serializable object (``default=str`` handles the rest).
        path: destination file. If it ends in ``.gz`` it is always compressed.
        compress: ``None`` (default) = auto — compress when the path ends in
            ``.gz`` or the payload exceeds :data:`COMPRESS_THRESHOLD_BYTES`.
            ``True``/``False`` force it (a ``.gz`` suffix is appended when
            forcing compression on a plain path).
        indent: JSON indent (``None`` = compact — best paired with compression).
        gzip_level: gzip compression level 0–9 (default 6, a good size/time
            trade-off).
    """
    path = Path(path)
    payload = _serialize(obj, indent=indent)

    ends_gz = path.suffix == ".gz"
    if compress is None:
        do_compress = ends_gz or len(payload) > COMPRESS_THRESHOLD_BYTES
    else:
        do_compress = bool(compress)

    if do_compress and not ends_gz:
        path = path.with_suffix(path.suffix + ".gz")

    path.parent.mkdir(parents=True, exist_ok=True)
    if do_compress:
        path.write_bytes(_gzip_bytes(payload, gzip_level))
    else:
        path.write_bytes(payload)
    return path


def _gzip_bytes(payload: bytes, gzip_level: int) -> bytes:
    """gzip ``payload`` deterministically — no embedded filename, ``mtime=0`` —
    so identical input yields identical bytes (stable diffs, cache-friendly)."""
    import io

    buf = io.BytesIO()
    # filename="" keeps the source name out of the gzip header.
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf,
                       compresslevel=gzip_level, mtime=0) as fh:
        fh.write(payload)
    return buf.getvalue()


def is_gzipped(path: PathLike) -> bool:
    """True if ``path`` begins with the gzip magic bytes (extension-agnostic)."""
    path = Path(path)
    try:
        with open(path, "rb") as fh:
            return fh.read(2) == GZIP_MAGIC
    except OSError:
        return False


def load_json(path: PathLike) -> Any:
    """Read JSON from ``path``, decompressing transparently.

    Detection is by magic bytes, so a gzipped file that lost its ``.gz``
    suffix (or a plain file that gained one) still loads correctly.
    """
    path = Path(path)
    raw = path.read_bytes()
    if raw[:2] == GZIP_MAGIC:
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def compress_file(src: PathLike, dst: PathLike | None = None, *, gzip_level: int = 6) -> Path:
    """Gzip an existing JSON file. ``dst`` defaults to ``<src>.gz``. Returns dst."""
    src = Path(src)
    dst = Path(dst) if dst else src.with_suffix(src.suffix + ".gz")
    data = src.read_bytes()
    if data[:2] != GZIP_MAGIC:  # don't double-compress
        dst.write_bytes(_gzip_bytes(data, gzip_level))
    else:
        dst.write_bytes(data)
    return dst


def decompress_file(src: PathLike, dst: PathLike | None = None) -> Path:
    """Inflate a gzipped JSON file. ``dst`` defaults to ``src`` minus ``.gz``
    (or ``<src>.json`` if there's no ``.gz`` suffix to strip). Returns dst."""
    src = Path(src)
    if dst is not None:
        dst = Path(dst)
    elif src.suffix == ".gz":
        dst = src.with_suffix("")  # foo.json.gz -> foo.json
    else:
        dst = src.with_suffix(src.suffix + ".json")
    data = src.read_bytes()
    if data[:2] == GZIP_MAGIC:
        data = gzip.decompress(data)
    dst.write_bytes(data)
    return dst
