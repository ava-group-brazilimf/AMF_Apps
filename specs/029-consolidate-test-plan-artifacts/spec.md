# Agent Specification: Consolidate Test Plan Artifacts

**Feature Branch**: `[029-consolidate-test-plan-artifacts]`
**Created**: 2026-07-24
**Status**: Draft
**Change Type**: modify-existing
**Input**: Agent description: "Consolidate test plan artifacts to 4 core deliverables — eliminate 11 redundant outputs from ava-test-plan-tobe and downstream consumers."

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-test-plan-tobe` |
| **Version** | `4.0.0` (MAJOR — breaking change: 11 artifacts eliminated, output contract reduced from 15 to 4) |
| **Phase** | `F2` |
| **Module** | `ava-fabric-agents/tobe-architecture` |
| **Role** | Consolidate test planning to 4 core artifacts and eliminate 11 redundant outputs. |
| **Skill** | `ava-test-plan-tobe` |
| **Dispatch** | internal-only via orchestrator |

> **Change Type is `modify-existing`**:
> - Reference the existing agent file path: `src/modules/ava-fabric-agents/tobe-architecture/agents/test-plan-tobe.md`
> - Version bump: MAJOR (breaking change: 11 artifacts eliminated, output contract reduced from 15 to 4)
> - The module.yaml entry already exists — Category 4 tasks are N/A
> - The SKILL.md already exists — Category 1.5 is N/A

---

## 2. Agent Frontmatter

The agent `.md` file opens with YAML frontmatter (Constitution Article II):

```yaml
---
name: "ava-test-plan-tobe"
version: "4.0.0"
description: |
  Gera o plano de testes TO-BE focado nos 4 artefatos essenciais: test-plan.md,
  traceability-matrix.md, automatable-test-cases.md e functional-test-matrix.md.
  Consolida pirâmide de testes, thresholds, CI strategy e rastreabilidade BR/FR.
  Ativa com: "plano de testes TO-BE", "test plan", "pirâmide de testes",
  "cobertura", "thresholds", "rastreabilidade", "traceability matrix", "TM", "AC", "TP".
allowed-tools: Read, Write, Edit, Glob, Grep
---
```

Do NOT include `phase`, `module`, `inputs`, `outputs`, or `dependencies` in frontmatter.
These are not valid frontmatter fields in IMFAI agents.

---

## 3. Output Contract

The `## Output Contract` YAML block in the agent body (Constitution Article II):

```yaml
## Output Contract
```yaml
outputs:
  test_plan:             "projects/{project_name}/outputs/tobe/qa/test-plan.md"
  functional_tests:      "projects/{project_name}/outputs/tobe/tests/functional-test-matrix.md"
  traceability_matrix:   "projects/{project_name}/outputs/tobe/tests/traceability-matrix.md"
  automatable_cases:     "projects/{project_name}/outputs/tobe/tests/automatable-test-cases.md"
```
```

> **New file vs. append decision**: This agent writes new files.
> Appending to an existing contract is NOT needed — the 4 artifacts are standalone.

Path conventions:
| Phase | Output folder |
|---|---|
| F2 (TO-BE arch) | `projects/{project_name}/outputs/tobe/qa/` (test-plan) |
| F2 (TO-BE tests) | `projects/{project_name}/outputs/tobe/tests/` (matrix + cases) |

---

## 4. User Scenarios (Given-When-Then)

> **Language convention**: Story descriptions (`**Story**:`) may be written in
> Brazilian Portuguese — IMFAI developers and client stakeholders read them.
> Acceptance scenarios (Given/When/Then) MUST be in English for BDD traceability
> with F5 QA agents (`ava-qa-behavior-mapping`, `ava-qa-scenario-generator`).

### Scenario 1 - Nominal Path (Priority: P1)

**Story**: As the migration orchestrator, I want `ava-test-plan-tobe` to produce only the 4 essential test artifacts so that downstream agents consume a focused, coherent contract.

**Why this priority**: Eliminates artifact bloat, reduces maintenance surface, and aligns with the lean pipeline principle.

**Acceptance Scenarios**:

1. **Given** the TO-BE pipeline has generated architecture and wave plan artifacts, **When** the agent executes, **Then** it produces `test-plan.md`, `traceability-matrix.md`, `automatable-test-cases.md` and `functional-test-matrix.md`, and `AgentResult.success` is true.
2. **Given** the above, **When** execution completes, **Then** no eliminated artifacts (`wave-test-plan.md`, `smoke-tests.md`, smoke suites, `load-test-plan.md`, `ui-test-plan.md`, `coverage-strategy.md`, `bdd-coverage-per-wave.md`, `security-test-strategy.md`, `coverage-gap-strategy.md`) are referenced in the output contract or generated.

### Scenario 2 - Edge Case: Missing Input Artifacts (Priority: P2)

**Why this priority**: Defensive handling of incomplete inputs.

**Acceptance Scenarios**:

1. **Given** `business-rules.md` is absent, **When** the agent executes, **Then** it skips traceability generation, logs `[MISSING INPUT]`, and still produces the remaining 3 artifacts.
2. **Given** the above, **Then** `AgentResult.risk.level` is 'low' and no artifacts are left empty.

### Scenario 3 - Quality Gate: Downstream Integrity (Priority: P1)

**Why this priority**: Safety gate — must never break consumers.

**Acceptance Scenarios**:

1. **Given** the orchestrator, summary agent, and build script reference the agent's outputs, **When** the 11 eliminated artifacts are removed, **Then** all downstream files are updated simultaneously so no dangling references remain.
2. **Given** the above, **Then** `AgentResult.human_gate_required` is false and no orphan variables or sections exist in downstream parsers.

---

## 5. Quality Gate Requirements

- [x] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) (Article II)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [x] Agent registered in module-level `module.yaml` diff included in plan (Article IV)
- [x] All output paths use lowercase `{project_name}` and correct phase folder (Article II)
- [x] BDD scenarios cover nominal, edge, and gate paths (Article VI)
- [x] Security sub-pipeline impact assessed (Article VII)
- [x] No technology versions hardcoded (Article I)
- [x] Skill/Agent split declared: SKILL.md or internal-only with justification (Article XI)
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Phase orchestrator | `ava-tobe-orchestrator` | Must complete before this agent runs |
| Architecture Design TO-BE | `ava-tobe-architecture-design` | `architecture-blueprint.md` input |
| Migration Plan TO-BE | `ava-tobe-migration-plan` | `wave-plan.md` input |
| AS-IS Documentation | `ava-asis-documentation` | `business-rules.md` input |

---

## 7. Exclusions & Content Migration

- Smoke test suites, load tests, UI test plan, coverage strategy, BDD coverage per wave, security test strategy, coverage gap strategy — **eliminated from this agent's scope**
- `wave-test-plan.md` — **eliminated**; wave-level thresholds and entry gates now inline within `test-plan.md` Section 15
- **Content absorption strategy** (critical content retained, artifact file eliminated):
  - Wave-level thresholds / go-no-go gates → `test-plan.md` Section 15
  - Security test considerations → reference `security-architecture.md` (no duplication)
  - Smoke suite concepts / health checks → inline in `test-plan.md` CI strategy section
  - Coverage gap dimensions → absorbed into `functional-test-matrix.md` risk annotations
  - Load test baselines → reference `tech-framework-document.md` + `master-report.md` (no separate artifact)
- These were previously generated but never consumed by any downstream agent in the production pipeline (confirmed by gap analysis)

---

## 8. Assumptions

- The legacy repo is analyzed and AS-IS artifacts exist at the documented paths
- `project-config.yaml` exists at `projects/{project_name}/context/`
- Downstream consumers (orchestrator, summary, docs) will be updated in the same changeset to maintain coherence

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Artifacts produced | Exactly 4 paths in section 3 exist after execution |
| Contract compliance | AgentResult validates against agent-result.schema.json |
| No regression | `orchestrator-tobe.md`, `summary-agent.md`, `build_summary_comprehensive.py`, and 5 doc files are updated simultaneously without breaking references |
| Elimination verified | Zero references to the 11 eliminated artifacts remain in any project file |
| Gate accuracy | No `human_gate_required` triggered by artifact elimination |
| Completeness gate | Agent validates that all 4 retained artifacts exist and are non-empty before emitting `AgentResult.success`; `traceability-matrix.md` is exempted when `business-rules.md` is absent |

---

## Clarifications

### Session 2026-07-24

- **Q1**: Should content from eliminated artifacts be absorbed into retained artifacts or discarded?  
  **A**: Absorb critical content into retained artifacts. Wave-level thresholds → `test-plan.md` Section 15; security test considerations → reference `security-architecture.md`; smoke suite concepts → inline in `test-plan.md` CI strategy section.
- **Q2**: Deprecation or transition strategy for legacy pipelines expecting eliminated artifacts?  
  **A**: No special handling — assume all consumers are updated in the same changeset. Zero tolerance for dangling expectations.
- **Q3**: Version bump — minor (3.3.0) or major (4.0.0)?  
  **A**: `4.0.0` major bump. Eliminating 11 artifacts from the output contract is a breaking change under SemVer.
- **Q4**: Should the revised agent include a completeness gate validating the 4 retained artifacts exist and are non-empty?  
  **A**: Yes — add a gate step that validates all 4 retained artifacts exist and are non-empty (`test-plan.md`, `functional-test-matrix.md`, `automatable-test-cases.md`, and `traceability-matrix.md` when `business-rules.md` is present).
