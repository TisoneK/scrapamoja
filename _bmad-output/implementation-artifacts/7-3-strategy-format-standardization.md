# Story 7.3: Strategy Format Standardization

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **scraper system**,
I want **to convert Flashscore strategy format to engine's StrategyPattern format**,
So that **all selector configs use the unified StrategyPattern format, enabling seamless integration with the adaptive selector engine**.

## Acceptance Criteria

1. [x] All selector configs use StrategyPattern format
   - Identify all Flashscore selector configs using legacy format
   - Convert or map to engine's StrategyPattern format
   - Verify all converted configs work with engine

2. [x] Automatic conversion layer for legacy configs
   - Create conversion functions for legacy → StrategyPattern
   - Support both new StrategyPattern format and legacy format
   - Maintain backward compatibility with existing YAML configs

3. [x] All existing selectors remain functional
   - Test all existing selectors after conversion
   - Verify no regressions in extraction behavior
   - Maintain the fallback chain functionality from previous stories

## Tasks / Subtasks

- [x] Task 1: Analyze Flashscore strategy format (AC: 1)
  - [x] Scan src/sites/flashscore/selectors/ for strategy formats
  - [x] Identify all legacy strategy configurations
  - [x] Document current format structure

- [x] Task 2: Locate engine's StrategyPattern (AC: 1)
  - [x] Find StrategyPattern class in src/selectors/engine.py or adaptive module
  - [x] Understand required fields and format
  - [x] Document conversion mapping requirements

- [x] Task 3: Create conversion layer (AC: 2)
  - [x] Create conversion functions in src/selectors/strategies/
  - [x] Implement legacy → StrategyPattern conversion
  - [x] Add format detection logic

- [x] Task 4: Integrate with native loading (AC: 1, 2)
  - [x] Update yaml_loader to use conversion layer
  - [x] Test with existing Flashscore YAML configs
  - [x] Verify StrategyPattern format is used internally

- [x] Task 5: Validate and test (AC: 3)
  - [x] Run existing Flashscore tests
  - [x] Verify all selectors work correctly
  - [x] Check no regressions in extraction
  - [x] Test fallback chain still works (from Stories 1.1-1.4)

## Dev Notes

### Project Structure Notes

- **Location**: Primary changes in `src/selectors/` and `src/sites/flashscore/selectors/`
- **Integration Point**: Use conversion layer integrated with YAMLSelectorLoader from Story 7.2
- **Foundation**: Uses native YAML loading from Story 7.2 and UnifiedContext from Story 7.1
- **Pattern**: Follow existing integration patterns from architecture.md

### References

- Source: [sprint-change-proposal-2026-03-09.md#Story-7.3] - Story requirements
- Source: [src/selectors/engine.py] - Engine's StrategyPattern definition
- Source: [src/selectors/yaml_loader.py] - Story 7.2 native loading
- Source: [src/selectors/unified_context.py#UnifiedContext] - Story 7.1 foundation
- Source: [_bmad-output/planning-artifacts/architecture.md#Integration-Architecture] - Integration patterns
- Source: [_bmad-output/project-context.md] - Implementation rules (45 AI agent rules)
- Source: [src/selectors/adaptive/strategies.py] - Engine's strategy patterns

---

# DETAILED ANALYSIS

## Problem Statement

### Current State: Format Incompatibility

Flashscore uses a strategy format incompatible with the engine:

```
Flashscore format: {type, selector, weight}
Engine format: StrategyPattern(type, priority, config)
```

This incompatibility:
1. Prevents seamless integration with engine features
2. Blocks confidence scoring for Flashscore selectors
3. Limits fallback chain optimization
4. Creates maintenance overhead with dual formats

### Strategy Format Analysis

**Flashscore Legacy Format:**
```yaml
selectors:
  home_team:
    type: css
    selector: ".team.home"
    weight: 1.0
  away_team:
    type: css
    selector: ".team.away"
    weight: 0.8
```

**Engine StrategyPattern Format:**
```python
@dataclass
class StrategyPattern:
    type: str           # "css", "xpath", "semantic"
    priority: int       # Higher = more preferred
    config: Dict[str, Any]  # Additional configuration
    confidence: Optional[float] = None
```

### Desired State: Unified Strategy Format

```
Flashscore YAML → Conversion Layer → StrategyPattern → Engine
```

Benefits:
1. Full engine capabilities for all selectors
2. Confidence scoring works universally
3. Consistent fallback chain behavior
4. Single format to maintain

## Technical Foundation from Previous Stories

### Story 7.1: UnifiedContext
- Located in `src/selectors/unified_context.py`
- Combines SelectorContext and DOMContext into single model
- Enables context-aware loading

### Story 7.2: Native YAML Loading
- Uses `YAMLSelectorLoader` from engine
- Automatic loading on scraper initialization
- Fallback to legacy loading for backward compatibility

## Engine StrategyPattern

### Expected Structure

```python
# From src/selectors/engine.py or adaptive module
@dataclass
class StrategyPattern:
    """Unified strategy pattern for selector configuration."""
    
    type: str                    # Strategy type: css, xpath, semantic
    priority: int                # Priority (higher = preferred)
    config: Dict[str, Any]       # Type-specific configuration
    confidence: Optional[float] = None  # Confidence score (0.0-1.0)
    stability: Optional[float] = None    # Historical stability (0.0-1.0)
    alternatives: List[str] = field(default_factory=list)  # Fallback strategy IDs
```

### Conversion Mapping

| Flashscore Field | StrategyPattern Field | Notes |
|------------------|----------------------|-------|
| type | type | Direct mapping |
| selector | config.selector | Move to config dict |
| weight | priority | Convert 0.0-1.0 to 1-100 scale |
| alternatives | alternatives | If defined in YAML |

## Implementation Strategy

### Phase 1: Discovery

Find all strategy format locations:

```bash
# Search patterns
grep -r "weight:" src/sites/flashscore/
grep -r "selector:" src/sites/flashscore/selectors/
```

Expected locations:
- `src/sites/flashscore/selectors/*.yaml` - Selector configuration files
- `src/sites/flashscore/scraper.py` - Strategy initialization

### Phase 2: Conversion Layer

Create conversion module:

```python
# src/selectors/strategies/converter.py
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

@dataclass
class StrategyPattern:
    type: str
    priority: int
    config: Dict[str, Any]
    confidence: Optional[float] = None
    stability: Optional[float] = None
    alternatives: List[str] = None

def convert_legacy_to_strategypattern(legacy: Dict[str, Any]) -> StrategyPattern:
    """Convert Flashscore legacy format to StrategyPattern."""
    ...
    
def detect_format(config: Dict[str, Any]) -> str:
    """Detect if config uses legacy or StrategyPattern format."""
    ...
```

### Phase 3: Integration

1. Modify yaml_loader to use conversion layer
2. Auto-convert legacy configs on load
3. Test all extraction flows work
4. Verify backward compatibility

## Technical Requirements

### Must Follow (from project-context.md)

1. **Async/Await**: All I/O operations must use `async def`
2. **Type Safety**: MyPy strict mode - all functions need type annotations
3. **Pydantic Models**: Use for data transfer objects where appropriate
4. **Naming Conventions**: PascalCase (classes), snake_case (functions/variables)
5. **Custom Exceptions**: Create in src/selectors/exceptions.py if needed
6. **Structured Logging**: Use structlog with correlation IDs
7. **Testing**: Use pytest markers (@pytest.mark.unit, @pytest.mark.integration)

### Architecture Guidelines (from architecture.md)

1. **Integration Pattern**: In-process (import adaptive module directly)
2. **Failure Capture**: Validation layer pattern
3. **Connection Management**: Singleton pattern where appropriate
4. **Use existing**: Don't recreate functionality - integrate existing systems

### Integration Dependencies

This story depends on:
- Story 7.1 (Unified Context Model) - Uses UnifiedContext
- Story 7.2 (Native YAML Loading) - Uses yaml_loader integration

This story enables:
- Story 7.4: Registration Automation - Uses standardized strategy format

## Files to Modify

### Primary Changes

```
src/selectors/
├── strategies/
│   ├── __init__.py           # NEW - Strategy module
│   └── converter.py          # NEW - Conversion layer
├── yaml_loader.py            # MODIFY - Add conversion integration
└── engine.py                 # REVIEW - Check StrategyPattern definition
```

### May Need Changes

```
src/sites/flashscore/
├── selectors/*.yaml          # REVIEW - Ensure compatibility
└── scraper.py                # MODIFY - Use conversion layer if needed
```

### Tests

```
tests/selectors/strategies/
├── test_converter.py         # NEW - Test conversion functions
└── test_strategy_pattern.py  # NEW - Test StrategyPattern integration
```

## Testing Strategy

### Unit Tests
- Test convert_legacy_to_strategypattern with various inputs
- Test format detection logic
- Test backward compatibility

### Integration Tests
- Test yaml_loader with legacy configs
- Test scraper initialization with converted strategies
- Verify all extraction flows work

### Validation
- All existing Flashscore tests pass
- Manual testing of key extraction scenarios
- Verify fallback chain still functions (Stories 1.1-1.4)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| StrategyPattern doesn't exist | High | Create based on engine patterns |
| Breaking existing selectors | High | Extensive testing, maintain backward compatibility |
| Priority/weight conversion issues | Medium | Document mapping clearly |
| Performance regression | Medium | Benchmark before/after |

---

# IMPLEMENTATION CHECKLIST

- [x] Analyze Flashscore strategy format in selectors
- [x] Locate/verify StrategyPattern in engine
- [x] Create conversion functions in src/selectors/strategies/
- [x] Integrate with yaml_loader
- [x] Test with existing Flashscore YAML configs
- [x] Run existing tests to verify no regressions
- [x] Verify fallback chain still works

---

## File List

| File | Change Type | Description |
|------|-------------|-------------|
| src/selectors/strategies/converter.py | NEW | Strategy format converter module |
| src/selectors/strategies/__init__.py | MODIFIED | Added converter exports |
| src/selectors/yaml_loader.py | MODIFIED | Integrated conversion layer |
| tests/selectors/strategies/test_converter.py | NEW | Unit tests for converter |

---

## Change Log

| Date | Change | Details |
|------|--------|---------|
| 2026-03-09 | Story created | Comprehensive implementation guide created |
| 2026-03-09 | Implemented | Created converter.py with legacy→StrategyPattern conversion |
| 2026-03-09 | Integrated | Added conversion to yaml_loader for automatic format detection |
| 2026-03-09 | Tested | Added 21 unit tests, all passing |

---

## Code Review Summary

_N/A - Story not yet implemented_

---

*Story created by: minimax/minimax-m2.5:free*
*Date: 2026-03-09*
