# Agent Specification: Observability Self-Report Activation Fix

**Feature Branch**: `004-observability-self-report-activation-fix`
**Created**: 2026-07-04
**Status**: Superseded

> ⚠️ **Update 2026-07-04 (same day)**: this fix's own approach — inlining
> `track` calls behind a `ver @observability-self-report` reference — still
> did not fire in real user testing, and a deeper environmental gap (no
> enforced tool-calling harness anywhere in this repo) was discovered. See
> `specs/005-observability-mandatory-phase/` for the corrected approach
> (self-contained mandatory phase, no reference indirection, applied to all
> 97 agent files) and the honest documentation of the environmental
> constraint that no `.md` wording can fully resolve.
**Change Type**: modify-existing (5 orchestrator-tier agent files, root-cause bugfix of specs/003)
**Input**: "Verifique a implementação da observabilidade dos agentes — Ainda não está sendo gerado a observabilidade por agente conforme o proposto na especificação."

---

## 1. Problem Statement

`specs/003-agent-self-observability/` added a shared instruction file and a
one-line reference into 97 agent `.md` files, intended so every agent calls
`pipeline_observer.py track` on itself before its own completion signal. The
user reported this was never actually generating output. Investigation
confirmed: **zero `outputs/observability/` directories exist anywhere**, not
even the flat aggregate state that `ava-master-orchestrator`'s own PBI-002
integration would produce. The feature had never fired, not once.

**Root cause**: in every sampled file, the inserted self-report section sat
*after* the point where the file's own instructions describe the agent as
finished — structurally identical to `## i18n`/`## Changelog` (passive
reference material), not a required next step. `ava-master-orchestrator`'s
own `init`/`track`/`finalize` calls had the same problem: documented only in
a disconnected appendix, never inside the literal `Step 0`–`Step 7` sequence
it actually executes. The proven counter-example exists in the same files:
`ntp_time.py` calls, written as literal inline sub-steps, DO fire reliably.

## 2. Decision

Keep the self-report architecture (each agent tracks *itself*) rather than
switching to caller-side tracking. Fix by relocating the call into each
file's own genuine completion point — the same treatment as `ntp_time.py`.
**Scope**: `ava-master-orchestrator` + the 4 phase orchestrators
(`orchestrator-asis.md`, `orchestrator-tobe.md`, `orchestrator-stack.md`,
`qa-orchestrator-agent.md`). The other ~92 leaf-agent files keep their
existing (still non-functional) placement — fixing those requires per-file
anchor detection across genuinely heterogeneous structures (numbered step vs.
`## Handoff` vs. `### Step N — Completion Gate`) and is explicitly deferred.

## 3. Functional Changes by Component

| File | Anchor found | Fix applied |
|---|---|---|
| `master-orchestrator.md` | Explicit `## Completion Signal` (already existed, lines 802-808) | `init` inlined into Step 0.4; `track` + `finalize --auto-report` inserted immediately before the literal `↳ ✅` line; old appendix demoted to "reference only"; fixed a pre-existing `5.8`/`5.9` duplicate-step-numbering bug found while touching Step 5; version `1.1.0`→`1.4.0` |
| `orchestrator-asis.md` | `## Orchestration Completion Gate` (the file's real "before I close" gate) | new bullet: `track` call inserted before "Exibir Completion Banner"; old broken appendix removed; version `2.18.0`→`2.18.1` |
| `orchestrator-tobe.md` | `## Execution Timing Output` (its own "Step 6, mandatory before closing" block) | `track` call inserted before the `## ❱ Execução Concluída` template; old broken appendix removed; version `2.1.0`→`2.1.1` |
| `orchestrator-stack.md` | `## Execution Timing Output` (its own "Step 10, mandatory before closing" block) | same pattern; version `1.7.0`→`1.7.1` |
| `qa-orchestrator-agent.md` | `## Terminal Mandatory Steps (PT → RS)` (its own final gate) | new `### Passo T3 — Registrar Auto-Observabilidade` step; version `1.2.0`→`1.2.1` |

None of the 4 phase orchestrators had an explicit, literal
`↳ ✅ [ava-{phase}-orchestrator]` line of their own prior to this fix — that
signal was only referenced from the *caller's* side and treated as an
implicit, inherited convention. Rather than inventing a brand-new section
disconnected from each file's real structure, the fix reused whichever
mandatory "before I close" gate each file already had (confirmed present in
all 4, under different names), which is both lower-risk and keeps the file
internally consistent with its own established terminal-step convention.

## 4. Incidental Findings and Fixes

- **`master-orchestrator.md` Step 5 duplicate numbering**: `5.8`/`5.9` were
  reused for two different sub-steps. Renumbered the second occurrence to
  `5.10`–`5.12`.
- **`orchestrator-tobe.md` two unrelated regressions**, discovered while
  editing the same region, pre-dating this fix and unrelated to
  observability: (a) the `## ❱ Execução Concluída — TO-BE` heading had lost
  its `{project_name}` placeholder in both timing templates — restored; (b) a
  stray orphaned closing code fence at the very end of the file (absent in
  the git-committed HEAD version) — removed. Both were introduced by an
  earlier edit in this same working session, not by an external actor, and
  are corrected here since they were directly adjacent to the work.
- **`orchestrator-tobe.md` line-ending drift**: the file was natively LF in
  git HEAD; an editor auto-format pass converted it to CRLF and re-padded
  every markdown table's column widths (cosmetic only, verified byte-for-byte
  identical text content). Normalized back to LF to keep the diff readable;
  the table padding could not be cheaply reverted and is left as-is (harmless).

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Master-orchestrator produces real output (CA01)

**Given** `pipeline_observer.py init`/`track`/`finalize --auto-report` are
now inline in master-orchestrator's own Step 0.4 and Completion Signal,
**When** a real invocation of `ava-master-orchestrator` runs to completion,
**Then** `projects/{project}/outputs/observability/pipeline-run-state.json`,
`.../ava-master-orchestrator/metrics.json`, and the 4-sheet Excel report in
`docs/optimization/` are created — none of which had ever been produced
before this fix.

### Scenario 2 — Phase orchestrators self-report through their own real gate (CA02)

**Given** any of the 4 phase orchestrators is dispatched (by master, or
standalone), **When** it reaches its own pre-existing mandatory closing gate
(`Orchestration Completion Gate` / `Execution Timing Output` / `Terminal
Mandatory Steps`), **Then** it calls `track` for itself before emitting its
timing/completion output — not in a disconnected appendix.

### Scenario 3 — Dry-run proves the mechanism works (CA03)

**Given** a manual invocation of the same commands master-orchestrator's new
inline steps describe, **When** run end-to-end
(`init`→`track --agent ava-master-orchestrator`→`finalize --auto-report`),
**Then** the per-agent folder and the 4-sheet Excel report are produced —
verified directly in this session.

### Scenario 4 — 92 leaf agents remain a known, explicit gap (CA04, negative)

**Given** any non-orchestrator agent (e.g. `ava-qa-scenario-generator`),
**When** it completes, **Then** its self-report reference is still in the
old (appendix-style) location and will **not** reliably fire — this is
explicitly out of scope for this PBI, not silently left broken.

## 6. Quality Gate Requirements

- [x] No agent `name:`/`description:`/`allowed-tools:` changed in any of the 5 files (Article II)
- [x] Version bumps applied to all 5 files (PATCH-level, instrumentation/bugfix, no input/output contract change) (Article X)
- [x] BDD scenarios cover the fix, the mechanism proof, and the explicit remaining gap (Article VI)
- [x] No `[NEEDS CLARIFICATION]` markers remain

## 7. Dependencies

- `specs/002-agent-pipeline-observability` (the tool itself, unchanged) and
  `specs/003-agent-self-observability` (the shared doc + original, broken
  rollout) must both already exist.

## 8. Exclusions

- The ~92 non-orchestrator agent files are **not** touched by this PBI —
  their self-report references remain in the original (non-functional)
  location. A follow-up PBI should design a multi-pattern anchor detector
  before attempting that batch again.
- No change to `pipeline_observer.py`'s own logic.
- No orchestrator-side (caller-tracks-children) mechanism introduced — the
  self-report architecture from PBI 003 is preserved, just correctly wired.

## 9. Assumptions

- Reusing each file's own pre-existing "mandatory before closing" gate is
  lower-risk than inventing a new, generic `## Completion Signal` section
  disconnected from that file's established structure — even though this
  means the fix pattern differs slightly per file (a bullet in a gate list,
  a note before a timing template, a new numbered "Passo").
- `--duration-ms`/`--tokens-in`/`--tokens-out` remain LLM-estimated,
  consistent with the existing tool design; no new precise instrumentation
  was added.

## Success Criteria

| Criterion | Measure |
|---|---|
| Root cause identified with evidence | Confirmed via direct file reads + filesystem search: zero prior observability output anywhere |
| Fix mechanically verified | All 5 files show exactly one `pipeline_observer.py ... track` call inside their real completion-gate block, not past a `---`/`##` boundary |
| Fix functionally verified | Live dry-run of `init`→`track`→`finalize --auto-report` produces per-agent folder + 4-sheet Excel |
| Incidental regressions found while editing are fixed | `{project_name}` restored, stray fence removed, duplicate `5.8`/`5.9` numbering fixed |
| Remaining gap stated honestly | 92 leaf files explicitly still broken, not silently claimed fixed |
