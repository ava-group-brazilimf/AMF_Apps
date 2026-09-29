# Agent Specification: ava-asis-bridge-fastqa (Simplification)

**Feature Branch**: `023-bridge-fastqa-ast-simplification`
**Created**: 2026-07-19
**Status**: Draft
**Change Type**: `modify-existing`
**Input**: Simplify the Bridge FastQA agent in three dimensions: (1) switch PBI generation to consume AST JSON artifacts instead of derived documentation artifacts; (2) eliminate non-essential FastQA pipeline steps while keeping `identify_gaps`; (3) reduce the `test-plan.md` template to content that can be directly inferred from AST inputs.

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-asis-bridge-fastqa` |
| **Version** | `3.3.0` → `4.0.0` (MAJOR — Input Contract and pipeline shape change) |
| **Phase** | `F1` |
| **Module** | `asis-diagnostic` |
| **Role** | Bridge between AS-IS diagnostic pipeline and FastQA ecosystem; generates a PBI document from AST artifacts, orchestrates a lean FastQA sub-pipeline, and produces a test plan from the results |
| **Skill** | _(no skill — dispatched only by orchestrator via `dispatch_bridge_fastqa()`)_ |
| **Dispatch** | internal-only via `ava-asis-orchestrator` on `doc:RF✓ + doc:RN✓` |

> **Change type is `modify-existing`**:
> - Existing file: `src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md`
> - Version bump: MAJOR (Input Contract is fundamentally changed — different primary artifacts, removed optional artifacts)
> - `module.yaml` entry already exists — Category 4 tasks are N/A
> - No SKILL.md (internal agent)

---

## 2. Agent Frontmatter

```yaml
---
name: "ava-asis-bridge-fastqa"
version: "4.0.0"
description: |
  Bridge Agent entre o pipeline AS-IS e o ecossistema FastQA.
  Gera um documento PBI local a partir dos artefatos AST brutos (01_business_rules.json,
  02_form_business_rules.json, 03_database_rules.json), orquestra um pipeline FastQA
  enxuto (load_pbi → identify_gaps → analyze_requirements → map_behaviors →
  test_case_with_fastqa) e produz o Test Plan local derivado diretamente dos artefatos AST.
  Ativa com: "gerar PBI para FastQA", "bridge FastQA", "criar PBI local",
  "generate FastQA PBI", "bridge to FastQA", "create local PBI".
allowed-tools: Read, Write, Glob, Grep
---
```

---

## 3. Output Contract

Unchanged from v3.3.0 with the following correction: secondary outputs from eliminated
pipeline steps (`estimate_effort/`, `requirements_analysis/*_ac_scope.md`,
`test_cases/*_validation_report.md`) are no longer produced. The primary output set is:

```yaml
outputs:
  # Element 1 — PBI
  pbi_document: "fastqa/manual_test/US/PBI-{N}.md"
  # Element 2 — FastQA Pipeline (lean)
  gap_analysis:          "fastqa/manual_test/gap_analysis/PBI-{N}_gaps.md"
  requirements_analysis: "fastqa/manual_test/requirements_analysis/PBI-{N}_requirements.md"
  behavior_mapping:      "fastqa/manual_test/behavior_analysis/PBI-{N}_behaviors.md"
  # Element 3 — Test Design & Plan
  test_cases:    "fastqa/manual_test/test_cases/{funcionalidade}/PBI-{N}.md"
  test_plan:     "fastqa/manual_test/test_cases/PBI-{N}_test_plan.md"
  # QA Output Publication (for downstream phases)
  qa_gap_analysis:  "projects/{project_name}/outputs/asis/qa/gap-analysis.md"
  qa_test_cases:    "projects/{project_name}/outputs/asis/qa/test-cases.md"
  qa_test_plan:     "projects/{project_name}/outputs/asis/qa/test-plan.md"
```

**Removed outputs** (no longer produced by v4.0.0):
- `fastqa/manual_test/estimate_effort/PBI-{N}_planning.md` (Step 10 eliminated)
- `fastqa/manual_test/requirements_analysis/PBI-{N}_ac_scope.md` (Step 14 eliminated)
- `fastqa/manual_test/test_cases/PBI-{N}_validation_report.md` (Step 16 eliminated)

---

## 4. Changes by Dimension

### Dimension 1 — Input Contract: AST Artifacts Replace Derived Documentation

#### Current state (v3.3.0)
Primary inputs: `asis/docs/functional-requirements.md`, `asis/docs/business-rules.md` (BLOCKING)
Optional enrichments: `asis/docs/screen-rules.md`, `asis/docs/screen-navigation-map.md`, `asis/docs/value-chain.md`, `asis/bounded-context-map.md`

#### Target state (v4.0.0)

**New primary inputs (BLOCKING — hard stop if not found):**

| Artifact | AST content | Source |
|---|---|---|
| `01_business_rules.json` | Calculations, validations, business logic in code | `projects/{project_name}/outputs/asis/delphi-ast-raw/compressed/` |
| `02_form_business_rules.json` | Form/UI business rules, field definitions, event handlers | same |
| `03_database_rules.json` | DB write operations, table insertions/updates/deletes | same |

**Resolution order (Dependency Gate):**
1. Check `projects/{project_name}/outputs/asis/delphi-ast-raw/compressed/{01,02,03}_*.json`
2. If any missing: check `projects/{project_name}/outputs/asis/delphi-ast-raw/extraction/{01,02,03}_*.json`
3. If still missing from both paths: **HARD STOP** — emit blocking error and terminate execution without generating any output.

**Removed inputs (no longer read):**
- `asis/docs/functional-requirements.md` — no longer a mandatory input
- `asis/docs/business-rules.md` — no longer a mandatory input
- `asis/docs/screen-rules.md` — removed (was optional enrichment)
- `asis/docs/screen-navigation-map.md` — removed (was optional enrichment)
- `asis/docs/value-chain.md` — removed (was optional enrichment)
- `asis/bounded-context-map.md` — removed (was optional enrichment)

**Rationale:** The three AST JSON files are deterministically generated by `run_delphi_ast_analysis.py` (Step 0 of `solution-delphi`) and contain structured, machine-parseable business rules with source references. They replace the prose documentation artifacts that were derived from the same source code via LLM analysis — using them as primary input eliminates duplication in the dependency chain and makes the bridge agent robust to partial documentation pipelines.

#### PBI Composition from AST Artifacts

| PBI section | AST source |
|---|---|
| Title | Project name + legacy technology from `project-config.yaml` |
| User Story | Fixed template + `project_name` + `legacy_technology` |
| Detailed Description | Modules derived from `02_form_business_rules.json` `forms[].form_name` |
| Acceptance Criteria | One scenario per `01_business_rules.json` rule (`BR-NNN`) + one per DB write operation in `03_database_rules.json` (`DBR-NNN`) with clear effect |
| Technical Notes | `01_business_rules.json` counts + `02_form_business_rules.json` form/field counts + `03_database_rules.json` DB operation counts |

**Acceptance Criteria generation rules:**
- From `01_business_rules.json`: each calculation/validation rule → one `Dado/Quando/Então` scenario with `(Fonte: BR-NNN)` traceability
- From `03_database_rules.json`: each distinct table × operation pair → one scenario describing expected DB state change with `(Fonte: DBR-NNN)` traceability  
- From `02_form_business_rules.json`: each form with `event_handlers` non-empty → one scenario covering the field interaction with `(Fonte: form: {form_name})` traceability
- Maximum 30 scenarios total; consolidate by module when > 30

---

### Dimension 2 — Lean FastQA Pipeline

#### Current state (v3.3.0)
Element 2 (5 steps): `load_pbi → identify_gaps → estimate_effort → analyze_requirements → map_behaviors`
Element 3 (4 steps): `ac_scope_analysis → test_case_with_fastqa → validate_scenarios → azdo_create_test_plan (local)`

#### Target state (v4.0.0)
Element 2 (4 steps — `estimate_effort` eliminated): `load_pbi → identify_gaps → analyze_requirements → map_behaviors`
Element 3 (2 steps — `ac_scope_analysis` and `validate_scenarios` eliminated): `test_case_with_fastqa → test_plan (local)`

**Eliminated steps and rationale:**

| Step | Command | Reason eliminated |
|---|---|---|
| Step 10 | `@fastqa:estimate_effort` | Produces effort estimates and test data descriptions — valuable for sprint planning but not a structural prerequisite for test case generation. The `analyze_requirements` agent accepts it as optional and produces its output without it. |
| Step 14 | `@fastqa:ac_scope_analysis` | Classifies ACs by criticality — useful enrichment but `test_case_with_fastqa` has a built-in fallback (all ACs treated as important). Without a structured AC scope file, the test writer generates a complete test suite covering all acceptance criteria. |
| Step 16 | `@fastqa:validate_scenarios` | Validates quality and traceability of generated test cases — a QA-of-QA step that improves confidence but does not alter whether test cases exist. Removes one full LLM pass from the pipeline. |

**Retained steps (mandatory):**

| Step | Command | Why essential |
|---|---|---|
| Step 8 | `@fastqa:load_pbi` | Populates `pbi.current` — all subsequent FastQA agents depend on this in-memory context |
| Step 9 | `@fastqa:identify_gaps` | Kept per explicit requirement — surfaces requirement gaps early |
| Step 10 (renumbered 10) | `@fastqa:analyze_requirements` | Produces `REQ-F-*` / `REQ-NF-*` IDs — `map_behaviors` BLOCKS on this artifact |
| Step 11 (renumbered 11) | `@fastqa:map_behaviors` | Produces `BHV-*` IDs with traceability — `test_case_with_fastqa` uses this for structured test generation |
| Step 13 (renumbered 13) | `@fastqa:test_case_with_fastqa` | Primary output — generates test case files |
| Step 14 (renumbered 14) | Test Plan (local) | Produces `PBI-{N}_test_plan.md` required by downstream phases |

**New step numbering:**

```
Element 1 (PBI Generator): Steps 1–7  (unchanged)
Element 2 (FastQA Pipeline): Steps 8–11
  Step 8:  load_pbi
  Step 9:  identify_gaps
  Step 10: analyze_requirements  [was step 11]
  Step 11: map_behaviors          [was step 12]
  Step 12: Element 2 Checkpoint   [was step 13]
Element 3 (Test Cases & Plan): Steps 13–16
  Step 13: test_case_with_fastqa  [was step 15]
  Step 14: Test Plan (local)      [was step 17]
  Step 15: Publish QA Artifacts   [was step 17b]
  Step 16: Emit Completion Signal [was step 18]
```

---

### Dimension 3 — Lean test-plan.md Template

#### Current state (v3.3.0)
9 sections: Test Strategy, Unit Test Scope (Domain + Application + Validators), Integration Test Scope (Repository + API + Security), Architecture Tests, E2E Tests, Smoke Test Suite, Load Test Plan, Test Data Management, Test Quality Gates.

**Problems identified:**
- **§4 Architecture Tests**: Rules are generic and not derivable from AST input — they assume Clean Architecture is already decided (a TO-BE concern)
- **§5 E2E Tests**: Requires `screen-navigation-map.md` and `value-chain.md` — both removed from inputs in Dimension 1; without them, scenarios would be fabricated
- **§6 Smoke Test Suite**: Fully generic; independent of any project-specific data
- **§7 Load Test Plan**: Requires non-functional requirements (throughput, concurrency) — these are not present in the three AST files
- **§8 Test Data Management**: The Seed Data table requires `db/schema-inventory.md` which is not in scope of this agent

#### Target state (v4.0.0): 5 sections

**Kept sections (directly derivable from AST):**

| § | Section | AST source |
|---|---|---|
| 1 | Test Strategy — Pyramid | Fixed proportions (60/25/15); tool TBD in TO-BE phase |
| 2 | Unit Test Scope | `01_business_rules.json` (calculations/validations → domain tests) + `02_form_business_rules.json` (event handlers → validator tests) |
| 3 | Integration Test Scope | `03_database_rules.json` (write operations → repository tests per table) |
| 4 | Test Coverage Map | Table mapping `BR-NNN` and `DBR-NNN` IDs to test categories — traceability from AST to tests |
| 5 | Test Quality Gates | Fixed CI thresholds (BR/FR coverage ≥80%, 0 integration failures) |

**Removed sections:**
- §4 Architecture Tests — OUT (TO-BE concern; not inferable from AST)
- §5 E2E Tests — OUT (requires removed input artifacts)
- §6 Smoke Test Suite — OUT (generic boilerplate; added only after TO-BE deployment plan)
- §7 Load Test Plan — OUT (no NFR data in AST artifacts)
- §8 Test Data Management (Seed Data table) — OUT (requires db/schema-inventory.md, not in scope)

**New §4 — Test Coverage Map** (replaces the removed sections):

A traceability table derived from all three AST files mapping each rule ID to its test category:

```markdown
## 4. Test Coverage Map (Traceability)

| Rule ID | Rule Type | Module | Test Category | Test Description |
|---------|-----------|--------|---------------|-----------------|
| BR-0001 | calculation | {unit} | Unit — Domain | {target} = {expression} |
| DBR-0001 | write_operation | {tables[0]} | Integration — Repository | {operation} on {tables[0]} |
| form:{form_name} | event_handler | {form_name} | Unit — Validator | {event} on {field} |
```

---

## 5. Impact on Dependent Files

### `agents/orchestrator-asis.md`

The `dispatch_bridge_fastqa()` procedure references input artifacts from documentation agents.
The trigger `on(RF✓ + doc:RN✓)` must be reviewed because the new input contract does not depend
on `functional-requirements.md` or `business-rules.md`. However, changing the dispatch trigger
is **out of scope** for this spec — the existing trigger is conservative (fires only after docs
are complete) and ensures all upstream analysis is done before the bridge executes.

**Only required change**: Update the comment in `artifact_contracts.ava-asis-bridge-fastqa`
to reflect that primary inputs are now AST JSONs, not documentation artifacts.

### `docs/asis-diagnostic-io-map.md`

Section `### ava-asis-bridge-fastqa` must be updated:
- **Inputs**: Replace `functional-requirements.md` (mandatory) and `business-rules.md` (mandatory) with AST JSON artifacts as mandatory; remove all optional doc artifacts
- **Outputs**: Remove eliminated artifacts from the output list

---

## 6. User Scenarios

### Scenario 1 — Nominal: AST files found in primary path (Priority: P1)

**Story**: Como o orquestrador AS-IS, quero que o Bridge FastQA leia diretamente os artefatos AST para gerar o PBI e test plan, sem depender de artefatos de documentação intermediários.

**Acceptance Scenarios**:
1. **Given** `projects/{project_name}/outputs/asis/delphi-ast-raw/compressed/01_business_rules.json` (and 02, 03) exist and are non-empty, **When** the agent executes, **Then** it produces `fastqa/manual_test/US/PBI-{N}.md` containing Acceptance Criteria with `(Fonte: BR-NNN)` traceability.
2. **Given** the same, **When** execution completes, **Then** `fastqa/manual_test/test_cases/PBI-{N}_test_plan.md` contains sections 1–5 as defined in this spec and has size > 3 KB.
3. **Given** the same, **When** execution completes, **Then** `projects/{project_name}/outputs/asis/qa/test-plan.md` exists and matches the test plan.

### Scenario 2 — Fallback: AST files found only in extraction path (Priority: P2)

**Acceptance Scenarios**:
1. **Given** `compressed/` does not contain one or more AST files, **When** the agent checks the `extraction/` path and finds all three files, **Then** execution proceeds normally using the extraction artifacts.
2. **Given** the same, **Then** no warning is emitted about the fallback — the extraction path is a valid secondary source.

### Scenario 3 — Hard Stop: AST files not found in either path (Priority: P1)

**Acceptance Scenarios**:
1. **Given** neither `compressed/` nor `extraction/` contains the required AST files, **When** the agent executes, **Then** it emits a `⛔ BLOCKED` message identifying which files are missing and terminates without producing any output.
2. **Given** the same, **Then** `agentResult.status` is `blocked` and no PBI or test plan files are created.

### Scenario 4 — Lean pipeline: eliminated steps are not invoked (Priority: P2)

**Acceptance Scenarios**:
1. **Given** a nominal execution, **When** the pipeline completes, **Then** no call to `@fastqa:estimate_effort`, `@fastqa:ac_scope_analysis`, or `@fastqa:validate_scenarios` appears in the execution trace.
2. **Given** the same, **Then** no `PBI-{N}_planning.md`, `PBI-{N}_ac_scope.md`, or `PBI-{N}_validation_report.md` files are created.

### Scenario 5 — Test plan derived from AST (Priority: P1)

**Acceptance Scenarios**:
1. **Given** `03_database_rules.json` contains N distinct table-operation pairs, **When** the test plan is generated, **Then** §3 Integration Test Scope contains at least N repository test entries.
2. **Given** `01_business_rules.json` contains M business rules, **When** the test plan is generated, **Then** §4 Test Coverage Map contains M rows with `BR-NNN` IDs.

---

## 7. Quality Gate Requirements

- [x] Agent ID unchanged: `ava-asis-bridge-fastqa` follows `^ava-[a-z0-9-]+$` (Article II)
- [x] Version bump MAJOR justified: Input Contract changed fundamentally (Article II)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [x] All output paths use lowercase `{project_name}` and `asis/qa/` folder (Article II)
- [x] BDD scenarios cover nominal, fallback, hard-stop, lean pipeline, and test plan derivation (Article VI)
- [x] No technology versions hardcoded (Article I)
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 8. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Delphi AST extractor (Step 0) | `ava-asis-solution-delphi` | Must complete before bridge fires — produces the three required AST JSON files |
| Documentation pipeline (dispatch trigger) | `ava-asis-documentation` | Current trigger `doc:RF✓ + doc:RN✓` still used for timing; inputs no longer read |

---

## 9. Exclusions

- The dispatch trigger `on(RF✓ + doc:RN✓)` is NOT changed — out of scope; changing it requires orchestrator spec
- The `@fastqa:identify_gaps` step is NOT eliminated — explicitly mandated to remain
- The `element1_checkpoint`, `element2_checkpoint` checkpoints are kept
- Gherkin keyword language (EN keywords + PT content) and all existing Guardrails remain unless contradicted by this spec

---

## 10. Assumptions

- The three AST JSON files (`01_business_rules.json`, `02_form_business_rules.json`, `03_database_rules.json`) follow the schema documented in their respective examples attached to this spec: `schema_version: "0.1.0"`, `payload.rules` with `schema[]` and `rows[]` arrays for rules, `payload.forms` with `schema[]` and `rows[]` for forms, `payload.rules` with `schema[]` and `rows[]` for DB rules
- The `extraction/` path contains the same three files but in a pretty-printed format (not minified); both are valid for LLM consumption
- The bridge agent continues to be dispatched exclusively by `ava-asis-orchestrator` — no user-facing trigger is added
- The `@fastqa:load_pbi` invocation continues to use Modo B (local, no Azure DevOps)

---

## Success Criteria

| Criterion | Measure |
|---|---|
| AST primary inputs | Agent reads only `01_`, `02_`, `03_` JSON files; no `functional-requirements.md` or `business-rules.md` read calls |
| Hard stop enforced | Missing AST files → zero output files created; blocking error emitted |
| Lean pipeline | No invocations of `estimate_effort`, `ac_scope_analysis`, `validate_scenarios` in any execution path |
| Test plan sections | `test-plan.md` contains exactly 5 sections (§1–§5 as defined); §4 has rows for every BR-NNN and DBR-NNN from AST inputs |
| Downstream compatibility | `projects/{project_name}/outputs/asis/qa/test-plan.md` ≥ 3 KB (satisfies orchestrator `size_threshold`) |
| IO map updated | `docs/asis-diagnostic-io-map.md` bridge-fastqa section reflects new input contract |
| Orchestrator updated | Three edits applied to `orchestrator-asis.md`: (1) `external_mandatory` reduced from 9 to 6 entries — remove `estimate_effort/PBI-*_planning.md`, `requirements_analysis/PBI-*_ac_scope.md`, `test_cases/PBI-*_validation_report.md`; (2) dispatch prompt updated to `v4.0.0` / `16 Steps`; (3) `size_threshold` set to `3000` bytes |
