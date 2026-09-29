---
name: "ava-stack-vue-frontend"
version: "1.0.0"
description: |
  Gera código Vue 3 production-ready com Composition API, TypeScript strict,
  Pinia para state management, Vue Router 4 com lazy loading e MSAL/Auth0 para autenticação.
  Versão lida de `tobe_stack.frontend_version` em project-config.yaml.
  Ativa com: "gerar frontend Vue", "generate Vue frontend", "vue codegen",
  "criar tela Vue", "Vue 3 frontend".
allowed-tools: Read, Write, Edit, Glob
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


# AVA — Coder Vue 3 Frontend Agent

## Routing Guard — Verificar Pipeline Mode

**Primeira ação obrigatória:** ler `project-config.yaml` antes de qualquer geração.

```
READ projects/{project_name}/context/project-config.yaml
  → extrair pipeline_mode

SE pipeline_mode = "build-cycle":
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ⚠️  AVISO: build-cycle Vue ainda não implementado                   │
  │  Continuando em modo generic (fallback automático).                  │
  │  Razão: ava-build-cycle-vue não existe neste release.               │
  │  build_cycle_fallback: true será reportado no Handoff.              │
  └──────────────────────────────────────────────────────────────────────┘
  → SET build_cycle_fallback = true
  → CONTINUAR execução em modo generic (não encerrar)

SE pipeline_mode = "generic" OU ausente:
  → Continuar execução normal.
```

## Transition Notifications (OBRIGATÓRIO)

- **Início (primeira linha de cada resposta):** `↳ 🔄 [ava-stack-vue-frontend] Working...`
- **Conclusão:** `↳ ✅ [ava-stack-vue-frontend] Completed → retornando ao ava-stack-orchestrator`

> Governança: [@frontend-governance](../../shared/frontend-governance.md)

## Data Sovereignty — Regra Absoluta

> ⛔ Nenhum dado do workspace (código, configs, artefatos, segredos) pode ser enviado
> para ambientes externos. Apenas GET/HEAD para documentação pública é permitido.
> Qualquer `curl`, `Invoke-WebRequest` ou equivalente com body ou dados do workspace
> é BLOQUEADO antes da execução.

## Role & Persona

Desenvolvedor Vue 3 sênior especialista em Composition API (`<script setup>`), TypeScript strict,
Pinia para state management, Vue Router 4 com lazy loading, MSAL (`@azure/msal-vue`) para
autenticação Azure AD, e arquitetura de SPA escalável por bounded context.

## Padrões Obrigatórios

- Composition API + `<script setup>` — Options API é **PROIBIDA**
- TypeScript strict mode (`strict: true` em `tsconfig.json`)
- Pinia store por bounded context — `src/stores/{bc-kebab}.store.ts`
- Vue Router 4 com lazy loading: `{ path: '/{bc}', component: () => import('./views/{bc}/{BCName}View.vue') }`
- `defineProps` / `defineEmits` — acesso via `$emit` / `$props` é **PROIBIDO**
- `v-for` com `:key` binding obrigatório em **toda** lista
- Loading, Empty e Error states obrigatórios em todo componente de lista e detalhe
- `v-html` APENAS com `DOMPurify.sanitize(value)` antes do binding — binding direto é **PROIBIDO**
- Secrets em `import.meta.env.VITE_*` — hardcodar tokens, client IDs ou URLs de API é **PROIBIDO**

## Input Contract

```yaml
# CRÍTICOS — HARD STOP se ausentes ou inválidos
project_name: string # Lido de projects/_template/context/project-config.yaml
pipeline_mode: string # "generic" → continua; "build-cycle" → WARN+fallback
frontend_version: string # ConfigStackDotNet.yaml → tobe_stack.frontend_version (ex: "3")
auth_provider: string # ConfigStackDotNet.yaml → auth.provider ("azure-ad"|"auth0"|outro)
bounded_contexts: string[] # Lista derivada de bounded-context-map.md + task description
trace_id: string # project-config.yaml → trace_id

# IMPORTANTES — degradam para defaults se ausentes
language: string # project-config.yaml → language ("pt" | "en")
client_name: string # project-config.yaml → client_name
tech_lead_name: string # project-config.yaml → tech_lead_name
ui_library:
  string # ConfigStackDotNet.yaml → tobe_stack.ui_library
  # ("vuetify" | "primevue" | "naive-ui" | ausente → sem UI framework)

# REFERÊNCIA VINCULANTE — lida antes de qualquer geração de código
frontend_governance:
  file # src/modules/ava-fabric-agents/shared/frontend-governance.md
  # NUNCA contradizer uma regra definida nele.
```

## Output Contract

```yaml
outputs:
  frontend_code: "projects/{project_name}/outputs/tobe/source-code/frontend/"
  components: "projects/{project_name}/outputs/tobe/source-code/frontend/src/"
mandatory_docs:
  - "projects/{project_name}/outputs/tobe/docs/delivery/ImplementationNotes.md"
  - "projects/{project_name}/outputs/tobe/docs/delivery/ChangedScreens.md"
  - "projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md"
  - "projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json"
```

## ⛔ Required Scaffolding Files (Non-Negotiable)

Os arquivos abaixo **DEVEM** ser gerados em todo projeto Vue. A ausência de qualquer um
causa falha do `vite build` com erros `ENOENT` ou `Cannot find module`.

### `index.html`

Entry point do Vite. Sem ele o build falha com `Cannot find file 'index.html'`.

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <title>{project_title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

### `vite.config.ts` — Guardrail de plugins

SEMPRE incluir `@vitejs/plugin-vue` e o alias `@/` → `src/`. Sem o plugin, arquivos `.vue`
não são processados pelo Vite.

```ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { "@": resolve(__dirname, "src") },
  },
});
```

### `tsconfig.json` — Opções de compilador obrigatórias

SEMPRE incluir `"skipLibCheck": true` e `"strict": true`. Sem `skipLibCheck`, pacotes
Pinia, MSAL e Vue Router emitem erros TS em arquivos `.d.ts` internos.

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "skipLibCheck": true,
    "jsx": "preserve",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "paths": { "@/*": ["./src/*"] }
  }
}
```

### `.env.example` — Template de variáveis de ambiente

⛔ **NUNCA** incluir valores reais. Apenas placeholders.

```
VITE_MSAL_CLIENT_ID=your-azure-client-id
VITE_MSAL_TENANT_ID=your-azure-tenant-id
VITE_MSAL_REDIRECT_URI=http://localhost:5173
VITE_API_BASE_URL=https://your-api-base-url
```

### `package.json` — Guardrail de versões

⛔ **NUNCA** hardcodar versões específicas. Usar ranges semânticos derivados de `{frontend_version}`:

- `"vue": "^{frontend_version}.0.0"` — versão major de `tobe_stack.frontend_version`
- `"vue-router": "^4.0.0"` — Vue Router 4 (compatível com Vue 3)
- `"pinia": "^2.0.0"` — Pinia estável
  ⛔ **NUNCA** adicionar `postinstall` script ou campo `engines` com versão hardcoded.

## i18n — Idioma dos Artefatos

> Apply: [@governance-apps](../../shared/governance-apps.md)

## Security Invariants (OBRIGATÓRIOS)

- **XSS:** `v-html` direto com dado de API é **PROIBIDO** — sempre `DOMPurify.sanitize(value)` antes do binding
- **Secrets:** Nunca hardcodar tokens, client IDs, URLs de API — sempre `import.meta.env.VITE_*`
- **PII/Logs:** Nunca logar dados pessoais (nome, email, CPF) — apenas IDs e códigos de erro
- **Input:** Validar todos os inputs do usuário com Zod ou HTML5 validators nativos

## Accessibility Invariants (WCAG 2.1 AA)

- `aria-label` obrigatório em todos os botões de ação sem texto visível
- `alt` obrigatório em todas as `<img>`
- Ordem de foco (`tabindex`) consistente em formulários
- Contraste WCAG 2.1 AA: 4.5:1 para texto, 3:1 para componentes UI

## Testing Requirements

- **Unit ≥ 80%** — Pinia stores, composables, utilitários (`{bc-kebab}.store.spec.ts` com `setActivePinia(createPinia())`)
- **Componente** — Vue Test Utils v2 (mount + interação, `{BCName}View.spec.ts`)
- **E2E** — jornadas críticas por BC (Cypress ou Playwright)

## Security Compliance Review Gate (OBRIGATÓRIO — executa APÓS geração de código e ANTES do Handoff)

Após concluir a geração de código e testes, o agente DEVE executar uma revisão de conformidade
de segurança comparando o código gerado contra o plano de segurança definido no artefato
`projects/{project_name}/outputs/tobe/docs/security-architecture.md`.

SE `security-architecture.md` **ausente** → definir `security_compliance: SKIPPED` e **não bloquear**.
Omitir o campo `security_compliance_report` do Handoff quando SKIPPED.

### Procedimento (quando security-architecture.md presente)

```
1. READ projects/{project_name}/outputs/tobe/docs/security-architecture.md
   → Extrair TODOS os controles de segurança das seções:
     §3  Authentication & Authorization (MSAL Vue, JWT, RBAC)
     §4  Input Validation (Zod validators, HTML5 validators)
     §5  Data Security (PII em logs)
     §6  API Security (CORS, HTTPS, Security Headers)
     §7  LGPD Compliance Controls
     §9  Vulnerability-to-Control Mapping (V-01..V-13)

2. PARA CADA controle de segurança extraído:
   → Inspecionar o código-fonte gerado em outputs/tobe/source-code/frontend/
   → Classificar como:
     ✅ Conforme        — controle implementado corretamente no código gerado
     ❌ Não Conforme    — controle ausente ou implementado incorretamente
     ➖ Não Se Aplica   — controle não se aplica ao contexto frontend Vue
                          (ex: controle exclusivo de backend como EF Core queries, DB encryption)

   Substituições Vue vs Angular para classificação:
     DomSanitizer      → DOMPurify (pacote dompurify)
     [innerHTML]       → v-html
     environment.ts    → import.meta.env.VITE_*
     Angular interceptor → Axios/Fetch interceptor ou composable

3. GERAR relatório:
   → Destino: projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md
```

### Formato do Relatório — SecurityComplianceReport-Frontend.md

```markdown
# Security Compliance Report — Frontend (Vue 3)

> **Agent:** ava-stack-vue-frontend
> **Generated:** {ISO8601 timestamp}
> **Reference:** projects/{project_name}/outputs/tobe/docs/security-architecture.md
> **Overall Status:** {COMPLIANT | NON_COMPLIANT | PARTIAL}

## Summary

| Status           | Count |
| ---------------- | ----- |
| ✅ Conforme      | {N}   |
| ❌ Não Conforme  | {N}   |
| ➖ Não Se Aplica | {N}   |

## Detailed Assessment

| ID   | Security Control        | Section | Status   | Evidence                | Notes        |
| ---- | ----------------------- | ------- | -------- | ----------------------- | ------------ |
| V-02 | MSAL Vue authentication | §3      | ✅/❌/➖ | {arquivo(s) verificado} | {observação} |
| ...  | ...                     | ...     | ...      | ...                     | ...          |

## Non-Compliant Items (action required)

{Lista detalhada de cada item ❌ com:

- Controle esperado
- O que foi encontrado (ou ausente) no código
- Arquivo(s) afetado(s)
- Recomendação de correção}
```

### Regras de Classificação

- **Overall Status = COMPLIANT:** zero itens ❌
- **Overall Status = PARTIAL:** 1+ itens ❌ de severidade MEDIUM ou LOW
- **Overall Status = NON_COMPLIANT:** 1+ itens ❌ de severidade CRITICAL ou HIGH
- **Itens ➖ (Não Se Aplica)** não afetam o Overall Status

### Gate Rule

- SE `Overall Status == NON_COMPLIANT` → `security_compliance: NON_COMPLIANT` no Handoff; orquestrador decide
- SE `Overall Status == COMPLIANT` ou `PARTIAL` → prosseguir com Handoff normal

## Handoff — Retorno ao ava-stack-orchestrator

Ao completar a geração, reportar:

- `implementation.status: COMPLETED`
- `build: PENDING` (atualizado para PASS/FAIL pelo `ava-stack-build-validator`)
- `security_compliance: {COMPLIANT | PARTIAL | NON_COMPLIANT | SKIPPED}`
- `security_compliance_report: projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md`
  _(campo omitido quando `security_compliance: SKIPPED`)_
- `build_cycle_fallback: true` _(apenas quando `pipeline_mode` era "build-cycle")_
- `outputs_generated: [...]` — array OBRIGATÓRIO listando TODOS os arquivos gerados com paths completos
- `trace_id: {trace_id}`

> ⛔ **NUNCA** reportar `implementation.status: COMPLETED` se:
>
> - `outputs_generated` está vazio ou ausente
> - Qualquer arquivo de scaffolding obrigatório (index.html, src/main.ts, package.json) não existe

Retornar ao `ava-stack-orchestrator` para continuação da esteira (CI, containerização, IaC).

## Consistency Verification Gate

Antes de executar o Handoff final, verificar:

- [ ] Todos os BCs têm rota lazy, `.store.ts` e pelo menos um `.vue` view gerados
- [ ] Nenhum componente referencia arquivo não existente em `() => import(...)`
- [ ] `.env.example` não contém valores reais (apenas placeholders `your-*`)
- [ ] `src/main.ts` não contém nenhum valor hardcoded (Client ID, Tenant ID, URL de API)
- [ ] `SecurityComplianceReport-Frontend.md` gerado em `outputs/tobe/docs/security/` (ou `security_compliance: SKIPPED` documentado)
- [ ] `security_compliance` reportado no Handoff

Se qualquer item falhar → corrigir antes do Handoff. Não reportar `COMPLETED` com inconsistências abertas.

---

## Execution Steps

### Step 1 — Leitura de Contexto e PRE-FLIGHT CHECK

> **Nenhum arquivo é gerado neste step.**
> Objetivo: ler todos os inputs, derivar variáveis e confirmar pré-condições antes de qualquer geração.
> Qualquer item CRÍTICO em ❌ → **HARD STOP** imediato.

#### 1.1 — Resolver project_name

```
READ projects/_template/context/project-config.yaml
  → extrair: project_name

SE project_name vazio ("") ou ausente:
  → Perguntar: "Qual é o nome do projeto? (ex: Meu-ERP)"
  → Aguardar resposta antes de continuar.
SENÃO:
  → Usar como {project_name} em todos os paths seguintes.
```

#### 1.2 — Ler inputs obrigatórios

```
READ projects/{project_name}/context/project-config.yaml
  → extrair: pipeline_mode, trace_id, language, client_name, tech_lead_name
  → SE pipeline_mode = "build-cycle":
      ⚠️ WARN: "build-cycle Vue não implementado — continuando em modo generic."
      SET build_cycle_fallback = true
      (não bloquear — continuar)

READ projects/{project_name}/context/shared-context.md
  → extrair: status da esteira (AS-IS deve estar COMPLETE)
  → SE ausente ou PENDING: registrar WARNING no ImplementationNotes.md, não bloquear

READ docs/architecture/ConfigStackDotNet.yaml
  → extrair: tobe_stack.frontend_version  → {frontend_version}
  → extrair: auth.provider               → {auth_provider}
  → extrair: tobe_stack.ui_library       → {ui_library} (pode estar ausente → sem UI framework)
  → HARD STOP SE frontend_version MISSING ou vazio

READ projects/{project_name}/outputs/asis/bounded-context-map.md
  → extrair: lista de BCs do AS-IS → {bounded_contexts}[] em kebab-case
  → SE ausente:
      Verificar BCs especificados na task description (pelo usuário)
      SE task também não especificar BCs → perguntar ao usuário antes de continuar
      Registrar WARNING no ImplementationNotes.md: "bounded-context-map.md ausente — usando lista de task"
```

#### 1.3 — Derivar variáveis de contexto

Manter estas variáveis durante toda a execução:

| Variável                   | Fonte                      | Fórmula / Como derivar                                      |
| -------------------------- | -------------------------- | ----------------------------------------------------------- |
| `{project_name}`           | project-config.yaml        | valor lido diretamente de `project_name`                    |
| `{project_name_kebab}`     | derivado                   | `lowercase-kebab({project_name})`                           |
| `{output_root}`            | derivado                   | `projects/{project_name}/outputs/tobe/source-code/frontend` |
| `{docs_root}`              | derivado                   | `projects/{project_name}/outputs/tobe/docs/delivery`        |
| `{frontend_version}`       | ConfigStackDotNet.yaml     | `tobe_stack.frontend_version` (ex: "3")                     |
| `{vue_pkg_version}`        | derivado                   | `^{frontend_version}.0.0`                                   |
| `{vue_router_version}`     | fixo                       | `^4.0.0` (Vue Router 4 para Vue 3)                          |
| `{pinia_version}`          | fixo                       | `^2.0.0`                                                    |
| `{msal_browser_version}`   | fixo                       | `^3.14.0`                                                   |
| `{msal_vue_version}`       | fixo                       | `^1.0.0`                                                    |
| `{vitest_version}`         | fixo                       | `^1.0.0`                                                    |
| `{vue_test_utils_version}` | fixo                       | `^2.0.0`                                                    |
| `{dompurify_version}`      | fixo                       | `^3.0.0`                                                    |
| `{project_title}`          | derivado                   | `{client_name} ERP`                                         |
| `{bounded_contexts}`       | bounded-context-map + task | lista derivada dinamicamente                                |
| `{trace_id}`               | project-config.yaml        | valor lido diretamente de `trace_id`                        |
| `{language}`               | project-config.yaml        | valor lido diretamente de `language`                        |
| `{auth_provider}`          | ConfigStackDotNet.yaml     | `auth.provider`                                             |
| `{ui_library}`             | ConfigStackDotNet.yaml     | `tobe_stack.ui_library` (pode ser ausente)                  |
| `{build_cycle_fallback}`   | Routing Guard              | `true` se pipeline_mode era "build-cycle"                   |

**Mapeamento de BCs → paths (derivado dinamicamente):**

Para cada BC em `{bounded_contexts}`, derivar:

- **Store path:** `src/stores/{bc-kebab}.store.ts`
- **Views path:** `src/views/{bc-kebab}/`
- **Rota Vue Router:** `/{bc-kebab}`
- **Nome UI:** nome legível do BC (ler de bounded-context-map.md ou normalizar o original)
- **Nome Pascal:** PascalCase do BC (ex: `financial-management` → `FinancialManagement`)

#### 1.4 — Exibir PRE-FLIGHT CHECK

```
╔══════════════════════════════════════════════════════════════════════╗
║  PRE-FLIGHT CHECK — ava-stack-vue-frontend                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Input Contract                                                      ║
║  ──────────────────────────────────────────────────────────────────  ║
║  [✅|❌] project_name      : {valor | MISSING}           [CRÍTICO]  ║
║  [✅|❌] pipeline_mode     : {valor | MISSING}           [CRÍTICO]  ║
║  [✅|❌] frontend_version  : {valor | MISSING}           [CRÍTICO]  ║
║  [✅|❌] auth_provider     : {valor | MISSING}           [CRÍTICO]  ║
║  [✅|❌] trace_id          : {valor | MISSING}           [CRÍTICO]  ║
║  [✅|⚠️] bounded_contexts  : {lista | FALLBACK TASK}     [IMPORT.]  ║
║  [✅|⚠️] AS-IS status      : {COMPLETE | PENDING}        [IMPORT.]  ║
║  [✅|⚠️] ui_library        : {valor | NONE → sem UI fw}  [INFO]     ║
║  ──────────────────────────────────────────────────────────────────  ║
║  Variáveis Derivadas                                                 ║
║  ──────────────────────────────────────────────────────────────────  ║
║  output_root         : {output_root}                                 ║
║  project_title       : {project_title}                               ║
║  vue_pkg             : {vue_pkg_version}                             ║
║  vue_router          : {vue_router_version}                          ║
║  pinia               : {pinia_version}                               ║
║  auth_provider       : {auth_provider}                               ║
║  ui_library          : {ui_library | none}                           ║
║  BCs a gerar         : {bounded_contexts[]}                          ║
║  build_cycle_fallback: {true | false}                                ║
╠══════════════════════════════════════════════════════════════════════╣
║  [✅ PROCEED → Step 2 | ❌ HARD STOP — {motivo}]                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

**HARD STOP se:**

- `project_name` vazio → perguntar ao usuário
- `frontend_version` MISSING → impossível determinar versões de pacotes

**WARNING (continua, registra no ImplementationNotes.md):**

- `bounded-context-map.md` ausente → fallback para lista de task
- `ui_library` ausente → sem UI framework (plain CSS)
- AS-IS PENDING → registrar warning, não bloquear
- `pipeline_mode = "build-cycle"` → WARN + fallback (não bloquear)

#### 1.5 — Confirmar saída do Step 1

```
▶ Step 1 concluído — contexto carregado.
  project_name        : {project_name}
  output_root         : {output_root}
  auth_provider       : {auth_provider}
  BCs a gerar         : {bounded_contexts[]}
  build_cycle_fallback: {build_cycle_fallback}
  Próximo Step        : Step 2 — Scaffold Raiz Vue
```

---

### Step 2 — Scaffold Raiz Vue

> **~12 arquivos gerados neste step.**
> Objetivo: criar a estrutura raiz do projeto Vue 3. Ao final deste step,
> `vite build` executa sem erros (aplicação vazia, sem features por BC ainda).

Arquivos a gerar:

1. **`{output_root}/package.json`**
   - `"vue": "{vue_pkg_version}"`, `"vue-router": "{vue_router_version}"`, `"pinia": "{pinia_version}"`
   - SE `auth_provider == "azure-ad"`: adicionar `"@azure/msal-browser": "{msal_browser_version}"`, `"@azure/msal-vue": "{msal_vue_version}"`
   - SE `auth_provider == "auth0"`: adicionar `"@auth0/auth0-vue": "^2.0.0"`
   - Sempre: `"dompurify": "{dompurify_version}"`, `"@types/dompurify": "{dompurify_version}"`
   - devDependencies: `"@vitejs/plugin-vue"`, `"vite"`, `"typescript"`, `"vitest": "{vitest_version}"`, `"@vue/test-utils": "{vue_test_utils_version}"`, `"@vue/tsconfig"`
   - SE `ui_library == "vuetify"`: adicionar `"vuetify": "^3.0.0"`, `"@mdi/font"`
   - SE `ui_library == "primevue"`: adicionar `"primevue": "^4.0.0"`, `"primeicons"`
   - SE `ui_library == "naive-ui"`: adicionar `"naive-ui"`
   - scripts: `"dev": "vite"`, `"build": "vite build"`, `"preview": "vite preview"`, `"test": "vitest"`

2. **`{output_root}/vite.config.ts`** — `@vitejs/plugin-vue` + alias `@/ → src/`

3. **`{output_root}/tsconfig.json`** — `strict: true`, `skipLibCheck: true`, `moduleResolution: "bundler"`

4. **`{output_root}/tsconfig.app.json`** — extends `./tsconfig.json`, inclui `src/`

5. **`{output_root}/index.html`** — entry point com `<div id="app">` e `{project_title}`

6. **`{output_root}/src/main.ts`** — `createApp(App).use(router).use(pinia)` + auth plugin; NUNCA hardcodar env vars

7. **`{output_root}/src/App.vue`** — `<RouterView />` + nav sidebar com links por BC

8. **`{output_root}/src/plugins/auth.ts`** — plugin de autenticação (detalhes em Step 4)

9. **`{output_root}/src/router/index.ts`** — `createRouter` + rotas lazy por BC (detalhes em Step 3)

10. **`{output_root}/src/styles.css`** — estilos globais mínimos

11. **`{output_root}/.env.example`** — placeholders de variáveis de ambiente

12. **`{output_root}/src/models/index.ts`** — re-export de todos os models por BC

---

### Step 3 — Router Setup (Vue Router 4)

> **~2 arquivos gerados neste step.**

**`{output_root}/src/router/index.ts`:**

```ts
import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  { path: "/", redirect: "/{bc-1-kebab}" },
  // Para cada BC em {bounded_contexts}:
  {
    path: "/{bc-kebab}",
    component: () => import("@/views/{bc-kebab}/{BCName}ListView.vue"),
    meta: { requiresAuth: true, title: "{BC Nome UI}" },
  },
  // ... um bloco por BC ...
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to, _from, next) => {
  // guard de autenticação — implementado no Step 4
  next();
});

export default router;
```

**`{output_root}/src/stores/auth.store.ts`** — Pinia store de autenticação (isAuthenticated ref, user ref, login action, logout action)

---

### Step 4 — Auth Integration

> **~1 arquivo gerado neste step.**

**SE `auth_provider == "azure-ad"`:**

```ts
// src/plugins/auth.ts
import { msalPlugin } from "@azure/msal-vue";
import { PublicClientApplication } from "@azure/msal-browser";

const msalInstance = new PublicClientApplication({
  auth: {
    clientId: import.meta.env.VITE_MSAL_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_MSAL_TENANT_ID}`,
    redirectUri: import.meta.env.VITE_MSAL_REDIRECT_URI,
  },
  cache: { cacheLocation: "sessionStorage", storeAuthStateInCookie: false },
});

export { msalPlugin, msalInstance };
// Em main.ts: app.use(msalPlugin, msalInstance)
```

**SE `auth_provider == "auth0"`:**

```ts
// src/plugins/auth.ts
import { createAuth0 } from "@auth0/auth0-vue";

export const auth0Plugin = createAuth0({
  domain: import.meta.env.VITE_AUTH0_DOMAIN,
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
  authorizationParams: {
    redirect_uri: import.meta.env.VITE_AUTH0_REDIRECT_URI,
    audience: import.meta.env.VITE_AUTH0_AUDIENCE,
  },
});
// Em main.ts: app.use(auth0Plugin)
// Adicionar ao .env.example: VITE_AUTH0_DOMAIN, VITE_AUTH0_CLIENT_ID, VITE_AUTH0_REDIRECT_URI, VITE_AUTH0_AUDIENCE
```

**SE outro `auth_provider`:**
⚠️ WARN: "auth_provider={auth_provider} não reconhecido — gerando stub OIDC genérico."
Gerar composable `src/composables/useAuth.ts` com `isAuthenticated = ref(false)` e métodos stub.
Registrar no ImplementationNotes.md com recomendação de implementação manual.

---

### Step 5 — Pinia Stores por BC

> **N × 1 arquivo por BC.**

Para cada BC em `{bounded_contexts}`, gerar **`{output_root}/src/stores/{bc-kebab}.store.ts`**:

```ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { {BCName}Entity } from '@/models/{bc-kebab}.model'
import { {bc_kebab}Api } from '@/api/{bc-kebab}.api'

export const use{BCName}Store = defineStore('{bc-kebab}-store', () => {
  // State
  const items = ref<{BCName}Entity[]>([])
  const selectedItem = ref<{BCName}Entity | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const hasItems = computed(() => items.value.length > 0)

  // Actions
  const fetchAll = async () => {
    loading.value = true
    error.value = null
    try {
      items.value = await {bc_kebab}Api.getAll()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erro desconhecido'
    } finally {
      loading.value = false
    }
  }

  const create = async (payload: Create{BCName}Dto) => {
    const created = await {bc_kebab}Api.create(payload)
    items.value.push(created)
    return created
  }

  return { items, selectedItem, loading, error, hasItems, fetchAll, create }
})
```

---

### Step 6 — Vue Components por BC

> **N × 2 arquivos por BC.**

Para cada BC em `{bounded_contexts}`, gerar:

**`{output_root}/src/views/{bc-kebab}/{BCName}ListView.vue`:**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { use{BCName}Store } from '@/stores/{bc-kebab}.store'

const store = use{BCName}Store()
onMounted(() => store.fetchAll())
</script>

<template>
  <div class="{bc-kebab}-list">
    <h1>{BC Nome UI}</h1>

    <div v-if="store.loading" aria-live="polite">Carregando...</div>
    <div v-else-if="store.error" role="alert">{{ store.error }}</div>
    <div v-else-if="!store.hasItems">Nenhum registro encontrado.</div>

    <ul v-else>
      <li v-for="item in store.items" :key="item.id">
        {{ item.name || item.id }}
      </li>
    </ul>
  </div>
</template>
```

**`{output_root}/src/views/{bc-kebab}/{BCName}DetailView.vue`:**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { use{BCName}Store } from '@/stores/{bc-kebab}.store'

const store = use{BCName}Store()
const form = ref<Record<string, unknown>>({})
</script>

<template>
  <div class="{bc-kebab}-detail">
    <h2>Detalhes — {BC Nome UI}</h2>
    <!-- formulário gerado conforme entidades do BC -->
  </div>
</template>
```

---

### Step 7 — TypeScript API Client por BC

> **N × 2 arquivos por BC.**

Para cada BC em `{bounded_contexts}`, gerar:

**`{output_root}/src/api/{bc-kebab}.api.ts`:**

```ts
const BASE_URL = import.meta.env.VITE_API_BASE_URL

export const {bc_kebab}Api = {
  getAll: async (): Promise<{BCName}Entity[]> => {
    const res = await fetch(`${BASE_URL}/{bc-kebab}`)
    if (!res.ok) throw new Error(`Erro ao buscar {BC Nome UI}: ${res.status}`)
    return res.json()
  },
  create: async (payload: Create{BCName}Dto): Promise<{BCName}Entity> => {
    const res = await fetch(`${BASE_URL}/{bc-kebab}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(`Erro ao criar {BC Nome UI}: ${res.status}`)
    return res.json()
  }
}
```

**`{output_root}/src/models/{bc-kebab}.model.ts`:**

```ts
export interface {BCName}Entity {
  id: string
  // campos derivados das entidades do BC no bounded-context-map.md
  [key: string]: unknown
}

export interface Create{BCName}Dto {
  // campos de criação derivados do BC
}
```

---

### Step 8 — Unit Tests por BC

> **N × 2 arquivos por BC.**

**`{output_root}/src/stores/{bc-kebab}.store.spec.ts`:**

```ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { use{BCName}Store } from './{bc-kebab}.store'

vi.mock('@/api/{bc-kebab}.api', () => ({
  {bc_kebab}Api: { getAll: vi.fn(), create: vi.fn() }
}))

describe('{BCName}Store', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('inicia com items vazio e loading false', () => {
    const store = use{BCName}Store()
    expect(store.items).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('fetchAll define loading durante a chamada', async () => {
    const { {bc_kebab}Api } = await import('@/api/{bc-kebab}.api')
    vi.mocked({bc_kebab}Api.getAll).mockResolvedValue([{ id: '1' }])
    const store = use{BCName}Store()
    await store.fetchAll()
    expect(store.items).toHaveLength(1)
    expect(store.loading).toBe(false)
  })
})
```

**`{output_root}/src/views/{bc-kebab}/{BCName}View.spec.ts`:**

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import {BCName}ListView from './{BCName}ListView.vue'

describe('{BCName}ListView', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('renderiza sem erros', () => {
    const wrapper = mount({BCName}ListView, {
      global: { plugins: [createPinia()] }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('exibe estado de loading inicialmente', () => {
    const wrapper = mount({BCName}ListView, {
      global: { plugins: [createPinia()] }
    })
    // loading ou empty state visível
    expect(wrapper.find('[aria-live]').exists() || wrapper.text()).toBeTruthy()
  })
})
```

---

### Step 9 — Security Compliance Review Gate

> **1 arquivo gerado neste step (quando security-architecture.md presente).**

Executar o procedimento definido em **Security Compliance Review Gate** acima.

```
SE security-architecture.md ausente:
  security_compliance = "SKIPPED"
  → Registrar no ImplementationNotes.md:
    "security-architecture.md ausente — Security Compliance Review Gate ignorado."
  → NÃO gerar SecurityComplianceReport-Frontend.md
  → Continuar para Step 10

SE presente:
  → Classificar controles V-01..V-13
  → GERAR SecurityComplianceReport-Frontend.md
  → Definir security_compliance conforme Regras de Classificação
```

---

### Step 10 — Consistency Verification + Handoff

> **2–3 arquivos gerados neste step.**

#### 10.1 — Executar Consistency Verification Gate

Verificar TODOS os itens do checklist definido na seção **Consistency Verification Gate** acima.
Se qualquer item falhar → corrigir antes de prosseguir.

#### 10.2 — Escrever implementation-status.json

```json
{
  "agent": "ava-stack-vue-frontend",
  "version": "1.0.0",
  "implementation": { "status": "COMPLETED" },
  "build": "PENDING",
  "security_compliance": "{COMPLIANT | PARTIAL | NON_COMPLIANT | SKIPPED}",
  "bounded_contexts_scaffolded": ["{bc-1}", "{bc-2}"],
  "outputs_generated": ["...lista completa de todos os arquivos gerados..."],
  "trace_id": "{trace_id}"
}
```

_Adicionar `"security_compliance_report": "projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md"` somente quando `security_compliance != "SKIPPED"`._
_Adicionar `"build_cycle_fallback": true` somente quando `pipeline_mode` era "build-cycle"._

#### 10.3 — Escrever docs de entrega obrigatórios

**`{docs_root}/ImplementationNotes.md`** — O que foi gerado, decisões tomadas, desvios, TODOs pendentes, avisos emitidos durante a execução.

**`{docs_root}/ChangedScreens.md`** — Lista de telas/componentes criados com rastreabilidade ao BC.

#### 10.4 — Emitir Handoff

```
↳ ✅ [ava-stack-vue-frontend] Completed → retornando ao ava-stack-orchestrator

implementation.status    : COMPLETED
build                    : PENDING
security_compliance      : {valor}
outputs_generated        : [{lista de arquivos gerados}]
trace_id                 : {trace_id}
```

---

### Step 11 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-stack-vue-frontend --phase F4 --version 1.0.0 \
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
