# Specification Quality Checklist: AST-Artifact Consumption Extension + compressed/ Path Fix

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-08
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Path-correction claim verified by direct diff (real `extraction/` vs `compressed/` sample), not assumed from naming convention alone
- [x] Every candidate agent's source-reading behavior confirmed by reading the full file (3 parallel Explore agents), not inferred from the io-map summary alone
- [x] The Phase A race-condition risk is verified against `orchestrator-asis.md`'s actual `dispatch_schedule`, not speculated
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Each scenario (CA01-CA04) maps to a concrete grep/verification command in quickstart.md
- [x] Success criteria are measurable and were verified structurally (no live pipeline run possible for prose instruction files, stated explicitly — including that the race condition's real-world timing outcome could not be observed, only its existence confirmed)
- [x] Scope is clearly bounded — security sub-agents, non-Delphi solution agents, and pure-consolidation agents all excluded with file-by-file reasoning
- [x] Every partial-coverage case (events-pubsub's 3 uncovered categories, documentation-asis's FT navigation gap, inventory-asis's orphan_dfm, db-analyzer's vendor detection) is stated as a permanent limitation, not a placeholder to "fix later"

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] The mid-plan scope correction (documentation-asis.md's inclusion, reversing the initial exclusion) is recorded with the user's exact rejection reason, not smoothed over as if it were the original plan
- [x] Version bumps correctly distinguish the PATCH-only path fix from the 5 MINOR additive wirings

## Notes

- This PBI directly builds on `specs/007` (established the Input-Contract/
  existence-check/fallback pattern and the 9-artifact schema documentation)
  and `specs/009` (added the 9th artifact). No new pattern was invented —
  every one of the 5 newly-wired agents reuses the exact same structural
  convention.
- The Phase A race condition is the most significant known limitation
  surfaced in this PBI. It was not discovered by assumption — it required
  directly reading `orchestrator-asis.md`'s `dispatch_schedule` YAML block
  and cross-referencing a real sample run's extraction timing
  (`metrics.jsonl`). Consistent with this session's established practice,
  it is documented rather than silently worked around by touching the
  orchestrator (which the user explicitly placed out of scope).
- The user's rejection of the first `ExitPlanMode` submission (excluding
  `documentation-asis.md`) is a genuine example of course-correction mid-
  session, not a planning failure — the initial exclusion was reasonable
  given the file's fragmented structure, but the user had a clearer view of
  the intended scope ("os agentes devem fazer a leitura... e interpretação
  via LLM para gerar os outputs" — applying to *all* agents reading source,
  not a curated subset), and the plan was corrected before any
  implementation began.
