## ADDED Requirements

### Requirement: Hybrid flow pattern support
The template SHALL support hybrid flow patterns combining single flow.py with flows/ subfolder for different complexity levels.

#### Scenario: Hybrid pattern template generation
- **WHEN** developer selects "standard" complexity during site setup
- **THEN** template creates both flow.py and flows/ subfolder
- **AND** flow.py contains basic navigation flows
- **AND** flows/ contains specialized flows for complex operations

#### Scenario: Basic navigation in flow.py
- **WHEN** implementing simple navigation patterns
- **THEN** flow.py SHALL contain home page navigation and basic menu interactions
- **AND** SHALL handle straightforward page transitions without complex logic

#### Scenario: Specialized flows in flows/ subfolder
- **WHEN** implementing complex extraction or filtering logic
- **THEN** specialized flows SHALL be placed in flows/ subfolder
- **AND** SHALL handle complex operations like pagination, search, or data extraction

### Requirement: Pattern selection guidance
The template SHALL provide clear guidance on when to use hybrid vs other patterns.

#### Scenario: Pattern selection documentation
- **WHEN** developer reads template documentation
- **THEN** documentation SHALL clearly explain hybrid pattern use cases
- **AND** SHALL provide examples of sites suited for hybrid approach (GitHub, Wikipedia)

#### Scenario: Complexity assessment for hybrid pattern
- **WHEN** developer runs site setup complexity assessment
- **THEN** system SHALL recommend hybrid pattern for sites with moderate complexity
- **AND** SHALL provide rationale based on site characteristics

### Requirement: Flow coordination between patterns
The template SHALL support proper coordination between flow.py and flows/ subfolder flows.

#### Scenario: Flow import and registration
- **WHEN** system loads flows from hybrid pattern site
- **THEN** both flow.py and flows/ subfolder flows SHALL be properly registered
- **AND** flow names SHALL be unique across both locations

#### Scenario: Flow execution priority
- **WHEN** multiple flows can handle the same navigation pattern
- **THEN** flows from flows/ subfolder SHALL take priority over flow.py flows
- **AND** system SHALL log flow selection for debugging
