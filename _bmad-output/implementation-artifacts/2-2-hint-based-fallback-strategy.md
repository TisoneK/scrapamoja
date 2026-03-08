# Story 2.2: Hint-Based Fallback Strategy

**Status:** done

## Story

As a **scraper system**,
I want **to use hints to determine fallback strategy**,
so that **the fallback chain follows intelligent routing based on selector metadata**.

## Acceptance Criteria

**AC1: Hint-Driven Alternative Selection**
- **Given** a selector with defined hints including `alternatives: ["fallback1", "fallback2"]`
- **When** the primary selector fails
- **Then** the fallback chain uses the hint's `alternatives` to determine which selectors to try
- **And** the alternatives are attempted in the order specified in hints

**AC2: Strategy-Driven Execution Behavior**
- **Given** a selector with a `strategy` hint (`"linear"`, `"priority"`, or `"adaptive"`)
- **When** the fallback chain executes
- **Then** the strategy determines how fallback alternatives are ordered and attempted
- **And** the appropriate fallback behavior is applied per strategy type

**AC3: Custom Rule Evaluation**
- **Given** a selector with custom hint rules in `metadata.rules`
- **When** fallback is triggered
- **Then** the custom rules are evaluated (e.g., `"skip"` or `"prefer"` a specific alternative)
- **And** the fallback ordering/filtering follows the custom logic

## Tasks / Subtasks

- [x] Task 1: Extend `SelectorHint` model with `strategy` field (AC: 2)
  - [x] Add `strategy: str = "linear"` to `SelectorHint` dataclass in `src/selectors/hints/models.py`
  - [x] Update `HintSchema.validate()` to validate `strategy` field (allowed: `"linear"`, `"priority"`, `"adaptive"`)
  - [x] Update `SelectorHint.to_dict()` and `SelectorHint.from_dict()` to include `strategy`

- [x] Task 2: Create `HintBasedFallbackStrategy` in `src/selectors/hints/strategy.py` (AC: 1, 2, 3)
  - [x] Implement `build_chain_from_hint(primary_selector, hint, max_duration=5.0) -> FallbackChain`
  - [x] Implement `_apply_linear_strategy(alternatives) -> List[FallbackConfig]` (ordered as listed)
  - [x] Implement `_apply_priority_strategy(alternatives, metadata) -> List[FallbackConfig]` (per-alternative priorities from `metadata.priorities`)
  - [x] Implement `_apply_adaptive_strategy(alternatives, hint) -> List[FallbackConfig]` (deferred to Story 2-3; treat as linear + log warning)
  - [x] Implement `_apply_custom_rules(alternatives, metadata) -> List[FallbackConfig]` (support `"skip"` and `"prefer"` rule types)
  - [x] Raise `SelectorConfigurationError` if hint has no alternatives

- [x] Task 3: Add hint-driven execution method to `FallbackChainExecutor` (AC: 1, 2)
  - [x] Add `execute_with_hint_strategy(primary_selector, hint, context) -> FallbackResult` to `chain.py`
  - [x] Delegate chain-building to `HintBasedFallbackStrategy.build_chain_from_hint()`
  - [x] Delegate execution to existing `execute_chain(chain, context)`
  - [x] Log which strategy was applied at `DEBUG` level

- [x] Task 4: Export new symbols (AC: 1, 2)
  - [x] Add `HintBasedFallbackStrategy` to `src/selectors/hints/__init__.py`
  - [x] Add `execute_with_hint_strategy` re-export note in `src/selectors/fallback/__init__.py` docstring

- [x] Task 5: Write unit tests in `tests/selectors/hints/test_strategy.py` (AC: 1, 2, 3)
  - [x] Test `linear` strategy preserves listed order
  - [x] Test `priority` strategy reorders by per-alternative priorities in metadata
  - [x] Test `adaptive` strategy falls back to linear with a logged warning
  - [x] Test custom rules: `"skip"` removes an alternative from chain
  - [x] Test custom rules: `"prefer"` moves an alternative to front of chain
  - [x] Test raises `SelectorConfigurationError` when hint has no alternatives
  - [x] Test `execute_with_hint_strategy` integration with `FallbackChainExecutor`

## Review Follow-ups (AI)

- [ ] [AI-Review][Medium] Fix File List documentation: The hints module files (`models.py`, `__init__.py`) are listed as "Modified" but should be listed as "New" since the entire `src/selectors/hints/` directory was created in this epic (Story 2-1 and 2-2)
- [ ] [AI-Review][Low] Register `@pytest.mark.unit` in pytest.ini to eliminate 33 test warnings about unknown mark
- [ ] [AI-Review][Low] Consider removing the unused defensive `else` branch in `strategy.py` that handles unknown strategies (lines 92-99), since `SelectorHint.__post_init__` already validates this

## Dev Notes

### What This Story Implements

1. **`strategy` field** on `SelectorHint` - controls how alternatives are ordered in the fallback chain
2. **`HintBasedFallbackStrategy`** - converts a `SelectorHint` into a `FallbackChain` respecting the declared strategy
3. **`FallbackChainExecutor.execute_with_hint_strategy()`** - new entry point that builds chain from hints then delegates to existing `execute_chain()`
4. Custom rule evaluation via `metadata.rules` (AC3) - `"skip"` / `"prefer"` rule types

### What This Story Does NOT Include

- Stability-based prioritization across multiple selectors (Story 2-3)
- Full "adaptive" strategy using runtime metrics from the adaptive module (Story 2-3)
- Updating `@with_fallback` decorator to automatically detect and use YAML hints (future)
- Failure event capture / DB submission (Epic 3)

### 🚨 Critical Anti-Patterns to Avoid

1. **DO NOT** create a second `FallbackChain` builder elsewhere - `HintBasedFallbackStrategy` is the single owner
2. **DO NOT** modify `FallbackChainExecutor.execute_chain()` - add a NEW method `execute_with_hint_strategy()`; keep existing `execute_chain()` intact to avoid regressions
3. **DO NOT** call `_apply_adaptive_strategy` with the intention of full adaptive logic - it is a stub (linear + warning) in this story; Story 2-3 completes it
4. **DO NOT** require more than 1 alternative from hints (unlike `FallbackDecorator` which requires ≥2) - `FallbackChain` itself requires ≥1 fallback, which is sufficient
5. **NEVER** import `FallbackChain` / `FallbackConfig` from `src.selectors.fallback.models` inside `hints/strategy.py` without checking for circular import - use a type-only import if needed

### Architecture: Integration Flow

```
YAML Selector (with hints)
        │
        ▼ parse_hints() [already done in Story 2-1]
  SelectorHint(strategy="linear", alternatives=["fb1", "fb2"])
        │
        ▼ HintBasedFallbackStrategy.build_chain_from_hint()
  FallbackChain(primary="primary_sel", fallbacks=[FallbackConfig("fb1",p=1), FallbackConfig("fb2",p=2)])
        │
        ▼ FallbackChainExecutor.execute_chain()  [existing, unchanged]
  FallbackResult
```

`execute_with_hint_strategy()` is a thin orchestrator:
```python
async def execute_with_hint_strategy(
    self,
    primary_selector: str,
    hint: SelectorHint,
    context: DOMContext,
    max_chain_duration: float = 5.0,
) -> FallbackResult:
    strategy = HintBasedFallbackStrategy()
    chain = strategy.build_chain_from_hint(primary_selector, hint, max_chain_duration)
    return await self.execute_chain(chain, context)
```

### Strategy Type Implementations

**`linear` (default):**
```python
# alternatives: ["fb1", "fb2", "fb3"]  →  FallbackConfig priorities: 1, 2, 3
[FallbackConfig(selector_name=name, priority=i+1) for i, name in enumerate(alternatives)]
```

**`priority` (per-alternative priorities via metadata):**
```python
# metadata: {"priorities": {"fb1": 3, "fb2": 1, "fb3": 2}}
# Result: ordered by descending priority value → fb1(3), fb3(2), fb2(1)
priorities_map = metadata.get("priorities", {}) if metadata else {}
def get_p(name): return priorities_map.get(name, 5)  # default mid-priority
sorted_names = sorted(alternatives, key=get_p, reverse=True)
[FallbackConfig(selector_name=name, priority=i+1) for i, name in enumerate(sorted_names)]
```

**`adaptive` (Story 2-3 stub):**
```python
# Log warning, fall back to linear
self._logger.warning("adaptive_strategy_not_yet_implemented", ...)
return self._apply_linear_strategy(alternatives)
```

**Custom rules (AC3) - `_apply_custom_rules`:**
Rules live at `hint.metadata["rules"]`: a list of `{"type": "skip"|"prefer", "selector": "<name>"}` dicts.
- `"skip"`: remove that alternative from the list
- `"prefer"`: move that alternative to index 0 (highest priority)
- Unrecognized rule types are ignored with a debug log
- Called when `hint.metadata` contains `"rules"` key (any strategy type can carry custom rules; the executor should call `_apply_custom_rules` as a post-processing pass if `metadata.rules` exists)

### SelectorHint Model Changes

**In `src/selectors/hints/models.py`:**

```python
@dataclass
class SelectorHint:
    stability: float = 0.5
    priority: int = 5
    alternatives: List[str] = field(default_factory=list)
    strategy: str = "linear"           # ← NEW in Story 2-2
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # ... existing validation ...
        VALID_STRATEGIES = {"linear", "priority", "adaptive"}
        if self.strategy not in VALID_STRATEGIES:
            raise ValueError(f"Strategy must be one of {VALID_STRATEGIES}, got '{self.strategy}'")
```

Update `to_dict()` to include `"strategy"` key.
Update `from_dict()` to read `data.get("strategy", "linear")`.

**In `HintSchema.validate()`** add:
```python
strategy = hint_data.get("strategy", "linear")
VALID_STRATEGIES = {"linear", "priority", "adaptive"}
if strategy not in VALID_STRATEGIES:
    raise ValueError(f"Strategy must be one of {VALID_STRATEGIES}")
validated["strategy"] = strategy
```

### Project Structure Notes

**New files:**
```
src/selectors/hints/strategy.py           ← HintBasedFallbackStrategy
tests/selectors/hints/test_strategy.py    ← unit tests
```

**Modified files:**
```
src/selectors/hints/models.py             ← add strategy field
src/selectors/hints/__init__.py           ← export HintBasedFallbackStrategy
src/selectors/fallback/chain.py           ← add execute_with_hint_strategy()
```

**UNCHANGED (do NOT touch unless fixing a bug):**
```
src/selectors/fallback/decorator.py
src/selectors/fallback/models.py
src/selectors/fallback/logging.py
src/selectors/fallback/__init__.py
src/selectors/yaml_loader.py
```

### Naming Conventions (MUST Follow)

- Class: `HintBasedFallbackStrategy` (PascalCase)
- Methods: `build_chain_from_hint`, `execute_with_hint_strategy` (snake_case)
- Constants: `VALID_STRATEGIES = frozenset({"linear", "priority", "adaptive"})` (UPPER_SNAKE_CASE)
- Test file: `test_strategy.py`, test class: `TestHintBasedFallbackStrategy`
- Logger name: `"selector_hints_strategy"` (use same `_get_logger` pattern as other modules)

### Error Handling

- If `hint.alternatives` is empty → raise `SelectorConfigurationError(message="...", selector_id=primary_selector)`
- If `hint.strategy` is invalid → `SelectorHint.__post_init__` already raises `ValueError`; `parse_hints()` wraps it in `SelectorConfigurationError`
- Unrecognized rule type in `metadata.rules` → log at DEBUG, skip that rule (do NOT raise)
- Import: `from src.selectors.exceptions import SelectorConfigurationError`

### Logger Pattern (Copy Exactly from Existing Modules)

```python
def _get_logger(self):
    try:
        from src.observability.logger import get_logger
        return get_logger("selector_hints_strategy")
    except ImportError:
        import logging
        return logging.getLogger("selector_hints_strategy")
```

### Testing Patterns

- Use `@pytest.mark.unit` for all tests in `test_strategy.py`
- Tests must verify ACTUAL behavior (ordering, filtering), not just method existence
- Use `unittest.mock.AsyncMock` for mocking `SelectorEngine.resolve` in executor integration tests
- Use `datetime.now(timezone.utc)` (NOT `datetime.utcnow()`) in any test timestamps
- Follow existing test style in `tests/selectors/hints/test_parser.py`

**Minimal integration test pattern for `execute_with_hint_strategy`:**
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_with_hint_strategy_uses_alternatives():
    from unittest.mock import AsyncMock, MagicMock
    from src.selectors.fallback.chain import FallbackChainExecutor
    from src.selectors.hints.models import SelectorHint
    from src.selectors.context import DOMContext

    mock_engine = MagicMock()
    # Primary fails
    mock_engine.resolve = AsyncMock(side_effect=[
        MagicMock(success=False, failure_reason="not found", element_info=None),
        # fallback1 succeeds
        MagicMock(success=True, element_info=MagicMock()),
    ])
    executor = FallbackChainExecutor(selector_engine=mock_engine)
    hint = SelectorHint(alternatives=["fallback1"], strategy="linear")
    context = MagicMock(spec=DOMContext, url="http://test.com")

    result = await executor.execute_with_hint_strategy("primary", hint, context)

    assert result.fallback_executed is True
    assert result.fallback_success is True
```

### Dependency Flow Context

```
Story 1-1 → 1-2 → 1-3 → 1-4 (done)
                            ↓
              Story 2-1 (hints schema reading) ← done, in review
                            ↓
              Story 2-2 (this) - hint-based fallback strategy
                            ↓
              Story 2-3 - stability-based prioritization
```

Story 2-2 depends on Story 2-1's `SelectorHint` model and `parse_hints()`. Story 2-3 will extend the `"adaptive"` strategy stub created here.

### References

- Epic 2 details: `_bmad-output/planning-artifacts/epics.md#L231-256` (Story 2.2 ACs)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` (Fallback Chain Pattern, Integration Patterns)
- Previous story: `_bmad-output/implementation-artifacts/2-1-yaml-hint-schema-reading.md`
- Hint models: `src/selectors/hints/models.py`
- Hint parser: `src/selectors/hints/parser.py`
- Fallback chain executor: `src/selectors/fallback/chain.py`
- Fallback models: `src/selectors/fallback/models.py` (`FallbackChain`, `FallbackConfig`, `FallbackResult`)
- Exceptions: `src/selectors/exceptions.py` (`SelectorConfigurationError`)
- Existing hint tests: `tests/selectors/hints/test_parser.py`
- Epic 1 retro (patterns & lessons): `_bmad-output/implementation-artifacts/epic-1-retro-2026-03-07.md`

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5 (claude-sonnet-4-6)

### Debug Log References

No blocking issues. Pre-existing test failures in `tests/selectors/hints/test_yaml_loader_integration.py` (2 tests) are caused by `YAMLSelectorLoader` rejecting OS temp-dir paths — unrelated to this story and present before implementation began.

### Completion Notes List

- `VALID_STRATEGIES` defined as a module-level `frozenset` in `models.py`. The validation is enforced at `SelectorHint.__post_init__()` level, so `strategy.py` does not need to import it directly.
- `HintSchema` dataclass also received the `strategy` field and `to_dict()` update for consistency with `SelectorHint`.
- `_apply_custom_rules` operates on `List[FallbackConfig]` (post-strategy step) and re-normalises priority values (1, 2, 3 …) after skip/prefer mutations so `FallbackChain.__post_init__` sort remains stable.
- `execute_with_hint_strategy` uses a local import of `HintBasedFallbackStrategy` inside the method body to avoid any potential circular-import risk at module load time (hints → fallback.models is safe; fallback.chain → hints.strategy is the new edge).
- `_apply_adaptive_strategy` is a stub that logs a `warning` and delegates to linear — full runtime-metric logic is deferred to Story 2-3 as specified.
- 33 new unit tests: 25 for `HintBasedFallbackStrategy` directly, 8 integration tests for `execute_with_hint_strategy`. All pass (100%).
- No existing tests were broken: `tests/selectors/hints/` and `tests/selectors/fallback/` suites pass at 120/120 excluding the 2 pre-existing yaml-loader failures.

### File List

**New files:**
- `src/selectors/hints/strategy.py`
- `tests/selectors/hints/test_strategy.py`

**Modified files:**
- `src/selectors/hints/models.py` — added `strategy` field + validation to `SelectorHint` and `HintSchema`
- `src/selectors/hints/__init__.py` — exported `HintBasedFallbackStrategy`
- `src/selectors/fallback/chain.py` — added `execute_with_hint_strategy` method to `FallbackChainExecutor`
- `src/selectors/fallback/__init__.py` — updated module docstring with `execute_with_hint_strategy` note

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-03-07 | Added `strategy` field to `SelectorHint` and `HintSchema` | Story 2-2 AC2 — strategy controls how hint alternatives are ordered |
| 2026-03-07 | Created `HintBasedFallbackStrategy` in `src/selectors/hints/strategy.py` | Story 2-2 AC1/2/3 — single owner for converting hints into FallbackChains |
| 2026-03-07 | Added `execute_with_hint_strategy` to `FallbackChainExecutor` | Story 2-2 AC1/2 — new entry point for hint-driven chain execution |
| 2026-03-07 | Exported `HintBasedFallbackStrategy` from `src/selectors/hints/__init__.py` | Consistent public API surface |
| 2026-03-07 | Created `tests/selectors/hints/test_strategy.py` (33 tests) | Coverage for all ACs, strategy branches, custom rules, and executor integration |