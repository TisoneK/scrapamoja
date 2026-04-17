# Edge Case Hunter Review Prompt

You are an Edge Case Hunter. Review the following diff for edge cases, error handling gaps, and potential failure scenarios that the developer might have missed.

## Diff to Review (Story 2.5 Browser Profile Applier)

```diff
src/stealth/cloudflare/core/applier/apply.py:
- Imports inside __init__ on every instantiation
- config.is_enabled() called but check not in CloudflareConfig shown
- any([...]) creates unnecessary list allocation
- __aexit__ just sets references to None, no actual cleanup
- Errors collected but raised as generic StealthProfileApplierError
- No correlation ID used in logging
- Components applied sequentially without rollback on failure

src/stealth/cloudflare/models/config.py:
- webdriver_enabled: bool = Field(default=True) - no StrictBool
- fingerprint_enabled: bool = Field(default=True) - no validation
- user_agent_enabled: bool = Field(default=True) - no validation
- viewport_enabled: bool = Field(default=True) - no validation
```

## Output Format

Output as markdown list with:
- **Title** (one-line)
- **Trigger condition** 
- **Potential consequence**

Find edge cases covering: config validation, error handling, resource cleanup, concurrency, type safety.