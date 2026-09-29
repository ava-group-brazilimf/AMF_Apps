# Implementation Plan: Bridge FastQA AST Simplification

**Branch**: `023-bridge-fastqa-ast-simplification` | **Date**: 2026-07-19 | **Spec**: [spec.md](spec.md)

---

## Summary

`ava-asis-bridge-fastqa` (v3.3.0) is rewritten to v4.0.0 across three dimensions:

1. **Input contract** — replaces prose documentation artifacts (`functional-requirements.md`, `business-rules.md`, four optional doc artifacts) with three deterministic AST JSON files (`01_business_rules.json`, `02_form_business_rules.json`, `03_database_rules.json`). A two-level path resolution (`compressed/` → `extraction/`) with hard stop replaces the previous soft-dependency gate.

2. **Lean FastQA pipeline** — eliminates three non-essential steps (`estimate_effort`, `ac_scope_analysis`, `validate_scenarios`); Element 2 goes from 5 to 4 steps and Element 3 from 4 to 2 steps; total steps 1–18 become 1–16.

3. **Lean test-plan.md template** — reduces from 9 to 5 sections, retaining only content directly derivable from the three AST inputs; a new §4 Test Coverage Map traceability table replaces §§4–8.

Secondary changes: `orchestrator-asis.md` artifact contract and dispatch prompt updated; `docs/asis-diagnostic-io-map.md` bridge-fastqa entry updated.

---

## Technical Context

**Language/Version**: Markdown (LLM agent spec), YAML
**Primary Dependencies**: Three Delphi AST JSON files produced by `run_delphi_ast_analysis.py` Step 0
**Storage**: `projects/{project_name}/outputs/asis/delphi-ast-raw/{compressed,extraction}/`
**Testing**: Grep-based absence/presence checks; structural content checks
**Target Platform**: LLM execution environment (GitHub Copilot agent mode)
**Project Type**: Modify-existing agent spec (`.md` file rewrite)
**Constraints**: Agent spec body MUST remain in Brazilian Portuguese (Constitution Art. V); no new files created
**Scale/Scope**: 1 full rewrite + 2 targeted edits

---

## Constitution Check

| Article | Applicable? | Status |
|---|---|---|
| I — Configuration-Driven | No | ✅ N/A — no new hardcoded tech versions |
| II — Agent Contract Standard | Yes — MAJOR version bump | ✅ Frontmatter updated to v4.0.0; contract fields valid |
| III — Pipeline Execution Contract | No | ✅ N/A — bridge-fastqa is non-blocking; pipeline order unchanged |
| IV — Module Registration | No | ✅ `module.yaml` entry already exists; no new agent registered |
| V — Language Convention | Yes | ✅ Agent body stays in pt-BR; spec/plan in English |
| VI — Test-First | Satisfied | ✅ BDD scenarios in spec §6 cover all change dimensions |
| VII — Security-First | No | ✅ N/A — no new network calls or credentials |
| XI — Skill/Agent Split | No | ✅ Bridge-fastqa remains internal-only; no SKILL.md change |

**Gate result: PROCEED** — No violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/023-bridge-fastqa-ast-simplification/
├── plan.md          ← This file
├── spec.md          ← Feature spec
├── research.md      ← Phase 0 decisions
├── data-model.md    ← Exact change manifest per file
├── quickstart.md    ← Validation commands
└── checklists/
    └── requirements.md
```

### Files to be edited (no new files created)

```text
src/modules/ava-fabric-agents/asis-diagnostic/agents/
└── bridge-fastqa-asis.md                   [A1]  ← FULL REWRITE

src/modules/ava-fabric-agents/asis-diagnostic/agents/
└── orchestrator-asis.md                    [B1]  ← 3 targeted edits

docs/
└── asis-diagnostic-io-map.md              [C1]  ← 3 targeted edits
```

---

## Execution Order

Changes are grouped by dependency. Apply tiers in order; within a tier, edits are independent.

### Tier 1 — Core agent rewrite (the change owner)

| ID  | File | Edit | Risk |
|-----|------|------|------|
| A1  | `agents/bridge-fastqa-asis.md` | Full rewrite: frontmatter v4.0.0, new Input Contract (AST JSONs), new Dependency Gate, Steps 1–16 (6 steps removed/renumbered), lean test-plan template (5 sections), updated Guardrails and FastQA Integration Notes | **High** |

Apply A1 as a complete file replacement. See `data-model.md` §A for the section-by-section breakdown.

### Tier 2 — Orchestrator sync (apply after A1)

| ID  | File | Edit | Risk |
|-----|------|------|------|
| B1a | `orchestrator-asis.md` | `artifact_contracts.ava-asis-bridge-fastqa.external_mandatory` — remove 3 eliminated output entries (`estimate_effort/`, `requirements_analysis/*_ac_scope.md`, `test_cases/*_validation_report.md`) | Low |
| B1b | `orchestrator-asis.md` | `dispatch_bridge_fastqa()` Step C — update `v3.1.0→v4.0.0` and `18 Steps→16 Steps` in SubAgent prompt text | Low |
| B1c | `orchestrator-asis.md` | `size_threshold` comment — update "9 seções" → "5 seções"; update threshold `5000→3000` bytes | Low |

### Tier 3 — IO map documentation

| ID  | File | Edit | Risk |
|-----|------|------|------|
| C1a | `docs/asis-diagnostic-io-map.md` | `### ava-asis-bridge-fastqa` **Inputs** — replace doc-artifact list with AST JSON primary inputs + two-level path resolution description + hard stop note | Medium |
| C1b | `docs/asis-diagnostic-io-map.md` | `### ava-asis-bridge-fastqa` **Outputs** — remove three eliminated artifacts from the list | Low |
| C1c | `docs/asis-diagnostic-io-map.md` | §5 Cross-Agent Consumption table — update bridge-fastqa row from "documentation (2 mandatory + 4 optional)" to "AST JSON artifacts (3 mandatory — compressed/ or extraction/)" | Low |

---

## Post-Implementation Verification

See `quickstart.md` for the full validation script. Summary:

1. `grep -c "functional-requirements.md" bridge-fastqa-asis.md` → 0 (input removed)
2. `grep -c "business-rules.md" bridge-fastqa-asis.md` → 0 (input removed)
3. `grep -c "estimate_effort" bridge-fastqa-asis.md` → 0 (step eliminated)
4. `grep -c "ac_scope_analysis" bridge-fastqa-asis.md` → 0 (step eliminated)
5. `grep -c "validate_scenarios" bridge-fastqa-asis.md` → 0 (step eliminated)
6. `grep -c "01_business_rules.json" bridge-fastqa-asis.md` → ≥ 2 (new primary input)
7. `grep -c "version.*4.0.0" bridge-fastqa-asis.md` → 1 (frontmatter)
8. `grep -c "v3.1.0" orchestrator-asis.md` → 0 in bridge dispatch block
9. `grep -c "estimate_effort.*PBI" orchestrator-asis.md` → 0 in external_mandatory

---

## Complexity Tracking

| Gate | Failure | Justification | Mitigating Control |
|---|---|---|---|
| Article II MAJOR bump | Input Contract fundamentally changed (new primary sources, removed optional artifacts) | The AST JSONs are deterministic machine-generated artifacts that are more reliable than prose docs derived from the same source — removing the doc dependency makes the agent more robust | Version bump clearly documented; downstream orchestrator artifact_contracts updated in same change set |

---

## Test Strategy

| Test Type | Approach | Target |
|---|---|---|
| Input contract absence | Grep check | `functional-requirements.md`, `business-rules.md` not present as inputs |
| Input contract presence | Grep check | Three AST JSONs present as mandatory inputs with path resolution |
| Pipeline shape | Grep absence | `estimate_effort`, `ac_scope_analysis`, `validate_scenarios` absent |
| Template section count | Count check | Template has exactly 5 numbered sections |
| Coverage Map | Structural check | §4 Test Coverage Map table with BR-NNN / DBR-NNN columns present |
| Orchestrator sync | Grep check | `external_mandatory` in orchestrator matches bridge-fastqa v4.0.0 outputs |
| IO map sync | Manual review | IO map bridge-fastqa entry matches new Input/Output Contract |
