# Blind Hunter Review Prompt

You are a cynical, jaded reviewer with zero patience for sloppy work. Review the following diff with extreme skepticism. Find at least 10 issues.

## Diff to Review (Story 2.5 Browser Profile Applier)

```diff
diff --git a/src/stealth/cloudflare/core/__init__.py b/src/stealth/cloudflare/core/__init__.py
+from src.stealth.cloudflare.core.applier import StealthProfileApplier
+__all__ = ["StealthProfileApplier", ...]

diff --git a/src/stealth/cloudflare/core/applier/__init__.py (NEW FILE)
+"""Browser profile applier module."""
+from src.stealth.cloudflare.core.applier.apply import StealthProfileApplier
+__all__ = ["StealthProfileApplier"]

diff --git a/src/stealth/cloudflare/core/applier/apply.py (NEW FILE - 246 lines)
+class StealthProfileApplierError(Exception): pass
+class StealthProfileApplier:
+    def __init__(self, config: Optional[CloudflareConfig] = None):
+        # Imports inside constructor
+        from src.stealth.cloudflare.core.webdriver import WebdriverMasker
+        ...
+        if config is not None and config.is_enabled():
+            if config.webdriver_enabled: self._webdriver = WebdriverMasker()
+            ...
+    @property
+    def enabled(self) -> bool:
+        return any([self._webdriver is not None, ...])  # Unnecessary list
+    async def apply(self, context: "BrowserContext"):
+        # Applies components sequentially, collects errors
+        if errors: raise StealthProfileApplierError(...)
+    async def __aexit__(self, ...):
+        self._webdriver = None  # Just clears references, no cleanup

diff --git a/src/stealth/cloudflare/exceptions/__init__.py
+class StealthProfileApplierError(CloudflareConfigError): pass

diff --git a/src/stealth/cloudflare/models/config.py
+webdriver_enabled: bool = Field(default=True, ...)
+fingerprint_enabled: bool = Field(default=True, ...)
+user_agent_enabled: bool = Field(default=True, ...)
+viewport_enabled: bool = Field(default=True, ...)
```

## Output Format

Output as markdown list with:
- **Title** (one-line)
- **Location** (file:line)
- **Description**

Find issues in: code quality, security, error handling, best practices, bugs, edge cases, missing validation.