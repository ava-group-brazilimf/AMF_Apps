# Agent Implementation Plan: Model-Aware Observability

**Spec**: `specs/006-model-aware-observability/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (97 agent files + 2 tool scripts + 1 shared doc + 1 README) |
| **Primary Requirement** | Stop hardcoding `--model "Claude Opus 4.6"`; self-report the real model; make cost calculation model-aware |
| **Technical Approach** | Mechanical text substitution across 97 files (no repositioning — blocks already correctly placed by specs/005) + a real code fix (per-model pricing table) in both observability tools |
| **Implementation Status** | Complete. All 97 files verified. Tool re-tested against 6 model strings + a mixed-model end-to-end run. |

## Constitution Check

- [x] **Article II** — no agent contract fields changed.
- [x] **Article X** — content/instrumentation change, no contract-breaking change; no version bump required beyond what specs/005 already applied.
- [x] **Article VIII** — improves observability accuracy (cost now reflects the real model); does not resolve the still-open OpenTelemetry/trace_id gap from specs/002, unaffected by this PBI.
- [x] No `[NEEDS CLARIFICATION]` markers.

## Technical Context

Pure Python edits (2 files) + Markdown text substitution (97 files, via a
scratchpad-only batch script, not committed). No new dependencies.

## Implementation Phases

### Phase 0 — Investigation ✅ CONCLUÍDO
Confirmed no model-detection mechanism exists anywhere in this repo or
documented GitHub Copilot/Claude Code conventions (see research.md §1).
Confirmed the cost-calculation bug this exposed (research.md §2).

### Phase 1 — Tool-Side Fix ✅ CONCLUÍDO
Added `MODEL_PRICING`/`DEFAULT_MODEL`/`_get_pricing_for_model()` to both
`pipeline_observer.py` and `agent_observability.py`; threaded `model`
through `_calc_cost`; changed CLI defaults from Opus to Sonnet tier. Tested
directly against 6 model strings before touching any agent file.

### Phase 2 — Agent-Side Fix ✅ CONCLUÍDO
Batch script replaced the hardcoded literal with `{modelo_atual}` +
inline resolution note across 96 files automatically; 1 file
(`orchestrator-tobe.md`) handled manually after the script correctly
skipped it (missing heading from an external edit — restored along with the
model fix).

### Phase 3 — Shared Documentation ✅ CONCLUÍDO
`observability-self-report.md` (v2.1.0) and `src/shared/tools/README.md`
updated with the new pricing table and self-report convention.

### Phase 4 — Verification ✅ CONCLUÍDO
See `quickstart.md`. Structural checks (97/97 correct) + functional checks
(per-model cost verified 6 ways + mixed-model end-to-end run).

## Complexity Tracking

| Item | Status |
|---|---|
| Model self-report accuracy | Best-effort by design — no way to verify from outside the LLM's own self-knowledge; documented honestly, not oversold |
| Pricing table maintenance | Small hand-maintained dict; new/renamed models fall back to Sonnet-tier rate until updated — acceptable, documented in README |
| Recurring external-edit artifact in `orchestrator-tobe.md` | Second occurrence of the same dropped-fence pattern from specs/005; fixed again, flagged to the user as worth watching |

## Test Strategy

| Test | Command | Result |
|---|---|---|
| Per-model cost | `track` with 6 different `--model` values, same token counts | $1.80 / $9.00 / $1.25 / $0.625 / $1.80 (fallback) / $1.80 (fallback) — all correct |
| Mixed-model run | `init` → `track`(Sonnet) → `track`(Opus) → `finalize --auto-report` | Both agents' own model/cost correctly recorded and reported in the same Excel |
| Coverage | grep for hardcoded literal vs. `{modelo_atual}` across all agent files | 0 hardcoded, 97/97 with placeholder |
| Fence balance | per-file `` ``` `` parity check | 96/97 balanced, 1 pre-existing unrelated case (`solution-vb.md`) |
