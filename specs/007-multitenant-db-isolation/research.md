# Research: multitenant-db-isolation (PBI 2309)

**Phase 0 — All unknowns resolved**
**Date**: 2026-07-08

---

## §1 — Config Key Path Correction

**Finding (critical)**: The spec used `persistence.multi_tenancy: true` (flat boolean).  
The actual `project-config.yaml` template (line 178) defines it as a **nested object**:

```yaml
persistence:
  multi_tenancy:
    enabled: false           # boolean trigger
    strategy: "schema-per-tenant"  # schema-per-tenant | shared-table
```

**Decision**: All agent instructions and template files must use `persistence.multi_tenancy.enabled: true` as the trigger. The plan corrects this from the spec.

---

## §2 — Finbuckle.MultiTenant Version Resolution

**Finding**: `src/shared/data/reference-architecture.yaml` and `docs/architecture/ConfigStackDotNet.yaml` (now absorbed into `project-config.yaml`) do NOT include a Finbuckle entry.

**Decision**: The NuGet package version for `Finbuckle.MultiTenant.EntityFrameworkCore` is NOT hardcoded in this spec or plan (Constitution Article I). Instead:

- The `build-cycle-efcore-agent.md` Step 1.5 already implements a NuGet resolution protocol (Passos A → B → C against `api.nuget.org`) for absent packages.
- **The generated agent instruction** will call that same protocol to resolve the version at runtime and add the entry to `Directory.Packages.props`.
- **Rationale**: Finbuckle.MultiTenant follows its own versioning scheme (7.x as of .NET 9/10 era), decoupled from .NET SDK versioning. Hardcoding here would rot quickly.

**Alternative rejected**: Pinning version in `reference-architecture.yaml` was considered. Rejected because it creates a manual maintenance burden for a library not used in every project.

---

## §3 — Where the Conditional Step Belongs

**Finding**: `coder-dotnet-backend.md` is used when `pipeline_mode: generic`. It has no reference to `persistence.*` config keys today. The EF Core-specific logic (DbContext, Repositories) is entirely within `build-cycle-efcore-agent.md` for `pipeline_mode: build-cycle`.

**Decision**:

| Pipeline mode | Target file | What gets added |
|---|---|---|
| `build-cycle` | `build-cycle-efcore-agent.md` | Step 3.1-MT (variant DbContext) + new Step 7 (Multi-tenant EF Core Setup) |
| `generic` | `coder-dotnet-backend.md` | New Step: "Multi-tenancy Scaffold Gate" |

Both files get a conditional block guarded by `persistence.multi_tenancy.enabled: true`. This is the correct architectural split: one file per pipeline mode.

---

## §4 — Tenant Resolution Strategy

**Finding**: PBI 2309 requires resolving the current tenant from:
1. HTTP header `X-Tenant-Id` (first)
2. JWT claim `tid` (fallback)

**Decision**: `TenantResolutionMiddleware.cs` implements the Finbuckle `IMultiTenantStore<TTenantInfo>` strategy pattern, using `ITenantResolver` or the `UseMultiTenant<TTenantInfo>()` middleware pipeline approach:

```csharp
// Resolution order: X-Tenant-Id header → JWT claim `tid`
app.UseMultiTenant<TenantInfo>();
// Configured with: .WithResolutionStrategy<HeaderStrategy>()
//                  .WithResolutionStrategy<ClaimStrategy>(fallback)
```

**Alternatives considered**: 
- Custom `IMultiTenantContext<TenantInfo>` injection — rejected (too low-level, bypasses Finbuckle's DI pipeline).
- Single middleware reading both — accepted as simpler for projects not using the full Finbuckle store pipeline.

---

## §5 — AppDbContext Inheritance Chain

**Finding**: `EFCoreDbContext<TTenantInfo>` is Finbuckle's base `DbContext` that automatically applies the `TenantId` global query filter.

**Decision**: The multitenant `AppDbContext` inherits as:

```csharp
internal sealed class {BCName}DbContext
    : EFCoreDbContext<TenantInfo>, IUnitOfWork
```

Key invariants:
- `EFCoreDbContext<TenantInfo>` requires `IMultiTenantContextAccessor<TenantInfo>` injected via constructor.
- The `OnModelCreating` override calls `base.OnModelCreating(modelBuilder)` FIRST (Finbuckle requirement — this is where the global query filter is registered).
- Each entity that must be tenant-filtered implements `ITenantInfo` OR has a `TenantId` property covered by Finbuckle's auto-filter.

---

## §6 — KeyVault Naming Convention

**Finding**: The existing EF Core agent uses the pattern `{bc_name}-sql-connection-string` for Key Vault secrets.

**Decision**: The `KeyVaultTenantConnectionStringResolver.cs` uses the per-tenant pattern:

```
{tenant-id}--{bc_name}-sql-connection-string
```

Double-dash (`--`) is the Key Vault hierarchical separator. This avoids collisions with the single-tenant key while being parseable: `{tenantId}--{baseSecretName}`.

**Alternatives considered**: `sql-connstr-{tenant-id}` prefix — rejected (breaks alphabetical grouping in Key Vault by connection type).

---

## §7 — Migration Isolation Strategy

**Finding**: `persistence.multi_tenancy.strategy: "schema-per-tenant"` implies each tenant has its own schema but shares the same SQL Server database. EF Core migrations apply once to a database, not per-tenant.

**Decision**: The migration instructions document (Step 4 of `build-cycle-efcore-agent.md`) will include a sub-section for:
1. **Shared-table strategy**: no migration changes needed; `TenantId` column added automatically by Finbuckle.
2. **Schema-per-tenant strategy**: tenant schema creation via a custom `IMigrationsSqlGenerator` or per-tenant migration runner (documented as a TODO, not generated — architectural boundary).

This is explicitly documented in the `## Multi-tenant EF Core Setup` section.

---

## §8 — Template File Naming Convention

**Finding**: All other templates use `.md` (agent instructions). The 3 new files are C# code templates embedded within agent instructions (not standalone `.tpl` files).

**Decision**: The 3 C# template files are created as `.cs.tpl` under `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/`. Agents reference these files via `READ` commands and embed them as code blocks in their output. This follows the same pattern as how `build-cycle-dotnet-scaffold-agent.md` references shared templates.

---

## §9 — module.yaml Impact

**Finding**: `module.yaml` lists `agents:` only. Template files are not listed. No new agent IDs are being created.

**Decision**: `module.yaml` does NOT need to be updated for this feature. The `tech-stack` module's version will bump from `1.3.0` → `1.4.0` (MINOR — new capability added) as a documentation update only (no new agent registrations).

---

## Resolved Unknowns Summary

| # | Unknown | Resolution |
|---|---------|------------|
| 1 | Config key path for multi_tenancy | `persistence.multi_tenancy.enabled: true` (nested object) |
| 2 | Finbuckle version | Resolved at runtime via NuGet API (not hardcoded) |
| 3 | Which agent gets the conditional step | Both: EF Core agent (build-cycle) + coder-dotnet-backend (generic) |
| 4 | Tenant resolution order | X-Tenant-Id header → JWT claim `tid` |
| 5 | AppDbContext base class | `EFCoreDbContext<TenantInfo>` (Finbuckle) |
| 6 | Key Vault naming | `{tenantId}--{bc_name}-sql-connection-string` |
| 7 | Migration strategy | Documented as TODO for schema-per-tenant; auto for shared-table |
| 8 | Template format | `.cs.tpl` files under `tech-stack/templates/multitenant/` |
| 9 | module.yaml update | Not required; version bump only in module.yaml `version` field |
