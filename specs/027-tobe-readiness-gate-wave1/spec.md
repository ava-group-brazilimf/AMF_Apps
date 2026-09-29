# Agent Specification: ava-tobe-orchestrator — Readiness Gate before Phase 8

**Feature Branch**: `027-tobe-readiness-gate-wave1`
**Created**: 2026-07-22
**Status**: Draft
**Change Type**: `modify-existing`
**Input**: O Orquestrador TO-BE deve acionar `ava-readiness-gate` com `wave_number: 1` após a conclusão da Fase 8 (Azure Infra Estimator) e antes do Gate F2→F3 (Requestor Inspection). O objetivo é validar que o pipeline de migração tem condições de avançar para a primeira wave do Build Cycle.

## Clarifications

### Session 2026-07-22

- Q: Position of Fase 8.1 relative to Azure Infra Estimator — before or after? → A: **After** `ava-tobe-azure-infra` (Phase 8), before Gate F2→F3 (Requestor Inspection). PM has full F2 data including infra costs when making the readiness decision.
- Q: Re-run behavior when `readiness-gate-status.json` already exists with `gate_decision: "APPROVED"` → A: **Skip re-run** if APPROVED status file exists — idempotent; gate runs once until criteria change (file deleted or overwritten).
- Q: BLOCKED cascade scope — does BLOCKED halt Gate F2→F3 and all subsequent steps, or only F3/Build Cycle? → A: **Full halt** — BLOCKED stops all subsequent steps including Gate F2→F3, Migration Design Checklist, Strategy Align, and Package Approval. Running these gates is premature when sign-offs or infra are missing.

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-tobe-orchestrator` |
| **Version** | `2.5.0` (MINOR bump — new gate step, no contract change) |
| **Phase** | `F2` |
| **Module** | `tobe-architecture` |
| **Role** | Orquestrador da esteira TO-BE. Acrescenta invocação do `ava-readiness-gate` (wave_number=1) após a Fase 8 (Azure Infra Estimator) e antes do Gate F2→F3 (Requestor Inspection) como gate de aprovação humana pré-Build Cycle. |
| **Skill** | `ava-tobe-orchestrator` (já existente) |
| **Dispatch** | user-facing via SKILL.md (existente) |

> **Change Type is `modify-existing`**:
> - File to modify: `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`
> - Version bump: MINOR (2.4.1 → 2.5.0) — new phase step inserted, no removal of existing contract fields
> - The `module.yaml` entry already exists — Category 4 tasks (registration) are N/A
> - The `SKILL.md` already exists — Category 1.5 is N/A

---

## 2. Agent Frontmatter

The existing frontmatter in `orchestrator-tobe.md` is updated only for version:

```yaml
---
name: ava-tobe-orchestrator
description: |
  Coordena a esteira de design da arquitetura TO-BE.
  Recebe o AS-IS Master Report e orquestra os agentes de design,
  sizing, plano de migração, geração de atividades de migração,
  wave cycle refinement e geração de código.
  Stack e versão lidos de `tobe_stack.*` em project-config.yaml.
  Ativa com: "iniciar design TO-BE", "design arquitetura .NET",
  "start TO-BE design", "arquitetura alvo".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite
version: "2.5.0"
date: 2026-07-22
---
```

---

## 3. Output Contract

No new output artifacts are introduced by this change. The `ava-readiness-gate`
agent is responsible for producing its own output artifacts under the path it
already defines:

```
projects/{project_name}/outputs/readiness-gate/wave-1/readiness-gate-status.json
projects/{project_name}/outputs/readiness-gate/wave-1/readiness-gate-report.md
```

The orchestrator only reads the `gate_decision` field from `readiness-gate-status.json`
to decide whether to proceed to Phase 8.

---

## 4. Behavioral Change Description

### 4.1 New Phase: Fase 8.1 — Readiness Gate (Pré-Build Cycle)

A new gate phase is inserted in `orchestrator-tobe.md` **after Phase 8 (Azure Infra Estimator)
completes and before the existing Gate F2→F3 (Requestor Inspection)**. It is numbered **Fase 8.1**
to follow the Azure Infra Estimator phase (Phase 8) and reflect its position as the final
F2 gate before the Build Cycle.

This position ensures the PM has access to all F2 artifacts — including infra cost estimates
from `ava-tobe-azure-infra` — when making the readiness go/no-go decision.

**Insertion point**: Immediately **before** `### Gate F2→F3 — Requestor Inspection & Validation`
(line ~1452 in `orchestrator-tobe.md`), right after the Fase 7.8 `---` separator.

> ⚠️ **File structure note**: In the current file, `### Gate F2→F3` (line 1452) appears
> BEFORE `### Gate 8→Build Cycle` (line 1505). The correct insertion target is therefore
> before line 1452, not after line 1505. See `research.md §R1` for full analysis.

The new section heading is: `### Fase 8.1 — Readiness Gate (Wave 1 — Pré-Build Cycle)`

### 4.2 Dispatch Protocol

Consistent with the existing Dispatch Protocol (§ Dispatch Protocol in the orchestrator):

```
⛔ Read(src/modules/ava-fabric-agents/shared/readiness-gate.md) OBRIGATÓRIO
   (ver § Dispatch Protocol) → Invocar `ava-readiness-gate`.
```

The agent is invoked with:
- `project_name`: resolved from `project-config.yaml` (already in scope)
- `wave_number`: hardcoded as `1` (this is the first wave of the Build Cycle)
- All other inputs (`wave_scope`, `client_name`, `sponsor_name`, sign-offs) are read
  by `ava-readiness-gate` directly from `projects/{project_name}/context/project-config.yaml`

### 4.3 Gate Decision Handling

**Idempotency check (Option B — skip if already APPROVED):**
Before invoking `ava-readiness-gate`, the orchestrator MUST check:
```
projects/{project_name}/outputs/readiness-gate/wave-1/readiness-gate-status.json
```
- If the file exists AND `gate_decision == "APPROVED"` → log `✅ [READINESS GATE Wave 1] APPROVED (cached) — status file exists` and skip re-invocation. Continue to Gate F2→F3.
- If the file is absent, has `gate_decision != "APPROVED"`, or has `gate_decision == "BLOCKED"` → invoke `ava-readiness-gate` normally.
- If `gate_decision == "CONDITIONAL"` in cached file → re-invoke to refresh (CONDITIONAL requires active PM confirmation each run).

After `ava-readiness-gate` completes (or cached result is used):

| `gate_decision` in `readiness-gate-status.json` | Orchestrator Action |
|---|---|
| `"APPROVED"` (fresh or cached) | Log `✅ [READINESS GATE Wave 1] APPROVED — Prosseguindo para Gate F2→F3` → continue to Gate F2→F3 |
| `"CONDITIONAL"` | Display WARN block with warnings, require explicit PM confirmation (`"Confirmo"`) → only then continue to Gate F2→F3 |
| `"BLOCKED"` | Display `⛔ [READINESS GATE Wave 1] BLOCKED` with list of failed criteria and corrective actions → **HALT pipeline**. Gate F2→F3, Migration Design Checklist, Strategy Align, and Package Approval must NOT execute. |

### 4.4 Checklist of Completion

A completion checklist is added for Fase 8.1:

- [ ] Idempotency check executed: if `readiness-gate-status.json` exists with `gate_decision == "APPROVED"` → skip invocation and proceed
- [ ] `readiness-gate-status.json` exists at `outputs/readiness-gate/wave-1/`
- [ ] `readiness-gate-report.md` exists at `outputs/readiness-gate/wave-1/`
- [ ] `gate_decision == "APPROVED"` (fresh or cached) or `"CONDITIONAL"` (with PM confirmation) before Gate F2→F3 starts
- [ ] If `gate_decision == "BLOCKED"` → Gate F2→F3, Migration Design Checklist, Strategy Align, and Package Approval MUST NOT execute; full pipeline halt

### 4.5 Agent Completion Registry Update

A new entry `ava-readiness-gate` is added to the Agent Completion Registry and to all
timing tables (MICRO table, MACRO table — added to the Fase 8 / Infra row group):

```yaml
ava-readiness-gate:
  status: pending | running | completed | failed
  start_time_brz: string
  end_time_brz: string
  duration_seconds: number
  artifacts_confirmed: boolean   # readiness-gate-status.json exists with gate_decision
  retries: number
  error_detail: string | null
```

In the MICRO timing table, add one row:

```
│ ava-readiness-gate            │ 8.1-Gate  │ [STATUS]  │ [ISO-03:00] │ [ISO-03:00] │ [Xm Ys] │
```

Placement: **after** `ava-tobe-azure-infra` (8-Del) — as the last row in the MICRO table,
before Gate F2→F3 (which is not tracked in the MICRO table itself).

### 4.6 TODO Items Update

The Progress Tracker (TodoWrite) gains one new item:

| # | ID | Label | Emitido em | Completed quando |
|---|---|-------|-----------|------------------|
| 15 | `readiness-gate` | Execute Fase 8.1 — Readiness Gate Wave 1 | Step 3 | ava-readiness-gate gate_decision APPROVED ✓ |

Total TODO items changes from 14 to 15.

---

## 5. User Scenarios (Given-When-Then)

### Scenario 1 - Nominal Path: Gate APPROVED (Priority: P1)

**Story**: Como orquestrador TO-BE, quero validar as pré-condições da wave 1 antes de iniciar a estimativa de infraestrutura Azure, para garantir que o Build Cycle só inicia com arquitetura aprovada, Spec Kit completo, IaC provisionado e sign-offs formais.

**Acceptance Scenarios**:

1. **Given** all 5 readiness criteria (C1–C5) pass in `project-config.yaml`, **When** `ava-readiness-gate` is invoked with `wave_number: 1`, **Then** `readiness-gate-status.json` is created with `gate_decision: "APPROVED"` and Gate F2→F3 (Requestor Inspection) proceeds.
2. **Given** `gate_decision == "APPROVED"`, **When** the orchestrator reads the status file, **Then** it logs `✅ [READINESS GATE Wave 1] APPROVED` and continues to Gate F2→F3 without user intervention.

---

### Scenario 2 - Gate BLOCKED (Priority: P1)

**Story**: Como PM, quero que o pipeline pare antes do Gate F2→F3 se critérios de readiness não foram atendidos, para garantir que o Build Cycle só inicia com aprovação formal.

**Acceptance Scenarios**:

1. **Given** `project-config.yaml` has `signoffs.architecture_approved_by_client: false`, **When** `ava-readiness-gate` runs, **Then** `gate_decision == "BLOCKED"` and no subsequent steps (Gate F2→F3, Migration Design Checklist, Strategy Align, Package Approval) execute.
2. **Given** `gate_decision == "BLOCKED"`, **When** orchestrator reads the status, **Then** it displays the BLOCKED message with corrective actions and halts with no further step dispatched.

---

### Scenario 3 - Gate CONDITIONAL (Priority: P2)

**Story**: Como PM, quero poder confirmar ciência das advertências e liberar a wave, mesmo com itens WARN no gate.

**Acceptance Scenarios**:

1. **Given** all C1–C5 pass but `signoff_date` is > 90 days old, **When** `ava-readiness-gate` runs, **Then** `gate_decision == "CONDITIONAL"` and the orchestrator shows a WARN block requesting PM confirmation.
2. **Given** PM responds with `"Confirmo"`, **When** the orchestrator receives the confirmation, **Then** Gate F2→F3 proceeds normally.

---

## 6. Quality Gate Requirements

- [ ] Existing Phase 8 number and behavior are preserved unchanged
- [ ] New section `### Fase 8.1 — Readiness Gate (Wave 1 — Pré-Build Cycle)` inserted after Migration Design Checklist Gate and before Gate F2→F3
- [ ] Dispatch Protocol `Read()` call to `readiness-gate.md` before invocation
- [ ] `wave_number` is hardcoded to `1` (first Build Cycle wave)
- [ ] Gate decision `BLOCKED` halts ALL subsequent steps (Gate F2→F3, Migration Design Checklist, Strategy Align, Package Approval) — no partial execution
- [ ] Gate decision `CONDITIONAL` requires explicit PM confirmation before Gate F2→F3
- [ ] Idempotency: if `readiness-gate-status.json` exists with `gate_decision == "APPROVED"` → skip re-invocation
- [ ] MICRO timing table updated with `ava-readiness-gate` row (position: 8.1-Gate)
- [ ] Agent Completion Registry updated with `ava-readiness-gate` entry
- [ ] TODO item #15 `readiness-gate` added to Progress Tracker
- [ ] Version bump from `2.4.1` → `2.5.0` in frontmatter and `date` updated
- [ ] No technology versions hardcoded (Article I)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 7. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Readiness Gate Agent | `ava-readiness-gate` | Invoked by this orchestrator in Fase 8.1; defined in `src/modules/ava-fabric-agents/shared/readiness-gate.md` |
| Azure Infra Estimator | `ava-tobe-azure-infra` | Phase 8 — must complete before Fase 8.1 starts (PM needs cost data) |
| Gate F2→F3 — Requestor Inspection | `ava-requestor-inspection` | Blocked by Fase 8.1 BLOCKED decision |

---

## 8. Assumptions

- `ava-readiness-gate` agent already exists and is complete at `src/modules/ava-fabric-agents/shared/readiness-gate.md`
- The `project-config.yaml` for any project will contain (or be expected to contain) the `signoffs` section documented in `readiness-gate.md`
- `wave_number: 1` is correct because the Readiness Gate here validates readiness for the **first Build Cycle wave**, initiated right before infra estimation completes F2 and transitions to F3/F4
- No changes are needed to `readiness-gate.md` itself — only `orchestrator-tobe.md` is modified
- The STATUS_ONLY timing table (`timing_benchmark_enabled: false`) also receives the new row for `ava-readiness-gate`
