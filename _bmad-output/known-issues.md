# Known Issues - Pre-existing Test Failures

**Last Updated:** 2026-03-15

## Overview

This document tracks pre-existing test failures that are unrelated to the SCR-002 Network Interception epic work. These failures existed before the current sprint and should not block SCR-002 progress.

## Pre-existing Test Failures (12 tests)

The following 12 tests fail in the current test suite. These are **NOT** caused by SCR-002 work:

### Network Module Failures (12 tests)

| Test | File | Issue |
|------|------|-------|
| `test_run_get_request_success` | `tests/network/test_direct_cli.py` | CLI integration test |
| `test_gather_returns_network_error_on_failure` | `tests/network/test_errors.py` | Concurrent error handling |
| `test_create_response` | `tests/network/test_interception.py` | Response creation |
| `test_response_with_string_body` | `tests/network/test_interception.py` | String body handling |
| `test_response_with_timing` | `tests/network/test_interception.py` | Timing info |
| `test_attach_to_page` | `tests/network/test_interception.py` | Page attachment |
| `test_clear_captured_responses` | `tests/network/test_interception.py` | Response clearing |
| `test_execute_returns_httpx_response` | `tests/network/test_response_delivery.py` | HTTPX response |
| `test_execute_sync_returns_httpx_response` | `tests/network/test_response_delivery.py` | Sync HTTPX |
| `test_response_has_required_properties` | `tests/network/test_response_delivery.py` | Response properties |
| `test_gather_returns_httpx_response_objects` | `tests/network/test_response_delivery.py` | Concurrent response |
| `test_gather_response_content_accessible` | `tests/network/test_response_delivery.py` | Content access |

## Test Suite Status

- **Total tests in network/**: 287
- **Passing:** 275
- **Failing:** 12 (pre-existing)
- ** SCR-002 tests:** 76 passing (64 baseline + 12 new for Story 3.3)

## Notes

- These failures are in the legacy `tests/network/` directory, not the new `tests/unit/network/interception/` directory
- The new interception tests (Story 1.x, 2.x, 3.x) all pass
- These failures should be addressed in a separate cleanup task, not blocking SCR-002

## Action Items

- [ ] Create cleanup ticket for pre-existing test failures
- [ ] Investigate root causes of the 12 failures
- [ ] Fix or mark as known failures in pytest config
