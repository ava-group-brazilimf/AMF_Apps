---
template_id: migration-executive-summary
agent: ava-tobe-migration-plan
version: "1.0.0"
description: "Schema obrigatório do Resumo Executivo de Migração — documento autocontido de no máximo 1 página"
---

# Migration Executive Summary — Schema Template

> **Load when**: executing Step 7 of the Execution Protocol, when generating `migration-executive-summary.md`.
> Documento autocontido de no máximo 1 página (leitura ≤ 2 minutos). Sem referências cruzadas a outros artefatos.

```markdown
# Plano de Migração — Resumo Executivo
**Projeto**: {project_name} | **Data**: {data} | **Versão**: 1.0

## Recomendação
[Go / No-Go] — [justificativa em 1 frase]

## Visão Geral
[Máx. 3 linhas: escopo da migração, tecnologia de origem e destino, nº de waves]

## Resumo de Waves

| Wave | Módulos | T-Shirt | Tempo IA (h) | Tempo Manual (h) | Total (h) | Previsão |
|---|---|---|---|---|---|---|
| Wave 1 | [BCs] | S | 4 | 16 | 20 | [data] |
| Wave N | [BCs] | M | 8 | 40 | 48 | [data] |
| **TOTAL** | — | — | **Xh** | **Yh** | **Zh** | [data final] |

## Top 3 Riscos

| # | Risco | Impacto | Mitigação |
|---|---|---|---|
| 1 | [risco] | Crítico / Alto | [mitigação] |
```
