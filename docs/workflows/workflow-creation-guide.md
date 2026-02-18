---
description: Guide for creating new workflows in the Scorewise project
---

# Workflow Creation Guide

This guide explains how to create new workflows in the Scorewise project, following established patterns and conventions.

## Overview

Workflows in Scorewise are structured processes that guide users through specific tasks, whether they're LLM-assisted, automated, or manual procedures.

## Workflow Types

### Hybrid Workflows (Recommended)
- Combine LLM-guided steps with automation scripts
- Use interactive prompts for decision points
- Leverage scripts for repetitive tasks
- Include status tracking with `status.json` 
- Example: `/reference-fill` 

### LLM-Only Workflows
- Focus entirely on structured prompts and human-LLM interaction
- Provide step-by-step guidance with template prompts
- Include validation and quality assurance steps

### Script-Only Workflows  
- Primarily automated with minimal human interaction
- Provide command-line interfaces
- Focus on batch processing and efficiency
- Use `scripts/pwsh/` and `scripts/bash/` directories

## Directory Structure

### Workflow Locations

```
docs/workflows/                        # Main workflows directory
├── workflows.start.md                 # Central entry point for all workflows
├── new-workflow/                     # Individual workflow directory
│   ├── start.md                      # Workflow-specific entry point
│   ├── new-workflow.md                # Main workflow document (matches directory name)
│   ├── README.md                      # Workflow overview and quick start
│   ├── rules.md                       # LLM behavior rules and constraints
│   ├── status.json                   # Status tracking
│   ├── scripts/
│   │   ├── pwsh/                    # PowerShell automation scripts (.ps1)
│   │   └── bash/                    # Bash automation scripts (.sh)
│   ├── templates/                     # Template files
│   └── examples/                     # Example outputs
└── ...
```

**Naming Convention:** The main workflow document should be named `workflow-name.md`, matching the directory name. For example:
- Directory: `reference-fill/` → Main document: `reference-fill.md` 
- Directory: `selector-debugging/` → Main document: `selector-debugging.md` 
- Directory: `opsx-verify/` → Main document: `opsx-verify.md` 

### Choosing the Right Location

- **`docs/workflows/`**: All workflows live here
- **`workflows.start.md`**: Central entry point listing all workflows
- **`workflow/start.md`**: Individual workflow entry points
- **`workflow-templates/`**: Template workflows for creating new workflows

## Workflow Templates Directory

For creating new workflows, use the templates system:

```
docs/workflows/workflow-templates/           # Template workflows directory
├── start.md                                # Template selection entry point
├── hybrid-template/                         # Hybrid workflow template
│   ├── start.md
│   ├── hybrid-template.md
│   ├── README.md
│   ├── rules.md
│   ├── status.json
│   ├── scripts/
│   │   ├── pwsh/
│   │   └── bash/
│   ├── templates/
│   └── examples/
├── llm-only-template/                       # LLM-only workflow template
│   ├── start.md
│   ├── llm-only-template.md
│   ├── README.md
│   ├── rules.md
│   ├── status.json
│   └── examples/
├── script-only-template/                     # Script-only workflow template
│   ├── start.md
│   ├── script-only-template.md
│   ├── README.md
│   ├── rules.md
│   ├── status.json
│   ├── scripts/
│   │   ├── pwsh/
│   │   └── bash/
│   └── examples/
└── process-template/                        # Process workflow template
    ├── start.md
    ├── process-template.md
    ├── README.md
    ├── rules.md
    ├── status.json
    └── examples/
```

### Using Workflow Templates

1. **Select Template**: Choose from available workflow types
2. **Copy Structure**: Duplicate the template directory
3. **Customize**: Modify content for your specific needs
4. **Configure**: Update names, descriptions, and rules
5. **Test**: Validate the workflow works as expected

### Template Selection Workflow

```markdown
# Workflow Template Selection

## Available Templates

### 1. Hybrid Workflow Template
**Use when**: Combining LLM guidance with automation scripts
**Includes**: Full script structure, LLM integration, status tracking
**Best for**: Complex workflows requiring both AI and automation

### 2. LLM-Only Workflow Template  
**Use when**: Purely LLM-guided processes
**Includes**: Prompt templates, validation steps, quality checks
**Best for**: Analysis, documentation, creative tasks

### 3. Script-Only Workflow Template
**Use when**: Fully automated processes
**Includes**: PowerShell/Bash scripts, error handling, reporting
**Best for**: Batch processing, system maintenance

### 4. Process Workflow Template
**Use when**: Step-by-step manual processes
**Includes**: Checklists, decision trees, validation
**Best for**: Standardized procedures, compliance

## Quick Start

1. **Choose template type** based on your needs
2. **Copy template directory** to your workflow name
3. **Customize content** following the customization guide
4. **Test workflow** with sample data
5. **Publish** when ready

## Customization Guide

Each template includes:
- **README.md**: How to customize this template
- **rules.md**: LLM behavior guidelines to adapt
- **status.json**: Progress tracking structure
- **scripts/**: Automation scripts to modify
- **examples/**: Sample inputs/outputs to update
```

## Workflow Template

### Frontmatter

Every workflow must start with YAML frontmatter:

```yaml
---
description: Brief description of what the workflow does
---
```

### Standard Sections

```markdown
# Workflow Name

Brief one-sentence description of the workflow's purpose.

## Overview

More detailed explanation of what the workflow accomplishes, its goals, and its place in the broader system.

## Prerequisites

List of requirements:
- Tools needed
- Access requirements  
- Knowledge prerequisites
- Dependencies

## Workflow Steps

### Step 1: Step Name
Description of what this step accomplishes.

#### Sub-step 1.1
Detailed instructions or prompts.

#### Sub-step 1.2  
Additional details or examples.

## Integration

How this workflow connects with other workflows and systems.

## Advanced Workflow Patterns

### Hybrid LLM-Script Workflows

For sophisticated workflows that combine LLM capabilities with automation scripts, see the comprehensive guide: [Building LLM-Script Hybrid Workflows for IDE Development](hybrid-workflows-guide.md)

This guide covers:
- **Core Philosophy**: Right tool for each job (LLM vs Scripts vs Human)
- **Practical Patterns**: 4 proven workflow architectures
- **Anti-Patterns**: What to avoid and why
- **Production Practices**: Observability, reversibility, incremental progress
- **Scaling Considerations**: From prototype to production workflows
- **Cost Management**: Optimizing LLM usage and tracking expenses

### Key Patterns from Advanced Guide

#### Pattern 1: Script Discovery → LLM Processing → Script Application
**When to use:** Processing many items that require contextual decisions
**Example:** Refactoring deprecated API calls across large codebase

#### Pattern 2: LLM Strategy → Script Execution → LLM Validation  
**When to use:** Complex strategy with mechanical execution
**Example:** Database migration with business logic constraints

#### Pattern 3: Continuous LLM-Script Collaboration
**When to use:** Iterative refinement with frequent decision points
**Example:** Progressive code quality improvement

#### Pattern 4: Parallel Processing with LLM Aggregation
**When to use:** Many independent tasks requiring synthesis
**Example:** Codebase documentation generation

### Implementation Best Practices

#### Design for Observability
Always make state visible with structured `status.json` files that track:
- Current workflow step
- Steps completed
- Metrics and progress
- Pending human review items

#### Design for Reversibility
Every script operation should be:
- Atomic (all-or-nothing execution)
- Backed up before changes
- Recorded in a rollback manifest
- Easily reversible

#### Design for Incremental Progress
Break work into checkpoints that:
- Save expensive LLM results
- Enable resume from any point
- Allow modification of later steps
- Create audit trails

#### Clear Handoffs Between Components
Define explicit interfaces for:
- Script outputs (structured data)
- LLM inputs (context + constraints)  
- LLM outputs (validated schemas)
- Human approval points

## Troubleshooting

Common issues and solutions.

## Quick Reference

Summary table or checklist for quick access.
```

## Creation Process

### 1. Planning Phase

#### Define Purpose
- What problem does this workflow solve?
- Who is the target audience?
- What are the success criteria?

#### Identify Type
- Is this hybrid, LLM-only, or script-only?
- Does it need supporting scripts or files?
- What automation level is required?

#### Outline Steps
- Break down the process into logical steps
- Identify decision points and branches
- Plan validation and quality checks
- Determine which steps need LLM vs scripts

### 2. Structure Creation

#### Create Workflow Directory

**PowerShell:**
```powershell
# Create new workflow directory
New-Item -ItemType Directory -Path "docs/workflows/workflow-name"
Set-Location "docs/workflows/workflow-name"

# Create required files and directories
New-Item -ItemType File -Path "start.md"
New-Item -ItemType File -Path "workflow-name.md"  # Main workflow document - MUST match directory name
New-Item -ItemType File -Path "README.md"          # Workflow overview and quick start
New-Item -ItemType File -Path "rules.md"           # LLM behavior rules and constraints
New-Item -ItemType File -Path "status.json"
New-Item -ItemType Directory -Path "scripts/pwsh", "scripts/bash", "templates", "examples"
```

**Bash:**
```bash
# Create new workflow directory
mkdir -p docs/workflows/workflow-name
cd docs/workflows/workflow-name

# Create required files and directories
touch start.md
touch workflow-name.md  # Main workflow document - MUST match directory name
touch README.md          # Workflow overview and quick start
touch rules.md           # LLM behavior rules and constraints
touch status.json
mkdir -p scripts/pwsh scripts/bash templates examples
```

#### Add Frontmatter
```yaml
---
description: Clear, concise description
---
```

#### Create Status File
```json
{
  "workflow": "workflow-name",
  "created": "YYYY-MM-DDTHH:MM:SS",
  "last_updated": "YYYY-MM-DDTHH:MM:SS",
  "status": "in_progress",
  "steps_completed": [],
  "current_step": null
}
```

#### Create Basic Structure
Copy the standard template and adapt it to your needs.

#### Create README.md
```markdown
# Workflow Name

Brief one-sentence description of the workflow's purpose.

## Quick Start

1. **Prerequisites**: List what users need before starting
2. **Run the workflow**: How to execute (e.g., `./start.md`)
3. **Expected outcome**: What users will get

## Key Features

- Feature 1: What makes this workflow special
- Feature 2: How it solves specific problems
- Feature 3: Integration points with other workflows

## Usage Examples

### Basic Usage
```bash
# Example command or steps
```

### Advanced Usage
```bash
# Advanced example with options
```

## Troubleshooting

Common issues and quick fixes.

## Related Workflows

- **/related-workflow**: How it connects
- **/another-workflow**: Dependencies
```

#### Create rules.md
```markdown
# LLM Behavior Rules for [Workflow Name]

## Purpose
This document defines how the LLM should behave when assisting with this workflow.

## Core Principles

### 1. [Principle Name]
- **Rule**: Specific behavior requirement
- **Rationale**: Why this rule exists
- **Example**: How to apply this rule

### 2. [Principle Name]
- **Rule**: Specific behavior requirement
- **Rationale**: Why this rule exists
- **Example**: How to apply this rule

## Response Guidelines

### Tone and Style
- **Tone**: [formal/casual/technical/etc.]
- **Language**: [specific language requirements]
- **Formatting**: [markdown/code block/etc. preferences]

### Content Requirements
- **Must include**: [required elements in responses]
- **Must avoid**: [things to never include]
- **Preferred structure**: [how to organize responses]

## Decision Making

### When to Ask for Clarification
- [Condition 1]: When [specific situation occurs
- [Condition 2]: When [specific situation occurs

### When to Make Assumptions
- [Assumption 1]: Safe to assume [what]
- [Assumption 2]: Safe to assume [what]

## Error Handling

### Types of Errors
- **Input errors**: How to handle invalid inputs
- **Process errors**: How to handle workflow failures
- **Output errors**: How to handle generation issues

### Recovery Strategies
- **Strategy 1**: [description of recovery approach]
- **Strategy 2**: [description of recovery approach]

## Quality Standards

### Validation Criteria
- **Accuracy**: [specific accuracy requirements]
- **Completeness**: [what makes a response complete]
- **Consistency**: [how to maintain consistency]

### Quality Checks
- [ ] Check 1: [specific quality check]
- [ ] Check 2: [specific quality check]
- [ ] Check 3: [specific quality check]

## Constraints and Limitations

### Technical Constraints
- **File size limits**: [any file size restrictions]
- **Processing limits**: [any processing restrictions]
- **API constraints**: [any API usage limits]

### Content Constraints
- **Scope**: [what the workflow should not handle]
- **Boundaries**: [where the workflow should stop]
- **Dependencies**: [what external systems it relies on]

## Integration Rules

### Input Requirements
- **Format**: [required input format]
- **Validation**: [how to validate inputs]
- **Error handling**: [how to handle invalid inputs]

### Output Requirements
- **Format**: [required output format]
- **Validation**: [how to validate outputs]
- **Error handling**: [how to handle output failures]

## Examples

### Good Response Example
```
[Example of a good LLM response following these rules]
```

### Bad Response Example
```
[Example of what to avoid]
```

## Feedback Loop

### How to Improve
- **Success metrics**: [how to measure success]
- **Failure indicators**: [how to identify problems]
- **Improvement process**: [how to incorporate feedback]

---

*This rules file should be updated based on user feedback and workflow evolution.*
```

### 3. Content Development

#### Write Step-by-Step Instructions
- Use clear, actionable language
- Include specific examples
- Provide template prompts for LLM workflows
- Add code snippets for automated workflows

#### Add Validation Steps
- How to verify each step is complete
- Quality check criteria
- Success metrics

#### Include Troubleshooting
- Common problems and solutions
- Debug steps
- When to escalate

### 4. Integration Planning

#### Cross-Reference Other Workflows
```markdown
This workflow integrates with:
- **/related-workflow**: Provides input data
- **/another-workflow**: Consumes output
- **/process-workflow**: Handles validation
```

#### Update Workflow Registry
If this is a slash command workflow, ensure it's discoverable.

### 5. Testing and Refinement

#### Test with Real Scenarios
- Walk through the workflow step by step
- Test with different input types
- Verify integration points

#### Gather Feedback
- Have team members test the workflow
- Collect suggestions for improvement
- Identify unclear instructions

#### Refine and Document
- Update based on feedback
- Add more examples where needed
- Clarify ambiguous steps

## LLM-Guided Workflow Patterns

### Prompt Templates

Provide reusable prompt templates:

```markdown
#### Discovery Prompts
- "Scan [location] and identify [target]"
- "Analyze [content] for [criteria]"

#### Generation Prompts  
- "Generate [output] from [input]"
- "Create [document type] following [standards]"

#### Validation Prompts
- "Validate [content] against [criteria]"
- "Check [output] for [requirements]"
```

### Quality Assurance

Build in validation steps:

```markdown
### LLM Validation
**Prompt Template:**
```
Please validate this [content] for [criteria]:

[paste content]

Check for:
1. [Requirement 1]
2. [Requirement 2] 
3. [Requirement 3]

Report any issues and suggest improvements.
```
```

## Automated Workflow Patterns

### Script Structure

For workflows with automation:

```
docs/workflows/workflow-name/
├── workflow-name.md         # Main documentation (matches directory)
├── README.md                # Workflow overview and quick start
├── rules.md                 # LLM behavior rules and constraints
├── scripts/
│   ├── pwsh/
│   │   ├── scanner.ps1      # Input discovery
│   │   ├── processor.ps1    # Main processing
│   │   ├── validator.ps1    # Quality checks
│   │   └── reporter.ps1     # Output generation
│   └── bash/
│       ├── scanner.sh       # Input discovery
│       ├── processor.sh     # Main processing
│       ├── validator.sh     # Quality checks
│       └── reporter.sh      # Output generation
└── examples/
    ├── input/               # Sample inputs
    └── output/              # Expected outputs
```

### Script Guidelines

- Use clear, descriptive function names
- Include comprehensive error handling
- Provide command-line interfaces
- Support both file and directory operations
- Generate structured output (JSON preferred)
- Follow PowerShell best practices for .ps1 files
- Follow Bash best practices for .sh files

### PowerShell Script Template

```powershell
<#
.SYNOPSIS
    Brief description of what the script does

.DESCRIPTION
    Detailed description of the script's purpose and functionality

.PARAMETER InputPath
    Path to input files or directory

.PARAMETER OutputPath
    Path where output will be saved

.EXAMPLE
    .\script-name.ps1 -InputPath ".\input" -OutputPath ".\output"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$InputPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = ".\output"
)

# Script logic here
try {
    # Main processing
    Write-Host "Processing..."
    
    # Generate output
    $result = @{
        "status" = "success"
        "processed" = 0
        "errors" = @()
    }
    
    # Save as JSON
    $result | ConvertTo-Json -Depth 10 | Out-File -FilePath "$OutputPath\result.json"
    
    Write-Host "Complete!" -ForegroundColor Green
}
catch {
    Write-Error "Error: $_"
    exit 1
}
```

### Bash Script Template

```bash
#!/bin/bash

# Brief description of what the script does
#
# Usage: ./script-name.sh <input-path> <output-path>

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Default values
INPUT_PATH="${1:-}"
OUTPUT_PATH="${2:-./output}"

# Validate inputs
if [ -z "$INPUT_PATH" ]; then
    echo "Error: Input path required"
    echo "Usage: $0 <input-path> [output-path]"
    exit 1
fi

# Main processing
echo "Processing..."

# Generate output
cat > "$OUTPUT_PATH/result.json" << EOF
{
  "status": "success",
  "processed": 0,
  "errors": []
}
EOF

echo "Complete!"
```

## Process Workflow Patterns

### Checklist Format

```markdown
### Pre-Execution Checklist
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

### Execution Steps
1. **Step Name**: Detailed instructions
2. **Step Name**: Detailed instructions
3. **Step Name**: Detailed instructions

### Post-Execution Validation
- [ ] Output meets criteria
- [ ] Documentation updated
- [ ] Stakeholders notified
```

### Decision Trees

```markdown
### Decision Point: [Decision Name]

**If [Condition]:**
- Follow Path A
- Go to Step X

**If [Condition]:**  
- Follow Path B
- Go to Step Y

**If [Condition]:**
- Follow Path C
- Go to Step Z
```

## Naming Conventions

### Workflow Names
- Use kebab-case for file names
- Be descriptive but concise
- Include action words when appropriate
- Examples: `reference-fill`, `selector-debugging`, `opsx-verify` 
- **Main document name must match directory name**: `reference-fill/reference-fill.md` 

### Script Names
- PowerShell: Use kebab-case with `.ps1` extension
  - Examples: `find-files.ps1`, `process-data.ps1`, `validate-output.ps1` 
- Bash: Use kebab-case with `.sh` extension
  - Examples: `find-files.sh`, `process-data.sh`, `validate-output.sh` 

### Step Names
- Use clear, action-oriented language
- Start with verbs
- Be specific about the outcome
- Examples: "Identify Target Files", "Collect HTML Samples", "Validate Compliance"

## File Naming Reference

Here are concrete examples of the naming pattern:

| Workflow Directory | Main Document | Start Document | README | Rules File | Status File | Example Scripts |
|-------------------|---------------|----------------|---------|------------|-------------|-----------------|
| `reference-fill/` | `reference-fill.md` | `start.md` | `README.md` | `rules.md` | `status.json` | `scanner.ps1`, `scanner.sh` |
| `selector-debugging/` | `selector-debugging.md` | `start.md` | `README.md` | `rules.md` | `status.json` | `debugger.ps1`, `debugger.sh` |
| `opsx-verify/` | `opsx-verify.md` | `start.md` | `README.md` | `rules.md` | `status.json` | `validator.ps1`, `validator.sh` |
| `code-review/` | `code-review.md` | `start.md` | `README.md` | `rules.md` | `status.json` | `reviewer.ps1`, `reviewer.sh` |

## Documentation Standards

### Markdown Formatting
- Use proper heading hierarchy (##, ###, ####)
- Include code blocks with language specification
- Use tables for structured information
- Include emojis for visual clarity (✅, ❌, ⚠️, ℹ️)

### Code Examples

**PowerShell:**
```powershell
# Command examples
Get-ChildItem -Path .\src -Recurse -Filter *.js

# Script execution
.\scripts\pwsh\process-files.ps1 -InputPath ".\data" -OutputPath ".\results"
```

**Bash:**
```bash
# Command examples
find ./src -name "*.js" -type f

# Script execution
./scripts/bash/process-files.sh ./data ./results
```

**Prompt examples:**
```
Prompt template here
```

### Links and References
- Link to related workflows
- Reference external documentation
- Include file paths and locations
- Provide contact information for help

## Quality Checklist

Before publishing a workflow, verify:

### Content Quality
- [ ] Clear, concise descriptions
- [ ] Step-by-step instructions
- [ ] Comprehensive examples
- [ ] Troubleshooting section
- [ ] README.md with quick start guide
- [ ] rules.md with LLM behavior guidelines

### Structure Quality  
- [ ] Proper frontmatter
- [ ] Consistent formatting
- [ ] Logical flow
- [ ] Complete sections
- [ ] All required files present

### Integration Quality
- [ ] Cross-references other workflows
- [ ] Updates related documentation
- [ ] Tests integration points
- [ ] Documents dependencies

### Accessibility Quality
- [ ] Available in correct location
- [ ] Proper naming conventions
- [ ] Discoverable by target users
- [ ] Linked from relevant places

### Script Quality
- [ ] Both PowerShell and Bash versions provided (when applicable)
- [ ] Scripts have proper error handling
- [ ] Scripts generate structured output
- [ ] Scripts are tested and working

## Maintenance

### Regular Updates
- Review workflows quarterly
- Update based on system changes
- Incorporate user feedback
- Keep examples current

### Version Control
- Use descriptive commit messages
- Tag major workflow changes
- Document breaking changes
- Maintain backward compatibility when possible

## Examples

### Simple LLM Workflow
```markdown
---
description: Generate documentation from code
---

# Code Documentation Generator

Generates comprehensive documentation from source code using LLM assistance.

## Overview
...

## Workflow Steps

### 1. Code Analysis
**Prompt:**
```
Analyze this code for documentation needs:
[paste code]
```

### 2. Documentation Generation
**Prompt:**
```
Generate documentation following our standards:
[paste analysis]
```
```

### Hybrid Workflow with Scripts
```markdown
---
description: Batch process and validate data files
---

# Data Processing Pipeline

Automated workflow for processing and validating large datasets.

## Overview
...

## Workflow Steps

### 1. Input Discovery

**PowerShell:**
```powershell
.\scripts\pwsh\scanner.ps1 -InputDir ".\data" -Output "discovered.json"
```

**Bash:**
```bash
./scripts/bash/scanner.sh ./data discovered.json
```

### 2. LLM Analysis
**Prompt:**
```
Analyze these discovered files and categorize them:
[paste discovered.json content]
```

### 3. Data Processing

**PowerShell:**
```powershell
.\scripts\pwsh\processor.ps1 -Input "discovered.json" -Output "processed.json"
```

**Bash:**
```bash
./scripts/bash/processor.sh discovered.json processed.json
```

### 4. Validation

**PowerShell:**
```powershell
.\scripts\pwsh\validator.ps1 -Input "processed.json" -Report "validation.json"
```

**Bash:**
```bash
./scripts/bash/validator.sh processed.json validation.json
```
```

## Getting Help

- Review existing workflows for patterns
- Ask team members for feedback
- Test thoroughly before publishing
- Document any assumptions or limitations

---

This guide should help you create effective, maintainable workflows that follow Scorewise conventions and best practices.
