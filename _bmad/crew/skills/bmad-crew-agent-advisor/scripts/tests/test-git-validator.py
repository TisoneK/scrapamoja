#!/usr/bin/env python3
"""Unit tests for git-validator.py"""
import sys
import subprocess
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "git-validator.py"


def run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + args,
                          capture_output=True, text=True)


def test_help():
    r = run(["--help"])
    assert r.returncode == 0, "help should exit 0"
    assert "check-clean" in r.stdout


def test_check_clean_runs():
    r = run(["--check-clean"])
    # Should run without error (pass or fail depending on git state)
    assert r.returncode in (0, 1), f"unexpected returncode: {r.returncode}"


def test_validate_commits_runs():
    r = run(["--validate-commits"])
    assert r.returncode == 0


if __name__ == "__main__":
    tests = [test_help, test_check_clean_runs, test_validate_commits_runs]
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
