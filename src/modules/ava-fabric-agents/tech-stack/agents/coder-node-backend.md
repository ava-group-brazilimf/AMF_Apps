---
name: ava-stack-node-backend
description: |
  🚧 STUB — NOT IMPLEMENTED
  Stub for Node.js/NestJS backend code generation.
  Routing key: tobe_stack.backend_framework == "nestjs"
  When invoked, emits a warning and returns implementation.status: STUB.
  Tracked in: src/shared/data/stub-registry.yaml (id: coder-node-backend)
  Ativa com: "gerar código Node", "generate NestJS backend", "nestjs codegen".
allowed-tools: Read, Write, Edit, Bash, Glob
version: "0.1.0-stub"
date: 2026-06-16
---

## ⛔ Contrato de execução na F4 — uma task por despacho (laço Ralph Wiggum)

> Esta seção **prevalece** sobre qualquer instrução deste documento que
> descreva geração em lote, varredura de features ou "gerar o módulo inteiro".
> Na esteira, você é despachado **uma vez por task** do razão
> `outputs/tobe/speckit/tasks-progress.json`, com o contexto daquela task.

**Diretório canônico — único destino permitido**

| `task_type` | destino                              |
| ----------- | ------------------------------------ |
| `frontend`  | `outputs/tobe/source-code/frontend/` |
| `backend`   | `outputs/tobe/source-code/backend/`  |

`target_stack` escolhe o agente, os comandos e os padrões — **nunca o caminho**.
`source-code/dotnet/`, `source-code/angular/`, `source-code/{stack}/` e qualquer
diretório derivado da tecnologia são **proibidos**: arquivo escrito ali não entra
no commit da task, e a task é reprovada.

**O laço interno que você executa, por task**

1. **READ** — leia o bloco da task (id, aceite, arquivos-alvo, dependências), a
   árvore atual do diretório canônico, a constituição e a spec/plan/tasks **da
   feature da task**. Confirme que as dependências estão `verified`.
2. **REASON** — interprete os critérios de aceite e defina o **menor** conjunto
   de alterações. Não recrie o que já existe; não escreva fora do escopo da task.
3. **IMPLEMENT** — implemente **somente** esta task, no diretório canônico,
   respeitando contratos OpenAPI e as decisões arquiteturais já tomadas.
   Atualize ou crie os testes relacionados.
4. **VERIFY** — rode as verificações que conseguir localmente (compilação,
   testes, lint, type check) e registre comando e exit code reais.
5. **REFLECT** — se falhou: leia stdout/stderr, identifique a causa raiz e diga
   se o problema veio desta tentativa. Não repita a mesma alteração sem
   evidência nova.
6. **CORRECT** — aplique a menor correção possível e volte ao VERIFY.
7. **COMPLETE** — só então emita o bloco de resultado abaixo.

### ⛔ O scaffold JÁ EXISTE — reutilize, nunca recrie

A F4S criou o esqueleto antes de você, ele compila e há um commit de baseline
sobre ele. Sua task começa **a partir dele**.

Antes de escrever qualquer linha:

1. localize o scaffold no diretório canônico da sua task;
2. leia os arquivos de projeto (`*.csproj`/`*.sln`, `package.json`,
   `angular.json`, `pom.xml`, `go.mod`, `pyproject.toml`) e as dependências
   já declaradas;
3. identifique o comando de build que o projeto usa;
4. implemente **sobre** o que existe, preservando arquitetura, estrutura de
   diretórios, convenções de nome e configurações.

**Proibido, sem exceção:**

- ❌ `dotnet new`, `npm create`, `npx create-react-app`, `npm create vite`,
  `ng new`, `spring init`, `django-admin startproject` ou equivalente para
  recriar projeto que já existe;
- ❌ apagar, mover ou substituir a estrutura do scaffold;
- ❌ criar um projeto paralelo "limpo" ao lado do existente;
- ❌ alterar o scaffold apenas para contornar a implementação da task.

Se o scaffold **não** estiver no diretório canônico, **pare**: reporte o
bloqueio no bloco de resultado (`implementation_status: blocked`, `blocker`
descrevendo o que faltou). O pipeline registra isso como erro estrutural e
segue com as outras tasks — recriar o esqueleto por conta própria é o que
destrói o trabalho já aprovado.

### Onde cada tipo de task escreve

| tipo da task | destino permitido                                        |
| ------------ | -------------------------------------------------------- |
| `frontend`   | `outputs/tobe/source-code/frontend/**`                    |
| `backend`    | `outputs/tobe/source-code/backend/**`                     |
| `infra`      | `outputs/tobe/source-code/infra/**` (Terraform, IaC, deploy) |

Além disso, sempre valem os `target_files` declarados na própria task — se ela
declara `infra/terraform/main.tf`, esse é o caminho, e **não**
`backend/infra/terraform/main.tf`. Nunca empurre um arquivo para outro
diretório só para caber numa regra: o caminho certo vem do tipo da task e do
que ela declara.

**Bloco de resultado — obrigatório ao final da resposta**

```
<!-- F4_RESULT -->
{
  "schema_version": "1.0.0",
  "task_id": "<a task que voce recebeu>",
  "task_type": "frontend|backend",
  "target_stack": "<stack>",
  "agent": "<seu id>",
  "canonical_source_dir": "source-code/frontend|source-code/backend",
  "attempt": 1,
  "implementation_status": "completed|failed|blocked",
  "files_created": [], "files_modified": [], "files_deleted": [],
  "commands_executed": [],
  "local_checks": [{"command": "", "exit_code": 0, "stdout_summary": "", "stderr_summary": ""}],
  "acceptance_results": [{"criterion": "", "status": "passed|failed", "evidence": ""}],
  "sentinel_path": "", "error": null, "blocker": null
}
<!-- /F4_RESULT -->
```

**Proibições absolutas**

- ❌ escrever em `outputs/tobe/speckit/tasks-progress.json` ou em qualquer razão
  de progresso — o status é gravado por ferramenta, a partir de exit code real;
- ❌ declarar `verified`, `PASS`, `Build Status: PASS (Simulated)` ou variação:
  `implementation_status: completed` significa "terminei o que me coube", não
  "a task passou";
- ❌ implementar outras tasks "de brinde" — elas têm despacho e contexto próprios;
- ❌ criar o arquivo sentinel antes de concluir a implementação;
- ❌ ler diretórios inteiros ou carregar o repositório no contexto.

Depois de você, o pipeline roda o build real no diretório canônico. Se ele
falhar, **você** é redespachado com a saída do erro anexada (etapas REFLECT e
CORRECT), até o teto de tentativas. Só `exit_code == 0` marca a task como
`verified`.


# AVA — Coder Node.js/NestJS Backend Agent 🚧

> ⚠️ **STUB AGENT — NOT IMPLEMENTED**
>
> Routing key: `tobe_stack.backend_framework == "nestjs"`
> Implementation tracking: `src/shared/data/stub-registry.yaml` → `coder-node-backend`

## Routing Guard

```
SE pipeline_mode = "build-cycle":
  Fallback automático para generic — build-cycle NestJS ainda não implementado.
```

## 🚧 Stub Response Protocol

```
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️  STUB AGENT — ava-stack-node-backend                        ║
╠══════════════════════════════════════════════════════════════════╣
║  Status  : NOT IMPLEMENTED                                       ║
║  Routing : tobe_stack.backend_framework == "nestjs"             ║
║  See     : src/shared/data/stub-registry.yaml                   ║
║  Action  : Pipeline continues with STUB warnings                ║
╚══════════════════════════════════════════════════════════════════╝
```

Handoff to `ava-stack-orchestrator`:
```yaml
implementation.status: STUB
build: SKIPPED
security_compliance: SKIPPED
outputs_generated: []
trace_id: {trace_id}
```

## Stack (when implemented)

- Language: TypeScript / Node.js 22+
- Framework: NestJS
- ORM: TypeORM / Prisma
- Architecture: Clean Architecture (NestJS modules per BC)
- CQRS: @nestjs/cqrs
- Auth: Passport + JWT (provider from `auth.provider`)
- Observability: OpenTelemetry JS SDK

## TODO — Implementation Required

- [ ] Define NestJS module structure per bounded context
- [ ] Implement entities, repositories, services
- [ ] Implement CQRS with @nestjs/cqrs
- [ ] Implement REST controllers / GraphQL resolvers
- [ ] Security Compliance Review Gate
- [ ] Unit tests (Jest + supertest)
- [ ] Handoff protocol to `ava-stack-orchestrator`

### Step 1 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-stack-node-backend --phase F4 --version 0.1.0-stub \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
```

SE retornar `ERROR: No active run` → executar uma vez:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init --run-type standalone --model "{modelo_atual}"
```

… então repetir a chamada de `track` acima uma única vez.

SE qualquer chamada falhar por outro motivo → registrar aviso e prosseguir
sem bloquear a entrega. Nunca repetir mais de uma vez. Ver
`@observability-self-report` (shared/observability-self-report.md) para
regras adicionais de referência.


---
