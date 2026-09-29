# Agent Specification: Config-Driven AST Analyzer Path + Live Execution Log for `solution-delphi`

**Feature Branch**: `012-solution-delphi-ast-analyzer-config-path`
**Created**: 2026-07-08
**Status**: Implemented
**Change Type**: modify-existing (`solution-delphi.md` + `run_delphi_ast_analysis.py` + 2 `project-config.yaml` files + `module.yaml`, MINOR — bugfix + additive behavior, no field removed)
**Input**: "O agente solution-delphi retornou o seguinte problema: AST extraction failed — AVA_DELPHI_ANALYZER_HOME not configured [...] Para não depender de uma variavel sistemica, vamos criar uma configuração no arquivo project-config.yaml [...] O atributo {ava_ast_analyzer_path} deve apontar para o caminho da tool AST [...] o agente de solution-delphi executar o comando [...] usando a nova variável [...] o agente deve exibir o log de acompanhamento de execução da tool para usuario fazer o acompanhamento da execução."

**Amendment (2026-07-08, same-day follow-up)**: config field renamed `ava_delphi_analyzer_path`
→ `ava_ast_analyzer_path` across all referencing files (broader "AST" naming — not tied to a
single legacy technology's tooling, even though the analyzer tool itself is Delphi-specific
today). Also updated the test-project config reference from `Meu-ERP-006-AST-LLM-AS-IS-Orchestrator`
(renamed/replaced outside this repo session) to `Meu-ERP-007-AST-LLM-AS-IS-Orchestrator`. Applied
in place per user instruction — no new spec created. `solution-delphi.md` bumped `2.2.0`→`2.2.1`
(PATCH — the field is part of the documented `## Input Contract`, so its rename is a contract
change worth tracking, even though it carries no new behavior).

---

## 1. Agent Identity

| Field | File | Version |
|---|---|---|
| `ava-asis-solution-delphi` | `agents/solution-delphi.md` | `2.1.1` → `2.2.0` (MINOR — bugfix + additive behavior, no field removed) → `2.2.1` (PATCH — same-day amendment, `ava_delphi_analyzer_path` renamed to `ava_ast_analyzer_path`) |

**Phase**: F1. **Module**: `asis-diagnostic`. Also touched:
`utils/run_delphi_ast_analysis.py` (streaming rewrite, no version header — plain
util script, not an agent frontmatter), `projects/_template/context/project-config.yaml`,
`projects/Meu-ERP-007-AST-LLM-AS-IS-Orchestrator/context/project-config.yaml`,
`module.yaml` (`1.8.0`→`1.8.1`, PATCH — no new agent registered).

## 2. Problem Statement

The user reported `ava-asis-solution-delphi` failing its AST extraction with
`AST extraction failed — AVA_DELPHI_ANALYZER_HOME not configured`, falling back to
degraded Glob/Grep/Read analysis. Root cause, confirmed by direct read of
`solution-delphi.md:280-282`: the Bash command in Step 0 contained a **literal,
never-resolved placeholder**:

```
--ava-analyzer-path {AVA_DELPHI_ANALYZER_HOME configurado}
```

This string was never connected to any real source — not an env var read, not a
`project-config.yaml` lookup, just dead prompt text the LLM had no way to resolve.
`run_delphi_ast_analysis.py`'s own `resolve_analyzer_path()` (line 45-50) already
correctly supports `--ava-analyzer-path` (CLI, takes precedence) with an
`AVA_DELPHI_ANALYZER_HOME` env var fallback — the bug was entirely in the agent's
instructions, not the script's argument handling.

A second, related problem: the script used `subprocess.run(..., capture_output=True)`
(a blocking call with a 30-minute timeout) to invoke the external analyzer
(`run_pipeline.py`/`ava_ast_cli.exe`). The child process's own output was fully
buffered and never shown to the user during execution — only a final summary
(success) or the last 2000 characters of stderr (failure). For a step that can
legitimately run up to 30 minutes, this produces the same kind of "silent apparent
hang" symptom already diagnosed and fixed at the orchestrator level earlier in this
engagement (see `specs/011`) — here at the leaf-agent level instead.

## 3. Decision

### 3.1 `ava_ast_analyzer_path` config field replaces the env-var dependency

New field added to `project-config.yaml`, same style/placement as `repository_path`
(quoted absolute path, terse pt-BR inline comment):
- `projects/_template/context/project-config.yaml` — default `""`
- `projects/Meu-ERP-007-AST-LLM-AS-IS-Orchestrator/context/project-config.yaml` —
  real value `"C:\\Desenv\\repo\\tool\\ava-fabric-delphi-analyzer"` (verified to
  exist, with `src/run_pipeline.py` and `bin/ava_ast_cli.exe` present)

### 3.2 `solution-delphi.md` Step 0 resolves the path from config, not from a dead placeholder

A new explicit 4-step "Resolução do path do analyzer" procedure precedes the Bash
command: read `ava_ast_analyzer_path` from `project-config.yaml`; if non-empty,
pass it via `--ava-analyzer-path`; if empty/absent, **omit the flag entirely**
(preserves the pre-existing `AVA_DELPHI_ANALYZER_HOME` env var fallback for anyone
still using it — zero regression); an explicit invariant forbids ever using an
unresolved literal placeholder again.

### 3.3 Live execution log — two complementary changes

Neither alone solves the "invisible 30-minute step" problem:

- **`run_delphi_ast_analysis.py`**: `subprocess.run(capture_output=True)` replaced
  with `subprocess.Popen` + line-by-line read loop, printing each line immediately
  (`flush=True`) as it arrives, while also accumulating it for the log file (same
  `run_delphi_ast_analysis.log` path as before). A `threading.Timer(1800, proc.kill)`
  preserves the original 30-minute hard timeout even if the child process produces
  zero output (a case a naive per-line deadline check would miss, since blocking on
  the next line's arrival never re-enters the check).
- **`solution-delphi.md` Step 0**: explicitly instructs invoking this Bash command
  with `run_in_background: true` and using `Monitor` to stream/display the tool's
  progress to the user until completion — the only mechanism in this harness that
  gives genuine real-time visibility into a long-running synchronous subprocess (a
  plain foreground Bash call blocks the agent until exit regardless of how the
  script itself buffers).

### 3.4 Failure-path remediation hint

The pre-existing generic `AST_UNAVAILABLE_DEGRADED_ANALYSIS` failure branch now also
notes, when the cause is an unconfigured analyzer path, that the fix is filling
`ava_ast_analyzer_path` in `project-config.yaml` (or the env var as an
alternative) — closing the loop for whoever reads the risk report.

## 4. Functional Changes by Component

| Component | Change |
|---|---|
| `agents/solution-delphi.md` | Step 0: new path-resolution procedure (4 steps) + `run_in_background`/`Monitor` instruction; `## Input Contract` "Config:" line extended with `ava_ast_analyzer_path`; failure branch remediation hint; frontmatter version + changelog line |
| `utils/run_delphi_ast_analysis.py` | `subprocess.run(capture_output=True)` → `subprocess.Popen` + streaming read loop + `threading.Timer` timeout guard; `import threading` added |
| `projects/_template/context/project-config.yaml` | New `ava_ast_analyzer_path: ""` field after `repository_path` |
| `projects/Meu-ERP-007-AST-LLM-AS-IS-Orchestrator/context/project-config.yaml` | Same field, real value `C:\Desenv\repo\tool\ava-fabric-delphi-analyzer` |
| `module.yaml` (`asis-diagnostic`) | `1.8.0` → `1.8.1` (PATCH) |

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Config field set: real path used, no placeholder (CA01)

**Given** `ava_ast_analyzer_path` is filled in `project-config.yaml`, **When**
`solution-delphi` reaches Step 0, **Then** the Bash command includes
`--ava-analyzer-path "{the configured value}"` — never the literal string
`{AVA_DELPHI_ANALYZER_HOME configurado}` — and the AST extraction runs against the
real tool.

### Scenario 2 — Config field empty: env var fallback preserved (CA02)

**Given** `ava_ast_analyzer_path` is empty or absent, **When** Step 0 builds the
command, **Then** the `--ava-analyzer-path` flag is omitted entirely, and
`resolve_analyzer_path()` falls back to `AVA_DELPHI_ANALYZER_HOME` exactly as before
this change — no regression for existing env-var-based setups.

### Scenario 3 — Neither configured: honest, actionable failure (CA03)

**Given** neither the config field nor the env var is set, **When** the script runs,
**Then** it prints its pre-existing explicit error and exits 1; the agent registers
`AST_UNAVAILABLE_DEGRADED_ANALYSIS` with the new remediation hint pointing at
`ava_ast_analyzer_path`, and proceeds in degraded mode without blocking delivery
(unchanged behavior — see `specs/011`'s Solution Agent Gate, which treats this
correctly as a real failure/retry case, not silently ignored).

### Scenario 4 — Long-running extraction is visible, not silent (CA04)

**Given** a large repository where the AST extraction takes several minutes, **When**
Step 0 runs the Bash command in the background and attaches `Monitor`, **Then** the
user sees the tool's progress lines as they're produced (not just a final summary),
and the full transcript is still written to
`projects/{project_name}/outputs/asis/delphi-ast-raw/run_delphi_ast_analysis.log` for
later reference.

## 6. Quality Gate Requirements

- [x] Agent ID unchanged (`ava-asis-solution-delphi`), frontmatter fields unchanged except `version`/`description` (Article II)
- [x] Version bump MINOR (`2.1.1`→`2.2.0`) — bugfix (dead placeholder) + additive behavior (live log, config field), no Input/Output Contract field removed (Article X)
- [x] BDD scenarios cover config-set, config-empty-fallback, neither-configured, and live-visibility (Article VI)
- [x] No technology versions hardcoded (Article I)
- [x] No `[NEEDS CLARIFICATION]` markers remain

## 7. Dependencies

- `resolve_analyzer_path()` in `run_delphi_ast_analysis.py` (pre-existing, unchanged) —
  the CLI-arg/env-var precedence this fix relies on for the fallback path
- `Monitor` tool (harness-level) — required for Step 0's real-time log instruction to
  be actionable at execution time
- `specs/011-asis-orchestrator-solution-first-dispatch` — the orchestrator-level
  Solution Agent Gate that now correctly hard-stops the pipeline if this agent's AST
  extraction fails after retries; this PBI makes that failure mode less likely to
  trigger spuriously (real path resolution instead of a dead placeholder)

## 8. Exclusions

- No change to `resolve_analyzer_path()`'s own precedence logic (CLI arg wins over
  env var) — the agent-level fix simply supplies a real CLI arg value when available,
  instead of a broken one.
- No change to the external `ava-fabric-delphi-analyzer` tool itself (`run_pipeline.py`,
  `ava_ast_cli.exe`) — out of this repo's scope.
- `orchestrator-asis.md` — not touched; this PBI is scoped to the leaf agent and its
  invoked script, consistent with `specs/011`'s own scope boundary (mirror image: that
  PBI touched only the orchestrator, this one touches only the leaf agent + script).
- Other existing projects (e.g. `Meu-ERP-006-AST-LLM`, `Meu-ERP`) — not updated with
  the new field; only the template and the specific project named by the user were
  changed, per explicit instruction.

## 9. Assumptions

- `threading.Timer`-based timeout enforcement is an acceptable stdlib-only substitute
  for `subprocess.run(timeout=...)`'s built-in timeout, now that streaming requires
  `Popen` — verified to correctly cover the "child process produces zero output"
  edge case that a simple per-line deadline check would miss.
- `PYTHONUNBUFFERED=1` in the child's env plus `flush=True` on every print is
  sufficient to guarantee prompt visibility through `Monitor`, without needing
  further changes to the external analyzer tool's own buffering behavior (outside
  this repo's control).

## Success Criteria

| Criterion | Measure |
|---|---|
| Dead placeholder eliminated from the live command | `grep -n "AVA_DELPHI_ANALYZER_HOME configurado"` in `solution-delphi.md` → only the intentional "NUNCA usar" anti-pattern example in the new invariant (line ~288), never inside the actual Bash command block |
| Config field present everywhere required | `grep -c "ava_ast_analyzer_path"` → ≥1 in both `project-config.yaml` files and in `solution-delphi.md` (Input Contract + Step 0) |
| Fallback preserved | `resolve_analyzer_path()` unchanged; Step 0 omits the flag (not an empty-string flag) when the config field is unset |
| Script compiles | `python -m py_compile run_delphi_ast_analysis.py` → OK |
| Live streaming implemented | `run_delphi_ast_analysis.py` uses `subprocess.Popen` (not `subprocess.run(capture_output=True)`) with a per-line `print(..., flush=True)` |
| Timeout preserved | `threading.Timer(1800, proc.kill)` present and started before the read loop |
