---
description: Template for LLM-only workflows with pure AI guidance
---

# LLM-Only Workflow Template

This template provides structure for workflows that rely entirely on LLM guidance and human interaction, without automation scripts.

## Overview

LLM-only workflows are ideal for tasks that require:
- **Creative problem-solving** (LLM strength)
- **Contextual analysis** (LLM strength)
- **Human judgment** (Human strength)
- **Flexible processes** (LLM + Human strength)

## Quick Start

1. **Copy this template** to your workflow directory
2. **Rename files** to match your workflow name
3. **Customize prompts** for your specific domain
4. **Test with sample scenarios**
5. **Publish when ready**

## Template Structure

```
your-workflow/
├── start.md              # Entry point with mode selection
├── your-workflow.md      # Main workflow document
├── README.md             # Overview and quick start
├── rules.md              # LLM behavior rules
├── status.json           # Progress tracking
├── templates/           # Reusable prompt templates
└── examples/           # Sample inputs/outputs
```

## Customization Checklist

### Basic Setup
- [ ] Update workflow name in all files
- [ ] Replace template descriptions with your purpose
- [ ] Set up your specific prerequisites
- [ ] Configure status.json structure

### Content Customization
- [ ] Write your specific workflow steps
- [ ] Create relevant LLM prompts
- [ ] Design decision-making frameworks
- [ ] Add validation criteria

### LLM Configuration
- [ ] Update `rules.md` with your behavior requirements
- [ ] Define decision-making boundaries
- [ ] Set quality standards and validation
- [ ] Configure error handling preferences

### Prompt Development
- [ ] Create template prompts for each workflow step
- [ ] Design validation prompts for quality checks
- [ ] Build decision-making prompts for complex choices
- [ ] Test prompts with various scenarios

## Common LLM-Only Patterns

### Pattern 1: Analysis → Recommendation → Review
1. **LLM**: Analyze situation and identify options
2. **Human**: Review recommendations and provide feedback
3. **LLM**: Refine recommendations based on feedback
4. **Human**: Make final decision

### Pattern 2: Generation → Validation → Iteration
1. **LLM**: Generate content or solution
2. **LLM**: Self-validate against criteria
3. **Human**: Review and provide feedback
4. **LLM**: Iterate and improve

### Pattern 3: Exploration → Synthesis → Decision
1. **LLM**: Explore multiple approaches
2. **LLM**: Synthesize findings and compare options
3. **Human**: Evaluate trade-offs and decide

## Integration Examples

### With Other Workflows
```markdown
This workflow integrates with:
- **/data-analysis**: Provides input data for analysis
- **/decision-making**: Consumes recommendations
- **/documentation**: Records decisions and rationale
```

### With External Systems
```markdown
External integrations:
- **Document repositories**: For research and analysis
- **Communication tools**: For human collaboration
- **Knowledge bases**: For reference and validation
```

## Testing Your Workflow

1. **Test prompts** with various input scenarios
2. **Validate decision-making** with edge cases
3. **Review human interaction points** for clarity
4. **Check quality criteria** with sample outputs
5. **Verify integration** with dependent systems

## Deployment

When your workflow is ready:

1. **Finalize prompts** with comprehensive testing
2. **Document decision frameworks** clearly
3. **Create examples** for common scenarios
4. **Train users** on interaction patterns
5. **Monitor quality** and refine prompts

---

*This template provides a foundation for sophisticated AI-driven workflows. Adapt it to your specific domain and requirements.*
