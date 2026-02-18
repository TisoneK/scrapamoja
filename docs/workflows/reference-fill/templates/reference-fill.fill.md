---
description: Fill mode for reference file filling workflow
---

# Fill Mode - Fill Reference Files with HTML Samples

This mode guides users through collecting real HTML samples from Flashscore and filling reference files according to templates.

## Quick Flow

1. **Check status** → See which files need filling
2. **Select file** → Choose a target file
3. **Check if complete** → Skip if already done
4. **Ask 6 questions** → Get URL, Country, League, Teams, HTML
5. **Validate & Generate** → Check HTML, save file
6. **Next file** → Repeat

---

## Steps

### Step 1: Check Status Tracker
Read: `docs/workflows/reference-fill/status.json`

⚠️ **IMPORTANT:** Also read `docs/workflows/reference-fill/rules.md` to refresh memory on LLM behavior rules.

Skip any files already marked "completed".

### Step 2: Select File
```
Which reference file would you like to fill?

{present list from discovery}

Please select a number or I can suggest one.
```

⚠️ GATE: Wait for user answer.

### Step 3: Read Target File
Verify file status using scanner:
```powershell
powershell -ExecutionPolicy Bypass -File ".\docs\workflows\reference-fill\scripts\pwsh\scanner.ps1" -ShowContent "{REPLACE_WITH_RELATIVE_PATH}"
```

Where `{REPLACE_WITH_RELATIVE_PATH}` is the path relative to `docs/references/flashscore/html_samples/`.

For example, if selected file is `docs/references/flashscore/html_samples/live/basketball/odds/secondary.md`, use `live/basketball/odds/secondary.md`.

⚠️ CHECK: Does scanner show "NEEDS FILL"?
- YES → Continue to Step 4
- NO (shows "COMPLETE") → Tell user "Already complete!" → Skip to Step 7

### Step 4: Ask Questions (One at a time)

⚠️ **Remember rules:** Re-read `docs/workflows/reference-fill/rules.md` if you forget how to handle answers.

**Q1 - Source URL:****
```
What is the Source URL?
Example: https://www.flashscore.com/match/basketball/teamA-teamB/?mid=12345
```
⚠️ GATE

**Q2 - Country:**
```
What Country is the match from?
```
⚠️ GATE

**Q3 - League:**
```
What League?
```
⚠️ GATE

**Q4a - Home Team:**
```
What is the Home Team name?
```
⚠️ GATE

**Q4b - Away Team:**
```
What is the Away Team name?
```
⚠️ GATE

**Q5 - HTML:**
```
Provide the HTML content (outerHTML) for the [tab name] tab.

Steps:
- Go to: {source_url}
- Find tab: [TAB NAME IN UPPERCASE]
- Right-click → Inspect → Copy → Copy outerHTML
- Paste here
```
⚠️ GATE

### Step 5: Validate & Generate

⚠️ **Check rules:** If unsure, re-read `docs/workflows/reference-fill/rules.md` before validating.

**Check for mismatches:**
- Match state: Scheduled/Live/Finished
- Tab level: Primary/Secondary

If mismatch detected → Ask user: "HTML doesn't match target. Provide correct, use anyway, or start over?"

Then ask confirmation: "Generate {filename}?"

⚠️ GATE

After confirmed → Generate and save file.

⚠️ **IMPORTANT:** Remove `<!-- NEEDS_FILL -->` marker from generated file (since it's now complete).

### Step 6: Next File

⚠️ **Refresh memory:** Re-read `docs/workflows/reference-fill/rules.md` before continuing if needed.

Repeat from Step 2 for next file in queue.

---

## Question Reminders

When asking Q5 (HTML), replace:
- `[tab name]` → actual tab name (Summary, Odds, etc.)
- `[TAB NAME IN UPPERCASE]` → SUMMARY, ODDS, etc.

Selectors:
- Primary tabs: `data-testid="wcl-tabs" data-type="primary"`
- Secondary tabs: `data-testid="wcl-tabs" data-type="secondary"`

## Go Back

At confirmation (Step 5), user can:
- Yes → Generate
- No → Go back to correct a question (1-6)
