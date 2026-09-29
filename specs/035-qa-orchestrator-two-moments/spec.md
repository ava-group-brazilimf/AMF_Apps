---
name: ava-qa-orchestrator
version: 2.0.0
phase: qa-agents
date: 2026-08-05
---

# Spec 035 — QA Orchestrator em dois momentos: `TPT` (planejamento) e `QE` (execução)

## Problem Statement

O `ava-qa-orchestrator` (v1.3.0) concentra toda a esteira QA num único trigger `QS`, que executa
`GR→BM→TS→TC→AS→DBI→CT→FT→ET→EC→FQ→PT→RS` na Fase F5 — **antes** da esteira de código estar
validada e **antes** do DevOps Momento 2 (`DE`, Fase F6). Quatro consequências concretas:

1. **`RS` nunca executa.** O trigger `RS` consome `outputs/tobe/parity-test-report.md`, artefato
   produzido pelo `ava-devops-compare-version` — agente #11 do DevOps Momento 2
   (`devops-agents/agents/orchestrator-devops.md` Step 2.9;
   `devops-agents/agents/compare-version-agent.md:216`). Como `DE` só roda em F6 e o QA roda em
   F5, o Passo T2 do §Terminal Mandatory Steps sempre cai em
   `RS | ⚠ SKIPPED (parity-test-report.md ausente — PT não executado)`.

2. **`PT` não possui executor no módulo QA.** Não existe agente de parity test em
   `src/modules/ava-fabric-agents/qa-agents/agents/` — o "Parity Test" é, de fato, o
   `ava-devops-compare-version`. Além disso, as seções `§Routing — Trigger PT` e
   `§Routing — Trigger RS` são referenciadas 3× no arquivo do orquestrador (Routing `QS` passos
   10 e 11, Passos T1 e T2, tabela de cobertura) mas **não existem** — são referências pendentes
   em caminho de execução ativo, não latente.

3. **`DBI`, `CT`, `FT` e `FQ` dependem de artefatos de F4** (migrations EF Core,
   `*Controller.cs`, `*.component.ts`, OpenAPI specs). Hoje cada um tem apenas seu gate
   individual, sem um gate consolidado que impeça a esteira inteira de iniciar cedo demais.

4. **O DevOps consome o planejamento de QA.** `devops-agents/agents/cd-agent.md:45-46` lê
   `outputs/tobe/qa/test-plan.md` e `outputs/tobe/qa/functional-test-matrix.md` — artefatos
   produzidos pelo trigger `TPT`. Logo, o **planejamento** de QA precisa ocorrer antes do DevOps
   e a **execução** de QA depois dele.

Some-se a isso duas divergências internas de menor gravidade: `PT` e `RS` não constam do
`## Triggers / Menu` embora sejam invocáveis isoladamente na tabela "Resumo de cobertura por
trigger"; e a lista do invariante em §Terminal Mandatory Steps omite `FQ`, contradizendo a nota
do topo do arquivo e a própria tabela de cobertura.

## Decision

A correção espelha no QA a separação de momentos que o `ava-devops-orchestrator` já adota
(`DP` = Momento 1 Planejamento / `DE` = Momento 2 Execução):

| Momento | Trigger QA | Quando | Produz |
|---|---|---|---|
| 1 — Planejamento | `TPT` (já existe) | após F2 TO-BE | test-plan, test-cases, gap-analysis, matrizes |
| 2 — Execução | `QE` (novo) | após esteira de código (F4) **e** DevOps `DE` | scripts, testes DB/contract/frontend, exploratório, FastQA, evidências, paridade, regressão |

1. **Criar o trigger `QE`** (Momento 2 — Execução QA), com `§Pre-condition Gate (QE)` de quatro
   passos bloqueantes: F2 concluída (`bounded-context-map.md` com ≥1 BC); planejamento `TPT`
   concluído (`test-plan.md` + `test-cases.md`); esteira de código F4 concluída (sentinela
   `source-code/README.md` + backend ou frontend presentes); DevOps Momento 2 concluído
   (`iac/ci/`, `iac/cd/azure-pipelines-cd.yml`, `infra/`). Mais um passo 4b não-bloqueante que
   apenas sinaliza ausência de `parity-test-report.md`.
2. **Reclassificar `TPT`** como Momento 1 — Planejamento, sem alterar seu comportamento atual
   (gate próprio, dispatch para `ava-test-plan-tobe` com `trigger: TP` e interrupção imediata do
   fluxo do orquestrador).
3. **`QS` torna-se alias deprecado** que emite aviso e redireciona integralmente para
   `§Routing — Trigger QE`. Mantido por compatibilidade: o `master-orchestrator.md` Step 5.1
   ainda despacha `QS`.
4. **Criar `§Routing — Trigger PT`** — documenta que `PT` **não é um dispatch do QA**, e sim uma
   verificação de disponibilidade do artefato produzido pelo `ava-devops-compare-version` — e
   **`§Routing — Trigger RS`** — dispatch de `ava-qa-script-generator` em `mode: regression`
   (contrato em `script-generator-agent.md:715-721`).
5. **Adicionar `PT` e `RS` ao `## Triggers / Menu`**, eliminando a divergência com a tabela de
   cobertura.
6. **`FTM` entra no escopo do `QE`**, executado logo após `BM` (de quem depende, via
   `behavior-catalog.json`). `FTM` não pertence ao `TPT`: produz
   `outputs/qa/functional-test-matrix.md`, enquanto o `TPT` produz
   `outputs/tobe/tests/functional-test-matrix.md`.

Adicionalmente, o gate `QE`, ao bloquear, emite o sinal de conclusão
`↳ ✅ [ava-qa-orchestrator] QE DEFERRED — {motivo}`. Sem ele, o `master-orchestrator.md`
Step 5.2 — que aguarda `"↳ ✅ [ava-qa-orchestrator]"` — executaria 4 retentativas inúteis antes
de registrar WARN.

## Scenarios (BDD)

```gherkin
Feature: QA Orchestrator em dois momentos

  Scenario: Gate QE bloqueia quando o DevOps Momento 2 não rodou
    Given os artefatos do TPT e da esteira de código F4 existem
    And outputs/tobe/iac/cd/azure-pipelines-cd.yml não existe
    When o usuário invoca @ava-qa-orchestrator com trigger QE
    Then o agente emite "QE PRE-CONDITION GATE: BLOCKED" indicando o Passo 4
    And emite o sinal "QE DEFERRED"
    And não invoca nenhum sub-agente de QA

  Scenario: Gate QE bloqueia quando o planejamento TPT não foi executado
    Given outputs/tobe/qa/test-plan.md não existe
    When o usuário invoca @ava-qa-orchestrator com trigger QE
    Then o agente emite "QE PRE-CONDITION GATE: BLOCKED" indicando o Passo 2
    And a ação requerida instrui a executar o trigger TPT antes

  Scenario: Caminho nominal com F4 e DE completos
    Given os quatro passos do Pre-condition Gate QE estão satisfeitos
    When o usuário invoca @ava-qa-orchestrator com trigger QE
    Then o agente registra "PRE-CONDITION GATE QE: PASS"
    And executa GR, BM, FTM, TS, TC, AS, DBI, CT, FT, ET, EC e FQ
    And executa os passos terminais PT e RS

  Scenario: QS redireciona para QE com aviso de depreciação
    When o usuário invoca @ava-qa-orchestrator com trigger QS
    Then o agente emite um aviso de depreciação apontando para QE
    And executa o Routing do trigger QE integralmente

  Scenario: RS deixa de ser sempre pulado
    Given o DevOps Momento 2 gerou outputs/tobe/parity-test-report.md
    When o Passo T2 do fluxo terminal é alcançado
    Then RS invoca ava-qa-script-generator em mode regression
    And produz outputs/qa/regression-suite/Regression.Tests/
```

## Acceptance Criteria

- [ ] `qa-orchestrator-agent.md` está na versão 2.0.0 com `date` atualizado.
- [ ] `## Triggers / Menu` contém `QE`, `TPT` (Momento 1), `QS` (deprecado), `PT` e `RS`.
- [ ] `## Pre-condition Gate (QE)` existe com 4 passos bloqueantes + 1 aviso, usando os paths
      reais dos agentes produtores.
- [ ] A mensagem de bloqueio do `QE` emite o sinal `QE DEFERRED`.
- [ ] `## Routing — Trigger QE` preserva ET VERIFICATION GATE, FQ COMPLETION GATE, execução do
      `qa_test_runner.py` e a geração do `qa-master-report.md`.
- [ ] `## Routing — Trigger QS` é um stub de depreciação que delega ao `QE`.
- [ ] `## Routing — Trigger PT` e `## Routing — Trigger RS` existem — zero referências `§Routing
      — Trigger X` sem seção correspondente.
- [ ] `FQ` consta da lista do invariante em §Terminal Mandatory Steps.
- [ ] A tabela "Resumo de cobertura por trigger" lista todos os códigos do menu.
- [ ] O bloco `pipeline_observer.py` usa `--version 2.0.0`.
- [ ] `CHANGELOG.md` tem entrada MAJOR para `ava-qa-orchestrator` v1.3.0 → v2.0.0.

## Dependencies

- `specs/029-unify-test-plan-tobe` — origem do trigger `TPT` e do `ava-test-plan-tobe` unificado.
- Agentes upstream: `ava-stack-orchestrator` (trigger `SG`, esteira de código F4);
  `ava-devops-orchestrator` (trigger `DE`, Momento 2); `ava-test-plan-tobe` (trigger `TP`).
- Agentes consumidos pelo `QE`: `ava-qa-gaps-requirements`, `ava-qa-behavior-mapping`,
  `ava-qa-scenario-generator`, `ava-qa-test-case-generator`, `ava-qa-script-generator`,
  `ava-qa-db-integrity-test`, `ava-qa-contract-test-generator`,
  `ava-qa-frontend-test-generator`, `ava-qa-exploratory`, `ava-qa-evidence-capture`,
  `ava-qa-bridge-fastqa-tobe`.
- Agente downstream: `ava-master-orchestrator` (despacha o QA em F5).

## Exclusions

- **Não alterar `master-orchestrator.md`** nesta spec. Consequência assumida: o Step 5.1 despacha
  `QS` em F5, antes do `DE`; o gate `QE` falhará no Passo 4 e emitirá `QE DEFERRED`; o master
  registrará WARN e avançará para F6 — comportamento já previsto na sua linha 686
  (*"QA é não-bloqueante"*), sem hard stop. **Efeito prático**: na esteira automática (`FP`), a
  execução QA passa a exigir invocação manual de `QE` após F6.
- **Follow-up para uma rodada futura**: mover o dispatch QA no `master-orchestrator.md` para
  depois do Step 6 (ou criar um Step 6.5) passando `trigger: QE`, restaurando a automação
  fim-a-fim.
- **Não criar um agente de parity test** no módulo QA — o executor legítimo é o
  `ava-devops-compare-version`.
- **Não corrigir o gate F6 do `master-orchestrator.md`** (Step 6.3), que verifica
  `outputs/devops/{iac,ci,cd}/` enquanto os agentes DevOps escrevem em `outputs/tobe/infra/` e
  `outputs/tobe/iac/{ci,cd}/`. Discrepância registrada aqui; o Gate (QE) desta spec usa os paths
  reais dos produtores.
- **Não alterar `module.yaml`** — nenhum agente é adicionado ou removido; o arquivo lista apenas
  `id` + `file`.
- **Não alterar `.github/skills/ava-qa-orchestrator/SKILL.md`** — é genérico e apenas aponta para
  o arquivo do agente, sem enumerar triggers.
