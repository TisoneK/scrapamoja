## Why

The current site template only supports basic flow organization patterns, failing to reflect the sophisticated architectural patterns needed for complex modern web applications like Flashscore. This creates a gap between the template's guidance and real-world implementation needs, leading to under-engineered solutions that don't scale properly for SPA sites with complex navigation, filtering, and extraction requirements.

## What Changes

- **BREAKING**: Update template directory structure to include advanced flow organization patterns
- Add hybrid flow patterns (flow.py + flows/ subfolder combination)
- Introduce domain-specific flow subfolders (navigation/, extraction/, filtering/, authentication/)
- Update documentation with architectural decision guidance for pattern selection
- Enhance setup script to support complexity-based template generation
- Add real-world examples from Flashscore, GitHub, and Wikipedia implementations

## Capabilities

### New Capabilities
- `advanced-flow-architecture`: Support for multi-level flow organization with domain-specific subfolders
- `hybrid-flow-patterns`: Combined approach using both single flow.py and flows/ folder for different complexity levels
- `template-complexity-selection`: Setup script enhancement to generate templates based on site complexity (simple/standard/complex)
- `flow-domain-separation`: Organized flow structure separating navigation, extraction, filtering, and authentication concerns

### Modified Capabilities
- Leave empty - no existing capability requirements are changing, only adding new architectural patterns

## Impact

- **Template Structure**: The _template directory will be reorganized to include all four architectural patterns
- **Documentation**: README.md will be significantly expanded with pattern selection guidance
- **Setup Process**: New site creation will include complexity assessment and appropriate pattern selection
- **Developer Experience**: Clear guidance on when to use each pattern based on site complexity analysis
- **Code Generation**: Template-based site creation will generate appropriate flow structures automatically
