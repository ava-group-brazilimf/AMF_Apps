---
name: coexistence-validation-gate
version: "1.1.0"
date: 2026-07-09
description: "Validation gate obrigatória para o Coexistence Strategy Agent — 4 etapas de verificação antes de declarar artefatos concluídos"
applies_to: ava-tobe-coexistence-strategy
---

# Coexistence Strategy — Validation Gate

> **Execute when**: Step 9 of the Execution Protocol, before declaring the coexistence strategy complete.
> **Rule**: If any etapa fails → block delivery, fix, and re-execute before closing.

---

## Etapa 1 — Coexistence Strategy Check

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 1.1 | 8 seções obrigatórias presentes (§1–§8) | `coexistence-strategy.md` | 8/8 seções com conteúdo substantivo |
| 1.2 | Protocolo de graduação define 4 fases (0%, 10%, 50%, 100%) com métricas | `coexistence-strategy.md` §5 | 4 fases com thresholds numéricos |
| 1.3 | Protocolo de decommission com checklist de 5 items | `coexistence-strategy.md` §6 | 5 items com critérios mensuráveis |
| 1.4 | §7 cobre BCs com eventos/filas (se `events-pubsub-inventory.md` existir) | `coexistence-strategy.md` §7 | Zero BCs com eventos omitidos |

---

## Etapa 2 — Coexistence Matrix Check

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 2.1 | 100% dos BCs do `bounded-context-map.md` representados | `coexistence-matrix.md` | Zero BCs ausentes |
| 2.2 | Feature flag definida para todo BC com zona Z3 em qualquer wave | `coexistence-matrix.md` | Zero BCs Z3 sem flag |
| 2.3 | Composição BC×Wave consistente com `wave-model.json` | `coexistence-matrix.md` | Zero divergências |
| 2.4 | Rollback window preenchida para todos os BCs (default ou override) | `coexistence-matrix.md` | Zero células vazias |

---

## Etapa 3 — Diagram Check

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 3.1 | `.mmd` começa com `flowchart TB` e renderiza sem erros | `coexistence-architecture.mmd` | Exit code 0 do validate_diagram.py |
| 3.2 | Diagrama contém subgraphs para Gateway, Legacy, ≥1 Module, Sync, Feature Flags | `.mmd` | 5 subgraphs mínimos |

---

## Etapa 4 — Output Contract Check

| # | Verificação | Resultado esperado |
|---|---|---|
| 4.1 | Verificar existência em disco e tamanho > 0 de cada um dos 3 arquivos do Output Contract | Todos 3 com status `✅ OK`; qualquer `❌ FALTANDO` ou `⚠️ VAZIO` = bloqueio |

### Checklist de Completude — 3 arquivos obrigatórios

| # | Arquivo | Caminho esperado | Verificação |
|---|---|---|---|
| 1 | `coexistence-strategy.md` | `outputs/tobe/docs/coexistence-strategy.md` | existe + tamanho > 0 |
| 2 | `coexistence-matrix.md` | `outputs/tobe/docs/coexistence-matrix.md` | existe + tamanho > 0 |
| 3 | `coexistence-architecture.mmd` | `outputs/tobe/diagrams/coexistence-architecture.mmd` | existe + tamanho > 0 |

---

## Formato do Relatório de Completude (obrigatório antes de encerrar)

O agente DEVE gerar este relatório inline antes de declarar os artefatos concluídos:

```
## Relatório de Completude — Output Contract

| # | Arquivo | Status | Observação |
|---|---|---|---|
| 1 | coexistence-strategy.md | ✅ OK | — |
| 2 | coexistence-matrix.md | ✅ OK | — |
| 3 | coexistence-architecture.mmd | ✅ OK | — |

**Resultado**: 3/3 — CONCLUÍDO.
```

> Se qualquer arquivo tiver status `❌ FALTANDO` ou `⚠️ VAZIO` → substituir "CONCLUÍDO" por "BLOQUEADO"; listar os arquivos pendentes e gerar ou solicitar geração antes de encerrar.
