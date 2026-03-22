#!/usr/bin/env python3
"""Unit tests for mistakes-generator.py"""
import sys
import subprocess
import tempfile
import json
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "mistakes-generator.py"


def run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + args,
                          capture_output=True, text=True)


def test_help():
    r = run(["--help"])
    assert r.returncode == 0


def test_get_next_counter_empty_dir():
    with tempfile.TemporaryDirectory() as d:
        r = run(["--get-next-counter", "--sessions-dir", d, "--output-dir", d])
        assert r.returncode == 0
        assert r.stdout.strip() == "1"


def test_generate_clean_cycle():
    with tempfile.TemporaryDirectory() as d:
        r = run(["--story-id", "STORY-1.1", "--output-dir", d])
        assert r.returncode == 0
        files = list(Path(d).glob("ADVISOR_SESSION_MISTAKES_*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "STORY-1.1" in content


def test_counter_increments():
    with tempfile.TemporaryDirectory() as d:
        run(["--story-id", "STORY-1.1", "--output-dir", d])
        run(["--story-id", "STORY-1.2", "--output-dir", d])
        files = sorted(Path(d).glob("ADVISOR_SESSION_MISTAKES_*.md"))
        assert len(files) == 2
        assert "001" in files[0].name
        assert "002" in files[1].name


if __name__ == "__main__":
    tests = [test_help, test_get_next_counter_empty_dir,
             test_generate_clean_cycle, test_counter_increments]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
