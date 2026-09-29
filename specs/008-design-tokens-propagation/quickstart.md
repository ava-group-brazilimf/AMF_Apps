# Quickstart Validation Guide: Design Tokens Propagation

**Feature**: `008-design-tokens-propagation`
**Date**: 2026-07-08

---

## Prerequisites

- A project with completed F2 TO-BE architecture artifacts (specifically `design-system.md`
  at `projects/{project_name}/outputs/tobe/docs/design-system.md`)
- `ava-prototype` agent must have run, producing wireframes in
  `projects/{project_name}/outputs/tobe/prototype/`
- The Sophia project is the reference case for validation

---

## Validation Scenario 1 — design-tokens.json is exported by prototype

**Setup**: Run `@ava-prototype` against the Sophia project (or any project with `design-system.md`).

**Expected outcomes**:

```
projects/Sophia/outputs/tobe/prototype/
├── index.html                  ← existing
├── demo-script.md              ← existing
├── figma-spec.md               ← existing
├── screen-list.md              ← existing
└── design-tokens.json          ← NEW — must exist after this run
```

**Validate the JSON**:
```powershell
$tokens = Get-Content "projects/Sophia/outputs/tobe/prototype/design-tokens.json" | ConvertFrom-Json
$tokens.schema_version        # → "1.0"
$tokens.generated_by          # → "ava-prototype"
$tokens.layout.sidebar_width  # → non-empty string (e.g. "240px")
$tokens.layout.header_height  # → non-empty string (e.g. "64px")
$tokens.spacing.md            # → non-empty string (e.g. "16px")
$tokens.colors.primary        # → non-empty CSS color string
```

**Pass condition**: All fields present, `schema_version == "1.0"`, no empty strings.

---

## Validation Scenario 2 — Angular agent HARD STOP when tokens absent

**Setup**: Delete (or rename) `design-tokens.json`. Run `@ava-stack-angular-frontend`.

**Expected output**:
```
╔══════════════════════════════════════════════════════════════╗
║  PRE-FLIGHT CHECK — ava-stack-angular-frontend              ║
╠══════════════════════════════════════════════════════════════╣
║  Input Contract                                              ║
║  ❌ prototype_screens: MISSING                               ║
║     → projects/{project_name}/outputs/tobe/prototype/screen-list.md
║  ❌ design_tokens: MISSING                                   ║
║     → projects/{project_name}/outputs/tobe/prototype/design-tokens.json
║                                                              ║
║  DECISION: BLOCKED                                           ║
║  Run ava-prototype first to generate the missing artifacts.  ║
╚══════════════════════════════════════════════════════════════╝
```

**Pass condition**: Zero Angular/TypeScript/SCSS files generated. Message names `ava-prototype`.

---

## Validation Scenario 3 — G-DT guardrail: styles.scss contains token declarations

**Setup**: `design-tokens.json` present. Run `@ava-stack-angular-frontend` for the Sophia project.

**Check generated `styles.scss`**:
```powershell
$scss = Get-Content "projects/Sophia/outputs/tobe/source-code/frontend/src/styles.scss" -Raw
$scss -match ":root"                   # → True
$scss -match "--sidebar-width:"        # → True
$scss -match "--header-height:"        # → True
$scss -match "--spacing-md:"           # → True
```

**Check Sidebar component SCSS** (example path):
```powershell
$sidebar = Get-Content "projects/Sophia/outputs/tobe/source-code/frontend/src/app/shared/sidebar/sidebar.component.scss" -Raw
$sidebar -match "var\(--sidebar-width" # → True
$sidebar -match "240px"                # → False (no hardcoded values outside :root)
```

**Pass condition**: `:root` block present in `styles.scss`; Sidebar/Header components use
`var(--token-name)` syntax; no hardcoded layout dimensions in component SCSS.

---

## Validation Scenario 4 — React stub acknowledges planned input contract

**Setup**: Run `@ava-stack-react-frontend` (stub response).

**Expected**: Response includes a `## Planned Input Contract` section or note referencing
`design-tokens.json`. The stub BLOCKED response is NOT triggered by absent tokens
(stub enforcement is intentionally deferred).

**Pass condition**: Stub response body mentions `design-tokens.json` in a documentation
section.

---

## Schema Validation (Optional — CI)

```bash
npx ajv validate \
  -s specs/008-design-tokens-propagation/contracts/design-tokens.schema.json \
  -d projects/Sophia/outputs/tobe/prototype/design-tokens.json
```

Expected: `data is valid`.
