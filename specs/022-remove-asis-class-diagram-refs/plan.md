# Implementation Plan: Remove AS-IS Class Diagram References

**Branch**: `022-remove-asis-class-diagram-refs` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

---

## Summary

The artifact `asis/diagrams/class-diagram.mmd` was removed from the AS-IS pipeline (generation instructions already removed from `solution-delphi.md`). This plan organizes the complete cleanup of 19 residual references across 16 files — docs, module config, report templates, and summary pipeline utilities — while preserving all references to `tobe/diagrams/class-diagram.mmd`.

---

## Technical Context

**Language/Version**: Python 3.10+, Markdown, YAML  
**Primary Dependencies**: None (file edits only)  
**Storage**: N/A  
**Testing**: `python -m py_compile`, grep-based absence checks  
**Target Platform**: Developer workstation  
**Project Type**: Cross-cutting cleanup / bugfix  
**Constraints**: Must not alter any `tobe/diagrams/class-diagram.mmd` reference  
**Scale/Scope**: 16 files, 19 edits, 1 function removal

---

## Constitution Check

| Article | Applicable? | Status |
|---|---|---|
| I — Configuration-Driven | No | ✅ N/A — no new hardcoded values |
| II — Agent Contract Standard | PATCH only | ✅ No frontmatter changes; reference removals do not trigger version bumps |
| III — Pipeline Execution Contract | No | ✅ N/A |
| IV — Module Registration | Yes | ✅ `module.yaml` removal is a de-registration (artifact entry), not a new agent |
| V — Language Convention | Yes | ✅ Agent `.md` body edits remain in pt-BR |
| VI — Test-First | Satisfied | ✅ BDD scenarios in spec §5 |
| VII — Security-First | No | ✅ N/A |

**Gate result: PROCEED** — No violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/022-remove-asis-class-diagram-refs/
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
docs/
├── agents-catalog.md                                    [A1]
├── asis-diagnostic-io-map.md                            [A2]
└── guia-execucao-fluxo-agentes.md                       [A3]

src/modules/ava-fabric-agents/
├── asis-diagnostic/
│   ├── module.yaml                                      [B1]
│   ├── shared/output-paths.md                           [B2]
│   └── templates/reports/asis-solution-report.md        [B3]
└── summary/
    ├── data/artifact-map.yaml                           [C1]
    ├── agents/summary-agent.md                          [C2]
    ├── workflows/generate-summary/steps/
    │   └── step-03-build-html.md                        [D1]
    └── utils/
        ├── build_summary_complete.py                    [E1]
        ├── build_summary_comprehensive.py               [E2]
        ├── remediate_summary.py                         [E3]
        ├── validate_summary.py                          [E4]
        ├── generate_drawio_from_mermaid.py              [E5]
        └── validate_drawio_integration.py               [E6]
```

---

## Execution Order

Changes are grouped by dependency risk. Apply groups in order; within a group, edits are independent.

### Tier 1 — Source of truth: Module config & shared definitions

| ID | File | Edit | Risk |
|---|---|---|---|
| B1 | `asis-diagnostic/module.yaml` | Remove `- diagrams/class-diagram.mmd` | Low |
| B2 | `asis-diagnostic/shared/output-paths.md` | Remove 2 table rows | Low |
| B3 | `asis-diagnostic/templates/reports/asis-solution-report.md` | Remove 1 table row | Low |

### Tier 2 — Documentation

| ID | File | Edit | Risk |
|---|---|---|---|
| A1 | `docs/agents-catalog.md` | Remove `class_diagram:` YAML line | Low |
| A2 | `docs/asis-diagnostic-io-map.md` | Remove list item | Low |
| A3 | `docs/guia-execucao-fluxo-agentes.md` | Remove AS-IS tree line only (keep TO-BE) | **Medium** |

### Tier 3 — Summary data & agent contracts

| ID | File | Edit | Risk |
|---|---|---|---|
| C1 | `summary/data/artifact-map.yaml` | Remove `class_diagram:` block (3 lines) | Low |
| C2 | `summary/agents/summary-agent.md` | Remove `class` from Keys AS-IS + remove `"class"` doc line | **Medium** |
| D1 | `summary/workflows/.../step-03-build-html.md` | Remove `{{CLASS_DIAGRAM}}` row | Low |

### Tier 4 — Python utilities (apply in sub-order)

| ID | File | Edit count | Risk |
|---|---|---|---|
| E4 | `validate_summary.py` | 1 | Low |
| E3 | `remediate_summary.py` | 2 | Low |
| E5 | `generate_drawio_from_mermaid.py` | 1 | Low |
| E6 | `validate_drawio_integration.py` | 1 | Low |
| E1 | `build_summary_complete.py` | 3 | Medium |
| E2 | `build_summary_comprehensive.py` | 6 + function removal | **High** |

### Tier 5 — Backup file (informational)

| ID | File | Edit | Risk |
|---|---|---|---|
| F1 | `build_summary_complete.py.backup` | Same as E1/Edit 1 | Low |

---

## Disambiguation Reference

| Signal | Decision |
|---|---|
| Path contains `asis/` | **REMOVE** |
| Path contains `tobe/` | **KEEP** |
| Variable `CLASS_DIAGRAM` (no prefix) | **REMOVE** |
| Variable `TOBE_CLASS_DIAGRAM` | **KEEP** |
| Dict key `"class"` in `D.staticDiagrams` | **REMOVE** |
| Dict key `"tobeClass"` | **KEEP** |
| `diag / "class-diagram.mmd"` where `diag = asis_dir / "diagrams"` | **REMOVE** |
| `tobe_diag / "class-diagram.mmd"` | **KEEP** |
| `{{CLASS_DIAGRAM}}` placeholder | **REMOVE** |
| `{{TOBE_CLASS_DIAGRAM}}` placeholder | **KEEP** |

---

## Post-Implementation Verification

See `quickstart.md` for the full validation script. Summary:

1. `grep -rn "asis/diagrams/class-diagram"` → 0 matches
2. `grep -rn '"CLASS_DIAGRAM"' src/` → 0 matches
3. `grep -rn "tobe/diagrams/class-diagram"` → ≥ 6 matches (unchanged)
4. `python -m py_compile` on all 6 `.py` files → exit 0
5. `yaml.safe_load` on both `.yaml` files → exit 0
6. `grep -n "_synthesize_class_diagram" build_summary_comprehensive.py` → 0 matches

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
