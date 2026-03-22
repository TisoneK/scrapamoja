#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""
Generates ADVISOR_SESSION_MISTAKES_NNN.md after each completed story cycle.
Run automatically by the Advisor — never prompted by the Coordinator.

Usage:
  python3 mistakes-generator.py --story-id STORY-3.1 --output-dir path/to/sessions/
  python3 mistakes-generator.py --story-id STORY-3.1 --violations file.json --output-dir path/
  python3 mistakes-generator.py --get-next-counter --sessions-dir path/to/sessions/
"""

import argparse
import sys
import json
import re
from pathlib import Path
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from datetime import datetime


def get_next_counter(sessions_dir: Path) -> int:
    """Find the next available NNN counter by scanning existing files."""
    pattern = re.compile(r"ADVISOR_SESSION_MISTAKES_(\d+)\.md")
    max_n = 0
    if sessions_dir.exists():
        for f in sessions_dir.glob("ADVISOR_SESSION_MISTAKES_*.md"):
            m = pattern.match(f.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def generate_mistakes_file(
    story_id: str,
    violations: list,
    corrections: list,
    review_findings: list,
    process_notes: str,
    carry_forward: list,
    output_dir: Path
) -> Path:
    """Generate the mistakes file and return its path."""
    counter = get_next_counter(output_dir)
    filename = f"ADVISOR_SESSION_MISTAKES_{counter:03d}.md"
    filepath = output_dir / filename

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    lines = [
        f"# Advisor Session Mistakes — {story_id} — {timestamp}",
        "",
        "## Story",
        story_id,
        "",
    ]

    if violations:
        lines += ["## Violations Detected This Cycle", ""]
        for v in violations:
            lines.append(f"- VIOLATION: {v.get('type', 'unknown')} — {v.get('description', '')} — Caught at: {v.get('gate', 'unknown')}")
        lines.append("")
    else:
        lines += ["## Violations Detected This Cycle", "", "None.", ""]

    if corrections:
        lines += ["## Corrections Issued", ""]
        for c in corrections:
            lines.append(f"- {c}")
        lines.append("")

    if review_findings:
        lines += [
            "## Code Review Findings Summary",
            "",
            "| Finding | Classification | Resolution |",
            "|---------|---------------|------------|",
        ]
        for f in review_findings:
            lines.append(f"| {f.get('description', '')} | {f.get('classification', '')} | {f.get('resolution', '')} |")
        lines.append("")

    if process_notes:
        lines += ["## Process Notes", "", process_notes, ""]

    if carry_forward:
        lines += ["## Carry-Forward Reminders", ""]
        for item in carry_forward:
            lines.append(f"- {item}")
        lines.append("")

    if not violations and not corrections:
        lines = [
            f"# Advisor Session Mistakes — {story_id} — {timestamp}",
            "",
            "## Story",
            story_id,
            "",
            "## Result",
            "",
            "Clean cycle. No violations detected. No corrections required.",
            "",
        ]
        if review_findings:
            patch_count = sum(1 for f in review_findings if f.get("classification") == "patch")
            defer_count = sum(1 for f in review_findings if f.get("classification") == "defer")
            lines.append(f"## Code Review")
            lines.append("")
            lines.append(f"{len(review_findings)} findings: {patch_count} patch, {defer_count} defer — all resolved.")
            lines.append("")

    output_dir.mkdir(parents=True, exist_ok=True)
    filepath.write_text("\n".join(lines))
    return filepath


def main():
    parser = argparse.ArgumentParser(description="BMAD mistakes file generator")
    parser.add_argument("--story-id", help="Story identifier (e.g. STORY-3.1)")
    parser.add_argument("--violations", help="JSON file with violations list")
    parser.add_argument("--review-findings", help="JSON file with code review findings")
    parser.add_argument("--output-dir", required=True, help="Output directory for mistakes file")
    parser.add_argument("--get-next-counter", action="store_true",
                        help="Print next counter number and exit")
    parser.add_argument("--sessions-dir", help="Sessions dir (used with --get-next-counter)")

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if args.get_next_counter:
        sessions_dir = Path(args.sessions_dir) if args.sessions_dir else output_dir
        print(get_next_counter(sessions_dir))
        return

    violations = []
    if args.violations:
        violations = json.loads(Path(args.violations).read_text())

    review_findings = []
    if args.review_findings:
        review_findings = json.loads(Path(args.review_findings).read_text())

    filepath = generate_mistakes_file(
        story_id=args.story_id or "unknown",
        violations=violations,
        corrections=[],
        review_findings=review_findings,
        process_notes="",
        carry_forward=[],
        output_dir=output_dir,
    )

    result = {"path": str(filepath), "story_id": args.story_id, "status": "ok"}
    print(f"Mistakes file saved: {filepath}")
    if hasattr(args, "output") and args.output == "json":
        print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
