# Edge Case Hunter Review Findings

## Path Analysis: Story 1.3 Detection Sensitivity Configuration

**Reviewer:** Edge Case Hunter  
**Date:** 2026-03-19  
**Files Reviewed:**
- `src/stealth/cloudflare/models/sensitivity.py`
- `src/stealth/cloudflare/models/config.py`
- `src/stealth/cloudflare/config/schema.py`
- `src/stealth/cloudflare/config/flags.py`
- `tests/unit/test_cloudflare_config.py`

---

### JSON Findings:

```json
[
  {
    "location": "src/stealth/cloudflare/models/sensitivity.py:62-68",
    "trigger_condition": "parse_sensitivity_value receives empty string",
    "guard_snippet": "if not normalized: raise SensitivityConfigurationError(...)",
    "potential_consequence": "Empty string matches no keys, raises confusing KeyError-like error"
  },
  {
    "location": "src/stealth/cloudflare/models/sensitivity.py:62-68",
    "trigger_condition": "parse_sensitivity_value receives whitespace-only string",
    "guard_snippet": "normalized = value.lower().strip()",
    "potential_consequence": "Whitespace-only string returns default or raises unclear error"
  },
  {
    "location": "src/stealth/cloudflare/models/sensitivity.py:70-74",
    "trigger_condition": "parse_sensitivity_value receives float that equals int (e.g., 1.0, 3.0)",
    "guard_snippet": "if isinstance(value, float): raise SensitivityConfigurationError(...)",
    "potential_consequence": "Float values like 1.0 pass isinstance(value, int) check in some Python versions"
  },
  {
    "location": "src/stealth/cloudflare/models/sensitivity.py:103-105",
    "trigger_condition": "sensitivity_to_string receives value outside 1-5 range",
    "guard_snippet": "if value < 1 or value > 5",
    "potential_consequence": "Handled - raises SensitivityConfigurationError"
  },
  {
    "location": "src/stealth/cloudflare/models/config.py:48-67",
    "trigger_condition": "detection_sensitivity validator receives None",
    "guard_snippet": "Union[int, str] type hint - None not allowed",
    "potential_consequence": "Pydantic rejects None before validator runs"
  },
  {
    "location": "src/stealth/cloudflare/models/config.py:48-67",
    "trigger_condition": "detection_sensitivity validator receives boolean",
    "guard_snippet": "Union[int, str] - bool is not int or str",
    "potential_consequence": "Boolean values may cause unexpected behavior"
  },
  {
    "location": "src/stealth/cloudflare/config/schema.py:80-87",
    "trigger_condition": "String sensitivity with leading/trailing whitespace",
    "guard_snippet": "normalized = v.lower().strip()",
    "potential_consequence": "Handled - whitespace is stripped before validation"
  },
  {
    "location": "src/stealth/cloudflare/config/schema.py:65-93",
    "trigger_condition": "Invalid string after stripping whitespace",
    "guard_snippet": "if normalized not in VALID_SENSITIVITY_STRINGS",
    "potential_consequence": "Handled - invalid strings raise ValueError"
  },
  {
    "location": "src/stealth/cloudflare/config/flags.py:9-20",
    "trigger_condition": "_parse_sensitivity receives None",
    "guard_snippet": "if sensitivity is None: return 3",
    "potential_consequence": "Handled - returns default 3"
  },
  {
    "location": "src/stealth/cloudflare/config/flags.py:92-95",
    "trigger_condition": "Both nested and top-level detection_sensitivity present",
    "guard_snippet": "nested first, then top-level",
    "potential_consequence": "Nested takes precedence - may be unexpected"
  },
  {
    "location": "tests/unit/test_cloudflare_config.py:501-506",
    "trigger_condition": "parse_sensitivity_value receives whitespace around valid string",
    "guard_snippet": "normalized = value.lower().strip()",
    "potential_consequence": "Handled - whitespace stripped"
  },
  {
    "location": "tests/unit/test_cloudflare_config.py:501-506",
    "trigger_condition": "parse_sensitivity_value receives newline/tab characters",
    "guard_snippet": ".strip() handles newlines and tabs",
    "potential_consequence": "Handled - strip() removes whitespace"
  },
  {
    "location": "src/stealth/cloudflare/models/sensitivity.py:26-30",
    "trigger_condition": "Dictionary mutated at runtime",
    "guard_snippet": "frozen dict or copy on import",
    "potential_consequence": "Using frozenset for VALID_SENSITIVITY_STRINGS - safe"
  },
  {
    "location": "src/stealth/cloudflare/config/schema.py:94",
    "trigger_condition": "parse_sensitivity_value raises exception",
    "guard_snippet": "except SensitivityConfigurationError as e: raise ValueError(str(e))",
    "potential_consequence": "Custom exception converted to ValueError - loses context"
  }
]
```

---

### Additional Edge Cases Identified:

1. **Boolean coercion**: Python's `bool` is a subclass of `int`, so `True` would pass as 1 and `False` as 0 - no explicit guard against boolean values

2. **Float edge case**: Values like `1.0`, `3.0`, `5.0` could pass through depending on how Pydantic handles Union[int, str] deserialization

3. **Unicode strings**: No validation that string input is ASCII - Unicode "high" might cause issues in some contexts

4. **Nested config precedence**: When both `config["cloudflare"]["detection_sensitivity"]` and `config["detection_sensitivity"]` exist, the nested one takes precedence - this may surprise users

5. **Test coverage gap**: No test for `parse_sensitivity_value(1.0)` - would it work or fail?

6. **Test coverage gap**: No test for boolean sensitivity value

7. **No test for empty string**: What happens with `detection_sensitivity: ""`?

---

### Summary

- **Total Edge Case Findings:** 14
- **Unhandled:** 7 (items 1-7 in "Additional Edge Cases")
- **Already Handled:** 7 (items in JSON array)
