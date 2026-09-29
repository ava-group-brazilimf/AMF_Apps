# Agent Development Tasks: Bridge FastQA AST Simplification

**Plan**: `specs/023-bridge-fastqa-ast-simplification/plan.md`
**Agent ID**: `ava-asis-bridge-fastqa` | **Phase**: `F1` | **Module**: `asis-diagnostic`
**Change type**: modify-existing | **Version bump**: `3.3.0 → 4.0.0` (MAJOR)

> Complete categories sequentially. Mark [P] indicates tasks parallelizable within the same category.

---

## Category 1 — Frontmatter & Contract Definition

Must complete before any other category. Target file: `src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md`

- [X] 1.1 Update YAML frontmatter `version` from `"3.3.0"` to `"4.0.0"` and `date` to `"2026-07-19"` in `src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md`
- [X] 1.2 Replace frontmatter `description` block: remove all references to `functional-requirements`, `business-rules`, `estimate_effort`, `ac_scope_analysis`, `validate_scenarios`; add references to the three AST JSON files and the 16-step lean pipeline (see `data-model.md §A1`)
- [X] 1.3 Update `## Input Contract` section: replace the two mandatory doc-artifact rows + four optional rows with the three AST JSON rows + two-level path resolution table (`compressed/` primary → `extraction/` fallback → hard stop) and add the deprecation note for removed inputs (see `data-model.md §A3`)
- [X] 1.4 Update `## Output Contract` section: remove the three output rows for eliminated steps — `estimate_effort/PBI-{N}_planning.md`, `requirements_analysis/PBI-{N}_ac_scope.md`, `test_cases/PBI-{N}_validation_report.md` (see `data-model.md §A4`)

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1. All subsections target the same file as Category 1.

### 2a — Dependency Gate and AST Reading (Steps 1–3)

- [X] 2.1 Replace `PROCEDURE validate_inputs()` with `PROCEDURE validate_ast_inputs()`: implement two-level path resolution loop over the three AST filenames, populate `resolved` dict, emit `⛔ HARD STOP` block (identifying missing files and both paths checked) when any file is absent, return `resolved` dict on success (see `data-model.md §A5`)
- [X] 2.2 Update Step 1 item 1.2: replace `validate_inputs(project_name)` call with `validate_ast_inputs(project_name)`; store returned `resolved_paths` dict for downstream steps (see `data-model.md §A6`)
- [X] 2.3 Replace Step 2 body entirely: implement three sequential reads of `resolved_paths["01_business_rules.json"]`, `resolved_paths["02_form_business_rules.json"]`, `resolved_paths["03_database_rules.json"]`; for each file parse `payload.*.schema[]` + `payload.*.rows[]` positional arrays and store `business_rules[]`, `forms[]`, `form_event_handlers[]`, `db_rules[]` (see `data-model.md §A7`)
- [X] 2.4 Delete entire "Step 3 — Read Optional Artifacts (enriquecimento)" section (see `data-model.md §A8`)

### 2b — PBI Composition (Steps 4–7)

- [X] 2.5 Update Step 5 items 3–6: replace documentation-artifact derivation with AST-based derivation — modules from `forms[].form_name`, acceptance criteria from `business_rules[]` (BR-NNN), `db_rules[]` (DBR-NNN), and `form_event_handlers[]` (form:), dependencies from shared table prefixes, tech notes from AST counts (see `data-model.md §A9`)
- [X] 2.6 Update the PBI template `## ✅ Critérios de Aceite` block: replace the FR-NNN/BR-NNN scenario template with three scenario templates — one for BR-NNN (calculation/validation), one for DBR-NNN (DB state change), one for form event handler — each with correct `(Fonte: ...)` traceability notation (see `data-model.md §A10`)
- [X] 2.7 Update `## Core Responsibilities` bullets: replace "Ler artefatos obrigatórios (functional-requirements, business-rules)" + "Enriquecer com artefatos opcionais" with AST-reading bullets; remove `estimate_effort` bullet from Elemento 2; replace Elemento 3 bullets to reflect 2-step pipeline without `ac_scope_analysis` and `validate_scenarios` (see `data-model.md §A2`)

### 2c — Lean FastQA Pipeline: Element 2 (Steps 8–12)

- [X] 2.8 Update Element 2 header sequential pipeline description: `load_pbi → identify_gaps → analyze_requirements → map_behaviors` (remove `estimate_effort`) (see `data-model.md §A11`)
- [X] 2.9 Delete entire "Step 10 — Estimate Effort (`@fastqa:estimate_effort`)" section including Dispatch block, Instruções ao agente, and `PROCEDURE validate_estimate_effort` (see `data-model.md §A12`)
- [X] 2.10 Renumber Step 11 → Step 10 (analyze_requirements): update heading, remove `testPlanning` field from Dispatch block and its "Passagem de contexto" item, update `Step 12` back-reference in `validate_analyze_requirements` to `Step 11` (see `data-model.md §A13`)
- [X] 2.11 Renumber Step 12 → Step 11 (map_behaviors): update heading, update all internal step number references in `validate_map_behaviors` (see `data-model.md §A13`)
- [X] 2.12 Renumber Step 13 → Step 12 (Element 2 Checkpoint): update heading, update PROCEDURE comment "Step 11 e Step 12" → "Step 10 e Step 11" (see `data-model.md §A14`)

### 2d — Lean FastQA Pipeline: Element 3 (Steps 13–16)

- [X] 2.13 Update Element 3 header sequential pipeline description: `test_case_with_fastqa → azdo_create_test_plan (local)` (remove `ac_scope_analysis` and `validate_scenarios`) (see `data-model.md §A15`)
- [X] 2.14 Delete entire "Step 14 — AC Scope Analysis (`@fastqa:ac_scope_analysis`)" section (see `data-model.md §A16`)
- [X] 2.15 Renumber Step 15 → Step 13 (test_case_with_fastqa): update heading; remove `ac_scope.md` lookup line from Instruções ao agente dispatch; keep `behaviors_path` reference (see `data-model.md §A17`)
- [X] 2.16 Delete entire "Step 16 — Validate Scenarios (`@fastqa:validate_scenarios`)" section (see `data-model.md §A18`)

### 2e — Lean test-plan.md Template (Step 14)

- [X] 2.17 Renumber Step 17 → Step 14 (Create Test Plan): update heading and "v3.0.0" → "v4.0.0" in description comment (see `data-model.md §A19`)
- [X] 2.18 Replace "Geração de Conteúdo por Seção" numbered list with the new 5-source list: `01_business_rules.json → §2 Domain`, `02_form_business_rules.json → §2 Validators`, `03_database_rules.json → §3 Repository`, all three → `§4 Coverage Map`, fixed → `§1 + §5` (see `data-model.md §A19`)
- [X] 2.19 Replace the full 9-section test-plan.md template (from ` ```markdown ` to closing ` ``` `) with the new 5-section template: §1 Test Strategy, §2 Unit Test Scope (Domain + Validators tables from AST), §3 Integration Test Scope (Repository table from AST), §4 Test Coverage Map (unified traceability table), §5 Test Quality Gates (see `data-model.md §A19`)
- [X] 2.20 Replace "Regras de Preenchimento do Template" mapping table: update all rows to reference AST sources, remove 6 deleted-section rows (Architecture Tests, E2E Tests, Smoke Suite, Load Test, Test Data, removed Application Layer) (see `data-model.md §A19`)
- [X] 2.21 Update `PROCEDURE validate_test_plan` `required_sections` list from 9 items to 5 items: `["## 1. Test Strategy", "## 2. Unit Test Scope", "## 3. Integration Test Scope", "## 4. Test Coverage Map", "## 5. Test Quality Gates"]` (see `data-model.md §A19`)

### 2f — Completion, Observability and Guardrails (Steps 15–16 + global)

- [X] 2.22 Renumber Step 17b → Step 15 (Publish QA Artifacts): update heading only; no other content changes in this step (see `data-model.md §A20`)
- [X] 2.23 Renumber Step 18 → Step 16 (Completion Signal): update heading; remove three status lines for eliminated artifacts (`estimate_effort`, `ac_scope`, `validation_report`) from the signal template; update pipeline trace to `load_pbi → identify_gaps → analyze_requirements → map_behaviors → test_case_with_fastqa → create_test_plan (local)` (see `data-model.md §A21`)
- [X] 2.24 Update FASE OBRIGATÓRIA observability section: change `--version 3.3.0` to `--version 4.0.0` in the `pipeline_observer.py` Bash command (see `data-model.md §A22`)
- [X] 2.25 Update Guardrails section: replace FR-NNN/BR-NNN traceability guardrail with AST-sourced rule IDs (BR-NNN from 01, DBR-NNN from 03, `form:{form_name}` from 02); update step count in "NUNCA emitir" guardrail from `Steps 1-7 + Steps 8-13 + Steps 14-18` to `Steps 1-7 + Steps 8-12 + Steps 13-16`; update size threshold from `5000 bytes` to `3000 bytes`; remove guardrails for `estimate_effort`, `ac_scope_analysis`, `validate_scenarios` from Elemento 2 and 3 sections (see `data-model.md §A23`)
- [X] 2.26 Update FastQA Integration Notes: replace Element 2 pipeline diagram (4 steps, remove `estimate_effort`); replace Element 3 pipeline diagram (2 steps, remove `ac_scope_analysis` and `validate_scenarios`); update Fluxo de Dados table (remove 3 deleted rows, renumber remaining rows) (see `data-model.md §A24`)

---

## Category 3 — Shared Schema Updates

**N/A** — plan section 7 confirms no schema changes. No `agent-task.schema.json` or `agent-result.schema.json` modifications required.

---

## Category 4 — Module Registration

**N/A** — `module.yaml` entry for `ava-asis-bridge-fastqa` already exists. No new agent is registered. No `module.yaml` changes required.

---

## Category 5 — Quality Gate Checklists

- [X] 5.1 Locate `src/modules/ava-fabric-agents/asis-diagnostic/` readiness gate checklist and verify it has no entries referencing `estimate_effort`, `ac_scope_analysis`, or `validate_scenarios` as required bridge-fastqa outputs
- [X] 5.2 [P] Confirm `ava-asis-bridge-fastqa` artifact contract in `orchestrator-asis.md` reflects the updated output set (this will be applied in Category 7 — verify the contract is consistent before marking done)

---

## Category 6 — Acceptance Validation

Depends on Category 2. Run after all file changes are applied.

- [X] 6.1 [P] Run Check 1 from `quickstart.md`: verify removed input references → expect `functional-requirements.md`, `business-rules.md`, `screen-rules.md`, `value-chain.md`, `bounded-context-map` all return 0 matches in `bridge-fastqa-asis.md`
- [X] 6.2 [P] Run Check 2 from `quickstart.md`: verify new AST input references → expect `01_business_rules.json`, `02_form_business_rules.json`, `03_database_rules.json`, `delphi-ast-raw/compressed`, `delphi-ast-raw/extraction` all return ≥ 2 matches
- [X] 6.3 [P] Run Check 3 from `quickstart.md`: verify eliminated pipeline steps → expect `estimate_effort`, `ac_scope_analysis`, `validate_scenarios` all return 0 matches
- [X] 6.4 [P] Run Checks 4–7 from `quickstart.md`: version 4.0.0 present (×1); 5 test-plan template sections; `validate_ast_inputs` and `HARD STOP` present; observability version 4.0.0
- [X] 6.5 Confirm spec §6 Scenario 3 (Hard Stop) is fully implemented: `PROCEDURE validate_ast_inputs` emits the `⛔ HARD STOP` block with both paths listed and `PARAR` terminal statement; no output files are created when the procedure returns early

---

## Category 7 — Documentation & Catalog Update

Can run in parallel with Category 6.

- [X] 7.1 Apply edit B1a in `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`: remove three lines from `artifact_contracts.ava-asis-bridge-fastqa.external_mandatory` — `estimate_effort/PBI-*_planning.md`, `requirements_analysis/PBI-*_ac_scope.md`, `test_cases/PBI-*_validation_report.md` (see `data-model.md §B1a`)
- [X] 7.2 Apply edit B1b in `orchestrator-asis.md`: update SubAgent prompt text in `dispatch_bridge_fastqa()` Step C from `"v3.1.0 completo (3 Elementos, 18 Steps)"` to `"v4.0.0 completo (3 Elementos, 16 Steps)"` (see `data-model.md §B1b`)
- [X] 7.3 Apply edit B1c in `orchestrator-asis.md`: update `size_threshold` value from `5000` to `3000` and update the comment from `"mínimo 5KB ... 9 seções"` to `"mínimo 3KB ... 5 seções"` (see `data-model.md §B1c`)
- [X] 7.4 [P] Apply edit C1a in `docs/asis-diagnostic-io-map.md`: replace bridge-fastqa **Inputs** block — new three-row table for AST JSON files with path resolution order and deprecation note for removed inputs (see `data-model.md §C1a`)
- [X] 7.5 [P] Apply edit C1b in `docs/asis-diagnostic-io-map.md`: remove three eliminated output entries from bridge-fastqa outputs list (`estimate_effort/`, `requirements_analysis/*_ac_scope.md`, `test_cases/*_validation_report.md`) (see `data-model.md §C1b`)
- [X] 7.6 [P] Apply edit C1c in `docs/asis-diagnostic-io-map.md`: update §5 Cross-Agent Consumption table bridge-fastqa row — change relationship from "documentation (2 mandatory + 4 optional)" to "AST JSON artifacts (3 mandatory — compressed/ primary, extraction/ fallback; hard stop if absent from both)" (see `data-model.md §C1c`)
- [X] 7.7 [P] Add `CHANGELOG.md` entry: MAJOR bump, version 4.0.0, summarize the three simplification dimensions (AST inputs, lean pipeline, lean test-plan template)

---

## Completion Checklist

- [X] All Category 1–2 tasks applied to `bridge-fastqa-asis.md`
- [X] All Category 7 tasks applied to `orchestrator-asis.md` and `asis-diagnostic-io-map.md`
- [X] Run full validation script from `quickstart.md` → all 16 checks pass
- [X] `bridge-fastqa-asis.md` frontmatter validated: `name`, `version`, `description`, `allowed-tools` only
- [X] No `functional-requirements.md`, `business-rules.md`, or optional doc artifacts referenced as inputs
- [X] No `estimate_effort`, `ac_scope_analysis`, `validate_scenarios` referenced anywhere in agent body
- [X] Test-plan template contains exactly 5 sections (§1–§5)
- [X] `orchestrator-asis.md` artifact contract lists exactly 6 `external_mandatory` files (not 9)
- [X] `docs/asis-diagnostic-io-map.md` bridge-fastqa entry reflects AST JSON inputs
- [X] `CHANGELOG.md` entry committed

---

## Dependency Graph

```
Category 1 (Frontmatter)
  └── Category 2a (Dependency Gate + AST Read, Steps 1–3)
        └── Category 2b (PBI Composition, Steps 4–7)
              └── Category 2c (Element 2 lean, Steps 8–12)
                    └── Category 2d (Element 3 lean, Steps 13–16)
                          └── Category 2e (Test Plan template, Step 14)
                                └── Category 2f (Completion + Guardrails)
                                      ├── Category 5 (Checklists)  [parallel]
                                      ├── Category 6 (Validation)  [parallel]
                                      └── Category 7 (Docs update) [parallel]
```

**Parallel opportunities within Category 7**: tasks 7.1–7.3 (orchestrator) are independent of 7.4–7.6 (io-map) and can be applied simultaneously.

## Task Count Summary

| Category | Tasks | Parallelizable |
|---|---|---|
| 1 — Frontmatter & Contract | 4 | 0 |
| 2a — Dependency Gate + AST Read | 4 | 0 |
| 2b — PBI Composition | 3 | 0 |
| 2c — Element 2 lean | 5 | 0 |
| 2d — Element 3 lean | 4 | 0 |
| 2e — Test Plan template | 5 | 0 |
| 2f — Completion + Guardrails | 5 | 0 |
| 3 — Schema | 0 | N/A |
| 4 — Registration | 0 | N/A |
| 5 — Checklists | 2 | 1 |
| 6 — Validation | 5 | 4 |
| 7 — Documentation | 7 | 4 |
| **Total** | **44** | **9** |
