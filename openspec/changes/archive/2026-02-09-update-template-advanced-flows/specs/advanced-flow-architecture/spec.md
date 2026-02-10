## ADDED Requirements

### Requirement: Template supports multi-level flow organization
The site template SHALL support multi-level flow organization with domain-specific subfolders for complex web applications.

#### Scenario: Complex site template generation
- **WHEN** developer selects "complex" complexity during site setup
- **THEN** template creates flows/ with navigation/, extraction/, filtering/, and authentication/ subfolders
- **AND** each subfolder contains __init__.py and example flow files

#### Scenario: Subfolder flow discovery
- **WHEN** scraper loads flows from a complex site structure
- **THEN** system SHALL discover and register flows from all subfolders recursively
- **AND** flows SHALL be namespaced by their domain (e.g., navigation.match_nav)

### Requirement: Domain-specific flow separation
The template SHALL organize flows into four standard domains: navigation, extraction, filtering, and authentication.

#### Scenario: Navigation flows organization
- **WHEN** creating navigation-related flows
- **THEN** flows SHALL be placed in flows/navigation/ subfolder
- **AND** SHALL handle page navigation, tab switching, and menu interactions

#### Scenario: Extraction flows organization
- **WHEN** creating data extraction flows
- **THEN** flows SHALL be placed in flows/extraction/ subfolder
- **AND** SHALL handle data parsing, element extraction, and content processing

#### Scenario: Filtering flows organization
- **WHEN** creating filtering logic flows
- **THEN** flows SHALL be placed in flows/filtering/ subfolder
- **AND** SHALL handle date filters, sport filters, competition filters

#### Scenario: Authentication flows organization
- **WHEN** creating authentication flows
- **THEN** flows SHALL be placed in flows/authentication/ subfolder
- **AND** SHALL handle login, logout, and session management

### Requirement: Hierarchical flow registration
The flow registry SHALL support hierarchical flow organization with proper namespacing.

#### Scenario: Flow registration from subfolders
- **WHEN** system scans flows/ directory
- **THEN** flows SHALL be registered with their full namespace path
- **AND** flow names SHALL reflect their domain and purpose (e.g., filtering.date_filter)

#### Scenario: Flow discovery and import
- **WHEN** importing flows from a complex site
- **THEN** system SHALL automatically discover flows in all subdirectories
- **AND** SHALL maintain proper Python package structure with __init__.py files
