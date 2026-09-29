# Agent Specification: coder-react-frontend

**Feature Branch**: `PBI-2322`
**Created**: 2026-07-09
**Status**: Draft
**Change Type**: modify-existing
**Input**: PBI 2322 — Implementação completa do agente coder-react-frontend.md (atualmente STUB v0.1.0)

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-stack-react-frontend` |
| **Version** | `1.0.0` (MAJOR bump from `0.1.0-stub` — full contract implementation) |
| **Phase** | `F3` (Tech Stack) |
| **Module** | `tech-stack` |
| **Role** | Generates production-ready React 18 + Vite + TypeScript strict frontend code per bounded context, following the same pattern and quality bar as `coder-angular-frontend.md` |
| **Skill** | `ava-stack-react-frontend` (existing stub SKILL.md in `.github/skills/`) |
| **Dispatch** | user-facing via SKILL.md + routed by `ava-stack-orchestrator` when `frontend_framework == "react"` |

> **Change Type `modify-existing`**:
> - Target file: `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md`
> - Version bump type: **MAJOR** — contract changes from STUB (no outputs) to full implementation (new Output Contract with artifacts)
> - module.yaml entry already exists — Category 4 tasks may be N/A unless stub-registry.yaml requires update
> - SKILL.md already exists — Category 1.5 is N/A unless routing needs updating

---

## 2. Agent Frontmatter

```yaml
---
name: "ava-stack-react-frontend"
version: "1.0.0"
description: |
  Gera código React 18 + Vite + TypeScript strict production-ready por bounded context:
  Zustand/TanStack Query para state, MSAL para auth, padrões de Modal, FilterPanel,
  CRUD com cache invalidation, formulário de Update com pré-população via useQuery,
  service layer via openapi-typescript, guardrail de gráficos, Security Compliance Gate,
  e Test Scaffolder com Vitest + React Testing Library.
  Roteamento: tobe_stack.frontend_framework == "react".
  Ativa com: "gerar frontend React", "generate React frontend", "react codegen",
  "criar componente React", "scaffold React feature".
allowed-tools: Read, Write, Edit, Glob, Bash
---
```

> **Note**: `Bash` is required — task 2.10 invokes `npx openapi-typescript` to generate typed API contracts. The existing stub already lists `Bash`; retention is intentional.

---

## 3. Output Contract

```yaml
outputs:
  frontend_code:  "projects/{project_name}/outputs/tobe/source-code/frontend/"
  components:     "projects/{project_name}/outputs/tobe/source-code/frontend/src/features/"
mandatory_docs:
  - "projects/{project_name}/outputs/tobe/docs/delivery/ImplementationNotes.md"
  - "projects/{project_name}/outputs/tobe/docs/delivery/ChangedScreens.md"
  - "projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md"
```

**Path convention**: F3 codegen → `projects/{project_name}/outputs/tobe/source-code/`

**Feature structure per BC** (written to `src/features/{bc-name}/`):
```
src/
  features/
    {bc-name}/
      components/
        {ComponentName}.tsx
        {ComponentName}.spec.tsx
      hooks/
        use{Domain}Query.ts
        use{Domain}Mutation.ts
      stores/
        {domain}Store.ts          # Zustand (client state only)
      services/
        {domain}Api.ts            # generated from openapi-typescript
      types/
        index.ts
      pages/
        {DomainPage}.tsx
  shared/
    components/
    hooks/
    lib/
      queryClient.ts
      csrfToken.ts
  App.tsx
  main.tsx
  vite.config.ts
  tsconfig.json
  vitest.config.ts
  index.html
```

> Artifacts are created as new files (not appended). The output contract is
> structurally different from the STUB (which emitted no artifacts), justifying
> the MAJOR version bump.

---

## 4. User Scenarios (Given-When-Then)

### Scenario 1 — Nominal: Full BC scaffold with valid config (Priority: P1)

**Story**: Como o orquestrador de migração, quero que o `ava-stack-react-frontend` gere código
React 18 production-ready por bounded context para que a equipe possa entregar o frontend
modernizado sem erros de compilação nem vulnerabilidades de segurança.

**Why this priority**: Core value — replaces the STUB and enables 7 blocked PBIs from project Sophia.

**Acceptance Scenarios**:

1. **Given** `project-config.yaml` has `frontend_framework: "react"` and `pipeline_mode: "generic"`, **When** the agent executes for a BC named `financeiro`, **Then** it writes all Output Contract paths under `src/features/financeiro/` and `AgentResult.success` is true.
2. **Given** the above, **When** execution completes, **Then** `AgentResult.artifacts` lists every generated file and `AgentResult.next_agent` is `ava-stack-orchestrator`.
3. **Given** the above, **When** a Modal component is generated, **Then** it uses a boolean `isOpen` prop and typed `onClose: () => void` — no structural hallucination.
4. **Given** the above, **When** a FilterPanel is generated, **Then** applying filters calls a single state update that applies ALL active criteria simultaneously (not first-match).
5. **Given** the above, **When** a CRUD list component is generated with `useMutation`, **Then** `onSuccess` calls `queryClient.invalidateQueries([bc-key])` to prevent data duplication.
6. **Given** the above, **When** an Update form is generated, **Then** it calls `useQuery` on mount and pre-populates ALL schema fields before user interaction.
7. **Given** the above, **When** the service layer is generated, **Then** it uses `openapi-typescript` types derived from the BC's OpenAPI spec path in `project-config.yaml` — no manual type duplication.
8. **Given** the above, **When** a chart component is generated, **Then** the `dataKey` for X and Y axes is explicitly referenced from the API response schema field name — never inferred or hardcoded as a generic string.

---

### Scenario 2 — Routing Guard: wrong frontend_framework (Priority: P1)

**Story**: Como o orquestrador, quero que o agente bloqueie execução quando `frontend_framework` não é "react"
para evitar geração incorreta de código em projetos Angular ou Vue.

**Why this priority**: Prevents silent corruption of non-React projects.

**Acceptance Scenarios**:

1. **Given** `project-config.yaml` has `frontend_framework: "angular"`, **When** the agent is invoked, **Then** it prints a routing error box, sets `AgentResult.success: false`, and does NOT write any files.
2. **Given** `project-config.yaml` has `pipeline_mode: "build-cycle"`, **When** the agent is invoked, **Then** it redirects to `ava-build-cycle-react-scaffold` (or equivalent) and does NOT generate generic artifacts.

---

### Scenario 3 — Security Compliance Gate: PII in localStorage detected (Priority: P1)

**Story**: Como o time de segurança, quero que o agente bloqueie entrega quando detecta PII em localStorage
para garantir conformidade com LGPD/GDPR.

**Why this priority**: Legal compliance gate — must never be skipped.

**Acceptance Scenarios**:

1. **Given** generated code contains `localStorage.setItem` with a key or value matching PII patterns (name, email, CPF, token), **When** the Security Compliance Gate runs, **Then** `security_gate: BLOCKED` is emitted and `AgentResult.success: false`.
2. **Given** generated code configures CSP via `<meta http-equiv="Content-Security-Policy">` or Vite plugin, **When** the Security Compliance Gate runs, **Then** CSP check passes.
3. **Given** generated code uses `dangerouslySetInnerHTML`, **When** the Security Compliance Gate runs, **Then** a HIGH severity finding is raised and the gate blocks delivery unless DOMPurify sanitization is proven present.

---

### Scenario 4 — Edge Case: Missing OpenAPI spec for service layer (Priority: P2)

**Why this priority**: Defensive handling for projects without an OpenAPI spec yet.

**Acceptance Scenarios**:

1. **Given** no OpenAPI spec path is found for a BC in `project-config.yaml`, **When** the service layer step executes, **Then** the agent generates a typed placeholder service with `TODO:` markers and adds a WARNING to `ImplementationNotes.md` — it does NOT halt execution.
2. **Given** the above, **Then** `AgentResult.risk.level` is 'medium' and `AgentResult.risk.findings` lists the missing spec.

---

### Scenario 5 — Test Scaffolder: component spec generation (Priority: P2)

**Why this priority**: AC requires `.spec.tsx` for every generated component.

**Acceptance Scenarios**:

1. **Given** a component `ProductList.tsx` is generated, **When** the test scaffolder runs, **Then** a sibling `ProductList.spec.tsx` is written using Vitest + React Testing Library with at minimum: render smoke test, interaction test for primary action, and mocked service hook.
2. **Given** the above, **When** the file is generated, **Then** it imports from `@testing-library/react` and `vitest` — never from Jest globals.

---

## 5. Quality Gate Requirements

- [x] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) — `ava-stack-react-frontend` (Article II)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [x] Agent registered in module-level `module.yaml` — already registered as STUB; entry must be verified/updated (Article IV)
- [x] All output paths use lowercase `{project_name}` and correct phase folder (`tobe/source-code/`) (Article II)
- [x] BDD scenarios cover nominal, edge, and gate paths (Article VI)
- [x] Security sub-pipeline impact assessed: Security Compliance Gate is a mandatory step inside the agent (Article VII)
- [x] No technology versions hardcoded — React version read from `tobe_stack.frontend_version` (Article I)
- [x] Skill/Agent split declared: SKILL.md exists (stub); routing logic review may be needed if `ava-stack-orchestrator` checks stub status (Article XI)
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Stack orchestrator | `ava-stack-orchestrator` | Routes to this agent when `frontend_framework == "react"` |
| Architecture design | `ava-tobe-architecture-design` | Provides bounded-context-map.md with BC list |
| OpenAPI docs | `ava-docs-tobe` | Provides OpenAPI spec per BC for service layer generation |
| Security architecture | `ava-tobe-security-design` | Provides security-architecture.md used by Security Compliance Gate |
| stub-registry.yaml | `src/shared/data/stub-registry.yaml` | Must be updated from STUB → COMPLETE after implementation |

---

## 7. Exclusions

- **Build-cycle scaffold** — handled by `ava-build-cycle-react-scaffold` (separate stub); this agent covers `pipeline_mode: "generic"` only
- **Backend API generation** — handled by `ava-stack-dotnet-backend`, `ava-stack-python-backend`, or `ava-stack-java-backend`
- **CI/CD pipeline generation** — handled by `ava-devops-ci` and `ava-devops-cd`
- **Containerization** — handled by `ava-devops-containerize`
- **Next.js App Router** — out of scope for v1.0.0; Vite + React Router v6 is the canonical pattern

---

## 8. Assumptions

- `project-config.yaml` contains `tobe_stack.frontend_version` (React version, e.g., `"18"`) and `tobe_stack.frontend_framework: "react"`
- `tobe_stack.ui_library` is present in config (e.g., `"shadcn"`, `"mui"`, `"none"`) for UI component choices
- `auth.provider` is resolvable from `ConfigStackDotNet.yaml` or `project-config.yaml` (e.g., `"azure-ad"`, `"none"`)
- An OpenAPI spec may or may not exist per BC; the agent degrades gracefully when absent (Scenario 4)
- `coder-angular-frontend.md` behavior is the reference implementation — structural parity is expected for all common patterns
- The existing STUB SKILL.md in `.github/skills/ava-stack-react-frontend/SKILL.md` requires only minor updates (routing status text from STUB to active)
- `src/shared/data/stub-registry.yaml` has an entry `id: coder-react-frontend` with `status: STUB`; this must be updated to `COMPLETE`

---

## 9. Implementation Scope (Child Tasks from PBI 2322)

The following child PBIs map 1-to-1 to implementation areas. Each is a distinct deliverable:

| PBI | Area | Key Behavior |
|-----|------|-------------|
| 2323 | Routing Guard + base structure | Blocks if `frontend_framework != "react"` or `pipeline_mode == "build-cycle"`; generates `vite.config.ts`, `tsconfig.json` (strict), `main.tsx`, `App.tsx`, `index.html` |
| 2324 | Modal patterns | `isOpen: boolean` state, `onClose: () => void`, typed props interface — no inline state leakage |
| 2325 | FilterPanel simultaneous criteria | `useFilterStore` (Zustand) applies ALL active filters in a single `useMemo` pass |
| 2326 | CRUD complete | `useQuery` for GET; `useMutation` for POST/PUT/DELETE; `onSuccess: () => queryClient.invalidateQueries(...)` |
| 2327 | Update form pre-population | `useQuery({ queryKey: [bc, id], enabled: !!id })` drives `useEffect` → `form.reset(data)` on mount |
| 2328 | Service layer via openapi-typescript | `npx openapi-typescript {spec-url} -o src/features/{bc}/types/api.d.ts`; typed `createApiClient` wrapper |
| 2329 | Chart guardrail | Schema-driven axis: `dataKey` extracted from API response field names; degrades to `⚠️ TODO` comment + WARNING in ImplementationNotes.md if not resolvable — never invents generic field names |
| 2330 | Security Compliance Gate | CSP meta or Vite plugin; no PII in localStorage; `dangerouslySetInnerHTML` requires DOMPurify |
| 2331 | Test Scaffolder | `{ComponentName}.spec.tsx` generated alongside every component; Vitest + RTL; mocked hooks |
| 2332 | Registry update | `stub-registry.yaml` `coder-react-frontend` → `COMPLETE`; `ava-stack-orchestrator` routing text updated |

---

## Success Criteria

| Criterion | Measure |
|---|---|
| STUB removed | `coder-react-frontend.md` version is `1.0.0` with no STUB annotations |
| Routing Guard functional | Agent halts cleanly when `frontend_framework != "react"` or invalid `pipeline_mode` |
| Artifacts produced | All 3 mandatory docs + `src/features/{bc}/` structure written for each BC |
| Modal correctness | Generated Modal has boolean `isOpen` + typed `onClose` — no hallucinated structure |
| FilterPanel correctness | All active filter criteria applied simultaneously (verified by Scenario 1.4) |
| CRUD cache safety | `invalidateQueries` called in `onSuccess` after every mutation |
| Update form completeness | All schema fields pre-populated on mount via `useQuery` |
| Service layer traceability | Types derived from OpenAPI schema, not manually written |
| Chart axis safety | X/Y `dataKey` always explicitly from API schema — never guessed |
| Security gate passes | No PII in localStorage; CSP configured; XSS patterns absent |
| Test scaffolding | `.spec.tsx` generated for every component; Vitest + RTL imports |
| Registry updated | `stub-registry.yaml` shows `status: COMPLETE` for `coder-react-frontend` |
