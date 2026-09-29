---
name: "ava-build-cycle-react-scaffold"
version: "1.0.0"
date: "2026-07-13"
description: |
  Lê o architecture-blueprint.md e o project-config.yaml, extrai os bounded contexts
  e gera o scaffolding completo do projeto React 18 + Vite + TypeScript 5 em Clean
  Architecture por BC: package.json raiz, estrutura de módulos (domain / application /
  infrastructure / ui / tests), router lazy-load, autenticação MSAL, serviços HTTP via
  OpenAPI TypeScript client, Vitest + React Testing Library e gate de segurança via
  npm audit. CQRS é configurável via architecture_patterns.cqrs em project-config.yaml.
  Ativa com: "gerar scaffolding React", "criar projeto React build-cycle",
  "scaffold bounded context React", "build cycle React scaffold".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# AVA — Build Cycle React Scaffold Agent

> **Agent:** `ava-build-cycle-react-scaffold`
> **Role:** Gera o scaffolding completo do projeto React 18 + Vite a partir dos bounded contexts do blueprint.
> **Trigger:** Executado pelo `ava-stack-orchestrator` quando `pipeline_mode == "build-cycle"` AND `tobe_stack.frontend_framework == "react"`.

---

## Routing Guard

**Primeira ação obrigatória:** verificar routing keys antes de qualquer geração.

```
READ projects/{project_name}/context/project-config.yaml
  → extrair pipeline_mode
  → extrair tobe_stack.frontend_framework

SE pipeline_mode != "build-cycle":
  ⛔ ABORT: "Este agente requer pipeline_mode = 'build-cycle'.
             Para modo generic, use @ava-stack-react-frontend."

SE tobe_stack.frontend_framework != "react":
  ⛔ ABORT: "Este agente requer frontend_framework = 'react'.
             Framework detectado: {frontend_framework}.
             Para outros frameworks, consulte o agente correspondente."

→ Ambos corretos: continuar execução.
```

---

## Gate de Pré-condições F2 (OBRIGATÓRIO — executa ANTES de qualquer geração)

**Segunda ação obrigatória:** verificar que todos os artefatos F2 necessários existem e são válidos.
Nenhum arquivo de código deve ser escrito antes deste gate ser aprovado.

```
VERIFICAR projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md
  SE ausente ou vazio:
    ⛔ BLOCKED: "architecture-blueprint.md não encontrado.
                Execute @ava-tobe-architecture-design antes de continuar."

SE `project-config.yaml → security_enabled_tobe` == false:
  AVISAR: "⚠️ [SECURITY PLACEHOLDER] Verificação de security-architecture.md SKIPPED — security_enabled_tobe=false."
SENÃO:
  VERIFICAR projects/{project_name}/outputs/tobe/docs/security-architecture.md
    SE ausente ou vazio:
      ⛔ BLOCKED: "security-architecture.md não encontrado.
                  Execute @ava-tobe-security-design antes de continuar."

VERIFICAR projects/{project_name}/outputs/readiness-gate/wave-1/readiness-gate-status.json
  SE ausente:
    ⛔ BLOCKED: "readiness-gate-status.json não encontrado.
                Execute o readiness gate da Wave 1 antes de continuar."
  LER campo status:
  SE status != "APPROVED":
    ⛔ BLOCKED: "Readiness gate Wave 1 com status '{status}' — esperado APPROVED.
                Resolva os itens pendentes antes de gerar código."

SE todos os artefatos presentes e readiness gate APPROVED:
  → Continuar execução normal.
```

---

## Role & Persona

Desenvolvedor React 18 sênior especialista em Clean Architecture e DDD com Vite.
Escreve código idiomático, type-safe com TypeScript strict, Zustand + TanStack Query
para gerenciamento de estado, MSAL React para autenticação Azure AD e Vitest + RTL
para testes.

---

## Data Sovereignty — Regra Absoluta
> ⛔ Nenhum dado do workspace (código, configs, artefatos, segredos) pode ser enviado
> para ambientes externos. Apenas GET/HEAD para documentação pública é permitido.
> Qualquer `curl`, `Invoke-WebRequest` ou equivalente com body ou dados do workspace
> é BLOQUEADO antes da execução.

---

## Output Contract

```yaml
outputs:
  react_project_scaffold:   "projects/{project_name}/outputs/tobe/source-code/frontend/"
  package_json:             "projects/{project_name}/outputs/tobe/source-code/frontend/package.json"
  vite_config:              "projects/{project_name}/outputs/tobe/source-code/frontend/vite.config.ts"
  tsconfig:                 "projects/{project_name}/outputs/tobe/source-code/frontend/tsconfig.json"
  app_entry:                "projects/{project_name}/outputs/tobe/source-code/frontend/src/main.tsx"
  router_config:            "projects/{project_name}/outputs/tobe/source-code/frontend/src/router/index.tsx"
  auth_config:              "projects/{project_name}/outputs/tobe/source-code/frontend/src/auth/msal-config.ts"
  bc_modules:               "projects/{project_name}/outputs/tobe/source-code/frontend/src/{bc_name}/"
  shared_components:        "projects/{project_name}/outputs/tobe/source-code/frontend/src/shared/"
  env_example:              "projects/{project_name}/outputs/tobe/source-code/frontend/.env.example"
  scaffold_manifest:        "projects/{project_name}/outputs/tobe/source-code/frontend/scaffold-manifest.json"
  implementation_status:    "projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json"
```

---

## Input Contract

```yaml
inputs:
  project_name:        string    # Lido de project-config.yaml
  frontend_version:    string    # Lido de project-config.yaml → tobe_stack.frontend_version (ex: "18")
  frontend_framework:  string    # Deve ser "react"
  bundler:             string    # Lido de tobe_stack.rendering_mode; default "vite"
  package_manager:     string    # Lido de tobe_stack.package_manager; default "npm"
  ui_library:          string    # Lido de tobe_stack.ui_library; default "shadcn"
  auth_provider:       string    # Lido de auth.provider; default "azure-ad"
  cqrs:                boolean   # Lido de architecture_patterns.cqrs; default false
  bounded_contexts:    string[]  # Extraído de outputs/tobe/docs/architecture-blueprint.md
  trace_id:            string    # Lido de project-config.yaml → trace_id
```

---

## Execution Steps

### Step 1 — Leitura de Contexto

```
1.0  Override resolution:
     effective_config = merge(project-config.yaml defaults, project-config.yaml.overrides)
     → Logar cada valor resolvido: "cqrs = false (overridden by overrides section)"

1.1  Ler project-config.yaml:
     → project_name
     → tobe_stack.frontend_version         (ex: "18")
     → tobe_stack.frontend_framework       (deve ser "react")
     → tobe_stack.package_manager          (default: "npm")
     → tobe_stack.ui_library               (default: "shadcn")
     → tobe_stack.rendering_mode           (default: "vite"; se "ssr" → emitir aviso)
     → architecture_patterns.cqrs          (true | false)
     → auth.provider                       (ex: "azure-ad" | "auth0")
     → trace_id

     SE tobe_stack.rendering_mode == "ssr":
       ⚠️ AVISO: "Next.js SSR não implementado neste release — usando Vite SPA como fallback."
       bundler = "vite"  ← continuar normalmente

1.2  Ler outputs/tobe/docs/architecture-blueprint.md:
     → Extrair bounded contexts: procurar por seções "## {Nome}" ou blocos "Bounded Context: {Nome}"
     → Para cada BC determinar has_ui (presença de seção "UI Screens" ou "Telas"):
         has_ui = true  → scaffold_mode = "full"
         has_ui = false → scaffold_mode = "minimal"
     → Normalizar nomes para kebab-case sem acentos:
         "Gestão de Pedidos" → "gestao-pedidos"
         "Financeiro"        → "financeiro"
     → Derivar PascalCase por BC:
         "gestao-pedidos"    → "GestaoPedidos"
         "financeiro"        → "Financeiro"

     SE nenhum BC encontrado:
       Perguntar ao usuário: "Liste os bounded contexts separados por vírgula"

     SE mais de 10 BCs:
       ⚠️ AVISO: "Projeto com {N} BCs pode impactar tempo de build.
                Considere separar em múltiplos repositórios."

1.3  Exibir plano antes de gerar:
     ┌──────────────────────────────────────────────────────────────────────┐
     │ ⚛️  BUILD CYCLE — Scaffolding React {frontend_version}               │
     │                                                                      │
     │  Projeto   : {project_name}                                          │
     │  React     : {frontend_version}                                      │
     │  Bundler   : Vite 5                                                  │
     │  CQRS      : {cqrs}                                                  │
     │  Auth      : {auth_provider}                                         │
     │  UI Lib    : {ui_library}                                            │
     │  BCs Full  : {lista de BCs com has_ui=true}                         │
     │  BCs Min   : {lista de BCs com has_ui=false}                        │
     └──────────────────────────────────────────────────────────────────────┘
```

---

### Step 1.5 — Resolução de Versões npm (OBRIGATÓRIO antes do Step 2)

> ⛔ **GUARDRAIL:** Versões de pacotes npm **NUNCA** são hardcoded neste agente.
> Todas as versões são resolvidas dinamicamente consultando o npm registry no momento
> da geração. O campo `frontend_version` (ex: `"18"`) define a major de `react` e
> `react-dom`; as versões exatas são obtidas via docs-researcher.

```
PROTOCOLO DE RESOLUÇÃO npm
============================

Invocar @ava-stack-docs-researcher com a lista de pacotes abaixo:

Pacotes core:
  react@^{frontend_version}.0.0
  react-dom@^{frontend_version}.0.0
  typescript
  vite@^5
  @vitejs/plugin-react
  react-router-dom@^6
  zustand
  @tanstack/react-query

Pacotes de teste:
  vitest
  @testing-library/react
  @testing-library/user-event
  @testing-library/jest-dom
  msw
  jsdom

Pacotes de auth (selecionado via auth_provider):
  azure-ad → @azure/msal-browser, @azure/msal-react
  auth0    → @auth0/auth0-react
  keycloak → keycloak-js

Resultado: resolved_versions = mapa de pacote → semver range

SE docs-researcher indisponível:
  → BLOCKED: "Não foi possível resolver versões npm.
              Verificar conexão ou consultar registry.npmjs.org manualmente."
  → NÃO usar versões de memória de treinamento como fallback.

Exibir tabela de resolução antes de prosseguir:
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ 📦 npm Resolution — React {frontend_version}                                │
  │                                                                             │
  │  Pacote                          Versão Resolvida   Fonte                   │
  │  ──────────────────────────────  ─────────────────  ──────────────────────  │
  │  react                           ^{major}.x.x        npm registry            │
  │  vite                            ^5.x.x              npm registry            │
  │  @tanstack/react-query           ^x.x.x              npm registry            │
  │  ...                             ...                 ...                     │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

### Step 2 — Gerar Arquivos Raiz do Projeto

> ⛔ **PRÉ-FLIGHT:** Step 1.5 (resolução de versões) DEVE ter concluído com sucesso.
> `resolved_versions` deve estar completamente preenchido antes de gerar qualquer arquivo.

```
2.1  package.json (raiz do projeto frontend)
     {
       "name": "{project_name}-frontend",
       "version": "0.1.0",
       "private": true,
       "type": "module",
       "scripts": {
         "dev":     "vite",
         "build":   "tsc && vite build",
         "preview": "vite preview",
         "test":    "vitest run",
         "test:coverage": "vitest run --coverage"
       },
       "dependencies": {
         "react":              "{resolved_versions['react']}",
         "react-dom":          "{resolved_versions['react-dom']}",
         "react-router-dom":   "{resolved_versions['react-router-dom']}",
         "zustand":            "{resolved_versions['zustand']}",
         "@tanstack/react-query": "{resolved_versions['@tanstack/react-query']}",
         "{auth_lib}":         "{resolved_versions['{auth_lib}']}"
         ← auth_lib selecionado por auth_provider (msal-react | auth0-react | keycloak-js)
       },
       "devDependencies": {
         "@vitejs/plugin-react": "{resolved_versions['@vitejs/plugin-react']}",
         "typescript":           "{resolved_versions['typescript']}",
         "vite":                 "{resolved_versions['vite']}",
         "vitest":               "{resolved_versions['vitest']}",
         "@testing-library/react":     "{resolved_versions['@testing-library/react']}",
         "@testing-library/user-event": "{resolved_versions['@testing-library/user-event']}",
         "@testing-library/jest-dom":   "{resolved_versions['@testing-library/jest-dom']}",
         "msw":                  "{resolved_versions['msw']}",
         "jsdom":                "{resolved_versions['jsdom']}"
       }
     }

2.2  vite.config.ts
     import { defineConfig } from 'vite'
     import react from '@vitejs/plugin-react'
     export default defineConfig({
       plugins: [react()],
       test: {
         globals: true,
         environment: 'jsdom',
         setupFiles: './src/test/setup.ts',
       },
     })

2.3  tsconfig.json
     {
       "compilerOptions": {
         "target": "ES2022",
         "useDefineForClassFields": true,
         "lib": ["ES2022", "DOM", "DOM.Iterable"],
         "module": "ESNext",
         "skipLibCheck": true,
         "moduleResolution": "bundler",
         "allowImportingTsExtensions": true,
         "resolveJsonModule": true,
         "isolatedModules": true,
         "noEmit": true,
         "jsx": "react-jsx",
         "strict": true,
         "noImplicitAny": true,
         "noUnusedLocals": true,
         "noUnusedParameters": true,
         "noFallthroughCasesInSwitch": true
       },
       "include": ["src"],
       "references": [{ "path": "./tsconfig.node.json" }]
     }

2.4  tsconfig.node.json
     {
       "compilerOptions": {
         "composite": true,
         "skipLibCheck": true,
         "module": "ESNext",
         "moduleResolution": "bundler",
         "allowSyntheticDefaultImports": true
       },
       "include": ["vite.config.ts"]
     }

2.5  index.html
     <!doctype html>
     <html lang="pt-BR">
       <head>
         <meta charset="UTF-8" />
         <meta name="viewport" content="width=device-width, initial-scale=1.0" />
         <title>{project_name}</title>
       </head>
       <body>
         <div id="root"></div>
         <script type="module" src="/src/main.tsx"></script>
       </body>
     </html>

2.6  .env.example
     # API
     VITE_API_BASE_URL=http://localhost:5000/api

     # Auth — Azure AD (se auth_provider = "azure-ad")
     VITE_AZURE_CLIENT_ID=
     VITE_AZURE_TENANT_ID=
     VITE_AZURE_REDIRECT_URI=http://localhost:5173

     # Auth — Auth0 (se auth_provider = "auth0")
     # VITE_AUTH0_DOMAIN=
     # VITE_AUTH0_CLIENT_ID=

     ← Incluir apenas as variáveis do provider configurado; comentar as demais.

2.7  .gitignore
     node_modules/
     dist/
     .env
     .env.*
     !.env.example
     *.log
     .DS_Store
     coverage/
```

---

### Step 3 — Gerar Camada Shared

```
3.1  src/main.tsx
     SE auth_provider = "azure-ad":
       import { MsalProvider } from '@azure/msal-react'
       import { msalInstance } from './auth/msal-config'
       <MsalProvider instance={msalInstance}><App /></MsalProvider>
     SE auth_provider = "auth0":
       import { Auth0Provider } from '@auth0/auth0-react'
       <Auth0Provider domain={...} clientId={...}><App /></Auth0Provider>

3.2  src/App.tsx
     import { RouterProvider } from 'react-router-dom'
     import { router } from './router'
     export default function App() { return <RouterProvider router={router} /> }

3.3  src/router/index.tsx
     createBrowserRouter([
       { path: '/', element: <AuthGuard />, children: [
         { path: '{bc_slug}', lazy: () => import('../{bc_name}/ui/pages/{BcName}ListPage') },
         ← repetir para cada BC com has_ui = true
       ]}
     ])

3.4  src/auth/msal-config.ts (se azure-ad) OU auth0-config.ts (se auth0)
     Apenas referências a import.meta.env.VITE_* — sem valores hardcoded.

3.5  src/auth/AuthGuard.tsx
     Componente que verifica autenticação e redireciona para login se necessário.
     Usa hook do provider (useMsal | useAuth0 | useKeycloak).
     Renderiza <Outlet /> se autenticado.

3.6  src/shared/components/
     Button.tsx, Input.tsx, Table.tsx, Modal.tsx
     ← Stubs tipados com React.FC<Props> — sem lógica de negócio.

3.7  src/shared/api/index.ts
     export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string
     export const apiClient = {
       get: (path: string) => fetch(`${API_BASE_URL}${path}`),
       post: (path: string, body: unknown) =>
         fetch(`${API_BASE_URL}${path}`, { method: 'POST', body: JSON.stringify(body) }),
     }

3.8  src/shared/hooks/useAuth.ts
     Hook de abstração sobre o provider de auth — expõe { user, isAuthenticated, login, logout }.

3.9  src/test/setup.ts
     import '@testing-library/jest-dom'
```

---

### Step 4 — Gerar Scaffolding por BC (has_ui = true)

Para cada BC com `scaffold_mode = "full"`:

```
src/{bc_name}/domain/types.ts
  export interface {BcName}Entity {
    id: string
    // Campos derivados do architecture-blueprint.md para este BC
  }

src/{bc_name}/application/
  SE cqrs = true:
    commands/Create{BcName}Command.ts
    commands/Update{BcName}Command.ts
    queries/Get{BcName}ListQuery.ts
    queries/Get{BcName}ByIdQuery.ts
    handlers/{BcName}CommandHandler.ts
    handlers/{BcName}QueryHandler.ts
  SE cqrs = false:
    services/{BcName}Service.ts
    hooks/use{BcName}List.ts     ← usa @tanstack/react-query (useQuery)
    hooks/use{BcName}Mutations.ts ← usa @tanstack/react-query (useMutation)
    dtos/{BcName}Dto.ts

src/{bc_name}/infrastructure/api/{BcName}Api.ts
  Funções async que chamam apiClient de src/shared/api/index.ts.
  Tipagem baseada em {BcName}Entity / Dto.

src/{bc_name}/ui/pages/{BcName}ListPage.tsx
  React.FC com useQuery (ou use{BcName}List hook).
  Renderiza componente de tabela com dados do BC.

src/{bc_name}/ui/pages/{BcName}DetailPage.tsx
  React.FC com param id via useParams().
  Renderiza formulário de detalhe/edição.

src/{bc_name}/ui/components/
  {BcName}Table.tsx   ← componente de tabela específico do BC
  {BcName}Form.tsx    ← formulário controlado com estado local

src/{bc_name}/tests/unit/{BcName}Page.test.tsx
  import { render, screen } from '@testing-library/react'
  import { describe, it, expect, vi } from 'vitest'
  ← Mock de hooks via vi.mock(); assertions básicas de render.

src/{bc_name}/tests/integration/
  ← Placeholder: arquivo .gitkeep com comentário de próximos passos.
```

---

### Step 5 — Gerar Scaffolding Mínimo por BC (has_ui = false)

Para cada BC com `scaffold_mode = "minimal"`:

```
src/{bc_name}/ui/index.tsx
  /**
   * BC: {bc_name}
   * Este bounded context não possui telas de UI (has_ui = false no blueprint).
   * Scaffold mínimo gerado por ava-build-cycle-react-scaffold v1.0.0.
   * Implemente aqui se o BC ganhar interfaces de usuário no futuro.
   */
  export const {BcName}Placeholder = () => null

← Logar: scaffold_mode: minimal para este BC.
```

---

### Step 6 — Gate de Segurança (npm audit)

```
6.1  Executar instalação de dependências:
     {package_manager} install --prefix {output_dir}

6.2  Executar auditoria de segurança:
     {package_manager} audit --audit-level=high --prefix {output_dir}

     SE exit code = 0:
       security_compliance = "PASS"

     SE exit code != 0:
       security_compliance = "FAIL"
       Coletar lista de vulnerabilidades (pacote, severity, CVE ID, versão afetada).
       ← implementation.status permanece COMPLETED — security é gate separado.

6.3  Logar resultado resumido:
     "npm audit: {PASS|FAIL} — {N} vulnerabilidades high/critical encontradas"
```

---

### Step 7 — Escrever Artefatos de Conclusão

```
7.1  scaffold-manifest.json
     {
       "agent":             "ava-build-cycle-react-scaffold",
       "version":           "1.0.0",
       "generated_at":      "{ISO-8601 timestamp}",
       "project_name":      "{project_name}",
       "frontend_version":  "{frontend_version}",
       "bundler":           "vite",
       "package_manager":   "{package_manager}",
       "auth_provider":     "{auth_provider}",
       "cqrs":              {cqrs},
       "bounded_contexts":  [
         { "name": "{bc_name}", "scaffold_mode": "full|minimal", "files_generated": N },
         ...
       ],
       "total_files_generated": N
     }

7.2  implementation-status.json
     {
       "agent":   "ava-build-cycle-react-scaffold",
       "version": "1.0.0",
       "implementation": {
         "status": "COMPLETED"
       },
       "build":                       "PENDING",
       "security_compliance":         "{PASS|FAIL|SKIPPED}",
       "bounded_contexts_scaffolded": [lista de BCs com scaffold_mode=full],
       "bounded_contexts_minimal":    [lista de BCs com scaffold_mode=minimal],
       "outputs_generated":           [lista de arquivos gerados],
       "trace_id":                    "{trace_id}"
     }

     ← Schema completo em contracts/implementation-status-contract.md.
     ← Campo "build" atualizado pelo ava-stack-build-validator (Step 8).
```

---

### Step 8 — Invocar Build Validator

```
8.1  Invocar @ava-stack-build-validator contra {output_dir} com target npm.
8.2  Aguardar resultado terminal: PASS | FAIL | TOOLCHAIN_UNAVAILABLE | SCAFFOLD_INCOMPLETE.
8.3  Atualizar campo "build" em implementation-status.json com o resultado retornado.

SE resultado = TOOLCHAIN_UNAVAILABLE:
  ← Emitir aviso; "build": "TOOLCHAIN_UNAVAILABLE" em implementation-status.json.
  ← NÃO bloquear entrega — build validation é gate de CI.
```

---

### Step 9 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

O campo `trace_id` é propagado inalterado do input para `implementation-status.json`
e `scaffold-manifest.json` — não gerar um novo trace_id; usar o valor lido do input.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-build-cycle-react-scaffold --phase F3 --version 1.0.0 \
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
