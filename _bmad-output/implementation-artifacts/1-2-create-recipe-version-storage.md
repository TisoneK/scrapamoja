# Story 1.2: Create Recipe Version Storage

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to store recipe versions in a database
So that I can track selector stability over time and support inheritance.

## Acceptance Criteria

1. [AC1] **Given** a recipe configuration with metadata **When** it is first created **Then** it should be stored in the recipes table with all required fields **And** the initial version number should be 1

2. [AC2] **Given** an existing recipe **When** selectors are updated **Then** a new version should be created with incremented version number **And** the parent_version_id should reference the previous version

## Tasks / Subtasks

- [x] Task 1: Set up SQLite database and SQLAlchemy models (AC: #1)
  - [x] Subtask 1.1: Create database connection configuration
  - [x] Subtask 1.2: Define Recipe SQLAlchemy model with all required fields
  - [x] Subtask 1.3: Create database tables
- [x] Task 2: Implement recipe version storage (AC: #1)
  - [x] Subtask 2.1: Create repository class for recipe CRUD operations
  - [x] Subtask 2.2: Implement initial recipe creation with version 1
  - [x] Subtask 2.3: Add method to retrieve recipes by ID
- [x] Task 3: Implement version inheritance (AC: #2)
  - [x] Subtask 3.1: Create new version method that increments version number
  - [x] Subtask 3.2: Implement parent_version_id reference
  - [x] Subtask 3.3: Add method to get version history for a recipe

## Dev Notes

### Project Structure Notes

The recipe versioning system extends the YAML configuration with database storage:
- **Module Location**: `src/selectors/adaptive/` (new module per architecture)
- **Database Location**: `src/selectors/adaptive/db/`
- **Model Location**: `src/selectors/adaptive/db/models/`
- **Repository Location**: `src/selectors/adaptive/db/repositories/`

**Key Files to Create:**
- `src/selectors/adaptive/db/__init__.py` - Database package init
- `src/selectors/adaptive/db/models/__init__.py` - Models package init
- `src/selectors/adaptive/db/models/recipe.py` - Recipe SQLAlchemy model
- `src/selectors/adaptive/db/repositories/__init__.py` - Repositories package init
- `src/selectors/adaptive/db/repositories/recipe_repository.py` - Recipe CRUD repository

**Naming Conventions:**
- Python: `snake_case` for variables/functions
- SQLAlchemy Models: `PascalCase` for class names
- Database Tables: `snake_case` plural (e.g., `recipes`)
- Database Columns: `snake_case` (e.g., `created_at`, `parent_recipe_id`)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#177-194] - Story requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#155-160] - Tables Required: recipes, audit_log, weights, feature_flags, snapshots
- [Source: _bmad-output/planning-artifacts/architecture.md#218-227] - Code Organization: New module under `src/selectors/adaptive/`
- [Source: _bmad-output/implementation-artifacts/1-1-extend-yaml-schema-with-recipe-metadata.md] - Previous story (1.1) - extends YAML schema with metadata fields

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

**Implementation Summary:**
- Created SQLAlchemy 2.0 Recipe model with all required fields (id, recipe_id, version, selectors, parent_recipe_id, generation, stability_score, created_at, updated_at)
- Implemented RecipeRepository class with full CRUD operations: create_recipe(), create_new_version(), get_by_id(), get_version_history(), get_latest_version(), update_stability_score(), delete_recipe(), list_all_recipes()
- Added SQLAlchemy 2.0 as project dependency in pyproject.toml
- Created comprehensive unit tests for both Recipe model and RecipeRepository (20 tests total, all passing)
- Version inheritance implemented via parent_recipe_id field and automatic version incrementing
- Unique constraint on (recipe_id, version) combination ensures data integrity

### File List

**Files Created:**
- `src/selectors/adaptive/db/__init__.py` - Database package init
- `src/selectors/adaptive/db/models/__init__.py` - Models package init
- `src/selectors/adaptive/db/models/recipe.py` - Recipe SQLAlchemy model
- `src/selectors/adaptive/db/repositories/__init__.py` - Repositories package init
- `src/selectors/adaptive/db/repositories/recipe_repository.py` - Recipe CRUD repository
- `tests/unit/selectors/adaptive/__init__.py` - Test package init
- `tests/unit/selectors/adaptive/db/__init__.py` - Test package init
- `tests/unit/selectors/adaptive/db/test_recipe_model.py` - Recipe model tests
- `tests/unit/selectors/adaptive/db/test_recipe_repository.py` - Repository tests

**Files Modified:**
- `pyproject.toml` - Added SQLAlchemy 2.0+ dependency

---

## ARCHITECTURE COMPLIANCE

### From Architecture Document

**Key Architectural Decisions:**
- [Architecture: _bmad-output/planning-artifacts/architecture.md#155-160] - Tables Required: recipes table with fields for versioning
- [Architecture: _bmad-output/planning-artifacts/architecture.md#218-227] - Code Organization: New module under `src/selectors/adaptive/`
- [Architecture: _bmad-output/planning-artifacts/architecture.md#151-153] - Database: SQLite (MVP), ORM: SQLAlchemy 2.0

**Integration Points:**
- Must integrate with Story 1.1's YAML metadata fields (recipe_id, stability_score, generation, parent_recipe_id)
- Must work with existing selector configuration loading system

### Technical Stack Constraints

- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0 with async support
- **Database**: SQLite (MVP)
- **Migration**: Alembic (industry standard)

---

## TECHNICAL REQUIREMENTS

### Recipe Database Model

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer | Yes | Primary key |
| `recipe_id` | String | Yes | Unique identifier from YAML config |
| `version` | Integer | Yes | Version number (starts at 1) |
| `parent_recipe_id` | String | No | Reference to parent recipe for versioning |
| `generation` | Integer | No | Recipe generation number |
| `stability_score` | Float | No | Recipe stability (0.0 - 1.0) |
| `selectors` | JSON | Yes | Selector configuration data |
| `created_at` | DateTime | Yes | Creation timestamp |
| `updated_at` | DateTime | Yes | Last update timestamp |

### Validation Rules

1. **recipe_id**: Must be non-empty string, unique across all versions
2. **version**: Must be positive integer >= 1
3. **parent_recipe_id**: If provided, must reference existing recipe
4. **stability_score**: If provided, must be float between 0.0 and 1.0

### Database Constraints

- Unique constraint on (recipe_id, version) combination
- Foreign key relationship for parent_recipe_id self-referencing

---

## LIBRARY FRAMEWORK REQUIREMENTS

### Required Dependencies

- **SQLAlchemy 2.0+**: For ORM with async support
- **Alembic**: For database migrations (future)

### No New Dependencies Required

This story extends existing code using established Python libraries.

---

## TESTING REQUIREMENTS

### Unit Tests

1. **Recipe Model Tests**
   - Test model creation with all required fields
   - Test validation rules for each field
   - Test unique constraints

2. **Repository Tests**
   - Test create new recipe (version 1)
   - Test create new version from existing recipe
   - Test retrieve recipe by ID
   - Test retrieve version history

### Integration Tests

1. Create recipe with YAML metadata from Story 1.1
2. Verify stored correctly in database
3. Create new version and verify parent reference
4. Verify version history is correct

---

## PREVIOUS STORY INTELLIGENCE

### From Story 1.1 (1-1-extend-yaml-schema-with-recipe-metadata)

**Key Learnings:**
- ConfigurationMetadata extended with new fields: recipe_id, stability_score, generation, parent_recipe_id
- All new fields are Optional for backward compatibility
- Located in `src/selectors/models/selector_config.py`

**Files Modified in Previous Story:**
- `src/selectors/models/selector_config.py` - Added new metadata fields

**This Story Builds On:**
- Story 1.1's metadata fields are now stored in the database
- The recipe_id, stability_score, generation, parent_recipe_id from YAML become database columns

---

## LATEST TECH INFORMATION

### SQLAlchemy 2.0 Best Practices

- Use `Mapped[]` type annotations for columns
- Use `mapped_column()` for column definitions
- Use `dataclass` decorator with SQLAlchemy models
- Async support via `AsyncSession`

### SQLite Considerations

- Use `check_same_thread=False` for cross-thread access
- Store JSON as TEXT with JSON serialization
- Use Alembic for future migrations

---

## PROJECT CONTEXT REFERENCE

### From PRD

- [PRD: _bmad-output/planning-artifacts/prd.md] - Full requirements for adaptive selector system

### From Architecture

- [Architecture: _bmad-output/planning-artifacts/architecture.md#155-160] - Tables Required: recipes, audit_log, weights, feature_flags, snapshots
- [Architecture: _bmad-output/planning-artifacts/architecture.md#151-153] - Database: SQLite (MVP), PostgreSQL (production), ORM: SQLAlchemy 2.0

### From Epic 1

- [Epic 1: _bmad-output/planning-artifacts/epics.md#156-212] - Foundation & Schema Extension
- Story 1.1: Extend YAML Schema with Recipe Metadata
- **Story 1.2**: Create Recipe Version Storage (current)
- Story 1.3: Implement Recipe Stability Scoring (next)

---

## STORY COMPLETION STATUS

- **Status**: done
- **Epic**: 1 (Foundation & Schema Extension)
- **Story Key**: 1-2-create-recipe-version-storage
- **Dependencies**: Story 1.1 (complete - extends YAML metadata to database)
- **Next Story**: 1-3-implement-recipe-stability-scoring