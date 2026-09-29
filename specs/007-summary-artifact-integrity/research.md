# Research: Summary Artifact Integrity Verification (007)

**Feature**: `007-summary-artifact-integrity`
**Date**: 2026-07-08

---

## Q1 — Where is the correct insertion point for the pre-build check in summary-agent.md?

**Decision**: Insert as a new `## Verificação de Integridade de Artefatos (Pré-Build)` section placed immediately before `## Execution Steps` (i.e., after `## Execution Modes`). Within the execution flow, it is labelled **Step 0.5** and runs synchronously after the NTP timing initialization and before the `Step 1-2` block.

**Rationale**: The existing `Pre-Step — Garantir Artefatos Críticos (NOVO)` block (already in the agent body) handles fallback generation for `metrics.json` and `risk-register.json`. The new Step 0.5 is distinct — it iterates **all** entries in `artifact-map.yaml` (not just two), does not generate fallbacks, and emits named `[ARTIFACT-MISSING]`/`[ARTIFACT-EMPTY]` markers instead. The two steps are complementary.

**Alternatives considered**:  
- Merging into the existing Pre-Step block: rejected — different semantics (fallback vs. integrity gate).
- Inserting into `build_summary_comprehensive.py`: rejected — the spec requires the agent body (LLM prompt) to emit the signal, not the Python script.

---

## Q2 — How does artifact-map.yaml encode paths? Are they project-relative?

**Decision**: Paths in `artifact-map.yaml` use the prefix `project/outputs/` (note: singular, without the project name). The agent resolves actual paths as `projects/{project_name}/outputs/{rest_of_path}` at runtime. The integrity check must do the same resolution.

**Rationale**: Inspected `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` line 20 — `primary_output: "project/outputs/asis/master-report.md"`. The agent already knows `{project_name}` from Step 1.1.

**Alternatives considered**: Using glob patterns — rejected, artifact-map.yaml already gives canonical paths.

---

## Q3 — Where does C11 fit in validate_summary.py's CHECKS list and rule functions?

**Decision**: Add three new functions `_c11_1`, `_c11_2`, `_c11_3` after the C9 block (line ~792) and register three `Check(...)` entries in the CHECKS list after the C9.3 entry (line ~1489). The CHECKS list currently closes with `]` at line ~1490.

**Rationale**: The rule catalog structure is clear: one block of functions per category (C1–C9 at time of writing) and one block of Check registrations. C10 is referenced in the agent doc but absent from validate_summary.py (documentation is ahead of implementation). C11 should be added as the next implemented category.

**Alternatives considered**: Adding C10+C11 simultaneously — out of scope for this PBI. Placeholder C10 entries would require a separate PBI.

---

## Q4 — What severity should C11.3 (empty table) have?

**Decision**: `"warn"` — it does not trigger exit code 1 by itself.

**Rationale**: An empty table may legitimately occur in early-phase runs where only F1 is executed (F5 QA tables empty by design). Making it an error would block legitimate partial runs. The spec (Scenario 5) confirms warning level.

**Alternatives considered**: `"error"` — rejected per spec and stakeholder intent.

---

## Q5 — Does build_summary_comprehensive.py need changes?

**Decision**: **No changes** to `build_summary_comprehensive.py` are required for this PBI.

**Rationale**: The pre-build check runs in the LLM prompt layer (summary-agent.md Step 0.5) before the Python script is called. When a section is omitted, the agent simply skips passing that section's data to the script. The script already handles absent data gracefully (it outputs placeholder text which is then caught by C11.1/C11.2). Long-term remediation of `build_summary_comprehensive.py` is a separate concern.

**Alternatives considered**: Modifying the script to skip sections — deferred; out of scope per spec Exclusions.

---

## Q6 — Timing table: does Step 0.5 need its own row in the MICRO table?

**Decision**: **Yes** — add a `Step 0.5 — Verificação de Integridade` row to both FULL and STATUS_ONLY MICRO template tables in summary-agent.md.

**Rationale**: Constitution Article VIII (observability) + the timing invariant guarantee that every executed step appears in the MICRO table. Omitting Step 0.5 would violate the output invariant.

**Alternatives considered**: Including it under Step 1's row — rejected, it is a distinct, named step with its own NTP capture.
