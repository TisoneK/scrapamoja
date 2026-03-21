# Pushback Rules

## Pushback Definition
Pushback occurs when an Executor (or other agent) resists, questions, or attempts to override Advisor instructions or locked decisions.

## Pushback Handling Protocol

### Step 1: Identify Pushback Type
**Legitimate Questions**: Agent seeking clarification or understanding
**Process Challenges**: Agent questioning the validity of a rule or checkpoint
**Authority Challenges**: Agent attempting to override Advisor or locked decisions
**Implementation Issues**: Agent unable to execute instruction due to technical constraints

### Step 2: Apply Response Strategy

#### For Legitimate Questions
1. **Provide clarification**: Explain the reasoning behind the instruction
2. **Offer alternatives**: If multiple valid approaches exist, present options
3. **Document decision**: If new decision made, add to locked decisions
4. **Proceed with clarified instruction**

#### For Process Challenges
1. **Reference locked decisions**: "This rule is established per locked decision [id]"
2. **Explain process rationale**: Brief explanation of why the rule exists
3. **Offer proper challenge channel**: "To challenge this rule, we need to create a new locked decision"
4. **Maintain current instruction**: Do not modify instruction without proper process

#### For Authority Challenges
1. **Reiterate Advisor role**: "My role is to enforce BMAD process standards"
2. **Reference locked decisions**: Cite specific decisions that establish authority
3. **Escalate if necessary**: "Continued challenge requires Coordinator intervention"
4. **Document challenge**: Note in session report for follow-up

#### For Implementation Issues
1. **Identify specific barrier**: What exactly prevents execution?
2. **Provide workaround**: Alternative approach that achieves same goal
3. **Update instruction**: Modify instruction to be executable
4. **Verify workaround**: Ensure workaround still satisfies original requirement

### Step 3: Decision Documentation

#### When Pushback Results in New Decision
1. **Document the challenge**: What was challenged and why
2. **Document the resolution**: New rule or exception established
3. **Create locked decision**: Add to locked decisions document
4. **Update instructions**: Apply new decision to current and future instructions

#### When Pushback is Rejected
1. **Document rejection**: Why the challenge was not accepted
2. **Reinforce original instruction**: Reiterate with additional context
3. **Note pattern**: If repeated challenges from same agent, document pattern

## Pushback Prevention

### Clear Instructions
- Use precise, unambiguous language
- Include verification steps
- Provide context for why instruction is needed

### Anticipate Issues
- Identify potential implementation barriers
- Provide alternatives for common issues
- Reference relevant locked decisions upfront

### Progressive Disclosure
- Start with essential instructions
- Add detail as needed
- Allow for questions and clarification

## Escalation Procedures

### Level 1: Advisor Resolution
- Advisor handles pushback directly
- Uses established rules and locked decisions
- Documents outcome in session report

### Level 2: Coordinator Intervention
- When pushback challenges core process rules
- When agent refuses to comply with valid instructions
- When new locked decisions need to be created

### Level 3: Session Halt
- Persistent refusal to follow BMAD process
- Repeated violations despite clear instructions
- Ethical or safety concerns

## Pushback Response Templates

### Clarification Template
```
I understand you're asking about [specific point]. This instruction is needed because [rationale]. 
The rule we're following is [rule reference]. 

Would you like me to:
1. Proceed with original instruction
2. Modify the instruction to [alternative approach]
3. Create a new locked decision for this situation
```

### Process Challenge Template
```
I understand you're questioning [rule/checkpoint]. This is established per:
- Locked decision [id]: [summary]
- Process rule: [rule reference]

To properly challenge this, we need to create a new locked decision. 
Would you like to proceed with the current instruction and address the challenge separately?
```

### Implementation Issue Template
```
I see the instruction isn't working because [specific barrier]. Let me provide an alternative:

Tell the Executor:
```
[modified instruction that works around the barrier]
```

This achieves the same goal by [explanation of how workaround satisfies requirement].
```
