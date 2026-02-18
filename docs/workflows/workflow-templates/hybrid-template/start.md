---
description: Entry point for hybrid workflow with mode selection
---

# Hybrid Workflow Template

Choose your workflow mode:

## 🚀 Quick Start

### Discovery Mode
Identify and analyze targets for processing.
- **Use when**: Starting new workflow or exploring data
- **Output**: List of identified items with metadata

### Processing Mode  
Execute the main workflow logic.
- **Use when**: Ready to apply changes or generate output
- **Output**: Processed results and updated files

### Validation Mode
Check results and ensure quality.
- **Use when**: Verifying workflow completion
- **Output**: Validation report and issues found

### Status Mode
View current workflow progress and metrics.
- **Use when**: Checking workflow state
- **Output**: Current status and progress information

## 📋 Prerequisites

- **LLM Assistant**: For decision-making and analysis
- **PowerShell/Bash**: For automation scripts
- **File Access**: Read/write permissions for target directories
- **Configuration**: Rules and constraints defined in `rules.md`

## 🔧 Configuration

Current workflow settings are defined in:
- **rules.md**: LLM behavior and decision guidelines
- **status.json**: Progress tracking and metrics
- **scripts/**: Automation tools and utilities

## 📊 Current Status

```json
{
  "workflow": "hybrid-template",
  "status": "template",
  "progress": 0,
  "ready_for_customization": true
}
```

## 🚀 Getting Started

1. **Customize this template** for your specific needs
2. **Update rules.md** with your LLM behavior requirements
3. **Modify scripts** for your automation tasks
4. **Test with sample data** before production use
5. **Monitor progress** using status tracking

## 📚 Documentation

- **Main Guide**: [hybrid-template.md](hybrid-template.md)
- **Overview**: [README.md](README.md)
- **LLM Rules**: [rules.md](rules.md)

---

*This is a template. Customize it for your specific workflow requirements.*
