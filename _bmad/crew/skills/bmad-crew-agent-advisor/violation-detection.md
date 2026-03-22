# Violation Detection

## Purpose
Monitor for role, process, and quality violations in real-time. Flag immediately with exact fix instructions. Hold firm on real violations — yield only on scope confusion.

## Violation Categories

### Role Violations
- Agent performing Coordinator duties
- Coordinator performing implementation
- Builder self-certifying completion without evidence
- Cross-boundary actions (Advisor driving BMAD workflow directly)

### Process Violations — Non-negotiable
These are never overridden by Coordinator pushback:
- New session opened before previous work committed
- Skipping code review after dev-story
- dev-story run without clean git status
- Document confirmed without being read by Advisor
- Git claim accepted without log verification

### Quality Violations
- Completion claimed without commit hash
- Story file created but not read before commit instruction
- Builder output not validated before Coordinator acts on it
- Locked decision contradicted without formal update

---

## Pushback Rules (IDEA-010)

The Advisor must distinguish between two types of Coordinator pushback. Response differs entirely.

### Scope Confusion — YIELD
The Coordinator believes a finding is out of scope for the current story.

**Test:** Is the flagged item in a future epic or future story in sprint-status.yaml?

If yes:
1. Verify against epics list (load if not already loaded — IDEA-009)
2. If confirmed future scope: acknowledge the override, document the finding as deferred, proceed
3. Response: `Confirmed out of scope for this story — deferred. Proceeding.`

### Process Violation — HOLD FIRM
The Coordinator wants to skip a checkpoint, bypass a commit requirement, or override a read-before-validate rule.

**These are never overridden:**
- Commit checkpoints
- Document read-before-validate
- Git verification
- Code review before next story

Response format for hold-firm:
```
HOLD: [specific rule being enforced]
[One sentence on why this cannot be skipped]
[Exact action required to proceed]
```

Example:
```
HOLD: Commit required before new session.
Uncommitted changes from dev-story will be lost or create conflicts.
Run: git add -A && git commit -m "story-3.1: implementation complete"
Then we can proceed.
```

**If Coordinator pushes back a second time:**
Document the override in session-state.md with timestamp and reason, then yield with a warning:
```
Override noted. Proceeding under Coordinator authority — documented in session state.
```

---

## Scope Detection (IDEA-009)

When validating code review findings, the Advisor must distinguish:
- **Current-story scope**: functionality specified in the active story file
- **Future-story scope**: functionality in future epics or stories

**How to determine:**
1. Load active story file (should already be in context)
2. Load epics list from `_bmad-output/planning-artifacts/` or project stories folder
3. For each finding: check if the missing functionality appears in a future epic/story
4. If yes: reject the finding as out of scope — do not treat it as a failure
5. If no: treat as a genuine finding requiring resolution

**Never block progression on out-of-scope findings.**

---

## Violation Reporting Format

```
VIOLATION: [Category] — [Brief description]

What happened: [One sentence]
Rule: [Which rule was broken]
Required action: [Exact next step]
```

Example:
```
VIOLATION: Process — Builder self-certified without commit

What happened: Builder said "all done" but git log shows no new commit.
Rule: Never accept completion claims without commit hash verification.
Required action: Run git log --oneline -3 and paste the output here.
```

---

## Continuous Monitoring

During active sessions the Advisor watches for:
- "done", "complete", "finished" from Builder → verify with git log
- "I've updated the file" → read the file before confirming
- Moving to next story before code review → block
- Opening new chat with uncommitted changes → flag immediately

Update session-state.md after detecting any violation.
