# Story 3.3: Implement Clear Error Messages

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **site module developer**,  
I want **clear, actionable error messages when I make mistakes**,  
So that **I can quickly fix issues without deep debugging**.

## Acceptance Criteria

1. **Given** invalid input or incorrect usage, **When** the error occurs, **Then** the error message is specific and actionable

2. **And** for timing violations: "attach() must be called before page.goto(). Call attach() first, then navigate."

3. **And** for pattern errors: Clear description of what made the pattern invalid

4. **And** the errors do not expose internal Playwright concepts - site module developers never need to read Playwright documentation to understand error messages

## Tasks / Subtasks

- [x] Task 1: Verify TimingError message matches PRD specification (AC: #2)
  - [x] Subtask 1.1: Confirm current message already matches PRD exactly
  - [x] Subtask 1.2: Document that no changes are needed
  - [x] Subtask 1.3: Add test to ensure message remains correct
- [x] Task 2: Enhance PatternError regex message for better actionability (AC: #3)
  - [x] Subtask 2.1: Review current regex error message in interceptor.py line 124-126
  - [x] Subtask 2.2: Add guidance on common regex issues (unescaped chars, unmatched brackets)
  - [x] Subtask 2.3: Test enhanced message with various invalid regex scenarios
- [x] Task 3: Verify NetworkError usage doesn't need enhancement (AC: #1, #4)
  - [x] Subtask 3.1: Confirm NetworkError only used in backward compatibility
  - [x] Subtask 3.2: Document that no direct NetworkError raises need enhancement
  - [x] Subtask 3.3: Verify existing NetworkError messages are already clear
- [x] Task 4: Add comprehensive error message tests
  - [x] Subtask 4.1: Test TimingError message accuracy (should remain unchanged)
  - [x] Subtask 4.2: Test enhanced PatternError message actionability
  - [x] Subtask 4.3: Test NetworkError message clarity (should remain unchanged)
  - [x] Subtask 4.4: Verify no Playwright concepts in any error messages

## Dev Notes

### Current State Analysis

**Verification Results:**

1. **TimingError Message ✅ ALREADY CORRECT**
   - Current message in interceptor.py lines 214-217, 226-229, 231-235, 238-242:
   - `"attach() must be called before page.goto(). Call attach() first, then navigate."`
   - **Status: ALREADY MATCHES PRD SPECIFICATION EXACTLY - No changes needed**

2. **PatternError Messages ⚠️ NEEDS MINOR ENHANCEMENT**
   - Current messages in interceptor.py lines 110, 116, 124-126:
     - `"patterns list cannot be empty"` ✅ GOOD
     - `f"pattern at index {i} cannot be empty string"` ✅ GOOD  
     - `f"invalid regex pattern at index {i}: {pattern!r} - {e}"` ⚠️ COULD BE MORE ACTIONABLE
   - **Enhancement needed**: Add guidance on common regex issues

3. **NetworkError Usage ✅ NO DIRECT RAISES FOUND**
   - NetworkError is only used in backward compatibility function `create_network_error`
   - No direct NetworkError raises in interceptor.py that need enhancement
   - **Status: No changes needed**

### Implementation Requirements

**This is an enhancement story, not new implementation:**

1. **TimingError**: ✅ DO NOT CHANGE - already matches PRD specification exactly
2. **PatternError**: ⚠️ ENHANCE ONLY regex error message to be more actionable
3. **NetworkError**: ✅ DO NOT CHANGE - no direct raises found that need enhancement

**PatternError Enhancement Specification:**
- Current: `f"invalid regex pattern at index {i}: {pattern!r} - {e}"`
- Enhanced: `f"invalid regex pattern at index {i}: {pattern!r} - {e}. Check for: unescaped special characters, unmatched brackets, or invalid quantifiers."`

**Error Message Principles:**

1. **Specificity**: Exactly what went wrong and where
2. **Actionability**: Clear next step to fix the issue
3. **No Internal Exposure**: Hide Playwright internals unless explicitly required by PRD
4. **Consistency**: Same error type always has consistent message format

### Architecture Compliance

**MUST follow these architectural decisions:**

1. **Exception Types**: Use TimingError, PatternError, NetworkError (already defined)
2. **Error Location**: Raise exceptions at the point of detection (attach, constructor, response handling)
3. **Message Format**: String messages that are human-readable without technical documentation
4. **No Trace Pollution**: Errors should not expose internal stack traces or Playwright objects

**Anti-Patterns to Avoid:**
- NOT exposing Playwright internal APIs or objects in error messages
- NOT using generic error messages like "Invalid input"
- NOT requiring developers to read Playwright documentation to understand errors
- NOT including technical jargon that doesn't help fix the issue

### Project Structure Notes

**Module Structure (from Epic 1):**
- `src/network/interception/__init__.py` - exports NetworkInterceptor, CapturedResponse
- `src/network/interception/interceptor.py` - NetworkInterceptor class (error raising locations)
- `src/network/interception/models.py` - CapturedResponse dataclass
- `src/network/interception/exceptions.py` - TimingError, PatternError, NetworkError (THIS STORY)
- `src/network/interception/patterns.py` - pattern matching logic

**Dependencies:**
- Playwright >= 1.40.0
- Python 3.11+ with async/await
- Already implemented: 
  - Story 1.1 (module structure)
  - Story 1.2 (constructor with PatternError)
  - Story 1.3 (pattern matching)
  - Story 2.1 (attach method with TimingError)
  - Story 2.2 (network event listener)
  - Story 2.3 (response capture)
  - Story 2.4 (detach method)
  - Story 3.1 (error handling - NetworkError usage)
  - Story 3.2 (dev logging - NetworkError usage)

### Previous Story Learnings

**From Story 3.1 (Error Handling):**
1. **Error Isolation**: All errors caught and logged, don't crash interceptor
2. **NetworkError Usage**: Used for general interception failures
3. **Logging Pattern**: Structured logging with context fields
4. **Graceful Continuation**: After any error, monitoring continues

**From Story 3.2 (Dev Logging):**
1. **Dev Logging Integration**: Errors logged when dev_logging=True
2. **State Tracking**: Instance variables track error conditions
3. **User-Friendly Messages**: Already some user-friendly error messages in place

**From Story 2.1 (attach method):**
1. **Timing Detection**: Logic already exists to detect attach() after page.goto()
2. **TimingError**: Already raised, but message may need enhancement
3. **Two-Check Validation**: URL check + readyState check for robustness

**From Story 1.2 (constructor):**
1. **Pattern Validation**: Logic already exists to validate patterns
2. **PatternError**: Already raised for invalid patterns
3. **Validation Types**: Empty patterns, invalid regex detected

### Testing Requirements

**Test Coverage (100% error message clarity target):**

1. **TimingError Tests:**
   - Test exact message matches PRD specification
   - Test error raised at correct point (attach after goto)
   - Test message is actionable without Playwright knowledge

2. **PatternError Tests:**
   - Test empty patterns list message
   - Test invalid regex pattern message
   - Test malformed URL pattern message
   - Test each message provides specific fix guidance

3. **NetworkError Tests:**
   - Test all NetworkError usages have clear messages
   - Test messages don't expose Playwright internals
   - Test messages are actionable for site module developers

4. **Integration Tests:**
   - Test error messages in real usage scenarios
   - Test developer can fix issues using only error messages
   - Test no Playwright documentation needed for error resolution

### Error Message Specifications

**TimingError (PRD FR10):**
```
"attach() must be called before page.goto(). Call attach() first, then navigate."
```

**PatternError Examples (FR8):**
```
"Patterns list cannot be empty. Provide at least one URL pattern."
"Invalid regex pattern 'invalid[': Unterminated character set. Check regex syntax."
"Pattern must be a string. Got type 'int' for pattern 123."
```

**NetworkError Examples (FR13, FR14):**
```
"Failed to capture response body: Page navigated away before body could be read."
"Handler callback failed: Response processing continues but handler raised an exception."
```

### References

- [Source: epics.md#Story-33-Implement-Clear-Error-Messages]
- [Source: architecture.md#Error-Handling]
- [Source: architecture.md#Exception-Patterns]
- [Source: project-context.md#Error-Handling-Architecture]
- Related: Story 1.2 (PatternError), Story 2.1 (TimingError), Story 3.1 (NetworkError)
- FRs covered: FR8, FR10, FR24
- PRD specification: "attach() must be called before page.goto(). Call attach() first, then navigate."

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

- Implementation builds on Stories 1.2 (PatternError), 2.1 (TimingError), 3.1 (NetworkError)
- Story 3.1 already has NetworkError usage in error handling scenarios
- Story 3.2 has dev logging integration with error messages
- Key focus: Message clarity and actionability, not new error types
- Must maintain exact TimingError message as specified in PRD

### Completion Notes List

- [x] **Verified TimingError message:**
  - Confirmed exact PRD specification match: "attach() must be called before page.goto(). Call attach() first, then navigate."
  - Message matches PRD exactly at all 4 raising locations (lines 214-217, 226-229, 231-235, 238-242 in interceptor.py)
  - No changes needed - already correct
  
- [x] **Enhanced PatternError messages:**
  - Enhanced invalid regex pattern message to include actionable guidance
  - New message format: "invalid regex pattern at index {i}: {pattern!r} - {e}. Check for: unescaped special characters, unmatched brackets, or invalid quantifiers."
  - Tested with unclosed bracket, invalid quantifier patterns
  - Verified guidance is provided for all regex error types
  
- [x] **Verified NetworkError usage:**
  - NetworkError only used in backward compatibility function create_network_error()
  - No direct NetworkError raises in interceptor.py that need enhancement
  - No changes needed
  
- [x] **Added comprehensive error message tests:**
  - Created tests/unit/network/interception/test_error_messages.py with 11 tests
  - Tests verify exact TimingError message matches PRD
  - Tests verify PatternError provides actionable guidance
  - Tests verify no Playwright concepts in error messages
  - All 88 existing tests pass (no regressions)

### File List

- `src/network/interception/interceptor.py` - Enhanced PatternError message with actionable guidance (line 124-126)
- `tests/unit/network/interception/test_error_messages.py` - NEW FILE: Comprehensive error message tests (11 tests)
