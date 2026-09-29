# F4 Tech-Stack (Codegen) — Agent Input/Output Map

> **Driven by**: `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` (v1.7.1
> at the time this map was written — now v1.8.0, see update note below)
> **Purpose**: canonical reference for every agent this orchestrator dispatches, what each one
> reads (inputs) and writes (outputs), and how their artifacts chain together.
> All paths are relative to `projects/{project_name}/outputs/` unless stated otherwise.
> Project config is always at `projects/{project_name}/context/project-config.yaml`.
>
> **⚠️ Update 2026-07-15**: most gaps and discrepancies documented below (§4, and the Output
> Contract paths described throughout §2) were the diagnostic basis for
> `specs/019-codegen-dynamic-naming-path-fix`, `specs/020-codegen-business-rules-architecture-config`,
> and `specs/021-frontend-backend-api-contract-integration`, all now implemented. In particular:
> Discrepancy 4.1 (`module.yaml` stub labels) is fixed; backend Output Contracts now root under
> `source-code/backend/` (this map's own §1 table already flagged the `.../backend/` vs.
> `.../{module}/` mismatch — that mismatch is resolved); Angular's dead `ConfigStackDotNet.yaml`
> read (§2, coder-angular-frontend.md notes) is replaced with direct `project-config.yaml` reads;
> business-rules consumption and real OpenAPI contract consumption (both previously absent, per
> §2's notes) are now wired in. Discrepancy 4.5 (dual codegen invocation path,
> `orchestrator-tobe.md` vs. this orchestrator) remains open — explicitly excluded from all three
> specs as a team architecture decision, not a mechanical fix.

---

## 1. Overview — Agents Dispatched

`orchestrator-stack.md` does **not** run a fixed agent roster — it resolves a **backend
coder** and a **frontend coder** at runtime from `tobe_stack.backend_framework` /
`tobe_stack.frontend_framework` (Step 0.3b), then runs a fixed sequence of cross-cutting
"reliability pipeline" agents around whichever coder pair got resolved. In `pipeline_mode:
"build-cycle"` mode (an alternate, finer-grained path — see §2b) the single coder-per-layer
step is replaced by a chain of narrower scaffold/layer agents instead.

**Generic mode — execution order for one run (e.g. `dotnet` + `angular`):**

| Step | Agent ID (dispatch name) | Implementing file | Routing condition |
|---|---|---|---|
| 0 | *(orchestrator itself — pre-flight)* | `agents/orchestrator-stack.md` | always |
| 1.5 | `ava-stack-docs-researcher` | `agents/docs-researcher-agent.md` | always (cache-skippable, TTL 24h) |
| 3 | `{resolved_backend_agent}` (backend routing table below) | `agents/coder-{dotnet\|java\|python\|go\|node}-backend.md` | `tobe_stack.backend_framework` |
| 4 | *(no separate agent — OpenAPI contract emitted as part of backend coder's own output)* | — | — |
| 5 | `{resolved_frontend_agent}` (frontend routing table below) | `agents/coder-{angular\|react\|blazor\|vue}-frontend.md` | `tobe_stack.frontend_framework` |
| 5.5 | *(deterministic script, not an agent)* `verify_scaffold.py --manifest {dotnet\|angular}` | `src/shared/utils/verify_scaffold.py` | always, x2 (backend + frontend) |
| 6 | *(orchestrator itself — contract consistency check)* | `agents/orchestrator-stack.md` | always |
| 6a | `ava-stack-build-validator` (target: backend) | `agents/build-validator-agent.md` | always — MANDATORY, zero-skip invariant |
| ↳ internal | `ava-stack-build-fixer` (sub-agent, invoked by build-validator on FAIL, up to 5 cycles) | `agents/build-fixer-agent.md` | conditional on build errors |
| 6b | *(orchestrator itself — security compliance consolidation)* | `agents/orchestrator-stack.md` | always |
| 7 | `AG-07` (test generation trigger) | *outside this module — not documented here* | always, informational trigger only |
| 8 | `ava-stack-build-validator` (target: frontend) | `agents/build-validator-agent.md` | always — MANDATORY, zero-skip invariant |
| ↳ internal | `ava-stack-build-fixer` (sub-agent, invoked by build-validator on FAIL, up to 5 cycles) | `agents/build-fixer-agent.md` | conditional on build errors |
| 9-10 | *(orchestrator itself — NTP timing + observability output)* | `agents/orchestrator-stack.md` | always |

### Backend routing table (Step 0.3b `BACKEND_AGENTS`)

| `tobe_stack.backend_framework` | Agent ID | File | Orchestrator label | Actual file content |
|---|---|---|---|---|
| `dotnet` | `ava-stack-dotnet-backend` | `agents/coder-dotnet-backend.md` | ✅ Implemented | ✅ Fully implemented (v1.0.0, 9 guardrails, full gates) |
| `spring-boot` | `ava-stack-java-backend` | `agents/coder-java-backend.md` | ✅ Implemented | ✅ Fully implemented (v1.1.0, 9 guardrails, full gates) |
| `fastapi` | `ava-stack-python-backend` | `agents/coder-python-backend.md` | ✅ Implemented | ✅ Fully implemented (v1.1.0, full gates) |
| `gin` | `ava-stack-go-backend` | `agents/coder-go-backend.md` | ✅ Implemented | ✅ Fully implemented (v1.0.0, full gates) |
| `nestjs` | `ava-stack-node-backend` | `agents/coder-node-backend.md` | 🚧 STUB | 🚧 Genuine stub (v0.1.0-stub, 102 lines, `outputs_generated: []`) |

> ⚠️ `src/modules/ava-fabric-agents/tech-stack/module.yaml` marks `spring-boot`, `fastapi`,
> and `gin` as `status: stub` — contradicting both the orchestrator's own routing table
> (`✅ Implemented`) and each file's actual content (fully fleshed out). See §4 Discrepancy 1.

### Frontend routing table (Step 0.3b `FRONTEND_AGENTS`)

| `tobe_stack.frontend_framework` | Agent ID | File | Orchestrator label | Actual file content |
|---|---|---|---|---|
| `angular` | `ava-stack-angular-frontend` | `agents/coder-angular-frontend.md` | ✅ Implemented | ✅ Fully implemented (v1.0.0, 3135 lines, 10-step pipeline) |
| `react` | `ava-stack-react-frontend` | `agents/coder-react-frontend.md` | 🚧 STUB | 🚧 Genuine stub (v0.1.0-stub, `outputs_generated: []`) |
| `blazor` | `ava-stack-blazor-frontend` | `agents/coder-blazor-frontend.md` | 🚧 STUB | 🚧 Genuine stub (v0.1.0-stub, `outputs_generated: []`) |
| `vue` | `ava-stack-vue-frontend` | `agents/coder-vue-frontend.md` | 🚧 STUB | 🚧 Genuine stub (v0.1.0-stub, `outputs_generated: []`) |
| `svelte` | `ava-stack-svelte-frontend` | `agents/coder-svelte-frontend.md` | 🚧 STUB | ❌ **File does not exist** — see §4 Discrepancy 2 |

### Cross-cutting agents (reliability pipeline)

| Agent | File | Position | Status |
|---|---|---|---|
| `ava-stack-docs-researcher` | `agents/docs-researcher-agent.md` | Step 1.5 (pre-codegen) | ✅ Implemented (v1.0.0), cache TTL 24h |
| `ava-stack-build-validator` | `agents/build-validator-agent.md` | Step 6a (backend) / Step 8 (frontend) | ✅ Implemented (v2.3.0) |
| `ava-stack-build-fixer` | `agents/build-fixer-agent.md` | Internal to build-validator only | ✅ Implemented (v1.1.0), never dispatched directly by the orchestrator |

> `module.yaml` (tech-stack module registry) does not list `ava-stack-docs-researcher`,
> `ava-stack-build-validator`, or `ava-stack-build-fixer` at all — only the 9 coder agents
> are registered. See §4 Discrepancy 1.

---

## 2. Per-Agent Input/Output Detail

### `ava-stack-orchestrator` — `agents/orchestrator-stack.md`
- **Inputs (dispatch/user-provided)**: trigger code (`SG` full stack / `BG` backend only / `FG` frontend only / `CV` contract validation / `SR` status report)
- **Files read**: `context/project-config.yaml` (`project_name`, `pipeline_mode`, `overrides`, `tobe_stack.*`, `cloud_provider`, `architecture_patterns.cqrs`, `auth.*`, `persistence.*`, `quality_gates.*`, `infrastructure.*`, `timing_benchmark_enabled`, `build_runner.mode`)
- **Hard-blocking prerequisite gate (Step 0.5 — STOP entirely if any ❌, no output generated)**:
  - `outputs/tobe/docs/architecture-blueprint.md` (must contain bounded context list) — produced by `ava-tobe-architecture-design`
  - IF `cqrs == true`: `outputs/tobe/docs/spec/{BC}-spec.md` — produced by `ava-tobe-user-journeys`
  - `outputs/tobe/docs/security-architecture.md` — produced by `security-design-tobe`
  - `outputs/readiness-gate/wave-1/readiness-gate-status.json` with `status == "APPROVED"`
- **Outputs**: `outputs/tobe/docs/security/SecurityComplianceReport-Consolidated.md` (Step 6b, own generation), plus in-band `execution_timing{...}`, `build_validation{status, backend_report, frontend_report}`, `security_compliance{overall_status,...}`

### `ava-stack-docs-researcher` — `agents/docs-researcher-agent.md` (v1.0.0)
- **Dispatch params**: `project_name`, `backend_framework`, `backend_version`, `frontend_framework`, `frontend_version`, `packages_list`
- **Inputs**:
  - Hard-blocking: `context/project-config.yaml` (`BLOCKED` status if missing)
  - Optional: `outputs/tobe/source-code/Directory.Packages.props` (if present)
  - **Cache gate (TTL 24h)**: before running research, checks `outputs/tobe/docs/research/docs-research-bundle.md`'s `generated_at` header field — "SE age < 24h → EMIT '[DOCS RESEARCH] Cache hit' → SKIP pesquisa completa → Retornar status: 'COMPLETED' com cache_hit: true"
- **Outputs**: `outputs/tobe/docs/research/docs-research-bundle.md`, `outputs/tobe/docs/research/resolved-packages.json`
- **Consumption downstream**: both the backend and frontend coder agents receive `additional_context: ".../docs-research-bundle.md"` at dispatch (Steps 3 and 5) and are instructed they "DEVE ler este bundle antes de iniciar geração de código" — though see per-agent notes below, since some coders treat it as non-blocking.

### `ava-stack-dotnet-backend` — `agents/coder-dotnet-backend.md` (v1.0.0)
- **Dispatch params**: `project_name`; version read from `tobe_stack.backend_version`; `additional_context` (docs-research-bundle path, optional)
- **Inputs**:
  - Hard-blocking: `context/project-config.yaml` (routing/`pipeline_mode` guard — hard-stops if `pipeline_mode == "build-cycle"`, redirecting to the build-cycle chain); `outputs/tobe/docs/security-architecture.md` (required before the Security Compliance Gate)
  - Optional/non-blocking: `outputs/tobe/docs/research/docs-research-bundle.md` — explicitly: "SE bundle NÃO EXISTIR: → PROSSEGUIR com guardrails G1-G9 existentes (non-blocking) ... Sua ausência NÃO bloqueia a geração de código"
  - Scoped per-entity read (Guardrail G2): `src/{BCName}/{prefix}.{BCName}.Domain/Entities/{EntityName}.cs` — one entity file at a time
- **Outputs**: `outputs/tobe/source-code/{module}/`, `outputs/tobe/source-code/{module}.Tests/`, `outputs/tobe/source-code/Migrations/`, `outputs/tobe/docs/security/SecurityComplianceReport-Backend.md`
- **Full-source-read status**: ✅ scoped — no evidence of whole-tree reads (see §3)

### `ava-stack-java-backend` — `agents/coder-java-backend.md` (v1.1.0)
- **Dispatch params**: `project_name`; `tobe_stack.backend_version`; `tobe_stack.backend_framework` (must be `"spring-boot"`); `auth.provider`; `persistence.connection_source`
- **Inputs**:
  - Hard-blocking ("Dependency Validation Gate — OBRIGATÓRIO — executa ANTES de qualquer geração"): `outputs/tobe/docs/architecture-blueprint.md`, `outputs/tobe/docs/security-architecture.md`, `outputs/readiness-gate/wave-1/readiness-gate-status.json` (`status == "APPROVED"`) — each individually causes `⛔ BLOCKED` if missing
  - Routing guard: `context/project-config.yaml` — stops hard if `pipeline_mode == "build-cycle"` (unlike dotnet/python/go, which fall back or redirect more gracefully)
  - Scoped per-entity read (Guardrail G2): `src/{BCName}/domain/entity/{EntityName}.java`
  - External (non-repo): Maven Central Search API, for dependency version resolution
- **Outputs**: `outputs/tobe/source-code/{module}/`, `outputs/tobe/source-code/{module}-tests/`, `outputs/tobe/source-code/db/migration/`, `outputs/tobe/docs/security/SecurityComplianceReport-Backend.md`
- **Full-source-read status**: ✅ scoped — same per-entity pattern as dotnet (see §3)

### `ava-stack-python-backend` — `agents/coder-python-backend.md` (v1.1.0)
- **Dispatch params**: `project_name`; `tobe_stack.backend_version`; `tobe_stack.backend_framework` (must be `"fastapi"`); `auth.provider`; `persistence.connection_source`/`persistence.read_model`; `architecture_patterns.cqrs`; `observability.*`
- **Inputs**:
  - Hard-blocking ("Gate de Pré-condições F2 — OBRIGATÓRIO — executa ANTES de qualquer geração"): `outputs/tobe/docs/architecture-blueprint.md`, `outputs/tobe/docs/security-architecture.md`, `outputs/readiness-gate/wave-1/readiness-gate-status.json` (`status == "APPROVED"`)
  - Routing guard: `context/project-config.yaml` — non-blocking fallback to generic mode with a warning if `pipeline_mode == "build-cycle"` (softer than Java's hard stop)
  - No per-entity domain-file read pattern documented (unlike dotnet/java/go) — its G1-G9 guardrails are generic code-pattern rules, not file-verification steps
- **Outputs**: `outputs/tobe/source-code/{module}/`, `outputs/tobe/source-code/{module}/tests/`, `outputs/tobe/source-code/{module}/migrations/`, `outputs/tobe/docs/security/SecurityComplianceReport-Backend.md`
- **Full-source-read status**: ✅ scoped — Security Compliance Gate inspects only `outputs/tobe/source-code/{module}/` per-module, no evidence of any whole-tree/whole-repo read instruction

### `ava-stack-go-backend` — `agents/coder-go-backend.md` (v1.0.0)
- **Dispatch params**: `project_name`; `tobe_stack.backend_version`; `tobe_stack.backend_framework` (must be `"gin"`); `auth.provider`; `persistence.connection_source`/`persistence.read_model`; `architecture_patterns.cqrs`; `observability.*`
- **Inputs**:
  - Hard-blocking ("Gate de Pré-condições F2"): identical three-file gate to Python — `architecture-blueprint.md`, `security-architecture.md`, `readiness-gate-status.json == APPROVED`
  - Routing guard: `context/project-config.yaml` — non-blocking fallback to generic mode with a warning if build-cycle
  - Scoped per-BC read (Guardrail G2): `outputs/tobe/source-code/{bc}/domain/entity.go` — notable because, unlike dotnet/java (which read from an AS-IS-style legacy `src/{BCName}/...` path convention), Go reads its own **already-generated** ToBe output for the same BC — self-referential within the current BC only
  - External (non-repo): pkg.go.dev Proxy API, for dependency version resolution
- **Outputs**: `outputs/tobe/source-code/{bc}/`, `outputs/tobe/source-code/{bc}/*_test.go`, `outputs/tobe/source-code/migrations/`, `outputs/tobe/docs/security/SecurityComplianceReport-Backend.md`
- **Full-source-read status**: ✅ scoped — per-BC single-file read, security gate scoped to `outputs/tobe/source-code/{bc}/` only

### `ava-stack-node-backend` — `agents/coder-node-backend.md` (v0.1.0-stub) 🚧 STUB
- **Dispatch params**: `project_name` only (used for the observability tracker call)
- **Inputs**: none — no architecture-blueprint.md, no security-architecture.md, no readiness-gate check, no docs-research-bundle read. Only checks `pipeline_mode` for a build-cycle fallback routing rule.
- **Outputs**: none — `outputs_generated: []` is hardcoded; `build: SKIPPED`, `security_compliance: SKIPPED`, `implementation.status: STUB`
- **Full-source-read status**: N/A — no generation loop exists at all

### `ava-stack-angular-frontend` — `agents/coder-angular-frontend.md` (v1.0.0, 3135 lines)
- **Dispatch params (Input Contract)**: CRITICAL/hard-stop: `project_name`, `pipeline_mode` (must be `"generic"`, else hard-stops and redirects to `@ava-build-cycle-angular`), `frontend_version`, `auth_provider` (must be `"azure-ad"`), `bounded_contexts[]`, `trace_id`. Softer (degrade to defaults): `language`, `client_name`, `tech_lead_name`.
- **Inputs**:
  - Hard-blocking: `projects/_template/context/project-config.yaml` (resolve `project_name`); `context/project-config.yaml` (`pipeline_mode` gate); `imfai-ava-fabric-apps-agents/docs/architecture/ConfigStackDotNet.yaml` (hard-blocking on `auth_provider != "azure-ad"`, also sources `frontend_version`)
  - Optional/warning-only: `context/shared-context.md` (AS-IS completion status — warns if PENDING, does not block); `outputs/asis/bounded-context-map.md` (falls back to task-derived BC list); `src/shared/data/patterns/angular/angular-patterns-reference.md` (falls back to inline patterns)
  - Later, for the Security Compliance Gate: `outputs/tobe/docs/security-architecture.md`, then inspects its own freshly-generated `outputs/tobe/source-code/frontend/`
  - **Notably absent**: no read of any OpenAPI/API-contract spec, and no read of `docs-research-bundle.md` despite the orchestrator's Step 5 instruction to pass it — generated TS models use placeholder `[key: string]: unknown` typing (flagged as a TODO in the agent's own `ImplementationNotes.md` output), confirming no real dependency on the backend's Step 4 API contract
- **Outputs**: `outputs/tobe/source-code/frontend/` (full Angular app — `package.json`, `angular.json`, MSAL auth, core/shared modules, NgRx stores per BC, feature modules, routing/sidenav), `outputs/tobe/docs/delivery/ImplementationNotes.md`, `outputs/tobe/docs/delivery/ChangedScreens.md`, `outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md`
- **Full-source-read status**: ✅ scoped — only self-reviews its own freshly generated `outputs/tobe/source-code/frontend/` for the Security Compliance Gate; scaffold completeness is checked via the deterministic `verify_scaffold.py --manifest angular` script, not an LLM tree read

### `ava-stack-react-frontend` / `ava-stack-blazor-frontend` / `ava-stack-vue-frontend` — 🚧 STUB
- **Files**: `agents/coder-react-frontend.md`, `agents/coder-blazor-frontend.md`, `agents/coder-vue-frontend.md` (all v0.1.0-stub, ~100-103 lines, structurally identical templates)
- **Dispatch params**: none formally documented
- **Inputs**: none — no Input Contract, no Execution Steps
- **Outputs**: none — `outputs_generated: []`, `build: SKIPPED`, `security_compliance: SKIPPED` hardcoded in each Handoff block
- **Full-source-read status**: N/A — no generation logic exists

### `ava-stack-build-validator` — `agents/build-validator-agent.md` (v2.3.0)
- **Dispatch params**: `project_name`, `source_code_path` ("outputs/tobe/source-code/"), `target` (`"backend"`|`"frontend"`), `stack`, `backend_version`/`frontend_version`, `solution_file`, `node_version`, nested `build_runner: {mode, container_runtime, cache_volumes, platform}`
- **Hard-blocking gates**:
  - **Step B0/F0/VF0 — Container Runtime Pre-Gate**: detects docker/podman via `build_runner.py --detect-runtime`, checks daemon health — terminal outcome `TOOLCHAIN_UNAVAILABLE` if no runtime/daemon (container mode) or SDK/Node too old (local mode)
  - **Step B0.5/F0.5 — Source File Pre-Gate**: invokes `verify_scaffold.py --manifest {dotnet|angular} --root {path}` purely to check *file existence* before attempting `dotnet restore`/`npm ci` — "Evita 5 ciclos de retry com erros triviais de arquivo ausente." `FAIL` → immediate `SCAFFOLD_INCOMPLETE` abort, no `dotnet restore`/`npm ci` attempted. This is complementary to, not a duplicate of, the orchestrator's own Step 5.5 `verify_scaffold.py` call — same script, invoked independently by both the orchestrator (post-codegen gate) and build-validator (pre-build gate).
- **Inputs — full generated-tree scan (legitimate for build/lint/CVE)**: builds per-layer then whole-solution (`dotnet build {solution_file} --no-incremental`), lints whole tree (`dotnet format --verify-no-changes`), CVE-scans whole solution (`dotnet list package --vulnerable --include-transitive`), greps whole backend folder for `HintPath`. Frontend equivalents: `npm run build`, `npx eslint .`, `npm audit --json` — all whole-project scans.
  - **No incremental/dedup logic against prior invocations** — every build step explicitly forces `--no-incremental`; each invocation re-runs the entire B1→B7/F1→F5 pipeline from scratch. The only caching is dependency-download caching via named volumes (`cache_volumes: true`), not build-result caching.
- **Outputs**: `outputs/tobe/docs/build/{backend|frontend}-build-report.md`, plus a `build_gate_result` payload (`PASS|FAIL|BLOCKED|TOOLCHAIN_UNAVAILABLE|SCAFFOLD_INCOMPLETE`) returned to the orchestrator
- **Internal sub-dispatch**: on build/lint errors, classifies them and `DISPATCH ava-stack-build-fixer: INPUT: {project_name, source_code_path, target, stack, errors, iteration}`, looping up to 5 fixer cycles; 3 repeats of the same error → `UNRESOLVABLE`; exhausting 5 cycles → hard stop, `status: FAIL`

### `ava-stack-build-fixer` — `agents/build-fixer-agent.md` (v1.1.0, sub-agent of build-validator only)
- **Dispatch params (from build-validator, not the orchestrator)**: `project_name`, `source_code_path`, `target`, `stack`, `iteration` (1-5), `errors: [{code, message, file, line, column}]`
- **Inputs — scoped to the error list only**: "PARA CADA erro com solução identificada: READ {file} → entender contexto ao redor da linha com erro → APLICAR correção via Edit tool" — reads only the specific `{file}` named in each error entry, one at a time; does not glob/enumerate the source tree. Guardrail #4: "**NÃO modifica** arquivos fora do `source_code_path` do projeto." One conditional extra: if a fix touches `package.json`, runs `npm install` to resync `package-lock.json` — a targeted lockfile action, not a codebase-wide read. External doc lookups (`fetch_webpage`, `github_text_search`) are only for canonical-fix reference, never additional source files.
- **Outputs**: no named files in its own Output Contract — returns a `fix_result` payload (`status: FIXED|PARTIAL|FAILED`, `errors_fixed`, `errors_remaining[]`, `files_modified[]`, `lockfile_updated`) to build-validator; filesystem writes are direct `Edit` calls on the specific error-source files (+ `package-lock.json` when triggered)
- **Full-source-read status**: ✅ scoped to error list — see §3 for verbatim evidence

---

## 2b. Build-Cycle Mode (`pipeline_mode == "build-cycle"`) — Alternate Dispatch Path

When `project-config.yaml` sets `pipeline_mode: "build-cycle"`, Step 0.4 of the orchestrator
resolves a **chain** of narrower agents per backend/frontend framework instead of a single
coder agent per layer. Each agent in a chain Globs its predecessor's *generated filesystem
output* (not the full repo, not docs) to discover what to build against — several hard-block
or degrade-with-TODOs if the predecessor didn't run yet. Templates live under
`src/modules/ava-fabric-agents/tech-stack/templates/`.

### `.NET` chain — `dotnet-scaffold → efcore → (cqrs, if cqrs==true) → minimal-apis`

| Agent | File | Role | Depends on |
|---|---|---|---|
| `ava-build-cycle-dotnet-scaffold` (v1.0.0) | `templates/build-cycle-dotnet-scaffold-agent.md` | `.sln`, per-BC `.csproj` skeleton (Domain/Application/Infrastructure/Api/Tests), `Directory.Packages.props`, docker-compose — no business logic, empty Commands/Queries folders | `architecture-blueprint.md` + `project-config.yaml` only — first in chain |
| `ava-build-cycle-efcore` (v1.0.0) | `templates/build-cycle-efcore-agent.md` | `DbContext`, `IEntityTypeConfiguration<T>` per entity, `Repository<T>`/`IUnitOfWork`, migration instructions | Globs `outputs/tobe/source-code/{prefix}/src/*/` and `.../Domain/Entities/*.cs` from dotnet-scaffold's output; blocked with "Execute @ava-build-cycle-dotnet-scaffold primeiro" if absent. Reads one entity file at a time — "Map ONLY properties that EXIST in the entity" |
| `ava-build-cycle-cqrs` (v1.0.0) | `templates/build-cycle-cqrs-agent.md` | MediatR Commands/Queries/Handlers/Validators + Pipeline Behaviors; no-op redirect to `@ava-stack-dotnet-backend` if `cqrs: false` | Reads `spec.md` (falls back to CRUD-per-entity from `Domain/Entities/*.cs` if absent). Degrades gracefully (not hard-block) if efcore hasn't run: "WARN: handler gerado com dependência pendente" |
| `ava-build-cycle-minimal-apis` (v1.0.0) | `templates/build-cycle-minimal-apis-agent.md` | Carter `ICarterModule` endpoint mapping, `Program.cs`, `GlobalExceptionHandler`, `appsettings.json` — last backend agent in chain | Globs `Application/Commands/**/*Command.cs` and `Queries/**/*Query.cs`. Degrades gracefully (stub modules with `// TODO`) if CQRS wasn't run |

### `spring-boot` (Java) chain — scaffold only

| Agent | File | Role | Depends on |
|---|---|---|---|
| `ava-build-cycle-java-scaffold` (v1.0.0) | `templates/build-cycle-java-scaffold.md` | Maven multi-module Spring Boot 3/Java 21 skeleton — parent BOM, per-BC domain/application/infrastructure/api modules, SharedKernel, Contracts, Host | `architecture-blueprint.md` + `project-config.yaml`; own dual gate (Routing Guard + Step 0 Dependency Validation Gate requiring blueprint + security-architecture.md + APPROVED readiness-gate) — stricter pre-flight than the .NET scaffold agent |
| `ava-build-cycle-java-persistence` 🚧 STUB | *(referenced only — no file exists)* | Would presumably mirror efcore | java-scaffold's "Próximo" line points to it; **confirmed absent** from `templates/` — only a stale unmerged git branch ref (`origin/merge/2167-...-implementar-build-cycle-java-persistence`) exists, not present in this working tree |

### `fastapi` (Python) chain — scaffold only

| Agent | File | Role | Depends on |
|---|---|---|---|
| `ava-build-cycle-python-scaffold` (v1.0.0) | `templates/build-cycle-python-scaffold.md` | FastAPI + SQLAlchemy2 async + Alembic monorepo skeleton, `pip-audit` gate | `architecture-blueprint.md` + `project-config.yaml`; same dual gate pattern as Java (Routing Guard + Gate de Pré-condições F2) |
| `ava-build-cycle-python-persistence` / `ava-build-cycle-python-api` | *(referenced only — no files exist)* | — | python-scaffold's "Próximo" line points to a 2-agent continuation; **both confirmed absent** from `templates/`, same STUB pattern as Java (not previously called out by the orchestrator's own text, which lists python as scaffold-only) |

### `angular` chain — `angular → ngrx` (frontend, cross-references backend output)

| Agent | File | Role | Depends on |
|---|---|---|---|
| `ava-build-cycle-angular` (v1.0.0) | `templates/build-cycle-angular-agent.md` | Angular 17+ standalone-component shell, MSAL auth, per-BC list/detail/form components; "Trigger: Executar após `ava-build-cycle-minimal-apis`" | Globs `outputs/tobe/source-code/{prefix}/src/*/Api/Modules/**Module.cs` — cross-stack dependency on the .NET backend's own generated Carter modules, with fallback to `project-config.yaml`'s BC list |
| `ava-build-cycle-ngrx` (v1.0.0) | `templates/build-cycle-ngrx-agent.md` | NgRx Signal Store per BC (`@ngrx/signals` only — classic Actions/Reducers/Effects explicitly forbidden); rewires list/form components to consume the store | Globs `.../features/*/`, `models/*.model.ts`, `services/*.service.ts` from angular's output. **Hard block** (unlike cqrs/minimal-apis' graceful degradation): "Execute @ava-build-cycle-angular antes de @ava-build-cycle-ngrx" if service not found. Last agent in the whole build-cycle pipeline — emits `BUILD_CYCLE_COMPLETE` and hands off to devops-ci/cd + QA agents |

### `react` chain 🚧 STUB — *(referenced only, no file exists)*

The orchestrator's Step 0.4 warns `"build-cycle not yet implemented for react. Falling back to
generic mode"` for react (and any other unlisted framework) rather than hard-stopping —
confirming this is a known, intentional gap rather than a silent failure.

**Full-source-read status (all build-cycle agents)**: ✅ scoped throughout — every non-first
agent in a chain Globs only its predecessor's specific generated output directory/file
pattern (e.g. `Domain/Entities/*.cs`, `Api/Modules/**Module.cs`, `services/*.service.ts`), never
the whole `outputs/tobe/source-code/` tree or the AS-IS legacy `repository_path`. First-in-chain
agents (dotnet-scaffold, java-scaffold, python-scaffold) read only docs/config since no source
tree exists yet at that point.

---

## 3. Full Source Re-Read Flags

Per the AS-IS-phase precedent (where `solution-delphi.md` was optimized to consume pre-extracted
AST JSON instead of re-reading the whole legacy repo), every tech-stack agent was checked for
unbounded full-source reads. **None were found among the coder agents, build-fixer, or
build-cycle templates** — all read either specific artifact files or a single scoped file
(one entity, one BC's generated code, or the exact `{file}` named in a compile error) per read
operation. The one legitimate full-tree scanner is `build-validator-agent.md`, whose job
inherently requires it:

- **`agents/build-validator-agent.md` (v2.3.0) — full-tree scan, but legitimate.** Build/lint/CVE
  validation cannot be scoped to a single file — a compiler needs to see the whole solution to
  catch cross-file breaks. Verbatim evidence:
  - Step B2: `dotnet build src/{BC}/{Prefix}.{BC}.Domain/ --no-restore --no-incremental -c Release` (repeated per BC × per layer)
  - Step B3: `dotnet build {solution_file} --no-restore --no-incremental -c Release /p:TreatWarningsAsErrors=true` (whole solution)
  - Step B4: `dotnet format --verify-no-changes --severity warn` (whole tree)
  - Step B5: `dotnet list package --vulnerable --include-transitive` (whole solution)
  - Step B6: `grep -r "HintPath" --include="*.csproj" .` (recursive over the entire backend folder)
  - Frontend equivalents: `npm run build` / `npx vite build`, `npx eslint .`, `npm audit --json`
  - **No cross-invocation dedup**: every build step is explicitly run with `--no-incremental`,
    and there is no logic that skips already-validated files/layers on repeat invocations — each
    invocation re-runs the entire B1→B7 (or F1→F5/VF1→VF6) pipeline from scratch. The only
    caching present is dependency-download caching via named volumes
    (`cache_volumes: true — "reutilizar volumes nomeados NuGet/npm entre execuções"`), not
    build-result caching.
  - **Does it duplicate `verify_scaffold.py` (orchestrator Step 5.5)?** No — build-validator's own
    Step B0.5/F0.5 invokes the *same script* (`verify_scaffold.py --manifest {dotnet|angular}`)
    a second time, but for a distinct purpose (file-existence pre-gate before `dotnet
    restore`/`npm ci`, explicitly "Evita 5 ciclos de retry com erros triviais de arquivo
    ausente") — complementary, not duplicated compilation work, since the orchestrator's own
    Step 5.5 call is a hard gate on dispatching build-validator at all, and build-validator's
    call is defensive re-verification immediately before it starts spending build cycles.

**Everything else is scoped / artifact-based (no flag):**
- `coder-dotnet-backend.md` / `coder-java-backend.md` / `coder-go-backend.md`: read one Domain
  entity file at a time before generating service code for that entity (e.g. dotnet: `"READ
  src/{BCName}/{prefix}.{BCName}.Domain/Entities/{EntityName}.cs → enumerar: factory methods
  estáticos, métodos públicos/internos, propriedades de navegação"`), never the whole tree.
- `coder-python-backend.md`: no per-entity read pattern documented at all — no whole-tree
  read either.
- `coder-angular-frontend.md`: only self-reviews its own just-generated
  `outputs/tobe/source-code/frontend/` for the Security Compliance Gate; scaffold completeness
  is checked via the deterministic `verify_scaffold.py` script, not an LLM Glob/Read of the tree.
- `build-fixer-agent.md`: works strictly from the `errors[]` list handed to it by
  build-validator — `"PARA CADA erro com solução identificada: READ {file} → entender contexto
  ao redor da linha com erro"` — reads only the file(s) named in each error, never the whole
  codebase. Guardrail #4 explicitly forbids touching anything outside `source_code_path`.
- All build-cycle template agents: Glob only the specific predecessor-generated directory/file
  pattern they depend on (see §2b table), never the full tree.
- **None of the coder agents read the AS-IS legacy `repository_path` directly** — all backend/
  frontend coders consume the already-produced TO-BE artifacts (`architecture-blueprint.md`,
  `security-architecture.md`, `spec.md`, `bounded-context-map.md`) rather than re-reading legacy
  source. (Angular does read `outputs/asis/bounded-context-map.md` as an optional fallback, but
  that is an AS-IS-phase *artifact*, not raw legacy source.)

---

## 4. Discrepancies Found

These are documentation/spec inconsistencies surfaced while building this map — recorded here,
not silently corrected, since resolving them requires a decision about which file is authoritative.

### 4.1 `module.yaml` STUB labels contradict both the orchestrator and the files themselves

`src/modules/ava-fabric-agents/tech-stack/module.yaml` marks `ava-stack-java-backend`,
`ava-stack-python-backend`, and `ava-stack-go-backend` as `status: stub`. This contradicts
**both** `orchestrator-stack.md`'s own routing table (all three marked `✅ Implemented`) **and**
the actual content of each file (all three have full generation pipelines, 9 guardrails, hard
prerequisite gates, and complete Output/Security-Compliance contracts — nothing resembling the
genuine ~100-line stub template used by node/react/blazor/vue). `module.yaml` also omits
`ava-stack-docs-researcher`, `ava-stack-build-validator`, and `ava-stack-build-fixer` from its
agent registry entirely, even though all three are mandatory, always-invoked parts of the
pipeline per the orchestrator's own "Invocation Invariant." `module.yaml` appears stale relative
to the orchestrator and the coder-agent files.

### 4.2 `svelte` frontend — referenced but no implementing file exists

`orchestrator-stack.md`'s `FRONTEND_AGENTS` map (Step 0.3b) and its frontend routing table both
list `svelte → ava-stack-svelte-frontend`, marked `🚧 STUB`. No file
`agents/coder-svelte-frontend.md` exists anywhere in
`src/modules/ava-fabric-agents/tech-stack/agents/` (confirmed via directory listing — only
angular/react/blazor/vue frontend coders are present). If a project ever set
`tobe_stack.frontend_framework: svelte`, Step 0.3b's own guard (`IF resolved_frontend_agent is
undefined: ⛔ STOP`) would presumably fire, but since `resolved_frontend_agent` *is* defined
(the string `"ava-stack-svelte-frontend"`), the orchestrator would attempt to dispatch a
nonexistent agent rather than hitting its own "STACK NOT SUPPORTED" stop — a distinction the
routing map's undefined-check does not cover (defined-but-missing vs. truly undefined).

### 4.3 `build-cycle-java-persistence` and `build-cycle-python-persistence`/`-api` — referenced but no files exist

Same pattern as 4.2, one layer down: `orchestrator-stack.md`'s Step 0.4 build-cycle resolution
table marks `ava-build-cycle-java-persistence` as `🚧 STUB` for the java chain, and
`build-cycle-java-scaffold.md`'s own "Próximo" handoff line points to it by name — but no such
file exists under `templates/` (only a stale, unmerged git branch reference
`origin/merge/2167-premerge-implementar-build-cycle-java-persistence`, not present in this
working tree). The python chain has the same gap one step further: `build-cycle-python-
scaffold.md`'s own handoff points to `@ava-build-cycle-python-persistence →
@ava-build-cycle-python-api`, neither of which exists — this second gap is not mentioned in the
orchestrator's own Step 0.4 table at all (which lists the python chain as scaffold-only), so it
is only visible from inside the scaffold agent's own handoff text.

### 4.4 `ava-build-cycle-react` — referenced but no file exists

`orchestrator-stack.md`'s Step 0.4 build-cycle resolution table marks
`ava-build-cycle-react` `🚧 STUB` for the react frontend chain. No such file exists under
`templates/`. Unlike 4.2/4.3, this gap **is** explicitly acknowledged by the orchestrator's own
fallback logic: Step 0.4's `other → ⚠️ WARN: "build-cycle not yet implemented for
{frontend_framework}. Falling back to generic mode"` — so react in build-cycle mode degrades to
attempting the *generic*-mode `coder-react-frontend.md`, which is itself also a stub (see
frontend routing table, §1) — a stub-falls-back-to-a-stub chain with no working react path in
either pipeline mode.

### 4.5 Dual invocation path to backend/frontend code generation — open question, not resolved here

This orchestrator (`ava-stack-orchestrator`) has its own complete backend+frontend routing
tables and its own hard prerequisite gate (`architecture-blueprint.md`,
`security-architecture.md`, `readiness-gate-status.json == APPROVED`) before it will generate
anything — meaning it is built to run as a standalone entry point (triggers `SG`/`BG`/`FG`
dispatched directly). However, the separately-documented TO-BE architecture orchestrator
(`src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`) **also**
resolves and dispatches coder agents directly from its own `CODER_AGENTS` map at its "Fase 4.7 —
Geração de Código" (confirmed: `CODER_AGENTS = { "dotnet": "coder-dotnet", ... }`, resolving to
`tobe-architecture/agents/coder-dotnet.md` — a **distinct file** from this module's
`agents/coder-dotnet-backend.md`, not merely an alias). `orchestrator-tobe.md` line 100 states
explicitly: *"Este orquestrador NÃO executa gates de build. Esses gates são responsabilidade
exclusiva do `{resolved_coder_agent}` (resolvido de `tobe_stack.backend_framework` na Fase
4.7)"* — i.e. it expects the coder agent itself to run build gates inline, with no mention of
`ava-stack-build-validator`, `ava-stack-docs-researcher`, or this orchestrator's Step 6a/6b/8
pipeline at all. It is unclear from this orchestrator's file alone: (a) whether
`orchestrator-tobe.md`'s Fase 4.7 is supposed to invoke `ava-stack-orchestrator` (this module)
rather than `coder-dotnet` directly, making the latter dead/legacy code; (b) whether the two
`coder-dotnet*` files are two independent, divergent implementations of backend codegen; or (c)
which orchestrator is authoritative for a real pipeline run. This is flagged as an open question
for the separate `docs/tobe-architecture-io-map.md` research pass to resolve — not adjudicated
here.

### 4.6 `verify_scaffold.py` invoked independently by two callers with overlapping manifests

The orchestrator's own Step 5.5 (post-codegen, hard gate on whether build-validator is even
dispatched) and build-validator's Step B0.5/F0.5 (pre-build, defensive re-check) both invoke the
identical script (`src/shared/utils/verify_scaffold.py`) with the identical manifest
(`dotnet`/`angular`) against the identical root path. This is not flagged as a functional bug —
the two calls serve different purposes at different points in the pipeline (see §3) — but it is
duplicate work in the literal sense of running the same deterministic check twice per run with
no caching of the first result.

---

## 5. Cross-Agent Consumption Summary

| Consuming agent | Reads from | Relationship |
|---|---|---|
| `{resolved_backend_agent}` (Step 3) | `outputs/tobe/docs/research/docs-research-bundle.md` (docs-researcher) | orchestrator-injected `additional_context`; dotnet/java/python/go all treat it as **optional/non-blocking** enrichment |
| `{resolved_frontend_agent}` (Step 5) | `outputs/tobe/docs/research/docs-research-bundle.md` (docs-researcher) | orchestrator-injected `additional_context`; the angular coder's own file shows **no actual read** of this bundle despite the orchestrator instructing it to — see §2 note |
| `coder-{dotnet\|java\|go}-backend` | `architecture-blueprint.md`, `security-architecture.md`, `readiness-gate-status.json` (orchestrator-verified pre-flight artifacts, re-verified by each coder's own gate) | hard-blocking dependency gate, duplicated at both orchestrator and per-coder level |
| `coder-angular-frontend` | `outputs/asis/bounded-context-map.md` (AS-IS phase) | optional fallback — only consulted if `bounded_contexts[]` isn't already resolved |
| `ava-build-cycle-efcore` | `ava-build-cycle-dotnet-scaffold`'s generated `Domain/Entities/*.cs` | hard-blocking, chain-order dependency |
| `ava-build-cycle-cqrs` | `spec.md` (docs) + optionally `ava-build-cycle-efcore`'s repositories | soft dependency — degrades with a warning rather than blocking |
| `ava-build-cycle-minimal-apis` | `ava-build-cycle-cqrs`'s generated `Commands/**/*Command.cs`/`Queries/**/*Query.cs` | soft dependency — degrades to stub modules with TODOs if absent |
| `ava-build-cycle-angular` | `ava-build-cycle-minimal-apis`'s generated `Api/Modules/**Module.cs` | cross-stack (frontend reading backend's generated output) — falls back to `project-config.yaml`'s BC list if absent |
| `ava-build-cycle-ngrx` | `ava-build-cycle-angular`'s generated `models/*.model.ts`, `services/*.service.ts` | hard-blocking, chain-order dependency (unlike cqrs/minimal-apis' graceful degradation) |
| `ava-stack-build-validator` | orchestrator's Step 5.5 `artifacts_confirmed` flag | hard-blocking — "⛔ NUNCA despachar `ava-stack-build-validator` se `artifacts_confirmed == false`" |
| `ava-stack-build-fixer` | `errors[]` list from `ava-stack-build-validator` | internal sub-dispatch only — never invoked directly by the orchestrator or any coder agent |
| `ava-stack-orchestrator` (Step 6b) | `SecurityComplianceReport-Backend.md` (backend coder) + `SecurityComplianceReport-Frontend.md` (frontend coder) + `security-architecture.md` (TO-BE phase reference) | true consolidation — merges backend+frontend classifications into `SecurityComplianceReport-Consolidated.md` |
| `orchestrator-tobe.md` Fase 4.7 vs. this orchestrator | `coder-dotnet.md` (tobe-architecture module) vs. `coder-dotnet-backend.md` (this module) | **unresolved** — see §4.5, two independent invocation paths to backend codegen |
