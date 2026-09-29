# Agent Specification: Scaffold Angular determinístico com harness de validação

**Feature Branch**: `042-angular-scaffold-deterministic-harness`
**Created**: 2026-08-21
**Status**: Draft
**Change Type**: modify-existing (`angular-scaffold.md`, `f4s_phase_runner.py`, `f4s_build_runner.py`, `angular-scaffold-manifest.yaml`) + new-script (`f4s_angular_scaffold.py`, `verify_angular_app.py`) — sem agente novo, sem mudança de contrato de agente
**Origem**: análise do scaffold gerado em `projects/example-vcl-login/outputs/tobe/source-code/frontend/apps-login-spa/`

## Problem Statement

O scaffold Angular é hoje um spec em prosa que um agente LLM interpreta para escrever
arquivos. O código gerado **não compila**. A inspeção do único projeto já produzido
expôs seis defeitos independentes — não é um erro do agente numa execução, é o contrato
que está incompleto.

| #  | Defeito                                                                                                     | Efeito                                         |
| -- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| B1 | `tsconfig.app.json` / `tsconfig.spec.json` referenciados em `angular.json` mas **não gerados** | `ng build` morre antes de compilar uma linha |
| B2 | `tsconfig.json` sem `files`/`include`                                                                 | ngtsc compila zero arquivos                    |
| B3 | pipe`number` usado sem `DecimalPipe` no `imports` do standalone component                             | erro AOT`NG8004`                             |
| B4 | `serve` sem `buildTarget`                                                                               | `ng serve` falha na validação de schema    |
| B5 | `polyfills: ["zone.js"]` ausente                                                                          | build passa, app morre no browser (`NG0908`) |
| B6 | sem`configurations.production` / `fileReplacements`                                                     | `environment.prod.ts` é arquivo morto       |

Evidência de B1 e B3, respectivamente `angular.json:25` e `item-list.component.ts:49`
do projeto citado: o primeiro aponta `"tsConfig": "tsconfig.app.json"` para um arquivo
que não existe no diretório; o segundo usa `{{ item.value | number:'1.2-2' }}` num
componente cujo `imports` traz apenas `AsyncPipe`.

### Causas raiz

1. **A árvore do spec omite os arquivos que quebraram.** `angular-scaffold.md:28-47` não
   lista `tsconfig.app.json`, `tsconfig.spec.json` nem `src/environments/`. O agente gerou
   fielmente a árvore pedida — a árvore é que está errada.
2. **Os guardrails corretos existem mas não vinculam.**
   `build-cycle-angular-agent.md:92-118` já cobre B1, B2 e B5, mas o spec apenas manda
   "ler como referência de engenharia".
3. **Contradição de contrato.** O spec manda `styles.css` (`angular-scaffold.md:33`); o
   manifest exige `styles.scss` com `blocking: true`
   (`angular-scaffold-manifest.yaml:55`). Um scaffold que siga o spec à risca reprova no
   gate do próprio repositório.
4. **O gate que pegaria B1 não roda na esteira F4S.**
   `verify_scaffold.py --manifest angular` só é invocado como linha de Bash dentro de
   prompts markdown. Em `f4s_phase_runner.py` existem apenas `_run_scaffold_path_check` e
   `_run_nuget_checks` — e este último faz `if target_stack != "dotnet": return` na entrada.
5. **`npm ci` sem lockfile.** `f4s_build_runner.py:22` usa `npm ci`, que exige
   `package-lock.json`; o scaffold nunca gerou um.
6. **Divergência de raiz.** `f4s_phase_runner.py:390` define
   `repo_root = source-code/{target_stack}`, mas o projeto real foi escrito em
   `source-code/frontend/apps-login-spa/`. O build roda num diretório sem `package.json`.

Esta spec troca a geração interpretativa por **geração determinística a partir de
templates versionados**, acrescenta um **harness de validação end-to-end** e torna o
**commit inicial condicionado à validação**.

## User Stories

### US1 — Scaffold que compila na primeira tentativa

Como operador da esteira, quero que o scaffold Angular compile assim que gerado, sem
edição manual, para que o codegen de features comece sobre uma base sã.

### US2 — Prova de que o app sobe, não só de que compila

Como operador, quero que a validação suba o bundle de produção e faça uma requisição
real, porque B5 é um defeito que passa no `ng build` e só aparece no browser.

### US3 — Commit inicial já verificado

Como operador, quero que o primeiro commit do repositório de source-code contenha uma
estrutura comprovadamente compilando, para ter um ponto de retorno confiável.

### US4 — Dependências instaladas na pasta do projeto

Como operador, quero que as dependências do `package.json` sejam instaladas com
`npm install` no diretório do projeto, porque `npm ci` falha quando ainda não há
lockfile — que é exatamente o estado de um scaffold recém-gerado.

### US5 — Falha atribuída no próprio passo

Como operador, quero que um scaffold incompleto reprove **antes** do codegen de features,
para não descobrir o problema vários agentes adiante.

### US6 — Regeneração idempotente

Como operador, quero reexecutar o gerador sem perder o trabalho que o LLM fez depois,
para poder corrigir o scaffold sem recomeçar a feature.

## Acceptance Scenarios (BDD)

### Nominal — gerar, validar, commitar

```gherkin
Dado um projeto com project-config.yaml declarando tobe_stack.frontend_version = 17
  E um architecture-blueprint.md com os bounded contexts "vendas" e "estoque"
Quando f4s_angular_scaffold.py --project <p> é executado
Então a árvore é escrita em outputs/tobe/source-code/angular/
  E angular.json, tsconfig.app.json e tsconfig.spec.json existem os três
  E src/app/features/vendas/ e src/app/features/estoque/ contêm um componente compilável
Quando verify_angular_app.py --root <app_root> é executado
Então as fases install, build, boot e health saem todas PASS
  E o status final é PASS com exit code 0
Quando o commit inicial é feito
Então HEAD contém package-lock.json
  E não contém node_modules/ nem dist/
```

### Edge — primeira execução sem lockfile

```gherkin
Dado um app_root sem package-lock.json
Quando a fase install executa
Então o comando escolhido é `npm install`
  E ao final existe um package-lock.json
Quando verify_angular_app.py roda uma segunda vez
Então o comando escolhido é `npm ci`
```

### Edge — porta ocupada

```gherkin
Dado que a porta padrão do host está ocupada
Quando a fase boot executa
Então o servidor faz bind na porta 0 e usa a porta efêmera atribuída
  E a fase boot sai PASS
```

### Edge — major do Angular não suportado

```gherkin
Dado tobe_stack.frontend_version = 42
Quando o gerador executa
Então o status é ERROR com mensagem nomeando os majors suportados
  E nenhum arquivo é escrito
```

### Edge — scaffold pré-existente (idempotência)

```gherkin
Dado um app_root já gerado, cujo app.routes.ts foi editado pelo LLM
Quando o gerador executa sem --force
Então app.routes.ts é preservado e aparece em files_skipped
  E arquivos ausentes são criados e aparecem em files_written
Quando o gerador executa com --force
Então app.routes.ts é sobrescrito pelo template
```

### Edge — layout de dist do Angular 17+

```gherkin
Dado que o build produziu dist/<app>/browser/index.html
Quando a fase boot procura a raiz estática
Então ela resolve dist/<app>/browser, não dist/<app>
```

### Edge — servidor morre durante o boot

```gherkin
Dado que o processo servidor termina antes do primeiro health-check
Quando a fase health faz o poll
Então a falha é reportada como fase boot com exit code 40
  E não se espera o timeout inteiro
```

### Gate — scaffold incompleto reprova antes do build

```gherkin
Dado um app_root sem tsconfig.app.json
Quando o gate de stack do f4s_phase_runner executa para target_stack=angular
Então verify_scaffold.py --manifest angular reprova com blocking_missing > 0
  E run_build não é invocado
  E o passo entra em remediação com o arquivo faltante nomeado
```

## Quality Gate

- [ ] `pytest tests/tools/test_f4s_angular_scaffold.py tests/utils/test_verify_angular_app.py` verde
- [ ] `f4s_angular_scaffold.py` seguido de `verify_angular_app.py` sai `PASS` numa árvore
  recém-gerada, sem edição manual
- [ ] `verify_scaffold.py --manifest angular` sai `PASS` sobre a mesma árvore
- [ ] `git log` do repo de source-code mostra o commit inicial, com `package-lock.json`
  versionado e `node_modules/`/`dist/` ausentes
- [ ] `pytest tests/tools/test_f4s_phase.py tests/utils/test_verify_cpm_consistency.py` verde
  (não-regressão do caminho .NET)

## Out of Scope

React, Vue e Blazor sofrem do mesmo padrão — spec em prosa mais gate não conectado — mas
ficam fora desta entrega. O dispatch por stack introduzido em `_run_stack_checks` é
desenhado para recebê-los depois sem refatoração.

Também fora de escopo: substituir o agente `coder-angular-frontend` (que gera as features
por BC). Esta spec cobre apenas o scaffold — a base sobre a qual aquele agente trabalha.
