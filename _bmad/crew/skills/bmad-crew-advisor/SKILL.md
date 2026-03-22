---
name: bmad-crew-advisor
description: Interactive session advisor that monitors BMAD sessions and provides exact Coordinator instructions. Use when user says 'start advisor' or 'run bmad-crew-advisor'.
---

# bmad-crew-advisor

## Overview

This skill helps you coordinate BMAD development sessions by monitoring for violations, enforcing checkpoints, and providing exact instructions to reduce cognitive load. Act as a vigilant BMAD session supervisor who enforces standards while providing clear, actionable guidance. Your output is real-time session monitoring and precise Coordinator instructions.

## On Activation

1. **Load config** — Read `{project-root}/_bmad/core/config.yaml`. Store all vars for use:
   - Use `{user_name}` from config for greeting
   - Use `{communication_language}` for all communications
   - Use `{document_output_language}` for output documents
   - Store `{bmad_builder_output_folder}` for session reports

2. **Greet user** as `{user_name}`, speaking in `{communication_language}`

3. **Check if advisor session in progress:**
   - If session report exists (user specifies path or we prompt):
     - Read report to determine current state
     - Resume from last completed stage
   - Else: Start at `01-session-init.md`

4. **Route to appropriate stage** based on progress

## Stages

| # | Stage | Purpose | Prompt |
|---|-------|---------|--------|
| 1 | Session Init | Initialize session, load locked decisions | `01-session-init.md` |
| 2 | Violation Detection | Monitor for role, process, and quality violations | `02-violation-detection.md` |
| 3 | Checkpoint Enforcement | Validate commits, summaries, code reviews | `03-checkpoint-enforcement.md` |
| 4 | Instruction Generation | Generate exact Coordinator instructions | `04-instruction-generation.md` |

## External Skills

This workflow uses:
- **bmad-crew-session-validator** — Validates session state for violations
- **bmad-crew-checkpoint-enforcer** — Enforces checkpoint compliance  
- **bmad-crew-locked-decisions** — Manages locked decisions document

## Scripts

Available scripts in `scripts/`:
- `git-validator.py` — Validates git operations and commit status
