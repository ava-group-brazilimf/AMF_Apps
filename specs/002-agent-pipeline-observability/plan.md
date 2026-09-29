# Agent Implementation Plan: Agent Pipeline Observability

**Spec**: `specs/002-agent-pipeline-observability/spec.md`
**Tech Stack**: Pure Python 3.9+ (stdlib) + `openpyxl` for `.xlsx` generation — no framework, no service. See `src/shared/tools/README.md`.

---

## Summary

| Field | Value |
|---|---|
| **Change Type** | `modify-existing` (1 agent, metadata-only) + retrospective documentation (4 utility scripts + README, already implemented) |
| **Phase** | Cross-cutting — spans the entire master pipeline (F1→F2→F3→F5→F7→F6), owned by `ava-master-orchestrator`, not a single phase |
| **Module** | `master-orchestrator` (no `module.yaml` — this module has none) |
| **Primary Requirement** | Retrospectively document the already-shipped deterministic observability system and correct the one metadata gap found while documenting it |
| **Technical Approach** | Tool suite (`pipeline_observer.py` + 3 supporting scripts) is fully implemented and functionally correct. Integration into `ava-master-orchestrator.md` is documented but not inlined into the file's numbered Execution Steps. |
| **Implementation Status** | Tool suite: 100% built. Frontmatter/Changelog version: 1 metadata gap (`1.1.0` vs documented `1.2.0`). Wiring: 2 documented structural gaps — (a) `init`/`track`/`finalize` calls live only in a standalone appendix, not inlined into Steps 0/1–7; (b) only `ava-master-orchestrator`'s own ~21 direct dispatches are reachable by real `track` calls, not the full 54-row `AGENT_CATALOG`. Neither structural gap is remediated by this PBI — both are recorded as follow-up tasks. |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Article I** — No hardcoded tech versions in the agent body; this PBI changes only a version field. The utility scripts hardcode Claude Opus 4.6 pricing constants — Article I's mandate is scoped to agent bodies, not utility scripts, so this is not a violation, but it's flagged honestly in spec.md §9 as a config-driven-ness gap worth future attention. ✅ (with note)
- [x] **Article II** — Frontmatter will contain only `name`/`version`/`description`/`allowed-tools` plus the pre-existing (out-of-scope) `date` field after the version fix. `^ava-[a-z0-9-]+$` pattern unaffected. ✅
- [x] **Article III** — No pipeline sequencing change. `ava-master-orchestrator` remains the sole top-level orchestrator; F1→F2→F3→F5→F7→F6 order untouched. ✅
- [x] **Article IV** — N/A. No `module.yaml` exists under `src/modules/ava-fabric-agents/master-orchestrator/` (confirmed: only an `agents/` subfolder). Nothing to register. ✅
- [~] **Article V** — Agent body language must be pt-BR. All existing section headers in `master-orchestrator.md` are English (established convention), so the new `## ⚙️ Pipeline Observability Integration` header is consistent. However its body prose is English where every other section's body is Portuguese — a genuine, minor inconsistency. **PARTIAL**: documented as an optional PATCH-level fix in `tasks.md` Category 5, not a blocking gate for this PBI.
- [x] **Article VI** — BDD scenarios defined in spec.md §5 (7 scenarios, 10 CA-IDs), covering nominal, edge, negative/gap, and dependency paths. ✅
- [x] **Article VII** — No F1 security sub-pipeline impact; this feature does not touch `ava-asis-security-orchestrator` or any security gate. ✅
- [~] **Article VIII** — This Article literally governs "Observability & Traceability," and this PBI is exactly that feature — so its compliance must be assessed carefully rather than assumed. `trace_id` propagation is untouched (✅, unrelated). "Structured logs use W3C Trace Context correlation IDs (OpenTelemetry)" is **NOT implemented** — the tool is a simpler local JSON/JSONL/Excel pipeline with no OpenTelemetry span/trace correlation and no `trace_id` field in its own schema (see `data-model.md`). **PARTIAL**: this is stated here as a deliberate scope choice of the already-shipped implementation, not something this PBI fixes. Recorded in Complexity Tracking below.
- [x] **Article IX** — N/A. All artifacts are Python utility scripts and LLM instruction `.md` files, not generated Domain/Application/Infrastructure/Presentation code. ✅
- [x] **Article X** — Version bump task (frontmatter `1.1.0` → `1.2.0`, MINOR) is itself the compliance action for the drift found during documentation; no migration notes needed since the behavior was already shipped under the `1.2.0` Changelog entry. ✅ (after Category 2 task applied)
- [x] **Article XI** — No SKILL.md impact; `ava-master-orchestrator` is dispatched directly (top-level entry point), not skill-routed, and this PBI adds no new user-facing agent. ✅

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers in spec.md
- [x] All output paths in spec.md §3 follow `projects/{project_name}/outputs/...` or the shared `docs/optimization/` convention
- [x] Both Article V and Article VIII partial-compliance findings are stated explicitly, not silently marked as passing

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Language/runtime | Python 3.9+ (uses `from __future__ import annotations`) | `pipeline_observer.py` header |
| Excel generation | `openpyxl` (hard dependency, no manifest entry anywhere in repo) | `_generate_xlsx` functions in both tools; import-guarded with a `sys.exit(1)` + install hint |
| Timestamp convention | BRZ (UTC-3), ISO 8601 with explicit `-03:00` offset | `_now_brz()` in both tools |
| Cost model | Hardcoded Claude Opus 4.6 pricing: `$15/1M` input, `$75/1M` output tokens | `COST_PER_TOKEN_IN`/`COST_PER_TOKEN_OUT` constants |
| Lifecycle model | `pipeline_observer.py`: atomic `track` (1 call). `agent_observability.py`: non-atomic `start`+`end` (2 calls, legacy). | Confirmed by reading both `cmd_track` and `cmd_start`/`cmd_end` |
| Storage | State: `projects/{project}/outputs/observability/pipeline-run-state.json` + `agent-events.jsonl`. Reports: `docs/optimization/`. | `_get_data_dir`/`_get_state_file`/`_get_events_file` in both tools |
| Agent catalog | 54 hardcoded rows, duplicated verbatim in `pipeline_observer.py` and `generate_observability_report.py` | Confirmed via grep count |

---

## 2. Phase Placement

Unlike a single-phase feature (e.g. the 001 precedent, scoped to F3), this
integration's *intended* placement spans the entire master pipeline — a
horizontal overlay rather than a single box in the F1→F2→F3→F5→F7→F6 chain:

```
Step 0 (Pre-flight) ────────────────────────────────────────────► Step 7 (Completion Gate)
      │                                                                    │
  [intended: init]                                          [intended: finalize --auto-report]
      │  (documented in appendix only — NOT               │  (documented in appendix only — NOT
      │   present in Step 0's actual 0.1–0.6 body)         │   present in Step 7's actual 7.1–7.5 body)
      ▼                                                                    ▼
  F1 ──► F2 ──► F3 ──► F5 ──► F7 ──► F6
   │      │      │      │      │      │
   └──────┴──────┴──────┴──────┴──────┴── [intended: track after each DISPATCH/AWAIT — not present inline;
                                             master-orchestrator only directly dispatches 4 phase
                                             orchestrators + ~9 F7 agents + ~8 F6 agents itself]
```

This diagram is deliberately captioned with what's *intended* vs. what's
*actually wired* — the tool is fully built and callable, but its invocation
during a real run depends on the executing LLM separately honoring the
`## ⚙️ Pipeline Observability Integration` appendix rather than following
inline step instructions (spec.md §4.5, Scenario 7).

**Quality gates**: none of the pipeline's existing mandatory gates
(`security_gate`, `human_gate_required`, Requestor Inspection, Summary
Validator, etc.) are read, written, or otherwise affected by this feature —
confirmed no new `human_gate_required` occurrences were introduced.

---

## 3. Clean Architecture Alignment

```
Domain         → NO
Application    → NO
Infrastructure → NO
Presentation   → NO
```

**N/A** — all artifacts are LLM instruction files (`.md`) and Python utility
scripts, not generated application code. Clean Architecture governs code
*generated by* the agents (F3 codegen output), not the agents/tools
themselves.

---

## 4. Agent File Structure

No new files created by this PBI (all already exist); one metadata edit
proposed for Category 2:

```
src/modules/ava-fabric-agents/master-orchestrator/agents/
└── master-orchestrator.md        (872 lines; frontmatter 1.1.0 → 1.2.0 — metadata fix only, body unchanged)

src/shared/tools/
├── pipeline_observer.py             (primary tool — 8 commands, 54-row AGENT_CATALOG, 4-sheet xlsx with chart)
├── agent_observability.py           (legacy tool — 6 commands, non-atomic start/end, 3-sheet xlsx)
├── generate_observability_report.py (export/baseline report generator — uses legacy 3-sheet exporter)
├── _populate_pipeline_agents.py     (placeholder-fill helper for demo/report completeness)
└── README.md                        (usage docs for both tools)
```

**Dispatch mode**: `ava-master-orchestrator` is invoked directly (top-level
pipeline entry point) — not skill-routed. Utility scripts are invoked via
`Bash: python src/shared/tools/pipeline_observer.py ...`, matching the
existing pattern used for `build_summary_comprehensive.py` and `ntp_time.py`
elsewhere in the same agent file.

---

## 5. module.yaml Impact

**None.** Confirmed: no `module.yaml` file exists anywhere under
`src/modules/ava-fabric-agents/master-orchestrator/`. This module has no
module-level registry — `ava-master-orchestrator` is the pipeline's top-level
entry point, dispatched directly rather than through a phase module registry.

---

## 6. Observability & Trace Propagation

`trace_id` propagation elsewhere in the pipeline is unaffected by this
feature. The new observability schema (state JSON, events JSONL, Excel
columns — see `data-model.md`) does **not** itself carry a `trace_id` field;
token/cost/duration tracking and the pipeline's own trace-correlation
mechanism are currently two unlinked systems. This is stated once here as an
honest characterization (see Constitution Check Article VIII above and
spec.md §8 Exclusions) rather than repeated at length.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | NO | Observability metrics are collected outside the AgentTask/AgentResult contract entirely |
| `agent-result.schema.json` | NO | No new fields added to AgentResult; metrics live in separate state/event files |
| Observability state/event schema (informal, not JSON-Schema-governed) | N/A — already exists | See `data-model.md` for the full shape |

---

## 8. Implementation Phases

### Phase 0 — Research ✅ CONCLUÍDO

See [research.md](./research.md). All 5 utility/doc components and the
`ava-master-orchestrator.md` integration text already exist and function
correctly. Two independent code read-throughs (direct + background agent,
cross-validated) converged on the same findings. Remaining items are
metadata/documentation only:
1. Frontmatter version bump (`1.1.0` → `1.2.0`).
2. Decision on backfilling the formal `## Output Contract` block with the 5 observability paths (deferred, optional — see spec.md §8).
3. Decision on the Article V English-body-prose item (deferred, optional).
4. Honest capture of the two structural gaps (appendix-only wiring, leaf-agent tracking) as accepted limitations for this PBI, candidates for a future PBI.

**There is no "build the tool" phase — it is already built.**

### Phase 1 — Metadata Correction

#### Task 1.1 — Bump `ava-master-orchestrator.md` frontmatter version

**File**: `src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md`
**Change**: `version: "1.1.0"` → `version: "1.2.0"` (line 3).
**Criterio de aceite**: `grep -n '^version' master-orchestrator.md` shows `1.2.0`, matching the existing Changelog entry at line 870.

### Phase 2 — Verification

See [quickstart.md](./quickstart.md) for the full validation command set —
runs the tool end-to-end against `Meu-ERP-001` and checks structural claims
(4 sheets, 13-column header, cost arithmetic, failed-status handling,
import-json validation, compare) plus the negative check confirming Step
0/Step 7 do not contain inline `track` calls today.

### Phase 3 — Documentation

Update `.github/copilot-instructions.md`'s `<!-- SPECKIT START -->` block to
point at this plan; confirm `docs/agents-catalog.md`'s scope decision;
confirm/add a `CHANGELOG.md` (repo root) entry — see `tasks.md` Category 7.

---

## 9. Complexity Tracking

| Violation/Gap | Why It Exists | Mitigating Notes / Simpler Alternative Rejected Because |
|---|---|---|
| `AGENT_CATALOG` duplicated (54 rows) in both `pipeline_observer.py` and `generate_observability_report.py` | Two scripts built independently, no shared module extracted | LOW RISK today (both lists currently in sync); drift risk grows if agents are added/removed from the pipeline without updating both files. Recommend a future PBI extract a shared `agent_catalog.py`, not attempted here to keep this PBI documentation-scoped. |
| Article VIII partial compliance (no OpenTelemetry/trace_id) | Simpler local-file tool was the deliberate implementation choice for this iteration | MEDIUM — documented, not remediated. A future PBI could add `trace_id` to the observability schema and/or emit OpenTelemetry spans if APM-grade tracing becomes a requirement. |
| Appendix-only wiring (Step 0.4b/track/7.0b not inlined) | Integration was documented as a reference appendix rather than edited into the numbered steps | MEDIUM — documented, not remediated per user decision (see PBI scope decision: "document only"). Candidate follow-up: inline the 3 call sites into Steps 0, 1–6, and 7. |
| Article V English body-prose in the new appendix section | Section was likely drafted directly in English during implementation, inconsistent with the rest of the file's Portuguese body convention | LOW — cosmetic, optional PATCH-level fix, not blocking. |

---

## 10. Test Strategy

| Test Type | Comando / Abordagem | Cenário (spec sec. 5) | CA |
|---|---|---|---|
| End-to-end run + sheet structure | `init` → `track` (2–3 agents) → `finalize --auto-report`; `python -c "from openpyxl import load_workbook; print(load_workbook('...').sheetnames)"` | Nominal full-pipeline run | CA01/CA02/CA03 |
| Failed-agent tracking | `track --status failed --error-detail "..."`; inspect `status` JSON via `pipeline_observer.py status` | Failed agent still tracked | CA04/CA05 |
| Cost arithmetic | Hand-compute `tokens_in*15/1e6 + tokens_out*75/1e6` and diff against tool output | Cost calculation correctness | CA06 |
| Dashboard pre-finalize | `dashboard` invoked before `finalize` | On-demand dashboard | CA07 |
| Import-json happy + malformed | `import-json --input <valid.json>` then `--input <invalid.json>` (missing `agents` key) | Import migration path | CA08 |
| Compare two runs | `compare --run-a <path1> --run-b <path2>` against two existing `docs/optimization/*.json` samples | Compare two runs | CA09 |
| Negative: inline wiring absence | `grep -n "0.4b\|7.0b" master-orchestrator.md` restricted to the Step 0/Step 7 code blocks — expect **no matches** | Known gap — leaf/inline tracking | CA10 |
