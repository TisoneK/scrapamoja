# Reference Fill Workflow

Automated workflow for filling reference files in `docs/references/` using templates and LLM guidance.

## Purpose

This workflow helps populate reference files with HTML samples, metadata, and documentation following established templates and conventions.

## Quick Start

1. **Discovery Mode**: Find empty or incomplete reference files
2. **Fill Mode**: Generate content using templates and LLM guidance
3. **Validation Mode**: Check compliance with template standards
4. **Status Mode**: View current progress and metrics

## Algorithm

```
START → Assessment → Mode Selection → Execute Mode → Validate → Report → (Loop)
```

### Mode Flow

```
Discovery ──► Fill ──► Validate ──► Status
    │                              │
    └──────────── (loop) ──────────┘
```

### Discovery Mode
1. Run scanner.ps1
2. Analyze scan_results.json
3. Categorize by match state & tab level
4. Present prioritized list

### Fill Mode
1. Select target file
2. Guide HTML collection from Flashscore
3. Process HTML (extract, format, document)
4. Generate complete reference file
5. Validate & save

### Validation Mode
1. Run validator.ps1
2. Check YAML frontmatter & HTML syntax
3. Auto-fix simple issues
4. Report complex issues

### Status Mode
1. Load status.json
2. Calculate completion %
3. Generate progress report

## Key Features

- **Template-Based**: Uses established reference file templates
- **LLM-Guided**: AI assistance for content generation and validation
- **Automated Scripts**: PowerShell and Bash for file operations
- **Status Tracking**: Real-time progress monitoring
- **Quality Assurance**: Built-in validation and error checking

## Prerequisites

- **LLM Assistant**: For content generation and analysis
- **File Access**: Read/write permissions to `docs/references/`
- **Templates**: Access to reference file templates
- **Configuration**: Rules and constraints defined in `rules.md`

## Workflow Structure

```
reference-fill/
├── start.md              # Entry point with mode selection
├── reference-fill.md     # Main workflow documentation
├── README.md             # This overview file
├── rules.md              # LLM behavior rules
├── status.json           # Progress tracking
├── scripts/              # Automation scripts
├── templates/            # Reference file templates
└── examples/             # Sample outputs
```

## Usage Examples

### Basic Discovery
```bash
# Find incomplete reference files
./scripts/bash/scanner.sh docs/references/flashscore/
```

### Content Generation
```bash
# Generate content for specific file
./scripts/bash/generator.sh --template flashscore --target docs/references/flashscore/example.html
```

### Validation
```bash
# Validate reference file compliance
./scripts/bash/validator.sh docs/references/flashscore/
```

## How to Trigger

### Method 1: Via Main Workflows Menu (Recommended)
1. Load `docs/workflows/workflows.start.md`
2. Select **Reference Fill Workflow** from the menu
3. This triggers `reference-fill/start.md` which guides you through the workflow

### Method 2: Direct Start
1. Load `docs/workflows/reference-fill/start.md` directly
2. The workflow will guide you through Discovery/Fill/Validate/Status modes

### How the LLM Executes
The LLM collects input step-by-step (forms) from the user, then:
- Runs scripts with combined data, OR
- Updates files using the collected data

Example flow:
```
LLM: "Which reference file would you like to fill?"
User: [selects file]
LLM: "Navigate to Flashscore → Copy HTML → Paste here"
User: [pastes HTML]
LLM: [processes HTML] → [generates file] → [saves to target]
```

## Integration

This workflow integrates with:
- **Reference Templates**: Standard templates for different reference types
- **Validation Scripts**: Quality checking and compliance verification
- **Documentation**: Updates to broader documentation system

## Getting Help

- **Main Guide**: [reference-fill.md](reference-fill.md)
- **LLM Rules**: [rules.md](rules.md)
- **Status**: Check [status.json](status.json) for current progress
- **Templates**: See `templates/` directory for available templates

---

*This workflow helps maintain consistent, high-quality reference documentation across the project.*
