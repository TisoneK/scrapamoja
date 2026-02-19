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

## Issue Tracking Integration

⚠️ **IMPORTANT:** Throughout this workflow, you MUST log issues when:
- User corrects or redirects your behavior
- You make wrong assumptions
- You need multiple clarifications on the same step

**Issue Tracking Files:**
- Template: `docs/workflows/reference-fill/templates/reference-fill.issues.md`
- Database: `docs/workflows/reference-fill/issues.json`

See the Issue Tracking section in `docs/workflows/reference-fill/rules.md` for details.

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

🔍 **ISSUE CHECK:** Did user correct your file selection or suggestion? If YES → Log issue → Continue.

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

**Q1 - Source URL:**
```
What is the Source URL?
Example: https://www.flashscore.com/match/basketball/teamA-teamB/?mid=12345
```
⚠️ GATE
🔍 **ISSUE CHECK:** Did user correct your URL format or question? If YES → Log issue → Continue.

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

**Q4c - Tertiary Tab Check (Secondary Tabs Only):**
```
Does this secondary tab have tertiary sub-tabs?

Steps to verify:
1. Go to: {source_url}
2. Click on: [SECONDARY TAB NAME]
3. Look for: Additional tab navigation below the secondary tab
4. Check for: data-testid="wcl-tabs" data-type="tertiary"

Options:
1. Yes - Tertiary tabs exist (continue to Q5)
2. No - No tertiary tabs (document and skip to Step 7)
3. Unsure - Need help identifying
```
⚠️ GATE

**If "No":** Document the absence and skip to Step 7:
```
## Notes

### Tertiary Tabs
No tertiary tabs exist under this secondary tab. Verified on {date}.
```

**Q5a - Enumerate Tabs:**
```
List all available tabs at this level.

For primary tabs: Summary, Odds, H2H, Standings
For secondary tabs: List sub-tabs under current primary tab
For tertiary tabs: List sub-tabs under current secondary tab

Format:
| # | Tab Name | Status |
|---|----------|--------|
| 1 | [name] | pending |
| 2 | [name] | pending |
...
```
⚠️ GATE - Wait for tab list confirmation

**Q5b - HTML Content (One Tab at a Time):**
```
Now let's collect HTML for each tab one at a time.

**Current Tab:** [TAB NAME]

Steps:
1. Go to: {source_url}
2. Navigate to: [PARENT TAB] → [CURRENT TAB]
3. Wait for tab content to load
4. Right-click on tab navigation → Inspect
5. Find container with data-testid="wcl-tabs"
6. Copy → Copy outerHTML
7. Paste here

Expected selector: {expected_selector}
```
⚠️ GATE - Repeat for each tab

**Progress Tracking:**
After each tab, update the tab list:
| # | Tab Name | Status |
|---|----------|--------|
| 1 | [name] | ✅ collected |
| 2 | [name] | ⏳ current |
| 3 | [name] | pending |

### Step 5: Validate & Generate

⚠️ **Check rules:** If unsure, re-read `docs/workflows/reference-fill/rules.md` before validating.

**Check for mismatches:**
- Match state: Scheduled/Live/Finished
- Tab level: Primary/Secondary

If mismatch detected → Ask user: "HTML doesn't match target. Provide correct, use anyway, or start over?"

Then ask confirmation: "Generate {filename}?"

⚠️ GATE
🔍 **ISSUE CHECK:** Did user reject or correct your generated content? If YES → Log issue → Make correction.

After confirmed → Generate and save file.

⚠️ **IMPORTANT:** Remove `<!-- NEEDS_FILL -->` marker from generated file (since it's now complete).

### Step 5b: Update Status Automatically

After successfully saving the file, run the status updater:

```powershell
powershell -ExecutionPolicy Bypass -File "docs\workflows\reference-fill\scripts\pwsh\status_updater.ps1"
```

**Expected Output:**
```
✅ Status updated
Files completed: X/28
Progress: XX%
```

If status update fails:
- Log warning but continue workflow
- Note: "Status update failed - manual update may be required"

### Step 6: Next File

⚠️ **Refresh memory:** Re-read `docs/workflows/reference-fill/rules.md` before continuing if needed.

Repeat from Step 2 for next file in queue.

---

## Question Reminders

When asking Q5a (Enumerate Tabs):
- For primary tabs: Summary, Odds, H2H, Standings
- For secondary tabs: List sub-tabs under current primary tab
- For tertiary tabs: List sub-tabs under current secondary tab

When asking Q5b (HTML Content):
- Replace `[TAB NAME]` → actual tab name
- Replace `[PARENT TAB]` → parent tab name if applicable
- Replace `{expected_selector}` → appropriate selector

Selectors:
- Primary tabs: `data-testid="wcl-tabs" data-type="primary"`
- Secondary tabs: `data-testid="wcl-tabs" data-type="secondary"`
- Tertiary tabs: `data-testid="wcl-tabs" data-type="tertiary"`

## Go Back

At confirmation (Step 5), user can:
A) Yes → Generate
B) No → Go back to correct a question (1-6)

<!-- ⚠️ GATE: Validate format before sending - MUST be lettered A, B... -->
<!-- 🔍 **CRITICAL CHECK:** Are these options lettered? If not, FIX before sending. -->
