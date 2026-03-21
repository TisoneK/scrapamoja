#!/usr/bin/env python3
"""
Session Validator Script for BMAD Crew Advisor

Validates session state and file structure for BMAD development sessions.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def validate_file_exists(file_path: str, required: bool = True) -> dict:
    """Check if a file exists and is readable."""
    path = Path(file_path)
    
    if not path.exists():
        return {
            "exists": False,
            "readable": False,
            "path": file_path,
            "issue": f"File does not exist: {file_path}",
            "severity": "critical" if required else "medium"
        }
    
    if not path.is_file():
        return {
            "exists": True,
            "readable": False,
            "path": file_path,
            "issue": f"Path exists but is not a file: {file_path}",
            "severity": "critical" if required else "medium"
        }
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read(1)  # Try to read first byte
        return {
            "exists": True,
            "readable": True,
            "path": file_path,
            "issue": None,
            "severity": None
        }
    except Exception as e:
        return {
            "exists": True,
            "readable": False,
            "path": file_path,
            "issue": f"File exists but is not readable: {e}",
            "severity": "critical" if required else "medium"
        }


def validate_context_files(story_file: str = None, architecture: str = None, brainstorming: str = None) -> dict:
    """Validate context documents for session initialization."""
    results = {
        "status": "pass",
        "files_checked": 0,
        "files_found": 0,
        "issues": []
    }
    
    context_files = []
    if story_file:
        context_files.append(("story", story_file, True))
    if architecture:
        context_files.append(("architecture", architecture, False))
    if brainstorming:
        context_files.append(("brainstorming", brainstorming, False))
    
    for file_type, file_path, is_required in context_files:
        results["files_checked"] += 1
        validation = validate_file_exists(file_path, is_required)
        
        if validation["exists"] and validation["readable"]:
            results["files_found"] += 1
        
        if validation["issue"]:
            results["issues"].append({
                "file_type": file_type,
                "path": file_path,
                "issue": validation["issue"],
                "severity": validation["severity"],
                "required": is_required
            })
            
            if validation["severity"] == "critical":
                results["status"] = "fail"
            elif results["status"] == "pass" and validation["severity"] == "medium":
                results["status"] = "warning"
    
    return results


def validate_locked_decisions(locked_decisions_path: str) -> dict:
    """Validate locked decisions file structure and content."""
    validation = validate_file_exists(locked_decisions_path, required=True)
    
    if not validation["exists"] or not validation["readable"]:
        return {
            "status": "fail",
            "issue": validation["issue"],
            "severity": "critical"
        }
    
    try:
        with open(locked_decisions_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic structure validation
        if len(content.strip()) == 0:
            return {
                "status": "warning",
                "issue": "Locked decisions file is empty",
                "severity": "medium"
            }
        
        # Check for decision markers
        has_decisions = any(marker in content.lower() for marker in ["decision:", "## decision", "decision:", "locked:"])
        if not has_decisions:
            return {
                "status": "warning",
                "issue": "No locked decisions found in file",
                "severity": "medium"
            }
        
        return {
            "status": "pass",
            "issue": None,
            "severity": None
        }
        
    except Exception as e:
        return {
            "status": "fail",
            "issue": f"Error reading locked decisions: {e}",
            "severity": "critical"
        }


def validate_memory_structure(memory_path: str) -> dict:
    """Validate agent memory sidecar structure."""
    memory_dir = Path(memory_path)
    
    if not memory_dir.exists():
        return {
            "status": "fail",
            "issue": f"Memory directory does not exist: {memory_path}",
            "severity": "critical"
        }
    
    if not memory_dir.is_dir():
        return {
            "status": "fail",
            "issue": f"Memory path exists but is not a directory: {memory_path}",
            "severity": "critical"
        }
    
    required_files = [
        "access-boundaries.md",
        "session-state.md", 
        "locked-decisions.md",
        "index.md"
    ]
    
    results = {
        "status": "pass",
        "files_checked": len(required_files),
        "files_found": 0,
        "issues": []
    }
    
    for file_name in required_files:
        file_path = memory_dir / file_name
        validation = validate_file_exists(str(file_path), required=True)
        
        if validation["exists"] and validation["readable"]:
            results["files_found"] += 1
        
        if validation["issue"]:
            results["issues"].append({
                "file": file_name,
                "path": str(file_path),
                "issue": validation["issue"],
                "severity": validation["severity"]
            })
            
            if validation["severity"] == "critical":
                results["status"] = "fail"
            elif results["status"] == "pass" and validation["severity"] == "medium":
                results["status"] = "warning"
    
    return results


def validate_session_phase(phase: str, context_available: bool) -> dict:
    """Validate if session phase is appropriate for available context."""
    phase_requirements = {
        "brainstorming": False,  # Can start without context
        "planning": True,       # Needs some context
        "architecture": True,    # Needs requirements
        "implementation": True, # Needs architecture
        "code-review": True     # Needs implementation
    }
    
    if phase not in phase_requirements:
        return {
            "status": "warning",
            "issue": f"Unknown session phase: {phase}",
            "severity": "medium"
        }
    
    needs_context = phase_requirements[phase]
    if needs_context and not context_available:
        return {
            "status": "fail",
            "issue": f"Phase '{phase}' requires context but none is available",
            "severity": "critical"
        }
    
    return {
        "status": "pass",
        "issue": None,
        "severity": None
    }


def main():
    parser = argparse.ArgumentParser(description="Validate BMAD session state and structure")
    parser.add_argument("--validate-context", action="store_true", help="Validate context files")
    parser.add_argument("--story-file", help="Path to story file")
    parser.add_argument("--architecture", help="Path to architecture document")
    parser.add_argument("--brainstorming", help="Path to brainstorming session")
    parser.add_argument("--locked-decisions", help="Path to locked decisions file")
    parser.add_argument("--memory-path", help="Path to agent memory sidecar")
    parser.add_argument("--session-phase", help="Current session phase")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    results = {
        "script": "session-validator.py",
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
    
    # Validate context files
    if args.validate_context:
        context_result = validate_context_files(
            args.story_file, args.architecture, args.brainstorming
        )
        
        if context_result["status"] == "fail":
            results["findings"].append({
                "severity": "critical",
                "category": "structure",
                "location": {"file": "context files", "line": 0},
                "issue": f"Context validation failed: {len(context_result['issues'])} issues",
                "fix": "Provide required context files (at minimum, story file or sprint status)"
            })
            results["status"] = "fail"
        elif context_result["status"] == "warning":
            for issue in context_result["issues"]:
                if issue["severity"] == "critical":
                    severity = "high"
                else:
                    severity = issue["severity"]
                
                results["findings"].append({
                    "severity": severity,
                    "category": "completeness",
                    "location": {"file": issue["path"], "line": 0},
                    "issue": issue["issue"],
                    "fix": f"Provide {issue['file_type']} file or proceed without it"
                })
            
            if results["status"] == "pass":
                results["status"] = "warning"
        
        # Validate session phase against context
        if args.session_phase:
            context_available = context_result["files_found"] > 0
            phase_result = validate_session_phase(args.session_phase, context_available)
            
            if phase_result["status"] == "fail":
                results["findings"].append({
                    "severity": "critical",
                    "category": "process",
                    "location": {"file": "session phase", "line": 0},
                    "issue": phase_result["issue"],
                    "fix": "Provide context before entering this phase or choose appropriate phase"
                })
                results["status"] = "fail"
            elif phase_result["status"] == "warning":
                results["findings"].append({
                    "severity": "medium",
                    "category": "process",
                    "location": {"file": "session phase", "line": 0},
                    "issue": phase_result["issue"],
                    "fix": "Verify session phase is correct"
                })
                if results["status"] == "pass":
                    results["status"] = "warning"
    
    # Validate locked decisions
    if args.locked_decisions:
        decisions_result = validate_locked_decisions(args.locked_decisions)
        
        if decisions_result["status"] == "fail":
            results["findings"].append({
                "severity": "critical",
                "category": "structure",
                "location": {"file": args.locked_decisions, "line": 0},
                "issue": decisions_result["issue"],
                "fix": "Create or restore locked decisions file"
            })
            results["status"] = "fail"
        elif decisions_result["status"] == "warning":
            results["findings"].append({
                "severity": "medium",
                "category": "completeness",
                "location": {"file": args.locked_decisions, "line": 0},
                "issue": decisions_result["issue"],
                "fix": "Add locked decisions to the file"
            })
            if results["status"] == "pass":
                results["status"] = "warning"
    
    # Validate memory structure
    if args.memory_path:
        memory_result = validate_memory_structure(args.memory_path)
        
        if memory_result["status"] == "fail":
            results["findings"].append({
                "severity": "critical",
                "category": "structure",
                "location": {"file": "memory sidecar", "line": 0},
                "issue": f"Memory structure validation failed: {len(memory_result['issues'])} issues",
                "fix": "Initialize memory sidecar with required files"
            })
            results["status"] = "fail"
        elif memory_result["status"] == "warning":
            for issue in memory_result["issues"]:
                results["findings"].append({
                    "severity": issue["severity"],
                    "category": "structure",
                    "location": {"file": issue["path"], "line": 0},
                    "issue": issue["issue"],
                    "fix": f"Create missing memory file: {issue['file']}"
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
