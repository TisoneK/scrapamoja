# Hybrid Workflow Template

A comprehensive template for workflows that combine LLM guidance with automation scripts.

## Purpose

This template provides structure for complex workflows requiring both AI decision-making and automated processing.

## Key Features

- **LLM Integration**: Structured prompts and decision points
- **Automation**: PowerShell and Bash scripts for repetitive tasks
- **Status Tracking**: Real-time progress monitoring
- **Quality Assurance**: Built-in validation and error handling
- **Flexibility**: Adaptable to various use cases

## Quick Start

1. **Copy Template**: 
   ```bash
   cp -r docs/workflows/workflow-templates/hybrid-template docs/workflows/your-workflow
   ```

2. **Rename Files**: Replace `hybrid-template` with your workflow name

3. **Customize Content**: 
   - Update descriptions and purposes
   - Modify workflow steps
   - Configure LLM rules
   - Adapt automation scripts

4. **Test**: Validate with sample data

5. **Deploy**: Add to workflow registry

## Template Components

### Core Files
- **start.md**: Entry point with mode selection
- **hybrid-template.md**: Main workflow documentation
- **README.md**: User-friendly overview
- **rules.md**: LLM behavior guidelines
- **status.json**: Progress tracking

### Automation
- **scripts/pwsh/**: Windows PowerShell scripts
- **scripts/bash/**: Unix/Linux Bash scripts

### Resources
- **templates/**: Reusable prompt templates
- **examples/**: Sample inputs and outputs

## Common Use Cases

- **Code Refactoring**: Automated code updates with LLM guidance
- **Data Processing**: Batch processing with contextual decisions
- **Documentation Generation**: Auto-generate docs with AI review
- **Quality Assurance**: Automated testing with LLM validation

## Integration

This template integrates with:
- **Workflow Creation Guide**: For setup instructions
- **Hybrid Workflows Guide**: For advanced patterns
- **Reference Fill**: Example implementation

---

*Adapt this template to your specific workflow requirements.*
