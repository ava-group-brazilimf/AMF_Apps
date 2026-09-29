# Agent Implementation Plan: Independent Verification of the Delphi Solution Agent's Step 0 (AST) + Immediate Console Warning

**Spec**: `specs/018-solution-delphi-ast-step0-verification-gate/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (2 agent files + 1 `module.yaml`, no new agents) |
| **Primary Requirement** | `ava-asis-solution-delphi` keeps silently skipping Step 0 (deterministic AST extraction) when dispatched via `ava-asis-orchestrator`/`ava-master-orchestrator`, despite 3 prior fixes (`specs/011`, `specs/012`, `specs/013`) already targeting this exact symptom. Root cause this time: `orchestrator-asis.md` has no independent way to know Step 0 ran — `verify_artifacts()` only checks final deliverables, which look identical whether the AST extraction ran or was skipped entirely. |
| **Technical Approach** | New non-blocking Caso 5.5 in `evaluate_solution_gate()` — a cheap `Glob`-based check (`manifest.json` / `run_delphi_ast_analysis.log`) independent of the leaf agent's self-reporting — plus a reinforced immediate-console-warning instruction and top-of-file gate banner in `solution-delphi.md` itself (defense in depth, not the primary fix). |
| **Implementation Status** | Complete. Structural greps below. |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded.
- [x] **Article II** — frontmatter unchanged except `version`/`date`/`description` on both agent files.
- [x] **Article VI** — BDD scenarios cover the happy path, attempted-and-failed, never-attempted, and the non-Delphi/unconfigured no-false-positive guard.
- [x] **Article X (SemVer)** — MINOR for both `orchestrator-asis.md` (new gate case) and `solution-delphi.md` (new warning behavior + banner), PATCH for `module.yaml` (no new agent).
- [x] No `[NEEDS CLARIFICATION]` markers — WARN-vs-HALT semantics for the "never attempted" case were resolved directly from the user's own input text, not left ambiguous.

## Technical Context

Pure Markdown/prose edits to 2 LLM-prompt agent files (not executable code) plus one YAML
version bump. No changes to `run_delphi_ast_analysis.py` were needed — it already writes
`run_delphi_ast_analysis.log` on every Step 0 attempt (success or failure) and prints an
explicit `❌ ...` reason line on every failure branch (confirmed by direct read), which the
new orchestrator-side check reads as-is.

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO

Direct reads (not delegated) of `solution-delphi.md`, `orchestrator-asis.md`, and
`master-orchestrator.md` confirmed all three prior fixes (`specs/011`/`012`/`013`) are still
present and intact in the current files — this is not a file-level regression. Grepped
`orchestrator-asis.md` for `ava_ast_analyzer_path` → 0 occurrences, confirming the
orchestrator never reads this field and therefore has no way to reason about whether Step 0
should have run. Read `verify_artifacts()`'s `artifact_contracts.ava-asis-solution-delphi`
table directly and confirmed it only lists final deliverables
(`architecture-blueprint.md`, `.mmd` diagrams, etc.) — never the 9
`delphi-ast-raw/compressed/*.json` files. Read `run_delphi_ast_analysis.py` directly and
confirmed it writes `run_delphi_ast_analysis.log` and prints an explicit failure reason on
every non-zero-exit path, on both the "attempted and failed" and (implicitly, via absence)
the "never attempted" cases.

### Phase 1 — Gate Extension Design ✅ CONCLUÍDO

Decided to hook the new check into `evaluate_solution_gate()` (the existing decision point
already evaluated once per Wave 1 completion event) rather than `verify_artifacts()` (which
runs per-agent generically and has no Delphi/AST-specific knowledge) — keeps the Delphi-AST
concern scoped to the one place that already knows about `resolved_solution_agent` and the
Wave 1/Wave 2 boundary. Decided against introducing a new machine-readable status file —
`manifest.json` (success signal, pre-existing) and `run_delphi_ast_analysis.log`
(attempted-but-possibly-failed signal, pre-existing) already distinguish all 3 states
needed (`USED`/`FAILED`/`SKIPPED_UNVERIFIED`) without adding a new artifact to maintain.

### Phase 2 — `orchestrator-asis.md` Implementation ✅ CONCLUÍDO

- Step 2 (Decompose): added read of `ava_ast_analyzer_path` (conditional on
  `legacy_technology == "delphi"`), stored as `ast_analyzer_path_configured`.
- `evaluate_solution_gate()`: inserted Caso 5.5 between the pre-existing Caso 5
  (artifacts-missing → HALT) and Caso 6 (success → OPEN) — calls
  `verify_ast_extraction_used()` and, on any non-`USED` state, calls
  `emit_ast_step0_warning()`. Neither procedure can change the gate's own `OPEN`/`RETRYING`/
  `HALT` outcome — verified by construction (Caso 5.5 has no `RETURN` statement).
- New `verify_ast_extraction_used()` and `emit_ast_step0_warning()` procedures added directly
  below the `evaluate_solution_gate()` code block, reusing the same visual banner convention
  as the pre-existing `halt_pipeline()`.
- New bullet added to "Regras de aplicação" clarifying Caso 5.5's independence from the
  gate's final decision.
- Frontmatter version (`2.19.1`→`2.20.0`) + changelog line.

### Phase 3 — `solution-delphi.md` Implementation ✅ CONCLUÍDO

- New "🛑 STEP 0 GATE — ABSOLUTE INVARIANT" banner added at the top of the file (mirroring
  the pre-existing "🛑 PRE-WRITE VALIDATION GATE" convention for `.mmd` files), placed before
  the Role/Persona section so it can't be missed behind ~250 lines of Skills/Tools content.
- Step 0's "SE falhar" branch: added an explicit, first-priority instruction to print an
  `⚠️ Step 0 (extração AST) FALHOU — {motivo}` message to the console **immediately** on
  detection, before proceeding to Step 1 — in addition to (not replacing) the pre-existing
  report-registration instruction.
- Frontmatter version (`2.2.1`→`2.3.0`) + changelog line.

### Phase 4 — `module.yaml` Version Bump ✅ CONCLUÍDO

`asis-diagnostic/module.yaml`: `1.8.1` → `1.8.2` (PATCH, no new agent registered).

### Phase 5 — Verification (this session) ✅ CONCLUÍDO

Structural greps confirming the new `ava_ast_analyzer_path` read, the new Caso 5.5 /
`SKIPPED_UNVERIFIED` block, the immediate-console-print instruction in `solution-delphi.md`,
and consistent frontmatter versions across all 3 touched files — see `## Test Strategy`
below. No live pipeline run performed in this session (prose instruction files, not
executable code) — consistent with `specs/011`/`specs/012`/`specs/013`'s own precedent of
structural-only verification for this repo's agent-spec PBIs.

## Complexity Tracking

| Item | Status |
|---|---|
| Third recurrence of the same symptom — risk of repeating a fix that already failed twice | Deliberately chose a different lever this time (independent file-existence check at the orchestrator level) instead of a 4th round of stronger prose in the leaf agent, since the first 3 rounds were all prose-only and all eventually recurred |
| New gate case could accidentally change `OPEN`/`HALT` semantics | Caso 5.5 has no `RETURN` — verified by direct re-read after editing that control flow always falls through to Caso 6 regardless of `ast_status.state` |
| Reusing existing artifacts (`manifest.json`, `run_delphi_ast_analysis.log`) vs. introducing a new dedicated status file | Chose reuse — confirmed both files already exist under all 3 needed states without requiring any change to `run_delphi_ast_analysis.py` |
| Scope creep risk (extending the check to non-Delphi solution agents) | Explicitly scoped to `ava-asis-solution-delphi` only, matching `specs/012`'s own precedent that only Delphi has a real AST analyzer tool today |

## Test Strategy

| Test | Command | Expected |
|---|---|---|
| Orchestrator now reads the analyzer config | `grep -n "ava_ast_analyzer_path"` in `orchestrator-asis.md` | ≥1 occurrence (previously 0) |
| New Caso 5.5 present | `grep -n "Caso 5.5\|verify_ast_extraction_used\|SKIPPED_UNVERIFIED"` in `orchestrator-asis.md` | Present, positioned between Caso 5 and Caso 6 |
| Gate outcome unaffected | Manual trace of `evaluate_solution_gate()` | Caso 5.5 has no `RETURN`; falls through to Caso 6 |
| Immediate console warning reinforced | `grep -n "AVISO IMEDIATO NO CONSOLE"` in `solution-delphi.md` | Present in Step 0's failure branch |
| Top-of-file banner present | `grep -n "STEP 0 GATE"` in `solution-delphi.md` | Present before `# AVA — AS-IS Solution Agent (Delphi)` |
| Frontmatter version consistency | `orchestrator-asis.md` → `2.20.0`, `solution-delphi.md` → `2.3.0`, `module.yaml` → `1.8.2` | All match |
