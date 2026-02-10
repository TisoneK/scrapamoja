# tab-scoped-selectors Specification

## Purpose
TBD - created by archiving change flashscore-hierarchical-selectors. Update Purpose after archive.
## Requirements
### Requirement: Tab-specific selector sets
The system SHALL maintain separate selector sets for each tab context (SUMMARY, H2H, ODDS, STATS).

#### Scenario: SUMMARY tab selectors
- **WHEN** user views the SUMMARY tab
- **THEN** system loads and applies selectors specific to summary data extraction

#### Scenario: H2H tab selectors
- **WHEN** user views the H2H tab
- **THEN** system loads and applies selectors specific to head-to-head data extraction

#### Scenario: ODDS tab selectors
- **WHEN** user views the ODDS tab
- **THEN** system loads and applies selectors specific to odds data extraction

#### Scenario: STATS tab selectors
- **WHEN** user views the STATS tab
- **THEN** system loads and applies selectors specific to statistics data extraction

### Requirement: Tab context switching
The system SHALL handle seamless switching between tab contexts and their respective selector sets.

#### Scenario: Tab switching detection
- **WHEN** user switches between tabs
- **THEN** system detects tab change and activates appropriate selector set

#### Scenario: Selector set deactivation
- **WHEN** leaving a tab context
- **THEN** system deactivates selectors from the previous tab context

### Requirement: Sub-tab selector scoping
The system SHALL handle selector scoping for sub-tabs within the STATS tab.

#### Scenario: STATS sub-tab selectors
- **WHEN** user navigates to STATS sub-tabs (inc_ot, ft, q1, q2, q3, q4)
- **THEN** system loads selectors specific to the active sub-tab context

#### Scenario: Sub-tab context isolation
- **WHEN** switching between STATS sub-tabs
- **THEN** system isolates selector contexts to prevent cross-contamination

