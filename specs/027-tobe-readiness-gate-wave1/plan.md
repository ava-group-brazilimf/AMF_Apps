# Implementation Plan: Readiness Gate before Build Cycle (Wave 1)

**Branch**: `027-tobe-readiness-gate-wave1` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-tobe-orchestrator` |
| **Phase** | `F2` |
| **Module** | `tobe-architecture` |
| **Primary Requirement** | Insert `### Fase 8.1 — Readiness Gate (Wave 1)` into `orchestrator-tobe.md` — invokes `ava-readiness-gate` after Phase 8 and before Gate F2→F3, with idempotency and full-halt on BLOCKED. |
| **Technical Approach** | 9 targeted string-patch edits to a single existing markdown file; no new files created. Version bumped 2.4.1 → 2.5.0. |

---

## Constitution Check

- [X] **Article I** — No technology versions hardcoded
- [X] **Article II** — Frontmatter updated (version + date only); pattern `^ava-[a-z0-9-]+$` preserved
- [X] **Article III** — Phase placement valid; existing phase ordering unchanged
- [X] **Article IV** — `module.yaml` already exists; this is a `modify-existing` change — N/A
- [X] **Article V** — New Fase 8.1 section body written in Brazilian Portuguese
- [X] **Article VI** — BDD scenarios in spec §5: nominal (APPROVED), BLOCKED (full-halt), CONDITIONAL (PM confirm)
- [X] **Article VII** — Security not impacted; no F1 sub-pipeline change
- [X] **Article VIII** — trace_id propagated by `ava-readiness-gate` internally; orchestrator passes `project_name`
- [X] **Article IX** — N/A: this is an LLM prompt file, not generated code
- [X] **Article X** — MINOR bump (2.4.1 → 2.5.0): new step added, no contract removal
- [X] **Article XI** — `modify-existing`; SKILL.md unchanged; only agent body modified

**Quality gate**: No `[NEEDS CLARIFICATION]` markers remain. All outputs owned by `ava-readiness-gate`.

**Post-Design Re-check**: All gates PASS. No complexity violations.

---

## 1. Technical Context

**File modified**: `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`

**Language/Version**: Markdown — agent instruction specification  
**Primary Dependency**: `ava-readiness-gate` (exists at `src/modules/ava-fabric-agents/shared/readiness-gate.md`; no changes)  
**Storage**: Gate outputs `outputs/readiness-gate/wave-1/readiness-gate-status.json` + `readiness-gate-report.md` — owned by `ava-readiness-gate`  
**Testing**: Manual — grep/read validation (see Quickstart)  
**Target Platform**: GitHub Copilot agent execution context  
**Constraints**: Body text in pt-BR; existing sections must not change; insertion before `### Gate F2→F3` (line 1452)  

---

## 2. Phase Placement

```
Phase 8 (ava-tobe-azure-infra) → [NEW] Fase 8.1 (ava-readiness-gate) → Gate F2→F3 (ava-requestor-inspection) → Gate 8→Build Cycle → Steps F1/F2 → AVA Summary
```

**Gate**: Readiness Gate BLOCKED = full halt of all subsequent F3-transition steps.

---

## 3. Clean Architecture Alignment

N/A — this is an LLM prompt file, not generated code.

---

## 4. File Structure

```
src/modules/ava-fabric-agents/tobe-architecture/agents/
└── orchestrator-tobe.md    ← ONLY file modified (9 string patches)
```

No new files. No SKILL.md change. No `module.yaml` change.

---

## 5. module.yaml Impact

N/A — `modify-existing` change to an existing agent. Module entry already exists.

---

## 6. Observability & Trace Propagation

`trace_id` propagated by `ava-readiness-gate` internally. Orchestrator passes `project_name`; gate agent reads all other context from `project-config.yaml`.

---

## 7. Schema Changes

No schema changes. No new AgentTask/AgentResult fields.

---

## 8. Edit Inventory (9 patches to `orchestrator-tobe.md`)

> **⚠️ Critical Finding (research.md §R1):** The spec says "after `### Gate 8→Build Cycle`"
> but in the current file, `### Gate F2→F3` (line 1452) comes **before** `### Gate 8→Build Cycle`
> (line 1505). The correct insertion target is **before line 1452** (`### Gate F2→F3`), right
> after the Fase 7.8 `---` separator. This satisfies the semantic intent.

| ID | Section | Target text | Change |
|----|---------|-------------|--------|
| E1 | Frontmatter | `version: "2.4.1"` / `date: 2026-07-13` | → `"2.5.0"` / `2026-07-22` |
| E2 | Agent Team table | `\| Azure Infra Estimator TO-BE \| 8 — ...` | Add row after: `\| Readiness Gate (\`ava-readiness-gate\`) \| **8.1 — Gate de Readiness (Pré-Build Cycle, Wave 1)** \|` |
| E3 | Main body | `---\n\n### Gate F2→F3` | Insert `---\n\n### Fase 8.1 ...` block before this (see §8.1 below) |
| E4 | TODO header | `contrato fixo — 14 items` | → `contrato fixo — 15 items` |
| E4b | TODO table | after row 14 (`wcr` item) | Add row: `\| 15 \| \`readiness-gate\` \| Execute Fase 8.1 — Readiness Gate Wave 1 \| Step 3 \| ava-readiness-gate gate_decision APPROVED ✓ \|` |
| E4c | Regras de atualização | `TODAS as 14 tasks` | → `TODAS as 15 tasks` |
| E5 | Agent IDs list | ends with `, \`ava-tobe-azure-infra\`` | Append `, \`ava-readiness-gate\`` |
| E6 | MICRO table FULL (×2) | `\| ava-tobe-azure-infra ... \| 8-Del \|` (2 occurrences) | Insert row after each: `\| ava-readiness-gate \| 8.1-Gate \| ...` |
| E7 | MICRO table STATUS_ONLY (×2) | `\| ava-tobe-azure-infra ... \| 8-Del \|` (2 occurrences) | Insert row after each |

### 8.1 — New Section Text (E3)

```markdown
---

### Fase 8.1 — Readiness Gate (Wave 1 — Pré-Build Cycle)

⛔ Read(src/modules/ava-fabric-agents/shared/readiness-gate.md) OBRIGATÓRIO (ver § Dispatch Protocol) → Invocar `ava-readiness-gate`.

> ⚠️ **Gate Idempotente**: Antes de invocar `ava-readiness-gate`, verificar se o arquivo
> `projects/{project_name}/outputs/readiness-gate/wave-1/readiness-gate-status.json` já existe
> com `gate_decision == "APPROVED"`. Se sim → usar resultado cacheado e avançar sem re-invocar.
> Se `gate_decision == "CONDITIONAL"` no cache → re-invocar (confirmação PM necessária a cada run).

- `project_name`: extraído do contexto corrente (já em escopo)
- `wave_number`: **fixo = `1`** (primeira wave do Build Cycle)
- Todos os demais inputs (`wave_scope`, `client_name`, `sponsor_name`, sign-offs) são lidos
  pelo próprio `ava-readiness-gate` de `projects/{project_name}/context/project-config.yaml`

**Protocolo de decisão do gate:**

| `gate_decision` em `readiness-gate-status.json` | Ação do orquestrador |
|---|---|
| `"APPROVED"` (novo ou cacheado) | Emitir `✅ [READINESS GATE Wave 1] APPROVED — Prosseguindo para Gate F2→F3` → continuar |
| `"CONDITIONAL"` | Exibir bloco WARN com advertências; aguardar confirmação explícita do PM (`"Confirmo"`) → somente então continuar para Gate F2→F3 |
| `"BLOCKED"` | Emitir `⛔ [READINESS GATE Wave 1] BLOCKED` com lista de critérios reprovados e ações corretivas → **PARAR PIPELINE COMPLETO**. Gate F2→F3, Migration Design Checklist, Step F1 (Strategy Align) e Step F2 (Package Approval) NÃO DEVEM ser executados. |

> ⛔ **INVARIANTE ABSOLUTA (BLOCKED):** Quando `gate_decision == "BLOCKED"`, interromper
> imediatamente toda a execução subsequente. Não executar nenhum gate ou step adicional.
> Exibir as ações corretivas e aguardar resolução pelo PM antes de qualquer re-execução.

> Este gate segue o procedimento de escalonamento padrão de [@artifact-only-consumption-protocol](../../shared/artifact-only-consumption-protocol.md) §2.2 — aguardar decisão do usuário, nunca prosseguir automaticamente nem substituir por releitura de código legado.

**Checklist de conclusão da Fase 8.1:**

- [ ] Idempotência verificada: se `readiness-gate-status.json` existe com `gate_decision == "APPROVED"` → skip e continuar; se ausente ou != APPROVED → invocar normalmente
- [ ] `outputs/readiness-gate/wave-1/readiness-gate-status.json` existe com tamanho > 0
- [ ] `outputs/readiness-gate/wave-1/readiness-gate-report.md` existe com tamanho > 0
- [ ] `gate_decision == "APPROVED"` (novo ou cacheado) ou `"CONDITIONAL"` (com confirmação PM) antes de avançar para Gate F2→F3
- [ ] Se `gate_decision == "BLOCKED"` → Gate F2→F3, Migration Design Checklist, Step F1 e Step F2 NÃO executados; pipeline pausado aguardando PM
```

### 8.2 — New MICRO Table Row (E6 FULL mode)

Insert after each `| ava-tobe-azure-infra ... | 8-Del ... |` row:

```
     | ava-readiness-gate            | 8.1-Gate  | [STATUS]  | [PREENCHER: ISO-03:00]  | [PREENCHER: ISO-03:00]  | [Xm Ys] |
```

### 8.3 — New MICRO Table Row (E7 STATUS_ONLY mode)

Insert after each `│ ava-tobe-azure-infra ... │ 8-Del ... │` row:

For Reasoning Approach STATUS_ONLY table (line ~1912):
```
     | ava-readiness-gate            | 8.1-Gate  | [STATUS] |
```

For Execution Timing Output STATUS_ONLY table (line ~2213):
```
  │ ava-readiness-gate            │ 8-Del     │ ✅/❌/⏳ │
```

Wait — the status_only template for Execution Timing Output uses box-drawing characters. Insert:
```
  │ ava-readiness-gate            │ 8.1-Gate  │ ✅/❌/⏳ │
```

---

## 9. Complexity Tracking

No Constitution gate failures. No complexity violations to justify.

---

## 10. Quickstart Validation

```powershell
$f = "src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md"

# E1 version
Select-String 'version: "2.5.0"' $f

# E2 Agent Team row
Select-String 'ava-readiness-gate.*8.1' $f

# E3 Fase 8.1 section
Select-String '### Fase 8.1' $f

# E4 TODO 15 items
Select-String 'contrato fixo — 15 items' $f

# E4b readiness-gate TODO row
Select-String 'readiness-gate.*Wave 1' $f

# E5 Agent IDs
Select-String "ava-readiness-gate'" $f

# E6/E7 MICRO rows
Select-String '8.1-Gate' $f
# Expected: ≥4 matches (2 FULL + 2 STATUS_ONLY)
```

### Expected Outcome
All checks return ≥1 match → file is ready for commit.

---

## Project Structure

### Documentation

```text
specs/027-tobe-readiness-gate-wave1/
├── plan.md           ← This file
├── research.md       ← Phase 0 findings
├── spec.md           ← Feature spec (clarified, typo fixed)
├── checklists/
│   └── requirements.md
└── tasks.md          ← created by /speckit.tasks
```

### Source Code

```text
src/modules/ava-fabric-agents/tobe-architecture/agents/
└── orchestrator-tobe.md    ← only modified file
```
