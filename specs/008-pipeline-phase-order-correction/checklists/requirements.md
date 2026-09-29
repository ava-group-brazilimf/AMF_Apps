# Specification Quality Checklist: Pipeline Phase Order Correction

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Problem stated with evidence (8 contradictory schemes found via Explore agent, cross-verified by direct grep before planning — not assumed)
- [x] The most surprising finding (master-orchestrator.md never invoked `ava-prototype` at all, 0 matches) is documented as the root cause of the user's "remove other invocation points" requirement, not glossed over
- [x] The two-pass discovery process (initial Explore-agent-guided fix + a final, broader exhaustive sweep that caught 8 more files) is documented honestly, including that the first pass was incomplete
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — the requested order was explicit; only its mapping onto existing contradictory code required investigation, not user clarification
- [x] Each scenario (CA01-CA03) maps to a concrete, runnable verification command in quickstart.md
- [x] Success criteria are measurable and were verified (exhaustive grep sweeps + `py_compile` + direct CLI phase-resolution test)
- [x] Scope is clearly bounded — internal TO-BE sub-step numbering ("Fase 0-8") and the unrelated "F3 Build Cycle" trigger label were explicitly identified and left untouched, with reasoning given
- [x] The pre-existing duplication of two parallel Summary-build scripts is flagged honestly as out-of-scope-to-consolidate, not silently worked around

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (CA01-CA03 map directly to the user's original 3 acceptance criteria)
- [x] The higher-risk change (splitting `summary-template.html`'s combined `f3f4` sidebar nav group and swapping `f6`/`f7` content-section IDs) was de-risked by cross-checking every `nav()` target against every actual section id before declaring it complete — zero orphaned links
- [x] Version bumps (MINOR for orchestrator-tier agents with real orchestration changes; unchanged for the 36 mechanically-fixed leaf agents, consistent with Article X precedent from specs/006) are justified per-file, not applied uniformly without reasoning

## Notes

- This PBI is the direct continuation of a task the user raised earlier in
  this same session and then set aside before a plan existed. It was
  restarted from a fresh investigation rather than resumed from stale
  assumptions, since the earlier attempt had not been validated against a
  concrete target order.
- The final exhaustive repo-wide grep pass (Phase 7 in plan.md) was not
  originally planned as a separate step — it was added after the initial,
  Explore-agent-guided fix pass completed, specifically to catch files an
  agent-driven semantic search might miss (auxiliary generator scripts,
  historical one-off docs). This caught 8 additional files and is the
  reason the final file count in this PBI is larger than the plan's
  original estimate. Worth doing as standard practice on any future
  repo-wide renumbering/relabeling task in this codebase.
