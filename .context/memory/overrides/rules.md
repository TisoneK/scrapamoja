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

- **~~`kickoff.md` Step 1 — `sh .context/core/bin/context-sync verify`~~** → **SUPERSEDED 2026-08-01 (Session 35):** core **0.4.0+ ships a PowerShell port** — `pwsh -File .context/core/bin/context-sync.ps1 verify|status|update|rollback` — so Windows agents use the port instead of the manual PowerShell verification below. The manual script is kept only as a fallback for a project still on a pre-0.4.0 core. (set by agent, 2026-07-20; superseded by the core 0.4.0 ps1 port, noted 2026-08-01)
  ```powershell
  # Fallback only (pre-0.4.0 core): compare SHA256 of every file in .context/core/ against its MANIFEST.sha256
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
  # Status fallback: check core version + git log
  Get-Content ".context/core/VERSION" | Select-Object -First 1
  git log --oneline -5 -- .context/core/
  ```

- **`kickoff.md` Step 1 — `git pull --ff-only`** → **No change needed** — git works fine from PowerShell on Windows. (set by agent, 2026-07-20)
