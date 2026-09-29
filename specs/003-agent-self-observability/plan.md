# Agent Implementation Plan: Agent Self-Observability

**Spec**: `specs/003-agent-self-observability/spec.md`
**Tech Stack**: Same as `specs/002-agent-pipeline-observability` — Python 3.9+ (stdlib) + `openpyxl`. This PBI additionally touches 97 Markdown agent-instruction files.

---

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (bulk — 96 agent files + 1 special-cased) + new shared doc + tool enhancement |
| **Phase** | Cross-cutting — applies to every phase (F1–F8) plus `prototype` and `master-orchestrator` |
| **Module** | All modules — this is a repo-wide governance-style rollout, analogous to `@governance-apps` |
| **Primary Requirement** | Each agent self-reports its own execution metrics via `pipeline_observer.py track`, writing to its own `outputs/observability/{agent_name}/` folder, independent of who dispatched it |
| **Technical Approach** | Extend `pipeline_observer.py.cmd_track` to also write a per-agent snapshot (backward compatible); introduce one new shared governance doc; batch-insert a one-line "Apply" reference into 96 agent files via a script, plus a manual, more substantial edit to `master-orchestrator.md` |
| **Implementation Status** | **Complete.** Tool change implemented and tested end-to-end. Shared doc written. 96/96 files successfully modified by the batch script (0 errors). `master-orchestrator.md` manually updated (version bump + self-reference + Changelog row). All 97 relative-path references verified to resolve correctly. |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Article I** — No hardcoded tech versions introduced. ✅
- [x] **Article II** — Frontmatter unaffected in 96/97 files. `ava-master-orchestrator`'s frontmatter still has only its 4 allowed keys (+ pre-existing `date`). ✅
- [x] **Article III** — No pipeline sequencing change; F1→F2→F3→F5→F7→F6 order untouched. ✅
- [x] **Article IV** — N/A, no new agents, no module.yaml changes. ✅
- [x] **Article V** — New shared doc and all 97 inserted references are Portuguese-prose/established-syntax, consistent with the rest of each file's body language. ✅
- [x] **Article VI** — BDD scenarios in spec.md §5 (6 scenarios, 6 CA-IDs) cover standalone invocation, nested dispatch, isolation, backward compatibility, failure isolation, and correct exclusion. ✅
- [x] **Article VII** — Net positive: security sub-agents (previously zero observability coverage at any level) now self-report. No negative impact on the security gate itself. ✅
- [~] **Article VIII** — Materially improves coverage (97/101 vs ~21/101 agents previously reachable) but does **not** add OpenTelemetry/W3C Trace Context — that sub-requirement remains open from PBI 002, not addressed here either. **PARTIAL, explicitly not fully closed by this PBI.**
- [x] **Article IX** — N/A, no generated application code touched. ✅
- [~] **Article X** — `ava-master-orchestrator` version bump applied (`1.3.0`) with a Changelog row. The other 96 files did **not** receive a version bump — see spec.md §9 for the explicit reasoning (treated as a governance-doc rollout, mirroring the un-versioned rollout of `@governance-apps`). This is a **documented judgment call**, not an oversight — flagged for team review in `tasks.md`.
- [x] **Article XI** — No new user-facing agents; no SKILL.md impact. ✅

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers in spec.md
- [x] All new output paths (`outputs/observability/{agent_name}/`) follow the `projects/{project_name}/outputs/...` convention
- [x] The Article X judgment call (no per-file version bump) is stated explicitly, not silently assumed compliant

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Tool change | `pipeline_observer.py.cmd_track` extended with 3 new helper functions + 1 call site | Verified: compiles cleanly, tested end-to-end (`init` → `track` → per-agent `metrics.json`/`events.jsonl` produced correctly) |
| Rollout mechanism | One new shared governance doc (`observability-self-report.md`) + a one-line `> Apply: [...]` reference per agent file | Mirrors the pre-existing `@governance-apps` convention (79/101 files already used this pattern for i18n) |
| Batch-edit method | A Python script (not 96 individual manual edits) inserting the reference at the best available anchor per file | Anchor priority: before `## i18n` (majority of files) → before `## Changelog` (fallback) → end of file (final fallback) |
| Verification | Programmatic check that all 97 relative paths resolve to the actual shared file | Ran post-insertion: 97/97 resolve, 0 broken |
| Excluded files | 4 `db-analyzer/skills/*.md` — inlined, not independently dispatched | Confirmed via PBI 002/003 research: these are selected inline by `db-analyzer.md`, not DISPATCH/AWAIT targets |

---

## 2. Phase Placement

Unlike PBI 002 (cross-cutting but centered on one caller,
`master-orchestrator`), this PBI's placement is **every phase, every agent,
independent of caller**:

```
F1 ──► F2 ──► F3 ──► F5 ──► F7 ──► F6
 │      │      │      │      │      │
 ▼      ▼      ▼      ▼      ▼      ▼
[every agent in every phase now applies @observability-self-report
 and calls `track` on itself immediately before its own completion signal —
 regardless of whether it was dispatched by a phase orchestrator,
 by ava-master-orchestrator, or invoked standalone by a human]
```

This closes PBI 002's Scenario 7/CA10 gap for the ~35 leaf agents that were
previously unreachable by any `track` call, and additionally covers nested
dispatch chains (e.g. security sub-agents dispatched by
`ava-asis-security-orchestrator`, itself dispatched by `ava-asis-orchestrator`)
that PBI 002 could not reach even in principle, since caller-side tracking
only ever covers direct dispatches.

**Quality gates**: unaffected — no existing gate reads or writes observability
state; this remains true after this PBI.

---

## 3. Clean Architecture Alignment

```
Domain         → NO
Application    → NO
Infrastructure → NO
Presentation   → NO
```

**N/A** — all artifacts are LLM instruction files and one Python utility
script, not generated application code.

---

## 4. Agent File Structure

```
src/modules/ava-fabric-agents/shared/
└── observability-self-report.md        (NEW — governance doc, styled after governance-apps.md)

src/modules/ava-fabric-agents/master-orchestrator/agents/
└── master-orchestrator.md               (v1.1.0 → v1.3.0 — self-reference + Changelog row)

src/modules/ava-fabric-agents/{asis-diagnostic,tobe-architecture,tech-stack,qa-agents,devops-agents,deliverables,summary,prototype}/agents/**/*.md
└── 96 files — one-line `> Apply: [@observability-self-report](...)` inserted each, no frontmatter change

src/shared/tools/
├── pipeline_observer.py                 (cmd_track extended: _sanitize_agent_name, _get_agent_dir, _write_agent_metrics)
└── README.md                            (Data Storage section updated)
```

**Excluded** (unchanged): `asis-diagnostic/agents/db-analyzer/skills/{mariadb,mysql,oracle,sqlserver}-agent.md`.

---

## 5. module.yaml Impact

**None.** No new agents were created; no module registries changed.

---

## 6. Observability & Trace Propagation

This PBI *is* the observability feature — `trace_id` propagation elsewhere is
unaffected. The self-reported schema still does not carry `trace_id` (same
gap as PBI 002, unresolved here). Stated once, not repeated (see Constitution
Check Article VIII).

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | NO | Unaffected |
| `agent-result.schema.json` | NO | Unaffected |
| Observability per-agent schema (informal) | **YES — new** | `metrics.json`/`events.jsonl` per agent folder — see `data-model.md` |

---

## 8. Implementation Phases

### Phase 0 — Research ✅ CONCLUÍDO

See [research.md](./research.md). Investigated file-structure consistency
across all 101 agent files before designing the batch-edit strategy — found
no single universal anchor (only 79/101 have `## i18n`), designed a
3-tier fallback anchor strategy accordingly.

### Phase 1 — Tool Enhancement ✅ CONCLUÍDO

`pipeline_observer.py.cmd_track` extended (see spec.md §4.1). Verified by
direct execution: `init` → `track --agent ava-asis-solution-delphi ...` →
confirmed `outputs/observability/ava-asis-solution-delphi/metrics.json` and
`events.jsonl` created with correct content, alongside the pre-existing
shared state file.

### Phase 2 — Shared Governance Doc ✅ CONCLUÍDO

`observability-self-report.md` written, styled after `governance-apps.md`.

### Phase 3 — Master-Orchestrator Update ✅ CONCLUÍDO

Frontmatter version corrected (`1.1.0` → `1.3.0`), self-reference added,
Changelog row added.

### Phase 4 — Batch Rollout ✅ CONCLUÍDO

Script processed 101 candidate files: 96 modified successfully (0 errors), 5
excluded (4 db-analyzer skills + master-orchestrator, handled separately in
Phase 3). Post-run verification: 97/97 inserted relative-path references
resolve to the actual shared file.

### Phase 5 — Verification

See [quickstart.md](./quickstart.md) and `tasks.md` Category 6.

---

## 9. Complexity Tracking

| Violation/Gap | Why It Exists | Mitigating Notes |
|---|---|---|
| No per-file version bump across 96 files (Article X judgment call) | Treated as a governance-doc rollout, mirroring `@governance-apps`'s un-versioned application | Documented explicitly in spec.md §9, not hidden. Recommend team confirms this precedent is still desired; if not, a follow-up PBI can bump all 96 versions mechanically (the same batch-script technique would apply). |
| Article VIII still partial (no OpenTelemetry/trace_id) | Out of scope, inherited from PBI 002 | Unchanged risk profile; not worsened by this PBI. |
| 4 excluded files' dispatch status for the 3 "policy" docs (`database-policy-tobe.md`, `dotnet-nuget-policy.md`, `database-design-tobe.md`) was ambiguous during research | Confirmed via grep that all 3 ARE invoked by their orchestrators (`Invocar {file}.md com trigger ...`), so they were included, not excluded | LOW RISK — if a future audit shows these are pure reference docs never independently executed, their self-report instruction simply never fires; no functional harm either way. |
| Anchor-insertion fallback (end-of-file) used for ~40% of files lacking `## i18n` | No universal terminal section exists across all 101 files | Verified structurally sound in every case (matching brace/heading counts, no truncation) — see `quickstart.md` CA-verification commands. |

---

## 10. Test Strategy

| Test Type | Comando / Abordagem | Cenário (spec sec. 5) | CA |
|---|---|---|---|
| Standalone fallback | `track` without prior `init` → confirm fallback `init --run-type standalone` guidance is followed (manual read-through of the shared doc §2) | Standalone invocation | CA01 |
| Nested-dispatch coverage | `grep -l observability-self-report src/modules/ava-fabric-agents/asis-diagnostic/agents/security/*.md` | Nested dispatch chain | CA02 |
| Per-agent isolation | `track` two different agents in one run; diff their two `outputs/observability/{agent}/metrics.json` files | Isolation | CA03 |
| Backward compatibility | Re-run a `master-orchestrator`-style `track` call unchanged; confirm shared state file still updates as before | Backward compatibility | CA04 |
| Failure isolation | Read `observability-self-report.md` §3 — confirm explicit "never block" language present | Failure isolation | CA05 |
| Exclusion correctness | `grep -L observability-self-report src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/skills/*.md` (expect all 4 listed = none contain it) | Exclusion correctness | CA06 |
| Global coverage/link integrity | Programmatic check: every `observability-self-report]\(...\)` reference across all 101 files resolves to the real shared file | Coverage — supports Success Criteria | (whole-suite check) |
