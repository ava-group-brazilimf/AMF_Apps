# Agent Specification: Camada de planejamento SpecKit (`F3S`)

**Feature Branch**: `039-speckit-planning-layer`
**Created**: 2026-08-12
**Status**: Draft
**Change Type**: new-agent (7 agentes no módulo `speckit`)
+ add-new (`context_manifest.py` · `task_ledger.py` · `F3S.yaml` · 2 suítes de check ·
2 schemas · `artifact_gate_speckit.py`)
+ modify-existing (`ava-pipeline.yaml` · `pipeline_plan.py` · `sdk_engine.py` ·
`ava_pipeline.py` · `pipeline_runner 19.py` · `agent_registry.py` · `checks/context.py` ·
`readiness-gate.md` · 3 agentes coder · `artifact-map.yaml` · `module.yaml` · `CHANGELOG.md`)
**Input**: "Introduzir o SpecKit como camada de planejamento dentro da esteira de modernização.
Os agentes de geração de código (Angular, React, .NET) estão produzindo código com
inconsistências arquiteturais, implementações incompletas e problemas de compilação. A hipótese
é que gerar Constitution, Specifications, Plans e Tasks antes da geração de código melhora
conformidade arquitetural, qualidade, completude, rastreabilidade, taxa de compilação e
aderência às regras de negócio."

## Amendment 2026-08-21 — Output resilience and W0 scaffold

- W0/Foundation is executable and owns backend/frontend scaffold planning.
- Framework CLIs generate the original project skeleton; the LLM selects and manages parameters.
- Validation findings never prevent mandatory artifact persistence.
- `speckit_output_reconciler.py` materializes missing contracts as explicit placeholders.
- The pipeline continues after non-blocking failures, while F4 requires completeness `READY`.

---

## 1. Identidade

Sete agentes novos em um módulo novo, executados como o grupo **`F3S`** entre a F3 (Protótipo)
e a F4 (Stack Generation). Mais a infraestrutura determinística que faz os artefatos chegarem
até quem os consome — sem ela a camada não muda nenhum número.

| Componente | Papel |
|---|---|
| `src/modules/ava-fabric-agents/speckit/` | **Novo.** Módulo com os 7 agentes, templates e o gate |
| `src/shared/tools/context_manifest.py` | **Novo.** Resolução explícita de insumos por passo — implementação única |
| `src/shared/tools/task_ledger.py` | **Novo.** Livro-razão de progresso; transições de status a partir de exit code real |
| `src/shared/data/pipeline-dag/F3S.yaml` | **Novo.** DAG da F3S e as fatias de contexto por agente — fonte da verdade |
| `src/shared/schemas/speckit-traceability.schema.json` | **Novo.** Contrato do `traceability.json` |
| `src/shared/schemas/speckit-task-state.schema.json` | **Novo.** Contrato do `tasks-state.json` |
| `src/shared/checks/suites/speckit_traceability.py` | **Novo.** CHK-SK-001..012 |
| `src/shared/checks/suites/prototype_coverage.py` | **Novo.** CHK-PROTO-001..007 |
| `src/shared/data/ava-pipeline.yaml` | **Existe.** Ganha `inputs:`, `foreach:` e os passos da F3S |
| `src/shared/tools/sdk_engine.py` | **Existe.** Delega o contexto ao `context_manifest` |
| `pipeline_runner 19.py` | **Existe.** Importa o mesmo módulo; `PIPELINE` ganha a F3S |
| `src/modules/ava-fabric-agents/shared/readiness-gate.md` | **Existe.** C2 finalmente tem produtor |

**Agentes novos**: 7 (`ava-speckit-*`). **Skills novas**: 7. **Agentes alterados**: 3 coders
(contrato de entrada). **Não tocado por restrição**: `copilot-cli-headroom.bat` e
`copilot-cli-v1.bat` — CA02 da spec 033.

---

## 2. Problem Statement

A auditoria de `projects/nopcommerce-02-cli-ava` (`outputs/audit/auditoria-codigo-gerado.md`,
2026-08-11) mediu sete eixos contra o código gerado pela esteira:

| Eixo | Conformidade | Veredito |
|---|---|---|
| Frontend × Protótipo | ~13% | 🔴 |
| Regras de negócio | ~17% | 🔴 |
| Testes unitários × `test-cases.md` | ~7% | 🔴 |
| APIs × OpenAPI 3.1 | ~14% | 🔴 |
| Stack de configuração | ~65% | 🟠 |
| Arquitetura TO-BE | ~60% | 🟠 |
| ADRs (8 registros) | ~38% | 🔴 |
| `dotnet build` real | — | 🔴 **FALHA** |

O diagnóstico desta spec é que a causa dominante **não é qualidade de prompt**. É mecânica.

### P-1 — Nenhum artefato TO-BE chegou ao gerador de código

`load_context()` — em `pipeline_runner 19.py:743-779` e em `sdk_engine.py:135-176` — injeta o
corpo dos artefatos percorrendo `sorted(outputs.rglob("*"))` e pegando os **N primeiros** com
sufixo em `(.md, .mmd, .yaml, .json)`. N = 60 no runner de produção, 30 no motor do CLI. Em
ordem alfabética, `asis/` precede `tobe/`. Medido no projeto real:

| Injetado em todo passo depois da F1 | Qtd |
|---|---|
| `asis/ast-raw/**` (dumps brutos de AST) | 30 |
| demais `asis/**` | 30 |
| **`tobe/**` — qualquer coisa** | **0** |

A janela fecha exatamente em `asis/docs/screen-flow-manifest.json`. Tudo que a F4 precisava
está depois:

| Artefato exigido pelos coders | Posição | Injetado? |
|---|---|---|
| `tobe/docs/api-map.md` | 116 | ✗ |
| `tobe/docs/architecture-blueprint.md` | 117 | ✗ |
| `tobe/docs/architecture-decision-matrix.md` | 118 | ✗ |
| `tobe/docs/backlog-tobe.md` | 119 | ✗ |
| `tobe/docs/openapi/openapi-spec.yaml` | 144 | ✗ |
| `tobe/docs/regras-negocio.md` | 145 | ✗ |
| `tobe/docs/tech-framework-document.md` | 151 | ✗ |
| `tobe/docs/wave-plan.md` | 154 | ✗ |
| `tobe/prototype/design-tokens.json` | 164 | ✗ |
| `tobe/prototype/screen-list.md` | 167 | ✗ |
| `tobe/qa/test-cases.md` | 169 | ✗ |
| `tobe/prototype/index.html` | — | ✗ **nunca elegível** (`.html` fora da allowlist de sufixos) |

`asis/docs/business-rules.md` caiu na posição 57 — a única razão de regras de negócio marcarem
17% em vez de 0%.

Isto explica cada eixo da auditoria e confirma de forma independente as causas-raiz RC-04,
RC-05 e RC-07 do próprio documento. O
[protocolo P2C](../../src/modules/ava-fabric-agents/shared/prototype-conversion-protocol.md)
está bem escrito e nunca foi desobedecido pelo modelo — os arquivos simplesmente não chegaram.

> **Consequência direta para esta spec**: artefatos SpecKit escritos em `outputs/tobe/speckit/`
> ordenam **depois** de `asis/` também. Sem a Fase 0 eles seriam tão invisíveis quanto os
> artefatos TO-BE são hoje, e a camada mediria zero de melhoria.

### P-2 — A F4 é uma chamada, não uma esteira

`execution-report_20260811_193456.md` registra a F4 como **um único** despacho: 624.278 tokens
de entrada, 82.878 de saída contra um teto de 128.000, 14,9 min, **140 arquivos** (77 `.cs` +
40 `.ts`) em uma resposta. O motor SDK carrega apenas o `spec_path` do orquestrador e proíbe
tools, então os 13 agentes coder e os 13 `build_cycle_templates` declarados em
`tech-stack/module.yaml` — inclusive o `coder-angular-frontend.md` de 4955 linhas, que carrega
as regras do P2C — nunca foram carregados e nunca rodaram. `pipeline_mode: "build-cycle"` no
`project-config.yaml` não teve efeito algum.

Gerar uma solução inteira dentro de um orçamento de saída é o que produziu o truncamento em
"vertical slice" (RC-01) e os relatórios de build simulados (RC-02).

### P-3 — Já existe um consumidor de SpecKit sem produtor

`shared/readiness-gate.md`, critério **C2** (HARD, bloqueia toda wave do Build Cycle), faz glob
em `outputs/tobe/docs/spec-kit/*.md`, exige seis seções obrigatórias e lê
`signoffs.spec_kit_approved`. Nada no repositório produz esse arquivo. Ainda assim o gate do
nopcommerce-02 retornou `APPROVED` com 92,5% e `"spec_kit_approved": true` — um gate aprovando
com base em assinatura para um artefato inexistente.

### P-4 — Rastreabilidade é declarativa, não verificável

A auditoria sobre a `traceability-matrix.md` gerada: *"marca todas as 15 linhas AS-IS→TO-BE→TC
como ✅ … nenhuma dessas classes existe no código gerado. A matriz é um falso positivo
integral."* Rastreabilidade em prosa não é rastreabilidade — é narrativa.

---

## 3. Decision

### 3.1 Fase 0 — Entrega determinística de contexto (pré-requisito)

Substituir "os N primeiros em ordem alfabética" por um manifesto de entrada declarado,
explícito e *fail-fast*.

`src/shared/tools/context_manifest.py` é a **implementação única**, importada pelos dois
runners. O modo de falha documentado deste repositório é fonte-da-verdade duplicada
(`agent_registry.py`, `artifact_gate_tobe.py` e `pipeline-dag/F1.yaml` todos carregam avisos a
respeito) — este módulo não pode virar mais um espelho.

Vocabulário de tiers, herdado dos Input Contracts que os coders já usam
(`CRÍTICOS` / `IMPORTANTES` / `OPCIONAIS`) e do `slice:` do `pipeline-dag/F1.yaml`:

- `mandatory:` — ausente ⇒ o passo **não roda**, exit code 2. Nunca degrada em silêncio.
- `advisory:` — ausente ⇒ WARN registrado no log do passo; a execução continua.
- Globs permitidos; a ordem de injeção é a de **declaração**, não a do filesystem.
- Allowlist de sufixos ganha `.html`, `.ts`, `.cs`, `.scss`, `.sql`, `.props`, `.csproj`.
- Passo sem `inputs` declarado mantém o comportamento de hoje — nada existente quebra.

### 3.2 Fase 1 — O módulo `speckit` (7 agentes)

Grupo `F3S`, entre F3 e F4. O namespace `ava-speckit-*` evita colisão: `ava-tobe-spec` já é o
gerador de OpenAPI por BC e `outputs/tobe/docs/spec/` já é produzido pelo
`ava-tobe-user-journeys` sob CQRS.

| Agente | Trigger | Insumos obrigatórios | Saídas |
|---|---|---|---|
| `ava-speckit-orchestrator` | `SK` | — | despacho + `execution-log.json` |
| `ava-speckit-constitution` | `GC` | `project-config.yaml`, `architecture-blueprint.md`, `tech-framework-document.md`, `architecture-decision-matrix.md`, `decisions/ADR-*.md` | `constitution.md` |
| `ava-speckit-specification` | `GS` | `constitution.md` + um artefato-fonte por spec | `specs/spec-*.md` |
| `ava-speckit-prototype-spec` | `GP` | `constitution.md`, `prototype/index.html`, `screen-list.md`, `design-tokens.json`, `openapi/*.yaml`, `figma-spec.md` (advisory) | `specs/spec-prototype.md` |
| `ava-speckit-planning` | `GL` | `constitution.md`, um `specs/spec-*.md` | `plans/plan-*.md` |
| `ava-speckit-tasks` | `GT` | `constitution.md`, um `plans/plan-*.md` | `tasks/tasks-*.md` + linhas de rastreabilidade |
| `ava-speckit-compliance` | `AC` | `constitution.md`, todas as specs/plans/tasks, `traceability.json` | `compliance-report.md`, `compliance-status.json` |

Árvore de saída — `projects/{project_name}/outputs/tobe/speckit/`:

```
constitution.md
specs/    001-business-rules/  spec.md · plan.md · tasks.md
          002-api/ · 003-api-map/ · 004-backlog/
          005-waves/ · 006-test-cases/ · 007-prototype/
traceability.json                 ← espinha rastreável (imutável após a F3S)
tasks-state.json                  ← livro-razão de progresso, do runner
ava-agents-progress.txt           ← log narrativo, append-only
compliance-report.md · compliance-status.json
execution-log.json
```

**Uma especificação por artefato consumido.** O agente de specification é despachado uma vez
por fonte — não uma vez no total — para que cada chamada carregue apenas a sua fonte:

| Fonte | Spec |
|---|---|
| `asis/docs/business-rules.md` + `.json` + `tobe/docs/regras-negocio.md` | `spec-business-rules.md` |
| `tobe/docs/openapi/*.yaml` | `spec-api.md` |
| `tobe/docs/api-map.md` | `spec-api-map.md` |
| `tobe/docs/backlog-tobe.md` | `spec-backlog.md` |
| `tobe/docs/wave-plan.md` + `migration/wave-model.json` | `spec-waves.md` |
| `tobe/qa/test-cases.md` | `spec-test-cases.md` |
| `tobe/prototype/*` | `spec-prototype.md` |

Toda spec carrega as dez seções obrigatórias (Objetivos Funcionais, Regras de Negócio, Modelo
de Domínio, Fluxos de Aplicação, Critérios de Aceite, Tratamento de Erros, Requisitos de
Segurança, Dependências, Casos de Borda, Cenários de Teste) **e** as seis seções que o
readiness-gate C2 confere (`## Context`, `## Input`, `## Processing`, `## Output`,
`## Examples`, `## Failure Modes`) — um artefato satisfaz os dois contratos.

`spec-prototype.md` carrega ainda as dez seções de protótipo (Overview, Screen Inventory,
Navigation Flow, Component Spec, Form & Validation, API Integration Mapping, Frontend
Architecture Mapping, UX & Accessibility, Test Scenarios, Implementation Tasks Input). O
procedimento de extração não é inventado: reusa as regras já especificadas no
`prototype-conversion-protocol.md` §2 — parse do `screen-list.md` indexado por nome de coluna,
o rodapé `<!-- Prototype metadata -->` de cada tela (Screen/BC/API/AS-IS ref/UX rules), o
call-graph de `showScreen()` para navegação e as custom properties do `:root` para tokens. O
P2C deixa de ser prosa consultiva e passa a ser o procedimento de entrada de uma fase que tem
gate determinístico atrás.

### 3.3 Fase 2 — Espinha de rastreabilidade e gates

`traceability.json` é o artefato que sustenta a carga, não as matrizes em prosa. Uma linha por
task, com âncora verificável na fonte:

```json
{ "task_id": "T-PROTO-004", "spec_id": "SPEC-PROTO-007",
  "source_artifact": "tobe/prototype/screen-list.md", "source_anchor": "Carrinho de Compras",
  "screen_id": "screen-cart", "plan_id": "PLAN-PROTO-002",
  "rule_ids": ["BR-CHECKOUT-001"], "api_ops": ["POST /api/v1/cart/items"],
  "test_ids": ["TC-CART-003"], "target_files": ["frontend/src/app/cart/cart.component.ts"] }
```

Nenhuma task de implementação pode existir sem linha correspondente; nenhuma linha pode
apontar para uma âncora que não existe no arquivo-fonte. As duas direções são verificadas.

### 3.4 Fase 3 — Fan-out da F4 e harness de agente longo

`foreach:` no schema de passo expande um passo declarado em N execuções, cada uma despachando o
agente coder **real** com apenas a sua fatia. É isso que tira o orçamento de saída do caminho
crítico: N respostas limitadas em vez de uma resposta de 82.878 tokens contra teto de 128.000.

Com a F4 virando N chamadas, o problema passa a ser de agente de execução longa: cada chamada
começa com janela de contexto nova e precisa saber o que já foi construído. O padrão de
[harnesses eficazes para agentes de execução longa](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
— um contexto *inicializador* que produz os artefatos duráveis, depois contextos de *iteração*
que avançam uma feature por vez e deixam atualizações estruturadas — já descreve o que a F3S é.
Falta emitir os artefatos do harness:

| Artefato do artigo | Nesta esteira |
|---|---|
| agente inicializador | `ava-speckit-orchestrator` — a F3S produz constitution, specs, plans, tasks |
| `feature_list.json`, tudo `"passes": false` | `outputs/tobe/speckit/tasks-state.json`, tudo `"status": "pending"` |
| `claude-progress.txt` | `outputs/tobe/speckit/ava-agents-progress.txt` |
| `init.sh` | `outputs/tobe/source-code/verify.ps1` — restore, build, test, lint |
| histórico git | `outputs/.runs/{run_id}/run.json` + evidência por task concluída |
| uma feature por sessão | uma task pronta por expansão do `foreach` |

`tasks-state.json` é JSON, não Markdown, exatamente pela razão que o artigo dá: o modelo tem
muito menos probabilidade de reescrever ou reformatar um arquivo JSON. Dois arquivos, duas
vidas, deliberadamente não fundidos — `traceability.json` é **imutável** depois da F3S
(checksum conferido pelo gate de saída: uma task não pode perder a proveniência no meio da
execução), `tasks-state.json` é o livro-razão mutável.

**Um desvio deliberado em relação ao artigo.** Lá, o agente vira o `passes` depois de testar.
Aqui ele não pode. A RC-02 encontrou a esteira declarando
`Build Status: ✅ PASS (Simulated — toolchain validation pending)` com o `dotnet build` real
falhando, e a matriz de rastreabilidade marcando 15/15 ✅ para classes inexistentes. Um agente
que se auto-declara concluído é precisamente a falha que este projeto já tem. Portanto:

- **Agentes nunca escrevem em `tasks-state.json`.** Quem escreve é o wrapper do passo, depois
  de rodar `verify.ps1` e as suítes de check, a partir de exit codes reais. O status anda
  `pending → in_progress → verified | failed` e `evidence` registra comando, exit code e log.
- Task cujos arquivos foram escritos mas cuja verificação falhou termina em `failed`, não em
  `verified`, e volta para a fila com `attempts + 1` — com teto, e depois exposta em vez de
  retentada para sempre.
- `ava-agents-progress.txt` é prosa escrita pelo agente e **não carrega afirmação de status**.
  Narrativa e estado ficam separados para que uma narrativa confiante não contamine o razão.

### 3.5 Fase 4 — Fechar o ciclo nos consumidores

C2 do readiness-gate repontado para `outputs/tobe/speckit/specs/*.md`; `prototype_index`,
`prototype_screens` e `design_tokens` promovidos de `OPCIONAIS (WARN)` para
`CRÍTICOS (HARD STOP)` nos coders de frontend; `constitution.md`, `plan-*.md` e `tasks-*.md`
adicionados como `CRÍTICOS`. Degradar em silêncio quando falta o protótipo é como um catálogo
B2C virou uma tabela CRUD administrativa.

---

## 4. User Scenarios (Given-When-Then)

**US-1 — Insumo obrigatório ausente bloqueia o passo**
Given a project whose `outputs/tobe/docs/openapi/` is empty
When the operator runs `ava-pipeline run -p P --phase F3S`
Then the run stops before any inference, names the missing mandatory input and its expected
producer agent, and exits 2.

**US-2 — Os artefatos TO-BE chegam ao gerador**
Given a project with a complete TO-BE and prototype
When the operator runs `ava-pipeline run -p P --phase F4 --dry-run`
Then the resolved input list contains `architecture-blueprint.md`, `openapi/*.yaml`,
`regras-negocio.md`, `prototype/index.html`, `screen-list.md` and `design-tokens.json`.

**US-3 — Uma spec por artefato-fonte**
Given the seven declared sources exist
When the F3S group completes
Then `outputs/tobe/speckit/specs/` holds seven files, each with the ten mandatory sections and the
six readiness-gate sections, and each naming its source artifact in the header.

**US-4 — Toda tela do protótipo vira trabalho rastreável**
Given `screen-list.md` lists 15 screens with status `included`
When `spec-prototype.md`, `plan-prototype.md` and `tasks-prototype.md` are generated
Then every screen has a route, at least one task and at least one test scenario, and
CHK-PROTO-001 through CHK-PROTO-003 pass.

**US-5 — Task sem rastreabilidade reprova o gate**
Given a `tasks-*.md` file containing a task with no row in `traceability.json`
When the F3S exit gate runs
Then CHK-SK-005 fails, the gate exits non-zero and F4 does not start.

**US-6 — A F4 expande em vez de rodar uma vez**
Given `tasks-state.json` holds 42 pending tasks across 4 groups
When the operator runs `ava-pipeline run -p P --phase F4`
Then the plan expands into one step per task in topological order, each dispatching the real
coder agent for its target stack, and a successor starts only after every predecessor is
`verified`.

**US-7 — Execução interrompida retoma sem regerar**
Given an F4 run was interrupted with 12 tasks `verified`
When the operator re-invokes the same command
Then execution resumes at the first `pending` task and no `verified` task is regenerated.

**US-8 — Status não pode ser afirmado, só comprovado**
Given a coding agent that reports success in its response while `verify.ps1` exits non-zero
When the step wrapper updates the ledger
Then the task is recorded as `failed` with the real exit code in `evidence`, never `verified`.

---

## 5. Quality Gate Requirements

Suíte `speckit_traceability` — `python -m src.shared.checks --project P --suite speckit_traceability`:

| ID | Regra |
|---|---|
| CHK-SK-001..003 | constitution / cada spec / cada plan existe e não é trivial |
| CHK-SK-004 | cada `specs/spec-*.md` tem `plans/plan-*.md` e `tasks/tasks-*.md` |
| CHK-SK-005 | cada task em `tasks/*.md` tem linha em `traceability.json` |
| CHK-SK-006 | cada linha resolve para um `source_artifact` real e a âncora existe no arquivo |
| CHK-SK-007 | cada `BR-*` de `business-rules.json` alcança ≥1 task |
| CHK-SK-008 | cada operação do OpenAPI alcança ≥1 task |
| CHK-SK-009 | cada `TC-*` de `test-cases.md` alcança ≥1 task |
| CHK-SK-010 | cada task tem critério de aceite e `target_files` declarados |
| CHK-SK-011 | `tasks-state.json` é 1:1 com `traceability.json` por `task_id` |
| CHK-SK-012 | toda entrada `verified` tem `evidence` com exit code real e log existente |

Suíte `prototype_coverage`:

| ID | Regra |
|---|---|
| CHK-PROTO-001 | cada linha `included` do `screen-list.md` tem tela em `spec-prototype.md` |
| CHK-PROTO-002 | cada `<section class="screen" id="screen-*">` do `index.html` está inventariada |
| CHK-PROTO-003 | cada tela tem rota, ≥1 task e ≥1 cenário de teste |
| CHK-PROTO-004 | cada formulário tem spec de validação e task |
| CHK-PROTO-005 | cada chave do `design-tokens.json` mapeia para um token da stack alvo |
| CHK-PROTO-006 | cada endpoint declarado existe no contrato OpenAPI |
| CHK-PROTO-007 | `source_warnings[]` do `screen-list.md` são propagados, não descartados |

O gate de saída da F3S bloqueia a F4 enquanto qualquer uma das duas suítes estiver vermelha.

---

## 6. Dependencies

- **F2 completa** — `architecture-blueprint.md`, `tech-framework-document.md`,
  `architecture-decision-matrix.md`, `decisions/ADR-*.md`, `openapi/*.yaml`, `api-map.md`,
  `regras-negocio.md`, `backlog-tobe.md`, `wave-plan.md`.
- **F2c completa** — `tobe/qa/test-cases.md`.
- **F3 completa** — `prototype/index.html`, `screen-list.md`, `design-tokens.json`.
- **F1** — `asis/docs/business-rules.md` + `.json`.
- `agent_registry`, `pipeline_plan`, `sdk_engine`, `src/shared/checks` — todos existentes.
- Nenhuma dependência externa nova. `context_manifest.py` e `task_ledger.py` são stdlib-only.

---

## 7. Exclusions

- **Não corrige os defeitos de código apontados pela auditoria** — as 2 CVEs de severidade
  alta, o hash de senha não persistido em `RegisterCustomerHandler.cs:27-29` e as credenciais
  em texto claro em `outputs/tobe/source-code/.env`. Nenhuma camada de planejamento conserta
  isso retroativamente; as credenciais precisam ser rotacionadas independentemente desta spec.
- **Não substitui o `ava-stack-build-validator`.** A aceitação de build simulado (RC-02) é
  defeito separado; esta spec cria a evidência exigida pelo razão, não o validador.
- **Não cria `pipeline-dag/F4.yaml`.** O fan-out entra pelo motor SDK; a paridade no motor
  copilot fica para trabalho posterior.
- **Não altera a numeração de fases existente.** `F3S` é acrescentado; nada é renumerado.

---

## 8. Assumptions

- **A1** — A qualidade das specs é limitada pela qualidade das fontes. `screen-list.md` já
  chega com seção de warnings; a camada propaga a degradação (CHK-PROTO-007), não a resolve.
- **A2** — A geração fatiada preserva coerência entre arquivos porque a `constitution.md`
  entra em toda chamada. Se a coerência cair, o sintoma aparece no build, não no gate.
- **A3** — A ordem alfabética observada em `sorted(rglob)` é estável no Windows e no Linux
  para os nomes em uso; a Fase 0 remove a dependência dessa ordem de qualquer forma.
- **A4** — `PHASE_ORDER` e `PHASE_NAMES` têm consumidores conhecidos e enumeráveis
  (`pipeline_observer.py`, `generate_observability_report.py`, testes). Acrescentar `F3S` é
  contido; a T-verificação confere cada consumidor antes do merge.

---

## Success Criteria

1. `ava-pipeline run -p P --phase F4 --dry-run` lista os insumos TO-BE e do protótipo entre os
   obrigatórios — o defeito P-1 comprovadamente fechado.
2. Insumo obrigatório ausente sai com exit code 2 sem gastar inferência.
3. A F3S emite a árvore completa em `outputs/tobe/speckit/` para um projeto com F2/F3 completas.
4. As duas suítes de check ficam verdes, com zero task órfã e zero fonte não referenciada.
5. O gate de saída bloqueia a F4 enquanto qualquer suíte estiver vermelha.
6. A F4 expande em N passos, cada um despachando um agente coder real.
7. Execução interrompida e reinvocada retoma na primeira task `pending`.
8. Nenhuma task alcança `verified` sem exit code real registrado em `evidence`.
9. `readiness-gate` C2 passa a apontar para um artefato que existe de fato.
10. Piloto medido contra os mesmos sete eixos da auditoria: `dotnet build` com 0 erros; telas
    presentes ≥ 14/15; regras de negócio implementadas ≥ 15/18; operações OpenAPI ≥ 19/21.
