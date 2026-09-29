# Agent Specification: Solution Agent Must Dispatch First — Phase A Wave 1/Wave 2 Split + Hard-Stop Gate

**Feature Branch**: `011-asis-orchestrator-solution-first-dispatch`
**Created**: 2026-07-08
**Status**: Implemented
**Change Type**: modify-existing (`orchestrator-asis.md` + `shared/retry-protocol.md` + `docs/agents-catalog.md`, MINOR — new orchestration step, no field renames; no new agents, no `module.yaml` agent registration change)
**Input**: "O agente esta pararelizando a chamada de outros agentes de forma incorreta [...] O agente solution-delphi {vb| e outros linguagens} DEVE OBRIGATORIAMENTE SER CHAMADO primariamente para gerar os artefatos necessarios por meio da leitura de codigo via AST e gerar outputs. Os demais agentes devem ser executados na sequencia onde a dependencia é agente de solução ja tenha sido executado. Caso o agente de solução não gere os artefatos obrigatorios para os demais agentes, a esteira deve ser interrompida alertando o usuario."

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-asis-orchestrator` | `agents/orchestrator-asis.md` | `2.18.1` → `2.19.0` (MINOR — new orchestration step/gate, no field renames) |

**Phase**: F1. **Module**: `asis-diagnostic`. Also touched: `shared/retry-protocol.md`
(reconciled to match the real dispatch order), `docs/agents-catalog.md` (removed a
now-false "7 sub-agentes em paralelo" claim). No leaf agent file (`solution-delphi.md`,
`test-qa-asis.md`, etc.) was modified — this PBI is scoped entirely to the orchestrator's
own dispatch logic, the mirror image of `specs/010`'s exclusion ("orchestrator itself is
out of scope").

## 2. Problem Statement

`orchestrator-asis.md`'s `dispatch_schedule.phase_a` (`mode: immediate`) dispatched **8
agents simultaneously** in Phase A — including `solution-{legacy_technology}` (the only
agent that reads source via AST and produces the structural artifacts
`architecture-blueprint.md`, `pattern-classifications.json`, `bounded-context-map.md`,
and 6 `.mmd` diagrams) alongside `test-qa`, `inventory`, `db-analyzer`, `events-pubsub`,
`doc:FT`, `doc:VC`, and (conditionally) `security-orchestrator` — all "reading source code
directly" in parallel.

This was already a documented, unresolved problem: `specs/010-asis-agents-ast-artifact-consumption`
wired 5 of these agents to *prefer* the solution agent's AST artifacts when present, but
explicitly flagged the underlying race condition as out of scope (§3.3): "Fixing the Phase
A race would require reordering `orchestrator-asis.md`'s own dispatch phases — explicitly
out of scope". Separately, `shared/retry-protocol.md` already called `solution-{tech}` the
"predecessor de documentation" and stated "Wave 1 antes de Wave 2" — but that ordering was
only enforced during **retry**, never on the initial dispatch, and its own agent lists
(`test-qa`, `security`, `inventory`, `db-analyzer` all lumped into "Wave 1") didn't match
reality (`events-pubsub`, `doc:FT`, `doc:VC` weren't mentioned at all).

Additionally, when the solution agent failed outright, the existing generic
`on_retries_exhausted()` policy ("mark FAILED, continue pipeline with partial data,
dispatch dependents with `partial_input: true`") let the pipeline continue producing a
Master Report built on 6 agents that silently degraded to raw Glob/Grep source reads —
with no alert distinguishing this from a normal partial failure.

## 3. Decision

### 3.1 Phase A split into Wave 1 / Wave 2 (terminology aligned to the pre-existing `shared/retry-protocol.md`)

- **Wave 1** (`dispatch_schedule.phase_a_wave1`, `mode: immediate`): `solution-{legacy_technology}`
  + `security-orchestrator` (if `security_enabled_asis: true`) — the only two agents with
  no dependency on the solution agent's artifacts (confirmed via `specs/010`'s own
  Exclusions: security has no AST-artifact overlap).
- **Solution Agent Gate** (new `evaluate_solution_gate()`, modeled on the existing
  `evaluate_phase_a_all()`): opens only when `solution-{legacy_technology}` reaches
  `status=completed AND artifacts_confirmed=true`.
- **Wave 2** (`dispatch_schedule.phase_a_wave2`, `mode: on_event`, `trigger: "solution✓"`):
  `test-qa`, `inventory`, `db-analyzer`, `events-pubsub`, `doc:FT`, `doc:VC` — dispatched
  only once the gate opens, reusing the exact `on_event` trigger pattern already used by
  `phase_b.rules` (e.g. `{ trigger: "FT✓", dispatch: doc:RT }`).

### 3.2 Hard-stop on solution-agent failure or STUB (new `halt_pipeline()`)

The Solution Agent Gate returns `HALT` — instead of the generic retry-exhaustion
continue-with-partial-data policy — when either:

- `solution-{legacy_technology}` exhausts its 4 standard retries without reaching
  `artifacts_confirmed=true` (`reason: RETRIES_EXHAUSTED`), or
- `solution-{legacy_technology}` is a STUB agent (`solution-cobol`, `solution-vbnet`,
  `solution-powerbuilder` — `implementation_status: STUB`, confirmed by the user to also
  halt, not just real failures) (`reason: STUB`).

On `HALT`: Wave 2, Phase B, Phase C, and Phase D are **never dispatched**; a dedicated
`⛔ PIPELINE INTERROMPIDO` banner is emitted (worded differently for each reason); the
pipeline ends in a `HALTED` state with a minimal Agent Completion Registry snapshot
instead of the full `⏱ Execução Concluída` timing block (same precedent already used by
the Step 0.2/Step 1 `PARAR` paths). This is implemented as an explicit exception inside
`on_retries_exhausted()` (early-return for `agent_id == resolved_solution_agent`, bypassing
the generic partial-dispatch/HG-threshold logic) and inside `verify_artifacts()`'s
pre-existing STUB branch, detected by `evaluate_solution_gate()`.

`security-orchestrator` (Wave 1) is explicitly unaffected — it runs its own independent
lifecycle and never waits for, or is blocked by, the Solution Agent Gate.

### 3.3 `shared/retry-protocol.md` reconciled

Its stale "Wave 1" list (`solution-{tech}, test-qa, security, inventory, db-analyzer`) and
undocumented `events-pubsub`/`doc:FT`/`doc:VC` gap are corrected to match the real Wave
1 (`solution-{tech}`, `security`) / Wave 2 (`test-qa`, `inventory`, `db-analyzer`,
`events-pubsub`, `doc:FT`, `doc:VC`) — the predecessor→successor ordering it already
prescribed for retries now also describes the initial dispatch honestly.

## 4. Functional Changes by Component

| Component | Change |
|---|---|
| `agents/orchestrator-asis.md` | `## Agent Team Gerenciado` table (Execução column, + new `events-pubsub` row); `## Execution DAG` ASCII diagram (Wave 1 → gate → Wave 2 + HALT branch); `dispatch_schedule` YAML split into `phase_a_wave1`/`phase_a_wave2`; new `### Solution Agent Gate` section (`evaluate_solution_gate()` + `halt_pipeline()`); `on_retries_exhausted()` early-return for the solution agent; `## Streaming COLLECT Protocol` new "Avaliar Solution Agent Gate" branch; `## Guardrails` (2 new bullets + 2 amended); Reasoning Approach Step 3.1 split into 3.1 (Wave 1) + 3.1b (Wave 2); `## Progress Tracker` `phase-a` row description; frontmatter version + description changelog line |
| `shared/retry-protocol.md` | Wave 1/Wave 2 agent lists corrected; solution-agent HALT exception documented instead of generic HG escalation |
| `docs/agents-catalog.md` | F1 section intro + Responsabilidades list — removed "dispara os 7 sub-agentes em paralelo", describes the Wave 1/gate/Wave 2 sequence |
| `module.yaml` (`asis-diagnostic`) | Version `1.7.0` → `1.8.0` (MINOR, no agent registration change) |

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Happy path: Wave 1 → gate OPEN → Wave 2 (CA01)

**Given** a Delphi project with a valid `repository_path`, **When** the pipeline reaches
Phase A, **Then** only `solution-delphi` (+ `security-orchestrator` if enabled) are
dispatched immediately; once `solution-delphi` reports `completed` and
`verify_artifacts()` confirms all 9 mandatory artifacts, `evaluate_solution_gate()`
returns `OPEN` and `test-qa`, `inventory`, `db-analyzer`, `events-pubsub`, `doc:FT`,
`doc:VC` are dispatched together, immediately — with the AST artifacts already on disk
before any of them start (per `specs/010`'s existence-check logic, now guaranteed to
find them, not racing).

### Scenario 2 — Solution agent fails after exhausting retries → HALT (CA02)

**Given** `solution-delphi` fails 4 times (retries exhausted, `artifacts_confirmed` never
`true`), **When** `on_retries_exhausted()` is invoked for it, **Then** it does **not**
follow the generic partial-dispatch/HG path — it calls `halt_pipeline("RETRIES_EXHAUSTED")`,
Wave 2 is never dispatched, and the pipeline ends with a `⛔ PIPELINE INTERROMPIDO` banner
naming the failed agent and the missing artifacts, instructing the user to fix the
problem and re-run the trigger.

### Scenario 3 — STUB legacy technology → HALT with a distinct message (CA03)

**Given** a project with `legacy_technology: "cobol"` (or `vbnet`/`powerbuilder`), **When**
`solution-cobol` (a permanent `implementation_status: STUB`) responds, **Then**
`evaluate_solution_gate()` returns `HALT` with `reason: "STUB"` on the **first** response
(no retries attempted, consistent with the pre-existing STUB carve-out in
`verify_artifacts()`), and `halt_pipeline("STUB")` emits a banner explaining the
technology isn't implemented yet, pointing to `stub-registry.yaml` — distinct wording
from the real-failure case.

### Scenario 4 — Security runs independently in Wave 1, unaffected by the gate (CA04)

**Given** `security_enabled_asis: true`, **When** `solution-delphi` is still running (or
even after it HALTs the pipeline), **Then** `security-orchestrator` was already dispatched
in Wave 1 alongside it and continues (or has already completed) its own 7-sub-agent
lifecycle entirely independently — its status is included in the HALT snapshot if the
gate fails, but its own success/failure never opens or blocks the Solution Agent Gate.

## 6. Quality Gate Requirements

- [x] Agent ID unchanged (`ava-asis-orchestrator`), frontmatter fields unchanged except version/date/description (Article II)
- [x] Version bump MINOR — new orchestration step, no existing field renamed or removed (Article X), consistent with `specs/008`'s precedent (`master-orchestrator` 1.2.0→1.3.0 for a comparable new-dispatch-step change)
- [x] BDD scenarios cover the happy path (CA01), real failure (CA02), STUB (CA03), and the security-independence edge case (CA04) (Article VI)
- [x] No technology versions hardcoded (Article I)
- [x] No `[NEEDS CLARIFICATION]` markers remain (STUB-halts / security-Wave-1 / standard-4-retries all confirmed with the user before implementation)

## 7. Dependencies

- `specs/010-asis-agents-ast-artifact-consumption` — conceptual prerequisite; its 5 wired
  agents' "check compressed/, fallback to Glob" logic is what makes Wave 2 dispatch safe
  and non-racy now that the artifacts are guaranteed present before they run.
- `evaluate_phase_a_all()`, `verify_artifacts()`, `on_retries_exhausted()` (all pre-existing
  in `orchestrator-asis.md`) — reused/extended, not replaced.

## 8. Exclusions

- The 6 leaf agent files wired by `specs/010` (`test-qa-asis.md`, `inventory-asis.md`,
  `db-analyzer.md`, `events-pubsub-asis.md`, `documentation-asis.md`, and `solution-delphi.md`
  itself) — **not modified**. Their existing "check artifact, fallback to Glob/Grep" logic
  from `specs/010` becomes effectively always-primary-source now that Wave 2 only runs
  after the gate opens; the fallback branch remains as harmless defense-in-depth (e.g. for
  `legacy_technology != delphi`, where no AST artifacts ever exist).
- `security-orchestrator` and its 7 sub-agents — unaffected; confirmed independent of the
  Solution Agent Gate (§3.2, Scenario 4).
- Non-Delphi solution agents' own internal logic (`solution-vb.md`'s static-analysis
  approach, the 3 STUB agents' fixed warning banner) — unchanged; only how the orchestrator
  reacts to their *outcome* changed.
- Phase B/C/D internal event rules (`on(FT✓)`, `on(VC✓)`, etc.) — unchanged; they now simply
  fire later in wall-clock time since their Wave 2 predecessors start later, but their
  trigger logic is untouched.

## 9. Assumptions

- The standard `retry_config.max_retries_per_agent: 4` is the correct threshold before
  halting on the solution agent too — confirmed with the user rather than assuming a
  stricter/looser threshold for this critical-path agent.
- STUB agents halting the pipeline (rather than warning-and-continuing, their behavior
  everywhere else in the file) is the desired behavior for `cobol`/`vbnet`/`powerbuilder`
  projects specifically for the *initial dispatch* gate — confirmed with the user; this is
  a deliberate scope-narrowing versus the pre-existing generic STUB carve-out in
  `verify_artifacts()`, which still applies as-is to any other future STUB agent outside
  this gate.
- `phase_a_active_agents` (referenced in the pre-existing "Avaliar Phase A Gate" COLLECT
  block) still implicitly means all active Phase A agents across both waves — this variable
  was already used without a separate explicit definition before this PBI and was not
  introduced or changed by it.

## Success Criteria

| Criterion | Measure |
|---|---|
| Solution agent dispatched alone (with security) in Wave 1 | `dispatch_schedule.phase_a_wave1.agents` lists only `solution-{legacy_technology}` + `security*` |
| Wave 2 gated behind the solution agent | `dispatch_schedule.phase_a_wave2` is `mode: on_event`, `trigger: "solution✓"` |
| Hard-stop on failure/STUB implemented | `on_retries_exhausted()` has an early-return calling `halt_pipeline()` for `agent_id == resolved_solution_agent`; `evaluate_solution_gate()` checks `implementation_status == "STUB"` before any other condition |
| No orphaned "8 dispatches simultâneos" language remains | `grep -c "8 dispatches"` / `"Phase A (immediate — 8"` in `orchestrator-asis.md` → 0 |
| `shared/retry-protocol.md` reconciled | Its Wave 1/Wave 2 lists match `dispatch_schedule.phase_a_wave1`/`phase_a_wave2` exactly |
| `docs/agents-catalog.md` updated | `grep -c "7 sub-agentes em paralelo"` → 0 |
