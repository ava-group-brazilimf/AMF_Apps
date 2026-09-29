# Research: Unified Business Rules & Functional Requirements Artifact

**Feature**: `026-unified-business-rules-artifact`
**Date**: 2026-07-21

---

## Decisions

### D1 — Artifact Path Strategy

**Decision**: `parse_func_reqs()` uses a path-fallback pattern — attempts `business-rules.md` first,
falls back to legacy `functional-requirements.md` if absent.

**Rationale**: Backward compatibility — projects run before this spec still have
`functional-requirements.md` on disk. A fallback costs zero runtime overhead and prevents
silent data loss in mixed-state pipelines.

**Alternatives considered**: (a) Hard-cut to `business-rules.md` only — rejected because it
breaks existing project outputs without a migration step. (b) Migrate existing artifacts — rejected
as out of scope per spec § 10 Assumptions.

---

### D2 — Section-Scoped Parsing

**Decision**: `parse_func_reqs()` body is unchanged. No section-scoping logic is added.

**Rationale**: The parser already filters by FR-NNN regex patterns (`FR-`, `RF-`, `RQ-`).
`## Business Rules` content uses `BR-NNN`, `RN-XX-NN`, or `## Domain:` headers — none match the
FR-NNN regex. Adding section-scoping would add complexity for zero benefit.

**Evidence**: `build_summary_comprehensive.py:5405` — existing regex `r'^\|\s*((?:FR|RF|RQ)-[\w][\w.-]*)\s*\|'`

---

### D3 — Orchestrator Phase B Dispatch Simplification

**Decision**: Replace the two-step `doc:RF` + `doc:RN` cascade (linked via `functional-requirements.md` dep)
with a single `doc:BRF` dispatch. `bridge-fastqa` trigger changes from `RF✓ + RN✓` to `BRF✓`.

**Rationale**: Eliminates an intermediate artifact dependency from the orchestrator dispatch
graph. Reduces Phase B from 3 dispatch rules (RF, RN, bridge) to 2 (BRF, bridge). The
`functional-requirements.md` dep no longer exists so the cascade cannot be preserved as-is.

**Alternatives considered**: Keep RF+RN as separate dispatches using `business-rules.md` as the
dep for RN — rejected because it requires the orchestrator to read a section of the unified file
to determine if RF completed, adding fragility vs. a single completion signal from BRF.

---

### D4 — Coder Agent Simplification

**Decision**: Remove `code-business-rules.md` fallback entirely. Single source: `asis/docs/business-rules.md`.
BLOCKED message updated to reference the new unified file.

**Rationale**: `code-business-rules.md` is discontinued per spec. The AST-derived BR data
(`01_business_rules.json`) remains accessible for advanced consumers but the pre-processed
file is no longer written to disk. Coder agents read the documentation-tier BR IDs (BR-NNN)
which are sufficient for code annotation purposes.

---

### D5 — `FUNC_NAMES` constant cleanup

**Decision**: Remove `"functional-requirements"` from the `FUNC_NAMES` set at line 2144 of
`build_summary_comprehensive.py`. The `"business-rules"` entry already covers the unified file.

**Rationale**: `FUNC_NAMES` is used to verify that FUNC-type artifacts are non-empty. The
unified `business-rules.md` covers both FR and BR validation. Keeping both entries would
cause a false-negative check on a path that no longer exists.

---

## Key Line References

| File | Lines | Purpose |
|------|-------|---------|
| `build_summary_comprehensive.py` | 169 | Artifact discovery: `functional-requirements` entry — DELETE |
| `build_summary_comprehensive.py` | 2144 | `FUNC_NAMES` set — remove `"functional-requirements"` |
| `build_summary_comprehensive.py` | 5396–5450 | `parse_func_reqs()` function — call site update only |
| `build_summary_comprehensive.py` | 7215 | Call site — update path argument (add fallback) |
| `build_summary_complete.py` | 77 | Artifact discovery: `functional-requirements` entry — DELETE |
| `build_summary_complete.py` | 949–956 | `parse_functional_requirements()` — update path read |
| `build_summary_complete.py` | 2589 | Call site — no change needed if function updated internally |
| `validate_summary.py` | 300 | `src` path assignment — add fallback |
| `validate_summary.py` | 2307–2308 | Check C2.4 description — update text |
| `validate_summary.py` | 2499–2500 | Check C11.7 description — update text (no logic change) |
| `orchestrator-asis.md` | ~200–208 | Phase B dispatch rules — RF/RN → BRF |
| `documentation-asis.md` | Skills table | Add `BRF` row; update `RF` and `RN` rows |
| `documentation-asis.md` | Output Contract | Remove `functional-requirements.md` (artifact #2) |
| `documentation-asis.md` | ALL Trigger DAG | Update to 3-level DAG |
| `solution-delphi.md` | Steps 3, 14 | Remove `code-business-rules.md` write |
| `solution-delphi.md` | Output Contract | Remove `code-business-rules.md` entry |
