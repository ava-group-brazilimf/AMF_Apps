# Agent Implementation Plan: Observability Self-Report Activation Fix

**Spec**: `specs/004-observability-self-report-activation-fix/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (5 orchestrator-tier files) — root-cause bugfix of `specs/003` |
| **Primary Requirement** | Make the already-designed self-report mechanism actually fire, for the highest-value files |
| **Technical Approach** | Relocate each file's self-report `track` call from a disconnected appendix into that same file's own pre-existing "mandatory before closing" gate |
| **Implementation Status** | Complete for the 5 orchestrator-tier files; the ~92 leaf-agent files remain explicitly unfixed (deferred) |

## Constitution Check

- [x] **Article II** — no frontmatter contract fields changed in any of the 5 files.
- [x] **Article X** — PATCH version bump applied to all 5 files (instrumentation fix, no input/output contract change).
- [x] **Article VIII** — this PBI directly improves Article VIII compliance (observability now actually functions for these 5 files) but does not add OpenTelemetry/trace_id — same pre-existing, explicitly-acknowledged gap from `specs/002`/`specs/003`.
- [x] No `[NEEDS CLARIFICATION]` markers.

## Technical Context

Same as `specs/003` — no new tech stack. This PBI only relocates existing
Bash-call instructions within existing Markdown agent files; `pipeline_observer.py`
itself is untouched.

## Implementation Phases

### Phase 0 — Root Cause Investigation ✅ CONCLUÍDO
See `research.md`. Confirmed via direct file reads and a filesystem-wide
search that the feature had never fired once.

### Phase 1 — Master-Orchestrator Fix ✅ CONCLUÍDO
`init` inlined into Step 0.4; `track` + `finalize --auto-report` inlined into
the pre-existing `## Completion Signal` section, immediately before the
literal `↳ ✅` line. Old appendix demoted to reference-only. Incidental fix:
`5.8`/`5.9` duplicate step numbering in Step 5 corrected to `5.10`-`5.12`.
Version `1.1.0` → `1.4.0`.

### Phase 2 — Four Phase Orchestrators ✅ CONCLUÍDO
Each file's own real "mandatory before closing" gate was located individually
(no shared template — each file's structure differs) and the `track` call
inserted immediately before that gate's own output. Old broken appendix
sections removed from all 4. Versions bumped (PATCH) in all 4.

### Phase 3 — Incidental Regressions ✅ CONCLUÍDO
Found and fixed while editing `orchestrator-tobe.md`: restored a dropped
`{project_name}` placeholder in two timing templates, removed a stray
orphaned closing fence, normalized line endings back to LF.

### Phase 4 — Verification ✅ CONCLUÍDO
See `quickstart.md`. Structural check (exactly one correctly-placed `track`
call per file, balanced fences) + a live end-to-end dry run proving the
mechanism now actually produces `outputs/observability/` content and a
4-sheet Excel report for the first time.

## Complexity Tracking

| Item | Status |
|---|---|
| ~92 leaf-agent files still broken | Explicitly deferred — not attempted this pass, stated honestly in spec.md §8, not silently left ambiguous |
| Editor auto-reformatted `orchestrator-tobe.md`'s markdown tables | Cosmetic only (byte-for-byte text identical, verified table-by-table); left as-is, not reverted |

## Test Strategy

| Test | Command | Result |
|---|---|---|
| Structural placement | `grep -n "pipeline_observer.py -p {project_name} track" <file>` per file | Exactly 1 match each, inside the real gate |
| Fence balance | `grep -c '^```' <file>` | Even count, no orphaned fences |
| End-to-end dry run | `init` → `track --agent ava-master-orchestrator` → `finalize --auto-report` | Per-agent folder + shared state + 4-sheet Excel all produced |
