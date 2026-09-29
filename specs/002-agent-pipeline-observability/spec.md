# Agent Specification: Agent Pipeline Observability

**Feature Branch**: `002-agent-pipeline-observability`
**Created**: 2026-07-03
**Status**: Draft
**Change Type**: modify-existing (metadata only) + retrospective documentation of already-shipped utilities
**Input**: Agent description: "Observability Agents — coletar métricas de execução (Run ID, Data/Hora, Agent Name, Phase, Versão, Tokens IN/OUT/Total, Duration, Cost, Status, Model, Run Type) do master-orchestrator e de cada agente da esteira, exportando para Excel em docs/optimization/, com uma tool determinística em src/shared/tools/."

> **Language note**: This spec is a planning document written in **English**.
> The feature it documents is **already implemented**: `ava-master-orchestrator`'s
> body and the `src/shared/tools/` scripts are done. No new agent body prose is
> being authored by this PBI — see §8 Exclusions for what is explicitly not
> being changed here.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

This PBI documents **one existing agent** (metadata-only change) and **five
existing utility/doc files** (already implemented, zero new code proposed):

| Component | Type | File | Version Bump |
|---|---|---|---|
| `ava-master-orchestrator` | Existing agent | `src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md` | **MINOR — frontmatter `1.1.0` → `1.2.0`** (metadata correction only; see §4.5) |
| `pipeline_observer.py` | Utility script — primary/recommended tool | `src/shared/tools/pipeline_observer.py` | N/A (not versioned) |
| `agent_observability.py` | Utility script — legacy/low-level tool | `src/shared/tools/agent_observability.py` | N/A |
| `generate_observability_report.py` | Utility script — standalone report generator | `src/shared/tools/generate_observability_report.py` | N/A |
| `_populate_pipeline_agents.py` | Utility script — placeholder-fill helper | `src/shared/tools/_populate_pipeline_agents.py` | N/A |
| `src/shared/tools/README.md` | Documentation | `src/shared/tools/README.md` | N/A |

> Because the only agent touched is `ava-master-orchestrator` and the change
> is a version-field correction (not new behavior), Category 4 tasks (module
> registration) and SKILL.md creation are N/A — `ava-master-orchestrator` has
> no `module.yaml` (confirmed: no such file exists under
> `src/modules/ava-fabric-agents/master-orchestrator/`) and is dispatched
> directly, not via skill routing.

---

## 2. Agent Frontmatter Changes

### `ava-master-orchestrator` — version bump only

```yaml
---
name: ava-master-orchestrator
version: "1.2.0"   # was "1.1.0" — MINOR bump correcting drift: the agent's own
                   # Changelog table (line 870) already documents a 1.2.0 entry
                   # dated 2026-07-02 for this exact observability integration,
                   # but the frontmatter version field was never updated to match.
date: 2026-06-12   # pre-existing field, not one of Article II's 4 allowed
                   # frontmatter keys (name/version/description/allowed-tools).
                   # Pre-existing drift, out of scope for this PBI.
description: |
  Orquestra a esteira completa AVA Fabric end-to-end, coordenando todas as fases
  em sequência: F1 AS-IS → F2 TO-BE → F3 Stack → F5 QA → F7 DevOps → F6 Deliverables.
  Cada fase conclui com geração de Summary HTML antes de avançar.
  Ativa com: "executar pipeline completo", "iniciar esteira completa", "full pipeline",
  "run full avafabric pipeline", "master orchestrator".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite
---
```

`description` and `allowed-tools` are unchanged — this is a pure version-field
correction, not a behavior or contract change.

---

## 3. Output Contract

The observability tooling writes 5 file types, none of which currently appear
in `ava-master-orchestrator.md`'s own formal `## Output Contract` block
(lines 232–253) — they are documented only in the separate
`## ⚙️ Pipeline Observability Integration` appendix (lines 812–863). This spec
records the paths as the de-facto contract and flags the backfill as an
optional, PATCH-level follow-up (see §8 Exclusions and `tasks.md` Category 2).

```yaml
## Output Contract (observability — documented in appendix today, not yet in the formal block)
outputs:
  observability_state:  "projects/{project_name}/outputs/observability/pipeline-run-state.json"
  observability_events: "projects/{project_name}/outputs/observability/agent-events.jsonl"
  observability_xlsx:   "docs/optimization/agent-observability-{project_name}-{run_id}.xlsx"
  observability_json:   "docs/optimization/agent-observability-{project_name}-{run_id}.json"
  observability_md:     "docs/optimization/observability-report-{project_name}-{run_id}.md"
```

Note the split root: per-run *state* lives under the project's own output tree
(`projects/{project_name}/outputs/observability/`, ephemeral/regenerated each
`init`), while *reports* land in the shared, cross-project
`docs/optimization/` directory keyed by `{project_name}-{run_id}`.

---

## 4. Functional Changes by Component

### 4.1 `pipeline_observer.py` — primary tool (already implemented)

Deterministic CLI, stdlib + `openpyxl`, no other dependencies. Commands:
`init`, `track` (atomic — combines start+end in one call), `finalize
[--auto-report]`, `dashboard`, `report --format {all|xlsx|json|md}`,
`import-json --input <path>`, `compare --run-a <path> --run-b <path>`,
`status`.

- Embeds a hardcoded `AGENT_CATALOG` of **54 agent/phase/version rows**
  spanning F1→F2→F3→F5→F7→F6→F8, used by `track` to auto-fill `--phase`/
  `--version` when the caller omits them, and by `dashboard`/report
  generation to show `pending` rows for agents not yet tracked.
- Cost model: hardcoded constants `COST_PER_TOKEN_IN = $15 / 1,000,000`,
  `COST_PER_TOKEN_OUT = $75 / 1,000,000` (Claude Opus 4.6 reference pricing).
  Not read from any project config — see §9 Assumptions.
- All timestamps in BRZ (UTC-3), ISO 8601 with explicit `-03:00` offset.
- `_generate_xlsx` (verified directly in code) produces **exactly 4 sheets**:
  `Agent Metrics` (13-column schema below + TOTAL row with `SUM()` formulas +
  status-based row coloring), `Pipeline Summary` (run-level key/value totals),
  `Phase Breakdown` (per-phase aggregation **with an embedded `BarChart`** —
  "Cost per Phase (USD)" — when more than one phase is present), and
  `Token Analytics` (per-agent token/cost share ranked by `tokens_total`).
- `track --status failed --error-detail "..."` is a first-class path — failed
  agents are still recorded with duration/tokens/cost and a red-filled status
  cell, not dropped from the report.

### 4.2 `agent_observability.py` — legacy tool (already implemented)

Same state/event file locations as `pipeline_observer.py`, but a
**non-atomic** two-call lifecycle (`start` then a separate `end`, rather than
one `track` call). Its own `_export_xlsx` produces **3 sheets** (`Agent
Metrics`, `Pipeline Summary`, `Phase Breakdown` — no `Token Analytics` sheet,
no chart). Explicitly labeled "Legacy" in `README.md`, which recommends
`pipeline_observer.py` for new integrations. This 3-vs-4-sheet difference is
two tools' independent export functions, not an inconsistency to reconcile
(see `research.md`).

### 4.3 `generate_observability_report.py` — standalone report generator

Two modes: `export` (reads an existing `pipeline-run-state.json` and renders
reports from it) and `baseline` (pre-populates all 54 `AGENT_CATALOG` rows as
`status: pending` and generates a report immediately, for planning/demo
purposes before any real run has started). Imports its Excel writer from
`agent_observability.py` (the legacy exporter), so **baseline/export-mode
reports produced by this script are 3-sheet**, not 4-sheet like
`pipeline_observer.py`'s own reports.

### 4.4 `_populate_pipeline_agents.py` — placeholder-fill helper

Back-fills any `AGENT_CATALOG` agent not yet present in a run's state: F1
agents get `status: failed` (reason: "blocked: legacy repository not found"),
downstream-phase agents get `status: skipped` (reason: "F1 blocked"). This
produces demo-quality placeholder rows for reporting completeness — it does
not represent real execution and must not be read as evidence that those
agents were actually tracked.

### 4.5 `ava-master-orchestrator.md` — integration (already implemented, with a documented wiring gap)

The `## ⚙️ Pipeline Observability Integration` section (lines 812–863)
documents three intended integration points:

1. **Step 0.4b — INIT OBSERVABILITY**: `pipeline_observer.py init --run-type full-pipeline --model "Claude Opus 4.6"`
2. **After each agent — TRACK AGENT**: `pipeline_observer.py track --agent {name} --phase {phase} --version {version} --status {…} --tokens-in {…} --tokens-out {…} --duration-ms {…}`
3. **Step 7.0b — FINALIZE OBSERVABILITY**: `pipeline_observer.py finalize --auto-report`

**Verified directly against the file's actual numbered steps**: `### Step 0 —
Pre-flight` runs `0.1`–`0.6` with no `0.4b`; `### Step 7 — Pipeline
Completion Gate` runs `7.1`–`7.5` with no `7.0b`; none of the DISPATCH/AWAIT
cycles in Steps 1–6 (F1 through F6) contain a `track` call. **The integration
is documented in a standalone appendix section but is not inlined into the
literal numbered steps an executing LLM follows.** The tool itself is fully
built and correct; whether a given pipeline run actually emits `init`/`track`/
`finalize` calls depends on the executing agent separately honoring the
appendix, not on step-level instructions. This is recorded as a known
limitation, not fixed by this PBI (see §8 Exclusions, `tasks.md` Category 5).

A second, related consequence: `ava-master-orchestrator` itself only directly
`DISPATCH`es 4 phase orchestrators (`ava-asis-orchestrator`,
`ava-tobe-orchestrator`, `ava-stack-orchestrator`, `ava-qa-orchestrator`) plus
~9 F7 agents and ~8 F6 agents directly — it never dispatches F1/F2/F3/F5 leaf
agents (e.g. `ava-asis-solution-delphi`, `ava-tobe-adr`,
`ava-qa-scenario-generator`) itself; those are dispatched *inside* the phase
orchestrator `.md` files. A repo-wide grep confirms **no phase-orchestrator or
leaf-agent file references `pipeline_observer` or `agent_observability`** —
only `master-orchestrator.md` does. So even with the wiring gap above closed,
granular tracking of ~35 of the 54 catalog rows (the F1/F2/F3/F5 leaf agents)
would still require separately instrumenting the phase orchestrators — out of
scope for this PBI (see §8 Exclusions).

---

## 5. User Scenarios (Given-When-Then)

### Scenario 1 — Nominal Full-Pipeline Run Produces a 4-Sheet Excel (CA01, CA02, CA03)

**Story**: Como responsável pela esteira AVA Fabric, quero que uma execução completa do pipeline gere um relatório Excel com métricas por agente, para que eu possa auditar custo e desempenho após cada rodada.

**Acceptance Scenarios**:

1. **Given** `pipeline_observer.py init -p Meu-ERP-001` has been called, **When** one or more agents are recorded via `track`, **Then** `projects/Meu-ERP-001/outputs/observability/pipeline-run-state.json` contains a `run_id`, `start_time`, and an `agents` dict with one entry per tracked agent.
2. **Given** the above, **When** `finalize --auto-report` is called, **Then** `docs/optimization/agent-observability-Meu-ERP-001-{run_id}.xlsx` exists with sheet names exactly `["Agent Metrics", "Pipeline Summary", "Phase Breakdown", "Token Analytics"]`.
3. **Given** the same run, **When** the `Agent Metrics` sheet is inspected, **Then** its header row is exactly `Run ID, Data/Hora, Agent Name, Phase, Versão, Tokens IN, Tokens OUT, Tokens Total, Duration (ms), Cost (USD), Status, Model, Run Type` and a `TOTAL` row sums Tokens IN/OUT/Total/Duration/Cost.

### Scenario 2 — Failed Agent Is Still Tracked (CA04, CA05)

**Story**: Como responsável pela esteira, quero que falhas de agentes apareçam no relatório de observabilidade, para que eu não perca visibilidade de onde o pipeline quebrou.

**Acceptance Scenarios**:

1. **Given** `track --agent ava-stack-build-validator --status failed --error-detail "TOOLCHAIN_UNAVAILABLE"`, **When** the state is saved, **Then** the agent's record has `status: "failed"` and the error detail is preserved.
2. **Given** the above, **When** the Excel report is generated, **Then** that agent's row in `Agent Metrics` is filled with the failed-status color and still contributes its tokens/cost/duration to the `TOTAL` row.

### Scenario 3 — Cost Calculation Correctness (CA06)

**Story**: Como responsável financeiro pelo projeto, quero que o custo em USD seja calculado de forma determinística e auditável, para confiar no relatório sem recalcular manualmente.

**Acceptance Scenarios**:

1. **Given** `--tokens-in 50000 --tokens-out 30000`, **When** `track` computes cost, **Then** `cost_usd == round(50000 * 15/1_000_000 + 30000 * 75/1_000_000, 6)` exactly (`= 3.0`).
2. **Given** `--tokens-in 0 --tokens-out 0` (e.g. a `skipped` agent), **Then** `cost_usd == 0.0` and the agent still appears in the report.

### Scenario 4 — On-Demand Dashboard Before Finalization (CA07)

**Story**: Como acompanhante de uma execução em andamento, quero ver o progresso do pipeline sem esperar sua conclusão, para identificar bloqueios cedo.

**Acceptance Scenarios**:

1. **Given** a run has been `init`ed and partially `track`ed (not yet `finalize`d), **When** `dashboard` is invoked, **Then** it prints a progress view showing tracked agents by status and untracked `AGENT_CATALOG` entries as `pending`, without requiring `finalize` first.

### Scenario 5 — Import From External JSON (CA08)

**Story**: Como responsável por migrar dados de observabilidade de outra fonte, quero importar um snapshot JSON externo, para reaproveitar métricas já coletadas.

**Acceptance Scenarios**:

1. **Given** a valid JSON file containing both `run_id` and `agents` keys, **When** `import-json --input <path>` runs, **Then** the state is overwritten and a summary (`imported`, `run_id`, `agents` count, `completed` count) is printed.
2. **Given** a JSON file missing either `run_id` or `agents`, **When** `import-json` runs, **Then** it exits with code 1 and prints `"ERROR: Invalid JSON structure. Expected 'run_id' and 'agents' keys."`.

### Scenario 6 — Compare Two Runs (CA09)

**Story**: Como responsável por otimização de custo, quero comparar duas execuções lado a lado, para medir o efeito de mudanças no pipeline.

**Acceptance Scenarios**:

1. **Given** two existing state JSON files (e.g. two runs of the same project), **When** `compare --run-a <path> --run-b <path>` runs, **Then** it prints per-metric totals for both runs and highlights per-agent cost deltas.

### Scenario 7 — Known Gap: Leaf-Agent Tracking Is Not Emitted (CA10, negative scenario — documents a limitation, not a passing guarantee)

**Story**: Como auditor do pipeline, preciso saber exatamente quais agentes são realmente rastreados hoje, para não superestimar a cobertura do relatório de observabilidade.

**Acceptance Scenarios**:

1. **Given** a full pipeline run executed by `ava-master-orchestrator`, **When** F1's leaf agents (e.g. `ava-asis-solution-delphi`, run inside `ava-asis-orchestrator`) execute, **Then** **no `track` call is emitted for them** — confirmed by the absence of any `pipeline_observer`/`agent_observability` reference in any phase-orchestrator or leaf-agent `.md` file.
2. **Given** the same run, **When** `ava-master-orchestrator`'s own Step 0/Step 7 bodies are inspected, **Then** no `init`/`track`/`finalize` call appears inline (only in the separate appendix section) — so even master-orchestrator-level tracking depends on the executing LLM separately following the appendix rather than the numbered steps.

---

## 6. Quality Gate Requirements

- [x] Agent ID follows `ava-{phase}-{role}` pattern — `ava-master-orchestrator` unchanged (Article II)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (plus pre-existing, out-of-scope `date` field) (Article II)
- [ ] N/A — Module registration (Article IV): no `module.yaml` exists for master-orchestrator; nothing to register
- [x] Output paths use lowercase `{project_name}` and correct conventions (Article II) — verified in §3
- [x] BDD scenarios cover nominal, edge, negative/gap, and dependency paths (Article VI) — §5, 7 scenarios
- [x] Security sub-pipeline impact assessed (Article VII) — none; this feature does not touch F1 security orchestration
- [x] No technology versions hardcoded in agent body — N/A, this PBI changes only a version field (Article I); the utility scripts (not agent bodies, so Article I's agent-scoped mandate is not directly binding) do hardcode Opus 4.6 pricing — flagged honestly in §9 Assumptions, not silently accepted as compliant
- [~] **Article VIII (Observability & Traceability) — PARTIALLY ADDRESSED.** The article requires `trace_id` propagation (unaffected, unrelated to this feature) and "structured logs use W3C Trace Context correlation IDs (OpenTelemetry)". This feature implements a simpler deterministic local JSON/JSONL/Excel pipeline with **no OpenTelemetry span/trace correlation and no `trace_id` field anywhere in its schema** (see `data-model.md`). This is a documented, deliberate scope choice — not a claim of full Article VIII compliance.
- [~] **Article V (pt-BR agent body) — minor gap.** All other section headers in `master-orchestrator.md` are English by established house convention (`Execution Pipeline`, `Agent Team`, `Guardrails`, etc.), so the new section's English *header* is consistent. However, its *body prose* ("Deterministic observability tool for tracking agent execution metrics during the pipeline. Called by the master-orchestrator...") is English, where every other section's body prose is Portuguese. Flagged as an optional PATCH-level fix in `tasks.md` Category 5, not required to close this PBI.
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 7. Dependencies

| Dependency | Component | Reason |
|---|---|---|
| `openpyxl` (Python package) | `pipeline_observer.py`, `agent_observability.py`, `generate_observability_report.py` | Required for `.xlsx` generation; guarded with a runtime `ImportError` message, but **not declared in any manifest** anywhere in the repo (no `requirements.txt`/`pyproject.toml` exists for this tool) |
| Python 3.9+ | All 4 scripts | `pipeline_observer.py` uses `from __future__ import annotations` and modern type hints |
| `ava-master-orchestrator` → `pipeline_observer.py` | Agent integration | The agent must call `init` before `track`, and `track` before `finalize`; `pipeline_observer.py` enforces this via `_load_state` returning `{}` and commands erroring if no active run exists |

---

## 8. Exclusions

- **No changes to any F1/F2/F3/F5/F6/F7 phase-orchestrator or leaf-agent `.md` files** — instrumentation remains `ava-master-orchestrator`-only by design; extending tracking to leaf agents is a candidate future PBI, not part of this one.
  > **Update 2026-07-03**: this gap is now closed by `specs/003-agent-self-observability/`, which instruments 97 of 101 agent files (including nested dispatch chains this PBI could not reach in principle) via a self-reporting model rather than caller-side tracking.
- **No OpenTelemetry / W3C Trace Context / Azure Monitor / Application Insights wiring** — this is a simpler deterministic local-file tool, not an APM integration. Do not confuse this with `ava-devops-monitoring-observability` (an unrelated, pre-existing F7 DevOps agent that generates **application-level** monitoring artifacts — Azure Monitor alerts, App Insights dashboards, KQL queries — for the client's *modernized target system*, not for the AVA pipeline's own execution metrics).
- **No `trace_id` field** in the observability schema (state JSON, events JSONL, Excel columns) — cost/token/timing tracking is currently unlinked from the pipeline's own `trace_id` propagation mechanism.
- **No inlining of Step 0.4b/track/7.0b into the literal numbered Execution Steps** — documented as a known limitation in §4.5, not remediated by this PBI.
- **No decision to add `ava-master-orchestrator` to `docs/agents-catalog.md`** — confirmed the catalog has zero references to it today and is scoped to phase agents (F1–F8) only; this PBI treats that as intentional scope, not an oversight to fix.
- **No dependency manifest created** for `openpyxl` — flagged as a gap (§7) but not remediated here (would require deciding on a repo-wide Python dependency management approach, out of scope).

---

## 9. Assumptions

- `Meu-ERP-001` is the real on-disk sample project with existing generated artifacts under `docs/optimization/`; `Meu-ERP` (no numeric suffix) does not exist and must not be used in examples.
- `projects/{project_name}/outputs/observability/` is ephemeral and regenerated per run (events file is cleared on every `init`) — its absence between runs is expected, not a defect.
- Claude Opus 4.6 pricing ($15/1M input, $75/1M output tokens) is hardcoded as a point-in-time reference and will require a manual code edit in `pipeline_observer.py` (and separately in `agent_observability.py`) if pricing changes or a different model is used for a run.
- Token counts passed to `track --tokens-in/--tokens-out` are estimates supplied by the calling agent — no automatic token counting is implemented by the tool itself.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Excel report structure | Generated `.xlsx` has exactly 4 sheets: Agent Metrics, Pipeline Summary, Phase Breakdown (with chart), Token Analytics |
| Metrics schema compliance | `Agent Metrics` header row matches the 13 required columns exactly, in order |
| Cost arithmetic verified | `cost_usd` matches hand-computed value for a known tokens-in/out pair |
| Failed-agent visibility | `track --status failed` agents appear in reports with correct color and non-zero totals where applicable |
| Frontmatter/Changelog consistency | `ava-master-orchestrator.md` frontmatter `version` reads `1.2.0`, matching its own Changelog entry |
| Honest gap documentation | spec.md/plan.md explicitly state the appendix-only wiring gap and the leaf-agent tracking gap rather than claiming full closure |
| Scope clarity | `docs/agents-catalog.md` scope decision recorded; distinction from `ava-devops-monitoring-observability` documented |
