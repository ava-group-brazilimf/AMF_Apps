# Agent Development Tasks: Solution Delphi Test Coverage Artifact Mapping

**Plan**: `specs/009-solution-delphi-test-coverage-artifact/plan.md`
**Status**: Implementation and verification complete.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm frontmatter version bump
  ```bash
  grep -n '^version:' src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md
  ```
  **Result**: `"2.1.0"`.

## Category 2 — Implementation

- [x] **2.1** Add `09_test_coverage.json` row to `## Input Contract` — DONE
- [x] **2.2** Fix "8 acima" → "9 acima" text inconsistency (2 occurrences) — DONE
- [x] **2.3** Reframe Step 0 with explicit existence-check-before-invoke logic — DONE
- [x] **2.4** Note the tool produces all 9 files in one sequenced call — DONE
- [x] **2.5** Add `TestCoverageProfile` subsection to Step 3 — DONE
- [x] **2.6** Wire new risk `NO_AUTOMATED_TEST_COVERAGE` (raised when `test_units==0 AND test_methods==0`) — DONE
- [x] **2.7** Add honest degraded-mode handling (no Grep fallback, explicit omission) — DONE
- [x] **2.8** Sync `--version` literal in FASE OBRIGATÓRIA to `2.1.0` — DONE

## Category 3 — Schema Updates — SKIP

No new JSON schema authored by this repo; `09_test_coverage.json`'s schema
is owned and already implemented by the external analyzer tool.

## Category 4 — Module Registration — SKIP

No `module.yaml` change; `change type` is `modify-existing`, same agent ID.

## Category 5 — Quality Gate Checklists

- [x] **5.1** `delphi-patterns.md` Migration Readiness flags list updated — DONE
- [x] **5.2** `output-paths.md` Delphi note updated (8→9 artifacts, v2.1.0) — DONE
- [x] **5.3** `docs/asis-diagnostic-io-map.md` updated (9-file input list, enriched-not-new-file note) — DONE
- [x] **5.4** `pipeline_observer.py` + `generate_observability_report.py` catalog versions synced to `2.1.0` — DONE
- [x] **5.5** Fence balance confirmed — 12 fences, balanced
- [x] **5.6** Both touched Python files compile — OK

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — files already exist → tool invocation skipped — PASS (Step 0 text confirmed)
- [x] **6.2** CA02 — files missing → tool invoked mandatorily, then LLM interprets — PASS
- [x] **6.3** CA03 — new risk correctly wired into Migration Readiness — PASS
- [x] **6.4** CA04 — degraded mode does not assume "no tests" without the artifact — PASS

## Category 7 — Documentation

- [x] **7.1** `output-paths.md`, `docs/asis-diagnostic-io-map.md` — DONE
- [x] **7.2** This spec-kit documentation (spec/plan/research/data-model/quickstart/tasks/checklist) — DONE

## Completion Checklist

- [x] `solution-delphi.md` structurally verified sound (fence balance, mention counts)
- [x] `09_test_coverage.json` fully wired: Input Contract, Step 0 existence-check, Step 3 `TestCoverageProfile`, new risk flag
- [x] Degraded-mode behavior stated honestly (no Grep fallback, explicit omission)
- [x] Dependent docs (`delphi-patterns.md`, `output-paths.md`, `asis-diagnostic-io-map.md`, both observability tool catalogs) reconciled
- [x] `ava-asis-test-qa` explicitly left out of scope, not silently duplicated/raced
