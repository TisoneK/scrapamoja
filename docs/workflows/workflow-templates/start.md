---
description: Entry point for workflow template selection and creation
---

# Workflow Template Selection

Choose a template to create your new workflow.

## Available Templates

### 1. 🤖 Hybrid Workflow Template
**Best for**: Complex workflows combining LLM guidance with automation scripts
**Use when**: You need both AI decision-making and automated processing
**Examples**: Code refactoring, data processing pipelines, documentation generation

### 2. 🧠 LLM-Only Workflow Template  
**Best for**: Purely AI-guided processes
**Use when**: Workflow relies entirely on LLM interaction and human decisions
**Examples**: Code review, content analysis, creative tasks

### 3. ⚡ Script-Only Workflow Template
**Best for**: Fully automated processes
**Use when**: Workflow can be completely automated without AI assistance
**Examples**: Batch processing, system maintenance, file operations

### 4. 📋 Process Workflow Template
**Best for**: Step-by-step manual processes
**Use when**: Workflow follows standardized procedures with human checkpoints
**Examples**: Deployment procedures, compliance checks, quality assurance

## Quick Start

1. **Select template type** from the options above
2. **Copy template directory** to your desired workflow name
3. **Customize content** following the template's README instructions
4. **Test workflow** with sample data
5. **Publish** when ready

## Template Creation Commands

### PowerShell
```powershell
# Copy hybrid template
Copy-Item -Recurse "docs/workflows/workflow-templates/hybrid-template" "docs/workflows/your-workflow-name"

# Copy LLM-only template  
Copy-Item -Recurse "docs/workflows/workflow-templates/llm-only-template" "docs/workflows/your-workflow-name"

# Copy script-only template
Copy-Item -Recurse "docs/workflows/workflow-templates/script-only-template" "docs/workflows/your-workflow-name"

# Copy process template
Copy-Item -Recurse "docs/workflows/workflow-templates/process-template" "docs/workflows/your-workflow-name"
```

### Bash
```bash
# Copy hybrid template
cp -r docs/workflows/workflow-templates/hybrid-template docs/workflows/your-workflow-name

# Copy LLM-only template
cp -r docs/workflows/workflow-templates/llm-only-template docs/workflows/your-workflow-name

# Copy script-only template
cp -r docs/workflows/workflow-templates/script-only-template docs/workflows/your-workflow-name

# Copy process template
cp -r docs/workflows/workflow-templates/process-template docs/workflows/your-workflow-name
```

## Customization Guide

After copying your template:

1. **Update names**: Replace template names with your workflow name
2. **Modify content**: Adapt descriptions, steps, and examples
3. **Configure rules**: Update `rules.md` with your LLM behavior requirements
4. **Test scripts**: Modify automation scripts for your specific needs
5. **Update examples**: Replace sample data with your use cases

## Need Help?

- **Workflow Creation Guide**: [Comprehensive guide](workflow-creation-guide.md)
- **Hybrid Workflows Guide**: [Advanced patterns](hybrid-workflows-guide.md)
- **Example Workflow**: See [reference-fill](reference-fill/) for implementation reference

---

*Templates provide a solid foundation. Customize them to fit your specific needs and workflow requirements.*
