# Agent Specification: Mandatory Spec Read Before Every Cross-Agent Dispatch

**Feature Branch**: `013-master-orchestrator-mandatory-spec-read`
**Created**: 2026-07-08
**Status**: Implemented
**Change Type**: modify-existing (`master-orchestrator.md` + `orchestrator-asis.md` + `devops-agents/module.yaml`, MINOR/PATCH — new protocol section + reliability hardening, no field removed)
**Input**: "Vamos analisar o agente master-orchestrator [...] Quando executo o master-orchestrator ao invocar o ava-asis-orchestrator SA | FULL o comportamento é outro e não executa os steps projetados no orquestrator asis para gerar os artefatos via AST e vai direto lendo source code full [...] O comportamento do master orchestrator deve fazer a execução do orquestrador AS-IS de modo igual [...] quando o /ava-asis-orchestrator for invocado, os logs de execução devem ser exibidos com clareza para usuario [...] Investigue o gap de execução e crie um plano [...]"

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-master-orchestrator` | `master-orchestrator/agents/master-orchestrator.md` | `1.3.0` → `1.4.0` (MINOR — new `## Dispatch Protocol` section, 24 dispatch points hardened, no field removed) |
| `ava-asis-orchestrator` | `asis-diagnostic/agents/orchestrator-asis.md` | `2.19.0` → `2.19.1` (PATCH — same hardening applied to Step 3.1's own sub-dispatch of the solution agent) |

**Phase**: cross-cutting (master-orchestrator dispatches F1-F7; the Step 3.1 fix is internal to F1).
**Module**: `master-orchestrator` (primary), `asis-diagnostic` (Step 3.1 fix), `devops-agents`
(collateral `module.yaml` registration fix — see §3.4).

## 2. Problem Statement

Standalone invocation (`/ava-asis-orchestrator | FP | {project}`) correctly runs Step 0 of
`solution-delphi.md` — a real AST extraction (`run_delphi_ast_analysis.py`) producing 9
deterministic JSON artifacts consumed by the rest of the AS-IS analysis (per `specs/007`,
`specs/010`, `specs/012`). But `master-orchestrator.md` dispatching the identical phase via
`@ava-asis-orchestrator | SA | FULL` produced different behavior: the AST extraction was skipped
entirely, falling back to manual per-file `Get-Content` reads — even with `ava_ast_analyzer_path`
correctly configured in the target project's `project-config.yaml` (verified — not a config
problem).

Root cause, confirmed via 2 parallel investigations (direct file reads, not inference):

1. `master-orchestrator.md`'s Step 1.1 (F1 dispatch) is a purely declarative
   `DISPATCH @ava-asis-orchestrator` + parameter list + `AWAIT` — **no instruction anywhere to
   `Read` the target's `.md` spec** before continuing. This is not an F1-specific gap: the
   identical shallow pattern is used at all 24 dispatch points across F1-F7. The only place in the
   entire repository that already does this correctly is `dispatch_bridge_fastqa()` (inside
   `orchestrator-asis.md` itself), whose Step A is `Read(bridge-fastqa-asis.md)` as a hard,
   OBRIGATÓRIO gate before execution.
2. The identical gap exists one level down: `orchestrator-asis.md`'s own Step 3.1 (Wave 1)
   dispatches `@{resolved_solution_agent}` without an explicit `Read` of `solution-{tech}.md`
   first. Standalone invocation happens to work today — plausibly because a small, freshly-loaded,
   single-purpose context favors the LLM's implicit judgment to read the target before "becoming"
   it — but it is the same class of fragility, just not (yet) observed to fail.
3. Ruled out: `orchestrator-asis.md`'s own trigger-handling (`SA`, `SA | FULL`, `FP`) all flow
   through the identical Step 3 DAG (confirmed by direct read of `## Reasoning Approach` and the
   `FP` workflow, which only adds validation steps *after* the DAG, never bypasses Step 0). The
   Pre-Execution Workspace Reset (`FULL` flag) only wipes `outputs/` and resets
   `shared-context.md` — nothing AST-related, and it runs *before* the solution agent is ever
   dispatched. The bug does not live in `orchestrator-asis.md`'s trigger logic.
4. Collateral finding: `ava-devops-cost-estimate` (dispatched at F6 Step 6.6) and 3 cloud-specific
   IaC stub agents (`ava-devops-iac-aws/gcp/k8s-native`, dispatched conditionally at Step 6.5) all
   have real files on disk (`devops-agents/agents/*.md`) but were **never registered** in
   `devops-agents/module.yaml`'s `agents:` list (Article IV violation) — discovered while building
   the agent→spec-file lookup table this PBI required anyway.

## 3. Decision

### 3.1 New `## Dispatch Protocol` section in `master-orchestrator.md`

A single global guardrail (avoids repeating the explanation 24 times): before ANY
`DISPATCH @agent-id`, the LLM MUST `Read` the target agent's full `.md` spec (path resolved via
the `## Agent Team` table's new `Spec File` column) and follow its Steps literally — never
improvise from generic domain knowledge of what that agent "should" do. Explicitly states this
propagates through nested dispatches (`ava-asis-orchestrator` reading its own spec, which then
reads `solution-{tech}.md` before its own Wave 1 dispatch).

### 3.2 `## Agent Team` table gains a `Spec File` column

Resolved via each module's `module.yaml` (all 24 paths confirmed via direct grep, not assumed).
Single source of truth — avoids duplicating/drifting 24 hardcoded paths across the dispatch sites
themselves.

### 3.3 All 24 `DISPATCH @agent-id` points get an inline `⛔ Read(...)` prefix

No sub-step renumbering (low risk, no churn) — the `Read` instruction becomes part of the same
numbered line, e.g. `1.1 ⛔ Read(.../orchestrator-asis.md) OBRIGATÓRIO (ver § Dispatch Protocol) →
DISPATCH @ava-asis-orchestrator`. Applied to: F1 (1), F2 (1), F3 (1), F4 (1), F5 (1), F6 (9,
including all 4 conditional cloud-provider branches in Step 6.5), F7 (7). `ava-summary` dispatches
(via `Bash: python build_summary_comprehensive.py`) are explicitly excluded — deterministic script
execution has no "improvisation" risk.

### 3.4 Same pattern applied to `orchestrator-asis.md` Step 3.1

The Wave 1 dispatch of `@{resolved_solution_agent}` now requires `Read` of the resolved path
(via the `SOLUTION_AGENTS` routing table already defined in Step 2) before invoking — closing the
one-level-down instance of the same gap, per user's explicit choice to fix both points.

### 3.5 Log visibility (user's second request)

Explicit reinforcement in `## Dispatch Protocol`: output/checklists/progress emitted by a
dispatched agent — including its own internal sub-dispatches, such as the real-time AST extraction
log implemented in `specs/012` — MUST remain visible in the session, never summarized down to a
single completion signal. This is expected to resolve the symptom directly: the reason the
`specs/012` live-log behavior never activated when dispatched via master-orchestrator was the same
root cause (the spec containing that instruction was never loaded).

### 3.6 Collateral fix: `devops-agents/module.yaml` registration

Added the 4 missing entries (`ava-devops-cost-estimate`, `ava-devops-iac-aws/gcp/k8s-native`, the
latter 3 marked `status: stub` matching the file's own `0.1.0-stub` frontmatter and `🚧 STUB`
self-declaration).

## 4. Functional Changes by Component

| Component | Change |
|---|---|
| `master-orchestrator/agents/master-orchestrator.md` | New `## Dispatch Protocol` section; `## Agent Team` table `Spec File` column (+ 3 previously-missing STUB rows for iac-aws/gcp/k8s-native); 24 `DISPATCH` lines prefixed with `⛔ Read(...)`; frontmatter version + changelog line |
| `asis-diagnostic/agents/orchestrator-asis.md` | Step 3.1: `⛔ Read(...)` prefix before invoking `@{resolved_solution_agent}`; frontmatter version + changelog line |
| `devops-agents/module.yaml` | 4 missing agent registrations added; version `1.0.0` → `1.0.1` |

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — F1 via master-orchestrator now runs AST extraction (CA01)

**Given** a Delphi project with `ava_ast_analyzer_path` correctly configured, **When**
`master-orchestrator` reaches Step 1.1, **Then** it reads `orchestrator-asis.md` in full before
dispatching, which — following its own Step 3.1 — reads `solution-delphi.md` in full before
invoking it, which then executes Step 0's real AST extraction exactly as it does in the standalone
invocation case.

### Scenario 2 — Live extraction log visible when dispatched via master-orchestrator (CA02)

**Given** the AST extraction step is genuinely reached (Scenario 1), **When** it runs via
`run_in_background`+`Monitor` (per `specs/012`), **Then** its progress remains visible in the
session — not suppressed by any master-orchestrator-level summarization — because the spec
containing that instruction (`solution-delphi.md`) was actually loaded this time.

### Scenario 3 — All 22 other dispatch points hardened for consistency (CA03)

**Given** any of F2-F7's 22 remaining dispatch points, **When** master-orchestrator reaches that
step, **Then** it reads the target agent's spec file first — same protocol, no phase left with the
weaker, implicit-only behavior that caused the F1 bug.

### Scenario 4 — Previously-unregistered DevOps agents now resolve correctly (CA04)

**Given** `master-orchestrator` reaches F6 Step 6.5 (cloud-specific IaC) or Step 6.6 (cost
estimate), **When** it resolves the `Spec File` path via `## Agent Team` / `module.yaml`, **Then**
all 4 previously-unregistered agents (`iac-aws`, `iac-gcp`, `iac-k8s-native`, `cost-estimate`) now
resolve to a real, registered path.

## 6. Quality Gate Requirements

- [x] Agent IDs unchanged; frontmatter fields unchanged except `version`/`date`/`description` (Article II)
- [x] Version bumps: MINOR for `master-orchestrator.md` (new section, 24 sites touched, nothing removed), PATCH for `orchestrator-asis.md` (single-site reliability hardening) (Article X)
- [x] BDD scenarios cover the reported bug (CA01), the linked log-visibility symptom (CA02), the F2-F7 consistency extension (CA03), and the collateral module-registration fix (CA04) (Article VI)
- [x] No technology versions hardcoded (Article I)
- [x] No `[NEEDS CLARIFICATION]` markers — scope (both dispatch points + all F1-F7) confirmed with the user via `AskUserQuestion` before implementation

## 7. Dependencies

- `specs/012-solution-delphi-ast-analyzer-config-path` — the live-log/AST-extraction behavior this
  PBI makes reachable when dispatched via master-orchestrator (it already worked standalone).
- `specs/011-asis-orchestrator-solution-first-dispatch` — the Wave 1/Solution Agent Gate structure
  that Step 3.1's `Read` requirement now guards more reliably.
- Every module's own `module.yaml` (`asis-diagnostic`, `tobe-architecture`, `prototype`,
  `tech-stack`, `qa-agents`, `devops-agents`, `deliverables`, `summary`) — used as the source of
  truth for the `Spec File` column; all 24 paths confirmed via direct grep, not assumed.

## 8. Exclusions

- Did not audit whether the same "dispatch without Read" pattern exists *inside* other
  orchestrators' own sub-dispatches (e.g. `orchestrator-tobe.md` → its F2-internal sub-agents,
  `qa-orchestrator-agent.md` → its skills). Same risk class, not reported as broken, left as a
  possible future PBI.
- Did not introduce a SubAgent/Task-tool isolation mechanism — kept the repo's existing inline
  dispatch convention; only made the spec-read step explicit and mandatory instead of implicit.
- Did not touch the 4 newly-registered `devops-agents` entries' own file content — only their
  `module.yaml` registration.

## 9. Assumptions

- The "small, focused context favors implicit correct behavior; large, complex context does not"
  theory for why standalone invocation worked but master-orchestrator-dispatched invocation didn't
  is a plausible explanation, not independently verified against harness internals — the fix
  (making the requirement explicit rather than implicit) is correct regardless of which mechanism
  actually caused the divergence.
- Excluding `ava-summary` dispatches from the `Read`-first requirement is safe because those are
  deterministic Python script executions (`Bash: python build_summary_comprehensive.py`), not LLM
  agent invocations — there is no spec file to improvise away from.

## Success Criteria

| Criterion | Measure |
|---|---|
| All 24 dispatch points hardened | `grep -c "⛔ Read("` in `master-orchestrator.md` → 24 |
| No sub-step renumbering | Diff shows only the `DISPATCH` line changed at each site, no reindexing |
| Step 3.1 hardened | `orchestrator-asis.md` Step 3.1 contains `Read(...)` before `invocar` `@{resolved_solution_agent}` |
| Collateral registration fixed | `grep -n "ava-devops-cost-estimate\|ava-devops-iac-aws\|ava-devops-iac-gcp\|ava-devops-iac-k8s-native"` in `devops-agents/module.yaml` → all 4 present |
| `Spec File` column complete | Every row in `## Agent Team` has a non-empty `Spec File` value, verified against the corresponding `module.yaml` |
