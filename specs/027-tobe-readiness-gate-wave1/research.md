# Research: 027-tobe-readiness-gate-wave1

## R1 — Insertion Point (CRITICAL)

**Finding**: The spec states "after `### Gate 8→Build Cycle` and before `### Gate F2→F3`" — but this description is **inverted** relative to the actual file structure.

In `orchestrator-tobe.md` the sections appear in this order:
| Line | Section |
|------|---------|
| ~1450 | Fase 7.8 checklist ends + `---` separator |
| 1452 | `### Gate F2→F3 — Requestor Inspection & Validation` |
| ~1490 | Trigger codes table + SD gate note |
| 1505 | `### Gate 8→Build Cycle — Migration Design Checklist` |
| ~1700 | `### Step F1 — Strategy Align` |

**Gate F2→F3 comes before Gate 8→Build Cycle in the file.**

**Correct insertion point**: Insert `### Fase 8.1` **before line 1452** (`### Gate F2→F3`), immediately after the `---` separator that closes the Fase 7.8 checklist.

**Rationale**: The spec's semantic intent is "first gate after Phase 8, before any F3-transition gate" — which maps to the position just before Gate F2→F3 in the file.

**Spec typo to fix in plan**: `§ 6` Quality Gate Requirements lists "(position: 7.9-Gate)" — should be `8.1-Gate`.

---

## R2 — All Edit Targets in `orchestrator-tobe.md`

Seven distinct edits required:

| # | Location | Line(s) | Change |
|---|----------|---------|--------|
| E1 | Frontmatter | 3–4 | version 2.4.1 → 2.5.0; date 2026-07-13 → 2026-07-22 |
| E2 | Agent Team table | ~78 (after `ava-tobe-azure-infra` row) | Add `ava-readiness-gate` row with phase `8.1` |
| E3 | Main body | Before line 1452 | Insert full `### Fase 8.1` section |
| E4 | TODO Items table | Line 1947 | Header: 14→15 items; add row 15 for `readiness-gate` |
| E4b | TODO Regras de atualização | ~1968 | "14 tasks" → "15 tasks" |
| E5 | Agent Completion Registry | Line 1992 | Add `ava-readiness-gate` at end of Agent IDs list |
| E6 | MICRO table FULL (×2) | Lines 1880, 2175 | Add `ava-readiness-gate` row after `ava-tobe-azure-infra` |
| E7 | MICRO table STATUS_ONLY (×2) | Lines 1912, 2213 | Add `ava-readiness-gate` row after `ava-tobe-azure-infra` |

Total: **9 file edits** to a single file (`orchestrator-tobe.md`).

---

## R3 — New Section Text (Fase 8.1)

The full text of the new section to insert (written in Brazilian Portuguese per Constitution Article V):

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

---

## R4 — Agent Team Table Row

New row to add after `| Azure Infra Estimator TO-BE | 8 — Estimativa de infraestrutura Azure |`:

```
| Readiness Gate (`ava-readiness-gate`) | **8.1 — Gate de Readiness (Pré-Build Cycle, Wave 1)** |
```

---

## R5 — Spec Typo Found

In `spec.md` § 6 Quality Gate Requirements:
- Current: `MICRO timing table updated with \`ava-readiness-gate\` row (position: 7.9-Gate)`
- Correct: `MICRO timing table updated with \`ava-readiness-gate\` row (position: 8.1-Gate)`

This stale reference from the old phase numbering should be fixed in the spec file before tasks are generated.
