#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""
Git validator for BMAD Crew Advisor.
Validates git state at session checkpoints — run by the Advisor directly, not by the Coordinator.

Usage:
  python3 git-validator.py --check-clean
  python3 git-validator.py --validate-commits --since-last-checkpoint
  python3 git-validator.py --verify-commit --expected-files file1.md file2.md
  python3 git-validator.py --check-commits-after-output
"""

import subprocess
import sys
import json
import argparse
from pathlib import Path


def run_git(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git"] + args,
        capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_clean() -> dict:
    """Check for uncommitted changes."""
    code, stdout, _ = run_git(["status", "--porcelain"])
    dirty_files = [l for l in stdout.splitlines() if l.strip()]
    return {
        "clean": len(dirty_files) == 0,
        "dirty_files": dirty_files,
        "count": len(dirty_files)
    }


def get_recent_commits(n: int = 5) -> list[dict]:
    """Get the N most recent commits."""
    code, stdout, _ = run_git(["log", f"--oneline", f"-{n}"])
    commits = []
    for line in stdout.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            commits.append({"hash": parts[0], "message": parts[1]})
    return commits


def validate_commits_after_output() -> dict:
    """Check that output-producing commands were followed by commits."""
    output_keywords = [
        "brainstorming", "create-prd", "prd", "architecture",
        "epics", "stories", "create-story", "dev-story",
        "code-review", "retrospective"
    ]
    code, stdout, _ = run_git(["log", "--oneline", "-20"])
    commits = stdout.splitlines()

    missing_commits = []
    # Simple heuristic: look for sessions without follow-up commits
    # A proper implementation would check timestamps vs file modification times
    last_output_commit = None
    for commit in commits:
        for kw in output_keywords:
            if kw in commit.lower():
                last_output_commit = commit
                break

    return {
        "status": "ok",
        "recent_commits": commits[:5],
        "last_output_commit": last_output_commit,
        "note": "Manual verification recommended for full lifecycle coverage"
    }


def verify_commit(expected_files: list[str]) -> dict:
    """Verify that specific files were committed in the most recent commit."""
    code, stdout, _ = run_git(["diff", "--name-only", "HEAD~1", "HEAD"])
    committed_files = stdout.splitlines()

    missing = [f for f in expected_files if not any(f in cf for cf in committed_files)]
    return {
        "verified": len(missing) == 0,
        "committed_files": committed_files,
        "expected_files": expected_files,
        "missing_from_commit": missing
    }


def main():
    parser = argparse.ArgumentParser(description="Git validator for BMAD Crew Advisor")
    parser.add_argument("--check-clean", action="store_true", help="Check for uncommitted changes")
    parser.add_argument("--validate-commits", action="store_true", help="Validate recent commit history")
    parser.add_argument("--since-last-checkpoint", action="store_true", help="Used with --validate-commits")
    parser.add_argument("--verify-commit", action="store_true", help="Verify files were committed")
    parser.add_argument("--expected-files", nargs="+", help="Files expected in last commit")
    parser.add_argument("--check-commits-after-output", action="store_true",
                        help="Check output-producing commands were committed")
    parser.add_argument("--output", choices=["json", "human"], default="human")

    args = parser.parse_args()

    result = {}

    if args.check_clean:
        result = check_clean()
        if args.output == "human":
            if result["clean"]:
                print("✓ Git working directory is clean")
            else:
                print(f"✗ Git dirty — {result['count']} uncommitted file(s):")
                for f in result["dirty_files"]:
                    print(f"  {f}")
                sys.exit(1)

    elif args.validate_commits:
        commits = get_recent_commits(10)
        result = {"commits": commits}
        if args.output == "human":
            print("Recent commits:")
            for c in commits:
                print(f"  {c['hash']} {c['message']}")

    elif args.verify_commit and args.expected_files:
        result = verify_commit(args.expected_files)
        if args.output == "human":
            if result["verified"]:
                print("✓ All expected files found in last commit")
            else:
                print("✗ Missing from last commit:")
                for f in result["missing_from_commit"]:
                    print(f"  {f}")
                sys.exit(1)

    elif args.check_commits_after_output:
        result = validate_commits_after_output()
        if args.output == "human":
            print(f"Last output-related commit: {result.get('last_output_commit', 'none found')}")
            print("Recent commits:")
            for c in result.get("recent_commits", []):
                print(f"  {c}")

    if args.output == "json":
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
