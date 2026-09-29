# Agent Implementation Plan: Correction of Dead Input-Path References in the TO-BE Pipeline

**Spec**: `specs/017-tobe-path-corrections/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (7 agent files, PATCH each) + 3 doc-only syncs (`docs/tobe-architecture-io-map.md`, `docs/tobe-input-artifacts-existence-check.md`, `CHANGELOG.md`) |
| **Primary Requirement** | Correct the small, confirmed subset (7 of 163 audited references) of TO-BE input-file paths that resolve to no current producer under any name, or use a wrong extension/directory segment — without reintroducing the stale path conventions found in the reference project used for the original audit |
| **Technical Approach** | String-level path/extension corrections, each verified against the actual producing agent's current `## Output Contract` before being applied — mirrors the verification discipline already used in `specs/016`'s bundled path fixes, extended to close the remaining io-map §4 items it deliberately deferred |
| **Implementation Status** | Complete. Structural verification via grep (dead-path absence, corrected-path presence) — no code/runtime changes, all edits are prose/Markdown in agent instruction files. |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded.
- [x] **Article II** — frontmatter unchanged except `version` (+ `date` for `orchestrator-tobe.md`).
- [x] **Article V** — pt-BR body content preserved throughout.
- [x] **Article VI** — BDD scenarios cover resolvable-fix, permanent-gap, regression-guard, and negative (already-correct-refs-untouched) paths.
- [x] **Article X (SemVer)** — PATCH for all 7 files (pure bugfix, no Input/Output Contract shape change).
- [x] No `[NEEDS CLARIFICATION]` markers — ground-truth methodology (producer Output Contract vs.
      project file layout) and AS-IS-reference scope inclusion both confirmed via `AskUserQuestion`
      before implementation began.

## Technical Context

Pure Markdown/prose edits to 7 agent-instruction files. No new dependencies, no schema changes, no
code changes. Every fix was verified against the actual current `## Output Contract` of the real
producing agent (read directly, not inferred) before being applied — the investigation's central
finding was that the project used for the original existence-check audit
(`Meu-ERP-008-AST-LLM-Master-Orchestrator`) reflects a path convention that predates a
consolidation already present in the current agent specs, so it could not be used as ground truth
directly.

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
3 parallel Explore agents: (1) built a canonical AS-IS producer map by cross-referencing every
`outputs/asis/**` path in the existence-check audit against `docs/asis-diagnostic-io-map.md` and
each AS-IS agent's own Output Contract — found only 3 genuine AS-IS-side defects out of 25 audited
paths; (2) built the equivalent canonical TO-BE producer map — found the existence-check project's
layout was largely stale/superseded, confirmed only a handful of genuine TO-BE-internal defects,
mostly already known from `docs/tobe-architecture-io-map.md` §4; (3) compared project 008 against
the newly-opened `Meu-ERP-009-AST-LLM-Fullpipeline` — confirmed 009 is an empty, never-executed
scaffold and cannot serve as an alternative reference. A 4th agent (Plan) consolidated the 7
confirmed defects into an exact file/line/fix list, confirmed the `specs/016` migration-plan.md
residual check was clean, and proposed version bumps.

### Phase 1 — AS-IS-artifact consumer fixes ✅ CONCLUÍDO
3 defects, 4 files: `database-policy-tobe.md` (triggers-map.md → annotated permanent gap, Input
Contract row 7), `orchestrator-tobe.md` (mirrored triggers-map.md annotation in its Fase 1.4
table + `outputs/asis/docs/test-plan.md` → `outputs/asis/qa/test-plan.md` in the Fase 7.8 gate
checklist and Input Contract table, 2 sites), `designer-system-tobe.md` (`screen-flow.md` →
`screen-flow.mmd`). No `asis-diagnostic` agent touched — consumer-side only, per confirmed scope.

### Phase 2 — TO-BE-internal dead-path fixes ✅ CONCLUÍDO
4 defects, 4 files: `test-plan-tobe.md` (`architecture-technical.md` → `tech-framework-document.md`,
15 occurrences across the Input Contract table, blocking-rule prose, Step 1 read table, and 6
scattered BDD/fallback-text mentions), `user-journeys-tobe.md` (`architecture-design.md` →
`architecture-blueprint.md`, 1 occurrence), `azure-infra-estimator-tobe.md`
(`architecture-design-tobe.md` → `architecture-blueprint.md`, 6 occurrences: Read Priority list,
`estimation_profile` decision table, READ ATTEMPT LOG format string, 2 BDD scenarios), and
`developer-guide-tobe.md` (`outputs/tobe/docs/test-plan-tobe.md` → `outputs/tobe/test-plan.md`,
Input Contract row + 2 prose mentions in the Seção 7 template).

### Phase 3 — Residual verification ✅ CONCLUÍDO
Re-grepped `outputs/tobe/migration-plan.md` (the old path without `docs/`, already fixed in
`specs/016` for `orchestrator-tobe.md` and `risk-mitigation-tobe.md`) across every file in
`tobe-architecture/agents/`: zero residual occurrences. No further action needed; recorded as
evidence in `tasks.md`.

### Phase 4 — Version bumps ✅ CONCLUÍDO
PATCH bump on all 7 touched files: `orchestrator-tobe.md` (2.4.0→2.4.1, `date` also bumped to
2026-07-13), `database-policy-tobe.md` (1.0.0→1.0.1), `designer-system-tobe.md` (1.0.0→1.0.1),
`test-plan-tobe.md` (3.2.0→3.2.1, kept the pre-existing unquoted YAML scalar format rather than
introducing a new inconsistency), `user-journeys-tobe.md` (1.0.0→1.0.1),
`azure-infra-estimator-tobe.md` (1.1.0→1.1.1), `developer-guide-tobe.md` (1.1.0→1.1.1 — the agent
frontmatter only; a second, unrelated `version: "1.0.0"` at line 249 is part of the *output
artifact's* own frontmatter template, not the agent's version, and was correctly left untouched).

### Phase 5 — Documentation sync ✅ CONCLUÍDO
`docs/tobe-architecture-io-map.md`: Status notes appended to §4.6, §4.7, §4.8, §4.9, §4.11
recording exactly what was fixed and what (if anything) remains open; two new subsections §4.16
and §4.17 added documenting the 2 AS-IS-reference defects (triggers-map.md, asis/qa/test-plan.md)
that weren't previously catalogued anywhere. `docs/tobe-input-artifacts-existence-check.md`: new
closing §4 explaining the 85→7 scope reduction and cross-referencing this spec. `CHANGELOG.md`:
new dated entry at the top, same format as the `specs/016` entry.

### Phase 6 — Speckit documentation ✅ CONCLUÍDO
This spec/plan/tasks trio.

### Phase 7 — Verification ✅ CONCLUÍDO
See Test Strategy below. Grep-based structural checks only — no live pipeline run possible in this
session (prose instruction files consumed by an LLM at dispatch time, not executable code), same
limitation accepted in every prior spec in this repository that touches agent `.md` files.

## Complexity Tracking

| Item | Status |
|---|---|
| `test-plan-tobe.md`'s 15 scattered occurrences of the dead reference, spanning a table row, blocking-rule prose, a Step-1 read table, and 6 more mentions in fallback/BDD text | Handled with a single `replace_all` after reading enough surrounding context (20+ lines across the file) to confirm no false-positive substring matches (e.g. `architecture-technical-tobe.md`, the sibling agent's own filename, does not contain `architecture-technical.md` as a substring since `-tobe.md` intervenes) |
| `triggers-map.md` has no equivalent artifact to redirect to (unlike the other 6 defects) | Resolved by explicit user-confirmed decision: annotate as a permanent structural gap rather than force a redirect to a non-equivalent file (`db-type.json`'s trigger count field, or `business-logic-in-db.md`, are supersets, not 1:1 substitutes) |
| Distinguishing the agent's own frontmatter `version:` from an unrelated `version:` field inside a documented output-artifact template (`developer-guide-tobe.md` line 249) | Read surrounding context before editing; only the frontmatter occurrence (line 17) was bumped |
| Avoiding over-correction: most of the 85 "NÃO" existence-check rows are not bugs | Every one of the 7 fixes applied here was individually verified against the real producing agent's Output Contract before being touched — no fix was applied based on the existence-check table's SIM/NÃO column alone |

## Test Strategy

| Test | Command | Result |
|---|---|---|
| Triggers-map annotated in both files | Manual read confirms permanent-gap wording present in `database-policy-tobe.md` and `orchestrator-tobe.md` | Present |
| Screen-flow extension fixed | `grep -c "outputs/asis/docs/screen-flow.md"` in `designer-system-tobe.md` | 0 (`.mmd` present instead) |
| AS-IS test-plan segment fixed | `grep -rc "outputs/asis/docs/test-plan.md"` in `tobe-architecture/agents/` | 0 |
| Architecture-technical fully renamed | `grep -c "architecture-technical.md" test-plan-tobe.md` | 0 |
| Architecture-design dead refs fixed | `grep -rn "outputs/tobe/architecture-design.md"` (exact) / `grep -rn "outputs/tobe/architecture-design-tobe.md"` | 0 / 0 |
| Developer-guide test-plan path fixed | `grep -c "outputs/tobe/docs/test-plan-tobe.md"` | 0 |
| Migration-plan residual check | `grep -rc "outputs/tobe/migration-plan.md"` (old path) across `tobe-architecture/agents/*.md` | 0 (already clean pre-PBI) |
| Version consistency | Frontmatter `version` per file matches spec.md §1 table | All 7 matched |
| Fence balance | Per-file markdown code-fence parity check on all 7 touched files | All balanced |
| No Output Contract field removed | Manual diff review of each file's Output Contract/Output Files section | Unchanged everywhere |

## Rollout Note

This PBI intentionally leaves ~78 of the original 85 "NÃO" existence-check rows untouched — they
are not bugs. Anyone re-running the existence-check audit against a *fresh* pipeline execution
(not project 008) should expect most of those 78 to resolve SIM once a full run reaches the
relevant phase; a persistent NÃO on one of those paths after a genuinely complete run would be a
new finding, not a regression from this PBI.
