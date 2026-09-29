---
template_id: coexistence-matrix
agent: ava-tobe-coexistence-strategy
version: "1.0.0"
date: 2026-06-08
description: "Template canônico da matriz de coexistência — schema obrigatório para coexistence-matrix.md"
---

# Coexistence Matrix Template

> **Load when**: executing Step 8 of the Execution Protocol, when generating `coexistence-matrix.md`.

```markdown
# Matriz de Coexistência AS-IS ↔ TO-BE

| Campo | Valor |
|---|---|
| **Projeto** | {{PROJECT_NAME}} |
| **TraceID** | {{TRACE_ID}} |
| **Gerado em** | {{GENERATED_AT}} |
| **Versão do Agente** | {{AGENT_VERSION}} |

---

## Matriz de Coexistência por BC

| BC ID | BC Name | Wave | Zona Inicial | Zona na Wave | Feature Flag | Data Sync | Sync Frequency | Rollback Window | Decommission Criteria | Zona Final (pós-Cutover) |
|---|---|---|---|---|---|---|---|---|---|---|
| {{BC_ID}} | {{BC_NAME}} | {{WAVE}} | Z1 | {{ZONE_IN_WAVE}} | `migration.{{BC_NAME_KEBAB}}.{{SCOPE}}.enabled` | {{DATA_SYNC_DIRECTION}} · {{DATA_SYNC_MECHANISM}} | {{SYNC_FREQUENCY}} | {{ROLLBACK_WINDOW}} | {{DECOMMISSION_CRITERIA}} | Z2 |

> **Enforcement obrigatório**:
> - Coluna `Zona Inicial` = `Z1` para TODOS os BCs (CG-1).
> - Coluna `Feature Flag` preenchida para todo BC com `Zona na Wave` = `Z3` (CG-2).
> - Coluna `Zona Final (pós-Cutover)` = `Z2` para TODOS os BCs.
> - Zero linhas com `Feature Flag` vazia quando `Zona na Wave` = `Z3`.
> - Composição BC×Wave consistente com `wave-model.json` (CG-9).
>
> Fonte: `wave-model.json` + `bounded-context-map.md` + `integration-matrix.md`

---

## Catálogo de Feature Flags

| Flag Name | BC | Scope | Wave Ativação | Wave Remoção | Critérios de Flip |
|---|---|---|---|---|---|
| `migration.{{BC_NAME_KEBAB}}.{{SCOPE}}.enabled` | {{BC_NAME}} | {{SCOPE}} | {{WAVE_ACTIVATION}} | {{WAVE_REMOVAL}} | {{FLIP_CRITERIA}} |

> **Enforcement obrigatório**:
> - Naming convention: `migration.{bc_name_kebab}.{scope}.enabled` (CG-2).
> - `scope` = `all` para flag de BC inteiro ou `{endpoint_name_kebab}` para flag granular.
> - Wave Remoção = W4 (cutover) salvo override documentado.
> - Critérios de Flip derivados do Protocolo de Graduação (§5 do `coexistence-strategy.md`).
>
> Fonte: `project-config.yaml` → `tobe_stack.feature_flags.provider`

---

## Rollback Windows por Tipo de Wave

| Tipo de Wave | Tipo | Rollback Window Default | Override possível? |
|---|---|---|---|
| W1 | `domain_read` | 14 dias | ✅ Sim — via wave-plan por BC |
| W2 | `domain_write` | 30 dias | ✅ Sim — via wave-plan por BC |
| W3 | `domain_core` | 45 dias | ✅ Sim — via wave-plan por BC |

> Se override por BC for definido no `wave-plan.md`, o valor da matrix DEVE refletir o override (não o default).

---

## Resumo Consolidado

| Métrica | Valor |
|---|---|
| Total de BCs | {{TOTAL_BCS}} |
| BCs em Z1 (início) | {{TOTAL_BCS}} (100%) |
| BCs em Z2 (pós-cutover) | {{TOTAL_BCS}} (100%) |
| BCs que passam por Z3 | {{BCS_Z3_COUNT}} |
| Total de Feature Flags | {{TOTAL_FLAGS}} |
| BCs com Data Sync | {{BCS_DATA_SYNC_COUNT}} |
| BCs com Eventos/Filas | {{BCS_EVENTS_COUNT}} |
| BCs com Confidence LOW | {{BCS_LOW_CONFIDENCE}} |

> **Validação**: `Total de BCs` deve ser idêntico ao total de BCs no `bounded-context-map.md` TO-BE (CG-8).
```
