# Agent Development Tasks: ava-test-plan-tobe v4.0.0 — Consolidate Test Plan Artifacts

**Plan**: [specs/029-consolidate-test-plan-artifacts/plan.md](plan.md)
**Agent ID**: `ava-test-plan-tobe` | **Phase**: `F2` | **Module**: `ava-fabric-agents/tobe-architecture`

> **Change Type**: `modify-existing` — surgical deletion across 9 files, no new agent creation.
> Categories marked [N/A] are skipped because this is an existing agent with unchanged registration and schema.

---

## Category 1 — Agent Frontmatter & Contract Update

Must complete before any other category. Tasks are sequential (not parallelizable).

- [ ] **1.1** Open `src/modules/ava-fabric-agents/tobe-architecture/agents/test-plan-tobe.md`
- [ ] **1.2** Update YAML frontmatter:
  - Set `version: "4.0.0"`
  - Update `description:` to mention only 4 artifacts (`test-plan.md`, `traceability-matrix.md`, `automatable-test-cases.md`, `functional-test-matrix.md`)
  - Remove activation phrases for eliminated artifacts from `Ativa com:`
  - Verify `allowed-tools:` unchanged
- [ ] **1.3** Update `## Output Contract` YAML block:
  - Remove all entries except: `test_plan`, `functional_tests`, `traceability_matrix`, `automatable_cases`
  - Verify paths use lowercase `{project_name}` and correct phase folder (`outputs/tobe/qa/` and `outputs/tobe/tests/`)
- [ ] **1.4** Verify frontmatter contains ONLY: `name`, `version`, `description`, `allowed-tools` (Constitution Article II)

---

## Category 2 — Agent Behavior & Instructions Surgery

Depends on Category 1. Sequential execution recommended due to line-number dependencies.

- [ ] **2.1** Remove Skills subsections for eliminated artifacts:
  - Delete `### Smoke Tests` subsection
  - Delete `### Cobertura` subsection (or reduce to inline mention in `test-plan.md` CI strategy)
  - Delete `### Performance & Carga` subsection
  - Delete `### Testes de Tela` subsection
- [ ] **2.2** Remove canonical template sections:
  - Delete Section 7 (Smoke Tests)
  - Delete Section 8 (Load Test Plan)
  - Delete Section 14 (Security Test Strategy)
  - Delete Section 16 (Coverage Gap Strategy)
  - Retitle remaining sections to close numbering gaps (e.g., Section 15 → new number)
- [ ] **2.3** Remove execution steps for eliminated artifacts:
  - Delete Step 5c (Smoke Suite per Wave generation)
  - Delete Step 6b (Load Test Plan generation)
  - Delete entire Step SKW block (smoke suite dispatch)
  - Delete any step generating `coverage-gap-strategy.md`
- [ ] **2.4** Update triggers & activation menu:
  - Remove `SKW`, `CG`, `LD`, `UI`, `SS`, `ST` triggers from triggers table
  - Remove activation phrases for eliminated triggers from frontmatter `description`
- [ ] **2.5** Prune failure modes table:
  - Remove rows referencing `wave-test-plan.md`, `smoke-tests.md`, smoke suites, `load-test-plan.md`, `ui-test-plan.md`, `coverage-strategy.md`, `bdd-coverage-per-wave.md`, `security-test-strategy.md`, `coverage-gap-strategy.md`
  - Update remaining rows that mention eliminated artifacts in "Mitigation" or "Error Message" columns
- [ ] **2.6** Excise Azure DevOps pipeline validation block:
  - Remove `### 7.2 Suite por Wave` from section validation list
  - Remove `## 7. Smoke Tests`, `## 8. Load Test`, `## 14. Security Test Strategy`, `## 16. Coverage Gap Strategy` from `for SECTION in ...` loop
  - Remove orphaned `- script: |` blocks validating smoke-suite files (`smoke-suite-${WAVE_NAME}.md`, `.yml`, `.github.yml`)
  - Remove orphaned `- script: |` block validating `coverage-gap-strategy.md`
- [ ] **2.7** Add completeness gate (NEW behavior):
  - Add gate step validating 4 retained artifacts exist and are non-empty before emitting `AgentResult.success`
  - Exempt `traceability-matrix.md` when `business-rules.md` is absent

---

## Category 3 — Shared Schema Updates

**[N/A]** — No schema changes. `agent-task.schema.json` and `agent-result.schema.json` are unchanged. The `artifacts[]` array in `AgentResult` will contain 4 entries instead of 15 (data content change, not schema change).

---

## Category 4 — Module Registration

**[N/A]** — Agent `ava-test-plan-tobe` is already registered in `src/modules/ava-fabric-agents/tobe-architecture/module.yaml`. Agent ID, file path, and skill name are unchanged.

---

## Category 5 — Quality Gate Checklists

Depends on Category 2.

- [ ] **5.1** Add completeness gate checklist items to agent's internal gate logic:
  - Verify `test-plan.md` exists and is non-empty
  - Verify `functional-test-matrix.md` exists and is non-empty
  - Verify `automatable-test-cases.md` exists and is non-empty
  - Verify `traceability-matrix.md` exists and is non-empty (unless `business-rules.md` is absent)
- [ ] **5.2** [P] Verify checklist items use `- [ ]` format and are traceable to spec Scenario 3 (Gate P1)

---

## Category 6 — Acceptance Validation & QA Integration

Depends on Category 2.

> Validation is grep-based, not runtime execution. IMFAI agents are LLM prompt files.

- [ ] **6.1** Pre-implementation baseline:
  - Run `grep_search` for all 11 eliminated artifact names across `src/` and `docs/`
  - Record match count per artifact per file in `research.md`
- [ ] **6.2** [P] Post-implementation zero-match verification:
  - Re-run identical `grep_search`; verify **zero matches** for all 11 eliminated artifact names
  - Verify `test-plan-tobe.md` Output Contract YAML block has exactly **4 entries**
  - Verify `test-plan-tobe.md` frontmatter version is `4.0.0`
- [ ] **6.3** [P] Downstream consumer verification:
  - Verify `orchestrator-tobe.md` Fase 6 outputs table has no eliminated artifacts
  - Verify `summary-agent.md` has no `coverageGapStrategy` field
  - Verify `build_summary_comprehensive.py` has no `_cgs_path` variable
  - Verify `artifact-map.yaml` has exactly **4 entries** under `ava-test-plan-tobe`
- [ ] **6.4** [P] Regression test:
  - Confirm retained 4 artifacts (`test-plan.md`, `traceability-matrix.md`, `automatable-test-cases.md`, `functional-test-matrix.md`) still appear correctly in all files
  - Confirm no accidental deletion of unrelated content
- [ ] **6.5** Map acceptance scenarios to F5 QA pipeline:
  - Nominal P1 (Scenario 1): agent produces exactly 4 artifacts → `ava-qa-behavior-mapping` input
  - Edge P2 (Scenario 2): missing `business-rules.md` → skip traceability → `ava-qa-scenario-generator` edge case
  - Gate P1 (Scenario 3): zero dangling references → `ava-qa-gaps-requirements` coverage check

---

## Category 7 — Documentation & Catalog Update

Can run parallel with Category 6 after Category 2 completes.

- [ ] **7.1** [P] Update `docs/agents-catalog.md`:
  - Update `ava-test-plan-tobe` row to list only 4 output artifacts
  - Remove references to eliminated artifacts in description/notes
- [ ] **7.2** [P] Update `docs/summary-io-map.md`:
  - Remove `D.coverageGapStrategy` from summary input map
  - Remove `coverage-gap-strategy.md` from artifact-to-summary mappings
- [ ] **7.3** [P] Update `docs/tobe-architecture-io-map.md`:
  - Remove eliminated artifacts from F2 output map
  - Update `ava-test-plan-tobe` entry to list only 4 artifacts
- [ ] **7.4** [P] Update `docs/tobe-input-artifacts-existence-check.md`:
  - Remove eliminated artifacts from existence check list
  - Update check commands/validation to expect only 4 artifacts
- [ ] **7.5** [P] Update `CHANGELOG.md`:
  - Add entry for `ava-test-plan-tobe` v4.0.0 (MAJOR bump)
  - List 11 eliminated artifacts by name
  - Reference `specs/029-consolidate-test-plan-artifacts/spec.md`

---

## Completion Checklist

- [ ] Category 1 complete — frontmatter & contract updated to 4 artifacts, version 4.0.0
- [ ] Category 2 complete — all 11 eliminated artifacts excised from agent spec
- [ ] Category 3 skipped — no schema changes (N/A confirmed)
- [ ] Category 4 skipped — no module.yaml change (N/A confirmed)
- [ ] Category 5 complete — completeness gate checklist items added
- [ ] Category 6 complete — zero-match verification passed for all 11 eliminated artifacts
- [ ] Category 7 complete — 4 doc files + CHANGELOG updated
- [ ] `specify self check` — no SpecKit updates pending
- [ ] Agent `.md` frontmatter validated against Constitution Article II
- [ ] `docs/agents-catalog.md` updated
- [ ] `CHANGELOG.md` entry committed
- [ ] No references to eliminated artifacts remain in any project file
