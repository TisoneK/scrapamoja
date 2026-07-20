"""Unit tests for BetB2B JSON storage (gzip write + transparent read).

Run with::

    pytest src/sites/betb2b/tests/test_storage.py -v
"""

from __future__ import annotations

import gzip
import json

from src.sites.betb2b.storage import (
    COMPRESS_THRESHOLD_BYTES,
    GZIP_MAGIC,
    compress_file,
    decompress_file,
    dump_json,
    is_gzipped,
    load_json,
)


# A payload that mimics the terse-key feed shape and is large + repetitive,
# so it comfortably crosses the auto-compress threshold and compresses well.
def _big_payload() -> list:
    return [
        {"I": i, "O1": "Team A", "O2": "Team B", "SN": "Basketball",
         "E": [{"T": t, "C": 1.5 + t * 0.01, "P": t} for t in range(40)]}
        for i in range(300)
    ]


def test_roundtrip_plain(tmp_path):
    obj = {"a": 1, "b": [1, 2, 3], "c": "x"}
    path = dump_json(obj, tmp_path / "small.json", compress=False)
    assert path.suffix == ".json"
    assert not is_gzipped(path)
    assert load_json(path) == obj


def test_roundtrip_gzip_forced(tmp_path):
    obj = {"a": 1, "b": [1, 2, 3]}
    path = dump_json(obj, tmp_path / "forced.json", compress=True)
    assert path.name == "forced.json.gz"
    assert is_gzipped(path)
    assert path.read_bytes()[:2] == GZIP_MAGIC
    assert load_json(path) == obj


def test_gz_extension_always_compresses(tmp_path):
    obj = {"tiny": True}
    path = dump_json(obj, tmp_path / "explicit.json.gz")
    assert path.name == "explicit.json.gz"
    assert is_gzipped(path)
    assert load_json(path) == obj


def test_auto_compresses_large_payload(tmp_path):
    obj = _big_payload()
    path = dump_json(obj, tmp_path / "auto.json")  # compress=None (auto)
    # Serialized size exceeds the threshold, so it should have compressed.
    assert path.name == "auto.json.gz"
    assert is_gzipped(path)
    # Compression is real: file is far smaller than the raw JSON.
    raw_size = len(json.dumps(obj).encode())
    assert raw_size > COMPRESS_THRESHOLD_BYTES
    assert path.stat().st_size < raw_size // 2
    assert load_json(path) == obj


def test_auto_keeps_small_payload_plain(tmp_path):
    obj = {"small": "payload"}
    path = dump_json(obj, tmp_path / "auto_small.json")  # compress=None
    assert path.name == "auto_small.json"
    assert not is_gzipped(path)


def test_load_json_detects_gzip_by_magic_not_extension(tmp_path):
    # A gzipped file mis-named without .gz must still load.
    obj = {"mislabeled": 42}
    misnamed = tmp_path / "mislabeled.json"
    with gzip.GzipFile(misnamed, "wb", mtime=0) as fh:
        fh.write(json.dumps(obj).encode())
    assert is_gzipped(misnamed)
    assert load_json(misnamed) == obj


def test_compress_then_decompress_file(tmp_path):
    obj = _big_payload()
    plain = dump_json(obj, tmp_path / "card.json", compress=False)
    gz = compress_file(plain)
    assert gz.name == "card.json.gz"
    assert is_gzipped(gz)
    assert gz.stat().st_size < plain.stat().st_size

    back = decompress_file(gz)
    assert back.name == "card.json"  # foo.json.gz -> foo.json
    assert json.loads(back.read_text()) == obj


def test_compress_file_does_not_double_compress(tmp_path):
    obj = {"a": 1}
    gz = dump_json(obj, tmp_path / "x.json", compress=True)
    # Re-compressing an already-gzipped file yields a still-loadable file.
    twice = compress_file(gz, tmp_path / "y.gz")
    assert load_json(twice) == obj


def test_deterministic_bytes(tmp_path):
    # mtime=0 → identical input produces identical gzip bytes (stable diffs).
    obj = _big_payload()
    a = dump_json(obj, tmp_path / "a.json.gz")
    b = dump_json(obj, tmp_path / "b.json.gz")
    assert a.read_bytes() == b.read_bytes()
