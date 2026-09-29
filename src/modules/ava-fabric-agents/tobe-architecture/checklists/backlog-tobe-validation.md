---
name: backlog-tobe-validation
version: "1.0.0"
date: 2026-06-02
description: "Checklist de validação obrigatória do Backlog Preliminar TO-BE — 7 verificações antes de declarar backlog completo"
applies_to: ava-tobe-migration-plan
---

# Backlog TO-BE — Validation Checklist

> **Execute when**: after Step B5 of the Backlog TO-BE Protocol, before declaring the backlog complete.
> **Rule**: If any check fails → fix and re-execute before closing.

---

## Verificações Obrigatórias (BV-1 a BV-7)

| # | Verificação | Critério | Ação se falhar |
|---|---|---|---|
| BV-1 | Todos os BCs do `bounded-context-map.md` TO-BE estão representados **E** todos os BCs AS-IS com decisão Merge ou Eliminate têm suas funcionalidades rastreadas nas US do BC absorvente | N de seções `## BC-NN` ≥ N de BCs no mapa TO-BE **E** tabela `Rastreabilidade de BCs Eliminados/Absorvidos` presente com cobertura 100% (cada funcionalidade migrada tem ≥ 1 US no BC absorvente) | Adicionar seção para cada BC ausente **E** para BCs absorvidos: gerar US no BC absorvente cobrindo cada funcionalidade migrada listada na tabela de rastreabilidade |
| BV-2 | Cada user story tem rastreabilidade | Coluna `Regra de Negócio (ref)` preenchida com ≥ 1 referência (`BR-{N}` ou `RF-{N}`) | Associar a regra/requisito ou justificar como `ARCH-{componente}` |
| BV-3 | Prioridade MoSCoW atribuída | Coluna `Prioridade (MoSCoW)` preenchida para 100% das US | Atribuir usando critérios da tabela MoSCoW |
| BV-4 | Seção técnica presente + cobertura dos 6 domínios + IDs corretos | Seção `## User Stories Técnicas / Não-Funcionais` existe com ≥ 1 US **por cada um dos 6 domínios transversais** (Autenticação, CI/CD, Migração de Dados, Observabilidade, Segurança, Performance) **E** todas as US nesta seção usam o padrão de ID `US-TECH-{NNN}` **E** US de domínio (em seções de BC) usam o padrão `US-{BC_ID}-{NNN}`. Se IDs flat `US-{NNN}` forem encontrados → **FALHA** — refazer numeração | Gerar US técnicas faltantes para cada domínio descoberto e corrigir IDs para o padrão correto |
| BV-5 | Resumo executivo consistente | Totais do resumo = soma das US por BC | Recalcular totais |
| BV-6 | Cobertura de regras de negócio ≥ 80% | `Cobertura BR (%)` ≥ 80% para cada BC | Listar BRs não cobertos em Pendências |
| BV-7 | Pendências documentadas | Seção `## Pendências e Lacunas` existe | Criar seção mesmo que vazia (registrar "Nenhuma pendência identificada") |
| BV-8 | Consistência aritmética de SP | `∑(SP coluna Epics) == ∑(SP por seção de Wave) == Total na tabela Story Point Distribution`. Tolerância: **0 SP** (exata). | Recalcular e reconciliar todas as tabelas antes de salvar. Se divergência persistir, indicar qual tabela é a fonte de verdade e ajustar as demais. |
