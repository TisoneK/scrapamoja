## ADDED Requirements

### Requirement: Complexity-based template generation
The setup script SHALL support complexity-based template generation with simple, standard, and complex options.

#### Scenario: Complexity assessment during setup
- **WHEN** developer runs new site creation command
- **THEN** system SHALL prompt for complexity level (simple/standard/complex)
- **AND** SHALL provide descriptions and examples for each complexity level

#### Scenario: Simple complexity template
- **WHEN** developer selects "simple" complexity
- **THEN** system SHALL generate template with single flow.py file
- **AND** SHALL include basic navigation and extraction examples

#### Scenario: Standard complexity template
- **WHEN** developer selects "standard" complexity
- **THEN** system SHALL generate template with hybrid pattern (flow.py + flows/)
- **AND** SHALL include specialized flows for common operations

#### Scenario: Complex complexity template
- **WHEN** developer selects "complex" complexity
- **THEN** system SHALL generate template with multi-level flow organization
- **AND** SHALL include domain-specific subfolders (navigation/, extraction/, filtering/, authentication/)

### Requirement: Automated complexity recommendation
The setup script SHALL provide automated complexity recommendations based on site characteristics.

#### Scenario: Site characteristic assessment
- **WHEN** developer provides site URL or description
- **THEN** system SHALL analyze site characteristics (SPA, dynamic content, authentication)
- **AND** SHALL recommend appropriate complexity level with rationale

#### Scenario: Complexity recommendation override
- **WHEN** system recommends a complexity level
- **THEN** developer SHALL be able to override the recommendation
- **AND** system SHALL warn about potential under/over-engineering risks

### Requirement: Template customization options
The setup script SHALL allow customization of generated templates beyond basic complexity levels.

#### Scenario: Custom flow domain selection
- **WHEN** generating complex template
- **THEN** developer SHALL be able to select which flow domains to include
- **AND** system SHALL generate template only with selected domains

#### Scenario: Example flow selection
- **WHEN** generating template
- **THEN** developer SHALL be able to choose which example flows to include
- **AND** system SHALL generate template with selected examples only
