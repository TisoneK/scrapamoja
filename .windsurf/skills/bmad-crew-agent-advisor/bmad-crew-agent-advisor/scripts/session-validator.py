#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""
Session validator and artifact discovery for BMAD Crew Advisor.
Run by the Advisor on activation — never ask the Coordinator to run this.

Usage:
  python3 session-validator.py --discover
  python3 session-validator.py --validate-context --auto-discovered
  python3 session-validator.py --check-roles
  python3 session-validator.py --check-process
"""

import subprocess
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def find_project_root() -> Path:
    """Walk up from cwd to find project root (contains _bmad directory)."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "_bmad").exists():
            return parent
    return cwd


def discover_artifacts(root: Path) -> dict:
    """Auto-discover all relevant BMAD artifacts."""
    discovered = {
        "standard": {},
        "additional": [],
        "stories": []
    }

    # Standard artifacts
    standard_paths = {
        "sprint_status": root / "sprint-status.yaml",
        "project_context": root / "project-context.md",
        "locked_decisions": root / "_bmad" / "bmad-crew" / "locked-decisions.md",
    }

    for key, path in standard_paths.items():
        discovered["standard"][key] = {
            "path": str(path),
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else 0
        }

    # Story files
    story_dirs = [
        root / "_bmad" / "bmad-crew" / "stories",
        root / "stories",
        root / "_bmad" / "stories",
    ]
    for story_dir in story_dirs:
        if story_dir.exists():
            for story_file in story_dir.glob("*.md"):
                content = story_file.read_text(errors="ignore")
                status = "unknown"
                for line in content.splitlines()[:20]:
                    if "status:" in line.lower():
                        status = line.split(":", 1)[-1].strip()
                        break
                discovered["stories"].append({
                    "path": str(story_file),
                    "name": story_file.name,
                    "status": status
                })

    # Additional context files
    additional_patterns = [
        (root / "docs", "**/*.md"),
        (root / "proposals", "**/*.md"),
        (root / "_bmad-output", "**/*.md"),
    ]
    glob_patterns = [
        root / "*.proposal.md",
        root / "FEATURE_*.md",
        root / "brainstorming-*.md",
    ]

    for base_dir, pattern in additional_patterns:
        if base_dir.exists():
            for f in base_dir.glob(pattern):
                if f.stat().st_size > 100:  # skip empty files
                    discovered["additional"].append({
                        "path": str(f),
                        "name": f.name,
                        "size": f.stat().st_size
                    })

    for pattern in glob_patterns:
        for f in root.glob(pattern.name):
            if f.exists() and f.stat().st_size > 100:
                discovered["additional"].append({
                    "path": str(f),
                    "name": f.name,
                    "size": f.stat().st_size
                })

    # Deduplicate additional
    seen = set()
    deduped = []
    for item in discovered["additional"]:
        if item["path"] not in seen:
            seen.add(item["path"])
            deduped.append(item)
    discovered["additional"] = deduped[:20]  # cap at 20

    return discovered


def format_discovery_human(discovered: dict) -> str:
    lines = ["=== Artifact Discovery Results ===\n"]

    lines.append("Standard context:")
    for key, info in discovered["standard"].items():
        status = "✓ found" if info["exists"] else "✗ missing"
        lines.append(f"  {key}: {status} ({info['path']})")

    active_stories = [s for s in discovered["stories"]
                      if any(x in s["status"].lower()
                             for x in ["ready", "in-progress", "active"])]
    lines.append(f"\nStory files: {len(discovered['stories'])} total, "
                 f"{len(active_stories)} active")
    for s in active_stories:
        lines.append(f"  {s['name']} [{s['status']}]")

    if discovered["additional"]:
        lines.append(f"\nAdditional context ({len(discovered['additional'])} files):")
        for f in discovered["additional"][:10]:
            lines.append(f"  {f['name']}")
        if len(discovered["additional"]) > 10:
            lines.append(f"  ... and {len(discovered['additional']) - 10} more")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Session validator for BMAD Crew Advisor")
    parser.add_argument("--discover", action="store_true", help="Discover all project artifacts")
    parser.add_argument("--validate-context", action="store_true", help="Validate loaded context")
    parser.add_argument("--auto-discovered", action="store_true", help="Used with --validate-context")
    parser.add_argument("--check-roles", action="store_true", help="Check for role violations")
    parser.add_argument("--check-process", action="store_true", help="Check for process violations")
    parser.add_argument("--output", choices=["json", "human"], default="human")

    args = parser.parse_args()
    root = find_project_root()

    if args.discover:
        discovered = discover_artifacts(root)
        if args.output == "json":
            print(json.dumps(discovered, indent=2))
        else:
            print(format_discovery_human(discovered))

    elif args.validate_context:
        discovered = discover_artifacts(root)
        missing_critical = []
        for key, info in discovered["standard"].items():
            if not info["exists"] and key in ["sprint_status", "locked_decisions"]:
                missing_critical.append(key)

        if args.output == "json":
            print(json.dumps({
                "valid": len(missing_critical) == 0,
                "missing_critical": missing_critical
            }))
        else:
            if missing_critical:
                print(f"✗ Missing critical files: {', '.join(missing_critical)}")
                sys.exit(1)
            else:
                print("✓ Context validation passed")


if __name__ == "__main__":
    main()
