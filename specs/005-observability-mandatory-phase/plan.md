# Agent Implementation Plan: Observability Mandatory Phase

**Spec**: `specs/005-observability-mandatory-phase/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (97 agent files, bulk) + 2 shared docs updated |
| **Primary Requirement** | Make the self-report mechanism fire reliably, for every agent, for any project, via a self-contained mandatory phase instead of reference-doc indirection |
| **Technical Approach** | Tiered anchor detector (5 tiers) + idempotent old-section removal, batch-applied to 92 leaf files; 5 orchestrator-tier files manually re-strengthened with the same template |
| **Implementation Status** | Complete. 97/97 files verified structurally sound. Tool re-confirmed generic across 2 different project names. Environmental constraint (no enforced tool-calling wiring in this repo) documented explicitly, not resolved — cannot be resolved from within `.md` files. |

## Constitution Check

- [x] **Article II** — no agent `name:`/`description:`/`allowed-tools:` contract fields changed across all 97 files.
- [x] **Article X** — this is instrumentation/documentation content, not a contract change; no version bump required for the 92 batch-edited leaf files (consistent with specs/003's precedent); the 5 orchestrator files already had PATCH bumps from specs/004, left as-is (content changed, version numbers unchanged since the *mechanism*, not the *contract*, changed again).
- [x] **Article VIII** — directly targets Observability & Traceability; honestly reports that the OpenTelemetry/trace_id gap from specs/002 remains open, and additionally surfaces a new, more fundamental gap (no verified tool-calling harness) rather than claiming full compliance.
- [x] No `[NEEDS CLARIFICATION]` markers.

## Technical Context

Same as specs/002-004 — no new tech stack. Pure Markdown-file editing plus
one Python batch script (scratchpad-only, not committed) implementing the
tiered anchor detector.

## Implementation Phases

### Phase 0 — Diagnosis ✅ CONCLUÍDO
See `research.md`. Established the two-level root cause (environmental +
structural) via direct user testing feedback plus a fresh investigation into
the actual invocation mechanism.

### Phase 1 — Anchor Detector Design & Dry-Run Review ✅ CONCLUÍDO
Built a 5-tier regex-based detector, dry-ran in report-only mode, iteratively
broadened patterns based on manual review of borderline cases (18 → 12
Tier-5 fallback files), confirmed via direct read that all 3 known
severely-misplaced files resolve to their correct real anchor.

### Phase 2 — Batch Execution ✅ CONCLUÍDO
Ran the detector for real across 92 leaf-agent files (101 total minus 5
orchestrator-tier files minus 4 db-analyzer skills minus 2 stray duplicates).
0 errors. Verified: exactly one `FASE OBRIGATÓRIA` heading and one `track`
command per file, balanced code fences in 96/97 (1 pre-existing, unrelated
imbalance in `solution-vb.md`, confirmed present in git `HEAD`).

### Phase 3 — Orchestrator Re-Strengthening ✅ CONCLUÍDO
Manually replaced the specs/004-style bullet/note in all 5 orchestrator-tier
files with the new self-contained, maximally-imperative template, baking in
each file's own real `agent_id`/`phase`/`version`. Discovered and fixed an
unrelated pre-existing dropped-fence regression in `orchestrator-tobe.md`
while editing it (see research.md §5).

### Phase 4 — Shared Documentation Update ✅ CONCLUÍDO
`observability-self-report.md` reframed as reference/rationale material
(v2.0.0), no longer the primary actionable pointer. `src/shared/tools/README.md`
updated with an explicit environment-requirement callout.

### Phase 5 — Verification ✅ CONCLUÍDO
See `quickstart.md`. Structural checks across all 97 files + a live dry run
proving the tool itself works correctly and generically (tested against
`Meu-ERP-001` and an arbitrary new project name).

## Complexity Tracking

| Item | Status |
|---|---|
| Environmental tool-calling gap | **Not resolved, not resolvable from `.md` files alone** — documented in 3 places, flagged as the honest final state, not silently implied fixed |
| Pre-existing fence imbalance in `solution-vb.md` | Confirmed present in git `HEAD`, unrelated to observability, left untouched (out of scope) |
| `AGENT_CATALOG` duplication (pipeline_observer.py vs generate_observability_report.py) | Carried over from specs/002/003, still unaddressed, still low risk |

## Test Strategy

| Test | Command | Result |
|---|---|---|
| Coverage | grep count of `FASE OBRIGATÓRIA` across all agent files | 97 (92 leaf + 5 orchestrator) |
| Fence balance | per-file `` ``` `` count parity | 96/97 balanced, 1 pre-existing unrelated case |
| Command completeness | grep for literal `track` invocation | 97/97 present |
| Tool genericity | live `init`/`track` against 2 different project names | Both produced correct, isolated output |
| Misplacement repair | direct read of 3 previously-misplaced files | All 3 now anchor at their real completion point |
