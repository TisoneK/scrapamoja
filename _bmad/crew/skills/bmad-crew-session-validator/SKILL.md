---
name: bmad-crew-session-validator
description: Validates BMAD session state for role, process, and quality violations. Use when checking session compliance or detecting violations.
---

# bmad-crew-session-validator

## Overview

This skill validates current BMAD session state for role, process, and quality violations. Use when checking session compliance or detecting violations. Returns structured violation report with exact findings.

## Input

- Current session context (commands executed, agents involved, outputs produced)
- Git repository status and history
- Document locations and read status
- Agent role boundaries and activities

## Process

1. **Load config via bmad-init skill** — Store all returned vars for use:
   - Use `{user_name}` from config for context
   - Use `{communication_language}` for all communications
   - Use `{document_output_language}` for output documents

2. **Greet user** as `{user_name}`, speaking in `{communication_language}`

3. **Proceed to validation steps below**

## Workflow Steps

### Step 1: Role Violation Detection
Run `scripts/session-check.py --check-roles` to detect:
- Advisor becoming Executor
- Executor self-certifying completion
- Agent role confusion

### Step 2: Process Violation Detection
Run `scripts/session-check.py --check-process` to detect:
- New session before previous work committed
- Skipping code review
- dev-story without clean git status
- Session boundary violations

### Step 3: Quality Violation Detection
Run `scripts/session-check.py --check-quality` to detect:
- Completion without commit hash
- Documents confirmed without being read
- Incomplete output
- Quality standard violations

### Step 4: Compile Violation Report
Aggregate all findings into structured report:
- Categorize by severity (critical, high, medium, low)
- Reference specific rules from violation types
- Provide exact correction requirements

## Output

Structured JSON violation report with:
- Violation type and severity
- Rule references
- Exact correction instructions
- Verification methods

## Scripts

Available scripts in `scripts/`:
- `session-check.py` — Comprehensive session validation with git and file checks
