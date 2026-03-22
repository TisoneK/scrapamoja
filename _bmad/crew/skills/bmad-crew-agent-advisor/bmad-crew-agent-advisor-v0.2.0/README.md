# BMAD Crew Advisor v0.2.0

Enhanced session supervisor with automatic context discovery, document verification gates, and intelligent code review escalation paths.

## Version 0.2.0 - Critical Foundation Improvements

This major upgrade addresses the most critical gaps in the original advisor with three foundational improvements:

### 🚀 New Capabilities

**1. Auto-Discovery & Context Loading (IDEA-003)**
- Automatically reads sprint-status.yaml, story files, project-context.md on activation
- Intelligently scans docs/, proposals/, _bmad-output/ for additional context
- Presents three clear options: continue current state, start new session, or something else
- Eliminates manual context loading burden

**2. Document Verification Gate (IDEA-006)**
- Reads and validates ALL Builder outputs before allowing progression
- Never accepts completion claims without reading actual files
- Validates against locked decisions and project context
- Blocks progression until violations are resolved

**3. Code Review Escalation (IDEA-014)**
- Intelligent handling of finding classifications:
  - `patch` → Fix in current review session
  - `defer` → Acknowledge and move on
  - `intent_gap` → Flag for re-planning, ask Coordinator
  - `bad_spec` → Block progression, require story correction
- Provides exact escalation paths for each type

### 📋 Enhanced Features

- **Memory System v0.2.0** - Enhanced with discovery cache and escalation tracking
- **Access Boundaries** - Updated for auto-discovery constraints and verification limits
- **Automated Scripts** - New document-verifier.py for automated validation
- **Quality Assurance** - Comprehensive test suite for all components

## Installation

### Prerequisites
- BMAD Method framework
- Python 3.7+ for script execution
- Existing bmad-crew module structure

### Setup

1. **Backup Existing Advisor**
   ```bash
   cp -r _bmad/crew/skills/bmad-crew-agent-advisor _bmad/crew/skills/bmad-crew-agent-advisor-v0.1.0-backup
   ```

2. **Install v0.2.0**
   ```bash
   cp -r bmad-builder-creations/bmad-crew-agent-advisor-v0.2.0 _bmad/crew/skills/bmad-crew-agent-advisor
   ```

3. **Set Permissions**
   ```bash
   chmod +x _bmad/crew/skills/bmad-crew-agent-advisor/scripts/*.py
   chmod +x _bmad/crew/skills/bmad-crew-agent-advisor/scripts/*.sh
   ```

4. **Run Tests**
   ```bash
   cd _bmad/crew/skills/bmad-crew-agent-advisor
   ./scripts/run-tests.sh
   ```

5. **Update Memory Structure** (if upgrading from v0.1.0)
   ```bash
   # The advisor will automatically migrate memory structure on first activation
   # Existing session-state.md will be preserved
   ```

## Usage

### Session Initialization

The enhanced advisor now automatically discovers context:

```bash
/bmad-crew-agent-advisor
```

**What happens:**
1. Advisor automatically scans for artifacts
2. Presents discovered context with three options
3. Loads approved context automatically
4. Begins monitoring with full context awareness

### Document Verification

All Builder outputs are now automatically verified:

```bash
# After any BMAD command that produces output:
# 1. Advisor reads the actual output file
# 2. Validates against locked decisions and standards
# 3. Blocks progression if issues found
# 4. Provides specific remediation instructions
```

### Code Review Escalation

Code review findings are handled intelligently:

```bash
# During code review:
# 1. Advisor classifies each finding (patch/defer/intent_gap/bad_spec)
# 2. Provides exact escalation path for classification
# 3. Blocks progression for bad_spec findings
# 4. Prevents future issues with pattern tracking
```

## Configuration

### Memory Location
```
{project-root}/_bmad/_memory/bmad-crew-agent-advisor-sidecar/
├── session-state.md          # Current session tracking
├── discovery-cache.md        # Auto-discovery results
├── verification-results.md   # Document verification history
├── escalation-log.md        # Code review escalation tracking
└── access-boundaries.md     # Access control rules
```

### Access Boundaries

**Enhanced Read Access:**
- Auto-discovery of docs/, proposals/, _bmad-output/
- Intelligent file pattern matching
- Respect for .gitignore and project structure

**New Write Access:**
- Discovery cache for performance
- Verification results tracking
- Escalation outcome logging

**Strict Deny Zones:**
- No direct code modification
- No git operations (validation only)
- No cross-role boundary violations

## Scripts

### document-verifier.py
Automated document validation script:

```bash
python3 scripts/document-verifier.py \
  --document-type [story|architecture|prd|epics|code-review|retrospective] \
  --file-path [path/to/document] \
  --locked-decisions [path/to/locked-decisions.md] \
  --project-context [path/to/project-context.md]
```

### run-tests.sh
Comprehensive test suite:

```bash
./scripts/run-tests.sh
```

Tests:
- File structure integrity
- Manifest JSON validation
- Script syntax and functionality
- v0.2.0 feature implementation
- Access boundary compliance

## Migration from v0.1.0

### What's Preserved
- Existing session-state.md format
- Memory structure and location
- Core violation detection logic
- Coordinator instruction style

### What's Enhanced
- Automatic context discovery
- Document verification gates
- Code review escalation paths
- Enhanced memory tracking

### Breaking Changes
- New capabilities added to manifest
- Enhanced session-init.md flow
- Additional memory files created automatically

## Troubleshooting

### Common Issues

**Auto-discovery not finding files:**
- Check file permissions in project directories
- Verify .gitignore isn't excluding needed files
- Ensure project-root is correctly configured

**Document verification failures:**
- Check locked-decisions.md exists and is readable
- Verify project-context.md is available
- Review document-verifier.py error output

**Code review escalation issues:**
- Ensure findings are properly classified
- Check escalation-log.md for pattern tracking
- Verify instruction-generation.md has escalation paths

### Debug Mode

Enable detailed logging:

```markdown
In session-state.md, add:
## Debug Mode
- Enabled: true
- Log Level: verbose
```

### Support

For issues with v0.2.0:
1. Check test suite output: `./scripts/run-tests.sh`
2. Review memory files for error patterns
3. Verify all prerequisites are installed
4. Check BMAD framework compatibility

## Roadmap

### v0.2.1 (High Priority)
- Automated Validation (IDEA-004)
- Workflow Knowledge (IDEA-007)
- Locked Decisions Re-reference (IDEA-012)

### v0.2.2 (Medium Priority)
- Mistakes File Generation (IDEA-001)
- Session-End Detection (IDEA-013)
- Output Format Standards (IDEA-005)

## Contributing

When contributing to v0.2.0:
1. Run the test suite before submitting
2. Follow the established memory structure
3. Maintain access boundary compliance
4. Document new features appropriately

---

**BMAD Crew Advisor v0.2.0** - Enhanced session supervision for reduced cognitive load and improved process compliance.
