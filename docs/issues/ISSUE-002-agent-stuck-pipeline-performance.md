# ISSUE-002 — Agent Stuck / Excessive Subagent Dispatch (processaERP-008)

**Date**: 2026-07-29
**Project**: processaERP-008
**Severity**: HIGH
**Status**: ROOT CAUSE IDENTIFIED — Mitigation documented below
**Reported by**: Rafael Almeida (PM)

---

## 1. Symptom

During the AS-IS F1 pipeline run for `processaERP-008`, the `ava-asis-orchestrator` triggered
excessive subagent (`runSubagent`) dispatches and the pipeline ran for **~110 minutes** wall time
without completing the full F1 output contract. Eight (8) mandatory F1 artifacts were never
produced.

**Observed behaviour:**

- The pipeline completed the Delphi AST extraction successfully (4m 15s — normal).
- After extraction, the orchestrator dispatched multiple `runSubagent → Explore` calls to inline
  execute individual agents (solution-delphi, inventory, etc.).
- Three subagent calls consumed **2062s (~34 min)**, **319s (~5 min)**, and **3700s (~62 min)**
  respectively before the pipeline stalled entirely.
- Total wall time from first file to last: **110.6 minutes** with only 52 files created.
- The pipeline stopped after writing `complexity-map.md` at 18:24:55 — no further artifacts.

---

## 2. Timeline Evidence

Reconstructed from file system `mtime` + debug session logs:

| Clock    | +Min   | Event                                          |
| -------- | ------ | ---------------------------------------------- |
| 16:30:11 | 0:00   | AST extraction starts (363 .pas files)         |
| 16:34:25 | 4:14   | Extraction + Headroom compression complete     |
| 16:34:25 | 0:00   | **GAP #1 starts — 35 min idle**         |
| 17:09:26 | 35:01  | `bounded-context-map.md` written             |
| 17:10:42 | 36:17  | `architecture-blueprint.md` written          |
| 17:11:56 | 37:31  | `vcl-lifecycle-map.md` written               |
| 17:12:54 | 38:29  | `api-map.md` written                         |
| 17:14:07 | 39:52  | `data-structure.md` written                  |
| 17:15:31 | 41:06  | `migration-readiness.md` written             |
| 17:15:31 | 0:00   | **GAP #2 starts — 30 min idle**         |
| 17:45:57 | 71:32  | `form-registry.json` written (events agent)  |
| 17:47:12 | 72:47  | `events-pubsub-inventory.md` written         |
| 17:49:54 | 75:29  | `events-pubsub-risks.md` written             |
| 17:49:54 | 0:00   | **GAP #3 starts — 35 min idle**         |
| 18:24:55 | 110:30 | Batch: inventory, diagrams, complexity written |
| 18:24:55 | -      | **Pipeline stops** — no further output  |

### Debug Session Log Evidence

From session `28421c8d` (20:17→20:40, the ava-asis-orchestrator parent):

| Event | Time     | Duration         | Call                                                  |
| ----- | -------- | ---------------- | ----------------------------------------------------- |
| 253   | 20:27:09 | **777.8s** | `runSubagent → Explore` (ava-asis-solution-delphi) |
| 242   | 20:26:37 | 2.9s             | `runSubagent → Explore` (failed fast — error)     |
| 236   | 20:26:21 | ~0s              | `runSubagent → Explore` (immediate return)         |

From session `518fc3d8` (16:23→00:54, the main orchestration session):

| Event | Time     | Duration                    | Call                       |
| ----- | -------- | --------------------------- | -------------------------- |
| 378   | 16:42:14 | **2062.8s (~34 min)** | `runSubagent → default` |
| 390   | 17:17:31 | **319.4s (~5 min)**   | `runSubagent → default` |
| 449   | 17:26:36 | **3700.9s (~62 min)** | `runSubagent → default` |

The longest subagent call (3700s = **61.7 minutes**) corresponds precisely to the last GAP #3
and explains why the pipeline appeared stuck. The subagent ran the full ava-asis-solution-delphi
spec internally, processing 761,376 compressed tokens across 9 artifact files.

---

## 3. Root Cause Analysis

### RC-1 — Context Window Overload (PRIMARY)

**The Delphi AST compressed output for processaERP-008 is 761,376 tokens.**

The `ava-asis-solution-delphi` agent loads the full compressed artifacts into context before
generating each artifact. For a 363-unit, 174,375 LOC system with 4,254 business rules and
8,454 procedures, the payload is at the limit of what a single LLM context window can hold.

| Artifact               | Raw tokens          | Compressed        | Reduction        |
| ---------------------- | ------------------- | ----------------- | ---------------- |
| 01_business_rules      | 273,126             | 128,743           | -52.9%           |
| 05_procedures          | 662,447             | 426,984           | -35.5%           |
| 04_database_schemas    | 141,453             | 112,753           | -20.3%           |
| 02_form_business_rules | 77,080              | 65,918            | -14.5%           |
| **TOTAL**        | **1,194,239** | **761,376** | **-36.2%** |

When a `runSubagent` call carries this entire payload as prompt context PLUS the agent spec PLUS
tool results, the model must process 800,000+ tokens per turn. This causes:

- **Multi-minute inference latency per turn** (observed: 34–62 min for each subagent)
- **Repeated context reconstruction** — each subagent restart re-reads the same AST files
- **Diminishing returns** — each restart increases context load without gaining new knowledge

### RC-2 — Subagent Retry Loop (SECONDARY)

The orchestrator dispatched `runSubagent → Explore` **3 times in 16 seconds** (20:26:21,
20:26:37, 20:27:09) for the same `ava-asis-solution-delphi` agent. This suggests:

- The first two calls returned early/failed silently
- The orchestrator did not detect the failure, retried immediately
- The third call succeeded but ran for 777 seconds

This retry-without-backoff pattern multiplied the total inference cost by 3× for one agent.

### RC-3 — No Parallelism Gate (SECONDARY)

Agents that could run in parallel (inventory, db-analyzer, documentation) were dispatched
**sequentially** via the subagent mechanism. The 3 large subagent calls ran one after another:

- 16:42 → 17:16 (34 min subagent 1)
- 17:17 → 17:22 (5 min subagent 2)
- 17:26 → 19:26 (62 min subagent 3 — still running after session "stalled")

### RC-4 — Missing F1 Artifacts at Pipeline Exit

The pipeline stopped after writing `complexity-map.md` at 18:24:55 with these 8 F1 artifacts
still missing:

| Missing Artifact                    | Agent Responsible      |
| ----------------------------------- | ---------------------- |
| `master-report.md`                | ava-asis-orchestrator  |
| `gaps-risks-report.md`            | ava-asis-gaps-risks    |
| `docs/functional-requirements.md` | ava-asis-documentation |
| `docs/business-rules.md`          | ava-asis-documentation |
| `docs/screen-navigation-map.md`   | ava-asis-documentation |
| `db/schema-inventory.md`          | ava-asis-db-analyzer   |
| `db/er-diagram.mmd`               | ava-asis-db-analyzer   |
| `db/stored-procedures-map.md`     | ava-asis-db-analyzer   |

The last subagent (3700s) likely completed but the parent session lost the continuation context
after the 62-minute call returned — the orchestrator did not resume writing remaining artifacts.

---

## 4. Performance Metrics

| Metric                                 | Value                   |
| -------------------------------------- | ----------------------- |
| Total wall time                        | 110.6 min               |
| AST extraction                         | 4m 14s (normal)         |
| Headroom compression                   | ~7s                     |
| Subagent 1 (solution-delphi artifacts) | ~35 min (GAP#1)         |
| Subagent 2 (inventory/events)          | ~30 min (GAP#2)         |
| Subagent 3 (diagrams/complexity)       | ~35 min (GAP#3)         |
| Total compressed token payload         | 761,376 tokens          |
| F1 artifacts completed                 | 11 / 19 (58%)           |
| Missing F1 artifacts                   | 8 (42%)                 |
| Subagent retry storms                  | 3 retries in 16s (RC-2) |
| Longest single subagent call           | 3,700s (~62 min)        |

---

## 5. Mitigation Strategies

### M-1 — Artifact-Level Context Slicing (RECOMMENDED)

Instead of loading ALL 9 compressed artifacts into every `runSubagent` call, each agent should
only receive the artifacts it actually needs:

| Agent                    | Artifacts Needed            | ~Token Budget |
| ------------------------ | --------------------------- | ------------- |
| ava-asis-solution-delphi | 01, 02, 08 (+ scope filter) | ~200K         |
| ava-asis-db-analyzer     | 03, 04, 05                  | ~560K         |
| ava-asis-documentation   | 01, 02, 08                  | ~200K         |
| ava-asis-inventory       | 08 only                     | ~7K           |

This reduces per-subagent context by 60–90%.

### M-2 — Inline Execution for Large Systems

For systems with >500K compressed tokens, fall back from `runSubagent` dispatch to **inline
execution** (read agent spec → execute steps directly without subagent overhead). This avoids
the context reconstruction penalty on each subagent restart.

Threshold trigger: if `compressed/metrics.jsonl total_tokens > 400000` → use inline mode.

### M-3 — BC-Scoped Execution

For the largest agents (solution-delphi, db-analyzer), dispatch **one subagent per bounded
context** instead of one global subagent. With 16 BCs and ~47K tokens avg/BC, each call
stays under 100K tokens.

Requires: pass `scope_filter` (list of units per BC from `module-partition.json`) to each call.

### M-4 — Retry Guard

Before dispatching a `runSubagent`, check if the expected output files already exist. If yes,
skip. This prevents the retry-without-backoff storm (RC-2).

```python
# Pseudo-code for orchestrator guard
if not output_file_exists(expected_artifact):
    runSubagent(agent, prompt)
else:
    log(f"Skipping {agent} — output already present")
```

### M-5 — Parallel Dispatch (Future)

Agents with no shared input dependencies (inventory, documentation, db-analyzer) can be
dispatched in parallel. Current sequential dispatch serializes 3× of cost.

---

## 6. Recommended Immediate Actions

1. **Resume processaERP-008** using inline execution for the 8 missing artifacts.
   Reference: `processaERP-005` inline fallback documented in repo memory.
2. **Add extraction threshold check** to `ava-asis-orchestrator.md`:

   ```
   IF total_compressed_tokens > 400,000:
     SET execution_mode = "inline"
   ELSE:
     SET execution_mode = "subagent"
   ```
3. **Add artifact existence gate** before each subagent dispatch in the orchestrator.
4. **Document as known pattern** for large Delphi repos (>200 units / >100K LOC).

---

## 7. References

| Artifact                                           | Location                                                                             |
| -------------------------------------------------- | ------------------------------------------------------------------------------------ |
| AST extraction log                                 | `projects/processaERP-008/outputs/asis/delphi-ast-raw/run_delphi_ast_analysis.log` |
| Compression metrics                                | `projects/processaERP-008/outputs/asis/delphi-ast-raw/compressed/metrics.jsonl`    |
| Session log (orchestrator)                         | debug-logs/28421c8d-9397-47c2-933d-9455a0e6006c                                      |
| Session log (main pipeline)                        | debug-logs/518fc3d8-1ffe-4044-af5b-b2e052dd9a4c                                      |
| Performance analysis script                        | `tmp_perf_analyze.py` (repo root)                                                  |
| Prior inline execution precedent                   | MeuERP-007 notes in`/memories/repo/ava-fabric-asis-pipeline.md`                    |
| processaERP-005 reference (successful full F1 run) | `/memories/repo/ava-fabric-asis-pipeline.md` — "Successful full SA                |

---

## 8. Performance Benchmark Script

See `docs/issues/perf_pipeline_ntp.py` — NTP-style performance measurement script that:

- Computes wall-time per phase from file `mtime`
- Identifies gaps (subagent idle periods)
- Reports token budget per artifact
- Flags systems exceeding the 400K threshold

Run with:

```bash
python docs/issues/perf_pipeline_ntp.py --project processaERP-008
```
