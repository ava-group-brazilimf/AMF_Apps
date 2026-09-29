# Tasks: Artifact-Only Consumption Guardrail + Missing-Artifact Escalation Gate (F2 TO-BE)

**Spec**: `specs/016-tobe-artifact-only-guardrail/spec.md`
**Plan**: `specs/016-tobe-artifact-only-guardrail/plan.md`

## Category 1 — Shared Protocol File

- [x] 1.1 Create `src/modules/ava-fabric-agents/shared/artifact-only-consumption-protocol.md` with `## 1. Proibição de Releitura de Código Legado` (prohibition list + 3 preserved legitimate exceptions + positive rule)
- [x] 1.2 Add `## 2. Procedimento de Escalonamento — Artefato Obrigatório Ausente` (non-blocking soft-degrade path + blocking `⛔ [ARTIFACT GATE FAILED]` structured report with Opção A/B/C)
- [x] 1.3 Cross-reference Gate 0→1 (`orchestrator-tobe.md`) and `coder-dotnet.md` G-9 as pre-existing compliant examples, not replaced

## Category 2 — Orchestrator Hardening (`orchestrator-tobe.md`)

- [x] 2.1 Grep-confirm the authoritative list/count of `Invocar`/cross-module dispatch sites (do not trust a pre-computed line-number list)
- [x] 2.2 Add new `## Dispatch Protocol` section after `## Agent Team Gerenciado`, adapted from `master-orchestrator.md`'s own section
- [x] 2.3 Prefix every confirmed dispatch site with `⛔ Read({path}) OBRIGATÓRIO (ver § Dispatch Protocol) →`
- [x] 2.4 Add reference line to `@artifact-only-consumption-protocol` near `## Canonical Inputs`
- [x] 2.5 Fix Fase 4.5 input path: `outputs/tobe/migration-plan.md` → `outputs/tobe/docs/migration-plan.md` (io-map §4.4)
- [x] 2.6 Append escalation-format pointer to each existing `HARD STOP`/`[GATE FAILED]` block, preserving their existing custom report bodies verbatim
- [x] 2.7 Bump frontmatter `version: "2.3.0"` → `"2.4.0"`, `date:` → `2026-07-12`

## Category 3 — Module Registration (`module.yaml`)

- [x] 3.1 Diff `module.yaml`'s `agents:` list against every `.md` file's frontmatter `name:` in `tobe-architecture/agents/`
- [x] 3.2 Add missing entries confirmed live via `Invocar` grep: `ava-tobe-adr`, `ava-tobe-coexistence-strategy`, `ava-tobe-risk-mitigation`, `ava-coder-dotnet`, `ava-tobe-designer-system` (5 entries)
- [x] 3.3 Additionally register `ava-tobe-user-journeys` (`agents/user-journeys-tobe.md`) — a real, activation-phrase-bearing agent listed in the Agent Team Gerenciado table, but with **no explicit `Invocar` line** in `orchestrator-tobe.md` today (Fase 7 has no dedicated `### Fase N —` body, a pre-existing gap already tracked in `docs/tobe-architecture-io-map.md` §4.3 and left unfixed per this PBI's Exclusions). Registered in `module.yaml` regardless, since the Article IV registration gap exists independent of the separate Fase 7 dispatch-wiring gap.
- [x] 3.4 Confirm `dotnet-nuget-policy.md` correctly excluded (shared-style include, referenced via markdown link from `coder-dotnet.md`, never `Invocar`'d)
- [x] 3.5 Bump `version: "1.3.0"` → `"1.3.1"`

## Category 4 — Per-Agent Guardrail Wiring (20 files)

- [x] 4.1 Read `architecture-decision-matrix-tobe.md`, `adr-tobe.md`, `architecture-design-tobe.md`, `database-policy-tobe.md`, `database-design-tobe.md`, `security-design-tobe.md`, `architecture-technical-tobe.md`, `migration-plan-tobe.md`, `measure-size-tobe.md`, `coexistence-strategy-tobe.md`, `risk-mitigation-tobe.md`, `openapi-spec-tobe.md`, `coder-dotnet.md`, `docs-tobe.md`, `developer-guide-tobe.md`, `test-plan-tobe.md`, `user-journeys-tobe.md`, `designer-system-tobe.md`, `test-plan-consolidated-tobe.md`, `azure-infra-estimator-tobe.md` — locate each file's Input Contract/Input Sources section (heading name varies per file)
- [x] 4.2 Add `@artifact-only-consumption-protocol` reference line to each of the 20 files
- [x] 4.3 Append escalation-format pointer to each existing blocking-input clause per file (non-blocking clauses left untouched)
- [x] 4.4 Introduce `version: "1.0.0"` on the 9 files missing the field entirely: `database-policy-tobe.md`, `database-design-tobe.md`, `architecture-technical-tobe.md`, `risk-mitigation-tobe.md`, `openapi-spec-tobe.md`, `coder-dotnet.md`, `docs-tobe.md`, `user-journeys-tobe.md`, `designer-system-tobe.md`
- [x] 4.5 MINOR-bump `version:` on the remaining 11 files that already had one
- [x] 4.6 `risk-mitigation-tobe.md` — apply the same path fix as 2.5 to its own Input Sources table
- [x] 4.7 `azure-infra-estimator-tobe.md` — fix Read Priority path (1): `outputs/tobe/sizing-report.md` → `outputs/tobe/docs/sizing-report.md`
- [x] 4.8 `test-plan-tobe.md` — reclassify `architecture-technical.md` input from ✅ obrigatório to ❌ non-blocking (io-map §4.6)
- [x] 4.9 `designer-system-tobe.md` — verify `screen-flow.md` blocking status; confirmed already non-blocking (enrichment-only, outside `## Gate`) — no change needed, documented as such

## Category 5 — Documentation Sync

- [x] 5.1 `docs/tobe-architecture-io-map.md` §3 — append note that the prohibition is now enforced (not merely observed), referencing the new shared protocol + Dispatch Protocol
- [x] 5.2 `docs/tobe-architecture-io-map.md` §4.4/§4.6/§4.7/§4.8 — append `**Status**:` note per entry referencing this spec
- [x] 5.3 `CHANGELOG.md` — new entry describing the guardrail + escalation gate + Dispatch Protocol + bundled path fixes, matching existing entry format

## Category 6 — Speckit Documentation

- [x] 6.1 Write `specs/016-tobe-artifact-only-guardrail/spec.md` (Agent Identity, Problem Statement, Decision, User Scenarios, Quality Gate Requirements, Dependencies, Exclusions, Assumptions, Success Criteria)
- [x] 6.2 Write `specs/016-tobe-artifact-only-guardrail/plan.md` (Summary, Constitution Check, Technical Context, Implementation Phases, Complexity Tracking, Test Strategy)
- [x] 6.3 Write `specs/016-tobe-artifact-only-guardrail/tasks.md` (this file)

## Category 7 — Verification

- [x] 7.1 `grep -c "⛔ Read("` in `orchestrator-tobe.md` → **26**, matches the 26 confirmed `Invocar`/cross-module dispatch sites
- [x] 7.2 `grep -rl "artifact-only-consumption-protocol"` across `tobe-architecture/agents/` → **21 files** (orchestrator + 20 dispatched agents)
- [x] 7.3 `grep -c "outputs/tobe/migration-plan.md$"` (old path) in `orchestrator-tobe.md` + `risk-mitigation-tobe.md` → **0 / 0**
- [x] 7.4 `grep -c "outputs/tobe/sizing-report\.md[^/]"` (bare, old path) in `azure-infra-estimator-tobe.md` → **0**
- [x] 7.5 `module.yaml` → **21** `id: ava-*` entries total (15 original + 6 new: `ava-tobe-adr`, `ava-tobe-coexistence-strategy`, `ava-tobe-risk-mitigation`, `ava-coder-dotnet`, `ava-tobe-designer-system`, `ava-tobe-user-journeys`); `dotnet-nuget-policy` → **0** matches (correctly excluded)
- [x] 7.6 All 9 previously-versionless agent files now have `version: "1.0.0"` (confirmed by the wiring agent's per-file report)
- [x] 7.7 Markdown fence-balance / structural sanity confirmed by both editing agents during their own verification passes; `git status` shows exactly the expected 22 modified files + 2 new (shared protocol file, `specs/016-tobe-artifact-only-guardrail/`)
- [x] 7.8 No existing `## Output Contract` field removed in any touched file — both editing agents were explicitly constrained to additive-only diffs (reference lines, escalation pointers, version bumps, 4 path/label fixes) and reported no Output Contract touches

## Completion Checklist

- [x] All Category 1-6 tasks checked off with corresponding file changes verified present
- [x] Category 7 verification commands run and results recorded
- [x] `git status` reviewed — only the files named in `spec.md` §1/§3 touched (22 modified + shared protocol file + this spec folder), nothing unexpected staged
- [x] `CHANGELOG.md` entry present and correctly formatted
