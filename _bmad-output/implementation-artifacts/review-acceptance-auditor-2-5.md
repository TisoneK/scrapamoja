# Acceptance Auditor Review Prompt

You are an Acceptance Auditor. Review this diff against the spec and check for violations of acceptance criteria.

## Spec (Story 2.5 Browser Profile Applier)

### AC1: Unified Profile Application
**Given** a Playwright browser context
**When** applying stealth profile to context
**Then** all stealth configurations are applied in the correct order
**And** the context appears as a regular user browser

### AC2: Configuration Integration
**Given** Cloudflare protection is enabled via CloudflareConfig
**When** applying stealth profile
**Then** all feature flags are respected (webdriver_enabled, fingerprint_enabled, user_agent_enabled, viewport_enabled)
**And** each component is only applied if its feature flag is enabled

### AC3: Session Consistency
**Given** Cloudflare protection is enabled
**When** applying stealth profile to a new context
**Then** the profile remains consistent throughout the session
**And** all components use the same correlation ID for logging

### AC4: Error Handling
**Given** an error during profile application
**When** applying stealth profile
**Then** a clear error is raised with details
**And** partial state is avoided (all-or-nothing application)

## Diff to Review

```diff
src/stealth/cloudflare/core/applier/apply.py:
- StealthProfileApplier.apply() uses module-level logger
- No CorrelationContext used for correlation ID
- Components applied sequentially
- Errors collected but raised after all attempts
- No rollback mechanism visible

src/stealth/cloudflare/models/config.py:
- Added webdriver_enabled, fingerprint_enabled, user_agent_enabled, viewport_enabled
```

## Output Format

Output as markdown list with:
- **Title** (one-line)
- **AC violated** (AC1, AC2, AC3, or AC4)
- **Evidence** from diff

Check for: violations of acceptance criteria, deviations from spec intent, missing implementation of specified behavior.