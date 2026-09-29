# Agent Development Tasks: Pipeline Phase Order Correction

**Plan**: `specs/008-pipeline-phase-order-correction/plan.md`
**Status**: Implementation and verification complete.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm all touched Python scripts compile
  ```bash
  python -m py_compile src/shared/tools/pipeline_observer.py src/shared/tools/agent_observability.py \
    src/shared/tools/generate_observability_report.py \
    src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py \
    src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py \
    docs/inventory/generate-inventory.py
  ```
  **Result**: OK.

## Category 2 — Implementation

- [x] **2.1** `master-orchestrator.md`: new Step 3 (FASE 3 — Protótipo), full renumbering of Stack/QA/DevOps/Deliverables/Completion Gate, all tables/diagrams/contracts/timing templates/changelog — DONE, version 1.3.0
- [x] **2.2** `orchestrator-tobe.md`: removed "Fase 7.6 — Prototype TO-BE" dispatch + registry rows — DONE, version 2.3.0
- [x] **2.3** `prototype-agent.md`: `--phase F2`→`F3`, Step self-declaration — DONE
- [x] **2.4** `qa-orchestrator-agent.md`: 4 prose "F4 QA"→"F5 QA" fixes — DONE, version 1.2.2
- [x] **2.5** 13 tech-stack leaf agents: `--phase F3`→`F4` — DONE
- [x] **2.6** 13 devops-agents leaf agents: `--phase F7`→`F6` — DONE
- [x] **2.7** 10 deliverables leaf agents: `--phase F6`→`F7` — DONE
- [x] **2.8** `pipeline_observer.py`: `PHASE_ORDER`, `PHASE_NAMES`, `AGENT_CATALOG` — DONE
- [x] **2.9** `agent_observability.py`: `phase_order` — DONE
- [x] **2.10** `generate_observability_report.py`: duplicate `AGENT_CATALOG` (found in exhaustive sweep) — DONE
- [x] **2.11** `build_summary_comprehensive.py` + `build_summary_complete.py`: `PHASE_SOURCES`/`ARTIFACT_MAP`/`ALL_AGENTS` comments and labels (two independent scripts, both fixed) — DONE
- [x] **2.12** `summary-template.html`: `PHASES` array, i18n dictionaries (PT+EN), sidebar nav (`f3f4` split, `f6`/`f7` swap), section IDs, `PHASE_FOLDER_MAP`, `renderDeliverableFallback`, `FE_LABELS_MAP` — DONE
- [x] **2.13** `summary-agent.md`: Output HTML Structure outline, `D.fileTree`/`FILE_TREE_JSON` notes — DONE, version 1.1.0

## Category 3 — Schema Updates — SKIP

No JSON schema changes; this PBI only corrects orchestration order and labels.

## Category 4 — Module Registration — SKIP

No `module.yaml` changes; all changes are `modify-existing` on already-registered agents.

## Category 5 — Quality Gate Checklists

- [x] **5.1** Reference docs reconciled: `docs/agents-catalog.md`, `.github/copilot-instructions.md`, `docs/guia-execucao-fluxo-agentes.md`, `docs/stack-split-impacto-po.md`, `docs/speckit-guia.md` — DONE
- [x] **5.2** `.specify/memory/constitution.md`: Article III, Phase→Module Mapping, Output Path Conventions, `allowed-tools`, agent-count tables — DONE, version 1.4.0
- [x] **5.3** `observability-self-report.md`: phase-lookup table — DONE, version 2.2.0
- [x] **5.4** Final exhaustive repo-wide sweep (beyond the Explore agent's initially-flagged files) — caught 8 additional files, all fixed: `docs/speckit-guia.md`, `docs/azure-devops-workitems-revisao-agentes.md`, `docs/inventory/generate-inventory.py`, `docs/repo-structure.html`, `generate_observability_report.py`, `build_summary_complete.py`, `bridge-fastqa-asis.md`, `step-01-discover.md`

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — no contradicting phase-order scheme remains anywhere in the repo — PASS
- [x] **6.2** CA02 — master-orchestrator dispatches Prototype directly exactly once; orchestrator-tobe.md no longer dispatches it — PASS
- [x] **6.3** CA03 — Summary "Phases & Agents" menu (`PHASES` array + i18n + sidebar nav) reflects the correct order — PASS
- [x] **6.4** All 7 phases resolve correctly via direct CLI test (`pipeline_observer.py`, no `KeyError`, correct sort order) — PASS
- [x] **6.5** Azure DevOps work-items doc renumbered 1-42 with no gaps/duplicates — PASS

## Category 7 — Documentation

- [x] **7.1** This spec-kit documentation (spec/plan/research/quickstart/tasks/checklist)

## Completion Checklist

- [x] `master-orchestrator.md` restructured and fully internally consistent
- [x] Prototype promoted from a nested F2 sub-step to a real, singular top-level F3 phase
- [x] 37 mechanical leaf-agent phase-tag fixes verified with zero leftovers
- [x] Both observability tools + both Summary-build scripts + the duplicate `generate_observability_report.py` catalog all updated
- [x] Summary HTML template's actual render-order data structure (not just labels) corrected, with zero orphaned nav links
- [x] Every reference doc found across two grep passes (Explore-agent-guided + final exhaustive) reconciled
- [x] All touched Python files compile; direct CLI smoke test confirms correct phase resolution end-to-end
