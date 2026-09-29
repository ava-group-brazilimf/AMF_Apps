# Agent Implementation Plan: Solution Agent Must Dispatch First — Phase A Wave 1/Wave 2 Split + Hard-Stop Gate

**Spec**: `specs/011-asis-orchestrator-solution-first-dispatch/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (`orchestrator-asis.md` + 2 dependent docs, no new agents) |
| **Primary Requirement** | The solution agent (`solution-{legacy_technology}`, the only AST-reading agent) must dispatch first and complete with its mandatory artifacts confirmed before the other 6 Phase A agents run; failure (retries exhausted) or STUB status must interrupt the whole pipeline with a clear alert, instead of silently continuing with degraded/partial analysis |
| **Technical Approach** | Split `dispatch_schedule.phase_a` into `phase_a_wave1` (immediate: solution + security) and `phase_a_wave2` (`on_event`, `trigger: "solution✓"`) — reusing the exact `on_event` pattern already used by `phase_b.rules`; new `evaluate_solution_gate()`/`halt_pipeline()` pair modeled on the pre-existing `evaluate_phase_a_all()`; hard-stop wired as an early-return exception inside the pre-existing `on_retries_exhausted()` |
| **Implementation Status** | Complete. Structural verification pending in `quickstart`-equivalent checks below. |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded.
- [x] **Article II** — frontmatter unchanged except `version`/`date`/`description` (changelog line appended, same pattern as the pre-existing `v2.1:` line).
- [x] **Article III** — this PBI corrects intra-phase (F1-internal) dispatch sequencing, not the cross-module F1→F7 order; no conflict with Article III's macro phase sequence.
- [x] **Article V** — pt-BR body content preserved throughout; new sections written in pt-BR matching the file's existing style.
- [x] **Article VI** — BDD scenarios cover happy path, real failure, STUB, and the security-independence edge case.
- [x] **Article X (SemVer)** — MINOR (`2.18.1`→`2.19.0`): new orchestration step/gate, no existing Input/Output Contract field renamed or removed.
- [x] No `[NEEDS CLARIFICATION]` markers — all 3 open design questions (STUB behavior, security's wave, retry count) resolved with the user via `AskUserQuestion` before implementation began.

## Technical Context

Pure Markdown/prose edits to `orchestrator-asis.md` (the orchestrator is itself an LLM
prompt spec, not executable code — "implementation" means rewriting its dispatch
contract, DAG diagram, and COLLECT-loop pseudocode so the *next* LLM-driven execution of
this agent follows the new sequencing). Two shared docs updated for consistency
(`shared/retry-protocol.md`, `docs/agents-catalog.md`). No leaf agent file touched — this
PBI is the direct, previously-flagged-as-out-of-scope follow-up to `specs/010` §3.3.

## Phase Placement

F1 (AS-IS Diagnostic), intra-phase only. Does not change F1's position relative to F2-F7
(Article III macro sequence untouched) — only reorders the sub-agents *within* F1's own
Phase A.

## Clean Architecture Alignment

N/A — `orchestrator-asis.md` is a prompt/instruction agent, not generated application
code; Article IX's Clean Architecture requirements apply to code these agents *produce*
(F2+ .NET output), not to the orchestrator's own dispatch logic.

## Agent File Structure

No new `## Input Contract` / `## Output Contract` sections needed — `orchestrator-asis.md`
already has a full `dispatch_schedule` YAML contract, `Agent Team Gerenciado` table, and
`Execution DAG` diagram; all three were edited in place rather than restructured. New
content follows the file's existing procedural-pseudocode style (`FUNCTION`/`PROCEDURE`
blocks with `IF`/`RETURN`), mirroring `evaluate_phase_a_all()` and
`dispatch_bridge_fastqa()` as the closest precedents for a new gate function.

## module.yaml Impact

`asis-diagnostic/module.yaml`: version `1.7.0` → `1.8.0` (MINOR). No `agents:` list change
— `ava-asis-orchestrator` was already registered; this PBI changes its behavior, not its
identity or file path.

## Observability & Trace Propagation

No change to `trace_id` propagation (unaffected by dispatch ordering). No observability
tool script (`pipeline_observer.py`, etc.) references Phase A's internal wave structure —
they track per-agent `--phase F1` calls, which are unchanged (same agents, same phase
label, just a different relative start time). Not touched.

## Schema Changes

None — no new JSON artifact schema introduced; `dispatch_schedule` and the Agent
Completion Registry are internal orchestrator YAML/pseudocode constructs, not published
schemas consumed by other tools.

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
3 parallel Explore agents confirmed: (1) `solution-delphi.md`'s real AST pipeline (Step 0,
`run_delphi_ast_analysis.py`) and its exact 9+ mandatory artifacts; (2) all 5 agents wired
by `specs/010` already treat the solution agent's artifacts as an optional primary source
with a safe Glob/Grep fallback — meaning gating Wave 2 behind the solution agent requires
zero changes to those 5 files, their fallback simply becomes unreachable dead code except
for non-Delphi projects; (3) this repo's Spec Kit conventions (`.specify/templates/overrides/`)
and the closest precedent, `specs/008-pipeline-phase-order-correction`, for a
dispatch-ordering-fix spec's structure.

### Phase 1 — Design Clarification ✅ CONCLUÍDO
3 `AskUserQuestion` rounds resolved: STUB agents also halt (not just real failures);
`security-orchestrator` stays in Wave 1, independent of the gate; standard 4-retry policy
applies to the solution agent before halting (no custom threshold).

### Phase 2 — Core Orchestrator Edit ✅ CONCLUÍDO
`orchestrator-asis.md`: Agent Team table + `events-pubsub` row added (was missing
entirely) + Execução column rewritten; ASCII DAG redrawn (Wave 1 → gate → Wave 2 + HALT
branch); `dispatch_schedule` split (`phase_a_wave1`/`phase_a_wave2`); new
`### Solution Agent Gate` section (`evaluate_solution_gate()` + `halt_pipeline()`);
`on_retries_exhausted()` given a solution-agent early-return exception; Streaming COLLECT
Protocol given a new "Avaliar Solution Agent Gate" branch (evaluated before the pre-existing
"Avaliar Phase A Gate" branch, since it gates whether Wave 2 agents even exist to be
evaluated by that later block); `## Guardrails` amended (2 new/extended bullets);
Reasoning Approach Step 3.1 split into 3.1 (Wave 1 dispatch) + 3.1b (Wave 2 dispatch,
cross-referencing the COLLECT protocol rather than duplicating it); Progress Tracker
`phase-a` row description updated; frontmatter version + changelog description line.

### Phase 3 — Dependent Docs Reconciliation ✅ CONCLUÍDO
`shared/retry-protocol.md` rewritten: Wave 1 (`solution-{tech}`, `security`) / Wave 2
(`test-qa`, `inventory`, `db-analyzer`, `events-pubsub`, `doc:FT`, `doc:VC`) now match the
orchestrator's real `dispatch_schedule` exactly (previously listed `test-qa`/`inventory`/
`db-analyzer` in "Wave 1" and never mentioned `events-pubsub`/`doc:FT`/`doc:VC` at all);
solution-agent HALT exception documented explicitly instead of the generic HG-escalation
path. `docs/agents-catalog.md`: F1 section intro + Responsabilidades list — removed the
now-false "dispara os 7 sub-agentes em paralelo" claim.

### Phase 4 — Version Sync ✅ CONCLUÍDO
`orchestrator-asis.md` frontmatter `2.18.1`→`2.19.0` + `date` + new `v2.19:` description
line (same pattern as the pre-existing `v2.1:` line). `module.yaml` `1.7.0`→`1.8.0`.

### Phase 5 — Verification (this session)
Structural greps (no orphaned "8 dispatches" language, `solution✓` trigger present exactly
where expected, `shared/retry-protocol.md` matches the new dispatch lists) — see
`## Test Strategy` below. No live pipeline run possible in this session (prose instruction
file, not executable code) — verification is structural/textual, consistent with
`specs/008`/`specs/010`'s own precedent for this repo's agent-spec PBIs.

## Complexity Tracking

| Item | Status |
|---|---|
| STUB agents now halt the pipeline (a behavior change vs. `verify_artifacts()`'s generic "WARN, continue" STUB carve-out) | Deliberately scoped to *only* the Solution Agent Gate's own check (`evaluate_solution_gate()`'s Caso 1, checked before status/artifacts_confirmed) — the generic `verify_artifacts()` STUB branch itself is untouched and still governs any other agent that might report STUB in the future |
| Two "Wave 1/Wave 2" vocabularies coexisting (`shared/retry-protocol.md`'s pre-existing retry-time terminology vs. the new dispatch-time `phase_a_wave1`/`phase_a_wave2` YAML keys) | Reconciled deliberately rather than inventing new terminology (`Phase A0`/`Phase A1` was considered and rejected) — same "Wave 1"/"Wave 2" words now correctly describe both retry order and initial dispatch order |
| `on_retries_exhausted()`'s solution-agent early-return bypasses its own §5 "critical failure threshold" (>50% Phase A agents failed → HG) logic entirely | Intentional — for the solution agent, HALT always takes precedence over HG (per user confirmation); the >50% threshold logic still applies unchanged to all other Phase A agents |
| `events-pubsub` row was missing from `## Agent Team Gerenciado` before this PBI (pre-existing gap, unrelated to Phase A ordering) | Added while touching the table anyway, since it's now explicitly one of the 6 Wave 2 agents and its absence would make the corrected table incomplete |

## Test Strategy

| Test | Command | Expected |
|---|---|---|
| No orphaned "8 dispatches simultâneos" language | `grep -c "8 dispatches"` in `orchestrator-asis.md` | 0 |
| `solution✓` trigger present exactly where expected | `grep -n "solution✓"` in `orchestrator-asis.md` | Appears in `dispatch_schedule.phase_a_wave2`, `evaluate_solution_gate()`'s doc-comment, Step 3.1b, and the Streaming COLLECT Protocol branch |
| `phase_a_wave1`/`phase_a_wave2` both defined | `grep -c "phase_a_wave1:"` / `"phase_a_wave2:"` | 1 / 1 |
| `halt_pipeline` referenced consistently | `grep -c "halt_pipeline"` | ≥ 4 (definition + 3 call sites: `evaluate_solution_gate` doc, COLLECT branch, `on_retries_exhausted`) |
| `shared/retry-protocol.md` matches new Wave lists | Manual diff of Wave 1/Wave 2 agent lists against `dispatch_schedule.phase_a_wave1.agents`/`phase_a_wave2` rule | Identical agent sets |
| `docs/agents-catalog.md` no longer claims parallel-7 | `grep -c "7 sub-agentes em paralelo"` | 0 |
| Fence balance in `orchestrator-asis.md` | Count of ` ``` ` occurrences is even | Even |
