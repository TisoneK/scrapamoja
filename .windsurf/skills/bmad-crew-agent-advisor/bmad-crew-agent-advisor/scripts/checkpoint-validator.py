#!/usr/bin/env python3
"""
Checkpoint Validator Script for BMAD Crew Advisor

Validates checkpoint compliance and required artifacts for phase transitions.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def validate_artifact_exists(artifact_path: str, artifact_type: str, required: bool = True) -> dict:
    """Check if a required artifact exists and has content."""
    path = Path(artifact_path)
    
    if not path.exists():
        return {
            "exists": False,
            "has_content": False,
            "path": artifact_path,
            "type": artifact_type,
            "issue": f"Required artifact missing: {artifact_type} at {artifact_path}",
            "severity": "critical" if required else "medium"
        }
    
    if not path.is_file():
        return {
            "exists": True,
            "has_content": False,
            "path": artifact_path,
            "type": artifact_type,
            "issue": f"Artifact path exists but is not a file: {artifact_path}",
            "severity": "critical" if required else "medium"
        }
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_content = len(content.strip()) > 0
        if not has_content:
            return {
                "exists": True,
                "has_content": False,
                "path": artifact_path,
                "type": artifact_type,
                "issue": f"Artifact exists but is empty: {artifact_type}",
                "severity": "medium" if required else "low"
            }
        
        return {
            "exists": True,
            "has_content": True,
            "path": artifact_path,
            "type": artifact_type,
            "issue": None,
            "severity": None
        }
        
    except Exception as e:
        return {
            "exists": True,
            "has_content": False,
            "path": artifact_path,
            "type": artifact_type,
            "issue": f"Artifact exists but is not readable: {e}",
            "severity": "critical" if required else "medium"
        }


def get_phase_requirements(phase: str) -> dict:
    """Get required artifacts for each phase."""
    requirements = {
        "brainstorming": {
            "required": [
                {"type": "brainstorming-notes", "path": None, "description": "Brainstorming session notes"}
            ],
            "optional": [
                {"type": "idea-capture", "path": None, "description": "Idea capture document"}
            ]
        },
        "planning": {
            "required": [
                {"type": "product-brief", "path": None, "description": "Product brief or PRD"},
                {"type": "user-stories", "path": None, "description": "User stories document"}
            ],
            "optional": [
                {"type": "acceptance-criteria", "path": None, "description": "Acceptance criteria"},
                {"type": "requirements-backlog", "path": None, "description": "Requirements backlog"}
            ]
        },
        "architecture": {
            "required": [
                {"type": "architecture-document", "path": None, "description": "Architecture document"},
                {"type": "technical-decisions", "path": None, "description": "Technical decisions document"}
            ],
            "optional": [
                {"type": "integration-plan", "path": None, "description": "Integration plan"},
                {"type": "deployment-strategy", "path": None, "description": "Deployment strategy"}
            ]
        },
        "implementation": {
            "required": [
                {"type": "implementation-code", "path": None, "description": "Implemented code"},
                {"type": "unit-tests", "path": None, "description": "Unit tests"}
            ],
            "optional": [
                {"type": "integration-tests", "path": None, "description": "Integration tests"},
                {"type": "documentation", "path": None, "description": "Implementation documentation"}
            ]
        },
        "code-review": {
            "required": [
                {"type": "review-completed", "path": None, "description": "Code review completion record"},
                {"type": "issues-resolved", "path": None, "description": "Issue resolution record"}
            ],
            "optional": [
                {"type": "quality-report", "path": None, "description": "Quality assessment report"},
                {"type": "performance-tests", "path": None, "description": "Performance test results"}
            ]
        }
    }
    
    return requirements.get(phase, {"required": [], "optional": []})


def validate_phase_artifacts(phase: str, artifact_paths: dict = None) -> dict:
    """Validate all required artifacts for a phase."""
    requirements = get_phase_requirements(phase)
    
    if not requirements:
        return {
            "status": "fail",
            "issue": f"Unknown phase: {phase}",
            "severity": "critical"
        }
    
    results = {
        "status": "pass",
        "phase": phase,
        "artifacts_checked": 0,
        "artifacts_found": 0,
        "issues": []
    }
    
    # Check required artifacts
    for artifact in requirements["required"]:
        artifact_type = artifact["type"]
        artifact_path = artifact_paths.get(artifact_type) if artifact_paths else f"{artifact_type}.md"
        
        results["artifacts_checked"] += 1
        validation = validate_artifact_exists(artifact_path, artifact_type, required=True)
        
        if validation["exists"] and validation["has_content"]:
            results["artifacts_found"] += 1
        
        if validation["issue"]:
            results["issues"].append({
                "type": artifact_type,
                "path": artifact_path,
                "issue": validation["issue"],
                "severity": validation["severity"],
                "required": True,
                "description": artifact["description"]
            })
            
            if validation["severity"] == "critical":
                results["status"] = "fail"
            elif results["status"] == "pass" and validation["severity"] == "medium":
                results["status"] = "warning"
    
    # Check optional artifacts
    for artifact in requirements["optional"]:
        artifact_type = artifact["type"]
        artifact_path = artifact_paths.get(artifact_type) if artifact_paths else f"{artifact_type}.md"
        
        results["artifacts_checked"] += 1
        validation = validate_artifact_exists(artifact_path, artifact_type, required=False)
        
        if validation["exists"] and validation["has_content"]:
            results["artifacts_found"] += 1
        
        if validation["issue"] and validation["severity"] in ["critical", "medium"]:
            results["issues"].append({
                "type": artifact_type,
                "path": artifact_path,
                "issue": validation["issue"],
                "severity": validation["severity"],
                "required": False,
                "description": artifact["description"]
            })
            
            if validation["severity"] == "critical" and results["status"] == "pass":
                results["status"] = "warning"
    
    return results


def validate_git_status(repo_path: str = ".") -> dict:
    """Validate git repository status for checkpoint."""
    try:
        import subprocess
        
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {
                "status": "warning",
                "issue": "Not in a git repository",
                "severity": "medium"
            }
        
        # Check if status is clean
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {
                "status": "fail",
                "issue": "Failed to check git status",
                "severity": "critical"
            }
        
        has_changes = len(result.stdout.strip()) > 0
        if has_changes:
            return {
                "status": "fail",
                "issue": f"Git status not clean: {len(result.stdout.splitlines())} files with changes",
                "severity": "high"
            }
        
        return {
            "status": "pass",
            "issue": None,
            "severity": None
        }
        
    except subprocess.TimeoutExpired:
        return {
            "status": "fail",
            "issue": "Git command timed out",
            "severity": "critical"
        }
    except FileNotFoundError:
        return {
            "status": "warning",
            "issue": "Git command not found",
            "severity": "medium"
        }


def validate_checkpoint_compliance(phase: str, artifact_paths: dict = None, repo_path: str = ".") -> dict:
    """Comprehensive checkpoint validation for a phase."""
    results = {
        "status": "pass",
        "phase": phase,
        "timestamp": datetime.now().isoformat(),
        "validations": {},
        "overall_issues": []
    }
    
    # Validate phase artifacts
    artifact_result = validate_phase_artifacts(phase, artifact_paths)
    results["validations"]["artifacts"] = artifact_result
    
    if artifact_result["status"] == "fail":
        results["status"] = "fail"
        results["overall_issues"].extend(artifact_result["issues"])
    elif artifact_result["status"] == "warning" and results["status"] == "pass":
        results["status"] = "warning"
    
    # Validate git status (except for brainstorming phase)
    if phase != "brainstorming":
        git_result = validate_git_status(repo_path)
        results["validations"]["git"] = git_result
        
        if git_result["status"] == "fail":
            results["status"] = "fail"
            results["overall_issues"].append({
                "category": "git",
                "issue": git_result["issue"],
                "severity": git_result["severity"],
                "fix": "Commit or stash changes before proceeding"
            })
        elif git_result["status"] == "warning" and results["status"] == "pass":
            results["status"] = "warning"
            results["overall_issues"].append({
                "category": "git",
                "issue": git_result["issue"],
                "severity": git_result["severity"],
                "fix": "Consider initializing git repository"
            })
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Validate BMAD checkpoint compliance")
    parser.add_argument("--phase", required=True, help="Phase to validate (brainstorming, planning, architecture, implementation, code-review)")
    parser.add_argument("--check-artifacts", action="store_true", help="Check required artifacts")
    parser.add_argument("--artifact-paths", help="JSON file with artifact paths")
    parser.add_argument("--check-git", action="store_true", help="Check git repository status")
    parser.add_argument("--repo-path", default=".", help="Path to git repository")
    parser.add_argument("--recheck", action="store_true", help="Recheck after fixes")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Load artifact paths if provided
    artifact_paths = {}
    if args.artifact_paths:
        try:
            with open(args.artifact_paths, 'r') as f:
                artifact_paths = json.load(f)
        except Exception as e:
            print(f"Error loading artifact paths: {e}", file=sys.stderr)
            sys.exit(1)
    
    results = {
        "script": "checkpoint-validator.py",
        "version": "1.0.0",
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
    
    # Validate checkpoint compliance
    checkpoint_result = validate_checkpoint_compliance(
        args.phase, artifact_paths, args.repo_path
    )
    
    if checkpoint_result["status"] == "fail":
        results["status"] = "fail"
        
        # Add artifact issues
        if "artifacts" in checkpoint_result["validations"]:
            for issue in checkpoint_result["validations"]["artifacts"]["issues"]:
                severity = issue["severity"]
                results["findings"].append({
                    "severity": severity,
                    "category": "artifacts",
                    "location": {"file": issue["path"], "line": 0},
                    "issue": issue["issue"],
                    "fix": f"Create or complete {issue['type']}: {issue['description']}"
                })
        
        # Add git issues
        if "git" in checkpoint_result["validations"]:
            git_validation = checkpoint_result["validations"]["git"]
            if git_validation["status"] in ["fail", "warning"]:
                severity = "high" if git_validation["status"] == "fail" else "medium"
                results["findings"].append({
                    "severity": severity,
                    "category": "git",
                    "location": {"file": "git repository", "line": 0},
                    "issue": git_validation["issue"],
                    "fix": "Clean git status before proceeding"
                })
    
    elif checkpoint_result["status"] == "warning":
        results["status"] = "warning"
        
        # Add warning-level issues
        for validation_type, validation_data in checkpoint_result["validations"].items():
            if validation_type == "artifacts" and "issues" in validation_data:
                for issue in validation_data["issues"]:
                    if issue["severity"] in ["medium", "low"]:
                        results["findings"].append({
                            "severity": issue["severity"],
                            "category": "artifacts",
                            "location": {"file": issue["path"], "line": 0},
                            "issue": issue["issue"],
                            "fix": f"Consider adding {issue['type']} for completeness"
                        })
            
            elif validation_type == "git" and validation_data["status"] == "warning":
                results["findings"].append({
                    "severity": "medium",
                    "category": "git",
                    "location": {"file": "git repository", "line": 0},
                    "issue": validation_data["issue"],
                    "fix": "Consider initializing git repository"
                })
    
    # Add success message if no issues
    if results["status"] == "pass":
        results["findings"].append({
            "severity": "info",
            "category": "checkpoint",
            "location": {"file": args.phase, "line": 0},
            "issue": f"All {args.phase} checkpoint requirements satisfied",
            "fix": "Proceed to next phase"
        })
    
    # Update summary
    for finding in results["findings"]:
        if finding["severity"] in ["critical", "high", "medium", "low"]:
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
