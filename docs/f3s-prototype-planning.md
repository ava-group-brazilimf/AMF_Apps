# F3S — Protótipo, APIs e integração como fontes formais do planejamento

> Complementa `src/shared/data/pipeline-dag/F3S.yaml`, que continua sendo a
> **fonte de verdade** do despacho da fase. Este documento explica o *porquê* e o
> fluxo; o YAML declara o *o quê*. Não há uma segunda declaração do DAG aqui.

## O defeito que esta camada corrige

A F3S planejava frontend sem olhar o protótipo. `screen-list.md` servia só para
associar tela → bounded context por *slug*, e `index.html` não entrava em lugar
nenhum do planejamento. Duas medições:

- **`nopcommerce-02-cli-ava` (RC-04)** — o agente de protótipo produziu
  `design-tokens.json`, `screen-list.md` e 15 telas HTML; o agente de frontend
  não consumia nenhum dos três como entrada obrigatória. Resultado: **7 de 15
  telas ausentes do código, 2 fiéis (13%)**, catálogo B2C entregue como tabela
  administrativa.
- **`cadastro-funcionario-03`** — `verify_command` escrito em prosa pelo SpecKit
  (`ng build --configuration=production …`). `ng` não existe no PATH antes do
  `npm install`: exit 127 em três tentativas, seis remediações de LLM, 251s
  gastos num erro que nenhum agente conserta escrevendo código.

Um plano sem task de tela produz código sem tela. A F4 não inventa o que não
lhe pediram — e não deve.

## O fluxo, com o que mudou marcado

```
wave2   prototype_manifest.py       → prototype-implementation-manifest.json   [NOVO]
        speckit_wave_manifest.py    → wave-spec-manifest.json  (+ recorte por wave)
wave3   ava-speckit-specification   → spec.md  (+ 18 subseções de protótipo)
wave4   ava-speckit-planning        → plan.md + plan-graph.json  (v3.1.0)
wave4a  speckit_task_compiler diagnose --plans-only
wave5   ava-speckit-tasks           → task-fragment.json  (v3.1.0)
wave5a  f4s_scaffold_injector.py
wave5b  fragment_repair → compile → production_gate → reconciler → ledger
        → checks (speckit_traceability)
        → checks (speckit_frontend_integration)                                [NOVO]
wave6   compliance → normalize → reconcile → gate humano → exit gate
```

## Artefato novo: `prototype-implementation-manifest.json`

Local canônico: `outputs/tobe/speckit/` — o mesmo `output_base` do resto da fase.
Schema: `src/shared/schemas/speckit-prototype-manifest.schema.json` (v1.0.0).

Extração **estática**. Nenhum JavaScript do protótipo é executado; `onclick=
"showScreen('x')"` é lido como *texto* para descobrir o alvo de navegação.
Nenhuma etapa usa LLM.

| Bloco | Conteúdo | IDs estáveis |
|---|---|---|
| `prototype` | entrypoint, `checksum`, `content_checksum`, assets | — |
| `design_system` | cores, tipografia, espaçamento, outros tokens, breakpoints, ícones, estilos globais, padrões de componente | `TOK-*`, `BPT-*`, `ICO-*`, `PAT-*` |
| `screens[]` | rota, BC, layout, componentes, formulários, tabelas, ações, estados, tokens, endpoints, acessibilidade, responsividade | `SCR-*`, `CMP-*`, `FRM-*`, `FLD-*`, `TBL-*`, `ACT-*` |
| `shared_components[]` | componentes usados por mais de uma tela | `CMP-*` |
| `routes[]` / `flows[]` | rotas e fluxos de navegação | `RTE-*`, `FLW-*` |
| `warnings[]` | `PM-0xx` estruturados | — |

**O manifesto não inventa.** Comportamento não identificável vira warning
(`PM-006` tela sem linha no inventário, `PM-008` tela dinâmica sem endpoint,
`PM-030` asset externo, `PM-031` asset local quebrado). Asset externo é
registrado como dependência e **nunca baixado**. Referência que escapa do
workspace é recusada (`PM-010`/`PM-011`).

### Determinismo

Toda coleção sai ordenada por id; os ids derivam do conteúdo. `generated_at` é o
único campo não normativo e está fora dos dois checksums. Travado por
`test_cenario_10_determinismo_entre_execucoes`.

## Recorte fechado por wave

`speckit_wave_manifest.py` anexa `features[].prototype` a cada feature de
codegen: só as telas dos bounded contexts daquela wave, os componentes que essas
telas usam, suas rotas, seus tokens e as operações de API que consomem.

**O agente lê o manifesto, nunca o `index.html`.** É isso que impede a fatia
vertical de voltar a ser ingestão da base inteira.

`owns_shared_components: true` aparece em **uma única** feature (a foundation,
por padrão). Ela cria o Design System e os componentes compartilhados; as demais
consomem. Sem essa decisão única, cada wave reivindicava `create` do mesmo botão
— foram 31 conflitos de ownership em `cadastro-funcionarios-04`, 24 cross-wave.

## A junção protótipo → API

`screen-list.md` declara `GET /api/v1/funcionarios`; o OpenAPI declara
`operationId: GetAllFuncionarios` sob `paths: /funcionarios` com
`servers: …/api/v1`. O índice de endpoints casa as duas grafias — sem isso,
nenhum endpoint de tela resolvia para `operationId`, e o elo frontend↔backend
ficava vazio exatamente no ponto que esta camada existe para consertar.

Endpoint sem correspondência sai com `operation_id: null` e vira aviso.
**Nenhuma operação é inventada.**

## `work_kind` — taxonomia sem quebrar o roteamento

`task_type` continua sendo só `frontend`/`backend`: é a chave de
`f4_routing.component_type_for_task`, e ampliá-la quebraria o despacho da F4.
`work_kind` é o eixo fino que os gates leem:

`design_system` · `frontend_layout` · `frontend_component` · `frontend_page` ·
`frontend_route` · `frontend_form` · `frontend_validation` · `frontend_api_client` ·
`frontend_state` · `frontend_integration` · `backend_api_contract` ·
`backend_api_implementation` · `backend_domain` · `backend_persistence` ·
`integration_test` · `visual_regression_test` · `accessibility_test` ·
`end_to_end_test` · `scaffold`

## Tokens de contrato canônicos

`produces`/`consumes` seguem uma gramática, normalizada por
`speckit_task_compiler.normalize_token()` — a mesma função que
`speckit_fragment_repair` usa, para que reparo e compilação não discordem:

`api-contract:{operationId}` · `api-implementation:{operationId}` ·
`api-client:{operationId}` · `screen:{SCR-*}` · `component:{CMP-*}` ·
`route:{RTE-*}` · `design-token:{TOK-*}` · `test:e2e:{FLW-*}` ·
`contract:{nome}` (legado) · `artifact:scaffold:{stack}`

Fluxo funcional que o grafo passa a expressar:

```
backend_api_contract → backend_api_implementation → integration_test
                    ↘ frontend_api_client → frontend_integration → end_to_end_test
```

O frontend paraleliza quando depende só do contrato; a **integração real**
depende da implementação.

## `verify_profile` em vez de `verify_command`

`src/shared/tools/verify_profiles.py` resolve o comando a partir da stack, nesta
precedência:

1. verificador determinístico da stack (`f4s_build_runner.STACK_VERIFIERS` —
   Angular: install → build → boot → health; .NET: structure → restore → build → test);
2. script declarado no `package.json` (com o package manager do **lockfile**);
3. comando padrão da stack;
4. só então o texto da LLM — e ainda assim normalizado, nunca aceito cru.

Perfis: `frontend-build` · `frontend-unit-test` · `frontend-lint` ·
`backend-build` · `backend-unit-test` · `backend-lint` · `integration-test` ·
`e2e-test` · `accessibility-test` · `visual-regression-test` · `lint` · `none`.

Um perfil de família errada é corrigido pela stack (`dotnet build` numa task
Angular vira `frontend-build`), usando `scaffold_paths.STACK_COMPONENT_TYPES`
como autoridade — não há um segundo mapa de stacks.

O comando planejado usa `{python}`, não um caminho absoluto de interpretador:
o comando vai para um artefato, e um caminho de máquina tornaria o
`graph_checksum` não reproduzível.

## Os 12 checks novos

Suíte `speckit_frontend_integration`. Relatório estruturado em
`outputs/tobe/speckit/frontend-integration-checks.json`, um achado por check com
`check_id`, `status`, `severity`, `feature`, `wave`, `task_ids`,
`affected_items`, `evidence` e `recommended_action`.

| Check | Reprova quando |
|---|---|
| `PROTOTYPE-SCREEN-COVERAGE` | tela de wave codegen sem task de frontend |
| `PROTOTYPE-COMPONENT-COVERAGE` | componente **estrutural** sem arquivo/task |
| `DESIGN-SYSTEM-COVERAGE` | token ou componente compartilhado sem owner |
| `ROUTE-COVERAGE` | rota em escopo sem task de configuração |
| `API-OPERATION-COVERAGE` | `operationId` em escopo sem task backend |
| `FRONTEND-API-CLIENT-COVERAGE` | API consumida por tela sem client frontend |
| `FRONTEND-BACKEND-INTEGRATION` | tela dinâmica sem task de integração |
| `E2E-COVERAGE` | fluxo crítico sem task end-to-end |
| `SOURCE-REF-INTEGRITY` | referência a artefato ou âncora inexistente |
| `VERIFY-PROFILE-VALIDITY` | comando/perfil incompatível com a stack |
| `SINGLE-CREATE-OWNER` | arquivo com mais de um `create` |
| `PROTOTYPE-CHECKSUM-CONSISTENCY` | protótipo mudou depois do planejamento |

Botão e campo **não** são cobrados por `PROTOTYPE-COMPONENT-COVERAGE`: são
implementados dentro do formulário, tabela ou toolbar que os contém. Um gate que
nunca passa é um gate que se aprende a ignorar.

## Política de erro (inalterada, e por quê)

Continua valendo o cabeçalho do `F3S.yaml`: **erro não trava fase**. Estes checks
reprovam lacuna de *planejamento*, que é lacuna de qualidade — são
`blocking=False`, e `exit_gate.suites_on_fail: warn` segue intacto.

O que mudou não é a consequência, é a **existência do achado**: até aqui um
frontend planejado sem backend correspondente compilava e ninguém era avisado.

Erro **técnico** (I/O, JSON inválido, schema inválido, `project-config.yaml`
ausente, stack não identificável) continua sendo exit != 0. `PrototypeManifestError`
é dessa classe.

## Compatibilidade

- `plan-graph.json` e `task-fragment.json` aceitam `3.0.0` **e** `3.1.0`. Todos
  os campos novos são opcionais; um projeto planejado antes desta mudança compila
  sem conversão e sem perder nada.
- `traceability.json` continua v4 e continua a espinha **imutável**;
  `tasks-progress.json` continua o razão mutável, e `task_ledger` continua
  recusando qualquer `recorded_by` que pareça agente.
- `screen_id` singular continua sendo emitido, alimentado por `screen_ids[0]`.
- Plano legado sem `work_kind`: os checks de tela aceitam qualquer task de
  frontend que cite o `screen_id`. Exigir a taxonomia nova de projeto legado
  transformaria migração em reprovação em massa.
- `graph_checksum` não mudou para entradas 3.0.0 inalteradas (verificado em
  `cadastro-funcionarios-04`: `2810cded…` antes e depois).

## Testes

- `tests/tools/test_prototype_manifest.py` — 15 testes: extração, estados,
  formulários, tabelas, tela estática, protótipo ausente, checksum, determinismo,
  path traversal, asset externo, casamento de nomes.
- `tests/tools/test_f3s_frontend_integration.py` — 24 testes: recorte por wave,
  junção com o OpenAPI, grafo frontend↔backend, invenção de tela/API,
  ownership disputado, perfis de verificação, React+.NET e Angular+Spring Boot,
  e os 12 checks.
