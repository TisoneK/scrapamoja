---
name: bmad-crew-locked-decisions
description: Manages living document of locked decisions and handles pushback rules. Use when tracking decisions or handling Executor pushback.
---

# bmad-crew-locked-decisions

## Overview

This skill manages living document of locked decisions and handles pushback rules. Use when tracking decisions or handling Executor pushback. Returns current locked decisions and update instructions.

## Input

- Session context and current decision type
- Proposed changes or challenges to existing decisions
- Decision category and scope
- Agent involved in decision or challenge

## Process

1. **Load config via bmad-init skill** — Store all returned vars for use:
   - Use `{user_name}` from config for context
   - Use `{communication_language}` for all communications
   - Use `{document_output_language}` for output documents

2. **Greet user** as `{user_name}`, speaking in `{communication_language}`

3. **Proceed to decision management steps below**

## Workflow Steps

### Step 1: Load Existing Decisions
Run `scripts/decision-manager.py --load` to retrieve current locked decisions:
- Parse existing decisions document
- Load decision metadata and history
- Identify relevant decisions for current context

### Step 2: Analyze Decision Context
Determine decision requirements:
- Check if existing decisions apply to current situation
- Identify decision gaps that need new locked decisions
- Assess impact of proposed changes

### Step 3: Process Decision Request
Handle different decision scenarios:
- **New Decision**: Create new locked decision with proper documentation
- **Challenge Existing**: Apply pushback rules and provide challenge process
- **Update Decision**: Modify existing decision with proper process
- **Query Decisions**: Return relevant decisions for current context

### Step 4: Generate Decision Output
Create structured decision output:
- Current applicable locked decisions
- Decision history and rationale
- Instructions for compliance or challenge process

## Output

Structured decision report with:
- Current locked decisions relevant to context
- Decision history and rationale
- Compliance instructions
- Challenge process when applicable

## Scripts

Available scripts in `scripts/`:
- `decision-manager.py` — Document parsing, decision validation, and update generation
