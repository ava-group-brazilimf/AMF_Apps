# Agent Development Tasks: Agent Self-Observability

**Plan**: `specs/003-agent-self-observability/plan.md`
**Change Type**: bulk modify-existing (96 files) + 1 special-cased agent + 1 new shared doc + 1 tool enhancement
**Status**: Implementation and verification complete as of 2026-07-03 (`/speckit.implement` run). All acceptance scenarios pass. One item remains open by design: Category 5.2 (Article X judgment call) requires a human/team decision, not an automated check.

---

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm `pipeline_observer.py` still compiles after the `cmd_track` extension
  ```bash
  python -m py_compile src/shared/tools/pipeline_observer.py
  ```
  **Result**: OK, no syntax errors.

- [x] **1.2** Confirm `ava-master-orchestrator` frontmatter/Changelog are now consistent
  ```bash
  grep -n '^version' src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
  grep -n '^| 1\.3\.0' src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md
  ```
  **Result**: both show `1.3.0`.

- [x] **1.3** [P] Confirm `observability-self-report.md` exists and is well-formed
  ```bash
  head -10 src/modules/ava-fabric-agents/shared/observability-self-report.md
  ```
  **Result**: header block present (Version/Applies to/Reference-as), well-formed.

---

## Category 2 — Implementation

All real implementation for this PBI is complete. Recorded here for
traceability:

- [x] **2.1** Extend `pipeline_observer.py.cmd_track` with `_sanitize_agent_name`, `_get_agent_dir`, `_write_agent_metrics` — **DONE**, tested end-to-end (see quickstart.md CA03).
- [x] **2.2** Create `src/modules/ava-fabric-agents/shared/observability-self-report.md` — **DONE**.
- [x] **2.3** Update `ava-master-orchestrator.md`: version bump to `1.3.0`, self-reference note, Changelog row — **DONE**.
- [x] **2.4** Batch-insert `> Apply: [@observability-self-report](...)` into 96 agent files — **DONE**, 0 errors.
- [x] **2.5** Update `src/shared/tools/README.md` Data Storage section — **DONE**.
- [x] **2.6** (Incidental, discovered during Category 6 verification) Fix `UnicodeEncodeError` crash in `pipeline_observer.py`/`agent_observability.py` on Windows `cp1252` consoles — **DONE**, minimal UTF-8 `stdout`/`stderr` reconfigure added to both `__main__` blocks.

---

## Category 3 — Shared Schema Updates

**SKIP** — no `agent-task.schema.json`/`agent-result.schema.json` changes; the
new per-agent output is an informal schema documented in `data-model.md`, not
governed by JSON Schema.

---

## Category 4 — Module Registration

**SKIP** — no new agents created; no `module.yaml` changes.

---

## Category 5 — Quality Gate Checklists

- [x] **5.1** Confirm no agent's `name:` field, `description:`, or `allowed-tools:` changed as a side effect of the batch script (only new content was appended, nothing existing was removed except in the one file lacking a trailing newline — see research.md §4)
  ```bash
  git diff --numstat -- src/modules/ava-fabric-agents | awk '$1 > 1 {print}'
  ```
  **Result**: every batch file shows 6-7 pure insertions, 0 deletions, except `bridge-fastqa-asis.md` (1 deletion — benign no-trailing-newline artifact) and `master-orchestrator.md` (expected manual edit). No anomalies.

- [ ] **5.2** [P] Decide on the Article X judgment call (no per-file version bump across 96 files) — **team review, still open**
  See plan.md Constitution Check + Complexity Tracking for the documented reasoning. If the team wants per-file version bumps applied retroactively, this can be done with a follow-up script keyed off each file's own frontmatter `version:` field (MINOR bump, or add `"1.0.0"` if absent). Left unchecked deliberately — this is a human decision, not an automatable verification.

- [x] **5.3** [P] Confirm the 8 security sub-agents are now instrumented (Article VII net-positive check)
  ```bash
  grep -lc "observability-self-report" src/modules/ava-fabric-agents/asis-diagnostic/agents/security/*.md
  ```
  **Result**: all 8 security sub-agent files listed.

---

## Category 6 — Acceptance Validation

Run each quickstart scenario from [quickstart.md](./quickstart.md) and record pass/fail.

- [x] **6.1** **CA01 — Standalone fallback documented** — PASS
- [x] **6.2** [P] **CA02 — Nested-dispatch coverage (8/8 security sub-agents)** — PASS
- [x] **6.3** [P] **CA03 — Per-agent isolation (two agents, two independent folders)** — PASS (verified via a live `init`→`track`×2 run; each agent's `metrics.json` contained only its own data)
- [x] **6.4** [P] **CA04 — Backward compatibility (shared state still updates)** — PASS (`pipeline-run-state.json` contained both tracked agents)
- [x] **6.5** [P] **CA05 — Failure isolation documented** — PASS
- [x] **6.6** [P] **CA06 — Exclusion correctness (4 db-analyzer skills excluded, parent included)** — PASS
- [x] **6.7** **Whole-suite coverage/link-integrity check — expect 97 references, 0 broken** — PASS (97 references, 0 broken)
- [x] **6.8** **Tool-level regression check — Excel still has 4 sheets after the `cmd_track` extension** — PASS (`["Agent Metrics", "Pipeline Summary", "Phase Breakdown", "Token Analytics"]`)

**Incidental fix applied during this verification pass**: `finalize --auto-report`/`dashboard`/`report` were crashing on this Windows environment with `UnicodeEncodeError` (console `cp1252` can't encode the emoji used in status prints) — the underlying files were written correctly, but the CLI exited with a traceback. Fixed with a minimal UTF-8 `stdout`/`stderr` reconfigure in both `pipeline_observer.py` and `agent_observability.py`; re-verified all commands now run cleanly end-to-end.

---

## Category 7 — Documentation & Catalog Update

- [x] **7.1** [P] Update `.github/copilot-instructions.md` SPECKIT block to point at this feature's plan — **DONE** (now points to `specs/003-agent-self-observability/plan.md`; was still pointing at 001, since PBI 002's equivalent task was never actually applied)

- [x] **7.2** [P] Add a `CHANGELOG.md` (repo root) entry for this feature, distinct from the per-agent internal Changelog rows already added — **DONE**, `[2026-07-03]` entry added covering both the tool enhancement and the bulk agent-file rollout

- [x] **7.3** [P] Confirm `docs/agents-catalog.md` doesn't need a new column/note about self-observability — **DONE, confirmed out of scope**: the catalog doesn't reference `@governance-apps` either (the analogous pre-existing cross-cutting doc), confirming it's scoped to per-agent capabilities, not shared governance patches. No edit made.

- [x] **7.4** Cross-reference this spec from `specs/002-agent-pipeline-observability/spec.md`'s §8 Exclusions (which listed "no leaf-agent instrumentation" as future work) — **DONE**, added an "Update 2026-07-03" note there pointing to this PBI

---

## Completion Checklist

- [x] Tool enhancement implemented and tested (Category 2.1)
- [x] Shared governance doc created (Category 2.2)
- [x] Master-orchestrator updated (Category 2.3)
- [x] 96 agent files batch-updated, 0 errors (Category 2.4)
- [x] README updated (Category 2.5)
- [x] All Category 6 acceptance scenarios run and recorded — 8/8 PASS
- [ ] Article X judgment call reviewed by team (Category 5.2) — **still open, requires human decision**
- [x] Documentation cross-references updated (Category 7)
- [x] Incidental Windows console-encoding bug found and fixed during verification (see Category 6 note)

---

## Dependency Graph

```
Category 1 (Verify tool/agent state post-implementation)
    │
    ├─► Category 2 (Implementation — already complete)
    │       │
    │       └─► Category 5 (Gates)       ─┐
    │       └─► Category 6 (Acceptance)  ─┤─► Category 7 (Docs) — all parallel
    │                                     ┘
    └─► [Category 3 SKIP]
    └─► [Category 4 SKIP]
```

## Parallel Execution Opportunities

- **Category 1**: 1.3 parallel with 1.1/1.2
- **Category 5**: 5.2, 5.3 parallel with 5.1
- **Category 6**: 6.2–6.6 all independent and parallel after 6.1
- **Category 7**: all 4 tasks parallel with each other and with Category 6
