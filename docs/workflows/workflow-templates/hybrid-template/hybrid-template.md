---
description: Template for hybrid workflows combining LLM guidance with automation scripts
---

# Hybrid Workflow Template

This template provides a complete structure for workflows that combine LLM decision-making with automated script execution.

## Overview

Hybrid workflows are ideal for complex tasks that require:
- **Pattern recognition** (LLM strength)
- **Contextual decisions** (LLM strength) 
- **Batch processing** (Script strength)
- **Deterministic operations** (Script strength)

## Quick Start

1. **Copy this template** to your workflow directory
2. **Rename files** to match your workflow name
3. **Customize content** for your specific needs
4. **Test with sample data**
5. **Publish when ready**

## Template Structure

```
your-workflow/
├── start.md              # Entry point with mode selection
├── your-workflow.md      # Main workflow document
├── README.md             # Overview and quick start
├── rules.md              # LLM behavior rules
├── status.json           # Progress tracking
├── scripts/
│   ├── pwsh/            # PowerShell automation
│   └── bash/            # Bash automation
├── templates/           # Reusable templates
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
- [ ] Design automation scripts for your tasks
- [ ] Add your validation criteria

### LLM Configuration
- [ ] Update `rules.md` with your behavior requirements
- [ ] Define decision-making boundaries
- [ ] Set quality standards and validation
- [ ] Configure error handling preferences

### Script Development
- [ ] Modify PowerShell scripts for Windows environments
- [ ] Modify Bash scripts for Unix environments
- [ ] Add error handling and logging
- [ ] Test with your specific data formats

## Common Hybrid Patterns

### Pattern 1: Discovery → Analysis → Processing
1. **Script**: Scan and identify targets
2. **LLM**: Analyze and make decisions
3. **Script**: Apply changes based on decisions

### Pattern 2: Strategy → Execution → Validation
1. **LLM**: Generate strategy/plan
2. **Script**: Execute plan deterministically
3. **LLM**: Validate results and quality

### Pattern 3: Continuous Collaboration
1. **Script**: Present current state
2. **LLM**: Suggest next actions
3. **Script**: Execute and update state
4. **Repeat** until complete

## Integration Examples

### With Other Workflows
```markdown
This workflow integrates with:
- **/data-discovery**: Provides input data
- **/validation**: Consumes output for quality checks
- **/reporting**: Generates final reports
```

### With External Systems
```markdown
External integrations:
- **API endpoints**: For data retrieval
- **Database**: For persistent storage
- **File system**: For input/output operations
```

## Testing Your Workflow

1. **Unit test scripts** with sample data
2. **Test LLM prompts** with various inputs
3. **Validate end-to-end flow** with realistic scenarios
4. **Check error handling** with failure cases
5. **Verify integration** with dependent systems

## Deployment

When your workflow is ready:

1. **Update documentation** with final details
2. **Add to workflows.start.md** for discoverability
3. **Create examples** for common use cases
4. **Train users** on workflow operation
5. **Monitor performance** and iterate

---

*This template provides a solid foundation for sophisticated hybrid workflows. Adapt it to your specific requirements and constraints.*
