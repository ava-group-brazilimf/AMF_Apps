# Agent Specification: Independent Verification of the Delphi Solution Agent's Step 0 (AST) + Immediate Console Warning

**Feature Branch**: `018-solution-delphi-ast-step0-verification-gate`
**Created**: 2026-07-15
**Status**: Implemented
**Change Type**: modify-existing (`orchestrator-asis.md` + `solution-delphi.md` + `module.yaml`, MINOR — new non-blocking verification + reinforced warning, no field removed)
**Input**: "O agente [solution-delphi] não esta obdencendo Step 0 Obrigatorio de execução da Analise AST — O cenario acontence quando chamo asis-orchestrator e master-orchestrator — O cenario ja foi corrigido no passo e voltou acontecer, agente pula o step e faz leitura do source code full — O esperado é quando agente verificar que o atributo do ava_ast_analyzer_path configura em project-config, o mesmo deve executar o tool para geração dos artefatos, esse step é obrigatorio, caso a tool falhe o agente de seguir lendo via LLM o source code — O agente deve avisar o usuario no console de execução quando não foi possivel executar a tool e motivo — Observas specs, historico dessa correção e solucionar o problema."

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-asis-orchestrator` | `agents/orchestrator-asis.md` | `2.19.1` → `2.20.0` (MINOR — new independent verification case in the Solution Agent Gate, no field removed) |
| `ava-asis-solution-delphi` | `agents/solution-delphi.md` | `2.2.1` → `2.3.0` (MINOR — immediate console warning on Step 0 failure + top-of-file gate banner, no field removed) |

**Phase**: F1. **Module**: `asis-diagnostic` (`module.yaml` `1.8.1` → `1.8.2`, PATCH — no new agent registered). **Also touched**: none — `master-orchestrator.md` and `run_delphi_ast_analysis.py` required no changes (see §8 Exclusions).

## 2. Problem Statement

This is the **third reported recurrence** of the same symptom: `ava-asis-solution-delphi`
silently skips Step 0 (the deterministic AST extraction via `run_delphi_ast_analysis.py`)
and falls back to reading the full Delphi source tree manually (`Glob`/`Grep`/`Read`) —
observed both via `ava-asis-orchestrator` and via `ava-master-orchestrator` dispatch, even
with `ava_ast_analyzer_path` correctly configured in `project-config.yaml`.

Two prior fixes already targeted this exact class of bug:

- `specs/011-asis-orchestrator-solution-first-dispatch` — split Phase A into Wave 1
  (solution agent + security) / Wave 2, with a blocking Solution Agent Gate so downstream
  agents never race ahead of the solution agent's artifacts.
- `specs/012-solution-delphi-ast-analyzer-config-path` — fixed a dead placeholder in Step
  0's Bash command and added a live streaming log via `Monitor`.
- `specs/013-master-orchestrator-mandatory-spec-read` — added a mandatory `⛔ Read(...)`
  before every `DISPATCH @agent-id` in `master-orchestrator.md` (24 sites) and in
  `orchestrator-asis.md`'s own Step 3.1, specifically because `master-orchestrator` was
  "becoming" `orchestrator-asis` (and `orchestrator-asis` was "becoming" `solution-delphi`)
  from generic knowledge instead of literally reading and following each spec's Step 0.

Direct re-read of the current files (not assumed from memory) confirms **none of the three
prior fixes regressed** — `solution-delphi.md` v2.2.1 still has an explicit, forceful Step 0
("⛔ EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO") and `orchestrator-asis.md` v2.19.1
still has the `⛔ Read(...)` prefix on its Wave 1 dispatch of the solution agent. The prose
enforcement has already been escalated three times and the symptom still recurs — reinforcing
the text a fourth time has a low expected return.

**New root cause identified (not covered by specs 011-013):** `orchestrator-asis.md` has **no
independent visibility** into whether Step 0 actually ran. Its `verify_artifacts()` /
`evaluate_solution_gate()` only check the solution agent's **final deliverables**
(`architecture-blueprint.md`, `pattern-classifications.json`, `bounded-context-map.md`, the
`.mmd` diagrams) — never the 9 JSONs under `delphi-ast-raw/compressed/`. Because the solution
agent produces the exact same final deliverables whether it used the real AST extraction or
fell back 100% to manual source reads, the gate opens identically either way — there is no
mechanism for the orchestrator (or the user) to distinguish "ran via AST" from "silently
skipped Step 0" without manually inspecting `delphi-ast-raw/` after the fact. Confirmed via
direct grep: `ava_ast_analyzer_path` is never referenced anywhere in `orchestrator-asis.md` —
only `security_enabled_asis` and `timing_benchmark_enabled` are read at Step 2 (Decompose).

This explains why the symptom recurs *silently*: even when Step 0 is skipped, the pipeline
finishes "green," with no warning anywhere — precisely the 4th point raised by the user
("the agent must warn the user in the console when it wasn't possible to run the tool, and
why").

## 3. Decision

Instead of escalating the prose a fourth time, close the gap with a **cheap, independent
check** (1-2 `Glob` calls, no LLM judgment required) inside `orchestrator-asis.md` itself,
that detects and warns even when the solution agent fails to follow its own Step 0 — without
depending on the LLM "remembering" to self-report. The check is **non-blocking** (WARN, not
HALT), consistent with the user's own framing ("if the tool fails, the agent should continue
reading via LLM") and with the existing degrade-and-continue philosophy from `specs/011`/
`specs/012` — `HALT` remains reserved for STUB agents and retries-exhausted (per `specs/011`).

### 3.1 `orchestrator-asis.md` — new independent verification (Caso 5.5)

- **Step 2 (Decompose)**: now also reads `ava_ast_analyzer_path` from `project-config.yaml`
  (same pattern already used for `security_enabled_asis`) when `legacy_technology == "delphi"`,
  storing it as `ast_analyzer_path_configured`.
- **`evaluate_solution_gate()` gains Caso 5.5**, evaluated only when
  `resolved_solution_agent == "ava-asis-solution-delphi"` and `ast_analyzer_path_configured`
  is non-empty, via the new `verify_ast_extraction_used()`:
  - `delphi-ast-raw/compressed/manifest.json` exists → `USED` (silent, happy path).
  - `manifest.json` absent but `delphi-ast-raw/run_delphi_ast_analysis.log` exists → Step 0
    was **attempted and failed**; the reason is read from the log's own error line (the
    script already prints an explicit `❌ ...` on every failure path) → `FAILED`.
  - Neither exists → Step 0 was **never invoked at all** (the reported bug) →
    `SKIPPED_UNVERIFIED`.
  - For `FAILED`/`SKIPPED_UNVERIFIED`: `emit_ast_step0_warning()` prints an explicit console
    banner (same visual style as the existing `halt_pipeline()` banners) naming the agent,
    the state, and the reason (when known), and registers the corresponding risk flag
    (`AST_UNAVAILABLE_DEGRADED_ANALYSIS` for `FAILED`, new `AST_STEP0_SKIPPED_UNVERIFIED` for
    `SKIPPED_UNVERIFIED`) — **the gate itself is unaffected**; `OPEN`/`RETRYING`/`HALT` are
    still decided exclusively by Casos 1-6 as before.
- This closes the gap **independently** of whether `solution-delphi.md` obeys its own Step 0
  — the guarantee now comes from a file-existence check, not from one more prose instruction.

### 3.2 `solution-delphi.md` — reinforced, immediate warning (defense in depth)

- New top-of-file "🛑 STEP 0 GATE" banner (same convention as the pre-existing "🛑 PRE-WRITE
  VALIDATION GATE" for `.mmd` files), placed before the Role/Persona section, so the Step 0
  mandate is not buried ~250 lines into the document behind Skills/Tools/Triggers content.
- Step 0's failure branch now requires printing an explicit `⚠️ Step 0 (extração AST)
  FALHOU — {motivo}` message to the console **immediately**, before proceeding to Step 1 —
  previously this was only "registered in the final report," which the user could miss until
  well after the run.

### 3.3 `module.yaml` (`asis-diagnostic`)

`1.8.1` → `1.8.2` (PATCH) — no new agent registered, version bump only.

## 4. Functional Changes by Component

| Component | Change |
|---|---|
| `agents/orchestrator-asis.md` | Step 2: reads `ava_ast_analyzer_path`; new `evaluate_solution_gate()` Caso 5.5; new `verify_ast_extraction_used()` and `emit_ast_step0_warning()` procedures; new bullet in "Regras de aplicação" clarifying Caso 5.5 never changes the gate's outcome; frontmatter version + changelog line |
| `agents/solution-delphi.md` | New "🛑 STEP 0 GATE" top-of-file banner; Step 0 failure branch: immediate console-print instruction (in addition to the pre-existing report-registration instruction); frontmatter version + changelog line |
| `module.yaml` (`asis-diagnostic`) | Version `1.8.1` → `1.8.2` |

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — AST used normally: no warning (CA01)

**Given** `ava_ast_analyzer_path` is configured and Step 0 succeeds, **When**
`evaluate_solution_gate()` reaches Caso 5.5, **Then** `manifest.json` is found,
`verify_ast_extraction_used()` returns `USED`, and no warning is emitted — identical to
today's happy-path behavior.

### Scenario 2 — Step 0 attempted and failed: warning with reason, pipeline continues (CA02)

**Given** Step 0 is invoked but `run_delphi_ast_analysis.py` fails (e.g. `run_pipeline.py`
exits non-zero), **When** Caso 5.5 runs, **Then** `run_delphi_ast_analysis.log` is found
(but not `manifest.json`), the reason is extracted from its own error line, an explicit
console warning is printed citing that reason, `AST_UNAVAILABLE_DEGRADED_ANALYSIS` is
registered, and the gate still returns `OPEN` (assuming final deliverables are otherwise
complete) — the pipeline is not blocked.

### Scenario 3 — Step 0 never invoked: stronger warning, pipeline still continues (CA03)

**Given** `ava_ast_analyzer_path` is configured but `solution-delphi` never invokes Step 0
at all (the reported bug), **When** Caso 5.5 runs, **Then** neither `manifest.json` nor
`run_delphi_ast_analysis.log` exist, `verify_ast_extraction_used()` returns
`SKIPPED_UNVERIFIED`, a distinct (stronger-worded) console warning is printed naming the
configured analyzer path and recommending re-running the solution agent, and
`AST_STEP0_SKIPPED_UNVERIFIED` is registered — the gate still returns `OPEN`, matching the
user's explicit instruction not to hard-stop the pipeline over this.

### Scenario 4 — Non-Delphi or unconfigured analyzer: check is skipped entirely, no false positive (CA04)

**Given** `legacy_technology != "delphi"` OR `ava_ast_analyzer_path` is empty/absent, **When**
`evaluate_solution_gate()` runs, **Then** Caso 5.5 is skipped entirely (its guard condition is
false) — no warning is ever emitted for technologies or projects where AST extraction was
never expected to run.

## 6. Quality Gate Requirements

- [x] Agent IDs unchanged (`ava-asis-orchestrator`, `ava-asis-solution-delphi`), frontmatter fields unchanged except `version`/`date`/`description` (Article II)
- [x] Version bumps MINOR for both agent files — new verification/warning behavior added, nothing removed (Article X)
- [x] BDD scenarios cover the happy path (CA01), attempted-and-failed (CA02), never-attempted (CA03), and the no-false-positive guard (CA04) (Article VI)
- [x] No technology versions hardcoded (Article I)
- [x] No `[NEEDS CLARIFICATION]` markers remain — WARN-not-HALT semantics were derived directly from the user's own explicit instruction ("if the tool fails, the agent should continue reading via LLM" / "must warn the user... and why")

## 7. Dependencies

- `specs/011-asis-orchestrator-solution-first-dispatch` — the Solution Agent Gate (`evaluate_solution_gate()`) this PBI extends with Caso 5.5; the existing `HALT`-only-for-STUB/retries-exhausted philosophy this PBI preserves.
- `specs/012-solution-delphi-ast-analyzer-config-path` — `run_delphi_ast_analysis.py`'s existing `run_delphi_ast_analysis.log` (written on every Step 0 attempt, success or failure) is read as-is by the new `verify_ast_extraction_used()`; no changes to the script were needed.
- `specs/013-master-orchestrator-mandatory-spec-read` — the `⛔ Read(...)` / log-visibility protocol this PBI's new console warnings ride on; `master-orchestrator.md` needed no direct edit because its existing "Dispatch Protocol" already mandates that sub-dispatch output remain visible, never summarized away.

## 8. Exclusions

- `master-orchestrator.md` — not modified. Its Step 1.1 `⛔ Read(orchestrator-asis.md)` (from `specs/013`) already forces the full `orchestrator-asis.md` spec — including the new Caso 5.5 warning logic — to be loaded before dispatch; no new dispatch-site change was needed.
- `run_delphi_ast_analysis.py` — not modified. It already writes `run_delphi_ast_analysis.log` on every attempt and prints an explicit `❌ ...` reason on every failure path (confirmed by direct read); the new orchestrator-side check reads this pre-existing artifact rather than requiring a new one.
- No new machine-readable status file (e.g. a dedicated `ast-extraction-status.json`) was introduced — the existing `manifest.json` (success signal) and `run_delphi_ast_analysis.log` (attempted-but-possibly-failed signal) together already distinguish all three states (`USED` / `FAILED` / `SKIPPED_UNVERIFIED`) without adding a new artifact to maintain.
- Non-Delphi solution agents (`solution-vb.md`, and the 3 STUB agents) — unaffected; Caso 5.5's guard is scoped to `ava-asis-solution-delphi` only, since it is the only solution agent with a real AST analyzer tool today (per `specs/012`'s own scope decision).
- Did not introduce a hard `HALT` for the `SKIPPED_UNVERIFIED` case — evaluated and explicitly rejected, since it would contradict the user's own stated expectation ("if the tool fails, keep reading via LLM") and the pre-existing degrade-and-continue design from `specs/011`/`specs/012`.

## 9. Assumptions

- Reading the last error line of `run_delphi_ast_analysis.log` is sufficient to recover a
  human-readable failure reason for the console warning, since `run_delphi_ast_analysis.py`
  already prints one explicit `❌ ...` line per failure branch (confirmed by direct read of
  the script — not modified by this PBI).
- A cheap `Glob`/file-existence check at the orchestrator level is an acceptable enforcement
  mechanism given this repository's constraint of prompt-only orchestration (no tool-level
  hooks available to block a `Read` call outright) — it cannot force Step 0 to run, but it
  guarantees the user is told when it didn't, closing the observability half of the problem
  even when the compliance half remains probabilistic.

## Success Criteria

| Criterion | Measure |
|---|---|
| Orchestrator reads the analyzer config | `grep -n "ava_ast_analyzer_path"` in `orchestrator-asis.md` → present (previously 0 occurrences) |
| New independent verification present | `grep -n "verify_ast_extraction_used\|SKIPPED_UNVERIFIED"` in `orchestrator-asis.md` → present, positioned between Caso 5 and Caso 6 |
| Gate outcome unaffected by the new check | Manual trace of Casos 1-6 shows Caso 5.5 never returns/overrides `gate` |
| Immediate console warning reinforced in the leaf agent | `solution-delphi.md` Step 0 failure branch contains an explicit "print now" instruction, not only "register in the report" |
| Versions bumped consistently | `orchestrator-asis.md` → `2.20.0`, `solution-delphi.md` → `2.3.0`, `module.yaml` → `1.8.2` |
