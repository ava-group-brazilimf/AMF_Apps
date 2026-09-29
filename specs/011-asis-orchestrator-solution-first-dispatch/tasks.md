# Agent Development Tasks: Solution Agent Must Dispatch First — Phase A Wave 1/Wave 2 Split + Hard-Stop Gate

**Plan**: `specs/011-asis-orchestrator-solution-first-dispatch/plan.md`
**Status**: Implementation complete; verification in progress.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm `orchestrator-asis.md` frontmatter version (`2.19.0`) matches the new
  `v2.19:` changelog line in its own `description` field.

## Category 2 — Implementation

- [x] **2.1** `## Agent Team Gerenciado` table: Execução column rewritten for all 8 Phase A
  agents (Wave 1 vs Wave 2 labeling); new `events-pubsub` row added (was missing) — DONE
- [x] **2.2** `## Execution DAG (Event-Driven)` ASCII diagram: redrawn with Wave 1 → Solution
  Agent Gate → Wave 2, plus the `⛔ HALT` branch — DONE
- [x] **2.3** `dispatch_schedule` YAML: `phase_a` split into `phase_a_wave1` (`mode: immediate`,
  solution + security) and `phase_a_wave2` (`mode: on_event`, `trigger: "solution✓"`) — DONE
- [x] **2.4** New `### Solution Agent Gate` section: `evaluate_solution_gate()` (6 cases:
  STUB / pending / retrying / retries-exhausted / artifacts-missing / open) +
  `halt_pipeline(reason)` (2 banner variants: STUB vs real failure) — DONE
- [x] **2.5** `on_retries_exhausted()`: new early-return exception for
  `agent_id == resolved_solution_agent`, calling `halt_pipeline("RETRIES_EXHAUSTED")`
  instead of the generic partial-dispatch/HG-threshold flow — DONE
- [x] **2.6** `## Streaming COLLECT Protocol`: new "Avaliar Solution Agent Gate" branch
  inserted before the pre-existing "Avaliar Phase A Gate" branch — DONE
- [x] **2.7** `## Guardrails`: retry-exhaustion bullet amended with the solution-agent
  exception; new bullet forbidding Wave 2 dispatch before the gate opens; Output Invariant
  bullet amended with the HALT exception — DONE
- [x] **2.8** Reasoning Approach Step 3.1 split into 3.1 (Wave 1 dispatch only) + 3.1b
  (Wave 2 dispatch, on gate open) — DONE
- [x] **2.9** `## Progress Tracker` `phase-a` row: description updated to name the
  Wave 1 → gate → Wave 2 sequence and the HALT outcome — DONE
- [x] **2.10** Frontmatter: `version` `2.18.1`→`2.19.0`, `date` updated, new `v2.19:`
  changelog line in `description` — DONE

## Category 3 — Schema Updates — SKIP

No new JSON artifact schema introduced; `dispatch_schedule`/Agent Completion Registry are
internal orchestrator constructs, not published schemas.

## Category 4 — Module Registration — SKIP

No new agent registered; `ava-asis-orchestrator` already existed in `module.yaml` — only
its `version` field bumped (Category 7).

## Category 5 — Quality Gate Checklists

- [x] **5.1** No orphaned "8 dispatches simultâneos" / "Phase A (immediate — 8" language
  remains in `orchestrator-asis.md`
- [x] **5.2** `solution✓` trigger appears in `dispatch_schedule.phase_a_wave2`, the Solution
  Agent Gate doc-comment, Step 3.1b, and the Streaming COLLECT Protocol branch
- [x] **5.3** `halt_pipeline` referenced consistently across its definition and all 3 call
  sites (`evaluate_solution_gate` doc, COLLECT branch, `on_retries_exhausted`)
- [x] **5.4** Fence balance (` ``` ` count even) preserved in `orchestrator-asis.md` after
  all edits
- [x] **5.5** `shared/retry-protocol.md`'s Wave 1/Wave 2 agent lists match
  `dispatch_schedule.phase_a_wave1.agents` / `phase_a_wave2` rule exactly
- [x] **5.6** `docs/agents-catalog.md` no longer contains "7 sub-agentes em paralelo"

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — happy path: Wave 1 dispatch → gate OPEN → Wave 2 dispatch — PASS (structural)
- [x] **6.2** CA02 — solution agent fails after 4 retries → `halt_pipeline("RETRIES_EXHAUSTED")`,
  Wave 2 never dispatched — PASS (structural)
- [x] **6.3** CA03 — STUB legacy technology → `halt_pipeline("STUB")` on first response, no
  retries attempted — PASS (structural)
- [x] **6.4** CA04 — security-orchestrator runs independently in Wave 1, unaffected by gate
  outcome — PASS (structural)

## Category 7 — Documentation

- [x] **7.1** `shared/retry-protocol.md` — rewritten to match the real Wave 1/Wave 2 agent
  composition and the new HALT-vs-HG distinction
- [x] **7.2** `docs/agents-catalog.md` — F1 section intro + Responsabilidades updated
- [x] **7.3** `module.yaml` (`asis-diagnostic`) — version `1.7.0`→`1.8.0`
- [x] **7.4** This spec-kit documentation (spec.md, plan.md, tasks.md) — DONE

## Completion Checklist

- [x] Solution agent (`solution-{legacy_technology}`) dispatches alone (with security) in
  Wave 1 — no longer races with the 6 agents that depend on its artifacts
- [x] Wave 2 (`test-qa`, `inventory`, `db-analyzer`, `events-pubsub`, `doc:FT`, `doc:VC`)
  only dispatches after the Solution Agent Gate confirms `status=completed AND
  artifacts_confirmed=true`
- [x] Solution agent failure (retries exhausted) or STUB status interrupts the entire
  pipeline with a clear, cause-specific alert — Wave 2/Phase B/C/D never dispatch
- [x] `security-orchestrator` confirmed unaffected — independent Wave 1 lifecycle
- [x] `shared/retry-protocol.md` and `orchestrator-asis.md`'s `dispatch_schedule` no longer
  contradict each other on Wave 1/Wave 2 composition
- [x] No leaf agent file (`solution-delphi.md`, `test-qa-asis.md`, etc.) modified — scope
  held strictly to the orchestrator and its 2 dependent docs, per the user's framing
  ("o agente asis-orchestrator", singular)
