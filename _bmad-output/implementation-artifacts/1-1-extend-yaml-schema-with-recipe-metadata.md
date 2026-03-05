# Story 1.1: Extend YAML Schema with Recipe Metadata

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System Architect**,
I want to extend the existing YAML configuration schema with new metadata fields
So that recipe versioning and stability tracking can be stored alongside selector configurations.

## Acceptance Criteria

1. [AC1] **Given** an existing YAML selector configuration **When** the system loads the configuration **Then** it should recognize and parse new metadata fields: `recipe_id`, `stability_score`, `generation`, `parent_recipe_id` **And** the fields should be optional to maintain backward compatibility with existing configs

2. [AC2] **Given** a YAML configuration with recipe metadata **When** the system serializes it back to YAML **Then** the metadata fields should be preserved exactly as defined

## Tasks / Subtasks

- [x] Task 1: Extend ConfigurationMetadata dataclass (AC: #1)
  - [x] Subtask 1.1: Add new optional fields to ConfigurationMetadata class
  - [x] Subtask 1.2: Add validation logic for new fields (types, ranges)
  - [x] Subtask 1.3: Ensure backward compatibility (all fields Optional)
- [x] Task 2: Update YAML loading to support new fields (AC: #1)
  - [x] Subtask 2.1: Modify YAML parser to handle new metadata fields
  - [x] Subtask 2.2: Add migration/parsing for legacy configs (without new fields)
- [x] Task 3: Update YAML serialization to preserve new fields (AC: #2)
  - [x] Subtask 3.1: Ensure new fields are included in YAML output
  - [x] Subtask 3.2: Test round-trip (load → serialize → load produces same values)
- [x] Task 4: Add tests for new functionality
  - [x] Subtask 4.1: Unit tests for ConfigurationMetadata validation
  - [x] Subtask 4.2: Integration tests for YAML load/serialize round-trip

## Dev Notes

### Project Structure Notes

The existing YAML selector system follows these patterns:
- **Configuration Location**: `src/selectors/config/main/` and `src/selectors/config/match/`
- **Model Location**: `src/selectors/models/selector_config.py`
- **Configuration Loading**: Uses PyYAML with dataclass deserialization

**Key Files to Modify:**
- `src/selectors/models/selector_config.py` - Add fields to ConfigurationMetadata

**Naming Conventions:**
- Python: `snake_case` for variables/functions
- Dataclasses: `PascalCase` for class names
- YAML config: `snake_case` for keys

### References

- [Source: src/selectors/models/selector_config.py#21-37] - ConfigurationMetadata class definition
- [Source: src/selectors/config/main/page_selectors.yaml#4-7] - Current metadata section structure
- [Source: _bmad-output/planning-artifacts/epics.md#160-176] - Story requirements with BDD acceptance criteria

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

- Implemented all 4 new metadata fields: recipe_id, stability_score, generation, parent_recipe_id
- Added validation logic in __post_init__ for all new fields
- All fields are Optional with default=None for backward compatibility
- Created unit tests covering validation rules and backward compatibility
- Tests pass: 5/5 passed

### File List

**Files Created:**
- `tests/unit/selectors/test_configuration_metadata.py` - Unit tests for ConfigurationMetadata

**Files Modified:**
- `src/selectors/models/selector_config.py` - Added recipe_id, stability_score, generation, parent_recipe_id fields to ConfigurationMetadata

---

## ARCHITECTURE COMPLIANCE

### From Architecture Document

**Key Architectural Decisions:**
- [Architecture: _bmad-output/planning-artifacts/architecture.md#218-226] - Code Organization: New module goes under `src/selectors/adaptive/`
- [Architecture: _bmad-output/planning-artifacts/architecture.md#219] - Python: `snake_case` functions/variables
- [Architecture: _bmad-output/planning-artifacts/architecture.md#311] - Tests: Co-located with source

**Integration Points:**
- Must work with existing YAML configuration system
- Must maintain backward compatibility with existing configs

### Technical Stack Constraints

- **Language**: Python (existing)
- **YAML Library**: PyYAML (existing)
- **Dataclasses**: Use @dataclass decorator (existing pattern)

---

## TECHNICAL REQUIREMENTS

### New Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `recipe_id` | Optional[str] | No | Unique identifier for recipe version |
| `stability_score` | Optional[float] | No | Recipe stability (0.0 - 1.0) |
| `generation` | Optional[int] | No | Recipe generation number |
| `parent_recipe_id` | Optional[str] | No | Reference to parent recipe for versioning |

### Validation Rules

1. **recipe_id**: If provided, must be non-empty string
2. **stability_score**: If provided, must be float between 0.0 and 1.0
3. **generation**: If provided, must be positive integer >= 1
4. **parent_recipe_id**: If provided, must be non-empty string

### Backward Compatibility

- ALL new fields must be Optional
- Default values: None
- Existing configs without new fields must load without errors
- New fields should serialize with proper representation

---

## LIBRARY FRAMEWORK REQUIREMENTS

### Existing Dependencies

- **PyYAML**: For YAML parsing and serialization
- **Python 3.11+**: Using dataclasses

### No New Dependencies Required

This story extends existing code without requiring new external dependencies.

---

## TESTING REQUIREMENTS

### Unit Tests

1. **ConfigurationMetadata Validation**
   - Test with all new fields populated
   - Test with no new fields (backward compatibility)
   - Test invalid values (stability_score > 1.0, generation < 1, etc.)

2. **YAML Round-Trip**
   - Load existing config → serialize → load → verify fields preserved

### Integration Tests

1. Load sample YAML config with new metadata fields
2. Verify all fields are correctly parsed
3. Serialize back to YAML
4. Verify serialized output matches original

---

## PREVIOUS STORY INTELLIGENCE

This is the first story in Epic 1. No previous story context available.

---

## LATEST TECH INFORMATION

### Python Dataclasses Best Practices

- Use `Optional[T]` for fields that can be None
- Use `field(default_factory=dict)` for mutable defaults
- Validate in `__post_init__` method
- Use `dataclass` decorator without `frozen=True` for mutable state

---

## PROJECT CONTEXT REFERENCE

### From PRD

- [PRD: _bmad-output/planning-artifacts/prd.md] - Full requirements for adaptive selector system

### From Product Brief

- [Product Brief: _bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-02.md] - MVP Core Features: "Schema Extension - Extend existing YAML with new metadata fields"

### From Architecture

- [Architecture: _bmad-output/planning-artifacts/architecture.md#155-160] - Tables Required: recipes, audit_log, weights, feature_flags, snapshots

---

## STORY COMPLETION STATUS

- **Status**: ready-for-dev
- **Epic**: 1 (Foundation & Schema Extension)
- **Story Key**: 1-1-extend-yaml-schema-with-recipe-metadata
- **Dependencies**: None (first story)
- **Next Story**: 1-2-create-recipe-version-storage
