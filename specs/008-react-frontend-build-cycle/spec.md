# Agent Specification: ava-stack-react-frontend (Build Cycle Mode)

**Feature Branch**: `008-react-frontend-build-cycle`
**Created**: 2026-07-13
**Status**: Draft
**Change Type**: modify-existing
**Input**: Agent description: "Implementar agente ava-stack-react-frontend para o modo build-cycle do F3 (tech-stack). O agente deve: Criar template em tech-stack/templates/react-frontend/, Ser roteado pelo orchestrator-stack.md quando frontend_framework == 'react' AND pipeline_mode == 'build-cycle', Retornar implementation.status: COMPLETED (não STUB), Atualizar stub-registry.yaml com status: COMPLETE, Produzir output compatível com os demais agentes build-cycle do mesmo stack (ex: ava-build-cycle-python-scaffold)"

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

This spec covers **two agent deliverables**:

### 1A — Main coder agent (modify-existing)

| Field             | Value                                                                             |
| ----------------- | --------------------------------------------------------------------------------- |
| **Agent ID**      | `ava-stack-react-frontend`                                                        |
| **Version**       | `1.0.0` (up from `0.1.0-stub` — MAJOR: stub → full implementation)                |
| **Phase**         | `F3`                                                                              |
| **Module**        | `tech-stack`                                                                      |
| **Role**          | Gera código React 18 + TypeScript por bounded context a partir do blueprint TO-BE |
| **Skill**         | `ava-stack-react-frontend` (SKILL.md must be created — currently missing)         |
| **Dispatch**      | user-facing via SKILL.md + dispatched by orchestrator                             |
| **Existing file** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`         |

### 1B — Build-cycle scaffold template (new agent)

| Field        | Value                                                                                                       |
| ------------ | ----------------------------------------------------------------------------------------------------------- |
| **Agent ID** | `ava-build-cycle-react-scaffold`                                                                            |
| **Version**  | `1.0.0`                                                                                                     |
| **Phase**    | `F3`                                                                                                        |
| **Module**   | `tech-stack`                                                                                                |
| **Role**     | Gera o scaffolding completo do projeto React 18 + Vite + TypeScript por bounded context em modo build-cycle |
| **Skill**    | _(no skill — internal)_ per Constitution Article XI                                                         |
| **Dispatch** | internal-only via `ava-stack-orchestrator`                                                                  |
| **New file** | `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-react-scaffold.md`                          |

> **Justification for internal-only** (Article XI): All build-cycle template agents
> (`build-cycle-python-scaffold`, `build-cycle-angular-agent`, `build-cycle-ngrx-agent`,
> `build-cycle-dotnet-scaffold-agent`, etc.) are internal-only, dispatched exclusively
> by `ava-stack-orchestrator`. React follows the same pattern.

---

## 2. Agent Frontmatter

### 2A — `coder-react-frontend.md` (modified)

```yaml
---
name: "ava-stack-react-frontend"
version: "1.0.0"
description: |
  Gera código React 18 + TypeScript 5+ production-ready por bounded context,
  com Vite ou Next.js App Router, Zustand ou TanStack Query para estado,
  React Router v6, autenticação MSAL (Azure AD) ou Auth0, e integração com
  cliente TypeScript gerado a partir do OpenAPI. Em modo build-cycle, delega
  ao agente ava-build-cycle-react-scaffold.
  Ativa com: "gerar frontend React", "generate React frontend", "react codegen",
  "criar projeto React", "React 18 por bounded context".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---
```

### 2B — `build-cycle-react-scaffold.md` (new)

```yaml
---
name: "ava-build-cycle-react-scaffold"
version: "1.0.0"
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
```

---

## 3. Output Contract

### 3A — `coder-react-frontend.md`

```yaml
outputs:
  react_project_scaffold: "projects/{project_name}/outputs/tobe/source-code/frontend/"
  scaffold_manifest: "projects/{project_name}/outputs/tobe/source-code/frontend/scaffold-manifest.json"
  implementation_status: "projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json"
```

When `pipeline_mode == "build-cycle"`, this agent emits a **redirect message** pointing to
`@ava-build-cycle-react-scaffold` and stops — consistent with the `coder-angular-frontend.md`
redirect pattern. No files are written by this agent in build-cycle mode; the user (or orchestrator)
re-invokes `@ava-build-cycle-react-scaffold` directly.

> **Remediation H1**: Clarified from ambiguous "delegates/passes through" to explicit redirect-only
> behavior. Delegation (sub-agent call) is NOT the pattern used — redirect-and-stop is.

### 3B — `build-cycle-react-scaffold.md`

```yaml
outputs:
  react_project_scaffold: "projects/{project_name}/outputs/tobe/source-code/frontend/"
  package_json: "projects/{project_name}/outputs/tobe/source-code/frontend/package.json"
  vite_config: "projects/{project_name}/outputs/tobe/source-code/frontend/vite.config.ts"
  tsconfig: "projects/{project_name}/outputs/tobe/source-code/frontend/tsconfig.json"
  app_entry: "projects/{project_name}/outputs/tobe/source-code/frontend/src/main.tsx"
  router_config: "projects/{project_name}/outputs/tobe/source-code/frontend/src/router/index.tsx"
  auth_config: "projects/{project_name}/outputs/tobe/source-code/frontend/src/auth/msal-config.ts"
  bc_modules: "projects/{project_name}/outputs/tobe/source-code/frontend/src/{bc_name}/"
  shared_components: "projects/{project_name}/outputs/tobe/source-code/frontend/src/shared/"
  env_example: "projects/{project_name}/outputs/tobe/source-code/frontend/.env.example"
  scaffold_manifest: "projects/{project_name}/outputs/tobe/source-code/frontend/scaffold-manifest.json"
  implementation_status: "projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json"
```

`implementation_status.json` contract (compatible with `build_summary_comprehensive.py`):

```json
{
  "agent": "ava-build-cycle-react-scaffold",
  "version": "1.0.0",
  "implementation": {
    "status": "COMPLETED"
  },
  "build": "PASS | FAIL | TOOLCHAIN_UNAVAILABLE",
  "security_compliance": "PASS | FAIL | SKIPPED",
  "bounded_contexts_scaffolded": ["bc1", "bc2"],
  "outputs_generated": ["package.json", "vite.config.ts", "..."],
  "trace_id": "{trace_id}"
}
```

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Nominal Path: Build-Cycle Scaffold Completo (Priority: P1)

**Story**: Como orquestrador da esteira TO-BE, quero que `ava-build-cycle-react-scaffold`
leia o blueprint de arquitetura e gere o scaffolding React 18 + Vite completo por bounded
context, para que o time possa compilar e executar o frontend sem intervenção manual.

**Why this priority**: Core deliverable — scaffold incompleto bloqueia todos os agentes downstream.

**Acceptance Scenarios**:

1. **Given** a valid `project-config.yaml` with `tobe_stack.frontend_framework == "react"` AND `pipeline_mode == "build-cycle"`, **When** `ava-stack-orchestrator` dispatches the agent, **Then** `ava-build-cycle-react-scaffold` is invoked (not `coder-react-frontend` stub response).
2. **Given** a valid `architecture-blueprint.md` with 3 bounded contexts, **When** the agent executes, **Then** `src/{bc_name}/` directories are created for all 3 BCs with `domain/`, `application/`, `infrastructure/`, `ui/`, `tests/` sub-layers.
3. **Given** execution completes successfully, **Then** `implementation-status.json` contains `"status": "COMPLETED"` and lists all generated files.
4. **Given** the generated scaffold, **When** `ava-stack-build-validator` runs, **Then** `npm run build` exits 0 and the build status is `PASS`.

---

### Scenario 2 — Edge Case: Readiness Gate Ausente (Priority: P2)

**Story**: Como engenheiro de confiabilidade, quero que o agente bloqueie execução quando
o readiness gate da Wave 1 não foi aprovado, para evitar gerar código sobre arquitetura
não validada.

**Why this priority**: Defensive handling — prevents wasted generation on invalid pre-conditions.

**Acceptance Scenarios**:

1. **Given** `readiness-gate-status.json` is absent or has `status != "APPROVED"`, **When** the agent executes, **Then** it emits `⛔ BLOCKED` with the missing artifact path and `implementation.status: BLOCKED`.
2. **Given** `architecture-blueprint.md` is absent, **When** the agent executes, **Then** it emits `⛔ BLOCKED: architecture-blueprint.md não encontrado` and halts without writing any files.

---

### Scenario 3 — Edge Case: Bounded Context Sem Rotas UI (Priority: P2)

**Story**: Como arquiteto, quero que o agente produza um módulo React mínimo mas válido
para bounded contexts que não possuem telas (ex: módulos de integração pura), para que
o build não quebre.

**Why this priority**: Prevents hard failures when some BCs have no UI components.

**Acceptance Scenarios**:

1. **Given** a BC with no UI screens in the blueprint, **When** the agent generates the module, **Then** it creates a placeholder `index.tsx` that exports an empty route with a comment, and `implementation_status.json` lists the BC as `scaffolded_minimal`.
2. **Given** the above, **Then** the overall `implementation.status` remains `COMPLETED` (not `PARTIAL`).

---

### Scenario 4 — Wrong Routing Guard: Non-Build-Cycle Mode (Priority: P1)

**Story**: Como orquestrador, quero que `ava-build-cycle-react-scaffold` se recuse a
executar quando `pipeline_mode != "build-cycle"`, para evitar invocação acidental.

**Why this priority**: Safety guard — prevents mixing pipeline modes.

**Acceptance Scenarios**:

1. **Given** `project-config.yaml` with `pipeline_mode == "generic"`, **When** `ava-build-cycle-react-scaffold` is invoked, **Then** it emits `⛔ ABORT: Este agente requer pipeline_mode = 'build-cycle'` and returns without generating files.
2. **Given** `frontend_framework != "react"`, **When** the agent is invoked, **Then** it emits `⛔ ABORT: Este agente requer frontend_framework = 'react'` and returns without generating files.

---

## 5. Technical Design

### Stack Resolvida em Runtime

All versions are read from `project-config.yaml → tobe_stack.*` — never hardcoded
(Constitution Article I).

| Config Key                      | Default (when absent) | Resolved From         |
| ------------------------------- | --------------------- | --------------------- |
| `tobe_stack.frontend_version`   | `"18"`                | `project-config.yaml` |
| `tobe_stack.frontend_framework` | n/a (required)        | `project-config.yaml` |
| `tobe_stack.ui_library`         | `"shadcn"`            | `project-config.yaml` |
| `tobe_stack.package_manager`    | `"npm"`               | `project-config.yaml` |
| `auth.provider`                 | `"azure-ad"`          | `project-config.yaml` |
| `architecture_patterns.cqrs`    | `false`               | `project-config.yaml` |

### Estrutura de Diretórios Gerada

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── .env.example
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── router/
│   │   └── index.tsx          # React Router v6 lazy-load por BC
│   ├── auth/
│   │   ├── msal-config.ts     # Azure AD / Auth0 via auth.provider
│   │   └── AuthGuard.tsx
│   ├── shared/
│   │   ├── components/        # UI primitives (Button, Table, Form, etc.)
│   │   ├── hooks/             # useApi, useAuth, useErrorBoundary
│   │   └── api/               # OpenAPI TS client (gerado ou importado)
│   └── {bc_name}/             # Um diretório por BC do blueprint
│       ├── domain/            # Types, interfaces, value objects
│       ├── application/       # Hooks de estado, queries, commands
│       ├── infrastructure/    # Serviços HTTP, adapters de API
│       ├── ui/                # Páginas e componentes do BC
│       │   ├── pages/
│       │   └── components/
│       └── tests/
│           ├── unit/
│           └── integration/
├── scaffold-manifest.json
└── implementation-status.json
```

### CQRS Configurável

Quando `architecture_patterns.cqrs == true`:

- `application/` contém `commands/`, `queries/`, `handlers/`
- Segue padrão CQRS com separação explícita de read/write

Quando `architecture_patterns.cqrs == false`:

- `application/` contém `services/`, `hooks/`, `dtos/`
- Serviços de aplicação simples sem separação command/query

### Autenticação — Seleção por `auth.provider`

| `auth.provider` | Biblioteca           | Config File          |
| --------------- | -------------------- | -------------------- |
| `azure-ad`      | `@azure/msal-react`  | `msal-config.ts`     |
| `auth0`         | `@auth0/auth0-react` | `auth0-config.ts`    |
| `keycloak`      | `keycloak-js`        | `keycloak-config.ts` |

### Gate de Segurança (npm audit)

Após geração, o agente executa:

```bash
npm install --prefix {output_dir}
npm audit --audit-level=high --prefix {output_dir}
```

Se vulnerabilidades de nível `high` ou `critical` forem encontradas:

- `security_compliance: "FAIL"` no `implementation-status.json`
- Lista de CVEs no output
- `implementation.status` permanece `COMPLETED` (security é gate separado)

---

## 6. Files to Create / Modify

| Action     | File                                                                               | Notes                                                                                                                                           |
| ---------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **MODIFY** | `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`          | Upgrade from `0.1.0-stub` to `1.0.0`. Replace stub response with full implementation + build-cycle delegation logic.                            |
| **CREATE** | `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-react-scaffold.md` | New agent `ava-build-cycle-react-scaffold`. Reference: `build-cycle-python-scaffold.md` + `build-cycle-angular-agent.md`.                       |
| **CREATE** | `.github/skills/ava-stack-react-frontend/SKILL.md`                                 | New SKILL.md — currently missing. Reference: `.github/skills/ava-stack-angular-frontend/SKILL.md`.                                              |
| **MODIFY** | `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md`            | Add `build-cycle-react-scaffold` to frontend routing table. Add routing condition: `react + build-cycle → ava-build-cycle-react-scaffold`.      |
| **MODIFY** | `src/shared/data/stub-registry.yaml`                                               | Update `coder-react-frontend` status to `COMPLETE`. Add new entry `build-cycle-react-scaffold` with status `COMPLETE`.                          |
| **MODIFY** | `src/modules/ava-fabric-agents/tech-stack/module.yaml`                             | Update `ava-stack-react-frontend` entry (remove `status: stub`). Add `ava-build-cycle-react-scaffold` entry (internal-only, no `skill:` field). |
| **MODIFY** | `CHANGELOG.md`                                                                     | Add entry for `ava-stack-react-frontend` v1.0.0 and `ava-build-cycle-react-scaffold` v1.0.0.                                                    |

---

## 7. Quality Gate Requirements

- [x] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) (Article II)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [x] `build-cycle-react-scaffold` registered in module-level `module.yaml` (Article IV)
- [x] All output paths use lowercase `{project_name}` and `outputs/tobe/source-code/` (Article II)
- [x] BDD scenarios cover nominal, edge (absent gate, empty BC), and routing-guard paths (Article VI)
- [x] No technology versions hardcoded — all from `project-config.yaml` (Article I)
- [x] Skill/Agent split declared: `ava-stack-react-frontend` has SKILL.md; `ava-build-cycle-react-scaffold` is internal-only (Article XI)
- [x] `implementation.status: COMPLETED` in output (not STUB)
- [x] `stub-registry.yaml` updated for both `coder-react-frontend` and new `build-cycle-react-scaffold`
- [x] Output structure compatible with `build_summary_comprehensive.py` (trace_id propagated)
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 8. Dependencies

| Dependency             | Agent ID                       | Reason                                       |
| ---------------------- | ------------------------------ | -------------------------------------------- |
| Architecture blueprint | `ava-tobe-architecture-design` | Provides bounded contexts list               |
| Security architecture  | `ava-tobe-security-design`     | Required by F2 gate before codegen           |
| Readiness gate         | `ava-requestor-inspection`     | Wave 1 readiness gate must be APPROVED       |
| Stack orchestrator     | `ava-stack-orchestrator`       | Dispatches this agent                        |
| Build validator        | `ava-stack-build-validator`    | Validates generated scaffold post-generation |

---

## 9. Exclusions

- **State management deep implementation** (`Zustand` stores, `TanStack Query` hooks) — these are out of scope for the scaffold. The scaffold creates placeholder files; deep state implementation is handled by `ava-build-cycle-react-state` (future stub, tracked in `stub-registry.yaml`).
- **E2E tests** — handled by `ava-qa-script-generator` in F5.
- **CI/CD pipeline** — handled by `ava-devops-ci` in F7.
- **Docker / containerization** — handled by `ava-devops-containerize` in F7.
- **Vue, Svelte, Blazor frontends** — separate agents per framework.

---

## 10. Assumptions

1. `tobe_stack.frontend_version` for React is the React major version (e.g., `"18"`), resolved to the latest `18.x` patch at generation time via the `docs-researcher` step.
2. Vite is the default bundler. Next.js App Router is used when `tobe_stack.rendering_mode == "ssr"` (config key reserved for future use; default is `"spa"` = Vite).
3. The OpenAPI TypeScript client (`shared/api/`) is either already generated by the backend agent or is a stub that will be replaced by the `ava-docs-tobe` OpenAPI generator.
4. `npm audit` is the default security gate tool. If `tobe_stack.package_manager == "pnpm"`, the command adapts to `pnpm audit`.

---

## 11. Success Criteria

- All bounded contexts from `architecture-blueprint.md` have corresponding `src/{bc_name}/` directories with the expected 5-layer structure.
- `implementation-status.json` contains `"status": "COMPLETED"` after successful generation.
- `npm run build` (Vite) exits with code 0 on the generated scaffold (validated by `ava-stack-build-validator`).
- `stub-registry.yaml` shows `status: COMPLETE` for both `coder-react-frontend` and `build-cycle-react-scaffold`.
- `orchestrator-stack.md` frontend routing table reflects `react` as ✅ Implemented.
- No hardcoded version strings appear in the generated agent `.md` files.
