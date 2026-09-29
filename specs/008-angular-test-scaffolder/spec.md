# Agent Specification: Angular Test Scaffolder for coder-angular-frontend

**Feature Branch**: `008-angular-test-scaffolder`
**Created**: 2026-07-09
**Status**: Draft
**Change Type**: modify-existing
**PBI**: 2283 — Test scaffolder automatico para componentes Angular (Services, Guards, Interceptors, Pipes)
**Input**: Adicionar Test Scaffolder ao agente coder-angular-frontend.md: gerar *.spec.ts para cada Service, Guard, Interceptor e Pipe gerado, com mocks padrão.

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-stack-angular-frontend` |
| **Current Version** | `1.0.0` |
| **New Version** | `1.1.0` |
| **Phase** | `F3` |
| **Module** | `tech-stack` |
| **Role** | Extends the Angular frontend code generator to automatically scaffold `*.spec.ts` test files for every Service, Guard, Interceptor, and Pipe it generates — eliminating manual test bootstrapping and enforcing 80% coverage threshold. |
| **Skill** | `ava-stack-angular-frontend` |
| **Dispatch** | user-facing via SKILL.md (already exists) |

> **Change Type is `modify-existing`**:
> - Target file: `src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md`
> - Version bump type: **MINOR** — adds new optional generation step (test scaffold) without breaking existing output contract
> - The module.yaml entry already exists — Category 4 tasks are N/A
> - The SKILL.md already exists — Category 1.5 is N/A

---

## 2. Agent Frontmatter (updated)

```yaml
---
name: "ava-stack-angular-frontend"
version: "1.1.0"
date: 2026-06-10
description: |
  Gera código Angular production-ready com boas práticas: standalone
  components, signals, lazy loading, MSAL para auth, NgRx para state.
  Inclui scaffolding automático de *.spec.ts para Services, Guards,
  Interceptors e Pipes com mocks padrão (provideHttpClientTesting, MsalService).
  Versão lida de `tobe_stack.frontend_version` em project-config.yaml.
  Ativa com: "gerar componente Angular", "criar tela", "Angular frontend",
  "NgRx store", "MSAL authentication", "test scaffolder Angular".
allowed-tools: Read, Write, Edit, Glob
---
```

Do NOT include `phase`, `module`, `inputs`, `outputs`, or `dependencies` in frontmatter.

---

## 3. Output Contract (additions)

The existing `## Output Contract` block in the agent body gains new entries:

```yaml
outputs:
  # [existing outputs preserved]
  # NEW entries added by this spec:
  service_spec:     "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/{bc}/services/{service-name}.service.spec.ts"
  guard_spec:       "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/{bc}/guards/{guard-name}.guard.spec.ts"
  interceptor_spec: "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/core/interceptors/{interceptor-name}.interceptor.spec.ts"
  pipe_spec:        "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/shared/pipes/{pipe-name}.pipe.spec.ts"
```

Path convention: F3 codegen → `projects/{project_name}/outputs/tobe/source-code/`

> **Append decision**: New `*.spec.ts` files are co-located alongside their source counterparts. No existing output path is modified; this is a pure addition. `build_summary_comprehensive.py` does not parse spec files directly, so no downstream parser impact.

---

## 4. Feature Description

### Context

The `coder-dotnet-backend.md` agent already scaffolds xUnit test files automatically per handler. The `coder-angular-frontend.md` agent enforces a minimum unit coverage requirement (>= 80%) but does not scaffold test files — leaving test creation as a manual developer responsibility.

### Objective

Add a **Test Scaffolder** section to `coder-angular-frontend.md` that generates a `*.spec.ts` companion file for every Angular artifact it produces:

| Artifact Type | Spec Template | Default Mock |
|---|---|---|
| **Service** | `{name}.service.spec.ts` | `provideHttpClientTesting()` |
| **Guard** | `{name}.guard.spec.ts` | `MsalService` + `AuthService` |
| **Interceptor** | `{name}.interceptor.spec.ts` | `provideHttpClient(withInterceptors([fn]))` + `provideHttpClientTesting()` |
| **Pipe** | `{name}.pipe.spec.ts` | Transformation test cases (value in → value out) |

Additionally, configure the coverage threshold in the generated `angular.json`:
- `"statements": 80, "branches": 80, "functions": 80, "lines": 80`

### Child PBIs

| PBI | Description |
|---|---|
| 2284 | Add Test Scaffolder section to `coder-angular-frontend.md` with templates per component type |
| 2285 | Implement default mock for `HttpClientTestingModule` and `MsalService` in templates |
| 2286 | Add coverage threshold (80%) configuration to generated `angular.json` |
| 2287 | Validate that generated tests pass in the Sophia project with zero errors |

---

## 5. User Scenarios (Given-When-Then)

> **Language convention**: Story descriptions (`**Story**:`) may be in Brazilian Portuguese.
> Acceptance scenarios (Given/When/Then) MUST be in English.

### Scenario 1 — Nominal Path: Service Scaffolding (Priority: P1)

**Story**: Como o orquestrador de migração, quero que o agente Angular Frontend gere automaticamente um arquivo `.spec.ts` para cada Service criado, com mock de HttpClient, para que a cobertura mínima seja alcançada sem esforço manual.

**Why this priority**: Directly eliminates manual work and enforces the 80% coverage gate.

**Acceptance Scenarios**:

1. **Given** an AgentTask requesting generation of `UserService` in a bounded context, **When** the agent executes, **Then** it writes `user.service.ts` AND `user.service.spec.ts` to the output path.
2. **Given** the generated `user.service.spec.ts`, **When** inspected, **Then** it uses `provideHttpClientTesting()` in `TestBed.configureTestingModule`, declares a `TestBed` setup, and contains at least one `it()` block per public method.
3. **Given** both files exist, **When** `ng test --no-watch --code-coverage` runs, **Then** exit code is 0 and coverage meets the 80% threshold.

---

### Scenario 2 — Nominal Path: Guard Scaffolding (Priority: P1)

**Story**: Como o orquestrador, quero que cada Guard gerado tenha um `.spec.ts` com mock de MsalService e AuthService.

**Acceptance Scenarios**:

1. **Given** an AgentTask requesting generation of `AuthGuard`, **When** the agent executes, **Then** it writes `auth.guard.ts` AND `auth.guard.spec.ts`.
2. **Given** the generated guard spec, **When** inspected, **Then** it contains a `MsalService` mock and an `AuthService` stub, and tests both `canActivate: true` and `canActivate: false` paths.

---

### Scenario 3 — Nominal Path: Interceptor Scaffolding (Priority: P2)

**Story**: Como o orquestrador, quero que cada Interceptor gerado tenha um `.spec.ts`.

**Acceptance Scenarios**:

1. **Given** an AgentTask requesting `AuthInterceptor`, **When** the agent executes, **Then** `auth.interceptor.spec.ts` is written with `provideHttpClient(withInterceptors([authInterceptor]))`, `provideHttpClientTesting()`, and an `HttpTestingController` with `afterEach(() => httpMock.verify())`.
2. **Given** the spec file, **When** `ng test` runs, **Then** exit code is 0.

---

### Scenario 4 — Nominal Path: Pipe Scaffolding (Priority: P2)

**Story**: Como o orquestrador, quero que cada Pipe gerado tenha um `.spec.ts` com casos de transformação.

**Acceptance Scenarios**:

1. **Given** an AgentTask requesting `CurrencyFormatPipe`, **When** the agent executes, **Then** `currency-format.pipe.spec.ts` is written with at least 3 transformation test cases (happy path, null input, invalid input).
2. **Given** the spec file, **When** `ng test` runs, **Then** exit code is 0.

---

### Scenario 5 — Coverage Threshold in angular.json (Priority: P1)

**Story**: Como engenheiro de qualidade, quero que o `angular.json` gerado configure o threshold de cobertura em 80%.

**Acceptance Scenarios**:

1. **Given** the agent generates `angular.json`, **When** inspected, **Then** it contains `"coverageThreshold": {"statements": 80, "branches": 80, "functions": 80, "lines": 80}` under the `test` builder configuration.
2. **Given** a project with < 80% coverage, **When** `ng test --code-coverage` runs, **Then** it exits with a non-zero code (threshold enforcement confirmed).

---

### Scenario 6 — Edge Case: Component Without Public Methods (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a Service with no public methods, **When** the agent scaffolds its spec, **Then** the spec contains a minimal `TestBed` setup and a single smoke test (`it('should be created', () => expect(service).toBeTruthy())`).
2. **Given** the above, **When** `ng test` runs, **Then** exit code is 0.

---

### Scenario 7 — Edge Case: pipeline_mode = "build-cycle" (Priority: P1)

**Acceptance Scenarios**:

1. **Given** `pipeline_mode = "build-cycle"` in `project-config.yaml`, **When** the agent is invoked, **Then** the existing routing guard redirects to `ava-build-cycle-angular` and no spec files are generated by this agent.

---

## 6. Quality Gate Requirements

- [ ] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) — `ava-stack-angular-frontend` ✅ (Article II)
- [ ] Frontmatter contains only `name`, `version`, `date` (pre-existing non-standard field retained for compatibility), `description`, `allowed-tools` (Article II)
- [ ] Version bumped to `1.1.0` (MINOR bump — new non-breaking behavior added) (Article X)
- [ ] All output paths use lowercase `{project_name}` and correct phase folder (`tobe/source-code/`) (Article II)
- [ ] BDD scenarios cover nominal (Services, Guards, Interceptors, Pipes), edge cases, and routing gate path (Article VI)
- [ ] No technology versions hardcoded — Angular/Karma version read from `tobe_stack.frontend_version` in `project-config.yaml` (Article I)
- [ ] Skill/Agent split: SKILL.md already exists, only agent `.md` is modified (Article XI)
- [ ] `CHANGELOG.md` updated with MINOR bump entry (Article X)
- [ ] Duplicate `version` key removed from existing frontmatter (current file has two `version:` entries — bug fix)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 7. Dependencies

| Dependency | Agent ID | Reason |
|---|---|---|
| Stack orchestrator | `ava-stack-orchestrator` | Routes to this agent; no contract change required |
| Build validator | `ava-stack-build-validator` | Runs `ng test --no-watch --code-coverage` post-generation to validate spec files compile and pass |
| Sophia validation | _(manual gate — PBI 2287)_ | Human validates generated tests in the Sophia project before merging |

---

## 8. Assumptions

- The generated spec files use **Karma + Jasmine** (Angular default test runner) unless `tobe_stack.test_runner` specifies otherwise (e.g., Jest).
- `MsalService` is already imported as a dependency in the project via `@azure/msal-angular` — the spec only needs to provide a mock, not install the package.
- The `angular.json` coverage threshold format uses `coverageThreshold` under `projects.<name>.architect.test.options`.
- This change does NOT affect the `build-cycle` pipeline path — those agents (`ava-build-cycle-angular`) remain unchanged.
- Existing generated files in `outputs/` are not retroactively modified; scaffolding applies only to new agent invocations.
