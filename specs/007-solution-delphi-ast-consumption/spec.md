# Agent Specification: Solution Delphi — AST JSON Consumption

**Feature Branch**: `007-solution-delphi-ast-consumption`
**Created**: 2026-07-06
**Status**: Implemented
**Change Type**: modify-existing (`ava-asis-solution-delphi`, MAJOR — breaking Output Contract change)
**Input**: "Feature: Consumir arquivos gerados pelo AST para interpretação do LLM. Objetivo: Adequar o agente de solution-delphi para consumir os arquivos gerados pelo AST... Os diagrams devem ser gerados conforme o contexto (somente .mmd). Remover a geração de diagramas em .drawio."

---

## 1. Agent Identity

| Field              | Value                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| **Agent ID** | `ava-asis-solution-delphi`                                                                                              |
| **Version**  | `1.4.0` → `2.0.0` (MAJOR — Output Contract change: `.drawio` artifacts removed, `code-business-rules.md` added) |
| **Phase**    | F1                                                                                                                        |
| **Module**   | `asis-diagnostic`                                                                                                       |
| **File**     | `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md`                                               |

> Change type is `modify-existing` — no new agent created, no `module.yaml` change.

## 2. Problem Statement

An external AST analysis tool (`ava-fabric-delphi-analyzer`, using the real
`DelphiAST` parser for `.pas` + regex fallback for `.dfm`) is already wired
into this repo via `src/modules/ava-fabric-agents/asis-diagnostic/utils/run_delphi_ast_analysis.py`,
producing 8 deterministic JSON files under
`projects/{project_name}/outputs/asis/delphi-ast-raw/extraction/`:
`01_business_rules.json`, `02_form_business_rules.json`, `03_database_rules.json`,
`04_database_schemas.json`, `05_procedures.json`, `06_integrations.json`,
`07_apis.json`, `08_code_overview.json` (verified against a real sample run
at `projects/Meu-ERP-006-AST-LLM/outputs/asis/delphi-ast-raw/`).

`solution-delphi.md` already had **partial, uncommitted** wiring for 6 of
these 8 files as an optional, non-blocking enhancement: Steps 3, 6, 7, 9, 10,
12 used the JSON as a primary source when available; every step fell back
100% to raw `Glob`/`Grep`/`Read` over the legacy source otherwise — the
actual default for most of the pipeline. `01_business_rules.json` and
`02_form_business_rules.json` were never referenced anywhere.

The user asked to complete and harden this: rely on the 8 JSON files as the
agent's primary knowledge base (so the LLM isn't loading the whole legacy
codebase into context to do its job), wire in the two unused files, and
remove all native `.drawio` diagram generation (Mermaid `.mmd` only).

## 3. Decision

1. **Step 0 (AST extraction) reframed** from "additive optional enhancement"
   to "primary source, degrade-not-block" — same non-blocking philosophy
   (never hard-fail delivery), but explicit that JSON consumption is the
   intended path, with a new `AST_UNAVAILABLE_DEGRADED_ANALYSIS` risk flag
   when it's unavailable, instead of silently treating both paths as
   equally normal.
2. **`01_business_rules.json`** wired into Step 3 (alongside the existing
   `ClassRegistry[]`) as a new `BusinessRuleRegistry[]`, feeding a **new
   output artifact** `asis/code-business-rules.md` — deliberately named to
   avoid a real collision with `ava-asis-documentation`'s existing
   `asis/docs/business-rules.md` (doc-mined, different source).
3. **`02_form_business_rules.json`** wired into Step 4's Analysis #4 (VCL
   Lifecycle & UI Coupling — previously Grep-only, no JSON coverage),
   enriching `vcl-lifecycle-map.md` and adding a new `FIELD_VALIDATION_IN_UI`
   risk flag.
4. **Step 1 (Repository Inventory) redesigned**: when Step 0 succeeds, the
   Forms/DataModules/Units inventory is derived from
   `08_code_overview.json.payload.classes` (grouped by `file`, Form/DataModule
   inferred from the `parent` chain) instead of a `Glob` file-system scan.
   `Glob` remains the fallback only.
5. **Step 2 (`.dpr` bootstrap) — one narrow, explicitly-accepted exception**:
   neither `DelphiAST` nor any of the 8 JSON schemas capture `.dpr`-level
   `Application.CreateForm` order (AST covers `.pas` only). This step still
   reads the single `.dpr` file directly — documented as an accepted,
   minimal exception (one small project file), not a loophole.
6. **Steps 5, 8, 11 (partial), 13** have no AST coverage today (no schema
   covers global-state detection, threading, generic hardcoded-value
   detection, or file-export patterns) — remain `Grep`-based targeted
   pattern scans, explicitly distinguished from full-file `Read`.
7. **All `.drawio` generation removed**: the `DRAWIO_EOF` example, the
   already-dead commented-out "Diagram Builder Drawio" skill block, the
   `.drawio` column/consolidated-file row in Step 14, the `.drawio`-specific
   invariants (Step 14, Diagrams Creation Mandate), the `.drawio` column and
   placeholder in Step 15, and the entire "Draw.io Templates" section — all
   deleted. De-risked by a confirmed existing mechanism:
   `src/modules/ava-fabric-agents/summary/utils/generate_drawio_from_mermaid.py`
   already synthesizes consolidated `.drawio` views **from `.mmd` files** at
   Summary-build time ("REUSE: Zero code duplication — uses existing .mmd
   files") — no downstream capability is lost, it just moves to the correct,
   non-duplicated layer.
8. **New formal `## Input Contract` section** added (previously missing
   entirely) enumerating the 8 JSON files, the narrow `.dpr` exception, and
   the degraded fallback.
9. **`shared/output-paths.md`** updated: Delphi's row set now omits
   `.drawio`, adds `Code Business Rules`; VB6's `.drawio` rows remain
   (unaffected, separate agent, no AST integration yet).
10. **Scope**: `solution-delphi.md` only. `solution-vb.md` has near-identical
    `.drawio` scaffolding but no AST tool integration (DelphiAST is
    Delphi-specific) — explicitly out of scope, flagged as a natural
    follow-up.

## 4. Functional Changes by Component

See `research.md` for the full JSON schema reference and `data-model.md` for
the per-file structure. Summary of file-level changes in `solution-delphi.md`:

| Section                                        | Change                                                                                                                                        |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontmatter                                    | `version: "1.4.0"` → `"2.0.0"`                                                                                                           |
| PRE-WRITE VALIDATION GATE                      | Removed`DRAWIO_EOF` example and `drawio-governance.md` link; added note pointing to the downstream `.mmd`→`.drawio` synthesis script |
| VCL Lifecycle & UI Coupling Analyzer           | Added`FIELD_VALIDATION_IN_UI` flag + `02_form_business_rules.json` as primary source                                                      |
| Análise Estática                             | Added**Business Rules Extractor** skill (`01_business_rules.json` → `code-business-rules.md`)                                      |
| (dead code) Diagram Builder Drawio             | Commented-out block deleted outright                                                                                                          |
| New`## Input Contract`                       | Added — 8 JSON files,`.dpr` exception, degraded fallback                                                                                   |
| Step 0                                         | Reframed as primary source; added`AST_UNAVAILABLE_DEGRADED_ANALYSIS` flag                                                                   |
| Step 1                                         | AST-derived inventory (primary) vs.`Glob` (fallback)                                                                                        |
| Step 2                                         | Documented as a narrow, accepted exception                                                                                                    |
| Step 3                                         | Added`BusinessRuleRegistry[]` construction                                                                                                  |
| Step 4 table                                   | Analysis#4 row updated with new flag + JSON source                                                                                            |
| Step 14                                        | `.drawio` column/row/instructions removed; `code-business-rules.md` writing added                                                         |
| Output Contract                                | Updated: no`.drawio`; `code-business-rules.md` declared                                                                                   |
| Diagrams Creation Mandate                      | `.drawio` references removed                                                                                                                |
| Step 15                                        | `.drawio` column/placeholder removed                                                                                                        |
| `## Draw.io Templates`                       | Entire section deleted                                                                                                                        |
| `## FASE OBRIGATÓRIA` (unrelated prior PBI) | **Untouched** except syncing the `--version` literal to `2.0.0` for consistency                                                     |

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — AST succeeds: JSON is primary, minimal source reading (CA01)

**Given** `run_delphi_ast_analysis.py` succeeds and all 8 JSON files exist,
**When** the agent runs Steps 1, 3, and Step 4 Analyses #4/#6/#7/#9/#10/#12,
**Then** it consumes the JSON files as primary source and does not `Glob`/`Read`
the corresponding raw `.pas`/`.dfm` files for those analyses — the only
direct source read remaining is the single `.dpr` file in Step 2.

### Scenario 2 — Two previously-unwired files now produce real output (CA02)

**Given** Step 0 succeeded, **When** Step 3 runs, **Then**
`asis/code-business-rules.md` is produced from `01_business_rules.json`, and
`asis/vcl-lifecycle-map.md` includes `FIELD_VALIDATION_IN_UI` findings
sourced from `02_form_business_rules.json`, without colliding with
`ava-asis-documentation`'s existing `asis/docs/business-rules.md`.

### Scenario 3 — AST fails: degraded, not blocked (CA03)

**Given** Step 0 fails or the AST tool isn't configured, **When** the agent
continues, **Then** it records `AST_UNAVAILABLE_DEGRADED_ANALYSIS`, still
delivers all outputs via `Grep`/`Read` fallback (except `FIELD_VALIDATION_IN_UI`,
which has no Grep equivalent and is explicitly noted as absent), and does
**not** block delivery.

### Scenario 4 — No `.drawio` files are produced (CA04)

**Given** any successful run, **When** Step 14/15 complete, **Then** only
`.mmd` diagram files exist under `outputs/asis/diagrams/` — no `.drawio`
files are written by this agent.

## 6. Quality Gate Requirements

- [X] Agent ID unchanged, frontmatter contains only the 4 allowed fields (Article II)
- [X] Version bump is MAJOR, matching a real Output Contract change (Article X)
- [X] BDD scenarios cover success, new-artifact wiring, degraded fallback, and the drawio-removal outcome (Article VI)
- [X] No technology versions hardcoded (Article I)
- [X] No `[NEEDS CLARIFICATION]` markers remain

## 7. Dependencies

- `src/modules/ava-fabric-agents/asis-diagnostic/utils/run_delphi_ast_analysis.py` (already exists, unmodified by this PBI)
- The external `ava-fabric-delphi-analyzer` tool (outside this repo) that the wrapper script shells out to
- `src/modules/ava-fabric-agents/summary/utils/generate_drawio_from_mermaid.py` (already exists, unmodified — the downstream `.drawio` synthesis path that makes native removal safe)

## 8. Exclusions

- `solution-vb.md` and the 3 stub solution agents (`-cobol`, `-vbnet`, `-powerbuilder`) — unaffected, no AST tool integration for those legacy technologies today.
- `run_delphi_ast_analysis.py` itself — not modified; already functionally correct and tested (per prior sample run).
- No live pipeline execution possible from this session (this is a prose instruction file, not executable code) — verification is structural/documentary only.

## 9. Assumptions

- The external AST analyzer's 8-file JSON schema is stable (verified against one real sample run, not a formal published schema contract with the external tool).
- Steps 5, 8, 11 (partial), 13 genuinely have no AST-tool coverage today (confirmed against the real sample run's JSON contents) — full elimination of source-reading isn't 100% achievable with the current external tool's scope, and this is stated honestly rather than implied otherwise.

## Success Criteria

| Criterion                                  | Measure                                                                                                                                                                                      |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No`.drawio` generation remains           | Grep confirms zero`--model`-style hardcoded `.drawio` write instructions in `solution-delphi.md` (only 4 explanatory mentions remain, all pointing to the downstream synthesis script) |
| Both previously-unused JSON files wired in | `01_business_rules.json` → Step 3/`code-business-rules.md`; `02_form_business_rules.json` → Step 4 Analysis #4                                                                       |
| No artifact-name collision                 | `asis/code-business-rules.md` ≠ `asis/docs/business-rules.md`                                                                                                                           |
| Formal Input Contract exists               | New`## Input Contract` section present, enumerating all 8 JSON files + the `.dpr` exception                                                                                              |
| `output-paths.md` reconciled             | Delphi row set has no`.drawio`, has `Code Business Rules`; VB6 rows unaffected                                                                                                           |
| Structural integrity                       | Fence balance and heading structure verified after all edits                                                                                                                                 |
