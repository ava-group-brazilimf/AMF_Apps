# Agent Implementation Plan: Config-Driven AST Analyzer Path + Live Execution Log for `solution-delphi`

**Spec**: `specs/012-solution-delphi-ast-analyzer-config-path/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (1 agent file + 1 util script + 2 project configs + `module.yaml`) |
| **Primary Requirement** | Replace a dead, never-resolved placeholder (`{AVA_DELPHI_ANALYZER_HOME configurado}`) in `solution-delphi.md`'s Step 0 Bash command with a real `project-config.yaml`-driven value (`ava_ast_analyzer_path`), and make the AST extraction's execution visible to the user in real time instead of silently blocking for up to 30 minutes |
| **Technical Approach** | Config field addition (agent-spec pattern, no code); `subprocess.run(capture_output=True)` → `subprocess.Popen` + streaming read loop + `threading.Timer` timeout guard in the util script; `run_in_background`/`Monitor` instruction added to the agent spec (harness-level live visibility) |
| **Implementation Status** | Complete. `py_compile` verified; structural greps below. Amended same-day: field renamed `ava_delphi_analyzer_path`→`ava_ast_analyzer_path` (`solution-delphi.md` `2.2.0`→`2.2.1`, PATCH). |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded.
- [x] **Article II** — frontmatter unchanged except `version`/`description`.
- [x] **Article V** — pt-BR body content preserved.
- [x] **Article VI** — BDD scenarios cover config-set, config-empty-fallback, neither-configured, live-visibility.
- [x] **Article X (SemVer)** — MINOR for `solution-delphi.md` (bugfix + additive, nothing removed); PATCH for `module.yaml` (no new agent registered).
- [x] No `[NEEDS CLARIFICATION]` markers.

## Technical Context

Two file types: (1) a prompt/instruction Markdown agent (`solution-delphi.md`) — "implementation"
means rewriting its Step 0 procedure so the next LLM-driven execution resolves the
analyzer path correctly and surfaces progress; (2) an actual Python utility script
(`run_delphi_ast_analysis.py`) — a real code change (subprocess streaming), verified
by `py_compile`. No new dependencies (`threading` is stdlib). Two YAML config files
(template + one real project) get a new field each.

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
Direct reads (not just an Explore-agent summary) of `solution-delphi.md` Step 0
(lines 258-313) and the full `run_delphi_ast_analysis.py` confirmed: the placeholder
bug is 100% in the agent's prompt text (the script's own `resolve_analyzer_path()`
already correctly implements CLI-arg-wins-over-env-var precedence); the script's
`capture_output=True` fully buffers the child process's output with zero live
visibility, on both success and failure paths. Verified the user's real analyzer
path (`C:\Desenv\repo\tool\ava-fabric-delphi-analyzer`) exists on disk with the
expected `src/run_pipeline.py` and `bin/ava_ast_cli.exe`.

### Phase 1 — Config Field ✅ CONCLUÍDO
`ava_ast_analyzer_path` added to `projects/_template/context/project-config.yaml`
(default `""`, placed right after `repository_path`, same comment style) and to
`projects/Meu-ERP-007-AST-LLM-AS-IS-Orchestrator/context/project-config.yaml` (real
value). Only these 2 files touched, per explicit user instruction — other existing
projects not retrofitted.

### Phase 2 — Agent Spec Fix ✅ CONCLUÍDO
`solution-delphi.md` Step 0: replaced the single dead-placeholder command with a
4-step resolution procedure (read config → conditional flag → omit-if-empty →
explicit anti-placeholder invariant) followed by the corrected Bash command using
bracket-optional flag notation (`[--ava-analyzer-path "{ava_ast_analyzer_path}"]`);
added a mandatory `run_in_background: true` + `Monitor` instruction with rationale
(30-min worst case, same "apparent hang" failure mode already fixed at the
orchestrator level in `specs/011`); extended the `## Input Contract` "Config:" line;
added a remediation hint to the pre-existing generic failure branch. Frontmatter
version + changelog line updated.

### Phase 3 — Script Streaming Rewrite ✅ CONCLUÍDO
`run_delphi_ast_analysis.py`: `subprocess.run(..., capture_output=True, timeout=1800)`
replaced with `subprocess.Popen(..., stdout=PIPE, stderr=STDOUT, text=True, bufsize=1)`
+ a `for line in proc.stdout` loop printing each line immediately with `flush=True`
(also setting `PYTHONUNBUFFERED=1` in the child's env) while accumulating lines for
the log file (same `run_delphi_ast_analysis.log` path/format intent, now merged
stdout+stderr in chronological order instead of two separate sections). Timeout
enforcement moved to a `threading.Timer(1800, proc.kill)` started before the loop —
deliberately NOT a per-line deadline check, since that would never fire if the child
produces zero output (blocked forever on the iterator's `next()` call, never
re-entering a body-level check).

### Phase 4 — Version Sync ✅ CONCLUÍDO
`solution-delphi.md` frontmatter `2.1.1`→`2.2.0` + new `v2.2:` changelog line (same
pattern as the file's own prior changelog style). `module.yaml` `1.8.0`→`1.8.1`.

### Phase 5 — Verification (this session)
`py_compile` on the modified script (passed); structural greps confirming the dead
placeholder is gone and the new field/streaming logic are present — see `## Test
Strategy` below. No live end-to-end run of the actual AST extraction was performed
in this session (would require the real Delphi repository + analyzer binary
execution, outside a documentation/prompt-engineering session's scope) — this is
consistent with `specs/010`/`specs/011`'s own precedent of structural-only
verification for this repo's agent-spec PBIs, with the one addition that the Python
script change here IS syntax-verified via `py_compile`, unlike pure-prose PBIs.

### Phase 6 — Amendment: Field Rename ✅ CONCLUÍDO (same day)
User renamed the config field `ava_delphi_analyzer_path` → `ava_ast_analyzer_path`
before wider adoption. Applied via targeted `sed` across all 7 files that referenced
the old name (both `project-config.yaml` files, `solution-delphi.md`, this spec's own
3 documents, plus an untracked `docs/plan/config-driven-AST-analyzer-live-execution.md`
snapshot the user had saved from the original plan-mode review — updated for
consistency even though it isn't a Spec Kit artifact). Also corrected the test-project
reference from the no-longer-existing `Meu-ERP-006-AST-LLM-AS-IS-Orchestrator` folder
to `Meu-ERP-007-AST-LLM-AS-IS-Orchestrator` (renamed outside this repo session,
between the original PBI and this amendment). `solution-delphi.md` bumped
`2.2.0`→`2.2.1` (PATCH) since the renamed field is part of the documented
`## Input Contract`. No new spec created, per explicit user instruction — this plan
and its spec/tasks siblings were updated in place instead.

## Complexity Tracking

| Item | Status |
|---|---|
| Streaming rewrite risks losing the original hard 30-minute timeout if implemented naively (per-line deadline check) | Solved with `threading.Timer(1800, proc.kill)`, which fires regardless of whether the child process is producing output — a strictly equivalent guarantee to the original `subprocess.run(timeout=1800)`, not a weaker approximation |
| `Monitor`-based live visibility depends on harness behavior (a plain foreground Bash call blocks until exit, streaming or not) | Deliberately paired the script-level streaming fix with an explicit `run_in_background: true` + `Monitor` instruction in the agent spec — neither change alone solves the "invisible 30-minute step" problem, both were required |
| Whether to retrofit `ava_ast_analyzer_path` into other existing projects (`Meu-ERP-006-AST-LLM`, `Meu-ERP`) | Deliberately out of scope — user named exactly 2 files; noted in spec.md §8 Exclusions rather than silently expanding scope |

## Test Strategy

| Test | Command | Expected |
|---|---|---|
| Dead placeholder eliminated from the live command | `grep -n "AVA_DELPHI_ANALYZER_HOME configurado"` in `solution-delphi.md` | Only the intentional anti-pattern example in the new invariant, never inside the actual Bash command |
| New field present in both configs | `grep -c "ava_ast_analyzer_path"` in each `project-config.yaml` | ≥1 each |
| New field referenced in agent spec | `grep -c "ava_ast_analyzer_path"` in `solution-delphi.md` | ≥2 (Input Contract + Step 0) |
| Script compiles | `python -m py_compile run_delphi_ast_analysis.py` | OK (verified) |
| Streaming implemented, not blocking capture | `grep -c "capture_output=True"` in the script | 0 (removed) |
| Timer-based timeout present | `grep -c "threading.Timer"` in the script | 1 |
| `Monitor` instruction present | `grep -c "Monitor"` in `solution-delphi.md` Step 0 region | ≥1 |
