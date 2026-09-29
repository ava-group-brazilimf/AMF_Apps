# Agent Specification: ava-prototype (modificação)

**Feature Branch**: `023-prototype-optional-artifacts`
**Created**: 2026-07-21
**Status**: Draft
**Change Type**: modify-existing
**Input**: Prototype Agent should support execution with optional artifacts missing

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field        | Value                                                                                                                   |
| ------------ | ----------------------------------------------------------------------------------------------------------------------- |
| **Agent ID** | `ava-prototype`                                                                                                         |
| **Version**  | `1.2.0` (MINOR bump — new mandatory input field + new optional handling + new log outputs)                              |
| **Phase**    | `F3`                                                                                                                    |
| **Module**   | `prototype`                                                                                                             |
| **Role**     | Generates a navigable HTML prototype of the TO-BE solution using available artifacts, never blocking on optional inputs |
| **Skill**    | `ava-prototype`                                                                                                         |
| **Dispatch** | user-facing via SKILL.md \| dispatched by master-orchestrator after F2/TO-BE                                            |

> **Change Type is `modify-existing`**:
>
> - Existing agent file: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`
> - Version bump: MINOR — new mandatory input (`business-rules.md`), optional-input handling, and execution log outputs added; no existing output removed
> - The `module.yaml` entry already exists — Category 4 tasks are N/A
> - The SKILL.md already exists — Category 1.5 is N/A

---

## 2. Agent Frontmatter

The agent `.md` file opens with YAML frontmatter (Constitution Article II):

```yaml
---
name: "ava-prototype"
version: "1.2.0"
description: |
  Gera protótipo HTML navegável da solução TO-BE com UX heurísticas Nielsen-Norman,
  validações de formulário client-side e mensagens de erro amigáveis.
  Utiliza business-rules.md como fonte primária obrigatória; design-system e
  user-journeys são opcionais — ausência exibe aviso e solicita confirmação do
  usuário antes de prosseguir com a geração do protótipo.
  Ativa com: "criar protótipo", "gerar demo", "prototype TO-BE",
  "wireframes navegáveis", "demo sistema migrado".
allowed-tools: Read, Write, Edit
---
```

---

## 3. Output Contract

No new artifact files are added. The existing output contract is preserved. Two new log entries are written to the existing execution log file produced by the agent.

```yaml
## Output Contract
outputs:
  prototype_html: "projects/{project_name}/outputs/tobe/prototype/index.html"
  screen_list: "projects/{project_name}/outputs/tobe/prototype/screen-list.md"
  demo_script: "projects/{project_name}/outputs/tobe/prototype/demo-script.md"
  prototype_gate: "projects/{project_name}/outputs/tobe/prototype/prototype-gate-result.json"
  execution_log_start: "projects/{project_name}/outputs/tobe/prototype/execution-log.json" # appended
  execution_log_end: "projects/{project_name}/outputs/tobe/prototype/execution-log.json" # appended
```

> `execution-log.json` is appended (not a new file per run) — two structured log entries are added: one at agent start and one at agent end, consistent with other observability-enabled agents.

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 - Nominal Path: All Artifacts Present (Priority: P1)

**Story**: Como orquestrador de migração, quero que o ava-prototype execute com sucesso quando todos os artefatos estão presentes, mantendo o comportamento existente.

**Why this priority**: Baseline behavior must not regress.

**Acceptance Scenarios**:

1. **Given** `business-rules.md`, `design-system.md`, and `user-journeys.md` all exist, **When** the agent executes, **Then** pre-flight shows all inputs as ✅ and `DECISION: PROCEED`.
2. **Given** the above, **When** execution completes, **Then** `prototype_gate_result` has `success: true` and `AgentResult.next_agent` is set.
3. **Given** the above, **When** the agent starts, **Then** an entry with `event: "start"` is appended to `execution-log.json`.
4. **Given** the above, **When** the agent finishes, **Then** an entry with `event: "end"` and `status: "success"` is appended to `execution-log.json`.

---

### Scenario 2 - Optional Artifacts Missing (Priority: P1)

**Story**: Como usuário, quero que o protótipo seja gerado mesmo quando design-system.md ou user-journeys.md estão ausentes, recebendo avisos sobre o impacto na qualidade.

**Why this priority**: Core feature of this change — directly addresses the reported blocking behavior.

**Acceptance Scenarios**:

1. **Given** `business-rules.md` exists but `design-system.md` is absent, **When** the agent executes pre-flight, **Then** pre-flight displays `⚠️ design-system.md — OPTIONAL — MISSING`, lists the quality impact, and `DECISION: AWAITING CONFIRMATION`.
2. **Given** `business-rules.md` exists but `user-journeys.md` is absent, **When** the agent executes pre-flight, **Then** pre-flight displays `⚠️ user-journeys.md — OPTIONAL — MISSING`, lists the quality impact, and `DECISION: AWAITING CONFIRMATION`.
3. **Given** `DECISION: AWAITING CONFIRMATION`, **When** the agent displays the prompt, **Then** the user is asked to confirm (`Continue? [yes/no]`) before any output file is written.
4. **Given** the user confirms `yes`, **When** the agent proceeds, **Then** it generates a prototype using only the available artifacts (`business-rules.md` and `bounded-context-map.md` at minimum).
5. **Given** the user responds `no` (or does not confirm), **When** the agent receives the response, **Then** execution is cancelled, no output files are written, `AgentResult.success` is false, and `cancellation_reason: "user declined optional-artifact warning"` is written to `execution-log.json` only — `AgentResult` schema is unchanged.
6. **Given** optional artifacts are missing and the user confirmed, **When** the agent generates the prototype, **Then** the warning section in `screen-list.md` lists each missing optional artifact and the expected quality impact.

---

### Scenario 3 - Mandatory Artifact Missing: BLOCKED (Priority: P1)

**Story**: Como usuário, quero ser claramente informado quando business-rules.md está ausente, pois sem ele o agente não pode gerar o protótipo.

**Why this priority**: Safety gate — must never be silently skipped.

**Acceptance Scenarios**:

1. **Given** `business-rules.md` does not exist at `outputs/asis/docs/business-rules.md`, **When** the agent executes pre-flight, **Then** pre-flight shows `❌ business-rules.md — MANDATORY — MISSING` and `DECISION: BLOCKED`.
2. **Given** the above, **Then** no output files are written and `AgentResult.success` is false.
3. **Given** the above, **Then** the blocked message names the producing agent (`ava-asis-documentation`) as the prerequisite.

---

### Scenario 4 - Execution Logging (Priority: P2)

**Story**: Como engenheiro de observabilidade, quero que o prototype agent emita logs de início e fim de execução consistentes com os demais agentes.

**Why this priority**: Observability standard — tracked by spec `002-agent-pipeline-observability`.

**Acceptance Scenarios**:

1. **Given** any execution path (proceed, proceed-with-warnings, blocked, or cancelled), **When** the agent starts, **Then** a JSON entry `{ "agent": "ava-prototype", "event": "start", "timestamp": "<ISO8601>", "trace_id": "<uuid>" }` is appended to `execution-log.json`.
2. **Given** execution completes on any path, **When** the agent finishes, **Then** a JSON entry `{ "agent": "ava-prototype", "event": "end", "status": "success|warning|blocked|cancelled", "timestamp": "<ISO8601>", "trace_id": "<uuid>" }` is appended to `execution-log.json`.

---

## 5. Quality Gate Requirements

- [x] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) — `ava-prototype` (Article II)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [x] Existing module.yaml entry preserved — Category 4 tasks N/A (Article IV)
- [x] All output paths use lowercase `{project_name}` and correct phase folder `outputs/tobe/prototype/` (Article II)
- [x] BDD scenarios cover nominal, optional-missing, mandatory-missing, and logging paths (Article VI)
- [x] Security sub-pipeline: no impact — change is pre-flight logic only (Article VII)
- [x] No technology versions hardcoded (Article I)
- [x] Skill/Agent split: existing SKILL.md unchanged; only agent `.md` behavior is modified (Article XI)
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency                | Agent ID                                              | Reason                                                           |
| ------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------- |
| AS-IS Documentation       | `ava-asis-documentation`                              | Produces `outputs/asis/docs/business-rules.md` — mandatory input |
| TO-BE Architecture Design | `ava-tobe-architecture-design`                        | Produces `bounded-context-map.md` — mandatory input              |
| TO-BE User Journeys       | `ava-tobe-user-journeys`                              | Produces `user-journeys.md` — optional input                     |
| Design Tokens Propagation | `ava-tobe-architecture-design` (design-system output) | Produces `design-system.md` — optional input                     |

---

## 7. Exclusions

- Changes to the HTML prototype generation logic itself — only pre-flight validation and logging are modified.
- Changes to SKILL.md routing — existing routing is correct.
- Changes to `module.yaml` — the agent is already registered.
- Changes to any other agent's output contract — `business-rules.md` is already produced by `ava-asis-documentation`.

---

## 8. Assumptions

- `outputs/asis/docs/business-rules.md` is consistently produced by `ava-asis-documentation` and its path does not vary by project.
- The existing prototype generation steps that currently read `user-journeys.md` and `design-system.md` will fall back gracefully to `business-rules.md` content when those files are absent.
- `execution-log.json` in the prototype output folder follows the same schema used by other observability-enabled agents (spec `002`).
- `trace_id` is passed in from the orchestrator context and must be threaded through without mutation (Constitution Article VIII).
- The SKILL.md does not need changes since it delegates all input resolution to the agent `.md`.
- When dispatched by `ava-master-orchestrator`, the confirmation prompt will pause the pipeline until the user responds. This is intentional — the orchestrator is not expected to bypass user confirmation for optional-artifact warnings.

---

## Success Criteria

| Criterion                         | Measure                                                                                                                                                     |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No blocking on optional artifacts | A confirmation prompt is shown (not a hard block) when only `design-system.md` or `user-journeys.md` are absent; prototype is generated after user confirms |
| Mandatory gate enforced           | Execution is blocked when `business-rules.md` is absent                                                                                                     |
| Pre-flight clarity                | Pre-flight output distinguishes MANDATORY / OPTIONAL / MISSING for each artifact                                                                            |
| Warning visibility                | Missing optional artifacts are listed with quality impact in `screen-list.md`                                                                               |
| Execution logging                 | `execution-log.json` contains `start` and `end` entries after every run                                                                                     |
| No regression                     | All existing prototype outputs are produced unchanged when all inputs are present                                                                           |
| Contract compliance               | `AgentResult` validates against `agent-result.schema.json`                                                                                                  |
