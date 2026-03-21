---
name: bmad-crew-checkpoint-enforcer
description: Enforces BMAD checkpoints and validates completion requirements. Use when validating phase boundaries or checkpoint compliance.
---

# bmad-crew-checkpoint-enforcer

## Overview

This skill enforces BMAD checkpoints and validates completion requirements. Use when validating phase boundaries or checkpoint compliance. Returns pass/fail result with exact correction instructions.

## Input

- Checkpoint type to validate (commit, summary, code review, session)
- Current session state and context
- Required artifacts and their locations
- Previous checkpoint status

## Process

1. **Load config via bmad-init skill** — Store all returned vars for use:
   - Use `{user_name}` from config for context
   - Use `{communication_language}` for all communications
   - Use `{document_output_language}` for output documents

2. **Greet user** as `{user_name}`, speaking in `{communication_language}`

3. **Proceed to enforcement steps below**

## Workflow Steps

### Step 1: Determine Checkpoint Type
Identify which checkpoints to validate based on session context:
- Commit checkpoints (every output-producing command)
- Summary checkpoints (phase boundaries)
- Code review checkpoints (code changes)
- Session checkpoints (start/end)

### Step 2: Run Checkpoint Validation
Run `scripts/checkpoint-validator.py` with appropriate parameters:
- `--check-commits` for commit checkpoints
- `--check-summaries` for summary checkpoints
- `--check-reviews` for code review checkpoints
- `--check-sessions` for session checkpoints

### Step 3: Analyze Results
Process validation results:
- Identify failed checkpoints
- Determine exact requirements not met
- Generate specific correction instructions

### Step 4: Generate Instructions
Create step-by-step instructions for each failed checkpoint:
- Exact commands to fix checkpoint
- Verification steps to confirm fix
- Next actions after checkpoint passes

## Output

Structured checkpoint report with:
- Pass/fail status for each checkpoint type
- Exact correction instructions for failures
- Verification commands
- Checkpoint completion requirements

## Scripts

Available scripts in `scripts/`:
- `checkpoint-validator.py` — Validates commits, summaries, and code reviews
