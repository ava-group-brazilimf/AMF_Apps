# Agent Development Tasks: Remove Agents ava-asis-test-qa, ava-asis-baseline-test-generator, ava-asis-golden-dataset-capture

**Plan**: `specs/024-remove-test-qa-baseline-golden-agents/plan.md`
**Change type**: `cleanup` | **Phase**: `F1` | **Module**: `asis-diagnostic` + `summary`

> This is a multi-file cleanup, not a new-agent creation. Categories map to file groups from the plan,
> not to the standard new-agent frontmatter/body/registration flow.
> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.
> Categories 4, 5, and 6 can run in parallel after Category 3 completes.

---

## Category 1 — Orchestrator DAG & Artifact Contracts (`orchestrator-asis.md`)

Must complete before any other category. This file is the source of truth for DAG, dispatch schedule, and artifact_contracts consumed by all other files.

- [X] **1.1** Remove the `Test QA` row from the `Agent Team Gerenciado` table in `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`
- [X] **1.2** Remove the `Golden Dataset Capture` row from the `Agent Team Gerenciado` table in the same file
- [X] **1.3** Remove line `▶ test-qa ━━━━━━━━━━━┓` from the DAG ASCII diagram — `PHASE A · WAVE 2` block
- [X] **1.4** Remove `test-qa` from the `dispatch` array in `dispatch_schedule.phase_a_wave2` and delete its associated comment line (`# test-qa | deps: source code + 09_test_coverage.json`)
- [X] **1.5** Remove the two Phase B dispatch rules: `{ trigger: "RF✓ + RN✓", dispatch: test-qa:QA }` and `{ trigger: "test-qa:QA✓", dispatch: golden-dataset-capture }`
- [X] **1.6** Remove `"ava-asis-test-qa"` from the `active` array in `evaluate_phase_a_all()`
- [X] **1.7** Remove the full `ava-asis-test-qa` contract block from `artifact_contracts` (mandatory: test-map.md, test-coverage-asis.md, test-gaps.md, test-baseline.md)
- [X] **1.8** Remove the full `ava-asis-golden-dataset-capture` contract block from `artifact_contracts` (base_path_override + mandatory: golden-dataset.json, capture-report.md, execution-log.md)
- [X] **1.9** Update the `ava-asis-bridge-fastqa` contract block in `artifact_contracts` — replace `qa/gap-analysis.md` with `qa/test-gaps.md`; add `qa/test-cases.md` alongside the existing `qa/test-plan.md`; final mandatory list: `["qa/test-plan.md", "qa/test-gaps.md", "qa/test-cases.md"]`
- [X] **1.10** Remove the entire `Guard — golden_dataset_enabled_asis: false` block (banner text + `golden_dataset_status: SKIPPED` registration + C2c reference sentence)
- [X] **1.11** Remove the `ARTIFACT-COMPLETE-GOLDEN-DATASET` check block (C2c) from the Consistency Gate
- [X] **1.12** Remove `ava-asis-test-qa` and `ava-asis-golden-dataset-capture` from the `Agent Completion Registry` — Agent IDs list
- [X] **1.13** Update `Orchestration Completion Gate` prose: change "9 agentes" → "7 agentes"
- [X] **1.14** Remove the `golden_dataset_enabled_asis` read + default comment from `Step 2` (Decompose)
- [X] **1.15** Remove the `test-qa:QA` and `golden-dataset-capture` dispatch bullets from `Step 3.2` streaming collect section
- [X] **1.16** Remove line `✓ test-qa → completed (test-map.md + test-coverage-asis.md)` from `Verification Block — Pré-Consolidação`
- [X] **1.17** Remove `ava-asis-test-qa` from `execution_timing.per_orchestrator` sub_agents list; update `sub_agents_count` from 14 → 13
- [X] **1.18** In Workflow FP `Validar Artefatos Críticos`: remove the 4 `*(AG-04)*` lines for `test-coverage-asis.md`, `test-map.md`, `test-gaps.md`, `test-baseline.md`; add one new line: `Verificar projects/{project_name}/outputs/asis/qa/test-gaps.md (gerado por ava-asis-bridge-fastqa Step 15 — se ausente, registrar WARN e continuar)`
- [X] **1.19** Update `Progress Tracker` TODO item `phase-a` label: "Wave 2 (6 agents)" → "Wave 2 (5 agents)"
- [X] **1.20** Remove the guardrail bullet that lists `test-qa:QA` as trigger for `golden-dataset-capture`
- [X] **1.21** Bump `orchestrator-asis.md` frontmatter `version` from `2.20.0` → `2.20.1` (PATCH)

---

## Category 2 — Bridge FastQA Output Contract Extension (`bridge-fastqa-asis.md`)

Depends on Category 1 (artifact_contracts must reflect the extended mandatory list before this agent is edited).

- [X] **2.1** Bump `bridge-fastqa-asis.md` frontmatter `version` from `4.0.0` → `4.1.0` (MINOR — new output artifact)
- [X] **2.2** Update `description` field to reference version `4.1.0` and mention `test-gaps.md` generation in the Observability track call
- [X] **2.3** Rename the `Gap Analysis` row in the `QA Output Directory (Publicação)` table: path `qa/gap-analysis.md` → `qa/test-gaps.md`; description `Análise de gaps dos requisitos` → `Gaps TG-NNN por módulo, rastreáveis a BR-NNN/DBR-NNN`
- [X] **2.4** Update sub-step `# --- 1. Copiar Gap Analysis ---` in `PROCEDURE publish_qa_artifacts` (Step 15): rename comment to `# --- 1. Publicar Test Gaps ---`; change `gap_dest = qa_dir + "gap-analysis.md"` → `gap_dest = qa_dir + "test-gaps.md"`; update success/warning emits to reference `test-gaps.md`
- [X] **2.5** Update Step 16 Completion Signal — rename `Gap Analysis: projects/{project_name}/outputs/asis/qa/gap-analysis.md [{status_qa_gap}]` → `Test Gaps: projects/{project_name}/outputs/asis/qa/test-gaps.md [{status_qa_tg}]`
- [X] **2.6** Update the Observability `--version` flag in the `FASE OBRIGATÓRIA` section from `4.0.0` → `4.1.0`

---

## Category 3 — Module Config & Output Paths (2 files)

Depends on Category 1. Can proceed in parallel with Category 2.

- [X] **3.1** In `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml`: remove the `ava-asis-test-qa` agent entry (id + file + skill lines)
- [X] **3.2** In the same file: remove the `ava-asis-baseline-test-generator` agent entry
- [X] **3.3** In the same file: remove the `ava-asis-golden-dataset-capture` agent entry
- [X] **3.4** In the same file: update any total agent count field if present
- [X] **3.5** [P] In `src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md`: remove the 8 discontinued artifact path entries: `test-map.md`, `test-coverage-asis.md`, `test-baseline.md`, `test-cases-baseline-asis.md`, `test-cases-baseline-asis.json`, `golden-dataset.json`, `golden-dataset-capture-report.md`, `golden-dataset-execution-log.md`
- [X] **3.6** [P] Confirm `test-gaps.md` path entry remains in `output-paths.md`

---

## Category 4 — Documentation Cleanup (8 files)

Depends on Category 3. All tasks in this category are parallelizable with each other.

- [X] **4.1** [P] `.github/copilot-instructions.md` — remove 3 rows from the F1 AS-IS Diagnostic skills table: `@ava-asis-test-qa`, `@ava-asis-baseline-test-generator`, `@ava-asis-golden-dataset-capture`
- [X] **4.2** [P] `README.md` — remove all mentions of the 3 discontinued agents (any agent listing, skill description, or pipeline step)
- [X] **4.3** [P] `docs/full-pipeline-guide.md` — remove all references to the 3 discontinued agents and the `golden_dataset_enabled_asis` flag
- [X] **4.4** [P] `docs/guia-execucao-fluxo-agentes.md` — remove agent references and `golden_dataset_enabled_asis` from execution flow diagrams and tables
- [X] **4.5** [P] `docs/agents-catalog.md` — remove the 3 complete catalog entries (each entry includes: agent name, description, output block, input block)
- [X] **4.6** [P] `docs/asis-diagnostic-io-map.md` — remove 8 artifact output entries and the 3 discontinued agent boxes/rows; retain `test-gaps.md` attributed to `ava-asis-bridge-fastqa` (Step 15)
- [X] **4.7** [P] `docs/summary-io-map.md` — remove data-flow entries for `test-map.md`, `test-baseline.md`, `test-coverage-asis.md`, `golden-dataset.json`; retain `test-gaps.md`
- [X] **4.8** [P] `docs/tobe-architecture-io-map.md` — remove `test-coverage-asis.md`, `test-baseline.md`, `test-map.md` as TO-BE input artifacts; replace with `test-gaps.md` where a gap-analysis input is referenced

---

## Category 5 — Summary Agent Files (2 `.md` files)

Depends on Category 3. Parallelizable with Categories 4 and 6.

- [X] **5.1** `src/modules/ava-fabric-agents/summary/agents/summary-agent.md` — update the `testMap` Data Source Mapping row: replace the full multi-fallback chain (`qa/test-map.md` → `qa/test-coverage-asis.md` → `qa/test-baseline.md` → AST) with: primary = `delphi-ast-raw/compressed/09_test_coverage.json` (`payload.test_findings[]` + `payload.counts.*`); fallback = `[AUSENTE]` for non-Delphi
- [X] **5.2** Same file — update the `testGaps` Data Source Mapping row: remove the fallback `(fallback: seção "Test Gap Analysis" dentro de qa/test-coverage-asis.md)`; keep only `qa/test-gaps.md` as source
- [X] **5.3** Same file — replace the 4-line Read block (`Read: asis/qa/test-map.md`, `Read: asis/qa/test-baseline.md`, `Read: asis/qa/test-gaps.md`, `Read: asis/qa/test-coverage-asis.md`) with 2 lines: `Read: asis/qa/test-gaps.md` and `Read: asis/delphi-ast-raw/compressed/09_test_coverage.json`
- [X] **5.4** Same file — update section structure reference: rename "Test Baseline ← qa/test-map.md + qa/test-baseline.md + qa/test-gaps.md + qa/test-coverage-asis.md" → "Test Gaps ← qa/test-gaps.md + delphi-ast-raw/compressed/09_test_coverage.json (Delphi)"
- [X] **5.5** `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md` — replace the full content of `Regra C — Arquivos de Teste` with the updated rule: references only `asis/qa/test-gaps.md` + `asis/delphi-ast-raw/compressed/09_test_coverage.json`; remove all references to `test-map.md`, `test-baseline.md`, `test-coverage-asis.md`, and `test-qa-asis.md`

---

## Category 6 — Summary Python Utilities (4 `.py` files)

Depends on Category 3. Parallelizable with Categories 4 and 5.

- [X] **6.1** [P] `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py` — remove all read/fallback code for: `asis/qa/test-map.md`, `asis/qa/test-baseline.md`, `asis/qa/test-coverage-asis.md`, `outputs/qa/golden-dataset.json`, `outputs/qa/golden-dataset-capture-report.md`, `outputs/qa/golden-dataset-execution-log.md`
- [X] **6.2** [P] Same file — retain read for `asis/qa/test-gaps.md`; add guarded read for `asis/delphi-ast-raw/compressed/09_test_coverage.json` (guard: `if os.path.exists(path)` before reading)
- [X] **6.3** [P] `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` — apply the same removals as 6.1 and same additions as 6.2
- [X] **6.4** [P] `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py` — remove synthesis/fallback logic for `test-map.md`, `test-baseline.md`, and `test-coverage-asis.md`; retain logic for `test-gaps.md`
- [X] **6.5** `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` — replace the validation issue message string from `"The Test Baseline is empty the information comes from: test-map.md · test-baseline.md · test-gaps.md · test-coverage-asis.md"` with `"The Test Gaps section is empty: the information comes from: test-gaps.md · delphi-ast-raw/compressed/09_test_coverage.json (Delphi projects)"`

---

## Category 7 — Post-Implementation Validation

Depends on all previous categories.

- [X] **7.1** Run validation check 1 — no discontinued agent references in active files:
  ```bash
  grep -r "ava-asis-test-qa\|ava-asis-baseline-test-generator\|ava-asis-golden-dataset-capture" \
    --include="*.md" --include="*.py" --include="*.yaml" \
    --exclude-dir=".git" --exclude-dir="specs" .
  ```
  **Expected**: zero matches

- [X] **7.2** Run validation check 2 — `golden_dataset_enabled_asis` fully removed:
  ```bash
  grep -r "golden_dataset_enabled_asis\|golden-dataset-capture\|golden_dataset" \
    --include="*.md" --include="*.py" --include="*.yaml" \
    --exclude-dir=".git" --exclude-dir="specs" .
  ```
  **Expected**: zero matches

- [X] **7.3** Run validation check 3 — `test-gaps.md` registered in `artifact_contracts` under `ava-asis-bridge-fastqa`:
  ```bash
  grep -A 10 "ava-asis-bridge-fastqa:" \
    src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md \
    | grep "test-gaps.md"
  ```
  **Expected**: ≥1 match

- [X] **7.4** Run validation check 4 — bridge-fastqa version bumped:
  ```bash
  grep "^version:" \
    src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md
  ```
  **Expected**: `version: "4.1.0"`

- [X] **7.5** Run validation check 5 — discontinued artifact paths absent from summary utilities:
  ```bash
  grep -rn "test-map\|test-baseline\|test-coverage-asis\|golden-dataset" \
    src/modules/ava-fabric-agents/summary/utils/
  ```
  **Expected**: zero matches

- [X] **7.6** Run validation check 6 — `validate_summary.py` updated message:
  ```bash
  grep "Test Gaps\|test-gaps" \
    src/modules/ava-fabric-agents/summary/utils/validate_summary.py
  ```
  **Expected**: match containing `test-gaps.md · delphi-ast-raw/compressed/09_test_coverage.json`

- [X] **7.7** Run validation check 7 — `module.yaml` clean:
  ```bash
  grep "ava-asis-test-qa\|ava-asis-baseline-test-generator\|ava-asis-golden-dataset-capture" \
    src/modules/ava-fabric-agents/asis-diagnostic/module.yaml
  ```
  **Expected**: zero matches

- [X] **7.8** Run validation check 8 — orchestrator counts updated:
  ```bash
  grep "Wave 2 (5 agents)\|7 agentes\|sub_agents_count.*13" \
    src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md
  ```
  **Expected**: ≥1 match for each count

---

## Dependency Graph

```
Category 1 (orchestrator-asis.md)
    │
    ├── Category 2 (bridge-fastqa-asis.md)
    │
    └── Category 3 (module.yaml + output-paths.md)
            │
            ├── Category 4 (8 documentation files)  ─┐
            ├── Category 5 (2 summary agent .md)     ─┤ parallel
            └── Category 6 (4 summary .py utils)     ─┘
                    │
                    └── Category 7 (validation)
```

---

## Completion Checklist

- [ ] All 7 categories complete
- [ ] `grep` checks in Category 7 all pass (zero / expected matches)
- [ ] `bridge-fastqa-asis.md` version is `4.1.0`
- [ ] `orchestrator-asis.md` version is `2.20.1`
- [ ] `test-gaps.md` in `artifact_contracts.ava-asis-bridge-fastqa.mandatory`
- [ ] No SKILL.md files deleted (discontinued agents remain as dead code on disk)
- [ ] `docs/agents-catalog.md` updated (3 entries removed)
