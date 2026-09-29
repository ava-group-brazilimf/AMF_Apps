# Implementation Plan: Remove Agents ava-asis-test-qa, ava-asis-baseline-test-generator, ava-asis-golden-dataset-capture

**Branch**: `024-remove-test-qa-baseline-golden-agents` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/024-remove-test-qa-baseline-golden-agents/spec.md`

---

## Summary

Three AS-IS diagnostic agents (`ava-asis-test-qa`, `ava-asis-baseline-test-generator`, `ava-asis-golden-dataset-capture`) are retired from the F1 pipeline. Their 8 artifact outputs are removed. `test-gaps.md` is preserved and its production moves to `ava-asis-bridge-fastqa` (Output Contract extended, version 4.0.0 → 4.1.0, new Step 15 sub-step). The `golden_dataset_enabled_asis` flag is eliminated entirely. 18 files are modified; no new files are created.

---

## Technical Context

**Language/Version**: Markdown (agent `.md` files) + Python 3.x (summary utilities)

**Primary Dependencies**: None — cleanup/refactor of existing `.md` and `.py` files; no new packages

**Storage**: Files on disk under `projects/{project_name}/outputs/asis/qa/`

**Testing**: Manual post-edit grep validation (see Validation Checklist)

**Target Platform**: VS Code Copilot agent runtime

**Project Type**: Agent specification cleanup — content editing, no code generation

**Performance Goals**: N/A

**Constraints**: Must not break downstream consumers of `test-gaps.md`; `ava-asis-bridge-fastqa` `artifact_contracts` entry in `orchestrator-asis.md` must verify `qa/test-gaps.md`

**Scale/Scope**: 18 files; ~150 targeted line edits; 0 new files created

---

## Constitution Check

*GATE: Must pass before proceeding to task generation.*

| Article | Gate | Status | Notes |
|---|---|---|---|
| I | No hardcoded versions | ✅ PASS | No new version literals introduced |
| II | Agent contract standard | ✅ PASS | `bridge-fastqa-asis.md` MINOR bump follows SemVer; frontmatter unchanged |
| III | Pipeline execution contract | ✅ PASS | DAG dispatch schedule updated; bridge-fastqa remains non-blocking Phase B |
| IV | Module registration | ✅ PASS | 3 agents removed from `module.yaml`; no new agents added |
| V | Language convention | ✅ PASS | All agent `.md` edits maintain pt-BR |
| VI | Test-first agent behavior | ✅ PASS | Spec includes 4 BDD acceptance scenarios |
| VII | Security-first | ✅ PASS | No changes to security pipeline |
| VIII | Observability | ✅ PASS | bridge-fastqa observability call already present; `--version 4.1.0` reflects bump |
| IX | Clean Architecture | N/A | No generated code layer changes |
| X | Versioning | ✅ PASS | `bridge-fastqa-asis.md` → MINOR 4.1.0; `orchestrator-asis.md` → PATCH |
| XI | Skill/Agent split | ✅ PASS | 3 discontinued SKILL.md files become dead code (not deleted); bridge-fastqa SKILL.md unchanged |

No violations requiring Complexity Tracking entries.

---

## Project Structure

### Documentation (this feature)

```text
specs/024-remove-test-qa-baseline-golden-agents/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output (artifact inventory)
├── quickstart.md        ← Phase 1 output (validation guide)
└── tasks.md             ← Phase 2 output (/speckit.tasks — NOT created here)
```

### Files Modified (no new files created)

```text
# Documentation
README.md
.github/copilot-instructions.md
docs/full-pipeline-guide.md
docs/guia-execucao-fluxo-agentes.md
docs/agents-catalog.md
docs/asis-diagnostic-io-map.md
docs/summary-io-map.md
docs/tobe-architecture-io-map.md

# Module config
src/modules/ava-fabric-agents/asis-diagnostic/module.yaml
src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md

# Orchestrator (primary logic file)
src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md

# Bridge agent (Output Contract extension)
src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md

# Summary pipeline
src/modules/ava-fabric-agents/summary/agents/summary-agent.md
src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md
src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py
src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py
src/modules/ava-fabric-agents/summary/utils/remediate_summary.py
src/modules/ava-fabric-agents/summary/utils/validate_summary.py
```

**Structure Decision**: Cleanup-only. No new directories or files. Discontinued SKILL.md files remain on disk (dead code).

---

## Detailed Change Plan by File

### GROUP A — `orchestrator-asis.md` (18 edits)

| # | Location | Action | Detail |
|---|---|---|---|
| A-01 | `Agent Team Gerenciado` table | REMOVE rows | Delete `Test QA` row and `Golden Dataset Capture` row |
| A-02 | DAG ASCII diagram — Wave 2 block | REMOVE line | Delete `▶ test-qa ━━━━━━━━━━━┓` |
| A-03 | `dispatch_schedule.phase_a_wave2` | REMOVE from dispatch array | Remove `test-qa` entry + its comment line |
| A-04 | `dispatch_schedule.phase_b` | REMOVE two rules | Delete `test-qa:QA` and `golden-dataset-capture` dispatch rules |
| A-05 | `evaluate_phase_a_all()` — `active` array | REMOVE entry | Remove `"ava-asis-test-qa"` |
| A-06 | `artifact_contracts` | REMOVE blocks | Delete full `ava-asis-test-qa` and `ava-asis-golden-dataset-capture` contract blocks |
| A-07 | `artifact_contracts` — bridge-fastqa block | UPDATE | Add `qa/test-gaps.md`, `qa/gap-analysis.md`, `qa/test-cases.md` to mandatory list alongside existing `qa/test-plan.md` |
| A-08 | `Guard — golden_dataset_enabled_asis: false` | REMOVE entire block | Delete banner + `golden_dataset_status: SKIPPED` registration + C2c reference |
| A-09 | `Consistency Gate` — check C2c | REMOVE block | Delete `ARTIFACT-COMPLETE-GOLDEN-DATASET` check |
| A-10 | `Agent Completion Registry` — Agent IDs | REMOVE two IDs | Remove `ava-asis-test-qa`, `ava-asis-golden-dataset-capture` |
| A-11 | `Orchestration Completion Gate` | UPDATE count | "9 agentes" → "7 agentes" |
| A-12 | `Step 2` (Decompose) | REMOVE read | Remove `golden_dataset_enabled_asis` read + default comment |
| A-13 | `Step 3.2` streaming collect dispatch | REMOVE bullets | Remove `test-qa:QA` and `golden-dataset-capture` dispatch bullets |
| A-14 | `Verification Block — Pré-Consolidação` | REMOVE line | Remove `✓ test-qa → completed (test-map.md + test-coverage-asis.md)` |
| A-15 | Output Contract — `execution_timing.per_orchestrator` | REMOVE + UPDATE count | Remove `ava-asis-test-qa` sub-agent; `sub_agents_count`: 14 → 13 |
| A-16 | Workflow FP — `Validar Artefatos Críticos` | REMOVE + ADD | Remove 4 AG-04 lines; add single `test-gaps.md` WARN check attributed to bridge-fastqa Step 15 |
| A-17 | `Progress Tracker` TODO item `phase-a` | UPDATE label | "Wave 2 (6 agents)" → "Wave 2 (5 agents)" |
| A-18 | `Guardrails` section | REMOVE bullet | Remove bullet listing `test-qa:QA` as trigger for `golden-dataset-capture` |

**Version bump**: `orchestrator-asis.md` PATCH (2.20.0 → 2.20.1) — agent count and artifact_contracts change, no new behavior.

---

### GROUP B — `bridge-fastqa-asis.md` (4 edits)

| # | Location | Action | Detail |
|---|---|---|---|
| B-01 | Frontmatter `version` | BUMP | `4.0.0` → `4.1.0` (MINOR — new output artifact) |
| B-02 | `QA Output Directory` table | ADD row | `Test Gaps \| projects/{project_name}/outputs/asis/qa/test-gaps.md \| Derivado de gap_analysis/PBI-{N}_gaps.md + 01_business_rules.json \| Gaps TG-NNN com severidade/risco` |
| B-03 | `Step 15` — `publish_qa_artifacts` procedure | ADD sub-step | Add `# --- 4. Gerar e publicar test-gaps.md ---` block with `transform_gaps_to_test_gaps()` call + TG-NNN output format template |
| B-04 | `Step 16` — Completion Signal | UPDATE | Add `Test Gaps: projects/{project_name}/outputs/asis/qa/test-gaps.md [{status_qa_tg}]` to QA Output Publication block |

**`transform_gaps_to_test_gaps` output format (mandatory)**:

```markdown
# Test Gaps — {project_name} (PBI-{N})

**Gerado por**: ava-asis-bridge-fastqa v4.1.0 — Step 15
**PBI Origem**: PBI-{N}

| ID | Descrição | Categoria | Módulo | Risco | Recomendação |
|----|-----------|-----------|--------|-------|--------------|
| TG-001 | {gap_description} | {funcional/validação/integração} | {form_name ou unit} | {P0/P1/P2} | {ação recomendada} |
```

Severity mapping: `crítico` → `P0`, `médio` → `P1`, `baixo` → `P2`.

---

### GROUP C — Module Config (2 files)

| # | File | Action | Detail |
|---|---|---|---|
| C-01 | `asis-diagnostic/module.yaml` | REMOVE 3 agent entries | Delete `ava-asis-test-qa`, `ava-asis-baseline-test-generator`, `ava-asis-golden-dataset-capture`; update agent count |
| C-02 | `asis-diagnostic/shared/output-paths.md` | REMOVE 8 path entries | Remove `test-map.md`, `test-coverage-asis.md`, `test-baseline.md`, `test-cases-baseline-asis.md`, `test-cases-baseline-asis.json`, `golden-dataset.json`, `golden-dataset-capture-report.md`, `golden-dataset-execution-log.md`; retain `test-gaps.md` |

---

### GROUP D — Documentation (8 files)

| # | File | Action | Detail |
|---|---|---|---|
| D-01 | `.github/copilot-instructions.md` | REMOVE 3 table rows | `@ava-asis-test-qa`, `@ava-asis-baseline-test-generator`, `@ava-asis-golden-dataset-capture` from F1 skills table |
| D-02 | `README.md` | REMOVE references | All mentions of the 3 discontinued agents |
| D-03 | `docs/full-pipeline-guide.md` | REMOVE references | Agents + `golden_dataset_enabled_asis` flag |
| D-04 | `docs/guia-execucao-fluxo-agentes.md` | REMOVE references | Agents + flag from execution flow |
| D-05 | `docs/agents-catalog.md` | REMOVE 3 catalog entries | Full entry blocks (name, description, outputs, inputs) for each discontinued agent |
| D-06 | `docs/asis-diagnostic-io-map.md` | REMOVE + UPDATE | Remove 8 artifact entries + 3 agent boxes; retain `test-gaps.md` attributed to `ava-asis-bridge-fastqa` |
| D-07 | `docs/summary-io-map.md` | REMOVE + RETAIN | Remove `test-map.md`, `test-baseline.md`, `test-coverage-asis.md`, `golden-dataset.json` data-flow entries; retain `test-gaps.md` |
| D-08 | `docs/tobe-architecture-io-map.md` | REMOVE + REPLACE | Remove `test-coverage-asis.md`, `test-baseline.md`, `test-map.md` as TO-BE inputs; replace with `test-gaps.md` where gap-analysis input is referenced |

---

### GROUP E — Summary Pipeline (6 edits across 5 files)

| # | File | Action | Detail |
|---|---|---|---|
| E-01 | `summary/agents/summary-agent.md` | UPDATE 4 locations | (1) `testMap` row: replace multi-fallback with `09_test_coverage.json` primary + `[AUSENTE]` fallback; (2) `testGaps` row: remove `test-coverage-asis.md` fallback; (3) Read block: replace 4 reads with 2; (4) section structure ref: rename "Test Baseline" → "Test Gaps" |
| E-02 | `summary/agents/summary-remediation-agent.md` | REPLACE Regra C block | Rewrite to reference only `test-gaps.md` + `09_test_coverage.json`; remove all refs to `test-map.md`, `test-baseline.md`, `test-coverage-asis.md`, `test-qa-asis.md` |
| E-03 | `summary/utils/build_summary_complete.py` | REMOVE + ADD | Remove reads/fallbacks for 6 discontinued paths; retain `test-gaps.md`; add guarded `09_test_coverage.json` read |
| E-04 | `summary/utils/build_summary_comprehensive.py` | REMOVE + ADD | Same as E-03 |
| E-05 | `summary/utils/remediate_summary.py` | REMOVE | Remove synthesis logic for `test-map.md`, `test-baseline.md`, `test-coverage-asis.md`; retain `test-gaps.md` |
| E-06 | `summary/utils/validate_summary.py` | REPLACE issue message | Old: `"Test Baseline is empty … test-map.md · test-baseline.md · test-gaps.md · test-coverage-asis.md"` → New: `"Test Gaps section is empty: … test-gaps.md · delphi-ast-raw/compressed/09_test_coverage.json (Delphi projects)"` |

---

## Execution Order

```
1. GROUP A  — orchestrator-asis.md       (central DAG + artifact_contracts)
2. GROUP B  — bridge-fastqa-asis.md      (Output Contract extension)
3. GROUP C  — module.yaml + output-paths (config cleanup)
4. GROUP D  — 8 documentation files      (parallelisable within group)
5. GROUP E  — 5 summary files            (parallelisable within group)
```

---

## Validation Checklist (post-implementation)

```bash
# 1. No references to discontinued agents in active files
grep -r "ava-asis-test-qa\|ava-asis-baseline-test-generator\|ava-asis-golden-dataset-capture" \
  --include="*.md" --include="*.py" --include="*.yaml" \
  --exclude-dir=".git" --exclude-dir="specs" .

# 2. golden_dataset_enabled_asis fully removed
grep -r "golden_dataset_enabled_asis\|golden-dataset-capture\|golden_dataset" \
  --include="*.md" --include="*.py" --include="*.yaml" \
  --exclude-dir=".git" --exclude-dir="specs" .

# 3. test-gaps.md in orchestrator artifact_contracts under bridge-fastqa
grep "test-gaps.md" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md

# 4. bridge-fastqa version updated
grep "^version:" \
  src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md
# Expected: version: "4.1.0"

# 5. Discontinued artifact paths not in summary utils
grep -r "test-map\|test-baseline\|test-coverage-asis\|golden-dataset" \
  src/modules/ava-fabric-agents/summary/utils/
```

Expected: (1) zero matches, (2) zero matches, (3) ≥1 match, (4) `version: "4.1.0"`, (5) zero matches.


---

## 9. Complexity Tracking

| Gate | Failure Reason | Justification | Mitigating Controls |
|---|---|---|---|
| [GATE_NAME] | [What failed] | [Why acceptable] | [How risk managed] |

---

## 10. Test Strategy

| Test Type | Tool | Target |
|---|---|---|
| Contract (input) | JSON Schema | 100% of AgentTask paths |
| Contract (output) | JSON Schema | 100% of AgentResult paths |
| Nominal BDD | xUnit | Spec section 4 Scenario 1 |
| Edge case BDD | xUnit | Spec section 4 Scenario 2 |
| Gate trigger | xUnit | Spec section 4 Scenario 3 |
| Regression | Existing suite | No existing agent broken |
