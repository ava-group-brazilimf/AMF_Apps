# Implementation Plan: ava-test-plan-tobe v4.0.0 — Consolidate Test Plan Artifacts

**Branch**: `[029-consolidate-test-plan-artifacts]` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Consolidate `ava-test-plan-tobe` to 4 core artifacts; eliminate 11 redundant outputs and all downstream references.

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-test-plan-tobe` |
| **Phase** | `F2` |
| **Module** | `ava-fabric-agents/tobe-architecture` |
| **Primary Requirement** | Reduce agent output contract from 15 to 4 artifacts; remove all generation logic, references, triggers, failure modes, and downstream consumer bindings for the 11 eliminated artifacts. |
| **Technical Approach** | Surgical deletion across 9 files: prune agent spec canonical sections, clean orchestrator I/O tables, excise summary builder parser code, update artifact-map registry, and align 4 documentation files. |

---

## Constitution Check

*GATE: Must pass before implementation. Justify gate failures in Complexity Tracking (section 9).*

### Constitution Gates

- [x] **Article I** — No technology versions hardcoded in agent body (N/A — this is agent instruction surgery, not codegen)
- [x] **Article II** — Frontmatter contains ONLY: `name`, `version`, `description`, `allowed-tools`
- [x] **Article II** — agent `name` matches pattern `^ava-[a-z0-9-]+$`
- [x] **Article III** — Phase placement valid (F2 agent, internal-only dispatch via orchestrator)
- [x] **Article IV** — Module-level `module.yaml` — NO CHANGE REQUIRED (existing agent, id unchanged)
- [x] **Article V** — Agent body language is Brazilian Portuguese (modified body retains Portuguese)
- [x] **Article VI** — BDD scenarios in spec section 4 (nominal + edge + gate paths)
- [x] **Article VII** — Security sub-pipeline impact: NEGATIVE — security-test-strategy.md eliminated; critical content references `security-architecture.md` instead
- [x] **Article VIII** — trace_id propagation: N/A (agent .md is an LLM prompt file)
- [x] **Article IX** — Clean Architecture: N/A — agent is an LLM prompt file
- [x] **Article X** — Version bump: MAJOR (4.0.0) — breaking change per SemVer
- [x] **Article XI** — Skill/Agent split: internal-only via orchestrator; SKILL.md exists but requires no behavioral change

### Quality Gate Check

- [x] No [NEEDS CLARIFICATION] markers remain in spec (clarified in Session 2026-07-24)
- [x] All outputs follow `projects/{project_name}/outputs/[phase]/...`
- [x] Downstream next_agent confirmed: `ava-tobe-orchestrator` dispatches this agent; no downstream agent directly consumes eliminated artifacts

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Runtime | N/A | Agent is an LLM prompt file (`.md`) |
| Language | Brazilian Portuguese (agent body) | Constitution Article V |
| Storage | Markdown artifacts on filesystem | Agent writes to `projects/{project_name}/outputs/tobe/...` |
| Testing | F5 QA agents (`ava-qa-scenario-generator`, `ava-qa-behavior-mapping`) | BDD traceability |
| Target Platform | VS Code + Copilot Chat agent framework | `.github/skills/` + `src/modules/ava-fabric-agents/` |
| Constraints | Zero dangling references after changeset | Eliminated artifacts must not appear in any file |
| Scale/Scope | 9 files, ~50 discrete edits estimated | Agent spec (~1022 lines), orchestrator, summary, build script, artifact-map, 4 docs |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

```
F1 -> ava-summary -> F2 (TO-BE Architecture)
                     -> ava-tobe-orchestrator
                        -> ava-tobe-architecture-design
                        -> ava-tobe-adr
                        -> ava-tobe-measure-size
                        -> ava-tobe-migration-plan
                        -> ava-test-plan-tobe  <- [THIS AGENT]
                        -> ava-tobe-user-journeys
                        -> ...
                     -> ava-summary
```

**Quality gate at this phase**: Summary Validator (55 rules, 10 categories) runs after F2 completes.

**Conditions for `human_gate_required: true`**:
- `business-rules.md` absent AND `traceability-matrix.md` requested by config
- Output contract violation (e.g., eliminated artifact still generated)

---

## 3. Clean Architecture Alignment

N/A — this agent is an LLM prompt instruction file (`.md`), not generated code. Agent produces markdown artifacts consumed by humans and downstream agents.

---

## 4. Agent File Structure

**Skill/Agent split** (Constitution Article XI):

```
# SKILL.md — NO BEHAVIORAL CHANGE (routing wrapper unchanged)
.github/skills/ava-test-plan-tobe/SKILL.md

# Agent spec — MAJOR SURGERY REQUIRED
src/modules/ava-fabric-agents/tobe-architecture/agents/test-plan-tobe.md
    +-- frontmatter: version bump 4.0.0
    +-- Output Contract: 4 YAML entries (was 15)
    +-- Skills subsections: remove Smoke Tests, Cobertura, Performance & Carga, Testes de Tela
    +-- Canonical Template: remove sections 7 (Smoke Tests), 8 (Load Test Plan), 14 (Security Test Strategy), 16 (Coverage Gap Strategy)
    +-- Execution Steps: remove Step 5c (Smoke Suite per Wave), Step 6b (Load Test Plan), Step SKW (entire smoke suite block)
    +-- Failure Modes: remove rows referencing eliminated artifacts
    +-- Triggers/Menu: remove SKW, CG, LD, UI, SS, ST triggers
    +-- Azure DevOps pipeline validation: prune section list (remove §7, §8, §14, §16, §7.2) and remove orphaned script blocks
```

**Dispatch mode**: internal-only (orchestrator dispatches)

---

## 5. module.yaml Impact

**NO CHANGE REQUIRED.** Agent `ava-test-plan-tobe` is already registered in:

```
src/modules/ava-fabric-agents/tobe-architecture/module.yaml
```

The agent ID, file path, and skill name are unchanged. Only the agent's internal behavior and output contract change.

---

## 6. Observability & Trace Propagation

N/A — IMFAI agents are LLM prompt files. Trace context is handled implicitly by the orchestrator and SKILL.md wrapper through `shared-context.md`.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | NO | Input contract unchanged |
| `agent-result.schema.json` | NO | Output envelope unchanged; only artifact paths within `artifacts[]` array change |

> Note: The `artifacts` array in `AgentResult` will contain 4 entries instead of 15. This is a data content change, not a schema change.

---

## 8. Implementation Phases

### Phase 0 — Research & Gap Analysis

**Goal**: Confirm complete inventory of all references to eliminated artifacts across the codebase.

**Tasks**:
1. Run `grep_search` for each eliminated artifact name across `src/` and `docs/`
2. Document exact line numbers and contexts for each match
3. Classify each match as: (a) generation action, (b) reference/mention, (c) validation/gate, (d) downstream consumer binding

**Output**: `research.md` — inventory of all matches with classification

---

### Phase 1 — Agent Spec Surgery (`test-plan-tobe.md`)

**Goal**: Reduce agent to 4-artifact focus; excise all eliminated artifact logic.

**Sub-tasks**:

1.1 **Frontmatter & Output Contract**
- Bump `version` to `4.0.0`
- Update `description` to mention only 4 artifacts
- Reduce `## Output Contract` YAML block to 4 entries

1.2 **Skills Subsections**
- Remove `### Smoke Tests` subsection
- Remove `### Cobertura` subsection (or reduce to inline mention)
- Remove `### Performance & Carga` subsection
- Remove `### Testes de Tela` subsection

1.3 **Canonical Template Sections**
- Remove Section 7 (Smoke Tests)
- Remove Section 8 (Load Test Plan)
- Remove Section 14 (Security Test Strategy)
- Remove Section 16 (Coverage Gap Strategy)
- Retitle/restructure remaining sections to close numbering gaps

1.4 **Execution Steps**
- Remove Step 5c (Smoke Suite per Wave generation)
- Remove Step 6b (Load Test Plan generation)
- Remove entire Step SKW block (smoke suite dispatch)
- Remove Step 6c if it generated `coverage-gap-strategy.md`

1.5 **Triggers & Menu**
- Remove `SKW`, `CG`, `LD`, `UI`, `SS`, `ST` triggers from table
- Remove activation phrases for eliminated artifacts from `description`

1.6 **Failure Modes**
- Remove rows referencing `wave-test-plan.md`, `smoke-tests.md`, smoke suites, `load-test-plan.md`, `ui-test-plan.md`, `coverage-strategy.md`, `bdd-coverage-per-wave.md`, `security-test-strategy.md`, `coverage-gap-strategy.md`
- Update remaining rows that mention eliminated artifacts in their "Mitigation" or "Error Message" columns

1.7 **Pipeline Validation Block**
- Remove `### 7.2 Suite por Wave` from section validation list
- Remove §7, §8, §14, §16 from the `for SECTION in ...` loop
- Remove orphaned `- script: |` blocks validating smoke-suite files and coverage-gap-strategy

1.8 **Completeness Gate (NEW)**
- Add gate step validating 4 retained artifacts exist and are non-empty
- Exempt `traceability-matrix.md` when `business-rules.md` is absent

**Output**: `test-plan-tobe.md` — pruned to 4 artifacts, version 4.0.0

---

### Phase 2 — Orchestrator Update (`orchestrator-tobe.md`)

**Goal**: Align orchestrator's Fase 6 outputs and Fase 7.8 inputs with reduced contract.

**Sub-tasks**:

2.1 **Fase 6 Outputs Table**
- Remove `wave-test-plan.md` row
- Remove `smoke-tests.md` row
- Remove `smoke-suite-wave-{N}.md` row
- Remove `smoke-suite-wave-{N}.yml` row
- Remove `smoke-suite-wave-{N}.github.yml` row
- Remove `bdd-coverage-per-wave.md` row
- Remove `security-test-strategy.md` row

2.2 **Fase 7.8 Inputs Table**
- Remove `wave-test-plan.md` row
- Remove `security-test-strategy.md` row
- Remove `coverage-gap-strategy.md` row

2.3 **Dispatch Logic**
- Remove trigger SKW dispatch from orchestrator's decision table
- Remove references to eliminated artifacts in orchestrator comments

**Output**: `orchestrator-tobe.md` — synchronized with 4-artifact contract

---

### Phase 3 — Summary Agent Update (`summary-agent.md`)

**Goal**: Remove parsing logic for eliminated artifact `coverage-gap-strategy.md`.

**Sub-tasks**:

3.1 **D.* Field Definitions**
- Remove `D.coverageGapStrategy` row from field definition table (~line 253)

3.2 **Parser Section**
- Remove parser block that reads `coverage-gap-strategy.md` (~line 284)

**Output**: `summary-agent.md` — no references to `coverage-gap-strategy.md`

---

### Phase 4 — Build Script Update (`build_summary_comprehensive.py`)

**Goal**: Remove Python parsing and JS injection for `coverage-gap-strategy.md`.

**Sub-tasks**:

4.1 **Parser Block**
- Remove `_cgs_path` resolution (around line where `coverage-gap-strategy.md` is located)
- Remove "Matriz Consolidada" table parsing into `coverage_gap_strategy` list (~lines 7315–7343)

4.2 **JS Injection**
- Remove `coverageGapStrategy` key from the dictionary injected into the HTML template (~line 7860)

**Output**: `build_summary_comprehensive.py` — no `_cgs_path` or `coverageGapStrategy`

---

### Phase 5 — Artifact Map Update (`artifact-map.yaml`)

**Goal**: Remove eliminated entries from `ava-test-plan-tobe` outputs_map.

**Sub-tasks**:

5.1 **outputs_map**
- Remove `smoke_suite_wave_spec` entry
- Remove `smoke_suite_wave_azdo` entry
- Remove `smoke_suite_wave_github` entry
- Remove `load_tests` entry
- Remove `ui_tests` entry
- Remove `coverage_gap_strategy` entry

**Output**: `artifact-map.yaml` — only 4 entries under `ava-test-plan-tobe`

---

### Phase 6 — Documentation Files Update

**Goal**: Remove all references to eliminated artifacts from human-readable docs.

**Sub-tasks**:

6.1 **`docs/agents-catalog.md`**
- Remove `ava-test-plan-tobe` row references to eliminated artifacts in the catalog table

6.2 **`docs/summary-io-map.md`**
- Remove `D.coverageGapStrategy` from the summary input map
- Remove `coverage-gap-strategy.md` from artifact-to-summary mappings

6.3 **`docs/tobe-architecture-io-map.md`**
- Remove eliminated artifacts from the F2 output map
- Update `ava-test-plan-tobe` entry to list only 4 artifacts

6.4 **`docs/tobe-input-artifacts-existence-check.md`**
- Remove eliminated artifacts from the existence check list
- Update check commands/validation to expect only 4 artifacts

**Output**: 4 documentation files — synchronized with reduced contract

---

## 9. Complexity Tracking

> No Constitution violations. All gates pass. No cross-layer coupling. This is a pure deletion/refactoring task with zero new code.

| Complexity Item | Justification |
|---|---|
| 9 files touched | Required because eliminated artifacts had generation logic, references, and downstream consumer bindings across all these files |
| Surgical deletion (not bulk replacement) | Each reference has unique surrounding context; bulk replacement would risk corrupting unrelated content |
| Version MAJOR bump | Per SemVer, removing 11 artifacts from output contract is a breaking change for any consumer expecting them |

---

## 10. Validation & Verification

### 10.1 Pre-Implementation Baseline
- Run `grep_search` for all 11 eliminated artifact names across `src/` and `docs/`
- Record match count per artifact per file

### 10.2 Post-Implementation Verification
- Re-run identical `grep_search`; verify zero matches
- Verify `ava-test-plan-tobe.md` has exactly 4 entries in Output Contract YAML block
- Verify `ava-test-plan-tobe.md` frontmatter version is `4.0.0`
- Verify `orchestrator-tobe.md` Fase 6 outputs table has no eliminated artifacts
- Verify `summary-agent.md` has no `coverageGapStrategy` field
- Verify `build_summary_comprehensive.py` has no `_cgs_path` variable
- Verify `artifact-map.yaml` has exactly 4 entries under `ava-test-plan-tobe`

### 10.3 Regression Test
- Check that no references to retained 4 artifacts were accidentally removed
- Verify `test-plan.md`, `traceability-matrix.md`, `automatable-test-cases.md`, `functional-test-matrix.md` still appear correctly in all files

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Accidental deletion of retained artifact references | Medium | High | Use exact-match `replace_string_in_file` with 3-5 lines of context; verify with post-implementation grep |
| Orphaned script blocks remain in `test-plan-tobe.md` pipeline validation | Medium | Medium | Parse YAML structure during deletion; verify `displayName` blocks are paired correctly |
| `build_summary_comprehensive.py` breaks due to missing `coverageGapStrategy` key in template | Low | High | Remove both parser AND injection; check template does not hardcode the key |
| Documentation becomes stale beyond the 4 targeted files | Low | Medium | Run global grep for eliminated artifact names as final validation step |

---

## 12. Rollback Plan

If validation fails:
1. Do not commit; discard unstaged changes
2. Re-run baseline `grep_search` to confirm pre-change state
3. Re-apply edits one file at a time, verifying after each
4. Escalate to `human_gate_required` if any reference cannot be safely removed

---

## Post-Execution Hooks

**Optional Hook**: `speckit.agent-context.update`  
Command: `/speckit.agent-context.update`  
Description: Refresh agent context after planning

To execute: `/speckit.agent-context.update`
