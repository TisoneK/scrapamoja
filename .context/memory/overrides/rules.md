# Protocol Overrides (update in place — project-owned)

Project-local adjustments to the protocol. Sessions read this file
right after loading their edition; where an override and the edition
conflict, **the override wins** — except the two rules nothing can
override: secret handling and append-only guarantees.

Overrides are standing, project-shaped deltas — not session
instructions (those die with the session) and not user preferences
(those live in `../user/preferences.md`). Core updates never touch
this file: customizations here survive every core version bump.

<!-- TEMPLATE — one bullet per override, with provenance:
- **<what the protocol says>** → **<what THIS project does instead>** —
  <why> (set by <user/agent>, YYYY-MM-DD)

Example:
- **Push to main after each commit** → **push to the `develop` branch;
  main is release-only** — repo uses git-flow (set by user, 2026-07-14)
-->

*(none yet)*

- **`kickoff.md` Step 1 — `sh .context/core/bin/context-sync verify`** → **On Windows, skip the `sh context-sync` commands and verify integrity manually via PowerShell** — `context-sync` is POSIX-only (`sha256sum`/`shasum`/`sh` are not on Windows PATH). Replace with:
  ```powershell
  # Verify: compare SHA256 of every file in .context/core/ against its MANIFEST.sha256
  $manifest = Get-Content ".context/core/MANIFEST.sha256"
  $fail = $false
  foreach ($line in $manifest) {
    $hash, $path = $line -split '\s+', 2
    $path = $path.TrimStart('*').TrimStart(' ')
    $actual = (Get-FileHash ".context/core/$path" -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $hash.ToLower()) { Write-Warning "MISMATCH: $path"; $fail = $true }
  }
  if (-not $fail) { Write-Host "CORE INTEGRITY PASSED" }
  ```
  ```powershell
  # Status: check core version + git log
  Get-Content ".context/core/VERSION" | Select-Object -First 1
  git log --oneline -5 -- .context/core/
  ```
  (set by agent, 2026-07-20)

- **`kickoff.md` Step 1 — `git pull --ff-only`** → **No change needed** — git works fine from PowerShell on Windows. (set by agent, 2026-07-20)
