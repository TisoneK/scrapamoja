# Edge Case Hunter Review - Story 2-2 Canvas/WebGL Fingerprint Randomization

**Reviewer:** Edge Case Hunter (diff + project access)
**Story:** 2-2-canvas-webgl-fingerprint-randomization

## Diff Content

### Modified File
- `src/stealth/cloudflare/exceptions/__init__.py` - Added `FingerprintRandomizerError`

### New Files
- `src/stealth/cloudflare/core/fingerprint/__init__.py`
- `src/stealth/cloudflare/core/fingerprint/scripts.py` (~520 lines)
- `tests/unit/test_cloudflare_fingerprint.py` (~390 lines)

## Project Context Analysis

### Existing Patterns in Codebase
- The project uses async/await patterns consistently
- Uses `src.observability.logger` for logging
- Uses Pydantic for configuration validation
- Cloudflare module structure follows SCR-003 sub-module pattern

### Integration Points
- `src.stealth.cloudflare.exceptions` - imports `CloudflareConfigError` as base
- `src.observability.logger` - uses `get_logger()`
- Playwright integration via `context.add_init_script()`

## Edge Case Findings

### Critical Edge Cases

1. **Canvas read failure on tainted canvas**
   ```
   ctx.getImageData() throws DOMException on cross-origin images
   ```
   - Current code: catches all exceptions silently
   - Impact: Works silently but may not randomize tainted canvases
   - **Mitigation needed:** Document this limitation or detect tainting

2. **WebGL not available in context**
   - Code doesn't check if WebGL is available before spoofing
   - `WebGLRenderingContext` might be null in headless browsers
   - **Mitigation needed:** Add feature detection

3. **Multiple context applications**
   - Applying randomizer multiple times to same context
   - Each call adds init script again (cumulative)
   - Noise applied multiple times = excessive randomization
   - **Mitigation:** Track if already applied

### Medium Edge Cases

4. **Headless browser detection**
   - `navigator.webdriver` may still be true
   - Combined with Story 2.1, should be masked
   - **Check:** Verify webdriver masking is applied before fingerprint

5. **Canvas with zero dimensions**
   - `canvas.width = 0` or `canvas.height = 0`
   - `getImageData(0, 0, 0, 0)` behavior is undefined
   - **Mitigation:** Add dimension checks

6. **WebGL2 not present**
   - Code checks `if (WebGL2RenderingContext)` but could fail
   - Some browsers only support WebGL1
   - **Mitigation:** Ensure graceful fallback

7. **Performance on large canvases**
   - 4K screenshots: 3840×2160 × 4 bytes = ~33MB per operation
   - Random noise on every `toDataURL` call is expensive
   - **Mitigation:** Add sampling or throttling

8. **Context lost/restored events**
   - WebGL context can be lost and restored
   - Spoofing may not persist after context restore
   - **Mitigation:** Listen for `webglcontextlost` event

### Minor Edge Cases

9. **Color space differences**
   - Different browsers use different color spaces (sRGB vs P3)
   - Noise addition may be visible on color-managed displays
   - **Mitigation:** Consider color space handling

10. **Memory leaks in init scripts**
    - JS closures may capture references
    - Over time could accumulate memory
    - **Mitigation:** Use IIFE properly (already done)

11. **toBlob callback may be async**
    - `toBlob` signature: `toBlob(callback, type, quality)`
    - Current override doesn't handle async callback properly
    - **Mitigation:** Review callback handling

12. **Worker canvas**
    - OffscreenCanvas in Web Workers
    - Code doesn't handle worker canvas
    - **Mitigation:** Add OffscreenCanvas support if needed

## Summary

| Severity | Count |
|----------|-------|
| Critical | 3 |
| Medium | 5 |
| Minor | 4 |
| **Total** | **12** |

## Recommendations

1. Add feature detection for WebGL availability
2. Track application state to prevent duplicate initialization
3. Add canvas dimension validation
4. Add WebGL context restore handling
5. Document limitations (tainted canvas, WebGL1-only, etc.)
