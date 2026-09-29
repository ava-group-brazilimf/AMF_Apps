# Quickstart: Validating Prototype Optional Artifacts

**Feature**: 023-prototype-optional-artifacts
**Date**: 2026-07-21

---

## Prerequisites

- A project folder exists at `projects/{project_name}/`
- `ava-asis-documentation` has run and produced `outputs/asis/docs/business-rules.md`
- `ava-tobe-architecture-design` has run and produced `outputs/tobe/docs/bounded-context-map.md`

---

## Scenario A — All Artifacts Present (Nominal)

**Setup**: Ensure all six input artifacts exist under `projects/{project_name}/outputs/`:

- `asis/docs/business-rules.md`
- `tobe/docs/bounded-context-map.md`
- `tobe/docs/design-system.md`
- `tobe/docs/user-journeys.md`

**Run**: Invoke `@ava-prototype` (or trigger via `@ava-master-orchestrator`).

**Expected outcome**:

1. Pre-flight table shows all items as `✅` and `DECISION: PROCEED`.
2. `outputs/tobe/prototype/index.html` is created.
3. `outputs/tobe/prototype/screen-list.md` has no `## Warnings` section.
4. `outputs/tobe/prototype/execution-log.json` contains two entries: `event: "start"` and `event: "end"` with `status: "success"`.

---

## Scenario B — Optional Artifact Missing, User Confirms

**Setup**: Remove or omit `outputs/tobe/docs/design-system.md` (leave others present).

**Run**: Invoke `@ava-prototype`.

**Expected outcome**:

1. Pre-flight table shows `⚠️ design-system.md — OPTIONAL — MISSING` and `DECISION: AWAITING CONFIRMATION`.
2. Quality impact message is displayed: "Sem design-system.md, o protótipo utilizará tokens de design genéricos…"
3. Agent prompts `Continue? [yes/no]`.
4. After user types `yes`: prototype is generated.
5. `outputs/tobe/prototype/screen-list.md` contains a `## Warnings` section listing `design-system.md` and its impact.
6. `execution-log.json` end entry has `status: "warning"` and `missing_optional: ["outputs/tobe/docs/design-system.md"]`.

---

## Scenario C — Optional Artifact Missing, User Cancels

**Setup**: Same as Scenario B (design-system.md absent).

**Run**: Invoke `@ava-prototype`. When prompted `Continue? [yes/no]`, respond `no`.

**Expected outcome**:

1. No output files are written (no `index.html`, no `screen-list.md`).
2. `execution-log.json` end entry has `status: "cancelled"` and `cancellation_reason: "user declined optional-artifact warning"`.

---

## Scenario D — Mandatory Artifact Missing (BLOCKED)

**Setup**: Delete or omit `outputs/asis/docs/business-rules.md`.

**Run**: Invoke `@ava-prototype`.

**Expected outcome**:

1. Pre-flight table shows `❌ business-rules.md — MANDATORY — MISSING` and `DECISION: BLOCKED`.
2. Error message names `ava-asis-documentation` as the agent that must run first.
3. No prototype output files are written.
4. `execution-log.json` end entry has `status: "blocked"`.

---

## Verifying the Execution Log

After any run, check the log:

```bash
# Check the log entries exist
cat projects/{project_name}/outputs/tobe/prototype/execution-log.json
```

Expected structure (two entries minimum per run):

```json
[
  {"agent":"ava-prototype","event":"start","status":null,...},
  {"agent":"ava-prototype","event":"end","status":"success|warning|blocked|cancelled",...}
]
```

See [data-model.md](data-model.md#2-execution-log-entry-schema) for the full schema.
