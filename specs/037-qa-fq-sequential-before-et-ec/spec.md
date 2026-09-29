---
name: ava-qa-orchestrator
version: 2.1.1
phase: qa-agents
date: 2026-08-06
---

# Spec 037 — FQ sequencial, imediatamente antes de ET+EC (trigger `QE`)

## Problem Statement

No `## Routing — Trigger QE` do `ava-qa-orchestrator` (v2.1.0), o step 9 despacha três agentes
em **paralelo**: `ava-qa-exploratory` (ET), `ava-qa-evidence-capture` (EC) e
`ava-qa-bridge-fastqa-tobe` em modo `exploration-automation` (FQ — Momento 2), seguido de dois
gates de verificação (9b ET VERIFICATION GATE, 9c FQ COMPLETION GATE).

O paralelismo entre os três esconde uma diferença de natureza: FQ é um **orquestrador de
sub-agentes FastQA** (`@fastqa:load_pbi`, `@fastqa:map_behaviors`, `@fastqa:api_create_automated`)
que arquiva artefatos AS-IS, aplica um override de configuração (`project_config.tobe.json`) e só
depois restaura o estado original — uma sequência de 11 sub-passos com efeitos colaterais em
`fastqa/`. ET e EC, por outro lado, são agentes de leitura/análise autônomos sem essas
dependências de estado compartilhado. Rodar os três simultaneamente não traz benefício real (FQ
não alimenta nem é alimentado por ET/EC hoje — nenhum dos dois lê `outputs/qa/fastqa/*` como
input) e torna o diagnóstico de falhas mais difícil de correlacionar (qual dos três agentes
produziu qual linha de log, numa execução concorrente).

## Decision

FQ passa a rodar **sequencialmente**, imediatamente **antes** de ET+EC — que continuam paralelos
entre si. O step 9 do trigger `QE` é dividido em 4 sub-passos:

| Sub-passo | Conteúdo | Equivalente hoje |
|---|---|---|
| 9 | Dispatch de `ava-qa-bridge-fastqa-tobe` (FQ), sozinho | Metade do step 9 atual |
| 9a | FQ COMPLETION GATE | Conteúdo integral do atual 9c (renumerado) |
| 9b | Dispatch de `ava-qa-exploratory` + `ava-qa-evidence-capture`, em paralelo | Outra metade do step 9 atual |
| 9c | ET VERIFICATION GATE | Conteúdo integral do atual 9b (renumerado) |

Nenhuma instrução de conteúdo (blocos `⛔ CRITICAL`, os 4 artefatos obrigatórios do ET, a lógica
dos dois gates) é reescrita — apenas reordenada. O 9a já termina em "continuar (não bloquear
pipeline)" em todos os ramos (COMPLETE / FAILED / retry esgotado), então o fluxo sempre avança
para 9b independentemente do resultado de FQ — preservando a filosofia "non-blocking" já
estabelecida para este trigger.

Os passos 10 (`PT`, "após EC concluído") e 11 (`RS`) **não mudam**: EC continua sendo despachado
antes deles (agora em 9b), então a pré-condição desses passos continua satisfeita.

## Scope

**Único arquivo alterado**: `src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md`.

Investigação prévia confirmou ausência de acoplamento de dados a proteger:
- `evidence-capture-agent.md` — Input Contract não lista nenhum artefato de `outputs/qa/fastqa/`
  como obrigatório ou opcional.
- `exploratory-agent.md` — 100% AS-IS, nenhuma referência a FastQA.
- Nenhum código em `src/shared/**` ou `tests/**` faz parsing programático da ordem textual do
  DAG (é spec em linguagem natural consumida por LLM).
- `.github/agents/ava-qa-orchestrator.agent.md` é wrapper fino gerado por
  `generate_agent_wrappers.py` — não contém a lógica de routing, mas herda `version` do
  frontmatter (regenerar após o bump).

## Scenarios (BDD)

```gherkin
Feature: FQ sequencial antes de ET+EC no trigger QE

  Scenario: FQ despacha sozinho antes de ET/EC
    Given o Pre-condition Gate (QE) passou
    And os steps 1-8 concluíram
    When o orquestrador alcança o step 9
    Then invoca apenas ava-qa-bridge-fastqa-tobe (modo exploration-automation)
    And NÃO invoca ava-qa-exploratory nem ava-qa-evidence-capture neste step

  Scenario: ET+EC só disparam depois do FQ Completion Gate
    Given o step 9 (FQ) concluiu, com qualquer status (COMPLETE ou FAILED)
    When o orquestrador executa o step 9a (FQ COMPLETION GATE)
    Then registra o status de FQ (✅ COMPLETE / ⚠️ retry / ❌ FAILED)
    And prossegue para o step 9b independentemente do resultado

  Scenario: ET e EC permanecem paralelos entre si
    Given o step 9a concluiu
    When o orquestrador executa o step 9b
    Then invoca ava-qa-exploratory e ava-qa-evidence-capture em paralelo
    And nenhum dos dois aguarda o outro

  Scenario: PT continua correto após a reordenação
    Given o step 9b (EC) concluiu
    When o orquestrador executa o step 10 (PT)
    Then a pré-condição "após EC concluído" está satisfeita, como antes da mudança
```

## Acceptance Criteria

- [ ] `qa-orchestrator-agent.md` está na versão 2.1.1 com `date` atualizado para 2026-08-06.
- [ ] Tabela `## Agent Team QA`: linha do `ava-qa-bridge-fastqa-tobe` (Momento 2) descreve
      "sequencial, imediatamente antes de ET+EC" em vez de "paralelo a ET+EC".
- [ ] Tabela `## Triggers / Menu`, descrição do `QE`: ordem textual `...FT→FQ→ET→EC`.
- [ ] Nota da sequência mínima obrigatória: ordem textual `...FT→FQ→ET+EC→PT→RS`.
- [ ] `## Routing — Trigger QE` step 9 despacha **apenas** `ava-qa-bridge-fastqa-tobe`.
- [ ] Step 9a = FQ COMPLETION GATE (conteúdo idêntico ao atual 9c).
- [ ] Step 9b despacha `ava-qa-exploratory` + `ava-qa-evidence-capture` em paralelo.
- [ ] Step 9c = ET VERIFICATION GATE (conteúdo idêntico ao atual 9b).
- [ ] Referência cruzada no 4b (TS COMPLETION GATE) atualizada: "`ava-qa-evidence-capture`
      (passo 9)" → "(passo 9b)".
- [ ] Tabela "Resumo de cobertura por trigger": ordem textual `...FT→FQ→ET→EC`.
- [ ] Passos 10 (PT) e 11 (RS) permanecem textualmente inalterados.
- [ ] `CHANGELOG.md` tem entrada PATCH para `ava-qa-orchestrator` v2.1.0 → v2.1.1.
- [ ] `.github/agents/ava-qa-orchestrator.agent.md` regenerado via
      `generate_agent_wrappers.py` (metadata.version = 2.1.1).

## Dependencies

- Nenhuma dependência de outra spec — mudança isolada de ordenação dentro do `ava-qa-orchestrator`.

## Exclusions

- Não altera o comportamento individual de `ava-qa-exploratory`, `ava-qa-evidence-capture` ou
  `ava-qa-bridge-fastqa-tobe` — apenas a ordem de disparo pelo orquestrador.
- Não introduz dependência de dados de FQ para ET/EC (nenhuma foi encontrada, nenhuma é criada).
- Não abre spec para o `specs/035-qa-orchestrator-two-moments` (fechada/histórica) — este é um
  spec novo e independente.
