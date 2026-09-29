# Agent Specification: Aplicação do contrato de saída no runner da esteira

**Feature Branch**: `041-runner-output-contract-enforcement`
**Created**: 2026-08-18
**Status**: Implemented
**Change Type**: modify-existing (`pipeline_runner 19.py`) — sem agente novo, sem mudança de contrato de agente
**Origem**: `docs/issues/ISSUE-004-speckit-plan-graph-perda-silenciosa.md`

## Problem Statement

A spec 040 introduziu `plan-graph.json` como saída obrigatória de `ava-speckit-planning` e como
`inputs.mandatory` de `ava-speckit-tasks` e `ava-speckit-compliance`. A declaração existe em três
lugares — `speckit/module.yaml`, `pipeline-dag/F3S.yaml` e `planning-agent.md` — e **nenhum é
aplicado por código executável**.

Consequência observada no piloto `nopcommerce-04`: o agente de planning teve a resposta cortada
por `max_tokens` no meio do bloco do grafo; o parser do runner descartou o bloco truncado em
silêncio; a validação pós-passo aprovou por omissão; e a falha só aflorou um passo adiante, no
consumidor, como `SystemExit` que escapa do handler do laço e derruba o processo sem gravar
estado de retomada.

O artefato é declarado, esperado e consumido — mas nunca conferido em quem o produz. Esta spec
fecha essa lacuna no **runner**, que é o executor real da esteira. O CLI declarativo
`ava_pipeline.py` não participa da execução em produção e permanece intocado.

## User Stories

### US1 — Falha atribuída a quem falhou

Como operador da esteira, quero que um passo que não gravou suas saídas declaradas seja reprovado
**no próprio passo**, para não descobrir o problema horas depois em outro agente.

### US2 — Resposta cortada nunca vira sucesso

Como operador, quero que `stop_reason == max_tokens` reprove o passo e preserve o conteúdo
parcial em disco, para diagnosticar sem reexecutar às cegas.

### US3 — Nada de conteúdo gerado é descartado

Como operador, quero que todo bloco `FILE` presente na resposta seja materializado — completo ou
como `.PARTIAL` — para que trabalho de inferência já pago nunca se perca em silêncio.

### US4 — Insumo ausente não derruba o processo

Como operador, quero que insumo obrigatório ausente encerre a execução de forma limpa, com estado
salvo e dashboard fechado, para poder retomar sem reconstruir o estado à mão.

### US5 — Dependência conferida antes do despacho

Como operador, quero que o runner confira `inputs.mandatory` antes de despachar, com custo zero de
inferência, sem depender do CLI `ava-pipeline` que não é usado nesta esteira.

### US6 — Progresso visível durante o passo

Como operador, quero ver o dashboard avançar **durante** um passo longo, para distinguir um agente
trabalhando de um processo travado — distinção que era impossível justamente quando os dois
sintomas coexistiam.

## Acceptance Scenarios (BDD)

### Nominal

```gherkin
Cenário: passo emite todas as saídas declaradas
  Dado que o DAG declara outputs [plan.md, plan-graph.json] para F3S:planning:{feature}
  E o agente responde com ambos os blocos FILE fechados
  Quando o runner processa a resposta
  Então os dois arquivos existem em disco com tamanho maior que zero
  E val_ok é verdadeiro
  E a fase é registrada em `executed`
```

### Truncamento

```gherkin
Cenário: resposta cortada no meio do segundo artefato
  Dado que o agente emite plan.md fechado e plan-graph.json sem fechamento
  E o stop_reason é max_tokens
  Quando o runner processa a resposta
  Então plan.md é gravado íntegro e NÃO é fatiado em partes
  E plan-graph.json.PARTIAL é gravado com o conteúdo recebido
  E val_ok é falso, com detail citando o artefato incompleto
  E a fase NÃO é registrada em `executed`
```

### Saída declarada ausente

```gherkin
Cenário: agente ignora um artefato do contrato
  Dado que o DAG declara outputs [plan.md, plan-graph.json]
  E o agente responde apenas com plan.md, sem truncamento
  Quando o runner valida o passo
  Então val_ok é falso
  E required_missing contém specs/{feature}/plan-graph.json
```

### Edge — artefato de tamanho zero

```gherkin
Cenário: bloco FILE com corpo vazio
  Dado que o agente emite um bloco FILE cujo corpo é vazio
  Quando o runner valida as saídas declaradas
  Então o arquivo de zero byte conta como AUSENTE
  E o passo é reprovado
```

### Edge — corpo contendo `-->`

```gherkin
Cenário: comentário HTML dentro do corpo de um artefato
  Dado um bloco FILE cujo corpo contém a sequência "-->"
  Quando o runner determina se o bloco fechou
  Então a decisão vem do grupo de captura do marcador `<!-- /FILE -->`
  E não de heurística sobre o sufixo do texto
```

### Insumo obrigatório ausente

```gherkin
Cenário: preflight barra o despacho
  Dado que plan-graph.json não existe para a feature 003
  Quando o runner alcança F3S:tasks:003
  Então nenhuma inferência é gasta
  E a mensagem acionável do context_manifest é exibida
  E a fase entra em `aborted` com detail do insumo faltante
  E runner-state.json e pipeline-status.html são gravados antes de encerrar
```

### Retomada

```gherkin
Cenário: retomar após bloqueio por insumo
  Dado um runner-state.json salvo com F3S:tasks:003 em `aborted`
  Quando o operador retoma a execução
  Então os passos em `executed` são pulados
  E F3S:tasks:003 é reavaliado pelo preflight
```

### Observabilidade em tempo real

```gherkin
Cenário: passo longo em streaming
  Dado um passo de agente que leva 700 segundos
  Quando o modelo está emitindo tokens
  Então pipeline-status.html é reescrito no máximo a cada 3 segundos
  E a linha do passo exibe o tempo decorrido corrente e a saída acumulada
  E a escrita é estrangulada: uma rajada de 50.000 chamadas não gera 50.000 escritas
```

```gherkin
Cenário: retomada de execução
  Dado um estado salvo com 11 passos executados
  Quando o runner varre os passos já concluídos
  Então o dashboard reflete o estado restaurado durante a varredura
  E reflete a lista de 20 passos expandidos antes do primeiro despacho
```

```gherkin
Cenário: dashboard nunca derruba a execução
  Dado que a escrita do HTML falha por qualquer motivo
  Quando o heartbeat é chamado
  Então a exceção é engolida e o passo prossegue normalmente
```

## Quality Gate

- Nenhum passo de agente pode ir para `executed` com `val_ok` falso.
- Nenhum bloco `FILE` presente na resposta pode deixar de gerar arquivo — completo ou `.PARTIAL`.
- Nenhum caminho de erro do laço principal pode encerrar sem `_save_runner_state`.
- O contrato de fim de fase (`PHASE_ARTIFACT_CONTRACT`) não pode ser aplicado a passo
  intermediário: exige artefatos que só existem no fim da fase.

## Out of Scope

- Alterar contratos de agentes (`planning-agent.md`, `tasks-agent.md`) ou o schema
  `speckit-plan-graph`.
- Alterar `ava_pipeline.py` (CLI declarativo, fora do caminho de execução).
- Produzir `plan-graph.json` deterministicamente. Registrado como trabalho futuro em `plan.md`.
