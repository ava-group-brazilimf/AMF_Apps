# Specification Quality Checklist: Model-Aware Observability

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-06
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Root cause stated with evidence (repo-wide grep for any model-detection mechanism — none found)
- [x] The independent cost-calculation bug this exposed is documented as a necessary companion fix, not scope creep
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Each scenario maps to a concrete command in quickstart.md, all run directly in this session
- [x] Success criteria are measurable and were verified (6 model-string tests + 1 mixed-model end-to-end run)
- [x] Scope is clearly bounded — no attempt to add automatic model detection, since it's confirmed impossible from within this repo's `.md` files
- [x] The corrected default (Claude Sonnet 4.6, not Opus) reflects the user's explicit correction, not the assistant's original assumption

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] Self-report accuracy is stated as best-effort, not guaranteed — consistent with how token/duration estimates are already framed in `specs/003`

## Notes

- This PBI corrects course mid-plan: the initial draft (before `ExitPlanMode`)
  defaulted to Opus-tier pricing, matching the pre-existing (wrong) constant.
  The user's explicit correction — Sonnet 4.6 is the pipeline's actual
  default — was applied before implementation began, not discovered
  after the fact.
- The `orchestrator-tobe.md` file has now needed the same "dropped closing
  fence" repair twice across two different PBIs (`specs/005` and this one),
  both times from an external edit pass outside this session's own tool
  calls. Worth keeping an eye on if a third occurrence shows up.
