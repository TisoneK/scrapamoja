#!/usr/bin/env python3
"""
Checkpoint Validator Script for BMAD Crew Checkpoint Enforcer

Validates BMAD checkpoints including commits, summaries, code reviews, and sessions.
"""

import argparse
import json
import os
import re
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


def check_commit_checkpoint(repo_path: str, expected_commit: str = None) -> dict:
    """Check commit checkpoint compliance."""
    findings = []
    
    # Check git status
    success, stdout, stderr = run_command("git status --porcelain", repo_path)
    if not success:
        findings.append({
            "checkpoint": "commit",
            "status": "error",
            "message": f"Failed to check git status: {stderr}",
            "severity": "critical"
        })
        return {"status": "error", "findings": findings}
    
    is_clean = len(stdout.strip()) == 0
    if not is_clean:
        findings.append({
            "checkpoint": "commit",
            "status": "fail",
            "message": f"Unclean git status: {len(stdout.splitlines())} files with changes",
            "severity": "high",
            "correction": "Commit or stash changes before proceeding",
            "command": "git add . && git commit -m 'commit session work'"
        })
    
    # Check recent commits
    success, stdout, stderr = run_command("git log --oneline -5", repo_path)
    if not success:
        findings.append({
            "checkpoint": "commit",
            "status": "error",
            "message": f"Failed to get git log: {stderr}",
            "severity": "critical"
        })
        return {"status": "error", "findings": findings}
    
    commits = stdout.splitlines()
    if len(commits) == 0:
        findings.append({
            "checkpoint": "commit",
            "status": "fail",
            "message": "No commits found in repository",
            "severity": "medium",
            "correction": "Initialize repository or check if this is correct path"
        })
    
    # Check for expected commit
    if expected_commit:
        commit_exists = any(expected_commit in commit for commit in commits)
        if not commit_exists:
            findings.append({
                "checkpoint": "commit",
                "status": "fail",
                "message": f"Expected commit not found: {expected_commit}",
                "severity": "high",
                "correction": "Verify commit was made and check git log"
            })
    
    return {
        "status": "pass" if not findings else "fail",
        "findings": findings
    }


def check_summary_checkpoint(repo_path: str, summary_file: str = None) -> dict:
    """Check summary checkpoint compliance."""
    findings = []
    
    if not summary_file:
        findings.append({
            "checkpoint": "summary",
            "status": "fail",
            "message": "No summary file specified",
            "severity": "medium",
            "correction": "Provide summary file path for validation"
        })
        return {"status": "fail", "findings": findings}
    
    summary_path = Path(repo_path) / summary_file
    
    # Check if summary file exists
    if not summary_path.exists():
        findings.append({
            "checkpoint": "summary",
            "status": "fail",
            "message": f"Summary file does not exist: {summary_file}",
            "severity": "high",
            "correction": f"Create summary file at {summary_file}",
            "command": f"touch {summary_file}"
        })
        return {"status": "fail", "findings": findings}
    
    # Check summary content
    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required sections
        required_sections = ["summary", "completed", "next", "decisions"]
        missing_sections = []
        
        for section in required_sections:
            if section not in content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            findings.append({
                "checkpoint": "summary",
                "status": "fail",
                "message": f"Summary missing required sections: {', '.join(missing_sections)}",
                "severity": "medium",
                "correction": f"Add missing sections to {summary_file}"
            })
        
        # Check if summary is too short
        if len(content.strip()) < 100:
            findings.append({
                "checkpoint": "summary",
                "status": "fail",
                "message": "Summary appears too short or incomplete",
                "severity": "medium",
                "correction": "Expand summary with more detail about completed work"
            })
    
    except Exception as e:
        findings.append({
            "checkpoint": "summary",
            "status": "error",
            "message": f"Failed to read summary file: {e}",
            "severity": "critical"
        })
    
    return {
        "status": "pass" if not findings else "fail",
        "findings": findings
    }


def check_code_review_checkpoint(repo_path: str) -> dict:
    """Check code review checkpoint compliance."""
    findings = []
    
    # Check for recent code changes
    success, stdout, stderr = run_command("git diff HEAD~1 --name-only", repo_path)
    if not success:
        findings.append({
            "checkpoint": "code_review",
            "status": "error",
            "message": f"Failed to check code changes: {stderr}",
            "severity": "critical"
        })
        return {"status": "error", "findings": findings}
    
    changed_files = stdout.splitlines()
    code_files = [f for f in changed_files if f.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c'))]
    
    if not code_files:
        # No code changes, checkpoint passes
        return {"status": "pass", "findings": findings}
    
    # Check commit messages for review indicators
    success, stdout, stderr = run_command("git log --oneline -3", repo_path)
    if not success:
        findings.append({
            "checkpoint": "code_review",
            "status": "error",
            "message": f"Failed to get commit history: {stderr}",
            "severity": "critical"
        })
        return {"status": "error", "findings": findings}
    
    recent_commits = stdout.splitlines()
    review_indicators = ['review', 'pr', 'merge', 'approved']
    has_review_evidence = any(
        any(indicator in commit.lower() for indicator in review_indicators)
        for commit in recent_commits
    )
    
    if not has_review_evidence:
        findings.append({
            "checkpoint": "code_review",
            "status": "fail",
            "message": f"Code changes found without review evidence: {len(code_files)} files",
            "severity": "high",
            "correction": "Conduct code review before marking work complete",
            "command": "Review changed files and add review evidence to commit message"
        })
    
    return {
        "status": "pass" if not findings else "fail",
        "findings": findings
    }


def check_session_checkpoint(repo_path: str, session_file: str = None) -> dict:
    """Check session checkpoint compliance."""
    findings = []
    
    if not session_file:
        findings.append({
            "checkpoint": "session",
            "status": "fail",
            "message": "No session file specified",
            "severity": "medium",
            "correction": "Provide session file path for validation"
        })
        return {"status": "fail", "findings": findings}
    
    session_path = Path(repo_path) / session_file
    
    # Check if session file exists
    if not session_path.exists():
        findings.append({
            "checkpoint": "session",
            "status": "fail",
            "message": f"Session file does not exist: {session_file}",
            "severity": "high",
            "correction": f"Create session file at {session_file}"
        })
        return {"status": "fail", "findings": findings}
    
    # Check session file content
    try:
        with open(session_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required session elements
        required_elements = ["session_id", "start_time", "phase", "status"]
        missing_elements = []
        
        for element in required_elements:
            if element not in content.lower():
                missing_elements.append(element)
        
        if missing_elements:
            findings.append({
                "checkpoint": "session",
                "status": "fail",
                "message": f"Session missing required elements: {', '.join(missing_elements)}",
                "severity": "medium",
                "correction": f"Add missing elements to {session_file}"
            })
    
    except Exception as e:
        findings.append({
            "checkpoint": "session",
            "status": "error",
            "message": f"Failed to read session file: {e}",
            "severity": "critical"
        })
    
    return {
        "status": "pass" if not findings else "fail",
        "findings": findings
    }


def main():
    parser = argparse.ArgumentParser(description="Validate BMAD checkpoints")
    parser.add_argument("repo_path", nargs="?", default=".", help="Path to git repository")
    parser.add_argument("--check-commits", action="store_true", help="Check commit checkpoints")
    parser.add_argument("--check-summaries", help="Check summary checkpoints (specify file path)")
    parser.add_argument("--check-reviews", action="store_true", help="Check code review checkpoints")
    parser.add_argument("--check-sessions", help="Check session checkpoints (specify file path)")
    parser.add_argument("--expected-commit", help="Expected commit hash to verify")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    results = {
        "script": "checkpoint-validator.py",
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
        },
        "checkpoint_results": {}
    }
    
    # Run requested checkpoint checks
    if args.check_commits:
        commit_result = check_commit_checkpoint(args.repo_path, args.expected_commit)
        results["checkpoint_results"]["commit"] = commit_result
        for finding in commit_result.get("findings", []):
            results["findings"].append(finding)
    
    if args.check_summaries:
        summary_result = check_summary_checkpoint(args.repo_path, args.check_summaries)
        results["checkpoint_results"]["summary"] = summary_result
        for finding in summary_result.get("findings", []):
            results["findings"].append(finding)
    
    if args.check_reviews:
        review_result = check_code_review_checkpoint(args.repo_path)
        results["checkpoint_results"]["code_review"] = review_result
        for finding in review_result.get("findings", []):
            results["findings"].append(finding)
    
    if args.check_sessions:
        session_result = check_session_checkpoint(args.repo_path, args.check_sessions)
        results["checkpoint_results"]["session"] = session_result
        for finding in session_result.get("findings", []):
            results["findings"].append(finding)
    
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
