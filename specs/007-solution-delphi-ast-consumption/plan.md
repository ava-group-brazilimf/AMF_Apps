# Agent Implementation Plan: Solution Delphi AST Consumption

**Spec**: `specs/007-solution-delphi-ast-consumption/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (1 agent file + 1 shared doc + 1 cross-module doc) |
| **Primary Requirement** | Make `ava-asis-solution-delphi` treat the 8 AST JSON artifacts as its primary knowledge source instead of raw legacy source; remove all native `.drawio` generation |
| **Technical Approach** | Structural rewrite of `solution-delphi.md` (Input Contract, Steps 0/1/3/4/14/15, Output Contract) + narrow, honestly-scoped exceptions where no AST coverage exists |
| **Implementation Status** | Complete. Structural verification done (drawio references reduced to 4 intentional mentions; fence balance confirmed balanced). |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded.
- [x] **Article II** — frontmatter unchanged except version bump; no new/removed fields.
- [x] **Article V** — pt-BR body content preserved throughout all edits.
- [x] **Article VI** — BDD scenarios (CA01-CA04) cover success, new-artifact wiring, degraded fallback, and drawio removal.
- [x] **Article X (SemVer)** — MAJOR bump (`1.4.0` → `2.0.0`), correctly reflecting a breaking Output Contract change (`.drawio` artifacts removed).
- [x] No `[NEEDS CLARIFICATION]` markers.

## Technical Context

Pure Markdown/prose edits to one agent instruction file plus two dependent
shared docs. No code changes — `run_delphi_ast_analysis.py` and the external
`ava-fabric-delphi-analyzer` tool are consumed as-is, unmodified. No new
dependencies.

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
Confirmed the AST pipeline's real architecture (thin wrapper → external
tool → 8 JSON files), the file's pre-existing partial/uncommitted wiring
(6 of 8 files, optional/non-blocking), and verified all 8 JSON schemas
against a real sample run rather than assuming them (research.md §1-3).

### Phase 1 — Gap Analysis ✅ CONCLUÍDO
Cross-checked every one of Steps 1-14's sub-analyses against the 8 schemas
to determine, honestly, which steps can fully retire raw source reading
(Step 1, Step 3, Step 4 Analysis #4) versus which structurally cannot
(Step 2's `.dpr`, Steps 5/8/11/13's Grep-only analyses) because no AST/JSON
coverage exists today (research.md §4).

### Phase 2 — Agent Redesign ✅ CONCLUÍDO
Rewrote `solution-delphi.md`: new `## Input Contract` section; Step 0
reframed as primary-source/degrade-not-block with a new
`AST_UNAVAILABLE_DEGRADED_ANALYSIS` flag; Step 1 redesigned around
`08_code_overview.json.payload.classes`; Step 3 gained
`BusinessRuleRegistry[]` + `asis/code-business-rules.md`; Step 4 Analysis #4
rewired to `02_form_business_rules.json` with a new `FIELD_VALIDATION_IN_UI`
flag; Step 2 documented as a narrow, explicit exception.

### Phase 3 — `.drawio` Removal ✅ CONCLUÍDO
Deleted: `DRAWIO_EOF` example, the dead commented-out "Diagram Builder
Drawio" skill block, the `.drawio` column/rows in Steps 14/15, the
`.drawio`-specific invariants and Diagrams Creation Mandate bullets, and the
entire "Draw.io Templates" section. De-risked by confirming
`generate_drawio_from_mermaid.py` already synthesizes consolidated `.drawio`
views downstream from `.mmd` (research.md §5).

### Phase 4 — Dependent Docs Reconciliation ✅ CONCLUÍDO
`shared/output-paths.md`'s Solution Agent table split into Delphi
(AST-based, `.mmd`-only, `code-business-rules.md`) vs. VB6 (unchanged,
`.drawio` rows annotated `(VB6 only)`). `docs/asis-diagnostic-io-map.md`
updated to match.

### Phase 5 — Verification ✅ CONCLUÍDO
See `quickstart.md`. Structural checks only — this is a prose instruction
file, not executable code, so no live pipeline run is possible in this
session.

## Complexity Tracking

| Item | Status |
|---|---|
| Partial AST coverage (Steps 5, 8, 11 partial, 13) | Honestly documented as a real limitation of today's external tool's scope, not glossed over — these remain Grep-based targeted scans |
| `.dpr` bootstrap exception | Narrow and explicit — one small project file, not a loophole reopening the "read the whole codebase" pattern this PBI closes |
| Naming collision risk (`code-business-rules.md` vs. `docs/business-rules.md`) | Checked directly against `output-paths.md`; deliberately distinct names, distinct sources (code-mined vs. doc-mined) |
| `solution-vb.md` left un-migrated | Explicitly out of scope — no Delphi-AST-equivalent tool exists for VB6 today; flagged as a natural follow-up, not silently inconsistent |

## Test Strategy

| Test | Command | Result |
|---|---|---|
| No unintentional `.drawio` generation instructions remain | `grep -c drawio solution-delphi.md` | 4 (all confirmed intentional — explanatory/pointer mentions only) |
| Both previously-unused JSON files now referenced | `grep -n '01_business_rules.json\|02_form_business_rules.json' solution-delphi.md` | Present in Step 3 and Step 4 respectively |
| No naming collision | Manual diff of `output-paths.md`'s Solution Agent vs. Documentation Agent tables | `code-business-rules.md` ≠ `docs/business-rules.md`, confirmed distinct |
| Fence balance | Per-file `` ``` `` parity check on `solution-delphi.md` | Balanced |
| Heading structure intact | Manual re-verification of `##`/`###` hierarchy after all deletions | Clean |
