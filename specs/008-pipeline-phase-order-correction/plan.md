# Agent Implementation Plan: Pipeline Phase Order Correction

**Spec**: `specs/008-pipeline-phase-order-correction/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (4 orchestrator-tier agents + 36 leaf agents + 3 tool/build scripts duplicated across 2 files each + 1 HTML template + ~10 reference docs) |
| **Primary Requirement** | Correct the canonical pipeline phase order to F1 AS-IS → F2 TO-BE → F3 Prototype → F4 Stack → F5 QA → F6 DevOps → F7 Deliverables, promoting Prototype from a nested F2 sub-step to a real top-level phase |
| **Technical Approach** | Structural rewrite of `master-orchestrator.md` (new step + full renumbering) + removal of Prototype's old nested dispatch site + 37 mechanical single-line phase-tag fixes + reconciliation of every tool script, build script, and reference doc found via two grep passes (initial Explore-agent-guided pass + final exhaustive repo-wide pass) |
| **Implementation Status** | Complete. All changes verified structurally (exhaustive grep, zero contradicting patterns remain) and functionally (`py_compile` on all touched scripts + direct CLI phase-resolution test). |

## Constitution Check

- [x] **Article II** — no agent contract fields changed; only frontmatter versions bumped.
- [x] **Article X (SemVer)** — `master-orchestrator.md` and `orchestrator-tobe.md` bumped MINOR (new/removed orchestration step, no Output Contract field renames); `qa-orchestrator-agent.md` and `summary-agent.md` bumped PATCH-adjacent MINOR for the same reason; 36 leaf agents left at their existing version (single-line literal correction, no behavior change per Article X's own precedent from specs/006).
- [x] **Article I** — no technology versions hardcoded.
- [x] No `[NEEDS CLARIFICATION]` markers — the user's requested order was explicit and unambiguous; only the *mapping onto existing code* required investigation.

## Technical Context

Mixed Markdown (agent instructions + reference docs) and Python (2 observability
tools + 2 Summary-build scripts) plus one large HTML/JS template. No new
dependencies. No schema changes.

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
Re-ran the phase-order investigation from scratch via a dedicated Explore
agent (the prior attempt earlier in this session was abandoned before a
plan existed). Found 8 contradictory schemes, none matching the requested
order. Verified every claim with direct greps before planning (research.md
§1-4).

### Phase 1 — `master-orchestrator.md` Restructure ✅ CONCLUÍDO
Inserted new Step 3 (FASE 3 — Protótipo) dispatching `@ava-prototype`
directly; renumbered Stack (Step 4/F4), QA (Step 5/F5 — label only),
DevOps (Step 6/F6), Deliverables (Step 7/F7), Pipeline Completion Gate
(Step 8); updated every table, ASCII diagram, contract, timing template,
guardrail, and changelog entry referencing the old order. Version 1.2.0→1.3.0.

### Phase 2 — Remove Prototype's Old Nested Dispatch ✅ CONCLUÍDO
Deleted `orchestrator-tobe.md`'s "Fase 7.6 — Prototype TO-BE" step and all
its registry/timing-template rows; confirmed via grep that `ava-prototype`
is no longer dispatched from this file. Version 2.2.0→2.3.0.

### Phase 3 — Mechanical Leaf-Agent Fixes ✅ CONCLUÍDO
37 single-line `--phase` literal corrections across tech-stack (13, F3→F4),
devops-agents (13, F7→F6), deliverables (10, F6→F7), and prototype (1,
F2→F3) — done via targeted PowerShell regex replacement per module
directory, verified zero-leftover via grep immediately after.

### Phase 4 — QA Prose Self-Contradiction Fix ✅ CONCLUÍDO
Fixed 4 prose gate messages in `qa-orchestrator-agent.md` that said "F4 QA"
while its own tracking call already correctly said "F5" — a bugfix, not a
design change. Version 1.2.1→1.2.2.

### Phase 5 — Tooling & Build Scripts ✅ CONCLUÍDO
Updated `PHASE_ORDER`/`PHASE_NAMES`/`AGENT_CATALOG` in `pipeline_observer.py`;
`phase_order` in `agent_observability.py`; the duplicate `AGENT_CATALOG` in
`generate_observability_report.py` (found only in the Phase 7 exhaustive
sweep); `PHASE_SOURCES` and section comments in both
`build_summary_comprehensive.py` and `build_summary_complete.py` (two
independently-maintained Summary-build scripts, see research.md §6).

### Phase 6 — Summary HTML Template (CA03-critical) ✅ CONCLUÍDO
Fixed the `PHASES` JS array (the actual render-order data structure), both
PT/EN i18n dictionaries, the sidebar TOC (split the combined `f3f4` nav
group into independent `f3`/`f4` groups, swapped `f6`/`f7` content —
verified every `nav()` target resolves to an existing section id with zero
mismatches), `PHASE_FOLDER_MAP`, `renderDeliverableFallback`'s fallback
labels, and `FE_LABELS_MAP`.

### Phase 7 — Reference Docs + Final Exhaustive Sweep ✅ CONCLUÍDO
Fixed `docs/agents-catalog.md` (3 internally-contradicting sub-schemes),
`.github/copilot-instructions.md`, `docs/guia-execucao-fluxo-agentes.md`,
`docs/stack-split-impacto-po.md`, `.specify/memory/constitution.md`
(Article III + 2 tables + `allowed-tools` table + agent-count table),
`observability-self-report.md`. Then ran a final, broader exhaustive grep
(not scoped to the files the Explore agent had flagged) which caught 8 more
files: `docs/speckit-guia.md`, `docs/azure-devops-workitems-revisao-agentes.md`
(42 work items renumbered with zero gaps/duplicates after moving
Prototype's item earlier), `docs/inventory/generate-inventory.py`,
`docs/repo-structure.html`, plus 4 already covered in Phase 5/6.

### Phase 8 — Verification ✅ CONCLUÍDO
See quickstart.md. Structural (grep) + functional-in-isolation (`py_compile`
+ direct CLI phase-resolution smoke test across all 7 phases).

## Complexity Tracking

| Item | Status |
|---|---|
| Two parallel Summary-build scripts | Pre-existing duplication, not introduced by this PBI — both fixed identically; consolidation flagged as a separate follow-up (research.md §6) |
| Deep sidebar TOC restructure in `summary-template.html` | Higher-risk than a label-only fix (required splitting one nav group into two and swapping content-section IDs) — de-risked by cross-checking every `nav()` target against every actual section id before/after (zero mismatches both times) |
| 9th/10th/11th+ schemes found only in the final exhaustive sweep | Confirms the value of a broad final grep pass beyond what an Explore agent's semantic understanding surfaces — auxiliary generator scripts and historical docs encode the same labels independently and silently |
| Azure DevOps work-items doc renumbering | Moving Prototype's item earlier required renumbering all 42 items to avoid a duplicate/gap — done as a full-file rewrite, verified sequential 1-42 with no gaps |

## Test Strategy

| Test | Command | Result |
|---|---|---|
| No leftover old `--phase` tags | `grep -rl -- '--phase F3' tech-stack/agents/*.md` (and F7/devops, F6/deliverables, F2/prototype) | All empty |
| New tags present, correct count | `grep -c -- '--phase F4' tech-stack/*.md` etc. | 13+13+10+1 = 37 confirmed |
| QA prose fixed | `grep -c "F4 QA" qa-orchestrator-agent.md` | 0 |
| Tools compile | `python -m py_compile` on all 6 touched Python files | All OK |
| All 7 phases resolve | `pipeline_observer.py init` → `track --phase F1..F7` → `dashboard` | All succeed, correct names, correct sort order |
| Exhaustive repo sweep | broad regex grep for every old-order text pattern across `docs/`, `.github/`, `.specify/`, `src/` | Zero matches outside intentionally-preserved historical changelog entries |
| `nav()` targets match section ids | cross-check every `nav('s-f*-*'...)` call against every `id="s-f*-*"` in `summary-template.html` | Perfect 1:1 match, zero orphans |
