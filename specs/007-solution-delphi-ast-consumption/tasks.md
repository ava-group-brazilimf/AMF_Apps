# Agent Development Tasks: Solution Delphi AST Consumption

**Plan**: `specs/007-solution-delphi-ast-consumption/plan.md`
**Status**: Implementation and verification complete.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm frontmatter version bump matches the breaking Output Contract change
  ```bash
  grep -n '^version:' src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
  ```
  **Result**: `"2.0.0"`.

## Category 2 — Implementation

- [x] **2.1** Add `## Input Contract` section (8 JSON files + `.dpr` exception + degraded fallback) — DONE
- [x] **2.2** Reframe Step 0 as primary source + `AST_UNAVAILABLE_DEGRADED_ANALYSIS` flag — DONE
- [x] **2.3** Redesign Step 1 to derive inventory from `08_code_overview.json` (Glob as fallback only) — DONE
- [x] **2.4** Document Step 2's `.dpr` read as a narrow, explicit exception — DONE
- [x] **2.5** Wire `01_business_rules.json` into Step 3 → `BusinessRuleRegistry[]` → `code-business-rules.md` — DONE
- [x] **2.6** Wire `02_form_business_rules.json` into Step 4 Analysis #4 → `FIELD_VALIDATION_IN_UI` flag — DONE
- [x] **2.7** Remove `DRAWIO_EOF` example + dead "Diagram Builder Drawio" skill block — DONE
- [x] **2.8** Remove `.drawio` column/rows/invariants from Steps 14 and 15 — DONE
- [x] **2.9** Remove `.drawio` bullets from Diagrams Creation Mandate — DONE
- [x] **2.10** Delete entire `## Draw.io Templates` section — DONE
- [x] **2.11** Sync `--version` literal in the (unrelated, untouched-logic) FASE OBRIGATÓRIA block to `2.0.0` — DONE
- [x] **2.12** Fix duplicate `---` divider left by the Draw.io Templates deletion — DONE

## Category 3 — Schema Updates — SKIP

No JSON schema changes; this PBI only consumes existing, already-produced
artifacts.

## Category 4 — Module Registration — SKIP

No `module.yaml` change; `change type` is `modify-existing`, same agent ID.

## Category 5 — Quality Gate Checklists

- [x] **5.1** Confirm zero unintentional `.drawio` generation instructions remain
  ```bash
  grep -c drawio src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
  ```
  **Result**: `4` (all confirmed intentional/explanatory).

- [x] **5.2** Confirm fence balance
  **Result**: balanced.

- [x] **5.3** Confirm heading structure intact (`## Input Contract` present, `## Draw.io Templates` absent)
  **Result**: confirmed.

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — AST-primary, minimal raw-source reading — PASS
- [x] **6.2** CA02 — both previously-unwired files now wired, no naming collision — PASS
- [x] **6.3** CA03 — degraded-not-blocked fallback intact — PASS
- [x] **6.4** CA04 — no `.drawio` files produced by this agent — PASS

## Category 7 — Documentation

- [x] **7.1** `shared/output-paths.md` — Solution Agent table split Delphi vs. VB6 — DONE
- [x] **7.2** `docs/asis-diagnostic-io-map.md` — solution-delphi section updated (AST inputs, no `.drawio` output) — DONE
- [x] **7.3** This spec-kit documentation (spec/plan/research/data-model/quickstart/tasks/checklist) — DONE

## Completion Checklist

- [x] `solution-delphi.md` structurally verified sound (fence balance, heading structure, drawio count)
- [x] Both previously-unused JSON files (`01_business_rules.json`, `02_form_business_rules.json`) now wired in
- [x] No `.drawio` generation instructions remain in this agent
- [x] Dependent docs (`output-paths.md`, `asis-diagnostic-io-map.md`) reconciled
- [x] `solution-vb.md` explicitly left out of scope, not silently inconsistent
