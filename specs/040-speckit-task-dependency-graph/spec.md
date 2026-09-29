# Agent Specification: Grafo de dependências das tasks SpecKit

**Feature Branch**: `040-speckit-task-dependency-graph`  
**Created**: 2026-08-14  
**Status**: In Progress  
**Change Type**: modify-existing (`ava-speckit-planning`, `ava-speckit-tasks`,
`ava-speckit-orchestrator`, `ava-speckit-compliance`) + deterministic tooling

## Problem Statement

O `traceability.json` já aceita `depends_on`, mas a dependência é declarada pela LLM e não é
validada como grafo. Referências inexistentes e ciclos passam pela F3S e deixam a F4 sem tasks
prontas, sem distinguir conclusão de deadlock. Além disso, o fan-out atual é calculado uma vez
por grupo antes da execução, portanto não libera sucessores conforme predecessores são
verificados.

## User Stories

### US1 — Grafo válido antes da geração de código

Como operador da esteira, quero que referências ausentes, autorreferências e ciclos sejam
detectados no gate da F3S, para que a F4 nunca inicie com uma ordem impossível.

### US2 — Ordem determinística e rastreável

Como agente coder, quero receber exatamente uma task pronta, cuja posição e predecessoras
tenham sido calculadas por ferramenta, para não escolher trabalho fora de ordem.

### US3 — Retomada sem gaps

Como operador, quero reiniciar a F4 e continuar da primeira task pronta, sem regerar tasks
verificadas e sem liberar descendentes de uma task bloqueada.

### US4 — Migração compatível

Como mantenedor, quero continuar lendo `traceability.json` v1 durante a migração, com defaults
explícitos, enquanto novas execuções produzem o contrato v2.

### US5 — Dependência explícita entre frontend e backend

Como desenvolvedor frontend, quero identificar quais tasks são de frontend e quais tasks backend
expõem as APIs que cada tela consome, para implementar a integração somente depois do endpoint
correspondente estar verificado.

### US6 — Especificações verticais por migration wave

Como responsável pela migração, quero uma especificação por wave que combine regras de negócio,
APIs, backlog, telas e testes pertinentes, para que cada plano represente uma unidade entregável
e preserve as dependências definidas no plano de migração.

## Functional Requirements

- **FR-001** — O sistema deve construir um DAG a partir de `task_id` e `depends_on`.
- **FR-002** — IDs duplicados, dependências duplicadas, autorreferências e referências ausentes
  devem reprovar antes da execução.
- **FR-003** — Ciclos devem reprovar com o caminho causal completo e reproduzível.
- **FR-004** — O DAG deve produzir ordem e ondas topológicas estáveis, com desempate por
  prioridade, grupo e ID.
- **FR-005** — O plano deve declarar grupos, ownership de arquivos e relações
  produtor/consumidor em formato estruturado.
- **FR-006** — Cada despacho de tasks deve produzir um fragmento local; somente um compilador
  determinístico pode gravar o `traceability.json` global.
- **FR-007** — Apenas status `verified`, provado por exit code zero, satisfaz uma dependência.
- **FR-008** — O scheduler deve recalcular tasks prontas após cada resultado.
- **FR-009** — Ausência de task pronta deve ser classificada como `complete`, `waiting`,
  `blocked_by_terminal`, `dangling_dependency` ou `cycle`.
- **FR-010** — O gate de saída da F3S deve bloquear a F4 quando o DAG for inválido.
- **FR-011** — Cada arquivo planejado e cada task devem declarar `task_type` como `backend` ou
  `frontend`, sem inferência por caminho ou framework.
- **FR-012** — A task backend que expõe uma operação deve produzir `api:{operationId}` e toda task
  frontend que chama essa operação deve consumir o mesmo token.
- **FR-013** — O compilador deve derivar `backend_dependencies` para cada task frontend como o
  subconjunto exato de predecessoras diretas classificadas como backend; tasks backend devem ter
  a lista vazia.
- **FR-014** — O CHK-SK-016 deve reprovar `task_type` inválido ou `backend_dependencies`
  inconsistente com o DAG.
- **FR-015** — `wave-model.json` deve definir identidade, ordem, BCs e dependências das specs;
  `wave-plan.md` deve complementar e funcionar como fallback quando o modelo não existir.
- **FR-016** — Uma ferramenta determinística deve gerar `wave-spec-manifest.json` com uma feature
  por wave e somente as fontes/âncoras pertinentes.
- **FR-017** — Uma task deve aceitar múltiplos pares `{artifact, anchor}` e todos devem ser
  verificados por `CHK-SK-006`.
- **FR-018** — O compilador deve transformar dependências entre migration waves com codegen em
  arestas entre tasks terminais da predecessora e tasks raiz da sucessora.
- **FR-019** — Waves `foundation` e `cutover` devem gerar spec, mas não tasks de backend/frontend;
  seu trabalho permanece nas fases proprietárias de DevOps/Deliverables.
- **FR-020** — O gate deve derivar a cardinalidade e os artefatos esperados do manifesto, sem
  constantes como sete specs ou 35 arquivos.
- **FR-021** — Âncora formal sem associação determinística a uma wave deve bloquear a geração
  do manifesto e nomear os IDs órfãos; atribuição por similaridade textual é proibida.

## Non-Functional Requirements

- **NFR-001** — Tooling de grafo deve usar somente a biblioteca padrão do Python.
- **NFR-002** — A mesma implementação deve ser consumida por checks, ledger e runners.
- **NFR-003** — A ordenação deve ser determinística independentemente da ordem do JSON.
- **NFR-004** — O diagnóstico deve ser serializável em JSON e acionável por operador.
- **NFR-005** — Artefatos já existentes em `projects/*/outputs/` não serão reescritos manualmente.

## BDD Scenarios

### Nominal — branch e join

```gherkin
Given uma task raiz e duas tasks independentes que dependem dela
And uma task final que depende das duas branches
When o grafo é analisado
Then a raiz aparece na primeira onda
And as duas branches aparecem juntas na segunda onda
And a task final aparece na terceira onda
```

### Edge — referência inexistente

```gherkin
Given uma task que depende de um task_id ausente
When o gate da F3S valida a rastreabilidade
Then o gate reprova com o task_id consumidor e a referência ausente
And a F4 não é iniciada
```

### Quality gate — ciclo

```gherkin
Given as dependências T-A -> T-B -> T-C -> T-A
When o gate da F3S valida a rastreabilidade
Then CHK-SK-017 reprova
And o diagnóstico contém T-A -> T-B -> T-C -> T-A
And nenhuma task do ciclo é despachada
```

### Retomada — predecessora verificada

```gherkin
Given uma task predecessora com evidência de exit code zero
And uma task sucessora pendente
When a F4 é retomada
Then a predecessora não é regerada
And a sucessora passa a ser a próxima task pronta
```

### Integração — tela consome endpoint

```gherkin
Given uma task backend que produz api:getCart
And uma task frontend de tela que consome api:getCart
When o compilador constrói o grafo global
Then a task frontend depende diretamente da task backend
And a task frontend declara a task backend em backend_dependencies
And a F4 não libera a tela antes de o endpoint estar verified
```

### Planejamento — wave combina múltiplas fontes

```gherkin
Given W3 contém Orders e Shipping
And o manifesto liga BR-CHECKOUT-001, PlaceOrder e TC-ORD-007 a W3
When a especificação de W3 é gerada
Then uma única spec cobre regra, endpoint e teste
And a task correspondente preserva os três pares artifact/anchor
And CHK-SK-006 verifica todos os três pares
```

### Ordem — dependência entre migration waves

```gherkin
Given W3 depende de W2 no wave-model.json
And ambas possuem tasks de codegen
When o compilador constrói o DAG global
Then toda task raiz de W3 depende das tasks terminais de W2
And nenhuma task de W3 fica pronta antes de W2 estar verified
```

## Acceptance Criteria

- [ ] O grafo rejeita todas as formas inválidas de FR-002 e FR-003.
- [ ] Ordem e ondas são estáveis em testes com entrada embaralhada.
- [ ] CHK-SK-016..018 bloqueiam o gate de saída da F3S.
- [ ] O ledger nunca libera sucessora sem todas as predecessoras `verified`.
- [ ] Os runners executam a F3S e a F4 de forma incremental.
- [ ] Contratos e wrappers dos agentes alterados estão sincronizados.
- [ ] Toda task compilada indica `backend` ou `frontend`.
- [ ] Uma tela consumidora de API lista diretamente a task backend produtora do endpoint.
- [ ] CHK-SK-016 bloqueia projeções frontend → backend inconsistentes.
- [ ] Um projeto piloto completa F3S e lista a ordem da F4 sem deadlock silencioso.
- [ ] O número de specs coincide com `total_waves` do manifesto.
- [ ] Uma task vertical preserva e valida referências de BR, API e test case.
- [ ] A ordem das migration waves aparece no DAG sem reutilizar `execution_wave`.

## Out of Scope

- Execução paralela real de tasks na primeira entrega.
- Inferência de dependência baseada apenas em texto livre ou nomes semelhantes.
- Alterações nas regras de negócio dos coders.
- Edição manual de artefatos em `projects/{project_name}/outputs/`.