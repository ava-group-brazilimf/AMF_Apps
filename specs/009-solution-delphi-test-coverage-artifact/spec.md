# Agent Specification: Solution Delphi — Test Coverage Artifact Mapping

**Feature Branch**: `009-solution-delphi-test-coverage-artifact`
**Created**: 2026-07-08
**Status**: Implemented
**Change Type**: modify-existing (`ava-asis-solution-delphi`, MINOR — new input artifact + new risk flag, no existing Output Contract field removed/renamed)
**Input**: "No agente de Solution-delphi: Mapeie um novo arquivo gerado pela analise AST — o arquivo de cobertura de teste — 09_test_coverage.json. O Agente caso não exista os arquivos na pasta deve obrigatoriamente invocar a tool e gerar os arquivos na sequência, passar para interpretação do LLM para gerar os demais artefatos."

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-asis-solution-delphi` |
| **Version** | `2.0.0` → `2.1.0` (MINOR — new input artifact + new risk flag; no existing Output Contract field removed or renamed) |
| **Phase** | F1 |
| **Module** | `asis-diagnostic` |
| **File** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md` |

## 2. Problem Statement

The external `ava-fabric-delphi-analyzer` tool now produces a **9th** deterministic
JSON artifact, `09_test_coverage.json` — confirmed already implemented in the
external tool (design doc `docs/plan_novo_aterfato_test_coverage-json.md` in
that repo) and already expected by this repo's own wrapper script
(`run_delphi_ast_analysis.py`'s `expected` list already included
`"test_coverage"` before this PBI started). However, `solution-delphi.md`'s
own `## Input Contract` table still only listed 8 artifacts — the file was
never wired to consume the 9th, and its own Step 0 text ("Carregar os 9
artefatos") already referenced "9" inconsistently with its own 8-row table,
confirming the gap.

The user also asked to make explicit that the agent must **check for the
files' existence before invoking the tool** — if the 9 JSON files are
already present (e.g., on a resumed/re-entrant run), skip re-invocation;
if any are missing, invoke the tool (mandatory), let it produce the files
in sequence, and only then proceed to LLM interpretation of the artifacts.

## 3. Decision

1. **`09_test_coverage.json` added to `## Input Contract`** as the 9th
   primary artifact, with `_volatile`/`payload` schema documented in
   `data-model.md`.
2. **New `TestCoverageProfile` object**, built in Step 3 (alongside the
   existing `ClassRegistry[]`/`BusinessRuleRegistry[]` pattern), sourced
   directly from `09_test_coverage.json.payload.counts` +
   `payload.test_findings[]` + `payload.auxiliary_indicators[]` when Step 0
   succeeds.
3. **New risk flag `NO_AUTOMATED_TEST_COVERAGE`**: raised when
   `payload.counts.test_units == 0 AND payload.counts.test_methods == 0`
   (no DUnit/DUnitX tests and no auxiliary test indicators detected). Added
   to the shared `delphi-patterns.md` "Flags de Risco (Migration Readiness)"
   list — this risk reduces the Migration Readiness Score, consistent with
   every other flag in that list. **No new output file** — this enriches
   `architecture-blueprint.md`'s existing risk narrative.
4. **Degraded fallback is explicit and honest**: unlike other AST-covered
   analyses, `TestCoverageProfile` has **no Grep-based fallback** when Step 0
   fails — the external tool's own detection combines AST (attributes,
   visibility, class inheritance) with regex and auxiliary-file scanning in
   ways this agent is not scoped to replicate. On failure, the agent
   registers `TestCoverageProfile: indisponível` and explicitly omits the
   `NO_AUTOMATED_TEST_COVERAGE` risk rather than assuming absence of tests
   without the deterministic artifact.
5. **Step 0 reframed with an explicit existence check**: before invoking
   `run_delphi_ast_analysis.py`, the agent now checks whether all 9 JSON
   files already exist in `delphi-ast-raw/extraction/`. If so, the
   invocation is skipped (avoids redundant re-extraction on resumed runs).
   If any file is missing, the tool is invoked (mandatory, same as before)
   — it produces all 9 artifacts in a single call, in sequence
   (`01_business_rules` → `09_test_coverage`), and only then does the LLM
   proceed to interpret them across Steps 1-14.
6. **Scope boundary**: the external tool's design doc explicitly identifies
   `ava-asis-test-qa` (a different agent) as the intended primary consumer
   of `09_test_coverage.json` for full test-documentation purposes, and
   explicitly defers that integration to a future round. This PBI covers
   **only** `solution-delphi.md`'s use of the artifact as one additional
   Migration Readiness signal — it does not touch `test-qa-asis.md`.

## 4. Functional Changes by Component

| Section | Change |
|---|---|
| Frontmatter | `version: "2.0.0"` → `"2.1.0"` |
| `## Input Contract` | Added `09_test_coverage.json` row; "8 acima" → "9 acima" (2 occurrences) |
| Step 0 | Added explicit check-existence-before-invoke logic; noted the tool produces all 9 files in one sequenced call; added `TestCoverageProfile` to the degraded-mode explicit-omission list |
| Step 3 | New `TestCoverageProfile` subsection (mirrors `ClassRegistry`/`BusinessRuleRegistry` pattern) |
| FASE OBRIGATÓRIA | `--version` literal synced to `2.1.0` |
| `shared/delphi-patterns.md` | Added `NO_AUTOMATED_TEST_COVERAGE` to the Migration Readiness flags list, with source/rationale note |
| `shared/output-paths.md` | Delphi note updated: "8 deterministic" → "9 deterministic", version references bumped, new artifact mentioned |
| `docs/asis-diagnostic-io-map.md` | Input list extended to 9 files; Outputs bullet notes `architecture-blueprint.md` is enriched (not a new file) |
| `src/shared/tools/pipeline_observer.py`, `generate_observability_report.py` | `AGENT_CATALOG` version for `ava-asis-solution-delphi` synced to `2.1.0` |

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Files already exist: tool invocation skipped (CA01)

**Given** all 9 JSON files already exist in
`outputs/asis/delphi-ast-raw/extraction/` (e.g., a resumed run), **When**
the agent reaches Step 0, **Then** it does not re-invoke
`run_delphi_ast_analysis.py`, proceeds directly to "SE sucesso", and uses
the 9 artifacts as primary source for Steps 1, 3, and 4.

### Scenario 2 — Files missing: tool invoked mandatorily, then LLM interprets (CA02)

**Given** any of the 9 JSON files is missing, **When** the agent reaches
Step 0, **Then** it invokes `run_delphi_ast_analysis.py` (mandatory, not
optional), which produces all 9 artifacts in a single sequenced call; only
after this completes (or fails) does the LLM proceed to Steps 1-14.

### Scenario 3 — Test coverage risk correctly raised (CA03)

**Given** Step 0 succeeded and `09_test_coverage.json.payload.counts` shows
`test_units: 0, test_methods: 0`, **When** Step 3 builds
`TestCoverageProfile`, **Then** the agent registers risk
`NO_AUTOMATED_TEST_COVERAGE`, which reduces the Migration Readiness Score
reported in `architecture-blueprint.md`.

### Scenario 4 — AST unavailable: no false-negative risk (CA04)

**Given** Step 0 fails or is unavailable, **When** the agent proceeds in
degraded mode, **Then** it does **not** raise `NO_AUTOMATED_TEST_COVERAGE`
(since it cannot verify test presence without the artifact) and explicitly
records `TestCoverageProfile: indisponível` in the report.

## 6. Quality Gate Requirements

- [x] Agent ID unchanged, frontmatter contains only the 4 allowed fields (Article II)
- [x] Version bump is MINOR, matching an additive Input Contract + new risk flag change, no existing Output Contract field removed (Article X)
- [x] BDD scenarios cover the existence-check optimization, the mandatory-invoke path, the new risk being raised, and the honest degraded-mode omission (Article VI)
- [x] No technology versions hardcoded (Article I)
- [x] No `[NEEDS CLARIFICATION]` markers remain

## 7. Dependencies

- `src/modules/ava-fabric-agents/asis-diagnostic/utils/run_delphi_ast_analysis.py` (already produced/expected `09_test_coverage.json` in its `expected` list before this PBI — confirmed by direct read, no change needed)
- The external `ava-fabric-delphi-analyzer` tool (already implements `09_test_coverage.json` generation — confirmed via that repo's own design doc and real sample output)
- `shared/delphi-patterns.md` (Migration Readiness flags list)

## 8. Exclusions

- `ava-asis-test-qa` (`test-qa-asis.md`) — explicitly identified by the external tool's own design doc as the intended primary consumer of `09_test_coverage.json` for full test-documentation purposes; explicitly deferred to a future round, not touched by this PBI.
- No changes to the external analyzer tool or the wrapper script — both already correctly handle the 9th artifact.
- `solution-vb.md` and other legacy-technology solution agents — unaffected, no AST tool integration for those technologies.
- No live pipeline execution possible in this session (prose instruction file) — verification is structural/documentary only.

## 9. Assumptions

- The 9-file atomicity of `run_delphi_ast_analysis.py` (one invocation produces all 9 files or none, per its own `expected`-list gate) means the "check existence, invoke if any missing" logic only needs to check for the presence of all 9 — a partial set (e.g., 8 present, 1 missing) is not a realistic steady state given the wrapper's own all-or-nothing verification, but the check is still phrased per-file for clarity and defensiveness.
- `TestCoverageProfile`'s degraded-mode fallback is intentionally **not** implemented via Grep, unlike other AST-covered analyses — stated as a real, accepted limitation (the external tool's detection logic is not trivially replicable via simple pattern matching within this agent's scope), not silently glossed over.

## Success Criteria

| Criterion | Measure |
|---|---|
| `09_test_coverage.json` mapped | `## Input Contract` table has a 9th row; Step 3 has a `TestCoverageProfile` subsection |
| Existence-check-before-invoke present | Step 0 explicitly describes checking for all 9 files before deciding whether to invoke the tool |
| New risk wired into Migration Readiness | `NO_AUTOMATED_TEST_COVERAGE` present in both `solution-delphi.md` (Step 3) and `delphi-patterns.md`'s flags list |
| Degraded mode is honest | Step 0's failure branch explicitly states `TestCoverageProfile` has no Grep fallback and the risk is omitted, not assumed |
| No output-path/version drift | `output-paths.md`, `docs/asis-diagnostic-io-map.md`, and both observability tool catalogs reference `2.1.0`/9 artifacts consistently |
