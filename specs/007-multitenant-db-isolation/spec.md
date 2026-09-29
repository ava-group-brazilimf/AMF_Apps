# Agent Specification: multitenant-db-isolation (PBI 2309)

**Feature Branch**: `007-multitenant-db-isolation`
**Created**: 2026-07-07
**Status**: Draft
**Change Type**: modify-existing
**PBI**: 2309 — Pipeline de geração de isolamento de banco multitenant com Finbuckle.MultiTenant

> **Language note**: This spec is a planning document written in **English**.
> Agent body modifications MUST be written in **Brazilian Portuguese** per Constitution Article V.
> Frontmatter fields use mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Change Scope** | Modify two existing agents + create three C# template files |
| **Primary Agent (modified)** | `ava-coder-dotnet` — `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` |
| **Secondary Agent (modified)** | `build-cycle-efcore` — `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-efcore-agent.md` |
| **Version Bump Type** | MINOR — new optional conditional step added (no contract breakage) |
| **Phase** | F3 (code generation) |
| **Module** | `tech-stack` |
| **Trigger Condition** | `persistence.multi_tenancy.enabled: true` in `project-config.yaml` (nested object) |
| **Dispatch** | Internal — invoked via `ava-stack-orchestrator` / `ava-coder-dotnet` |
| **Skill Impact** | No new SKILL.md needed; existing `ava-coder-dotnet` and `ava-stack-orchestrator` skills are unchanged |

> **Existing files — do not create new agent files**:
> - Edit `coder-dotnet-backend.md` to add a conditional multi-tenancy step
> - Edit `build-cycle-efcore-agent.md` to add a `## Multi-tenant EF Core Setup` section
> - Create three new C# template files under `tech-stack/templates/multitenant/`

---

## 2. Agent Frontmatter Changes

**`coder-dotnet-backend.md`** — version bump only (MINOR):

```yaml
# Before:
version: "X.Y.Z"
# After:
version: "X.(Y+1).0"
```

No other frontmatter changes. The `allowed-tools` and `description` fields are unchanged.

**`build-cycle-efcore-agent.md`** — version bump only (MINOR):

```yaml
# Before:
version: "X.Y.Z"
# After:
version: "X.(Y+1).0"
```

---

## 3. Output Contract

New artifacts produced when `persistence.multi_tenancy.enabled: true`:

```yaml
outputs:
  tenant_middleware:     "projects/{project_name}/outputs/tobe/source-code/{bc}/Infrastructure/Multitenancy/TenantResolutionMiddleware.cs"
  app_db_context:        "projects/{project_name}/outputs/tobe/source-code/{bc}/Infrastructure/Persistence/{BCName}DbContext.cs"
  kv_tenant_resolver:    "projects/{project_name}/outputs/tobe/source-code/{bc}/Infrastructure/Multitenancy/KeyVaultTenantConnectionStringResolver.cs"
```

> **Note**: These files are generated per bounded-context (`{bc}`). The existing EF Core
> migration files written by `build-cycle-efcore-agent.md` are unaffected when
> `persistence.multi_tenancy.enabled: false` (default).

Template source files to create:

```
src/modules/ava-fabric-agents/tech-stack/templates/multitenant/
  TenantResolutionMiddleware.cs.tpl
  AppDbContext.multitenant.cs.tpl
  KeyVaultTenantConnectionStringResolver.cs.tpl
```

---

## 4. User Scenarios (Given-When-Then)

> **Language convention**: Story descriptions in Portuguese; Acceptance scenarios in English.

---

### Scenario 1 — Nominal Path: Multi-tenancy Enabled (Priority: P1)

**Story**: Como o orquestrador de geração de código, quero que o `coder-dotnet-backend` detecte
`persistence.multi_tenancy.enabled: true` no `project-config.yaml` e gere automaticamente o scaffolding
Finbuckle.MultiTenant completo, garantindo que dados de tenants distintos sejam isolados por padrão.

**Why this priority**: Core acceptance criterion — isolation must work end-to-end.

**Acceptance Scenarios**:

1. **Given** `project-config.yaml` has `persistence.multi_tenancy.enabled: true`, **When** `coder-dotnet-backend` executes the multi-tenancy step, **Then** all three C# files are generated under `outputs/tobe/source-code/{bc}/Infrastructure/` and `AgentResult.success` is `true`.
2. **Given** the generated `{BCName}DbContext.cs`, **Then** it inherits from `EFCoreDbContext<TenantInfo>` (Finbuckle) and registers a global query filter on `TenantId` for every entity.
3. **Given** the generated `TenantResolutionMiddleware.cs`, **Then** it resolves the current tenant from the `X-Tenant-Id` HTTP header first, falling back to JWT claim `tid`.
4. **Given** the generated `KeyVaultTenantConnectionStringResolver.cs`, **Then** it looks up the connection string in Azure Key Vault using the pattern `{tenantId}--{bc_name}-sql-connection-string` (see `research.md §6`).
5. **Given** execution completes, **Then** `AgentResult.artifacts` lists all three files and `AgentResult.next_agent` is set to the next pipeline step.

---

### Scenario 2 — Default Path: Multi-tenancy Disabled (Priority: P1)

**Story**: Como o orquestrador, quero que o comportamento padrão (sem multitenant) seja preservado
quando `persistence.multi_tenancy.enabled` está ausente ou `false`, evitando regressões.

**Why this priority**: Must not break existing non-multitenant projects.

**Acceptance Scenarios**:

1. **Given** `project-config.yaml` has `persistence.multi_tenancy.enabled: false` (or the field is absent), **When** `coder-dotnet-backend` executes, **Then** no multi-tenancy files are generated.
2. **Given** the above, **Then** the standard `{BCName}DbContext.cs` (non-Finbuckle) is generated as before.
3. **Given** the above, **Then** `AgentResult.success` is `true` and no regression occurs in any downstream artifact.

---

### Scenario 3 — Isolation Validation: Cross-Tenant Data Leak (Priority: P1)

**Story**: Como a equipe de QA, quero validar que consultas do tenant A não retornam dados
do tenant B, garantindo que o global query filter foi configurado corretamente.

**Why this priority**: Safety gate — data isolation failure is a critical security breach.

**Acceptance Scenarios**:

1. **Given** two tenants (A and B) with separate connection strings in Key Vault, **When** a query is executed in the context of tenant A, **Then** only records with `TenantId == A` are returned.
2. **Given** the above, **Then** the `build-cycle-efcore-agent.md` `## Multi-tenant EF Core Setup` section documents the global filter configuration and migration isolation strategy.
3. **Given** `AppDbContext` is seeded with records for both tenants, **When** the global query filter is active, **Then** no record belonging to tenant B appears in any query scoped to tenant A.

---

### Scenario 4 — Edge Case: Missing Finbuckle Package (Priority: P2)

**Story**: Como o agente, quero detectar quando o pacote `Finbuckle.MultiTenant.EntityFrameworkCore`
não está declarado em `project-config.yaml → overrides → nuget_packages` e alertar o operador.

**Why this priority**: Prevents a silent build failure in the generated solution.

**Acceptance Scenarios**:

1. **Given** `persistence.multi_tenancy.enabled: true` but `Finbuckle.MultiTenant.EntityFrameworkCore` is absent from the approved package list, **When** the agent executes, **Then** it emits a warning in `AgentResult.risk.findings` with severity `medium` and lists the missing package.
2. **Given** the above, **Then** `AgentResult.success` is `true` (warning, not failure) and the generated files include a `// TODO: add Finbuckle.MultiTenant.EntityFrameworkCore` comment.

---

## 5. Quality Gate Requirements

- [ ] Change type is `modify-existing` — no new agent ID created (Article II)
- [ ] Version bump is MINOR for both modified agents (new optional step, no contract breakage) (Article X)
- [ ] Conditional step guarded by `persistence.multi_tenancy.enabled: true` (nested config object) — not hardcoded (Article I)
- [ ] All output paths use lowercase `{project_name}` and `tobe/source-code/` folder (Article II)
- [ ] BDD scenarios cover nominal, regression-guard, isolation-validation, and edge paths (Article VI)
- [ ] Security impact assessed: global query filter is the primary isolation control; OWASP A01 (Broken Access Control) mitigated (Article VII)
- [ ] No technology versions hardcoded — Finbuckle version resolved at runtime via NuGet API (not from `reference-architecture.yaml`; see `research.md §2`) (Article I)
- [ ] No new SKILL.md required — internal modification only (Article XI)
- [ ] Template files placed under `tech-stack/templates/multitenant/` (not in `agents/`)
- [ ] No `[NEEDS CLARIFICATION]` markers remain

---

## 6. Dependencies

| Dependency | Agent / File | Reason |
|---|---|---|
| Stack orchestrator | `ava-stack-orchestrator` | Dispatches `coder-dotnet-backend`; reads `persistence.multi_tenancy.enabled` |
| EF Core agent | `build-cycle-efcore-agent.md` | Must include Multi-tenant Setup section before migrations run |
| Reference architecture | `src/shared/data/reference-architecture.yaml` | Stack defaults reference (Finbuckle version resolved via NuGet API at runtime — not stored here; see `research.md §2`) |
| Package approval | `ava-devops-package-approval` | `Finbuckle.MultiTenant.EntityFrameworkCore` must be in approved list |

---

## 7. Exclusions

- **Row-level security at the SQL layer** — handled separately by the DBA runbook; out of scope here.
- **Multi-database-per-tenant provisioning** — this spec covers shared-database / separate-schema isolation only.
- **Tenant onboarding API** — out of scope; assumed to be a separate bounded context.
- **Angular frontend tenant switching UI** — out of scope for this code-generation step.
- **`AgentResult.artifacts` and `AgentResult.next_agent` structured JSON** — these fields apply to agents using the JSON schema pipeline. `build-cycle-efcore-agent.md` and `coder-dotnet-backend.md` are LLM prompt files that produce file artifacts, not structured `AgentResult` JSON payloads; these fields are N/A for this change type.

---

## 8. Assumptions

- `persistence.multi_tenancy` is a **nested object** under `persistence` in `project-config.yaml`. The trigger field is `persistence.multi_tenancy.enabled: boolean` (default: `false`). The `persistence.multi_tenancy.strategy: string` field controls isolation mode (`"shared-table"` | `"schema-per-tenant"`).
- The approved NuGet package list includes (or will be updated to include) `Finbuckle.MultiTenant.EntityFrameworkCore` before code generation runs.
- Azure Key Vault is provisioned and accessible from the generated application (IaC handled by `ava-devops-iac-azure`).
- The tenant identifier is always a GUID or string present in both the HTTP header (`X-Tenant-Id`) and JWT claim (`tid`).
- The generated `AppDbContext` is the single DB context per bounded context — no existing secondary context is present.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Multi-tenancy scaffolding generated | All 3 C# files exist under `Infrastructure/` when `persistence.multi_tenancy.enabled: true` |
| Isolation enforced | Queries scoped to tenant A never return rows belonging to tenant B |
| No regression | All existing non-multitenant projects generate identical output to pre-change behavior |
| Warning on missing package | `AgentResult.risk.findings` contains package warning when Finbuckle absent from approved list |
| Documentation complete | `build-cycle-efcore-agent.md` contains `## Multi-tenant EF Core Setup` section with migration strategy |
| Contract compliance | `AgentResult` validates against `agent-result.schema.json` |
