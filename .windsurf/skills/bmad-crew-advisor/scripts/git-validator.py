#!/usr/bin/env python3
"""
Git Validator Script for BMAD Crew Advisor

Validates git operations and commit status for checkpoint compliance.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_git_command(cmd: str, repo_path: str = ".") -> tuple[bool, str, str]:
    """Run a git command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + cmd.split(),
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", "Git command not found"


def check_clean_status(repo_path: str) -> dict:
    """Check if git status is clean."""
    success, stdout, stderr = run_git_command("status --porcelain", repo_path)
    
    if not success:
        return {
            "status": "error",
            "message": f"Failed to check git status: {stderr}",
            "is_clean": False
        }
    
    is_clean = len(stdout.strip()) == 0
    return {
        "status": "success",
        "is_clean": is_clean,
        "has_uncommitted_changes": not is_clean,
        "uncommitted_files": stdout.splitlines() if not is_clean else []
    }


def get_recent_commits(repo_path: str, count: int = 5) -> dict:
    """Get recent commits from git log."""
    success, stdout, stderr = run_git_command(f"log --oneline -{count}", repo_path)
    
    if not success:
        return {
            "status": "error",
            "message": f"Failed to get git log: {stderr}",
            "commits": []
        }
    
    commits = []
    for line in stdout.splitlines():
        if line.strip():
            parts = line.split(" ", 1)
            commit_hash = parts[0] if parts else ""
            message = parts[1] if len(parts) > 1 else ""
            commits.append({
                "hash": commit_hash,
                "message": message
            })
    
    return {
        "status": "success",
        "commits": commits
    }


def check_commit_exists(repo_path: str, commit_hash: str) -> dict:
    """Check if a specific commit exists."""
    success, stdout, stderr = run_git_command(f"rev-parse --verify {commit_hash}", repo_path)
    
    if not success:
        return {
            "status": "error",
            "exists": False,
            "message": f"Commit {commit_hash} not found: {stderr}"
        }
    
    return {
        "status": "success",
        "exists": True,
        "full_hash": stdout.strip()
    }


def validate_commit_message(repo_path: str, commit_hash: str) -> dict:
    """Validate if commit message follows BMAD format."""
    success, stdout, stderr = run_git_command(f"log --format=%B -n 1 {commit_hash}", repo_path)
    
    if not success:
        return {
            "status": "error",
            "message": f"Failed to get commit message: {stderr}",
            "is_valid": False
        }
    
    message = stdout.strip()
    
    # Basic BMAD format validation
    is_valid = (
        len(message) > 10 and  # Not too short
        any(keyword in message.lower() for keyword in ["feat", "fix", "docs", "style", "refactor", "test", "chore"]) and  # Has type
        ":" in message  # Has type separator
    )
    
    return {
        "status": "success",
        "message": message,
        "is_valid": is_valid,
        "issues": [] if is_valid else ["Commit message should follow BMAD format (type: description)"]
    }


def main():
    parser = argparse.ArgumentParser(description="Validate git operations for BMAD checkpoints")
    parser.add_argument("repo_path", nargs="?", default=".", help="Path to git repository")
    parser.add_argument("--check-status", action="store_true", help="Check git status")
    parser.add_argument("--check-commits", type=int, default=5, help="Check recent commits")
    parser.add_argument("--commit-exists", help="Check if specific commit exists")
    parser.add_argument("--validate-message", help="Validate commit message format")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    results = {
        "script": "git-validator.py",
        "version": "1.0.0",
        "skill_path": args.repo_path,
        "timestamp": datetime.now().isoformat(),
        "status": "pass",
        "findings": [],
        "summary": {
            "total": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
    }
    
    # Check git status
    if args.check_status:
        status_result = check_clean_status(args.repo_path)
        if status_result["status"] == "error":
            results["findings"].append({
                "severity": "critical",
                "category": "structure",
                "location": {"file": "git repository", "line": 0},
                "issue": status_result["message"],
                "fix": "Check git repository and permissions"
            })
            results["status"] = "fail"
        elif not status_result["is_clean"]:
            results["findings"].append({
                "severity": "high",
                "category": "process",
                "location": {"file": "git status", "line": 0},
                "issue": f"Unclean git status: {len(status_result['uncommitted_files'])} files with changes",
                "fix": "Commit or stash changes before proceeding"
            })
            if results["status"] == "pass":
                results["status"] = "warning"
    
    # Check recent commits
    if args.check_commits:
        commits_result = get_recent_commits(args.repo_path, args.check_commits)
        if commits_result["status"] == "error":
            results["findings"].append({
                "severity": "critical",
                "category": "structure",
                "location": {"file": "git log", "line": 0},
                "issue": commits_result["message"],
                "fix": "Check git repository and history"
            })
            results["status"] = "fail"
        elif len(commits_result["commits"]) == 0:
            results["findings"].append({
                "severity": "medium",
                "category": "process",
                "location": {"file": "git log", "line": 0},
                "issue": "No commits found in repository",
                "fix": "Initialize repository or check if this is the correct path"
            })
    
    # Check specific commit
    if args.commit_exists:
        commit_result = check_commit_exists(args.repo_path, args.commit_exists)
        if commit_result["status"] == "error":
            results["findings"].append({
                "severity": "high",
                "category": "process",
                "location": {"file": "git commit", "line": 0},
                "issue": commit_result["message"],
                "fix": "Verify commit hash and check git history"
            })
            results["status"] = "fail"
        elif not commit_result["exists"]:
            results["findings"].append({
                "severity": "high",
                "category": "process",
                "location": {"file": "git commit", "line": 0},
                "issue": f"Commit {args.commit_exists} does not exist",
                "fix": "Check commit hash or verify work was committed"
            })
            results["status"] = "fail"
    
    # Validate commit message
    if args.validate_message:
        message_result = validate_commit_message(args.repo_path, args.validate_message)
        if message_result["status"] == "error":
            results["findings"].append({
                "severity": "critical",
                "category": "structure",
                "location": {"file": "git commit", "line": 0},
                "issue": message_result["message"],
                "fix": "Check commit hash and repository state"
            })
            results["status"] = "fail"
        elif not message_result["is_valid"]:
            for issue in message_result["issues"]:
                results["findings"].append({
                    "severity": "medium",
                    "category": "consistency",
                    "location": {"file": "git commit", "line": 0},
                    "issue": issue,
                    "fix": " Amend commit with proper BMAD format (type: description)"
                })
            if results["status"] == "pass":
                results["status"] = "warning"
    
    # Update summary
    for finding in results["findings"]:
        results["summary"]["total"] += 1
        results["summary"][finding["severity"]] += 1
    
    # Output results
    json_output = json.dumps(results, indent=2)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        if args.verbose:
            print(f"Results written to {args.output}")
    else:
        print(json_output)
    
    # Set exit code
    if results["status"] == "fail":
        sys.exit(1)
    elif results["status"] == "warning":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
