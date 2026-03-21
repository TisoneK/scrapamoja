# Instruction Patterns

## Pattern Philosophy
Instructions are patterns and examples, not rigid templates. The Advisor generates instructions contextually based on session state, using these patterns as guidance for structure and approach.

## Universal Instruction Structure

### Three-Part Pattern
All instructions follow this structure:
1. **Assessment** - What was found and why it matters
2. **Instruction** - Exact command in code block for Coordinator to paste
3. **Next Action** - What Coordinator should do after Executor completes instruction

### Code Block Requirement
All executable instructions MUST be in code blocks:
```
Tell the Executor:
```
[exact instruction here]
```
```

## Violation Correction Patterns

### Role Violation Pattern
```
Assessment: Role violation detected - [specific role violation]

Tell the Executor:
```
[correction instruction that restores proper role boundaries]
```

Next Action: Verify the role correction by [verification method]
```

**Example**:
```
Assessment: Role violation detected - Advisor attempting to execute BMAD commands

Tell the Executor:
```
Please run the build command and provide the output for review.
```

Next Action: Verify the Executor runs the command and Advisor provides review only.
```

### Process Violation Pattern
```
Assessment: Process violation detected - [specific process violation]

Tell the Executor:
```
[step-by-step instructions to follow correct process]
```

Next Action: Confirm [process requirement] is satisfied before proceeding.
```

**Example**:
```
Assessment: Process violation detected - New session started without committing previous work

Tell the Executor:
```
Please commit all changes from the previous session:
1. Run `git add .` to stage all changes
2. Run `git commit -m "Complete previous session work"`
3. Verify commit appears in git log
```

Next Action: Confirm clean git status before starting new session work.
```

### Quality Violation Pattern
```
Assessment: Quality violation detected - [specific quality issue]

Tell the Executor:
```
[instructions to bring work up to quality standards]
```

Next Action: Verify quality standards are met by [verification method].
```

**Example**:
```
Assessment: Quality violation detected - Document confirmed without being read

Tell the Executor:
```
Please read the document and provide specific feedback:
1. Read sections [list sections]
2. Note any issues or missing information
3. Confirm understanding of key points
```

Next Action: Verify document was actually read by referencing specific content.
```

## Checkpoint Fix Patterns

### Commit Checkpoint Pattern
```
Assessment: Commit checkpoint failed - [specific commit issue]

Tell the Executor:
```
[git commands to satisfy commit requirements]
```

Next Action: Verify commit checkpoint passes by checking git log.
```

**Example**:
```
Assessment: Commit checkpoint failed - No new commit hash found after claimed completion

Tell the Executor:
```
Please commit your completed work:
1. Run `git status` to see what needs to be committed
2. Run `git add .` to stage all changes
3. Run `git commit -m "feat: complete [feature name] implementation"`
4. Run `git log --oneline -1` to verify new commit
```

Next Action: Confirm new commit hash appears in git log.
```

### Summary Checkpoint Pattern
```
Assessment: Summary checkpoint failed - [specific summary issue]

Tell the Executor:
```
[instructions to create or complete summary]
```

Next Action: Verify summary checkpoint passes by checking content and location.
```

## Progress Instruction Patterns

### Clean Session Pattern
```
Assessment: Session is clean - no violations or checkpoint issues detected

Tell the Executor:
```
You may proceed with [next planned action].
```

Next Action: Monitor for violations during the next action.
```

### Locked Decision Pattern
```
Assessment: Locked decision applies - [decision summary]

Tell the Executor:
```
[instruction that respects the locked decision]
```

Next Action: Verify instruction follows locked decision guidelines.
```

## Contextual Adaptation Patterns

### Agent-Specific Adaptations
**For Executor**: Focus on execution commands and verification steps
**For Coordinator**: Focus on oversight and validation commands  
**For Other Agents**: Adapt language and expectations to agent role

### Session Phase Adaptations
**Discovery Phase**: Focus on information gathering and validation
**Planning Phase**: Focus on decision documentation and requirement gathering
**Execution Phase**: Focus on process compliance and quality standards
**Review Phase**: Focus on thoroughness and completion verification

### Complexity Adaptations
**Simple Issues**: Direct instruction with single verification step
**Complex Issues**: Multi-step instructions with intermediate verifications
**Systemic Issues**: Pattern identification and process improvement recommendations

## Error Recovery Patterns

### Instruction Failure Pattern
```
Assessment: Previous instruction failed - [reason for failure]

Tell the Executor:
```
[alternative instruction or workaround]
```

Next Action: Verify workaround achieves the original goal.
```

### Ambiguity Resolution Pattern
```
Assessment: Instruction was ambiguous - [what was unclear]

Tell the Executor:
```
[clarified instruction with more specific details]
```

Next Action: Confirm instruction is clear and executable.
```

## Verification Patterns

### Git Verification
```bash
git log --oneline -5  # Verify commits
git status --porcelain   # Verify clean status
git diff HEAD~1         # Verify changes
```

### File Verification
```bash
ls -la {file_path}      # Verify file exists
grep -c "pattern" {file}  # Verify content
wc -l {file}            # Verify completeness
```

### Process Verification
- Check for expected outputs
- Validate required steps were completed
- Confirm quality standards met

## Pattern Evolution

These patterns evolve based on:
- Session experience and feedback
- New violation types discovered
- Process improvements implemented
- Agent behavior patterns observed

The Advisor uses these patterns as starting points, adapting instructions to specific context while maintaining the core structure and precision requirements.
