# Specification Quality Checklist: Prototype → Component Conversion (P2C)

**Purpose**: Validate specification completeness and quality before proceeding to implementation
**Created**: 2026-08-04
**Feature**: [spec.md](../spec.md)

## IMFAI Constitution Compliance *(mandatory — always first)*

> These items apply to every IMFAI agent development checklist regardless of change type.

- [x] CHK-C01 `[Article II]` Agent frontmatter contains ONLY `name`, `version`, `description` (Portuguese + activation phrases), `allowed-tools` — no `phase`, `module`, `inputs`, `outputs`, or `dependencies`
- [x] CHK-C02 `[Article I]` No technology versions hardcoded in agent body — all values resolved from `reference-architecture.yaml` or `project-config.yaml`
- [x] CHK-C03 `[Article II]` All output paths use lowercase `{project_name}` and the correct phase folder (`asis/`, `tobe/docs/`, `qa/`, etc.)
- [x] CHK-C04 `[Article V]` Agent instruction body is written in Brazilian Portuguese
- [x] CHK-C05 `[Article IV]` Module-level `module.yaml` registration reviewed — new entry added (new-agent) or existing entry version-bumped (modify-existing)
- [x] CHK-C06 `[Article XI]` SKILL.md status confirmed — new SKILL.md created (new-agent) or existing verified still routes correctly after changes (modify-existing)
- [x] CHK-C07 `[Article VI]` BDD acceptance scenarios cover nominal path, edge case (empty/missing input), and quality gate path (human_gate_required trigger)

**Notes on CHK-C01:** both agents carried a `date:` key before this change — a pre-existing
violation, corrected here. Angular additionally declared `allowed-tools: Read, Write, Edit, Glob`
while invoking `Bash:` in three steps; `Bash` was added.

**Notes on CHK-C05:** both agents were already registered in `tech-stack/module.yaml`; only the
module version changed (1.4.0 → 1.5.0). The three new files are a shared include and two data
references — not agents — so no entry is required.

## Content Quality

- [x] No implementation detail leaks into the problem statement — §2 describes observed behaviour and cites file/line evidence
- [x] Written so a reviewer who has not read the agent bodies can follow it
- [x] All mandatory template sections present, in the override template's order
- [x] Every claim about current behaviour is backed by a verifiable check (grep count, line number, or quoted text)

## Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Requirements are testable — Success Criteria are grep- or exit-code-verifiable
- [x] Success criteria are measurable and technology-agnostic where possible (SC-14/SC-15 are behavioural)
- [x] All acceptance scenarios are defined (nominal / prototype-absent / assertion-failure)
- [x] Edge cases identified — the 7-case discrepancy matrix covers every combination of `screen-list.md` × `index.html`
- [x] Scope is clearly bounded — §7 excludes Vue, Blazor, the prototype agent, the build validator, browser smoke runs and visual regression
- [x] Dependencies and assumptions identified — §6 and §8, including the `verify_scaffold.py` CWD assumption and the RNF04 cap
- [x] Version bump type justified against Article X for both agents

## Feature Readiness

- [x] Each functional requirement from the user maps to at least one acceptance scenario
- [x] The user's explicit "WARN and continue" requirement is encoded as a P1 scenario, not an afterthought
- [x] The contradiction between Angular's HARD STOP and `master-orchestrator.md`'s non-blocking F3 is resolved explicitly, in favour of the orchestrator
- [x] No blocking ambiguity remains for implementation

## Feature-Specific — Conversion Fidelity

- [x] CHK001 The unit of screen generation is the prototype screen, not the bounded context, in both agents
- [x] CHK002 The assertion denominator (`effective_status == "included"`) is defined literally and is robust to a stale `screen-list.md`
- [x] CHK003 A second, template-level assertion exists — file existence alone produced the exact false positive this spec fixes
- [x] CHK004 The repair loop is bounded (max 3 iterations) and cannot spin indefinitely
- [x] CHK005 `deferred` screens are excluded from the denominator **and** must be listed in `## TODOs Pendentes`, so `prototype_fidelity: full` cannot be misread
- [x] CHK006 Prototype-only affordances (`btn-simular-erro`) are dropped deliberately and recorded in `dropped_constructs[]`
- [x] CHK007 Every prototype construct in the mapping table has a named destination component in both frameworks

## Feature-Specific — Degradation

- [x] CHK008 No prototype artifact is a HARD STOP in either agent
- [x] CHK009 `P2C-W001` continues execution and marks the assertion `SKIPPED`, never `FAIL`
- [x] CHK010 The design-token fallback chain has three documented levels and records `design_tokens_source`
- [x] CHK011 Default tokens satisfy WCAG 2.1 AA contrast (4.5:1 for text)
- [x] CHK012 Every warn code `P2C-W001..W009` has a defined condition and behaviour

## Feature-Specific — Business Rules and API

- [x] CHK013 `business-rules-catalog.json` is the primary source; `business-rules.md` is fallback only
- [x] CHK014 The hard/soft binding split is justified — failing on a heuristic `bc-fallback` binding would be dishonest
- [x] CHK015 The `// Implements: BR-XXXX` marker regex is specified, making the assertion greppable
- [x] CHK016 Path/method normalisation strips the version prefix before comparison — raw string compare produces false negatives against `servers[].url`
- [x] CHK017 The OpenAPI contract wins for anything that becomes code, and no divergence is resolved silently
- [x] CHK018 `MISSING_IN_CONTRACT` still generates the screen — fidelity outranks the contract gap

## Feature-Specific — Working Software

- [x] CHK019 Unit tests are **executed**, not merely configured — the previous `coverageThreshold` was never exercised
- [x] CHK020 `json-summary` is mandated in both coverage reporters so the numbers can be read deterministically
- [x] CHK021 `TOOLCHAIN_UNAVAILABLE` is a first-class, non-blocking outcome with a stated rationale
- [x] CHK022 `COMPLETED` preconditions are enumerated and distinguish real failures from known degradations
- [x] CHK023 Each converted screen has a test asserting the literal prototype title

## Notes

- The `verify_scaffold.py` repo-root assumption is documented in spec §8 rather than fixed here —
  changing the script's search path is outside this spec's scope and every existing caller already
  runs from the root.
- `specs/021` §8 explicitly excluded "non-Angular frontend stubs"; this spec closes exactly that gap.
- Check items off as completed: `[x]` · CHK-C items are IMFAI-specific; all others are feature-specific.
