## Why

The current flat selector structure with 6 YAML files cannot handle the complex multi-layer navigation requirements of the flashscore workflow. The workflow document explicitly requires tab-scoped selectors, context-dependent selectors for tertiary navigation, and different selectors for each tab context, which the current structure cannot accommodate.

## What Changes

- **BREAKING**: Replace flat YAML selector structure with hierarchical folder organization
- Create primary subfolders for navigation contexts (authentication/, navigation/, extraction/, filtering/)
- Create secondary subfolders within extraction/ for different data types (match_list/, match_summary/, match_h2h/, match_odds/, match_stats/)
- Create tertiary subfolders within match_stats/ for sub-tab contexts (inc_ot/, ft/, q1/, etc.)
- Implement context-aware selector loading system that can handle different DOM states
- Add selector validation for hierarchical structure compliance

## Capabilities

### New Capabilities
- `hierarchical-selector-organization`: Multi-level folder structure for organizing selectors by navigation context and data extraction context
- `context-aware-selector-loading`: Dynamic selector loading based on current navigation state and tab context
- `tab-scoped-selectors`: Tab-specific selector sets that activate based on current UI context
- `navigation-context-management`: System to track and manage different navigation states and their corresponding selector requirements

### Modified Capabilities
- Leave empty - no existing capability requirements are changing, this is entirely new functionality

## Impact

- **Code**: Requires refactoring of selector loading and management system
- **Configuration**: Migration from flat YAML files to hierarchical folder structure
- **API**: New selector context management APIs
- **Testing**: New test cases for hierarchical selector loading and context switching
- **Documentation**: Updated selector organization documentation and examples
