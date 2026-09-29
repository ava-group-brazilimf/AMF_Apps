# Data Model: Agent Pipeline Observability

All shapes below are transcribed directly from `pipeline_observer.py` (the
tool `ava-master-orchestrator` actually calls). `agent_observability.py`
(legacy) uses the same field names but a non-atomic `start`/`end` write
sequence instead of the atomic `track` shown here.

---

## 1. Pipeline Run State — `pipeline-run-state.json`

Path: `projects/{project_name}/outputs/observability/pipeline-run-state.json`
(one file per project, overwritten on each `init`; ephemeral between runs).

```json
{
  "run_id": "9D61EA92",
  "project_name": "Meu-ERP-001",
  "run_type": "full-pipeline",
  "model": "Claude Opus 4.6",
  "start_time": "2026-07-02T14:03:11-03:00",
  "end_time": "2026-07-02T15:02:22-03:00",
  "status": "complete",
  "agents": {
    "ava-asis-orchestrator": { "...": "see §2 below" }
  }
}
```

| Field | Type | Set by | Notes |
|---|---|---|---|
| `run_id` | string (8-char uppercase hex) | `init` | `str(uuid.uuid4())[:8].upper()` |
| `project_name` | string | `init` | e.g. `Meu-ERP-001` |
| `run_type` | string | `init` (`--run-type`, default `full-pipeline`) | inherited by every `track`ed agent's `run_type` field |
| `model` | string | `init` (`--model`, default `Claude Opus 4.6`) | fallback model for agents that don't override it |
| `start_time` | string (BRZ ISO 8601, `-03:00`) | `init` | |
| `end_time` | string \| null | `finalize` | null until finalized |
| `status` | `"running"` \| `"complete"` \| `"partial"` | `init` sets `"running"`; `finalize` derives `"complete"` (all agents completed) or `"partial"` (any failed) | |
| `agents` | object, keyed by agent name | `track` (one entry per call) | see §2 |

---

## 2. Per-Agent Record — `state.agents[agent_name]`

Written atomically by a single `track` call (unlike `agent_observability.py`,
which writes this same shape across two separate `start`/`end` calls).

```json
{
  "phase": "F1",
  "version": "2.18.0",
  "start_time": "2026-07-02T14:03:11-03:00",
  "end_time": "2026-07-02T14:09:25-03:00",
  "duration_ms": 374000,
  "tokens_in": 50000,
  "tokens_out": 30000,
  "tokens_total": 80000,
  "cost_usd": 3.0,
  "status": "completed",
  "model": "Claude Opus 4.6",
  "run_type": "full-pipeline",
  "error_detail": "TOOLCHAIN_UNAVAILABLE"
}
```

| Field | Type | Source |
|---|---|---|
| `phase` | string (`F1`..`F8`) | `--phase`, or auto-filled from `AGENT_CATALOG` lookup by agent name if omitted |
| `version` | string (SemVer) | `--version`, or auto-filled from `AGENT_CATALOG` |
| `start_time` / `end_time` | string (BRZ ISO 8601) | `--start-time`/`--end-time`, or both default to "now" if omitted |
| `duration_ms` | int | `--duration-ms` if supplied, else computed from `start_time`/`end_time` delta |
| `tokens_in` / `tokens_out` | int | `--tokens-in`/`--tokens-out` (LLM-estimated — no automatic token counting) |
| `tokens_total` | int | computed: `tokens_in + tokens_out` |
| `cost_usd` | float, 6 decimals | computed: `round(tokens_in*15/1e6 + tokens_out*75/1e6, 6)` |
| `status` | `"completed"` \| `"failed"` \| `"skipped"` \| `"running"` | `--status`, default `"completed"` |
| `model` | string | `--model`, else the run-level `model` |
| `run_type` | string | inherited from run-level `run_type`, not overridable per agent |
| `error_detail` | string (optional — key only present if non-empty) | `--error-detail` |

---

## 3. Event Log — `agent-events.jsonl`

Path: `projects/{project_name}/outputs/observability/agent-events.jsonl`
(append-only; cleared at the start of each `init`). One JSON object per line.

```json
{"type": "agent_tracked", "run_id": "9D61EA92", "agent": "ava-asis-orchestrator", "phase": "F1", "version": "2.18.0", "status": "completed", "tokens_in": 50000, "tokens_out": 30000, "tokens_total": 80000, "duration_ms": 374000, "cost_usd": 3.0, "model": "Claude Opus 4.6", "timestamp": "2026-07-02T14:09:25-03:00"}
```

`agent_observability.py`'s legacy events use `type: "agent_start"` and
`type: "agent_end"` (two lines per agent) instead of a single
`type: "agent_tracked"` line.

---

## 4. Agent Catalog Entry — `AGENT_CATALOG` (in-code constant, not a file)

54 rows, hardcoded identically in both `pipeline_observer.py` and
`generate_observability_report.py` (see plan.md Complexity Tracking for the
duplication risk):

```python
{"agent": "ava-asis-orchestrator", "phase": "F1", "version": "2.18.0"}
```

Used to auto-fill `phase`/`version` on `track` calls that omit them, and to
render `pending` placeholder rows in `dashboard`/report output for catalog
agents not yet tracked in the current run.

---

## 5. Excel Report — `Agent Metrics` sheet row (the 13-column schema)

Exact header row, verified directly in `pipeline_observer.py`:

| # | Column | Source field |
|---|---|---|
| 1 | Run ID | `state.run_id` (same value on every row) |
| 2 | Data/Hora | `agents[x].start_time` |
| 3 | Agent Name | dict key |
| 4 | Phase | `agents[x].phase` |
| 5 | Versão | `agents[x].version` |
| 6 | Tokens IN | `agents[x].tokens_in` |
| 7 | Tokens OUT | `agents[x].tokens_out` |
| 8 | Tokens Total | `agents[x].tokens_total` |
| 9 | Duration (ms) | `agents[x].duration_ms` |
| 10 | Cost (USD) | `agents[x].cost_usd` |
| 11 | Status | `agents[x].status` (drives row/cell color) |
| 12 | Model | `agents[x].model` |
| 13 | Run Type | `agents[x].run_type` |

A final `TOTAL` row sums columns 6–10 via `=SUM(...)` formulas. Additional
sheets (`Pipeline Summary`, `Phase Breakdown`, `Token Analytics`) aggregate
this same per-agent data — see spec.md §4.1 for their content.
