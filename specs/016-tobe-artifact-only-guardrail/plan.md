# Agent Implementation Plan: Artifact-Only Consumption Guardrail + Missing-Artifact Escalation Gate (F2 TO-BE)

**Spec**: `specs/016-tobe-artifact-only-guardrail/spec.md`

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (`orchestrator-tobe.md` + 20 dispatched agent files + `module.yaml`, MINOR/PATCH each) + 1 `new` shared protocol file + 2 doc-only syncs (`docs/tobe-architecture-io-map.md`, `CHANGELOG.md`) |
| **Primary Requirement** | Prevent TO-BE agents from re-reading legacy source / bulk-reading generated code; force `Read()` of a sub-agent's full spec before every dispatch (closing the gap `specs/013` left open for this orchestrator); replace silent-degrade/bare-hard-stop behavior with a structured escalation report that waits for explicit user approval when a required artifact is missing |
| **Technical Approach** | Additive documentation/prose changes generalizing 3 patterns already proven in this repository (`specs/013`'s Dispatch Protocol, `orchestrator-tobe.md`'s own Gate 0→1 report format, `coder-dotnet.md`'s G-9 guardrail) into one shared, reusable include file — mirrors `specs/010`'s and `specs/013`'s own methodology of extending an existing proven pattern rather than inventing new conventions |
| **Implementation Status** | Complete. Structural verification via grep-based counts (fence balance, reference-presence counts, path-string absence checks) — no code/runtime changes, all edits are prose/Markdown in agent instruction files. |

## Constitution Check

- [x] **Article I** — no technology versions hardcoded.
- [x] **Article II** — frontmatter unchanged except `version`/`date`; 9 files gain a previously-missing `version:` field (collateral fix, not a violation introduced by this PBI).
- [x] **Article IV** — `module.yaml` diff included (§3.4 of spec); 7 missing agent registrations added.
- [x] **Article V** — pt-BR body content preserved/added throughout; the new shared protocol file's body is pt-BR (frontmatter-less header block in English mirrors `governance-apps.md`'s own style, which is bilingual header + pt-BR-agnostic content since it's a cross-cutting include — same treatment applied here).
- [x] **Article VI** — BDD scenarios cover nominal, missing-blocking-artifact, Dispatch Protocol, non-blocking-degrade, and module-registration paths.
- [x] **Article X (SemVer)** — MINOR for `orchestrator-tobe.md` and the 20 agent files (additive guardrail references, no contract-shape change), PATCH for `module.yaml` (pure registration completeness), `1.0.0` for the new shared file.
- [x] No `[NEEDS CLARIFICATION]` markers — 3 scope questions (Dispatch Protocol inclusion, path-bug-fix scope, collateral module/version fixes) resolved via `AskUserQuestion` before implementation began.

## Technical Context

Pure Markdown/prose edits across 22 agent-instruction files + 1 module registry (YAML) + 2 docs.
No new dependencies, no code changes, no schema changes. The new shared file
(`shared/artifact-only-consumption-protocol.md`) follows the exact structural convention of
`shared/governance-apps.md` (versioned header block, `@reference-name` convention, `## ABSOLUTE
INVARIANT` framing) so it slots into the existing include ecosystem without introducing a new
pattern.

## Implementation Phases

### Phase 1 — Shared protocol file ✅ CONCLUÍDO
Created `shared/artifact-only-consumption-protocol.md` in full: §1 (legacy-code-reread
prohibition, with the 3 pre-existing legitimate exceptions preserved) + §2 (escalation
procedure, reusing the existing `[MISSING INPUT:]`/`[FONTE AUSENTE]` vocabulary and generalizing
the Gate 0→1 / `coder-dotnet.md` G-9 report shape into a reusable `⛔ [ARTIFACT GATE FAILED]`
format with Opção A/B/C). Nothing else depends on it structurally, but it had to exist before any
reference could be added elsewhere — done first.

### Phase 2 — Orchestrator hardening ✅ CONCLUÍDO
`orchestrator-tobe.md`: added `## Dispatch Protocol` section (adapted from
`master-orchestrator.md`'s own, lines 201-227, for the `Invocar` idiom); prefixed all 26
dispatch sites (confirmed by direct grep, not assumed) with `⛔ Read(...)`; added the shared
protocol reference near `## Canonical Inputs`; fixed the Fase 4.5 path bug (§4.4); appended a
pointer to the shared escalation format on each existing `HARD STOP` block. Version
`2.3.0` → `2.4.0` (MINOR). This is the highest-leverage single file — the direct root-cause fix
per the historical `specs/013` precedent.

### Phase 3 — `module.yaml` registration ✅ CONCLUÍDO
Diffed `module.yaml`'s `agents:` list against the frontmatter `name:` of every file in
`tobe-architecture/agents/`; added 5 entries confirmed live via `Invocar` grep in
`orchestrator-tobe.md` (`ava-tobe-adr`, `ava-tobe-coexistence-strategy`, `ava-tobe-risk-mitigation`,
`ava-coder-dotnet`, `ava-tobe-designer-system`), plus a 6th (`ava-tobe-user-journeys`) added
despite having no literal `Invocar` line — it's a real dispatched agent per the Agent Team table,
just wired through Fase 7's pre-existing missing-section gap (io-map §4.3, deferred separately);
deliberately excluded `dotnet-nuget-policy.md` (a `shared/`-style include, not a dispatched
agent). Version `1.3.0` → `1.3.1` (PATCH). Ran in parallel with Phase 2 — independent files, no
ordering dependency.

### Phase 4 — Per-agent guardrail wiring (20 files) ✅ CONCLUÍDO
Mechanical, identical pattern per file: added the shared-protocol reference line near each
file's Input Contract/Input Sources section; appended an escalation-format pointer to each
existing blocking-input clause (non-blocking clauses left untouched); introduced
`version: "1.0.0"` on the 9 files that had no `version:` field at all, MINOR-bumped the other 11.
Four files carried a second, distinct change handled with extra care: `risk-mitigation-tobe.md`
(path fix, mirrors Phase 2's §4.4 fix) and `azure-infra-estimator-tobe.md` (path fix, §4.8
partial) were corrected; `test-plan-tobe.md` and `designer-system-tobe.md` had one input each
reclassified from blocking to non-blocking (§4.6, §4.7) since the target files structurally do
not exist anywhere in the pipeline's Output Contracts.

### Phase 5 — Doc sync ✅ CONCLUÍDO
`docs/tobe-architecture-io-map.md`: §3's conclusion extended to state the prohibition is now
*enforced* (not merely observed as absent); §4.4/§4.6/§4.7/§4.8 each got a `**Status**:` note
pointing to this spec. `CHANGELOG.md`: new entry added describing the guardrail + escalation
gate, matching the file's existing entry format.

### Phase 6 — Verification ✅ CONCLUÍDO
See `Test Strategy` below. Grep-based structural checks only (fence balance, reference-count
parity, old-path-string absence) — no live pipeline run possible in this session (these are
prose instruction files consumed by an LLM at dispatch time, not executable code), same
limitation already accepted in `specs/010`'s and `specs/013`'s own verification sections.

## Complexity Tracking

| Item | Status |
|---|---|
| 26 dispatch sites in a single 2000+ line file, each needing an identical but individually-placed prefix | Handled via authoritative grep-then-edit (not a pre-computed line-number list, which would drift) — same discipline `specs/013` used for its 24 sites |
| 20-file mechanical wiring with 4 files carrying a second, distinct change | Delegated as one batch with explicit per-file exception instructions for the 4 non-uniform files, to avoid the uniform-pattern agent accidentally over-generalizing the path/downgrade fixes to files that don't need them |
| Deciding which of 15 known path bugs to fix now vs. defer | Resolved via explicit user confirmation (`AskUserQuestion`) rather than unilaterally expanding or unilaterally minimizing scope — 4 fixed/downgraded, 11 deferred and named individually in Exclusions |
| `designer-system-tobe.md`'s `screen-flow.md` downgrade depends on that file's actual current blocking/non-blocking status, not assumed | Verified by direct read of the file's current state before applying the note in `docs/tobe-architecture-io-map.md` §4.7, rather than asserting an outcome pre-emptively |

## Test Strategy

| Test | Command | Expected Result |
|---|---|---|
| All dispatch sites hardened | `grep -c "⛔ Read("` in `orchestrator-tobe.md` | Equals total `Invocar`/cross-module dispatch site count (26) |
| Shared protocol referenced everywhere | `grep -rl "artifact-only-consumption-protocol" src/modules/ava-fabric-agents/tobe-architecture/agents/` | 21 files (orchestrator + 20 dispatched agents) |
| Old wrong path removed | `grep -rc "outputs/tobe/migration-plan.md"` across `orchestrator-tobe.md` + `risk-mitigation-tobe.md` | 0 / 0 (only the corrected `outputs/tobe/docs/migration-plan.md` remains) |
| Old wrong path removed (azure) | `grep -c "outputs/tobe/sizing-report.md"` (bare, not `docs/`) in `azure-infra-estimator-tobe.md`'s Read Priority list | 0 |
| Downgrades applied | Manual read confirms `test-plan-tobe.md` (`architecture-technical.md`) and `designer-system-tobe.md` (`screen-flow.md`) no longer mark those rows ✅ obrigatório | Confirmed |
| `module.yaml` complete | `grep -c "id: ava-"` before/after in `module.yaml` | 15 → 21 (+6) |
| Version fields introduced | `grep -L "version:"` (files lacking the field) across the 9 previously-versionless files | 0 remaining |
| Fence balance | Per-file markdown code-fence parity check across all 23 touched agent-adjacent files | All balanced |
| No Output Contract field removed | Manual diff review of each touched file's `## Output Contract` section | Unchanged everywhere |

## Rollout Note

Per `spec.md` §8 Assumptions: once live, the new `⛔ [ARTIFACT GATE FAILED]` gate will surface
additional missing-artifact warnings at the 11 deferred path-bug locations (§4.1–4.3, 4.5,
4.9–4.15 of the io-map) that were previously silent. This is expected — it is the visibility the
user explicitly requested — and should not be read as a regression when first observed in a real
run.
