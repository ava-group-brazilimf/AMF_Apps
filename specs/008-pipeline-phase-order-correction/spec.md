# Agent Specification: Pipeline Phase Order Correction

**Feature Branch**: `008-pipeline-phase-order-correction`
**Created**: 2026-07-07
**Status**: Implemented
**Change Type**: modify-existing (`ava-master-orchestrator`, `ava-tobe-orchestrator`, `ava-prototype`, `ava-qa-orchestrator` + 36 leaf agents + 2 observability tools + 1 build script + reference docs — no new agents, no `module.yaml` changes)
**Input**: "Feature: Ordem de execução da Esteira... A esteira é executada em sub-fases, sendo que as fases MUST obedecer a seguinte ordem: F1-AS-IS, F2-TO-BE, F3-Prototype, F4-Tech Stack, F5-QA, F6-DevOps, F7-Deliverables... O Agente de prototype no master orchestrator ser invocado após a fase F2-TO-BE, caso esse agente esteja sendo invocado em outras fase, faça a remoção dessa chamada."

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Primary Agent** | `ava-master-orchestrator` — `1.2.0` → `1.3.0` (MINOR — new orchestration step, no field renames) |
| **Also modified** | `ava-tobe-orchestrator` (`2.2.0`→`2.3.0`), `ava-qa-orchestrator` (`1.2.1`→`1.2.2`), 36 leaf agents (mechanical `--phase` literal fix only, no version bump) |
| **Phase** | Cross-cutting — this PBI corrects the phase-order contract itself |
| **Files** | See § Functional Changes below |

## 2. Problem Statement

The pipeline's phase order was internally inconsistent across the repository.
A full re-survey (research.md) found **at least 8 mutually-contradictory
numbering schemes** for the same 7 phases, live simultaneously across
`master-orchestrator.md`, `pipeline_observer.py`, `docs/agents-catalog.md`,
`.github/copilot-instructions.md`, `docs/guia-execucao-fluxo-agentes.md`,
`.specify/memory/constitution.md`, and the Summary HTML template — plus 8
more files discovered only after a second, exhaustive repo-wide grep pass
(`docs/speckit-guia.md`, `docs/azure-devops-workitems-revisao-agentes.md`,
`docs/inventory/generate-inventory.py`, `docs/repo-structure.html`,
`generate_observability_report.py`, `build_summary_complete.py`,
`bridge-fastqa-asis.md`, `step-01-discover.md`).

Critically, **none of the pre-existing schemes matched the user's requested
order.** Every scheme put Tech Stack at F3 and either omitted Prototype
entirely, nested it inside F2/TO-BE as a non-standalone sub-step, or placed
it at F4 or F5 depending on the file. `master-orchestrator.md` itself never
invoked `ava-prototype` at all — the only real dispatch site in the whole
repo was a single nested step ("Fase 7.6") deep inside
`ava-tobe-orchestrator`'s own internal sequence, meaning Prototype ran (if
at all) as a side effect of F2, never as its own top-level pipeline phase.

## 3. Decision

1. **New canonical order**: F1 AS-IS → F2 TO-BE → **F3 Prototype** → F4 Stack
   → F5 QA → F6 DevOps → F7 Deliverables. Summary remains cross-cutting
   (informally "F8" where a label is already used, not a hard sequence slot).
2. **Prototype promoted to a real top-level phase.** A new
   `### Step 3 — FASE 3: Protótipo` was added to `master-orchestrator.md`,
   dispatching `@ava-prototype` directly (non-blocking — WARN on failure,
   consistent with QA's non-blocking precedent), right after F2 completes.
3. **Its old nested invocation site removed.** `orchestrator-tobe.md`'s
   internal "Fase 7.6 — Prototype TO-BE" step (the only other place
   `ava-prototype` was ever dispatched from) was deleted; the artifacts it
   depends on (`design-system.md`, `user-journeys.md`) are still produced by
   F2's own internal sequence, just no longer trigger Prototype's dispatch.
4. **Stack renumbered F3→F4, DevOps renumbered F7→F6, Deliverables renumbered
   F6→F7.** QA stays F5 (it was already consistently F5 in its own
   `--phase` tracking calls across all 10 files — only 4 *prose* gate
   messages inside `qa-orchestrator-agent.md` still said "F4", contradicting
   its own tracking call; fixed as a bug, not a design change).
5. **37 mechanical `--phase` literal fixes** across leaf agent files: 13
   tech-stack files (F3→F4), 13 devops-agents files (F7→F6), 10 deliverables
   files (F6→F7), 1 prototype file (F2→F3) — content otherwise untouched.
6. **Both observability tool scripts and both Summary build scripts**
   updated: `PHASE_ORDER`/`PHASE_NAMES`/`AGENT_CATALOG` in
   `pipeline_observer.py`, `phase_order` in `agent_observability.py`, a
   duplicate `AGENT_CATALOG` in `generate_observability_report.py`, and the
   `PHASE_SOURCES`/section-comment labels in both `build_summary_comprehensive.py`
   and `build_summary_complete.py`.
7. **The Summary "Phases & Agents" menu (CA03)** — the actual `PHASES`
   JavaScript array and both PT/EN i18n dictionaries in
   `summary-template.html`, plus the deeper sidebar TOC (`data-phase-id`
   groups, per-artifact `s-f*`/`nd-f*` section IDs, `PHASE_FOLDER_MAP`,
   `renderDeliverableFallback`'s fallback labels, and `FE_LABELS_MAP`) — all
   reconciled to the new order. The `F3/F4` combined nav group (previously
   "Stack & Protótipo") was split into two independent groups.
8. **Reference docs reconciled**: `docs/agents-catalog.md` (3 internally
   contradicting sub-schemes fixed to 1), `.github/copilot-instructions.md`,
   `docs/guia-execucao-fluxo-agentes.md`, `docs/stack-split-impacto-po.md`,
   `docs/speckit-guia.md`, `.specify/memory/constitution.md` (Article III +
   Phase→Module Mapping + Output Path Conventions — previously 2 internally
   disagreeing tables), `observability-self-report.md`'s phase-lookup table,
   `docs/azure-devops-workitems-revisao-agentes.md` (42 work items
   renumbered 1-42 with no gaps/duplicates after moving Prototype earlier),
   `docs/inventory/generate-inventory.py`, `docs/repo-structure.html`.

## 4. Functional Changes by Component

| Component | Change |
|---|---|
| `master-orchestrator/agents/master-orchestrator.md` | New Step 3 (Prototype dispatch); Stack/QA/DevOps/Deliverables steps renumbered 4-7; Pipeline Completion Gate renumbered Step 8; all tables, ASCII diagrams, Input/Output Contracts, Progress Tracker, Timing templates, Guardrails, Changelog updated; version 1.2.0→1.3.0 |
| `tobe-architecture/agents/orchestrator-tobe.md` | Removed "Fase 7.6 — Prototype TO-BE" dispatch step and all its registry/timing-template rows; added note that Prototype is now dispatched by master-orchestrator as FASE 3; version 2.2.0→2.3.0 |
| `prototype/agents/prototype-agent.md` | Self-report `--phase F2`→`F3`; "Step" self-declaration updated |
| `qa-agents/agents/qa-orchestrator-agent.md` | 4 prose gate messages "F4 QA"→"F5 QA"; version 1.2.1→1.2.2 |
| 13 `tech-stack/agents/*.md` | `--phase F3`→`F4` (mechanical, single line each) |
| 13 `devops-agents/agents/*.md` | `--phase F7`→`F6` (mechanical, single line each) |
| 10 `deliverables/agents/*.md` | `--phase F6`→`F7` (mechanical, single line each) |
| `src/shared/tools/pipeline_observer.py` | `PHASE_ORDER`, `PHASE_NAMES`, `AGENT_CATALOG` (added Prototype F3 entry, retagged Stack/DevOps/Deliverables) |
| `src/shared/tools/agent_observability.py` | `phase_order` list |
| `src/shared/tools/generate_observability_report.py` | Duplicate `AGENT_CATALOG` (same fix as pipeline_observer.py) |
| `summary/utils/build_summary_comprehensive.py` | `ARTIFACT_MAP` phase-section comments reordered/relabeled |
| `summary/utils/build_summary_complete.py` | `ALL_AGENTS` comments, `ARTIFACT_MAP` blocks (reordered), `PHASE_SOURCES` list (labels + F6/F7 swap) |
| `summary/templates/html/summary-template.html` | `PHASES` array (num:3↔4, num:6↔7 swap), both i18n dictionaries (`ph3`-`ph7`, `grp-f3`-`grp-f7`), sidebar nav (`f3f4` split into `f3`+`f4`, `f6`↔`f7` content swap), all `s-f*`/`nd-f*` section IDs renamed to match, `PHASE_FOLDER_MAP`, `renderDeliverableFallback` labels, `FE_LABELS_MAP` |
| `summary/agents/summary-agent.md` | "Output HTML Structure" outline reordered; `D.fileTree` and `FILE_TREE_JSON` doc notes updated; version 1.0.0→1.1.0 |
| `docs/agents-catalog.md`, `.github/copilot-instructions.md`, `docs/guia-execucao-fluxo-agentes.md`, `docs/stack-split-impacto-po.md`, `docs/speckit-guia.md` | All F3/F4/F6/F7 sub-schemes reconciled to canonical order |
| `.specify/memory/constitution.md` | Article III sequence diagram, Phase→Module Mapping table, Output Path Conventions table, `allowed-tools` table, agent-count table; version 1.3.0→1.4.0 with amendment rationale |
| `shared/observability-self-report.md` | Phase-lookup-by-prefix table; version 2.1.0→2.2.0 |
| `docs/azure-devops-workitems-revisao-agentes.md` | 42 work items renumbered 1-42 (no gaps/duplicates) after moving Prototype's item earlier |
| `docs/inventory/generate-inventory.py`, `docs/repo-structure.html` | Phase labels/`phase_order` list corrected |

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Phases appear in correct order everywhere (CA01)

**Given** any reference artifact in the repo (agent files, tool scripts,
docs, the constitution, the Summary HTML template), **When** it lists or
labels the 7 pipeline phases, **Then** it shows F1 AS-IS, F2 TO-BE, F3
Prototype, F4 Stack, F5 QA, F6 DevOps, F7 Deliverables — with no
contradicting scheme anywhere in the repo (verified via exhaustive grep).

### Scenario 2 — Master-orchestrator dispatches Prototype directly, once (CA02)

**Given** a full pipeline run reaches the end of F2/TO-BE, **When** the
master-orchestrator continues, **Then** it dispatches `@ava-prototype`
directly as its own Step 3/FASE 3 — not as a side effect of F2 — and no
other file in the repo still dispatches `ava-prototype` (confirmed:
`orchestrator-tobe.md`'s old nested dispatch was removed).

### Scenario 3 — Summary "Phases & Agents" menu reflects the correct order (CA03)

**Given** a generated Summary HTML report, **When** the user opens the
"Phases & Agents" menu, **Then** it lists phases in the order F1→F7 with
Prototype at position 3 and Stack at position 4, DevOps at 6 and
Deliverables at 7 — driven by the corrected `PHASES` JavaScript array (not
just a label change; the actual render-order data structure).

### Scenario 4 — Observability tools resolve all 7 phases with no error (verification-only, not a numbered CA)

**Given** `pipeline_observer.py` tracking an agent in any of F1-F7, **When**
`track` is called, **Then** `PHASE_NAMES.get(phase)` resolves to the correct
name with no `KeyError`, and the phase-breakdown dashboard sorts phases in
the correct F1→F7 order.

## 6. Quality Gate Requirements

- [x] Agent IDs unchanged; only version numbers and content changed (Article II)
- [x] Version bumps are MINOR/PATCH matching the nature of each change (Article X) — no agent's Output Contract fields were renamed, only orchestration order and instrumentation
- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Scenarios cover order correctness (CA01), Prototype's promotion + de-duplication (CA02), and the Summary menu (CA03)

## 7. Dependencies

- `src/shared/tools/pipeline_observer.py` / `agent_observability.py` (both updated in this PBI)
- `summary/utils/build_summary_comprehensive.py` / `build_summary_complete.py` (both updated — two parallel Summary-build scripts coexist in this repo; see research.md §6)
- `summary/templates/html/summary-template.html` (CA03-critical)

## 8. Exclusions

- No agent's actual business logic (what each agent produces) was changed — only orchestration order, phase labels, and instrumentation.
- Deep internal sub-step numbering inside `orchestrator-tobe.md` (its own "Fase 0-8" scheme for internal TO-BE steps like "Fase 7.5 — Design System") is a *different, unrelated* numbering system and was **not** touched, except for removing the one step (7.6) that dispatched Prototype.
- The one genuinely distinct "F3 Build Cycle" trigger label inside `constitution.md`/`orchestrator-tobe.md` (an internal TO-BE build-cycle trigger name, unrelated to the top-level pipeline phase F3) was left untouched — renaming it would have conflated two unrelated concepts that happen to share the string "F3".
- No live pipeline execution was possible in this session (these are prose instruction files plus supporting scripts) — verification is structural (grep sweeps) and functional-in-isolation (direct CLI invocation of the observability tools with all 7 phase codes).

## 9. Assumptions

- Summary (`ava-summary`) remains cross-cutting/non-sequential — kept as an informal "F8" label only where a label was already in use (e.g., `PHASE_NAMES`, the constitution's mapping table), not forced into every file that didn't already have one.
- The two parallel Summary-build scripts (`build_summary_comprehensive.py`, invoked by `master-orchestrator.md`, and `build_summary_complete.py`, referenced by `summary-agent.md`/`summary-validate-agent.md`/`docs/summary-validator-guide.md`) are a pre-existing duplication in this repo, not introduced by this PBI — both were updated identically for consistency, but consolidating them into one script is out of scope.

## Success Criteria

| Criterion | Measure |
|---|---|
| No contradicting phase-order scheme remains | Exhaustive repo-wide grep for old F3=Stack/F4=Prototype/F6=Deliverables/F7=DevOps patterns returns zero matches (outside historical changelog entries, intentionally preserved) |
| Prototype is a real, singular top-level phase | `master-orchestrator.md` has exactly one `ava-prototype` dispatch (its own Step 3); `orchestrator-tobe.md` has zero |
| Mechanical fixes complete | 13+13+10+1 = 37 leaf-agent `--phase` literals corrected, verified via grep count |
| Tools resolve all 7 phases | Direct CLI test: `track` with `--phase F1` through `F7` all succeed with correct `PHASE_NAMES` resolution and correctly-ordered dashboard output |
| Summary menu order correct | `PHASES` array in `summary-template.html` has `num:3`=Prototype, `num:4`=Stack, `num:6`=DevOps, `num:7`=Deliverables |
