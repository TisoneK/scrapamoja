# Instruction Generation

## Purpose
Generate exact, actionable Coordinator instructions for violation remediation and process compliance. This capability reduces cognitive load by providing precise guidance.

## On Activation

1. **Load Context**
   - Load current session state and violations
   - Review locked decisions and standards
   - Identify specific issue requiring instruction

2. **Determine Instruction Type**
   Based on the issue:
   - **Violation remediation** - Fix specific violations
   - **Process compliance** - Follow correct workflow
   - **Quality improvement** - Meet quality standards
   - **Decision alignment** - Align with locked decisions

## Instruction Generation Framework

### Structure for All Instructions
```
## [Action Category]: [Specific Issue]

**What needs to happen:** [Clear, concise statement of required action]

**Step-by-step instructions:**
1. [First specific action]
2. [Second specific action]
3. [Third specific action]

**Why this matters:** [Brief explanation of impact/importance]

**Verification:** [How to confirm the action is complete]

**If you need help:** [What to do if instructions are unclear]
```

## Violation Remediation Instructions

### Role Boundary Violations

**Agent Overreach:**
```
## Role Correction: Agent Boundary Violation

**What needs to happen:** Redirect agent to proper role boundaries

**Step-by-step instructions:**
1. Stop the current agent action immediately
2. Say: "That task is outside your role boundaries. Let me handle this."
3. Assign the task to the appropriate role/person
4. Reinforce the agent's proper role: "Your focus should be on [proper role]."

**Why this matters:** Role boundaries prevent confusion and ensure proper workflow execution.

**Verification:** Agent is working within their defined role and not overstepping.

**If you need help:** Ask me to clarify role boundaries for any agent.
```

**Coordinator Overreach:**
```
## Role Correction: Coordinator Implementation

**What needs to happen:** Move implementation tasks to proper executor

**Step-by-step instructions:**
1. Stop any implementation work you're doing
2. Say: "I need to assign this implementation work to the appropriate agent."
3. Use the bmad-dev or bmad-quick-dev agent for implementation
4. Focus on coordination and decision-making

**Why this matters:** Coordinators should guide, not implement. This maintains clear separation of concerns.

**Verification:** Implementation is being handled by development agents, not you.

**If you need help:** I can recommend the right agent for the specific implementation task.
```

### Process Violations

**Skipping Phase:**
```
## Process Compliance: Complete Missing Phase

**What needs to happen:** Complete the [Phase Name] phase before proceeding

**Step-by-step instructions:**
1. Stop current work in [Current Phase]
2. Return to [Missing Phase]
3. Complete these required artifacts:
   - [Artifact 1]: [Specific requirement]
   - [Artifact 2]: [Specific requirement]
4. Run checkpoint validation: `python scripts/checkpoint-validator.py --phase [Missing Phase]`
5. Once validated, proceed to [Current Phase]

**Why this matters:** Each phase builds necessary foundations for the next. Skipping creates risks.

**Verification:** Checkpoint validator confirms phase completion.

**If you need help:** I can guide you through the specific requirements for [Missing Phase].
```

**Missing Documentation:**
```
## Process Compliance: Document Current Work

**What needs to happen:** Create required documentation for current phase

**Step-by-step instructions:**
1. Document what has been accomplished so far
2. Capture decisions made and their rationale
3. Identify any gaps or unresolved issues
4. Create the missing artifact: [Artifact Name]
5. Save to: {bmad_builder_output_folder}/[appropriate-folder]/

**Why this matters:** Documentation ensures continuity and enables proper handoffs.

**Verification:** Required artifact exists and contains necessary information.

**If you need help:** I can provide a template for [Artifact Name].
```

### Quality Violations

**Standards Non-compliance:**
```
## Quality Compliance: Align with Standards

**What needs to happen:** Bring work into compliance with established standards

**Step-by-step instructions:**
1. Review the violated standard: [Standard Name]
2. Identify specific non-compliant elements
3. Modify work to meet standard requirements:
   - [Specific change 1]
   - [Specific change 2]
4. Validate compliance against standard
5. Update documentation to reflect changes

**Why this matters:** Standards ensure consistency, quality, and maintainability.

**Verification:** Work now passes standard validation checks.

**If you need help:** I can provide detailed guidance on [Standard Name] requirements.
```

**Contradicting Locked Decisions:**
```
## Decision Alignment: Respect Locked Decisions

**What needs to happen:** Align current approach with locked decisions

**Step-by-step instructions:**
1. Review locked decision: [Decision Reference]
2. Identify the contradiction in current approach
3. Choose one option:
   - Option A: Modify current approach to align with locked decision
   - Option B: Formally update the locked decision (requires consensus)
4. If Option A: Make these specific changes...
5. If Option B: Document the change request and circulate for review

**Why this matters:** Locked decisions provide architectural consistency and prevent fragmentation.

**Verification:** Current approach aligns with locked decisions or decision is properly updated.

**If you need help:** I can facilitate the decision update process if needed.
```

## Process Improvement Instructions

### Workflow Optimization
```
## Workflow Improvement: Streamline [Process Name]

**What needs to happen:** Optimize the current workflow for better efficiency

**Step-by-step instructions:**
1. Analyze current workflow bottlenecks
2. Identify improvement opportunities
3. Implement these optimizations:
   - [Optimization 1]
   - [Optimization 2]
4. Test the improved workflow
5. Document the changes for future sessions

**Why this matters:** Efficient workflows reduce session time and improve outcomes.

**Verification:** Workflow completes faster with same or better quality.

**If you need help:** I can suggest specific optimizations based on current session patterns.
```

## Memory Integration

After generating instructions:
1. **Update session-state.md** with issued instructions
2. **Track instruction effectiveness** 
3. **Note patterns** for recurring instruction types
4. **Update locked decisions** if instructions lead to new decisions

## Instruction Customization

### Adapt to User Context
- **User experience level** - More detail for beginners, concise for experts
- **Session time pressure** - Quick fixes vs. thorough solutions
- **Team composition** - Adjust instructions based on available roles
- **Technical constraints** - Consider limitations and workarounds

### Follow-up Support
Always include:
- **Verification criteria** - How to know it's done right
- **Help availability** - When and how to ask for more help
- **Next steps** - What to do after instruction completion

## Integration Points

This capability works with:
- **violation-detection.md** - Receive violation alerts and generate remediation
- **checkpoint-enforcement.md** - Provide instructions for blocked checkpoints
- **session-init.md** - Generate setup instructions for new sessions
- **External skills** - Use specialized skills for complex instruction generation
