# Research — 025 Summary Test Cases AS-IS Menu

## Decision: Source artifact structure

**Decision**: Parse `## CT-NNN — <title>` H2 blocks with forgiving regex; missing fields default to `""`.

**Rationale**: The `test-cases.md` produced by `ava-asis-bridge-fastqa` Step 17b has a well-defined but potentially variable format (metadata can appear on one line or multiple lines, `—` vs `-` separator, optional `### Pós-condições`). A forgiving per-field regex approach (same as `build_test_map()`) is more resilient than a strict line-by-line parser.

**Alternatives considered**:
- Strict YAML frontmatter per case: would require changing the producer agent; rejected (out of scope)
- JSON source file: would be ideal but `ava-asis-bridge-fastqa` Step 17b currently produces Markdown; rejected (out of scope)

---

## Decision: D.testCases as a flat array (no nesting)

**Decision**: Flat `list[dict]` serialised via `safe_json()` identical to `testMap` and `testGaps`.

**Rationale**: The template JS only needs to render a table; no nested objects required. `steps_raw` (raw Markdown string) provides enough data for any future detail modal without requiring a nested array of step objects at this time.

**Alternatives considered**:
- `steps` as an array of `{n, action, expected}` objects: richer but adds complexity to the parser and increases HTML payload size; deferred to a future spec if a step-detail modal is requested.

---

## Decision: C11.37 as `warn` not `error`

**Decision**: `warn` level in `validate_summary.py`.

**Rationale**: `test-cases.md` is optional — it is produced by `ava-asis-bridge-fastqa` only when the FastQA pipeline has been run on the project. Many existing projects will not have this file. Blocking the summary with an `error` for an optional artifact contradicts the graceful-degradation principle already established for F5 QA data (see C11.11 `warn` pattern).

---

## Decision: Remediation Regra J synthesis guard

**Decision**: Only synthesize placeholder when `fastqa/manual_test/` does not exist.

**Rationale**: If `fastqa/manual_test/` exists, FastQA has been run but `ava-asis-bridge-fastqa` Step 17b hasn't consolidated the cases yet. Synthesizing in this case would hide the real upstream gap. The `write_if_absent()` + `SYNTH_TAG` approach is consistent with all other rules (A–I) in `remediate_summary.py`.

---

## Decision: No new CSS classes

**Decision**: Re-use `.kg`, `.kc`, `.at`, `.sv`, `.sc`, `.sa`, `.sm`, `.sb2` for the new section.

**Rationale**: All KPI tiles, tables, and priority badges in the new section have the same visual requirements as existing sections. Adding new CSS classes would risk conflicts in the single-file HTML output without any UX benefit.

---

## No further research required

All open questions resolved. Proceeding to Phase 1 design.
