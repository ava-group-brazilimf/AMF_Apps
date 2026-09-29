# Agent Development Tasks: Unified Business Rules & Functional Requirements Artifact

**Plan**: `specs/026-unified-business-rules-artifact/plan.md`
**Change Type**: `modify-existing` | **Phase**: `F1` + cross-cutting | **Module**: `asis-diagnostic`

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Category 4 is N/A (no new agents). Category 5 is N/A (no new gate checklist items).
> Categories 3, 6, and 7 can run in parallel after Category 2 completes.

---

## Category 1 — Output Contract & Version Bumps

Must complete before any other category. Establishes the new contracts both agents commit to.

- [X] **1.1** Update `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md` frontmatter: bump version `"1.6.0"` → `"2.0.0"`; update `description` to mention `BRF` trigger and unified `business-rules.md` output
- [X] **1.2** Update `documentation-asis.md` `## Output Contract` table: remove row `functional-requirements.md` (artifact #2); update `business-rules.md` description to `"unified — contains ## Functional Requirements and ## Business Rules sections"`; renumber remaining artifacts (6 total)
- [X] **1.3** [P] Update `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md` frontmatter: bump version `"2.5.0"` → `"2.6.0"`; update `description` to remove reference to `code-business-rules.md` generation
- [X] **1.4** [P] Update `solution-delphi.md` `## Output Contract` section: remove `asis/code-business-rules.md` entry; remove its row from the Output Contract table

---

## Category 2 — Agent Behavior Changes

Depends on Category 1. Largest category — tackle primary agents first, reference-only agents last.

### 2a — `documentation-asis.md` (primary agent — v2.0.0)

- [X] **2.1** Add `BRF` trigger row to the `## Skills & Outputs` table in `documentation-asis.md`: `| BR+FR Combined | BRF | asis/docs/business-rules.md (ambas as seções — escrita atômica) |`
- [X] **2.2** Update `RF` skill row description: `asis/docs/business-rules.md (seção ## Functional Requirements — upsert)`
- [X] **2.3** Update `RN` skill row description: `asis/docs/business-rules.md (seção ## Business Rules — upsert)`
- [X] **2.4** Add `BRF` trigger execution block (after the `RF` and `RN` skill definitions): single-pass atomic write of both sections in order (`## Functional Requirements` first, `## Business Rules` second); runs FR extraction logic (same as RF) then BR mining logic (same as RN) in one pass; calls FR↔value-chain cross-validation before writing
- [X] **2.5** Update `RF` skill execution block: change from "write `functional-requirements.md`" to "upsert `## Functional Requirements` section in `business-rules.md`" using the upsert algorithm from `data-model.md`
- [X] **2.6** Update `RN` skill execution block: change from "write `business-rules.md`" to "upsert `## Business Rules` section in `business-rules.md`" using the upsert algorithm from `data-model.md`
- [X] **2.7** Update `## ALL Trigger — Parallel DAG Execution` section: replace 4-level DAG with 3-level DAG — Level 1: `VC + FT`; Level 2: `BRF + RT` (BRF replaces RF; RN level eliminated); Level 3: `PR` (depends on RT + BRF)
- [X] **2.8** Update `## FR Module Cross-Validation (RF skill)` section: adapt step 5 ("Re-gravar `functional-requirements.md` via Write") → "Re-gravar a seção `## Functional Requirements` de `business-rules.md` via Write usando upsert"
- [X] **2.9** Update `## Output Verification` section: verify 6 artifacts (not 7); replace `functional-requirements.md` check with a check that `business-rules.md` contains both `## Functional Requirements` and `## Business Rules` sections when trigger = ALL or BRF
- [X] **2.10** Update `## Pre-Completion Validation Checklist`: remove `functional-requirements.md` item; replace with "Quando trigger = ALL ou BRF: `business-rules.md` contém ambas as seções"; update artifact count from 7 to 6

### 2b — `solution-delphi.md` (secondary agent — v2.6.0)

- [X] **2.11** Update `solution-delphi.md` Step 3 `## 🔒 BusinessRuleRegistry` block: remove the sentence "Ao final, o agente DEVE ter produzido o `BusinessRuleRegistry[]`, escrito em `asis/code-business-rules.md`"; retain the registry in memory for internal use but remove the file-write directive
- [X] **2.12** Update `solution-delphi.md` Step 14 `## Write Diagram Outputs`: remove `code-business-rules.md` from the write list; update the step note "Escrever também, neste mesmo passo, os outputs não-diagrama produzidos nos Steps anteriores" to remove `asis/code-business-rules.md` reference
- [X] **2.13** Update `solution-delphi.md` `## Input Contract` table: remove the `Business Rules (código)` row (the `01_business_rules.json` → `code-business-rules.md` mapping); the raw JSON artifact is still used internally (Step 3) but no longer produces a file output

### 2c — Orchestrator & workflow agents

- [X] **2.14** Update `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md` Phase B dispatch rules: replace `{ trigger: "VC✓", dispatch: doc:RF, ... }` + `{ trigger: "RF✓", dispatch: doc:RN, deps: functional-requirements.md }` with `{ trigger: "VC✓", dispatch: doc:BRF, blocking: true, deps: value-chain.md }`; replace `{ trigger: "RF✓ + RN✓", dispatch: bridge-fastqa }` with `{ trigger: "BRF✓", dispatch: bridge-fastqa, blocking: false }`
- [X] **2.15** Update all remaining `functional-requirements.md` references in `orchestrator-asis.md` (lines ~640, 1286, 1446, 1530, 1537, 2007): replace path with `docs/business-rules.md`; update any contextual descriptions (e.g., "extrair módulos de functional-requirements.md" → "extrair módulos da seção ## Functional Requirements de business-rules.md")

### 2d — Downstream reference-only agents (Input Contract path updates)

- [X] **2.16** [P] Update `src/modules/ava-fabric-agents/tobe-architecture/agents/adr-tobe.md`: replace `functional-requirements.md` references in Input Contract with `asis/docs/business-rules.md` (seção `## Functional Requirements`)
- [X] **2.17** [P] Update `src/modules/ava-fabric-agents/tobe-architecture/agents/architecture-decision-matrix-tobe.md`: same path update in Input Contract
- [X] **2.18** [P] Update `src/modules/ava-fabric-agents/tobe-architecture/agents/architecture-design-tobe.md`: replace all `functional-requirements.md` occurrences in Input Contract and READ directives with `asis/docs/business-rules.md`
- [X] **2.19** [P] Update `src/modules/ava-fabric-agents/tobe-architecture/agents/docs-tobe.md`: same path update in Input Contract
- [X] **2.20** [P] Update `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`: replace `functional-requirements.md` Input Contract entry with `asis/docs/business-rules.md`
- [X] **2.21** [P] Update `src/modules/ava-fabric-agents/qa-agents/agents/behavior-mapping-agent.md`: replace `functional-requirements.md` Input Contract path
- [X] **2.22** [P] Update `src/modules/ava-fabric-agents/qa-agents/agents/exploratory-agent.md`: replace `functional-requirements.md` Input Contract path
- [X] **2.23** [P] Update `src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md`: update verification step (line ~2007 pattern) from `functional-requirements.md` to `business-rules.md`
- [X] **2.24** [P] Update `src/modules/ava-fabric-agents/qa-agents/agents/test-case-generator-agent.md`: replace `functional-requirements.md` reference in Input Contract

### 2e — Coder agents (code-business-rules.md fallback removal)

- [X] **2.25** [P] Update `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`: remove `READ asis/code-business-rules.md` line and its "SE code-business-rules.md existir: usar como fonte AUTORITATIVA" block; update BLOCKED message to reference only `asis/docs/business-rules.md`
- [X] **2.26** [P] Update `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`: same removal pattern as 2.25
- [X] **2.27** [P] Update `src/modules/ava-fabric-agents/tech-stack/agents/coder-go-backend.md`: same
- [X] **2.28** [P] Update `src/modules/ava-fabric-agents/tech-stack/agents/coder-java-backend.md`: same
- [X] **2.29** [P] Update `src/modules/ava-fabric-agents/tech-stack/agents/coder-python-backend.md`: same

### 2f — FastQA bridge

- [X] **2.30** [P] Update `src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md`: update exclusion note — replace `functional-requirements.md` reference with `business-rules.md` (unified artifact)

---

## Category 3 — Shared Contracts & Summary Scripts

Can run parallel with Category 6 and 7 after Category 2 completes.

### 3a — Shared markdown contracts

- [X] **3.1** Update `src/modules/ava-fabric-agents/asis-diagnostic/shared/parser-contracts.md`: rename section `## functional-requirements.md` → `## Functional Requirements section (within business-rules.md)`; add note: "A partir da spec-026, o conteúdo de requisitos funcionais reside na seção `## Functional Requirements` de `asis/docs/business-rules.md`"; preserve all existing format invariants unchanged
- [X] **3.2** [P] Update `src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md`: remove `| Functional Requirements | asis/docs/functional-requirements.md |` row from the Documentation Agent table; update `business-rules.md` row description to "(unified — inclui ## Functional Requirements e ## Business Rules)"
- [X] **3.3** [P] Update `src/modules/ava-fabric-agents/asis-diagnostic/shared/artifact-size-governance.md`: update size rules section for `functional-requirements.md` — replace with note that FR content is now part of `business-rules.md` (inherits 300 KB soft / 600 KB hard limit and partition-by-domain strategy)
- [X] **3.4** [P] Update `src/modules/ava-fabric-agents/asis-diagnostic/workflows/analyze-delphi/steps/step-03-documentation.md`: update expected output list — remove `functional-requirements.md`; update `business-rules.md` description
- [X] **3.5** [P] Update `src/modules/ava-fabric-agents/asis-diagnostic/workflows/analyze-delphi/steps/step-05-consolidation.md`: replace path `outputs/asis/docs/functional-requirements.md` with `outputs/asis/docs/business-rules.md`

### 3b — Summary agent instruction files

- [X] **3.6** [P] Update `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`: update parser reference — replace `functional-requirements.md` with "seção `## Functional Requirements` de `business-rules.md`" in the `funcReqs` parser description
- [X] **3.7** [P] Update `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`: update `functional-requirements.md` reference to `business-rules.md`
- [X] **3.8** [P] Update `src/modules/ava-fabric-agents/summary/workflows/generate-summary/steps/step-01-discover.md`: remove `functional-requirements.md` row from artifact discovery table; add note that FR content is in `business-rules.md`

### 3c — Python summary utility scripts

- [X] **3.9** Update `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` line 169: delete the `{"key": "functional-requirements", "path": "asis/docs/functional-requirements.md"}` entry from the artifact discovery list
- [X] **3.10** [P] Update `build_summary_comprehensive.py` line 2144: remove `"functional-requirements"` from the `FUNC_NAMES` set (the `"business-rules"` entry already covers the unified file)
- [X] **3.11** [P] Update `build_summary_comprehensive.py` line 7215 (call site for `parse_func_reqs`): replace `asis_dir / "docs" / "functional-requirements.md"` with path-fallback logic — attempt `business-rules.md` first, fall back to `functional-requirements.md` for legacy projects
- [X] **3.12** [P] Update `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py` line 77: delete `functional-requirements` entry from artifact discovery list
- [X] **3.13** [P] Update `build_summary_complete.py` lines 949–956 (`parse_functional_requirements()` body): replace hardcoded `asis_dir / "docs" / "functional-requirements.md"` with path-fallback (`business-rules.md` → `functional-requirements.md`)
- [X] **3.14** [P] Update `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` line 300 (`_c2_4()` function): replace `src = ctx.outputs_dir / "asis" / "docs" / "functional-requirements.md"` with path-fallback (`_src_br` if exists else `_src_fr`)
- [X] **3.15** [P] Update `validate_summary.py` lines 2307–2308 (Check C2.4 description): replace "parse_functional_requirements() reads functional-requirements.md" with "parse_func_reqs() reads ## Functional Requirements section from business-rules.md (legacy: functional-requirements.md)"

---

## Category 4 — Module Registration

**N/A** — `modify-existing` change type. No new agents created; `module.yaml` unchanged (both `ava-asis-documentation` and `ava-asis-solution-delphi` already registered).

- [X] **4.1** Confirm `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml` contains entries for both agents (read-only verification, no edits needed)

---

## Category 5 — Quality Gate Checklists

**N/A** — no new pipeline gate items required. The Pre-Completion Validation Checklist inside `documentation-asis.md` is updated in task 2.10 (Category 2).

- [X] **5.1** Verify task 2.10 result: `documentation-asis.md` checklist has exactly 6 artifact items (not 7) and includes a check for dual-section presence in `business-rules.md`

---

## Category 6 — Acceptance Validation

Can run parallel with Category 3 and 7 after Category 2 completes.

- [X] **6.1** Run grep audit to confirm zero remaining `functional-requirements.md` references in agent/script source files (excluding `specs/`): `grep -r "functional-requirements\.md" src/modules/ava-fabric-agents/ --include="*.md" --include="*.py" -l | grep -v specs/` — expected: empty output
- [X] **6.2** [P] Run grep audit to confirm zero remaining `code-business-rules` references in agent/script source files: `grep -r "code-business-rules" src/modules/ava-fabric-agents/ --include="*.md" --include="*.py" -l` — expected: empty output
- [X] **6.3** [P] Run quickstart validation scenario 4 — `parse_func_reqs()` correctly extracts FR entries from the unified `business-rules.md` of an existing project (see `quickstart.md` Scenario 4)
- [X] **6.4** [P] Run quickstart validation scenario 5 — `validate_summary.py` Check C2.4 passes on a project with the unified file (see `quickstart.md` Scenario 5)
- [X] **6.5** [P] Verify `documentation-asis.md` spec scenarios: confirm spec Section 6 Scenarios 1–3 are fully addressed by the changes in Categories 1–2 (trace each acceptance criterion to the task that implements it)

---

## Category 7 — Documentation & Catalog Update

Can run parallel with Categories 3 and 6 after Category 2 completes.

- [X] **7.1** [P] Update `docs/agents-catalog.md`: `ava-asis-documentation` entry → version `2.0.0`, outputs list removes `functional-requirements.md`, adds note "business-rules.md unified (FR + BR)"; `ava-asis-solution-delphi` entry → version `2.6.0`, outputs list removes `code-business-rules.md`
- [X] **7.2** [P] Add `CHANGELOG.md` entry: `## [2.0.0] ava-asis-documentation / [2.6.0] ava-asis-solution-delphi — YYYY-MM-DD` — describe artifact consolidation, new `BRF` trigger, discontinued artifacts, and downstream reference updates
- [X] **7.3** [P] Search `docs/full-pipeline-guide.md` for `functional-requirements.md` or `code-business-rules.md` references; update any found to `business-rules.md` with appropriate section context

---

## Completion Checklist

- [X] All categories complete (Category 4 and 5 verified as N/A)
- [X] `documentation-asis.md` version = `2.0.0`; output contract has 6 artifacts
- [X] `solution-delphi.md` version = `2.6.0`; no `code-business-rules.md` references remain
- [X] Grep audit (6.1) returns empty — zero `functional-requirements.md` refs in source
- [X] Grep audit (6.2) returns empty — zero `code-business-rules.md` refs in source
- [X] `validate_summary.py` C2.4 = PASS on unified file
- [X] `docs/agents-catalog.md` updated for both agents
- [X] `CHANGELOG.md` entry committed

---

## Dependency Graph

```
Category 1 (contracts)
    └─► Category 2a (documentation-asis.md — primary)
    └─► Category 2b (solution-delphi.md — primary)
            └─► Category 2c (orchestrator)
            └─► Category 2d [P] (TO-BE + QA + prototype refs)
            └─► Category 2e [P] (coder agents)
            └─► Category 2f [P] (bridge-fastqa)
                    └─► Category 3 [P] (shared contracts + scripts)
                    └─► Category 6 [P] (validation)
                    └─► Category 7 [P] (docs + catalog)
```

## Parallel Execution Examples

**After Category 1 completes**: 2a and 2b can start simultaneously.  
**After 2a+2b complete**: 2c must precede 2d; 2d/2e/2f can run in parallel.  
**After 2f complete**: Category 3, 6, and 7 are fully independent — all three can run in parallel.  
**Within Category 3**: tasks 3.2–3.15 are all independent and can run simultaneously.

## Implementation Strategy

MVP scope (minimum for pipeline correctness):
1. **Category 1** (version bumps) — 15 min
2. **Category 2a** (documentation-asis.md behavior) — highest complexity; do first
3. **Category 2b** (solution-delphi.md) — straightforward removals
4. **Category 2c** (orchestrator) — critical for correct pipeline dispatch
5. **Category 3c** (Python scripts) — required for summary to work
6. **Category 6.1–6.2** (grep audits) — validates all reference updates complete

Categories 2d/2e/2f, 3a/3b, 7: can follow in parallel once MVP passes grep audit.
