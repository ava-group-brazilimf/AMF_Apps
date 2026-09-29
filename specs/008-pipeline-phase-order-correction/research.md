# Research Notes: Pipeline Phase Order Correction

## 1. This task was abandoned once before in this same session

An earlier attempt at this exact request was started, mid-investigation,
earlier in this session. The user moved on to a different, unrelated task
before a plan was finalized. Scope-clarification questions had been raised
but never answered. When the user re-raised the request, the investigation
was redone from scratch (not resumed from stale assumptions), since repo
state could have changed and the earlier partial findings were not yet
validated against a concrete target order.

## 2. First-pass investigation: 8 contradictory schemes found via a dedicated Explore agent

A thorough Explore-agent survey (not a quick grep) found phase-order/labeling
inconsistencies in:

1. `src/shared/tools/pipeline_observer.py` — `PHASE_ORDER = ["F1","F2","F3","F5","F7","F6","F8"]`, with `AGENT_CATALOG` never actually emitting an F4 or F8-tagged entry (self-contradicting its own `PHASE_NAMES`).
2. `src/shared/tools/agent_observability.py` — a separate, shorter `phase_order` list, missing F8 entirely.
3. `docs/agents-catalog.md` — 3 different sub-schemes disagreeing *within the same file* (its own index vs. its ASCII diagram vs. its body section headers vs. its own output-folder table).
4. `.github/copilot-instructions.md` — a 4th distinct scheme (uniquely putting QA at F4 and Prototype at F5), plus 2 more internally-disagreeing variants in the same file (master-orchestrator summary line vs. section headers vs. output-structure block).
5. `docs/guia-execucao-fluxo-agentes.md` — internally self-consistent (F1,F2,F3-Stack,F4-Prototype,F5-QA,F6-DevOps,F7-Deliverables,F8-Summary), but still disagreeing with every other file.
6. `master-orchestrator.md` — never used the label "F4" anywhere, and had **zero** invocations of `ava-prototype` (confirmed by grep — word count 0). Its only real per-phase steps were F1, F2, F3(Stack), F5(QA), F7(DevOps), F6(Deliverables).
7. The Summary module's `summary-template.html` `PHASES` JS array and `summary-agent.md`'s own outline — matched `docs/agents-catalog.md`'s body-header variant (F6=Deliverables, F7=DevOps), contradicting `copilot-instructions.md` and `guia-execucao-fluxo-agentes.md`.
8. QA orchestrator's own file (`qa-orchestrator-agent.md`) — internally self-contradicted: 4 prose gate messages said "F4 QA", one gate message and its own `--phase` tracking call said "F5" — the file disagreed with itself.
9. `.specify/memory/constitution.md` — described as the "canonical" governing source, yet its own Phase→Module Mapping table and Output Path Conventions table (a few lines apart) disagreed with each other on whether DevOps (F7) comes before or after Deliverables (F6).

**Critical finding**: none of these 8+ schemes matched what the user asked
for. Every one of them put Tech Stack at F3 (the user wants Prototype there)
and treated Prototype as either F4, F5, a sub-phase of F2 with no standalone
number, or omitted it from the sequence description entirely.

## 3. Direct-grep verification before committing to a plan

Rather than trust the Explore agent's prose summary alone, every claim was
re-verified with direct greps before finalizing the plan:

- `grep -rl -- '--phase F4' src/modules/ava-fabric-agents` → **zero results**,
  confirming no collision risk when Tech Stack moves to F4.
- All 10 QA leaf agent files (including the orchestrator) already used
  `--phase F5` in their actual tracking calls — only the orchestrator's
  *prose* (not its tracking call) said F4. This meant the QA fix was a
  4-line prose bugfix, not a design decision.
- All 13 tech-stack files used `--phase F3`; all 13 devops-agents files used
  `--phase F7`; all 10 deliverables files used `--phase F6`; the single
  prototype file used `--phase F2`. This gave an exact, verified blast-radius
  count (37 mechanical single-line fixes) before any edits began.
- `master-orchestrator.md` was re-read in full (not sampled) to confirm the
  zero-Prototype-invocation finding and to design the exact insertion point
  for the new Step 3.

## 4. Where Prototype actually lived before this PBI

`orchestrator-tobe.md` (the F2/TO-BE orchestrator) had its own internal
"Fase 0-8" sub-step numbering — a completely separate numbering system from
the top-level pipeline's F1-F7 phase codes, used only for TO-BE's own
internal sequencing (e.g., "Fase 7.5 — Design System", "Fase 7.8 — Test Plan
Consolidated"). Buried inside this internal sequence was "Fase 7.6 —
Prototype TO-BE", which dispatched `prototype-agent.md` directly. This was
the **only** dispatch site for Prototype in the entire repo. Its own
handoff protocol doc said the orchestrator "consumes this block... to
decide if it advances to Fase 8" — confirming Prototype was wired as an
internal gate within F2, never as a standalone pipeline phase.

This explains the user's specific requirement ("Prototype must run after F2,
remove it from other invocation points if present"): there was no duplicate
invocation to remove, but the single invocation needed to be **promoted**
out of F2's internals into a genuine top-level `master-orchestrator.md` step.

## 5. Second-pass exhaustive sweep found 8 more affected files

After completing the initial fix pass (guided by the Explore agent's
findings), a final verification grep swept the *entire* repo (not just the
files the Explore agent had flagged) for the specific old-order text
patterns (`F3 — Stack`, `F4 — Prototype`, `F6 — Deliverables`, `F7 —
DevOps`). This caught 8 additional files the first pass had missed:

- `docs/speckit-guia.md` — its own Phase→Module table, Article III summary, and `allowed-tools` table.
- `docs/azure-devops-workitems-revisao-agentes.md` — a historical Azure DevOps work-item generation checklist with **yet another (9th) distinct scheme**: F3=Stack, F4=QA, F5=Prototype, F6=DevOps, F7=Deliverables (the last two already matched the new canonical order by coincidence).
- `docs/inventory/generate-inventory.py` — an Excel-inventory-generating script with its own `ARTIFACT_MAP`-equivalent list and `phase_order` array.
- `docs/repo-structure.html` — a static folder-tree snapshot with per-folder phase annotations, using the same 9th scheme as the work-items doc.
- `src/shared/tools/generate_observability_report.py` — a near-exact **duplicate** of `pipeline_observer.py`'s `AGENT_CATALOG` (same bug, independently).
- `summary/utils/build_summary_complete.py` — a **second, independently-maintained** Summary-build script (see §6) with its own `ALL_AGENTS` list, `ARTIFACT_MAP`, and `PHASE_SOURCES` list — internally using yet another distinct scheme (F3=Stack, F4=QA, F5=Prototype) different even from its sibling script `build_summary_comprehensive.py`.
- `asis-diagnostic/agents/bridge-fastqa-asis.md` — one cross-reference comment mentioning "F6-Deliverables".
- `summary/workflows/generate-summary/steps/step-01-discover.md` — a workflow step's canonical-label table and count-summary block.

This second pass was necessary because the first (Explore-agent-guided) pass
covered the files a semantic understanding of "the pipeline" would surface,
but missed auxiliary/generator scripts and one-off historical docs that
happen to encode the same phase labels independently.

## 6. Two parallel Summary-build scripts — a pre-existing duplication, not introduced here

`build_summary_comprehensive.py` (invoked by `master-orchestrator.md`'s own
"Summary Generation — INVARIANTE ABSOLUTA" section) and
`build_summary_complete.py` (referenced by `summary-agent.md`,
`summary-validate-agent.md`, and `docs/summary-validator-guide.md` as the
script that wires in the HTML validator) are **two separate, independently-
maintained scripts** with their own `ARTIFACT_MAP`/`ALL_AGENTS`/
`PHASE_SOURCES` data structures — confirmed by reading both in full. This
duplication pre-dates this PBI and was not introduced by it; both scripts
were updated identically (same phase-order fix applied twice) so that
whichever one actually runs in a given environment produces correct labels.
Consolidating them into a single script is flagged as a natural follow-up,
out of scope here.

## 7. Verification approach

Since every touched file is either a prose agent-instruction `.md` file, a
static reference doc, or a script that requires a full project directory to
execute meaningfully, verification was necessarily two-tiered:

1. **Structural**: exhaustive `grep` sweeps (both broad, e.g. `F[1-8]`, and
   targeted, e.g. old-order-specific patterns) after every file edit and
   again as a final full-repo pass.
2. **Functional-in-isolation**: `python -m py_compile` on every touched
   Python file, plus a direct CLI smoke test of `pipeline_observer.py`
   (`init` → `track --phase F1` through `F7` → `dashboard`), confirming all
   7 phases resolve to the correct name with no `KeyError` and the
   phase-breakdown table sorts in the correct F1→F7 order.

No live `master-orchestrator.md` pipeline run was possible in this session
(it is a prose instruction file executed by an LLM, not a script) — this
limitation is stated honestly, consistent with every prior PBI in this
session (specs/002 through specs/007).
