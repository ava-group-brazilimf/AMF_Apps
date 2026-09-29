# Agent Implementation Plan: Solution Delphi Test Coverage Artifact Mapping

**Spec**: `specs/009-solution-delphi-test-coverage-artifact/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (1 agent file + 1 shared risk-flags doc + 1 shared output-paths doc + 1 cross-module doc + 2 observability tool catalogs) |
| **Primary Requirement** | Map `09_test_coverage.json` as a 9th deterministic AST input; make Step 0's tool invocation explicitly conditional on file absence; wire the new artifact into a new Migration Readiness risk flag |
| **Technical Approach** | Additive documentation/prose changes mirroring the exact pattern already established for artifacts 01-08 in specs/007 (Input Contract row, Step 3 derived-object subsection, degraded-mode honesty) |
| **Implementation Status** | Complete. Structural verification done (fence balance, mention counts, cross-file version sync). |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded.
- [x] **Article II** — frontmatter unchanged except version bump.
- [x] **Article V** — pt-BR body content preserved.
- [x] **Article VI** — BDD scenarios cover the existence-check optimization, mandatory-invoke path, new risk raised, and honest degraded-mode omission.
- [x] **Article X (SemVer)** — MINOR bump (`2.0.0`→`2.1.0`), correctly reflecting an additive change (no existing Output Contract field removed).

## Technical Context

Pure Markdown/prose edits to one agent file plus 4 dependent references
(2 shared docs, 1 cross-module doc, 2 observability tool catalogs). No code
changes to the external analyzer or the wrapper script — both already
correctly produce/expect the 9th artifact (confirmed by direct read before
any edits, per research.md §1).

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
Confirmed the wrapper script (`run_delphi_ast_analysis.py`) already expected
`09_test_coverage.json` in its success gate — no wrapper change needed.
Found and read the external analyzer's own design doc for this exact
artifact, confirming its schema and the intended-consumer analysis
(`ava-asis-test-qa`, explicitly deferred). Verified the schema against a
real, already-executed sample rather than assuming it.

### Phase 1 — Input Contract + Step 0 ✅ CONCLUÍDO
Added `09_test_coverage.json` as the 9th row in `## Input Contract`; fixed
the pre-existing "9 artefatos" text inconsistency (Step 0 already said "9"
while its own table only had 8 rows). Reframed Step 0 to explicitly check
for all 9 files' existence before deciding whether to invoke the tool
(skip if present, invoke if any missing) — directly implementing the
user's "caso não exista... deve invocar a tool" requirement.

### Phase 2 — `TestCoverageProfile` + New Risk ✅ CONCLUÍDO
Added a new Step 3 subsection mirroring the `ClassRegistry[]`/
`BusinessRuleRegistry[]` pattern: primary source from
`09_test_coverage.json.payload.counts`/`test_findings[]`/
`auxiliary_indicators[]`; new risk `NO_AUTOMATED_TEST_COVERAGE` raised when
no tests/test-methods detected; explicit, honest degraded-mode handling
(no Grep fallback attempted — limitation stated, not glossed over).

### Phase 3 — Shared Docs Reconciliation ✅ CONCLUÍDO
`delphi-patterns.md`'s Migration Readiness flags list updated with the new
flag + rationale. `output-paths.md`'s Delphi note updated (8→9 artifacts,
version bump). `docs/asis-diagnostic-io-map.md` updated (9-file input list,
enriched-not-new-file note on `architecture-blueprint.md`). Both
observability tool catalogs (`pipeline_observer.py`,
`generate_observability_report.py`) synced to version `2.1.0`.

### Phase 4 — Verification ✅ CONCLUÍDO
See `quickstart.md`. Structural checks (fence balance, mention counts,
version consistency across all touched files) + `py_compile` on the two
touched Python files. No live pipeline run possible in this session (prose
instruction file).

## Complexity Tracking

| Item | Status |
|---|---|
| No Grep fallback for `TestCoverageProfile` | Deliberate, honestly-documented limitation — the external tool's AST+regex+glob detection logic is not trivially replicable, and a false negative (falsely reporting "no tests") would be worse than an explicit "unavailable" state |
| Overlap risk with `ava-asis-test-qa` | Explicitly identified (in the external tool's own design doc) and explicitly deferred — this PBI touches only `solution-delphi.md`, not `test-qa-asis.md`, avoiding the race-condition risk flagged in that doc |
| Existence-check-before-invoke | Verified against the wrapper's own all-or-nothing success gate — no realistic partial-file state exists in practice, but the check is written defensively per-file anyway |

## Test Strategy

| Test | Command | Result |
|---|---|---|
| Input Contract has 9th row | `grep -c "09_test_coverage.json" solution-delphi.md` | 5 matches (Input Contract row, Step 0 ×2, Step 3 subsection, degraded-mode note) |
| New risk flag present | `grep -c "NO_AUTOMATED_TEST_COVERAGE" solution-delphi.md` | 4 matches (Input Contract, Step 3 ×2, Guardrails cross-reference) |
| Fence balance | Per-file `` ``` `` parity check | 12 fences, balanced |
| Shared flags list updated | `grep NO_AUTOMATED_TEST_COVERAGE delphi-patterns.md` | Present with rationale |
| Version consistency | `grep 2.1.0` across `solution-delphi.md`, `pipeline_observer.py`, `generate_observability_report.py` | All consistent |
| Tools compile | `python -m py_compile pipeline_observer.py generate_observability_report.py` | OK |
