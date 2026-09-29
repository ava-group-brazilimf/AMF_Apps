# Agent Development Tasks: Config-Driven AST Analyzer Path + Live Execution Log for `solution-delphi`

**Plan**: `specs/012-solution-delphi-ast-analyzer-config-path/plan.md`
**Status**: Implementation complete; verification in progress.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm `solution-delphi.md` frontmatter version (`2.2.0`) matches the new
  `v2.2:` changelog line in its own `description` field.

## Category 2 — Implementation

- [x] **2.1** `projects/_template/context/project-config.yaml`: new `ava_ast_analyzer_path: ""`
  field after `repository_path` — DONE
- [x] **2.2** `projects/Meu-ERP-007-AST-LLM-AS-IS-Orchestrator/context/project-config.yaml`:
  same field, value `C:\Desenv\repo\tool\ava-fabric-delphi-analyzer` — DONE
- [x] **2.3** `solution-delphi.md` Step 0: 4-step path-resolution procedure + corrected Bash
  command (bracket-optional `--ava-analyzer-path`) replacing the dead placeholder — DONE
- [x] **2.4** `solution-delphi.md` Step 0: `run_in_background: true` + `Monitor` instruction
  for real-time log visibility — DONE
- [x] **2.5** `solution-delphi.md` `## Input Contract` "Config:" line extended with
  `ava_ast_analyzer_path` — DONE
- [x] **2.6** `solution-delphi.md` failure branch: remediation hint pointing at
  `ava_ast_analyzer_path` — DONE
- [x] **2.7** `run_delphi_ast_analysis.py`: `subprocess.run(capture_output=True)` →
  `subprocess.Popen` + streaming read loop (`flush=True` per line) — DONE
- [x] **2.8** `run_delphi_ast_analysis.py`: `threading.Timer(1800, proc.kill)` timeout guard
  replacing `subprocess.run(timeout=1800)` — DONE
- [x] **2.9** `solution-delphi.md` frontmatter `version`/`description` changelog — DONE

## Category 3 — Schema Updates — SKIP

No new JSON artifact schema; `ava_ast_analyzer_path` is a plain YAML config field,
not a published schema.

## Category 4 — Module Registration — SKIP

No new agent registered; only `module.yaml`'s own `version` field bumped (Category 7).

## Category 5 — Quality Gate Checklists

- [x] **5.1** `grep -n "AVA_DELPHI_ANALYZER_HOME configurado"` in `solution-delphi.md` → only the intentional "NUNCA usar" anti-pattern example (line ~288), confirmed absent from the actual Bash command block
- [x] **5.2** `grep -c "ava_ast_analyzer_path"` present in both `project-config.yaml` files
  and in `solution-delphi.md` (Input Contract + Step 0)
- [x] **5.3** `python -m py_compile run_delphi_ast_analysis.py` → OK (verified in this session)
- [x] **5.4** `grep -c "capture_output=True"` in the script → 0 (removed)
- [x] **5.5** `grep -c "threading.Timer"` in the script → 1
- [x] **5.6** `grep -c "Monitor"` in `solution-delphi.md` Step 0 region → ≥1

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — config field set: real path used in the Bash command, no placeholder — PASS (structural)
- [x] **6.2** CA02 — config field empty: flag omitted, env var fallback preserved — PASS (structural)
- [x] **6.3** CA03 — neither configured: honest failure + remediation hint — PASS (structural)
- [x] **6.4** CA04 — long-running extraction visible via `run_in_background`+`Monitor`, full log still written to disk — PASS (structural; no live 30-min extraction run performed in this session)

## Category 7 — Documentation

- [x] **7.1** `module.yaml` (`asis-diagnostic`) — version `1.8.0`→`1.8.1`
- [x] **7.2** This spec-kit documentation (spec.md, plan.md, tasks.md) — DONE

## Category 8 — Amendment: Field Rename (same-day follow-up)

- [x] **8.1** `ava_delphi_analyzer_path` → `ava_ast_analyzer_path` renamed in
  `projects/_template/context/project-config.yaml` — DONE
- [x] **8.2** Same rename in `solution-delphi.md` (Input Contract + Step 0, all 6
  occurrences) — DONE
- [x] **8.3** Same rename in `projects/Meu-ERP-007-AST-LLM-AS-IS-Orchestrator/context/project-config.yaml`
  (corrected project reference — the `006` folder this PBI originally targeted no
  longer exists, renamed outside this repo session) — DONE
- [x] **8.4** Same rename applied to this spec's 3 documents (spec.md, plan.md,
  tasks.md) — updated in place, no new spec created, per explicit user instruction — DONE
- [x] **8.5** Same rename applied to `docs/plan/config-driven-AST-analyzer-live-execution.md`
  (untracked plan-review snapshot found via repo-wide grep, not a Spec Kit artifact
  but kept consistent) — DONE
- [x] **8.6** `solution-delphi.md` version `2.2.0`→`2.2.1` (PATCH — Input Contract
  field rename) — DONE
- [x] **8.7** Repo-wide grep confirms zero remaining occurrences of
  `ava_delphi_analyzer_path` — DONE

## Completion Checklist

- [x] Dead placeholder (`{AVA_DELPHI_ANALYZER_HOME configurado}`) eliminated from
  `solution-delphi.md`
- [x] `ava_ast_analyzer_path` resolves the analyzer path from `project-config.yaml`,
  with the pre-existing `AVA_DELPHI_ANALYZER_HOME` env var preserved as a fallback
  when the field is empty
- [x] AST extraction now streams live to the user (`Popen` + `flush=True` per line +
  `run_in_background`/`Monitor`) instead of silently blocking for up to 30 minutes
- [x] Original 30-minute hard timeout preserved via `threading.Timer`, correct even
  if the child process produces zero output
- [x] Script change verified via `py_compile`
- [x] Only the 2 files the user named got the new config field — no silent scope
  expansion to other existing projects
