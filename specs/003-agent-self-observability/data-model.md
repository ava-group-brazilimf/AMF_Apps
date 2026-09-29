# Data Model: Agent Self-Observability

This PBI adds one new output shape (per-agent files) and does not change the
shapes documented in `specs/002-agent-pipeline-observability/data-model.md`
(shared `pipeline-run-state.json`, `agent-events.jsonl`, Excel schema,
`AGENT_CATALOG`) — those remain exactly as before and continue to be written
by the same `track` call.

---

## 1. Per-Agent Metrics Snapshot — `outputs/observability/{agent_name}/metrics.json`

Path: `projects/{project_name}/outputs/observability/{sanitized_agent_name}/metrics.json`
(one file per agent per project; **overwritten** on each `track` call for that
agent — it always reflects the agent's most recent run, not a history).

```json
{
  "run_id": "ECDDDA43",
  "agent": "ava-asis-solution-delphi",
  "phase": "F1",
  "version": "1.4.0",
  "start_time": "2026-07-03T17:30:57-03:00",
  "end_time": "2026-07-03T17:30:57-03:00",
  "duration_ms": 45000,
  "tokens_in": 12000,
  "tokens_out": 8000,
  "tokens_total": 20000,
  "cost_usd": 0.78,
  "status": "completed",
  "model": "Claude Opus 4.6",
  "run_type": "standalone"
}
```

| Field | Type | Notes |
|---|---:|---|
| `run_id` | string | Added by `_write_agent_metrics`; identifies which pipeline run produced this snapshot |
| `agent` | string | Added by `_write_agent_metrics`; redundant with the folder name, kept for self-containment |
| all other fields | — | Identical shape to the shared state's per-agent record (`specs/002/data-model.md` §2) — same fields, same source |

## 2. Per-Agent Event Log — `outputs/observability/{agent_name}/events.jsonl`

Path: `projects/{project_name}/outputs/observability/{sanitized_agent_name}/events.jsonl`
(append-only — unlike `metrics.json`, this accumulates one line per `track`
call for that agent across multiple runs/re-invocations, since it is never
cleared).

Each line has the exact same shape as `metrics.json` above (the same payload
object is both written as the snapshot and appended as an event line).

## 3. Directory Naming — `_sanitize_agent_name`

Agent names are sanitized before being used as directory names: any character
that is not alphanumeric, `-`, or `_` is replaced with `-`. In practice, every
current agent `name:` value (`ava-{phase}-{role}` pattern, lowercase-hyphenated)
already passes through unchanged — sanitization exists defensively for names
that might otherwise contain characters unsafe for filesystem paths.

## 4. Relationship to the Shared Aggregate State

```
projects/{project_name}/outputs/observability/
├── pipeline-run-state.json          ← unchanged from PBI 002 (shared, one per project)
├── agent-events.jsonl               ← unchanged from PBI 002 (shared, one per project)
├── {agent_name_1}/
│   ├── metrics.json                 ← NEW (this PBI) — self-contained, this agent only
│   └── events.jsonl                 ← NEW (this PBI) — self-contained, this agent only
├── {agent_name_2}/
│   ├── metrics.json
│   └── events.jsonl
└── ...
```

Both layers are written by the **same** `track` call — there is no separate
"self-report" command; the existing `track` command was extended so any
caller (orchestrator-side tracking from PBI 002, or an agent's own
self-reporting per this PBI) gets both outputs for free.
