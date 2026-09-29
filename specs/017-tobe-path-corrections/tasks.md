# Tasks: Correction of Dead Input-Path References in the TO-BE Pipeline

**Spec**: `specs/017-tobe-path-corrections/spec.md`
**Plan**: `specs/017-tobe-path-corrections/plan.md`

## Category 1 — AS-IS-Artifact Consumer Fixes

- [x] 1.1 `database-policy-tobe.md` — annotate Input Contract row 7 (`outputs/asis/db/triggers-map.md`)
      as a permanent structural gap (no AS-IS producer exists under any name)
- [x] 1.2 `orchestrator-tobe.md` — mirror the same annotation in the Fase 1.4 input table
- [x] 1.3 `orchestrator-tobe.md` — Fase 7.8 gate checklist: `outputs/asis/docs/test-plan.md` →
      `outputs/asis/qa/test-plan.md`
- [x] 1.4 `orchestrator-tobe.md` — Fase 7.8 Input Contract table: same path fix, second occurrence
- [x] 1.5 `designer-system-tobe.md` — Input Sources row 5: `outputs/asis/docs/screen-flow.md` →
      `outputs/asis/docs/screen-flow.mmd`

## Category 2 — TO-BE-Internal Dead-Path Fixes

- [x] 2.1 `test-plan-tobe.md` — all 15 occurrences of `architecture-technical.md` →
      `tech-framework-document.md` (Input Contract table, blocking-rule prose, Step 1 read table,
      6 scattered BDD/fallback mentions)
- [x] 2.2 `user-journeys-tobe.md` — `outputs/tobe/architecture-design.md` →
      `outputs/tobe/docs/architecture-blueprint.md`
- [x] 2.3 `azure-infra-estimator-tobe.md` — Read Priority entry (2): `architecture-design-tobe.md`
      → `outputs/tobe/docs/architecture-blueprint.md`
- [x] 2.4 `azure-infra-estimator-tobe.md` — `estimation_profile` decision table: same rename
- [x] 2.5 `azure-infra-estimator-tobe.md` — READ ATTEMPT LOG format string: same rename
- [x] 2.6 `azure-infra-estimator-tobe.md` — Scenario 2 (BDD): same rename, 2 occurrences
- [x] 2.7 `azure-infra-estimator-tobe.md` — Scenario 3 (BDD): same rename
- [x] 2.8 `developer-guide-tobe.md` — Input Contract row: `outputs/tobe/docs/test-plan-tobe.md` →
      `outputs/tobe/test-plan.md`
- [x] 2.9 `developer-guide-tobe.md` — Seção 7 template prose: same rename, 2 occurrences

## Category 3 — Residual Verification

- [x] 3.1 Grep `outputs/tobe/migration-plan.md` (old path, no `docs/`) across all of
      `tobe-architecture/agents/*.md` — confirmed 0 residual occurrences; `specs/016`'s fix is
      complete, no action needed here

## Category 4 — Version Bumps (PATCH, all 7 files)

- [x] 4.1 `orchestrator-tobe.md` — `2.4.0` → `2.4.1`, `date` → `2026-07-13`
- [x] 4.2 `database-policy-tobe.md` — `1.0.0` → `1.0.1`
- [x] 4.3 `designer-system-tobe.md` — `1.0.0` → `1.0.1`
- [x] 4.4 `test-plan-tobe.md` — `3.2.0` → `3.2.1` (kept pre-existing unquoted scalar format)
- [x] 4.5 `user-journeys-tobe.md` — `1.0.0` → `1.0.1`
- [x] 4.6 `azure-infra-estimator-tobe.md` — `1.1.0` → `1.1.1`
- [x] 4.7 `developer-guide-tobe.md` — `1.1.0` → `1.1.1` (frontmatter only; output-template
      `version:` at line 249 correctly left untouched)

## Category 5 — Documentation Sync

- [x] 5.1 `docs/tobe-architecture-io-map.md` §4.6 — Status note: architecture-technical.md fully
      renamed to tech-framework-document.md
- [x] 5.2 `docs/tobe-architecture-io-map.md` §4.7 — Status note: screen-flow.md extension fixed
- [x] 5.3 `docs/tobe-architecture-io-map.md` §4.8 — Status note: second half (architecture-design-tobe.md)
      now fixed
- [x] 5.4 `docs/tobe-architecture-io-map.md` §4.9 — Status note: dead-path half fixed, BC-map-source
      ambiguity half explicitly left open
- [x] 5.5 `docs/tobe-architecture-io-map.md` §4.11 — Status note: test-plan-tobe.md path fixed
- [x] 5.6 `docs/tobe-architecture-io-map.md` — new §4.16 (triggers-map.md, permanent gap)
- [x] 5.7 `docs/tobe-architecture-io-map.md` — new §4.17 (asis/docs/test-plan.md → qa/, fixed)
- [x] 5.8 `docs/tobe-input-artifacts-existence-check.md` — new closing §4, cross-referencing this
      spec and explaining the 85→7 scope reduction
- [x] 5.9 `CHANGELOG.md` — new dated entry (2026-07-13), same format as the `specs/016` entry

## Category 6 — Speckit Documentation

- [x] 6.1 Write `specs/017-tobe-path-corrections/spec.md`
- [x] 6.2 Write `specs/017-tobe-path-corrections/plan.md`
- [x] 6.3 Write `specs/017-tobe-path-corrections/tasks.md` (this file)

## Category 7 — Verification

- [x] 7.1 `grep -c "lacuna permanente\|lacuna estrutural\|nenhum agente do pipeline AS-IS produz"` near
      the triggers-map.md reference → `database-policy-tobe.md`: 2, `orchestrator-tobe.md`: 1
- [x] 7.2 `grep -c "outputs/asis/docs/screen-flow.md"` in `designer-system-tobe.md` → 0
- [x] 7.3 `grep -rc "outputs/asis/docs/test-plan.md"` in `tobe-architecture/agents/` → 0
- [x] 7.4 `grep -c "architecture-technical.md" test-plan-tobe.md` → 0
- [x] 7.5 `grep -rn "outputs/tobe/architecture-design.md"` (exact) → 0
- [x] 7.6 `grep -rn "outputs/tobe/architecture-design-tobe.md"` → 0
- [x] 7.7 `grep -c "outputs/tobe/docs/test-plan-tobe.md"` → 0
- [x] 7.8 `grep -rc "outputs/tobe/migration-plan.md"` (old path) across `tobe-architecture/agents/*.md` → 0
- [x] 7.9 All 7 frontmatter versions confirmed matching spec.md §1 (2.4.1 / 1.0.1 / 1.0.1 / 3.2.1 /
      1.0.1 / 1.1.1 / 1.1.1); `developer-guide-tobe.md`'s second `version: "1.0.0"` confirmed to be
      the output-artifact template, correctly left untouched
- [x] 7.10 Manual diff review: no `## Output Contract`/`## Output Files` field removed in any of the 7 files

## Completion Checklist

- [x] All Category 1-6 tasks checked off with corresponding file changes verified present
- [x] Category 7 verification commands run and results recorded — all pass
- [x] `git status` reviewed — exactly the 7 agent files + 3 doc files + this spec folder touched,
      nothing unexpected
- [x] `CHANGELOG.md` entry present and correctly formatted
