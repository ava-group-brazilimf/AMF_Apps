# Agent Implementation Plan: ava-prototype (modificação)

**Spec**: `specs/023-prototype-optional-artifacts/spec.md`
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` (v1.0.0) — do not hardcode versions.

---

## Summary

| Field                   | Value                                                                                                                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent ID**            | `ava-prototype`                                                                                                                                                                                         |
| **Phase**               | `F3`                                                                                                                                                                                                    |
| **Module**              | `prototype`                                                                                                                                                                                             |
| **Primary Requirement** | Reclassificar design-system.md e user-journeys.md como opcionais; adicionar business-rules.md como entrada obrigatória primária; exibir prompt de confirmação quando artefatos opcionais estão ausentes |
| **Technical Approach**  | Modificar seção de pre-flight e leitura obrigatória do `prototype-agent.md` para usar tabela canônica, adicionar lógica de confirmação e gerar entradas no `execution-log.json`                         |

---

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Justify gate failures in Complexity Tracking (section 9)._

### Constitution Gates

- [x] **Article I** — No technology versions hardcoded in agent body
- [x] **Article II** — Frontmatter contains ONLY: `name`, `version`, `description` (Portuguese + activation phrases), `allowed-tools`
- [x] **Article II** — agent `name` matches pattern `^ava-[a-z0-9-]+$` → `ava-prototype` ✅
- [x] **Article III** — Phase placement valid: F3 dispatched by master-orchestrator after F2; ava-summary runs after F3
- [x] **Article IV** — module.yaml already contains `ava-prototype`; version field will be bumped (see section 5)
- [x] **Article V** — Agent body language is Brazilian Portuguese (existing body preserved; new sections written in Portuguese)
- [x] **Article VI** — BDD scenarios in spec section 4: Scenario 1 (nominal), Scenario 2 (optional missing + confirm/cancel), Scenario 3 (mandatory missing), Scenario 4 (logging) ✅
- [x] **Article VII** — Security sub-pipeline: no impact — change is pre-flight instruction logic only
- [x] **Article VIII** — trace_id: read from AgentTask, written to both log entries unchanged (see section 6)
- [x] **Article IX** — N/A: `ava-prototype` is an LLM prompt `.md` file, not generated code
- [x] **Article X** — Version bump: MINOR (`1.1.0 → 1.2.0`) — new mandatory input added, optional handling added, log output added; no existing output removed
- [x] **Article XI** — SKILL.md at `.github/skills/ava-prototype/SKILL.md` already exists and is unchanged; only `agents/prototype-agent.md` is modified

### Quality Gate Check

- [x] No [NEEDS CLARIFICATION] markers remain in spec
- [x] All outputs follow `projects/{project_name}/outputs/tobe/prototype/…`
- [x] Downstream `next_agent`: `ava-prototype` emits `next_agent: ava-summary` — confirmed to exist

**GATE DECISION: PROCEED**

---

## 1. Technical Context

| Dimension                  | Choice                                                  | Source                                       |
| -------------------------- | ------------------------------------------------------- | -------------------------------------------- |
| Agent file type            | LLM prompt Markdown (.md)                               | Existing pattern                             |
| Pre-flight format          | Canonical `╔═══╗` table (see data-model.md §1)          | Established by spec 002 + constitution       |
| Log format                 | JSON array append-mode (see data-model.md §2)           | Research R2                                  |
| Confirmation prompt        | Hard pause, user types `yes/no`                         | Spec §4 Scenario 2; user decision 2026-07-21 |
| Fallback: no design-system | Inline CSS custom properties already in agent body      | Research R5                                  |
| Fallback: no user-journeys | Derive screens from business-rules.md sections + BC map | Research R6                                  |
| CHANGELOG entry            | Required (MINOR bump)                                   | Constitution Article X + Research R7         |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

Master pipeline sequence (F3 dispatched directly by master-orchestrator):

```
F2 (ava-tobe-orchestrator) → ava-summary
                           → [THIS AGENT: ava-prototype] → ava-summary
                           → F4 (ava-stack-orchestrator)
```

This agent's position:

```
F2 Orchestrator → emits next_agent: ava-prototype
F3 → ava-prototype (THIS AGENT)
   → emits next_agent: ava-summary
F3 done → ava-summary (invoked by master-orchestrator after F3 completes)
```

**Quality gate at this phase**: `summary-validator` (after F3 completes). No security gate triggered by this change.

Conditions for `human_gate_required: true`:

- Not applicable to this modification; human_gate logic in the agent is unchanged.

---

## 3. Clean Architecture Alignment

```
Domain         -> NO  — agent is an LLM prompt file
Application    -> NO  — agent is an LLM prompt file
Infrastructure -> NO  — agent is an LLM prompt file
Presentation   -> NO  — agent is an LLM prompt file
```

**N/A** — `ava-prototype` is an LLM prompt `.md` instruction file, not generated application code.

---

## 4. Agent File Structure

Skill/Agent two-layer split (Constitution Article XI):

```
.github/skills/ava-prototype/
└── SKILL.md                          ← UNCHANGED (routing wrapper)

src/modules/ava-fabric-agents/prototype/agents/
└── prototype-agent.md                ← MODIFIED (pre-flight + log sections)
```

**Dispatch mode**: user-facing (SKILL.md required) — already exists and is unchanged.

**Shared resources**: agent-task.schema.json | agent-result.schema.json

---

## 5. module.yaml Impact

Agent is already registered. Only the module version field is bumped:

```
src/modules/ava-fabric-agents/prototype/module.yaml
```

Diff to apply:

```diff
-version: "1.1.0"
+version: "1.2.0"
```

The top-level `module.yaml` at the repo root does **not** need updating (no new phase/module created).

---

## 6. Observability & Trace Propagation

```
Input: AgentTask.trace_id
  → copied unchanged to both log entries:
    execution-log.json[start].trace_id
    execution-log.json[end].trace_id
Output: AgentResult.trace_id = AgentTask.trace_id (unchanged)
```

Log file: `projects/{project_name}/outputs/tobe/prototype/execution-log.json`
Schema: see [data-model.md](data-model.md#2-execution-log-entry-schema)

---

## 7. Schema Changes

| Schema                   | Change Required | Description                                                                                               |
| ------------------------ | --------------- | --------------------------------------------------------------------------------------------------------- |
| agent-task.schema.json   | NO              | No new input fields required                                                                              |
| agent-result.schema.json | NO              | `missing_optional` and `cancellation_reason` are written to `execution-log.json`, not to AgentResult JSON |

---

## 8. Implementation Phases

**Phase 0 — Frontmatter Update**

- File: `src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`
- Change `version: "1.1.0"` → `version: "1.2.0"`
- Update `description` to state that design-system and user-journeys are optional and that a confirmation prompt is shown when absent

**Phase 1 — Pre-flight Section Replacement**

- File: `prototype-agent.md` → section `## Pre-Execução — Leitura Obrigatória`
- Replace current `★`/`○` list with canonical pre-flight table + decision logic from [data-model.md §1](data-model.md#1-pre-flight-validation-table)
- Add quality impact messages from [data-model.md §3](data-model.md#3-quality-impact-messages)
- Add fallback behaviour prose for absent optional artifacts (Research R5 and R6)
- Add confirmation prompt instruction (`Continue? [yes/no]`) and both outcomes

**Phase 2 — Execution Logging**

- File: `prototype-agent.md` — add new section `## Registro de Execução`
- Start entry written before any file I/O; end entry written after all outputs or after blocked/cancelled decision
- Schema from [data-model.md §2](data-model.md#2-execution-log-entry-schema)
- Append-mode: create file if absent, otherwise append before closing `]`

**Phase 3 — screen-list.md Warnings Section**

- File: `prototype-agent.md` — update instruction for screen-list generation
- When optional artifacts were absent and user confirmed: prepend `## Warnings` section (see [data-model.md §4](data-model.md#4-screen-listmd-warnings-section))

**Phase 4 — Registration & CHANGELOG**

- Bump `version` in `src/modules/ava-fabric-agents/prototype/module.yaml` from `1.1.0` to `1.2.0`
- Add CHANGELOG entry (see Research R7)

---

## 9. Complexity Tracking

| Gate                                        | Failure Reason                                             | Justification                                                                              | Mitigating Controls                                                                                 |
| ------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| Confirmation prompt vs. automated pipelines | Hard pause blocks non-interactive master-orchestrator runs | User explicitly chose interactive confirmation (2026-07-21); pipeline pause is intentional | Documented in spec §8 Assumptions; future `--non-interactive` flag is out of scope for this feature |

---

## 10. Test Strategy

| Test Type                                       | Tool           | Target                                                        | Spec Scenario         |
| ----------------------------------------------- | -------------- | ------------------------------------------------------------- | --------------------- |
| Pre-flight: all present                         | Manual / F5 QA | `DECISION: PROCEED`, all ✅                                   | Scenario 1            |
| Pre-flight: optional missing, user confirms yes | Manual / F5 QA | `DECISION: AWAITING CONFIRMATION` → prototype generated       | Scenario 2, steps 1–4 |
| Pre-flight: optional missing, user cancels      | Manual / F5 QA | No output files; `status: "cancelled"`                        | Scenario 2, step 5    |
| Pre-flight: mandatory missing                   | Manual / F5 QA | `DECISION: BLOCKED`; no output files                          | Scenario 3            |
| Execution log: start entry                      | Manual / F5 QA | `execution-log.json` has `event: "start"`                     | Scenario 4, step 1    |
| Execution log: end entry                        | Manual / F5 QA | `execution-log.json` has `event: "end"` with correct `status` | Scenario 4, step 2    |
| Regression                                      | Manual         | All prototype artifacts unchanged when all inputs present     | Scenario 1            |
