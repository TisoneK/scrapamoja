#!/usr/bin/env python3
"""Unit tests for session-validator.py"""
import sys
import subprocess
import tempfile
import json
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "session-validator.py"


def run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + args,
                          capture_output=True, text=True)


def test_help():
    r = run(["--help"])
    assert r.returncode == 0


def test_discover_runs():
    r = run(["--discover"])
    assert r.returncode == 0
    assert "Artifact Discovery" in r.stdout or "standard" in r.stdout.lower()


def test_discover_json():
    r = run(["--discover", "--output", "json"])
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "standard" in data
    assert "stories" in data


if __name__ == "__main__":
    tests = [test_help, test_discover_runs, test_discover_json]
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
