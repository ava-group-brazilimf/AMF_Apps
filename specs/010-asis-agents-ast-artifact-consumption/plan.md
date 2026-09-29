# Agent Implementation Plan: Extend AST-Artifact Consumption + Fix compressed/ Path

**Spec**: `specs/010-asis-agents-ast-artifact-consumption/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (6 agent files + 2 shared docs + 2 observability tool catalogs) |
| **Primary Requirement** | Correct the AST artifact path (`extraction/` → `compressed/`); extend AST-artifact consumption from `solution-delphi.md` alone to 5 more `orchestrator-asis.md`-dispatched agents wherever they read Delphi source directly |
| **Technical Approach** | Additive documentation/prose changes mirroring the exact Input-Contract/existence-check/fallback pattern established in `specs/007`; no code changes to the external analyzer or wrapper script |
| **Implementation Status** | Complete. Structural verification done (fence balance, `Fallback` heading presence, version consistency across all 6 files + 2 tool catalogs). |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded.
- [x] **Article II** — frontmatter unchanged except version bumps.
- [x] **Article V** — pt-BR body content preserved throughout.
- [x] **Article VI** — BDD scenarios cover resumed-run success, race-condition fallback, non-Delphi no-op, and the path fix.
- [x] **Article X (SemVer)** — PATCH for `solution-delphi.md` (pure bugfix), MINOR for the other 5 (additive, nothing removed).
- [x] No `[NEEDS CLARIFICATION]` markers.

## Technical Context

Pure Markdown/prose edits to 6 agent files + 2 shared docs, plus 2 Python
dict-literal edits (observability tool catalogs, compile-checked). No new
dependencies. No changes to `run_delphi_ast_analysis.py` or the external
analyzer — both already correctly produce all 9 artifacts in both
`extraction/` and `compressed/` variants.

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
3 parallel Explore agents read every `orchestrator-asis.md`-dispatched
agent in full. Confirmed via direct diff that `compressed/` is genuinely
token-optimized (not a no-op mirror) and that `solution-delphi.md` had the
wrong directory everywhere. Confirmed via direct read of
`orchestrator-asis.md`'s `dispatch_schedule` that Phase A dispatches 6
source-reading agents in parallel — a real race-condition risk for the new
existence-check logic, honestly documented rather than fixed (fixing it
would require touching the orchestrator, explicitly out of scope).

### Phase 1 — Scope Correction ✅ CONCLUÍDO
Initial plan excluded `documentation-asis.md`; user explicitly rejected
this via `ExitPlanMode` rejection reason. Plan revised to include VC/FT/RT/RF
skills before implementation began (see research.md §3).

### Phase 2 — Path Correction (solution-delphi.md) ✅ CONCLUÍDO
17 occurrences of `delphi-ast-raw/extraction/` → `delphi-ast-raw/compressed/`
via a single scripted find-replace (PowerShell regex substitution, verified
count matched before/after); same correction applied to `shared/output-paths.md`
and `docs/asis-diagnostic-io-map.md`. Version bumped PATCH (`2.1.0`→`2.1.1`).

### Phase 3 — Five-Agent Wiring ✅ CONCLUÍDO
For each of `test-qa-asis.md`, `inventory-asis.md`, `db-analyzer.md`,
`events-pubsub-asis.md`, `documentation-asis.md`: added/extended
`## Input Contract`, added an existence-check step ("SE artefato existe →
ler; SENÃO → Fallback inalterado"), demoted the pre-existing Glob/Grep
procedure to an explicit "Fallback" heading (verbatim, nothing deleted).
Partial-coverage cases (`events-pubsub-asis.md`'s Events/PubSub/IPC
categories; `documentation-asis.md`'s FT navigation-edge gap;
`inventory-asis.md`'s `orphan_dfm`; `db-analyzer.md`'s vendor detection)
stated honestly as permanent exceptions, not oversold as full replacements.

### Phase 4 — Version Sync ✅ CONCLUÍDO
Frontmatter version, FASE OBRIGATÓRIA `--version` literal, and (where
catalogued) `pipeline_observer.py`/`generate_observability_report.py`
`AGENT_CATALOG` entries all synced per file. `events-pubsub-asis` confirmed
absent from both catalogs (pre-existing gap, unrelated to this PBI, not
introduced by it) — nothing to sync there.

### Phase 5 — Verification ✅ CONCLUÍDO
See `quickstart.md`. Structural checks (fence balance, `Fallback` heading
count, `extraction/`→0 count, version consistency) + `py_compile` on both
touched Python files. No live pipeline run possible in this session (prose
instruction files) — this includes not being able to directly observe
whether the Phase A race resolves favorably or not in a real run; documented
as a known limitation rather than tested.

## Complexity Tracking

| Item | Status |
|---|---|
| Phase A race condition (6 agents may find AST artifacts absent on fresh runs) | Honestly documented, not fixed — fixing requires touching `orchestrator-asis.md`, explicitly out of scope per the user's own instruction |
| `documentation-asis.md`'s fragmented structure (no Input Contract/Execution Steps originally) | Introduced a new `## Input Contract` section from scratch; hooked per-skill notes into existing ad-hoc sections (`## Form Registry Input`, `## FR Module Cross-Validation`) rather than inventing a full Execution Steps skeleton the file never had |
| `db-analyzer.md`'s near-total absence of concrete Glob/Grep procedures | New `### AST Data Ingestion` subsection added as genuinely new content (not a refactor of an existing step, since none existed) |
| FT's navigation-edge gap (02_form_business_rules.json may not encode transition targets) | Stated honestly as unconfirmed/partial rather than assumed solved |
| Scope reversal mid-plan (documentation-asis.md) | User's `ExitPlanMode` rejection was treated as a hard correction — plan file edited and re-submitted before any implementation began, not layered on after the fact |

## Test Strategy

| Test | Command | Result |
|---|---|---|
| Path fully corrected | `grep -c "delphi-ast-raw/extraction"` across 3 files | 0/0/0 |
| Compressed count matches prior extraction count | `grep -c "delphi-ast-raw/compressed" solution-delphi.md` | 17 |
| Fallback preserved in all 5 wired files | `grep -c "Fallback"` per file | 5 / 4 / 2 / 2 / 11 (test-qa / inventory / db-analyzer / events-pubsub / documentation) |
| Fence balance | Per-file `` ``` `` parity check, all 6 files | All balanced |
| Version consistency | Frontmatter == FASE OBRIGATÓRIA `--version` literal, per file | All 6 matched |
| Observability catalogs updated | `pipeline_observer.py` + `generate_observability_report.py` version entries | 4/4 updated (events-pubsub absent from both, pre-existing gap) |
| Tools compile | `python -m py_compile pipeline_observer.py generate_observability_report.py` | OK |
