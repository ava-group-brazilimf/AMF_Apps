# Análise — Esteira de Geração de Código Travada (F4 Tech-Stack Orchestrator)

> **Escopo**: `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` (v1.7.1)
> **Motivado por**: projeto `Meu-ERP` (e variantes `Meu-ERP-001-AST-AS-IS-Orchestrator` /
> `Meu-ERP-002-AST-Master-Orchestrator`) — código não é gerado / esteira parece travar na fase de codegen.
> **Método**: leitura direta do orchestrator, dos 2 coder agents ✅ implementados (dotnet/angular), dos
> scripts determinísticos (`verify_scaffold.py`, `build_runner.py`), dos manifests de scaffold, e dos
> outputs reais dos 3 projetos Meu-ERP no filesystem.
> **Data**: 2026-07-15
>
> **⚠️ Atualização 2026-07-15 (mesmo dia)**: todas as correções descritas no §8 (Plano de
> Correção) desta análise foram implementadas e documentadas via SpecKit em três specs:
> - `specs/019-codegen-dynamic-naming-path-fix/` — causas A-H deste documento (naming dinâmico,
>   paths de output, dependências quebradas do Angular/containerize, higiene de `module.yaml`)
> - `specs/020-codegen-business-rules-architecture-config/` — consumo de regras de negócio +
>   configuração arquitetural TO-BE nos coder agents (requisito funcional adicional do usuário,
>   fora do escopo original desta análise)
> - `specs/021-frontend-backend-api-contract-integration/` — integração real de contrato de API
>   entre backend e frontend (requisito funcional adicional do usuário, fora do escopo original
>   desta análise)
>
> Este documento permanece como o registro do diagnóstico original — para o estado pós-correção,
> ver os três specs acima (`spec.md` + `plan.md` + `tasks.md` cada, todos com Status: Implemented).

---

## 1. Resumo Executivo

Foram encontradas **duas causas distintas e independentes**, uma explicando por que **nada foi gerado
ainda para o projeto Meu-ERP** (causa operacional/config), e outra explicando por que, **quando a
geração for de fato disparada, o código .NET tem alto risco de não compilar / travar no gate de
scaffold** (causa estrutural no módulo `tech-stack`, latente, ainda não disparada neste projeto):

| # | Causa | Camada | Severidade | Já se manifestou no Meu-ERP? |
|---|-------|--------|------------|-------------------------------|
| A | Fase TO-BE nunca rodou — pré-requisitos do Step 0.5 do orchestrator não existem | Config / sequenciamento do pipeline | 🔴 Bloqueante (esperado) | **Sim — é a causa raiz do "nada gerado" hoje** |
| B | `dotnet-scaffold-manifest.yaml` tem paths **hardcoded** com o literal `MeuERP`, sem substituição de `{SolutionPrefix}` | Bug determinístico em `src/shared/data/scaffold-manifests/dotnet-scaffold-manifest.yaml` + `verify_scaffold.py` | 🔴 Bloqueante (vai disparar assim que a fase TO-BE terminar e o codegen for de fato invocado) | Ainda não (nenhum codegen rodou) |
| C | `coder-dotnet-backend.md` não tem uma seção de "Execution Steps" (ao contrário do Angular) — o agente improvisa nomenclatura de projetos/solution a partir de guardrails soltos | Especificação do agente `agents/coder-dotnet-backend.md` | 🟠 Alto risco de não-compilação | Ainda não |
| D | `module.yaml` do tech-stack marca `java/python/go-backend` como `status: stub`, contradizendo o próprio orchestrator e o conteúdo real dos arquivos | Metadado/registro (`tech-stack/module.yaml`) | 🟡 Médio (não afeta Meu-ERP, que usa dotnet+angular) | Não |
| E | Dois caminhos de invocação de codegen divergentes: `orchestrator-tobe.md` (Fase 4.7) dispara `coder-dotnet.md` (módulo `tobe-architecture`) diretamente, sem passar pelo `ava-stack-build-validator`; só depois, manualmente, o PM é instruído a rodar `@ava-stack-orchestrator` (módulo `tech-stack`) para o "Build Cycle" real | Ambiguidade de arquitetura entre módulos `tobe-architecture` e `tech-stack` | 🟠 Confunde o operador sobre "onde" o código real deveria sair | Relevante — nenhum dos dois rodou ainda no Meu-ERP, mas explica por que a esteira "parece parar" após o TO-BE sem deixar claro o próximo passo |

**Conclusão em uma frase**: no projeto Meu-ERP a esteira não está "travada" durante a geração — ela
**nunca chegou** à geração, porque a Fase TO-BE está pendente e o `ava-stack-orchestrator` se recusa
(corretamente) a gerar código sem os artefatos TO-BE. Quando a Fase TO-BE for concluída e o codegen for
disparado, no entanto, existe um bug concreto e determinístico (causa B) que vai travar o backend .NET
no gate de scaffold (Step 5.5) antes mesmo do build-validator rodar — **a menos que o projeto se chame
literalmente "MeuERP" sem hífen nem sufixo**, coincidência que só ocorreria pelo acaso do nome do
projeto de teste.

---

## 2. Causa A — Fase TO-BE pendente (por que nada foi gerado ainda)

### Evidência

`projects/Meu-ERP-001-AST-AS-IS-Orchestrator/context/shared-context.md`:

```
| Fase               | Status       | Agente                   | Concluído em              |
| ------------------ | ------------ | ------------------------ | -------------------------- |
| AS-IS Diagnóstico  | ✅ COMPLETED | ava-asis-orchestrator    | 2026-07-15T15:16:12-03:00 |
| TO-BE Design       | ⏳ PENDING   | ava-tobe-orchestrator    | —                          |
| Codegen Stack      | ⏳ PENDING   | ava-stack-orchestrator   | —                          |
```

- O diagnóstico AS-IS (Delphi/VCL, 30 `.pas`, 4630 LOC) está 100% completo — `master-report.md`,
  `architecture-blueprint.md`, os 9 artefatos brutos de AST, todos presentes e sem erro no log de
  extração (`outputs/asis/ast-raw/{language}/run_ast_analysis.log`).
- **Não existe `outputs/tobe/` em nenhum dos três projetos** (`Meu-ERP`, `Meu-ERP-001-...`,
  `Meu-ERP-002-...`). Ou seja, nenhum dos artefatos que o `orchestrator-stack.md` exige no seu **Step
  0.5 (pré-flight, bloqueante)** existe:
  - `outputs/tobe/docs/architecture-blueprint.md` (produzido por `ava-tobe-architecture-design`)
  - `outputs/tobe/docs/security-architecture.md` (produzido por `security-design-tobe`)
  - `outputs/readiness-gate/wave-1/readiness-gate-status.json` com `status == "APPROVED"`
- `outputs/observability/` existe mas está **vazio** — confirma que `pipeline_observer.py` nunca
  registrou um run de F4 (Codegen).
- `Meu-ERP-002-AST-Master-Orchestrator/context/shared-context.md` ainda contém placeholders
  não preenchidos (`{{PROJECT_NAME}}`, `{{STATUS}}`) — é uma cópia fresca do `_template`, nunca
  executada.
- O `project-config.yaml` do projeto-base `Meu-ERP` (em `C:\Desenv\factory_apps\...\Meu-ERP\context\`)
  é um esqueleto de 17 linhas **sem a seção `tobe_stack.*` inteira** — se alguém tentasse rodar
  `@ava-stack-orchestrator` contra esse config específico, o Step 0.3b não conseguiria resolver
  `resolved_backend_agent`/`resolved_frontend_agent` (campo `tobe_stack.backend_framework`
  simplesmente não existe) e o orchestrator emitiria `⛔ STOP: STACK NOT SUPPORTED`. Só os projetos
  `Meu-ERP-001-...` e `Meu-ERP-002-...` têm o `tobe_stack` completo (`dotnet` 10.0 + `angular` 17).

### Por que isso "parece" uma esteira travada

O comportamento do orchestrator aqui é **correto por design** (Step 0.7: *"IF any prerequisite ❌:
STOP. Do NOT generate any output... Report exactly which agent produces the missing artifact"*).
O problema não é um bug de execução — é que, do ponto de vista do operador, a esteira "parou" após o
AS-IS sem deixar um sinal óbvio de qual comando disparar em seguida. Isso é agravado pela Causa E
(abaixo): existem *dois* orquestradores TO-BE/codegen concorrentes e não é óbvio qual deveria ser
chamado.

### Correção

Nenhuma mudança de código é necessária para este ponto — é uma questão de **sequenciamento de
execução**: rodar `ava-tobe-orchestrator` (módulo `tobe-architecture`) para `Meu-ERP-001-...` até a
Fase 4.6/4.61 e o Readiness Gate Wave 1 ser `APPROVED`, **antes** de invocar `@ava-stack-orchestrator
trigger: SG`. Ver §5 para o plano de ação passo a passo.

---

## 3. Causa B — Bug determinístico: manifest de scaffold .NET com prefixo hardcoded

Esta é a descoberta mais crítica e mais fácil de corrigir. É um bug reproduzível, não uma questão de
interpretação de agente.

### Evidência

`src/shared/data/scaffold-manifests/dotnet-scaffold-manifest.yaml` declara no cabeçalho (linha 8):

```yaml
# NOTE: {SolutionPrefix} and {BC} are resolved at runtime by the calling agent.
```

Mas os 4 caminhos marcados `blocking: true` (os únicos que realmente derrubam o Step 5.5) usam o
literal **`MeuERP`**, não um placeholder:

| Linha | Path (blocking: true) |
|---|---|
| 36 | `src/Shared/MeuERP.Shared.Domain/MeuERP.Shared.Domain.csproj` |
| 67 | `src/Shared/MeuERP.Shared.Infrastructure/MeuERP.Shared.Infrastructure.csproj` |
| 85 | `src/Api/MeuERP.Api.csproj` |
| 98 | `src/Api/Program.cs` *(este não tem o literal — é o único blocking-check realmente genérico)* |

`src/shared/utils/verify_scaffold.py::check_file_exists()` (linha 129-145) faz correspondência de
caminho **literal** (ou glob, mas sem qualquer substituição de variável) — não existe nenhum mecanismo
de template no script, e `orchestrator-stack.md` Step 5.5 invoca o script sem passar nenhum parâmetro
de prefixo:

```
Bash: python src/shared/utils/verify_scaffold.py --manifest dotnet --root projects/{project_name}/outputs/tobe/source-code/backend
```

### Impacto

Para **qualquer** projeto cujo `SolutionPrefix` não seja literalmente `MeuERP` — incluindo
`Meu-ERP-001-AST-AS-IS-Orchestrator` e `Meu-ERP-002-AST-Master-Orchestrator`, cujos nomes de projeto
geram prefixos diferentes — os 3 checks bloqueantes acima vão **sempre falhar**, mesmo que o
`ava-stack-dotnet-backend` gere uma solução .NET perfeitamente correta e compilável com o nome de
projeto certo. O resultado no Step 5.5 do orchestrator:

```
⛔ HARD STOP — não despachar build-validator.
Reportar: "ava-stack-dotnet-backend reportou COMPLETED mas 3 arquivos obrigatórios estão
ausentes: src/Shared/MeuERP.Shared.Domain/..., src/Shared/MeuERP.Shared.Infrastructure/...,
src/Api/MeuERP.Api.csproj"
```

Ou seja: **o `ava-stack-build-validator` nunca chega a rodar**, o pipeline para exatamente no gate
anterior a ele — a "esteira trava na geração de código" de forma literal e determinística, e o relatório
de erro vai parecer contraditório para o operador ("os arquivos existem, só que com outro nome").

O manifest Angular (`angular-scaffold-manifest.yaml`) **não tem esse problema** — todos os seus paths
(`package.json`, `src/app/app.component.ts`, etc.) são genéricos, sem nome de projeto embutido.

### Correção proposta

1. Parametrizar o manifest .NET para usar um placeholder real (ex.: `{{SolutionPrefix}}`) nos 3 paths
   afetados, e estender `verify_scaffold.py` para aceitar um argumento `--solution-prefix` (resolvido
   pelo orchestrator a partir de `project_name`, mesma lógica de derivação que o coder já deveria usar
   para nomear os `.csproj`), substituindo o placeholder antes do glob/match.
2. Alternativa mais simples e robusta a ambiguidades de nomenclatura: trocar os 3 paths hardcoded por
   glob patterns (`src/Shared/*.Shared.Domain/*.Shared.Domain.csproj`,
   `src/Shared/*.Shared.Infrastructure/*.Shared.Infrastructure.csproj`, `src/Api/*.Api.csproj`) — já
   existe suporte a `glob: true` no script, então isso elimina a dependência do nome exato do projeto
   sem precisar tocar em `verify_scaffold.py`. **Esta é a correção recomendada — menor blast radius.**

---

## 4. Causa C — `coder-dotnet-backend.md` sem seção de execução (risco de não-compilação)

### Evidência

Comparando a estrutura dos dois coder agents ✅ "Implementados":

| Arquivo | Linhas | Seção de execução passo-a-passo |
|---|---|---|
| `agents/coder-angular-frontend.md` | 3135 | ✅ Step 1 → Step 2.1–2.17, template completo arquivo-por-arquivo, alinhado 1:1 com `angular-scaffold-manifest.yaml` |
| `agents/coder-dotnet-backend.md` | ~580 | ❌ Ausente — pula das Guardrails (G1–G11, linhas 77–397) direto para um "Clean Architecture Template" genérico de 6 linhas (linha 399) e uma lista solta de "Skills" (linha 410), sem instruções de criação de `.sln`, `Directory.Packages.props`, `Program.cs`, convenção de nomenclatura de projeto, ou como resolver `SolutionPrefix` |

O arquivo tem 11 guardrails bem escritos cobrindo erros pontuais de compilação já conhecidos (G1–G11:
Mapster DI, `async` sem `await`, `IAsyncDisposable`, SDK version, etc. — nota-se inclusive um cabeçalho
duplicado "G11 — SDK Version Validation" nas linhas 270 e 338), mas **nenhuma instrução estrutural**
equivalente ao que o Angular tem. Isso deixa a montagem da solução inteira (nomes de projeto, estrutura
de pastas, arquivo `.sln`) a critério de interpretação livre do modelo a cada execução — o oposto do
padrão determinístico usado no resto do pipeline.

Esta é provavelmente a causa raiz de origem da Causa B: o manifest foi aparentemente escrito **depois**
de uma execução manual de teste contra um projeto chamado literalmente "MeuERP", e o hardcode nunca foi
generalizado porque não existe uma seção no coder agent que declare explicitamente "o prefixo da solução
é derivado de `project_name`, formato X" — não havia uma fonte única de verdade para o manifest herdar.

### Correção proposta

Adicionar ao `coder-dotnet-backend.md` uma seção "Execution Steps" nos moldes do Angular:
- Passo explícito de resolução do `SolutionPrefix` a partir de `project_name` (ex.: remover hífens/
  espaços, PascalCase) — a mesma regra deve ser referenciada pelo manifest (via glob, conforme §3).
  Se um projeto legado precisa manter um nome fixo (e.g. herdado do sistema Delphi original), esse
  valor deveria ser um campo explícito em `project-config.yaml` (`tobe_stack.solution_prefix` ou
  similar), não inferido implicitamente.
- Passo explícito de criação do `.sln`, `Directory.Packages.props`, `Directory.Build.props`,
  estrutura `src/Shared/`, `src/{BC}/`, `src/Api/` — alinhado file-a-file com
  `dotnet-scaffold-manifest.yaml`, do mesmo jeito que o Angular está alinhado com o seu manifest.

---

## 5. Causa D — `module.yaml` do tech-stack desatualizado (metadado, não bloqueante para Meu-ERP)

`src/modules/ava-fabric-agents/tech-stack/module.yaml` marca `ava-stack-java-backend`,
`ava-stack-python-backend` e `ava-stack-go-backend` como `status: stub`, mas:
- `orchestrator-stack.md` (routing table) marca os três como `✅ Implemented`;
- `src/shared/data/stub-registry.yaml` marca os três como `status: COMPLETE`;
- o conteúdo real dos três arquivos tem pipeline completo (9 guardrails, gates de pré-requisito,
  Security Compliance Gate) — nada parecido com o template de stub genuíno usado por
  `coder-node-backend.md` (~102 linhas, `outputs_generated: []`).

`module.yaml` também não lista `ava-stack-docs-researcher`, `ava-stack-build-validator` nem
`ava-stack-build-fixer` no registro de agentes, apesar de serem obrigatórios em todo run.

**Não afeta o Meu-ERP** (que usa `dotnet` + `angular`, ambos corretamente listados em `module.yaml`
sem status `stub`), mas é uma fonte de confusão para qualquer ferramenta/pessoa que confie em
`module.yaml` como fonte de verdade de "o que está pronto" — vale corrigir por higiene, já que a
inconsistência foi documentada independentemente em `docs/tech-stack-io-map.md` §4.1.

**Correção**: atualizar `module.yaml` para refletir `status: COMPLETE`/ausência de `status` para
java/python/go, e adicionar as 3 entradas cross-cutting ausentes.

---

## 6. Causa E — Dois caminhos de invocação de codegen (`tobe-architecture` vs `tech-stack`)

### Evidência

`src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`:

- **Fase 4.7 ("Geração de Código", linha 1066)** resolve seu próprio mapa `CODER_AGENTS` (linha 1073)
  e despacha `coder-dotnet` → **um arquivo diferente**:
  `src/modules/ava-fabric-agents/tobe-architecture/agents/coder-dotnet.md` (não
  `tech-stack/agents/coder-dotnet-backend.md`). O próprio orchestrator-tobe declara explicitamente
  (linha 135): *"Este orquestrador NÃO executa gates de build. Esses gates são responsabilidade
  exclusiva do `{resolved_coder_agent}`"* — ou seja, nesta fase o `ava-stack-build-validator` **não é
  mencionado nem invocado**; a validação de build fica a cargo do próprio `coder-dotnet.md`.
- **Depois**, numa numeração separada ("Step F2 — Package Approval Document", linha 1691), após
  sign-off formal do Human SME, o texto instrui o PM manualmente: *"4. Iniciar Build Cycle:
  `@ava-stack-orchestrator project: {project_name}`"* (linha 1724) — isto é, o pipeline **real** de
  codegen com `docs-researcher` + `build-validator` + `build-fixer` (módulo `tech-stack`, este
  documento analisado) só é disparado **manualmente pelo PM**, depois de aprovação humana, como uma
  segunda etapa distinta da Fase 4.7.

### Impacto

Não é possível, só pela leitura destes dois arquivos, determinar com certeza se:
(a) `coder-dotnet.md` (tobe-architecture) é usado para um protótipo/rascunho inicial e
`ava-stack-dotnet-backend` (tech-stack) é o gerador "de produção" — nesse caso o fluxo é intencional,
mas mal documentado como sequência; ou
(b) os dois arquivos são implementações divergentes concorrentes do mesmo problema, mantidas por
descuido (`coder-dotnet.md` seria legado).

Nenhum código foi gerado ainda em nenhum dos três projetos Meu-ERP, então este ponto não causou o
travamento observado — mas é a explicação mais provável para a confusão de "por que a esteira parece
não seguir automaticamente do TO-BE para o codegen": **o disparo do `@ava-stack-orchestrator` real é
manual**, não automático, e fica documentado apenas em um texto de instrução ao PM no meio de um step
sobre aprovação de documento, longe de onde se esperaria procurar essa informação.

### Correção proposta

Este ponto requer uma decisão de arquitetura (não uma correção mecânica) — recomenda-se:
1. Confirmar com o time se `coder-dotnet.md` (tobe-architecture) está de fato obsoleto/deve ser
   removido, ou se cumpre um propósito distinto (ex.: geração de protótipo de viabilidade antes do
   Readiness Gate).
2. Se `@ava-stack-orchestrator` é sempre o caminho de produção, adicionar um gate explícito e visível
   no fim da Fase 4.6/4.61 do `orchestrator-tobe.md` (não enterrado dentro do Step F2) apontando
   claramente "próximo comando: `@ava-stack-orchestrator trigger: SG`", e no `shared-context.md`
   gerado, atualizar a linha "Codegen Stack" para incluir esse comando quando o status virar `⏳
   PENDING → READY (aguardando trigger manual)`.

---

## 7. O que os agentes efetivamente consomem para gerar código (mapa rápido)

Detalhamento completo já existe em `docs/tech-stack-io-map.md` (produzido nesta mesma investigação de
base) — resumo dos pontos relevantes às causas acima:

- **`ava-stack-dotnet-backend`** lê: `project-config.yaml` (gate de `pipeline_mode`),
  `security-architecture.md` (antes do Security Gate), opcionalmente `docs-research-bundle.md`
  (não-bloqueante), e um arquivo de entidade por vez em `src/{BC}/{prefix}.{BC}.Domain/Entities/*.cs`
  (guardrail G2) — nenhuma leitura de árvore inteira.
- **`ava-stack-angular-frontend`** lê: `project-config.yaml`, `ConfigStackDotNet.yaml`
  (bloqueante se `auth_provider != azure-ad`), opcionalmente `bounded-context-map.md` (AS-IS,
  fallback) — **não lê `docs-research-bundle.md`** apesar do orchestrator instruir isso no Step 5
  (gap documentado, não bloqueante).
- **`ava-stack-build-validator`** é o único agente com leitura de árvore completa legítima (precisa
  compilar a solução inteira) — `dotnet build {solution_file} --no-incremental`,
  `dotnet format --verify-no-changes`, `dotnet list package --vulnerable`, `npm run build`,
  `npx eslint .`, `npm audit`. Sem essas leituras o agente não teria como fazer seu trabalho; não é
  um problema.
- **`verify_scaffold.py`** (Step 5.5, chamado 1x pelo orchestrator + 1x internamente pelo
  build-validator como pre-gate) é puramente determinístico — só existência de arquivo, sem qualquer
  substituição de variável (causa B).

---

## 8. Plano de Correção (priorizado)

| # | Ação | Arquivo(s) | Esforço | Prioridade |
|---|------|-----------|---------|------------|
| 1 | Trocar os 3 paths `blocking: true` hardcoded (`MeuERP.*`) por glob patterns genéricos em `dotnet-scaffold-manifest.yaml` | `src/shared/data/scaffold-manifests/dotnet-scaffold-manifest.yaml` | Baixo (15 min) | 🔴 **Crítica — bloqueia todo codegen .NET com nome de projeto ≠ "MeuERP"** |
| 2 | Adicionar seção "Execution Steps" ao `coder-dotnet-backend.md` definindo a regra de resolução de `SolutionPrefix` e o layout de arquivos file-a-file, espelhando o padrão do Angular | `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` | Médio (2-4h) | 🟠 Alta |
| 3 | Rodar a Fase TO-BE (`ava-tobe-orchestrator`) até o Readiness Gate Wave 1 = `APPROVED` para `Meu-ERP-001-AST-AS-IS-Orchestrator`, depois disparar `@ava-stack-orchestrator trigger: SG` | Execução de pipeline (sem mudança de código) | — | 🔴 Necessário para desbloquear o Meu-ERP hoje |
| 4 | Esclarecer e documentar a relação entre `coder-dotnet.md` (tobe-architecture, Fase 4.7) e `ava-stack-dotnet-backend`/`ava-stack-orchestrator` (tech-stack) — decidir se um é legado | `orchestrator-tobe.md`, `coder-dotnet.md` | Decisão de arquitetura + doc | 🟠 Alta (clareza operacional) |
| 5 | Tornar mais visível o comando de disparo manual do Build Cycle real ao final da Fase TO-BE (hoje enterrado no Step F2 / Package Approval) | `orchestrator-tobe.md`, template de `shared-context.md` | Baixo | 🟡 Média |
| 6 | Corrigir `module.yaml` do tech-stack (status stub incorreto para java/python/go; agentes cross-cutting ausentes do registro) | `src/modules/ava-fabric-agents/tech-stack/module.yaml` | Baixo (15 min) | 🟡 Média (higiene, não bloqueia Meu-ERP) |
| 7 | Remover header duplicado "G11 — SDK Version Validation" em `coder-dotnet-backend.md` (linhas 270 e 338) | `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` | Trivial | 🟢 Baixa |

### Ordem recomendada de execução

1. **Ação #1** primeiro — é o bug determinístico de menor esforço e maior impacto; sem ele, mesmo depois
   de corrigir tudo o resto, o próximo run de codegen .NET vai travar da mesma forma no Step 5.5.
2. **Ação #3** pode rodar em paralelo (é só orquestração/execução, não código) — desbloqueia o Meu-ERP
   para efetivamente chegar à fase de codegen e validar as ações #1/#2 na prática.
3. **Ação #2** antes do primeiro run real de codegen .NET em produção — reduz risco de erros de
   compilação não cobertos pelos guardrails G1-G11 existentes (que tratam sintomas pontuais, não a
   estrutura da solução).
4. **Ações #4 e #5** — resolver antes de abrir o pipeline para outros projetos além do Meu-ERP, para
   evitar que o próximo operador tropece na mesma ambiguidade.
5. **Ações #6 e #7** — higiene, sem urgência.

---

## 9. Referências

- `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` (v1.7.1)
- `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` (v1.0.0)
- `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md` (v1.0.0, referência de padrão)
- `src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md` (v2.3.0)
- `src/shared/data/scaffold-manifests/dotnet-scaffold-manifest.yaml`
- `src/shared/data/scaffold-manifests/angular-scaffold-manifest.yaml`
- `src/shared/utils/verify_scaffold.py`
- `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`
- `src/modules/ava-fabric-agents/tobe-architecture/agents/coder-dotnet.md`
- `projects/Meu-ERP-001-AST-AS-IS-Orchestrator/context/shared-context.md`
- `projects/Meu-ERP-001-AST-AS-IS-Orchestrator/context/project-config.yaml`
- `docs/tech-stack-io-map.md` (mapa completo de input/output por agente, produzido como parte desta investigação)
