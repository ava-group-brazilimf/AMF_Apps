---
name: ava-test-plan-tobe
version: 5.0.0
phase: tobe-architecture
date: 2026-07-25
---

# Spec 029 — Unificar e otimizar `ava-test-plan-tobe`

## Problem Statement

O agente `ava-test-plan-tobe` (v4.0.0) e o agente `ava-tobe-test-plan-consolidated` (v2.1.0) possuem responsabilidades sobrepostas: ambos leem os mesmos artefatos TO-BE, ambos produzem/sobrescrevem `outputs/tobe/qa/test-plan.md`, e ambos constroem pirâmide de testes, thresholds por wave e rastreabilidade. O agente consolidado acrescenta apenas três entregas úteis — `test-cases.md`, `gap-analysis.md` e enriquecimento por artefatos tardios — mas exige uma fase extra (7.8) no orquestrador TO-BE, aumentando complexidade e tempo de execução sem valor proporcional.

Além disso, o Input Contract de `test-plan-tobe.md` contém artefatos cujo uso não se sustenta:
- `outputs/asis/gaps-risks-report.md` é declarado, mas nunca consumido.
- `outputs/asis/qa/test-strategy-asis.md` e `outputs/asis/qa/test-execution-plan-asis.md` são obrigatórios, porém nenhum agente AS-IS documentado os produz.
- `outputs/tobe/docs/business-rules-tobe.md` é ambíguo; o produtor padrão gera `outputs/tobe/docs/regras-negocio.md`.
- `outputs/tobe/docs/bounded-context-map.md`, `tech-framework-document.md` e `security-architecture.md` são usados intensivamente, mas marcados como opcionais.

## Decision

1. Absorver as capacidades únicas do `ava-tobe-test-plan-consolidated` no `ava-test-plan-tobe`.
2. Elevar `bounded-context-map.md`, `tech-framework-document.md` e `security-architecture.md` a obrigatórios no Input Contract.
3. Rebaixar `test-strategy-asis.md`, `test-execution-plan-asis.md` e `gap-list-report.md` para opcionais.
4. Remover `gaps-risks-report.md` e `business-rules-tobe.md`; usar `gap-list-report.md` e `regras-negocio.md`.
5. O agente unificado gera `test-plan.md`, `test-cases.md`, `gap-analysis.md`, `functional-test-matrix.md`, `traceability-matrix.md` e `automatable-test-cases.md`.
6. Eliminar `test-plan-consolidated-tobe.md`, seu skill wrapper e a Fase 7.8 do orquestrador.

## Scenarios (BDD)

```gherkin
Feature: Plano de testes TO-BE unificado

  Scenario: Geração completa com todos os artefatos obrigatórios
    Given os artefatos obrigatórios estão presentes
    When o usuário invoca @ava-test-plan-tobe com trigger TP
    Then o agente gera test-plan.md, test-cases.md, gap-analysis.md, functional-test-matrix.md, traceability-matrix.md e automatable-test-cases.md

  Scenario: Ausência de artefatos opcionais
    Given faltam test-strategy-asis.md, test-execution-plan-asis.md e gap-list-report.md
    When o usuário invoca @ava-test-plan-tobe
    Then o agente continua usando defaults e não registra gaps críticos na seção 16

  Scenario: Integridade do Output Contract
    Given o agente concluiu a execução
    Then nenhum dos outputs gerados pode estar em branco e todos possuem tabela de resumo, versionamento e rastreabilidade
```

## Acceptance Criteria

- [ ] `test-plan-tobe.md` está na versão 5.0.0 com Input/Output Contract unificado.
- [ ] `test-plan-consolidated-tobe.md` e `.github/skills/ava-tobe-test-plan-consolidated/SKILL.md` foram excluídos.
- [ ] Fase 7.8 foi removida de `orchestrator-tobe.md`.
- [ ] `module.yaml` não lista mais `ava-tobe-test-plan-consolidated`.
- [ ] `qa-orchestrator-agent.md` e `bridge-fastqa-tobe.md` apontam para `ava-test-plan-tobe`.
- [ ] Docs e specs cruzadas foram sincronizadas.
- [ ] Grep confirma zero ocorrências ativas do agente eliminado.

## Dependencies

- `specs/028-tobe-orchestrator-v280` (conflito parcial documentado).
- `specs/016-tobe-artifact-only-guardrail` (protocolo de consumo de artefatos).
- Agentes upstream: `ava-tobe-migration-plan`, `ava-tobe-architecture-design`, `ava-tobe-architecture-technical`, `ava-tobe-security-design`, `ava-asis-orchestrator`.
- Agentes downstream: `ava-qa-orchestrator`, `ava-qa-bridge-fastqa-tobe`.

## Exclusions

- Não criar produtor AS-IS para `test-strategy-asis.md` / `test-execution-plan-asis.md`.
- Não corrigir demais path-bugs do IO map fora do escopo do agente unificado.
- Não alterar agentes F5 além de `bridge-fastqa-tobe.md` e `qa-orchestrator-agent.md`.
