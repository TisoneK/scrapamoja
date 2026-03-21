#!/usr/bin/env python3
"""
Session Check Script for BMAD Crew Session Validator

Validates BMAD session state for role, process, and quality violations.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: str, cwd: str = ".") -> tuple[bool, str, str]:
    """Run a shell command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def check_git_status(repo_path: str) -> dict:
    """Check git repository status."""
    success, stdout, stderr = run_command("git status --porcelain", repo_path)
    
    if not success:
        return {"status": "error", "message": f"Git status failed: {stderr}"}
    
    is_clean = len(stdout.strip()) == 0
    uncommitted_files = stdout.splitlines() if not is_clean else []
    
    return {
        "status": "success",
        "is_clean": is_clean,
        "uncommitted_files": uncommitted_files,
        "has_uncommitted_changes": not is_clean
    }


def get_recent_commits(repo_path: str, count: int = 10) -> dict:
    """Get recent commits from git log."""
    success, stdout, stderr = run_command(f"git log --oneline -{count}", repo_path)
    
    if not success:
        return {"status": "error", "message": f"Git log failed: {stderr}"}
    
    commits = []
    for line in stdout.splitlines():
        if line.strip():
            parts = line.split(" ", 1)
            commits.append({
                "hash": parts[0] if parts else "",
                "message": parts[1] if len(parts) > 1 else ""
            })
    
    return {"status": "success", "commits": commits}


def check_file_exists(file_path: str) -> dict:
    """Check if a file exists and get basic info."""
    path = Path(file_path)
    
    if not path.exists():
        return {
            "status": "error",
            "exists": False,
            "message": f"File does not exist: {file_path}"
        }
    
    stat = path.stat()
    return {
        "status": "success",
        "exists": True,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
    }


def check_role_violations(session_context: dict, repo_path: str) -> list:
    """Check for role violations."""
    violations = []
    
    # Check if Advisor is attempting to execute commands
    if session_context.get("advisor_executing_commands", False):
        violations.append({
            "type": "role_violation",
            "subtype": "advisor_becoming_executor",
            "severity": "critical",
            "rule": "advisors_must_not_execute_commands",
            "message": "Advisor attempting to execute BMAD commands",
            "correction": "Return to advisory role, provide instruction to Coordinator for Executor"
        })
    
    # Check if Executor is self-certifying completion
    if session_context.get("executor_self_certified", False):
        violations.append({
            "type": "role_violation",
            "subtype": "executor_self_certifying",
            "severity": "high",
            "rule": "executors_must_not_self_certify",
            "message": "Executor claiming completion without external validation",
            "correction": "Require external validation, commit evidence, or Coordinator confirmation"
        })
    
    # Check for agent role confusion
    if session_context.get("role_confusion", False):
        violations.append({
            "type": "role_violation",
            "subtype": "agent_role_confusion",
            "severity": "medium",
            "rule": "agents_must_stay_in_role_boundaries",
            "message": "Agent performing actions outside their defined role",
            "correction": "Clarify roles, provide role-appropriate instructions"
        })
    
    return violations


def check_process_violations(session_context: dict, repo_path: str) -> list:
    """Check for process violations."""
    violations = []
    
    # Check git status for uncommitted changes
    git_status = check_git_status(repo_path)
    if git_status["status"] == "success" and not git_status["is_clean"]:
        violations.append({
            "type": "process_violation",
            "subtype": "uncommitted_changes",
            "severity": "critical",
            "rule": "commit_before_new_session",
            "message": f"Uncommitted changes found: {len(git_status['uncommitted_files'])} files",
            "correction": "Commit all changes before starting new session",
            "details": git_status["uncommitted_files"]
        })
    
    # Check for code review skips
    if session_context.get("code_review_skipped", False):
        violations.append({
            "type": "process_violation",
            "subtype": "code_review_skipped",
            "severity": "high",
            "rule": "code_review_required",
            "message": "Code changes committed without review process",
            "correction": "Require code review, incorporate feedback, recommit if needed"
        })
    
    # Check for dev-story without clean status
    if session_context.get("dev_story_dirty_status", False):
        violations.append({
            "type": "process_violation",
            "subtype": "dev_story_dirty_status",
            "severity": "high",
            "rule": "dev_story_requires_clean_status",
            "message": "dev-story command run with uncommitted changes",
            "correction": "Commit or stash changes before running dev-story"
        })
    
    return violations


def check_quality_violations(session_context: dict, repo_path: str) -> list:
    """Check for quality violations."""
    violations = []
    
    # Check for completion without commit hash
    if session_context.get("completion_without_commit", False):
        violations.append({
            "type": "quality_violation",
            "subtype": "completion_without_commit",
            "severity": "critical",
            "rule": "completion_requires_commit",
            "message": "Executor claimed completion without new commit hash",
            "correction": "Require commit before accepting completion claim"
        })
    
    # Check for documents confirmed without reading
    if session_context.get("documents_confirmed_unread", False):
        violations.append({
            "type": "quality_violation",
            "subtype": "documents_confirmed_unread",
            "severity": "high",
            "rule": "documents_must_be_read",
            "message": "Documents confirmed without evidence of reading",
            "correction": "Require actual document reading with specific references"
        })
    
    # Check for incomplete output
    if session_context.get("incomplete_output", False):
        violations.append({
            "type": "quality_violation",
            "subtype": "incomplete_output",
            "severity": "medium",
            "rule": "output_must_be_complete",
            "message": "Required outputs missing or incomplete",
            "correction": "Complete missing outputs before proceeding"
        })
    
    return violations


def main():
    parser = argparse.ArgumentParser(description="Validate BMAD session state")
    parser.add_argument("repo_path", nargs="?", default=".", help="Path to git repository")
    parser.add_argument("--check-roles", action="store_true", help="Check for role violations")
    parser.add_argument("--check-process", action="store_true", help="Check for process violations")
    parser.add_argument("--check-quality", action="store_true", help="Check for quality violations")
    parser.add_argument("--session-context", help="JSON file with session context")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Load session context
    session_context = {}
    if args.session_context:
        try:
            with open(args.session_context, 'r') as f:
                session_context = json.load(f)
        except Exception as e:
            print(f"Error loading session context: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Default to checking all types if none specified
    if not any([args.check_roles, args.check_process, args.check_quality]):
        args.check_roles = True
        args.check_process = True
        args.check_quality = True
    
    results = {
        "script": "session-check.py",
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
    
    # Run checks based on arguments
    if args.check_roles:
        role_violations = check_role_violations(session_context, args.repo_path)
        for violation in role_violations:
            results["findings"].append({
                "severity": violation["severity"],
                "category": "process",
                "location": {"file": "session_context", "line": 0},
                "issue": violation["message"],
                "fix": violation["correction"],
                "rule": violation["rule"],
                "type": violation["type"],
                "subtype": violation["subtype"]
            })
    
    if args.check_process:
        process_violations = check_process_violations(session_context, args.repo_path)
        for violation in process_violations:
            results["findings"].append({
                "severity": violation["severity"],
                "category": "process",
                "location": {"file": "git_repository", "line": 0},
                "issue": violation["message"],
                "fix": violation["correction"],
                "rule": violation["rule"],
                "type": violation["type"],
                "subtype": violation["subtype"],
                "details": violation.get("details", [])
            })
    
    if args.check_quality:
        quality_violations = check_quality_violations(session_context, args.repo_path)
        for violation in quality_violations:
            results["findings"].append({
                "severity": violation["severity"],
                "category": "consistency",
                "location": {"file": "session_output", "line": 0},
                "issue": violation["message"],
                "fix": violation["correction"],
                "rule": violation["rule"],
                "type": violation["type"],
                "subtype": violation["subtype"]
            })
    
    # Update summary
    for finding in results["findings"]:
        results["summary"]["total"] += 1
        results["summary"][finding["severity"]] += 1
    
    # Set overall status
    if results["summary"]["critical"] > 0:
        results["status"] = "fail"
    elif results["summary"]["high"] > 0:
        results["status"] = "warning"
    
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
