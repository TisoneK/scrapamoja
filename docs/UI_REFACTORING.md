# UI Refactoring — Consolidate to Single App

## Problem Summary

The `ui/` directory currently contains three folders, two of which are redundant:

```
ui/
├── escalation/               ← orphan fragment, no package.json, not runnable
├── feature-flag-management/  ← stale duplicate, superseded by shared/
└── shared/                   ← the real app, misnamed
```

### `ui/escalation/` — Orphan Fragment

Contains components, one hook, and one page, but is missing everything needed
to run as a standalone app (`package.json`, `vite.config.ts`, `index.html`,
`main.tsx`, `App.tsx`, `tsconfig.json`). Its entire contents are already present
in `ui/shared/src/` — it is an early draft that was absorbed into `shared/` and
never cleaned up.

Duplicate files:

| `ui/escalation/` | `ui/shared/src/` |
|---|---|
| `components/failures/ApprovalPanel.tsx` | `components/failures/ApprovalPanel.tsx` |
| `components/failures/CustomSelectorForm.tsx` | `components/failures/CustomSelectorForm.tsx` |
| `components/failures/FailureDashboard.tsx` | `components/failures/FailureDashboard.tsx` |
| `components/failures/FailureDetailView.tsx` | `components/failures/FailureDetailView.tsx` |
| `components/failures/VisualPreview.tsx` | `components/failures/VisualPreview.tsx` |
| `components/failures/index.ts` | `components/failures/index.ts` |
| `hooks/useFailures.ts` | `hooks/useFailures.ts` |
| `pages/FailuresPage.tsx` | `pages/EscalationPage.tsx` (same logic, renamed) |

### `ui/feature-flag-management/` — Stale Duplicate

An earlier, smaller version of the same app. Every file it contains also exists
in `ui/shared/src/`. `ui/shared/` is the evolved version — it includes everything
`feature-flag-management/` has, plus:

- `components/failures/` (escalation UI)
- `components/AuditLogViewer.tsx`
- `components/FeatureFlagFilters.tsx`
- `hooks/useFailures.ts`, `hooks/useWebSocket.ts`
- `pages/EscalationPage.tsx`
- `App.tsx` with `BrowserRouter` and all three routes

Additional issues with `feature-flag-management/`:

- **Same `package.json` name** as `shared/` (`"feature-flag-management"`)
- **Same `vite.config.ts`** — both bind to port `3000`, they cannot run together
- **No `node_modules/`** — dependencies have never been installed here
- **`App.tsx` missing `BrowserRouter`** — routing would not work

### `ui/shared/` — The Real App, Misnamed

This is the canonical, complete application. It is a fully runnable Vite + React 18
+ TypeScript app with all three features (Feature Flags, Escalation, Audit Log) wired
together. The name `shared/` implies a utility library, which is misleading.

---

## Target Structure

Rename `ui/shared/` to `ui/app/` and delete the two redundant folders.

```
ui/
└── app/
    ├── public/
    ├── src/
    │   ├── api/
    │   │   └── featureFlagApi.ts
    │   ├── components/
    │   │   ├── failures/
    │   │   │   ├── ApprovalPanel.tsx
    │   │   │   ├── CustomSelectorForm.tsx
    │   │   │   ├── FailureDashboard.tsx
    │   │   │   ├── FailureDetailView.tsx
    │   │   │   ├── VisualPreview.tsx
    │   │   │   └── index.ts
    │   │   ├── ui/
    │   │   ├── AuditLogViewer.tsx
    │   │   ├── FeatureFlagFilters.tsx
    │   │   ├── FeatureFlagList.tsx
    │   │   ├── FeatureFlagList.test.tsx
    │   │   └── Layout.tsx
    │   ├── hooks/
    │   │   ├── useFailures.ts
    │   │   ├── useFeatureFlags.ts
    │   │   └── useWebSocket.ts
    │   ├── lib/
    │   ├── pages/
    │   │   ├── AuditLogPage.tsx
    │   │   ├── EscalationPage.tsx
    │   │   └── FeatureFlagsPage.tsx
    │   ├── types/
    │   │   └── featureFlag.ts
    │   ├── utils/
    │   │   └── index.ts
    │   ├── App.tsx
    │   ├── index.css
    │   └── main.tsx
    ├── index.html
    ├── package.json       ← rename to "scrapamoja-ui"
    ├── postcss.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── tsconfig.node.json
    └── vite.config.ts
```

---

## Refactoring Steps

### Step 1 — Check before deleting

Before removing anything, verify no unique file exists in the two redundant
folders that is absent from `ui/shared/src/`:

| Item | Where to check | Risk |
|---|---|---|
| `@radix-ui/react-table` dep | `feature-flag-management/package.json` only | Check if any component in `shared/` imports a table primitive |
| `src/lib/` contents | Both apps have a `lib/` folder | Read both; copy anything unique to `shared/lib/` first |
| `public/` assets | `feature-flag-management/public/` | Check for icons or static files not in `shared/public/` |

### Step 2 — Delete `ui/escalation/`

All contents already exist in `ui/shared/src/`. Nothing needs to be moved first.

```bash
rm -rf ui/escalation/
```

### Step 3 — Delete `ui/feature-flag-management/`

```bash
rm -rf ui/feature-flag-management/
```

### Step 4 — Rename `ui/shared/` to `ui/app/`

```bash
# Linux / macOS
mv ui/shared/ ui/app/

# Windows
rename ui\shared ui\app
```

### Step 5 — Update `package.json` name

In `ui/app/package.json`, change:

```json
"name": "feature-flag-management"
```

to:

```json
"name": "scrapamoja-ui"
```

### Step 6 — Confirm `node_modules/` is gitignored

Check that `.gitignore` includes `node_modules/` or `ui/app/node_modules/`.
The existing `node_modules/` from `ui/shared/` must not be committed.

### Step 7 — Install and smoke-test

```bash
cd ui/app
npm install
npm run dev
```

Open `http://localhost:3000` and confirm all three routes load:

| Route | Expected page |
|---|---|
| `/` or `/feature-flags` | Feature Flags |
| `/escalation` | Escalation / Failures |
| `/audit-log` | Audit Log |

### Step 8 — Run tests

```bash
npm run test
```
