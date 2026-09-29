# Agent Development Tasks: multitenant-db-isolation (PBI 2309)

**Plan**: `specs/007-multitenant-db-isolation/plan.md`
**Change Type**: `modify-existing` | **Phase**: F3 | **Module**: `tech-stack`

> Change type is `modify-existing`. Categories 1, 3, and 5 are adapted accordingly.
> Complete categories sequentially unless [P] marks a task as parallelizable.
> Design references: `data-model.md` (types + layer ownership), `research.md` (all key decisions), `quickstart.md` (validation scripts).

---

## Category 1 — Pre-flight: Version Bumps & Context Read

Must complete before any other category. Establishes the exact current state of both target files.

- [X] **1.1** Read `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-efcore-agent.md`
  — Confirm current `version:` value in frontmatter
  — Identify line numbers of: Step 1.2, Step 1.5, Step 3.1, Step 3.6, and the Output Contract section
  — Note the exact heading text of the last step (Step 6 — Exibir Resultado)

- [X] **1.2** [P] Read `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
  — Confirm current `version:` value in frontmatter
  — Identify position of guardrail G9 (last guardrail) and the `## Clean Architecture Template` heading that follows it
  — Note whether a `## Multi-tenancy Scaffold Gate` section already exists (must NOT exist)

- [X] **1.3** Bump `version:` in `build-cycle-efcore-agent.md` frontmatter: `1.0.0` → `1.1.0`
  — Edit only the `version:` field; leave `name:`, `description:`, `allowed-tools:` unchanged

- [X] **1.4** [P] Bump `version:` in `coder-dotnet-backend.md` frontmatter: `1.0.0` → `1.1.0`
  — Edit only the `version:` field; leave `name:`, `description:`, `allowed-tools:` unchanged

---

## Category 2 — C# Template Files

**Blocks tasks 3.3, 3.4, and 4.1.** Create independently of Category 3 modifications.
All 3 template files live in `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/`.
Agent instructions embed them as code-block examples and reference them via `READ` commands.

- [X] **2.1** Create directory `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/`
  — Verify the `templates/` parent directory exists (it does — `build-cycle-efcore-agent.md` is inside it)

- [X] **2.2** Create `TenantResolutionMiddleware.cs.tpl`
  — Path: `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/TenantResolutionMiddleware.cs.tpl`
  — Content: C# ASP.NET Core middleware class with `#nullable enable`
  — Namespace: `{SolutionPrefix}.{BCName}.Infrastructure.Multitenancy`
  — Resolution logic (see `data-model.md §2.3`):
    1. Check `context.Request.Headers["X-Tenant-Id"]` — if present, resolve tenant by this ID
    2. If absent, check `context.User.FindFirst("tid")?.Value` — resolve tenant by JWT claim
    3. If neither present: return `context.Response.StatusCode = 400` + problem details JSON
    4. If tenant ID found but `ITenantStore<TenantInfo>` cannot find it: return `404`
    5. Set `IMultiTenantContextSetter<TenantInfo>` and call `next(context)`
  — Include `using Finbuckle.MultiTenant;` and `using Finbuckle.MultiTenant.Abstractions;`
  — ⚠️ Include comment: `// ⛔ GUARDRAIL: DO NOT add using Microsoft.EntityFrameworkCore — Infrastructure only`

- [X] **2.3** Create `AppDbContext.multitenant.cs.tpl`
  — Path: `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/AppDbContext.multitenant.cs.tpl`
  — Content: C# EF Core DbContext class with `#nullable enable`
  — Namespace: `{SolutionPrefix}.{BCName}.Infrastructure.Persistence`
  — Class signature: `internal sealed class {BCName}DbContext : EFCoreDbContext<TenantInfo>, IUnitOfWork`
  — Constructor: injects `DbContextOptions<{BCName}DbContext>`, `ICurrentUserService`, `IMultiTenantContextAccessor<TenantInfo>` — passes options and accessor to `base(...)`
  — `OnModelCreating`: calls `base.OnModelCreating(modelBuilder)` FIRST (Finbuckle requirement, add comment), then `modelBuilder.HasDefaultSchema("{bc_name_lower}")`, then `ApplyConfigurationsFromAssembly`
  — Global query filter for soft-delete (conditional on `soft_delete: true`): applied AFTER base call
  — `SaveChangesAsync(CancellationToken cancellationToken = default)` with `override async` (see guardrail G5 in `coder-dotnet-backend.md` for the CS0114 rule)
  — Audit fields logic matching existing `build-cycle-efcore-agent.md` Step 3.1 pattern
  — ⚠️ Comment at top: `// Multi-tenant variant — generated when persistence.multi_tenancy.enabled: true`

- [X] **2.4** [P] Create `KeyVaultTenantConnectionStringResolver.cs.tpl`
  — Path: `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/KeyVaultTenantConnectionStringResolver.cs.tpl`
  — Content: C# class with `#nullable enable`
  — Namespace: `{SolutionPrefix}.{BCName}.Infrastructure.Multitenancy`
  — Interface: `public interface IKeyVaultTenantConnectionStringResolver { Task<string> ResolveAsync(string tenantId, string bcName, CancellationToken ct = default); }`
  — Implementation: `internal sealed class KeyVaultTenantConnectionStringResolver : IKeyVaultTenantConnectionStringResolver`
  — Constructor: injects `SecretClient` (from `Azure.Security.KeyVault.Secrets`) and `IMemoryCache`
  — `ResolveAsync` logic:
    1. Build cache key: `$"connstr:{tenantId}:{bcName}"`
    2. Check `IMemoryCache` — return cached value if present
    3. Key Vault secret name: `$"{tenantId}--{bcName}-sql-connection-string"` (double-dash separator per `research.md §6`)
    4. Await `_secretClient.GetSecretAsync(secretName, cancellationToken: ct)` — extract `.Value.Value`
    5. Cache with `absoluteExpirationRelativeToNow: TimeSpan.FromMinutes(5)`
    6. Return connection string
  — Include `using Azure.Security.KeyVault.Secrets;` and `using Microsoft.Extensions.Caching.Memory;`

---

## Category 3 — build-cycle-efcore-agent.md Modifications

**Depends on Category 2 (task 3.3 and 3.4 read those template files).**
Tasks 3.1 and 3.2 are independent of Category 2 and can start immediately after Category 1.

- [X] **3.1** Add Step 1.2c to `build-cycle-efcore-agent.md`
  — Insert immediately after the existing Step 1.2 block (which reads `connection_resiliency`) and before Step 1.2b
  — Actually: insert as a new sub-step after Step 1.2b (the connection_source validation block)
  — Content (in Brazilian Portuguese):

  ```
  1.2c  Ler persistence.multi_tenancy.enabled  (default: false)
        Ler persistence.multi_tenancy.strategy  (default: "shared-table")
        
        SE multi_tenancy.enabled: true:
          EXIBIR: "⚡ Multi-tenancy Finbuckle ativado — strategy: {strategy}"
          → Adicionar Finbuckle.MultiTenant.EntityFrameworkCore à lista
            de pacotes a verificar no Step 1.5
          → A geração do DbContext no Step 3.1 usará a variante multitenant (Step 3.1-MT)
  ```

- [X] **3.2** Add `Finbuckle.MultiTenant.EntityFrameworkCore` to the package list in Step 1.5
  — Insert a conditional block at the end of the Step 1.5 package list (after `StackExchange.Redis`):

  ```
  SE multi_tenancy.enabled: true:
    - Finbuckle.MultiTenant.EntityFrameworkCore  ← Resolver via NuGet API (Passos A→B→C)
      ⚠️ Versão NÃO hardcoded — usar protocolo de resolução automática
      Target framework: net{backend_version}
  ```

- [X] **3.3** Add Step 3.1-MT (multitenant DbContext variant) to `build-cycle-efcore-agent.md`
  — Insert immediately after the existing `#### Step 3.1 — DbContext` block
  — Content: new heading `#### Step 3.1-MT — DbContext (Variante Multitenant)` in Brazilian Portuguese
  — Guard clause at top: `⚠️ Executar APENAS quando persistence.multi_tenancy.enabled: true. Substitui o Step 3.1 padrão — não gerar ambos para o mesmo BC.`
  — Instruction to READ `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/AppDbContext.multitenant.cs.tpl`
  — Instruction to substitute placeholders: `{BCName}`, `{bc_name_lower}`, `{SolutionPrefix}`
  — Instruction to WRITE to `Infrastructure/Persistence/{BCName}DbContext.cs`
  — Include a note: `base.OnModelCreating(modelBuilder)` MUST be called first (Finbuckle requirement)
  — Include the Package Reference instruction: add `<PackageReference Include="Finbuckle.MultiTenant.EntityFrameworkCore" />` to `{SolutionPrefix}.{BCName}.Infrastructure.csproj` (no version — CPM)

- [X] **3.4** Add Finbuckle DI registration block to Step 3.6 (DependencyInjection.cs)
  — Locate the existing Step 3.6 `DependencyInjection.cs` generation in `build-cycle-efcore-agent.md`
  — Add a conditional block at the end of the `Add{BCName}Infrastructure` method (after the `IDbConnectionFactory` registration, before `return services;`), guarded by `// SE multi_tenancy.enabled: true`:

  ```csharp
  // SE multi_tenancy.enabled: true
  services.AddMultiTenant<TenantInfo>()
      .WithHeaderStrategy("X-Tenant-Id")
      .WithClaimStrategy("tid");

  services.AddScoped<IKeyVaultTenantConnectionStringResolver,
                     KeyVaultTenantConnectionStringResolver>();
  ```
  — Add instruction to also register `TenantResolutionMiddleware` usage note:
    `// ⚠️ Em Program.cs: adicionar app.UseMultiTenant<TenantInfo>() APÓS UseAuthentication() e ANTES de UseAuthorization()`

- [X] **3.5** Add `## Multi-tenant EF Core Setup` section to `build-cycle-efcore-agent.md`
  — Insert after the existing `### Step 6 — Exibir Resultado` section (as a new top-level `##` section, not a numbered step)
  — Sub-steps (in Brazilian Portuguese):

  ```
  7.1  Gerar TenantResolutionMiddleware.cs por BC:
       READ: src/modules/ava-fabric-agents/tech-stack/templates/multitenant/TenantResolutionMiddleware.cs.tpl
       Substituir: {BCName}, {SolutionPrefix}
       WRITE: Infrastructure/Multitenancy/TenantResolutionMiddleware.cs

  7.2  Gerar KeyVaultTenantConnectionStringResolver.cs por BC:
       READ: src/modules/ava-fabric-agents/tech-stack/templates/multitenant/KeyVaultTenantConnectionStringResolver.cs.tpl
       Substituir: {BCName}, {SolutionPrefix}, {bc_name} (kebab-case do BC)
       WRITE: Infrastructure/Multitenancy/KeyVaultTenantConnectionStringResolver.cs

  7.3  Gerar TenantInfo.cs por BC (classe que implementa ITenantInfo):
       Namespace: {SolutionPrefix}.{BCName}.Infrastructure.Multitenancy
       Campos: Id (string), Identifier (string), Name (string), ConnectionString (string)
       WRITE: Infrastructure/Multitenancy/TenantInfo.cs

  7.4  Atualizar MigrationInstructions.md com seção de isolamento multitenant:
       SE strategy = "shared-table":
         Acrescentar: "Multi-tenant: TenantId adicionado automaticamente pelo EFCoreDbContext<TenantInfo>.
         Nenhuma alteração adicional nas migrations é necessária."
       SE strategy = "schema-per-tenant":
         Acrescentar bloco TODO: "# Multi-tenant Schema-per-Tenant (TODO)
         Implementar IMigrationsSqlGenerator customizado ou script de criação de schema por tenant.
         Referência: https://www.finbuckle.com/MultiTenant/Docs/EFCore — Schema Per Tenant Strategy."
  ```

  — Also update the Output Contract section at the bottom of `build-cycle-efcore-agent.md` to add 3 conditional output paths:
  ```yaml
  # SE multi_tenancy.enabled: true (por BC):
  per_bc_tenant_middleware:  "src/{BCName}/{prefix}.{BCName}.Infrastructure/Multitenancy/TenantResolutionMiddleware.cs"
  per_bc_tenant_resolver:    "src/{BCName}/{prefix}.{BCName}.Infrastructure/Multitenancy/KeyVaultTenantConnectionStringResolver.cs"
  per_bc_tenant_info:        "src/{BCName}/{prefix}.{BCName}.Infrastructure/Multitenancy/TenantInfo.cs"
  ```

- [X] **3.6** Add missing-package warning path to `build-cycle-efcore-agent.md` Step 1.2c (covers Scenario 4)
  — Extend the Step 1.2c block (added in task 3.1) with a second conditional:

  ```
  SE multi_tenancy.enabled: true E Finbuckle.MultiTenant.EntityFrameworkCore
  NÃO encontrado no Directory.Packages.props APÓS tentativa de resolução NuGet (Step 1.5):
    WARN: "⚠️ Finbuckle.MultiTenant.EntityFrameworkCore não encontrado na lista de pacotes aprovados."
    → Adicionar ao AgentResult.risk.findings:
        { severity: "medium", message: "Finbuckle.MultiTenant.EntityFrameworkCore ausente.
          Adicionar ao Directory.Packages.props antes de compilar." }
    → Gerar os 3 arquivos normalmente, mas incluir em cada um o comentário:
        // TODO: adicionar <PackageReference Include=\"Finbuckle.MultiTenant.EntityFrameworkCore\" />
        //        ao Infrastructure.csproj e resolver versão via NuGet antes de compilar.
    → AgentResult.success: true (warning, não falha — continuar pipeline)
  ```
  — This warning path satisfies Scenario 4 AC1 and AC2 from spec §4

---

## Category 4 — coder-dotnet-backend.md Modification (Generic Pipeline Mode)

**Depends on Category 2 (reads template files).** Independent of Category 3.

- [X] **4.1** Add `## Multi-tenancy Scaffold Gate` section to `coder-dotnet-backend.md`
  — Insert between `### G9 — NuGet Package Completeness` and `## Clean Architecture Template`
  — Content (in Brazilian Portuguese):

  ```markdown
  ## Multi-tenancy Scaffold Gate

  > Executado APENAS quando `persistence.multi_tenancy.enabled: true` em project-config.yaml.
  > Ler também: `persistence.multi_tenancy.strategy` (default: "shared-table").

  ```
  READ projects/{project_name}/context/project-config.yaml
    → persistence.multi_tenancy.enabled  (default: false)
    → persistence.multi_tenancy.strategy (default: "shared-table")

  SE multi_tenancy.enabled: false (ou ausente):
    → PULAR esta seção. Continuar com ## Clean Architecture Template.

  SE multi_tenancy.enabled: true:
    EXIBIR: "⚡ Multi-tenancy Scaffold Gate — Gerando arquivos Finbuckle.MultiTenant"

    PARA CADA bounded context em {bounded_contexts}:

      1. Gerar TenantResolutionMiddleware.cs:
         READ src/modules/ava-fabric-agents/tech-stack/templates/multitenant/TenantResolutionMiddleware.cs.tpl
         Substituir: {BCName}, {SolutionPrefix}
         WRITE projects/{project_name}/outputs/tobe/source-code/{BCName}/src/{BCName}/{SolutionPrefix}.{BCName}.Infrastructure/Multitenancy/TenantResolutionMiddleware.cs

      2. Gerar {BCName}DbContext.cs (variante multitenant):
         READ src/modules/ava-fabric-agents/tech-stack/templates/multitenant/AppDbContext.multitenant.cs.tpl
         Substituir: {BCName}, {bc_name_lower}, {SolutionPrefix}
         WRITE projects/{project_name}/outputs/tobe/source-code/{BCName}/src/{BCName}/{SolutionPrefix}.{BCName}.Infrastructure/Persistence/{BCName}DbContext.cs

      3. Gerar KeyVaultTenantConnectionStringResolver.cs:
         READ src/modules/ava-fabric-agents/tech-stack/templates/multitenant/KeyVaultTenantConnectionStringResolver.cs.tpl
         Substituir: {BCName}, {SolutionPrefix}, {bc_name} (kebab-case)
         WRITE projects/{project_name}/outputs/tobe/source-code/{BCName}/src/{BCName}/{SolutionPrefix}.{BCName}.Infrastructure/Multitenancy/KeyVaultTenantConnectionStringResolver.cs

      4. Adicionar ao Infrastructure.csproj:
         <PackageReference Include="Finbuckle.MultiTenant.EntityFrameworkCore" />
         ⚠️ Versão via CPM (Directory.Packages.props) — resolver via NuGet API se ausente
  ```

  — Close the markdown fence after the DI note above
  — After this section, continue with the existing `## Clean Architecture Template`

---

## Category 5 — Module Registration

Independent of all categories except 1. Can run immediately after Category 1 completes.

- [X] **5.1** Bump `version:` in `src/modules/ava-fabric-agents/tech-stack/module.yaml`: `1.3.0` → `1.4.0`
  — Edit only the `version:` field at the top of the file
  — Do NOT add any new `agents:` entries (no new agent IDs created per Constitution Article IV)
  — Do NOT modify the `description:` field

---

## Category 6 — Quality Gate Checklists

- [X] **6.1** Verify that the `## Output Contract` section of `build-cycle-efcore-agent.md` now includes the 3 conditional MT output paths added in task 3.5
  — Expected keys: `per_bc_tenant_middleware`, `per_bc_tenant_resolver`, `per_bc_tenant_info`
  — All paths must use lowercase `{project_name}` (not `{PROJECT_NAME}`)

- [X] **6.2** [P] Verify that `coder-dotnet-backend.md` `## Multi-tenancy Scaffold Gate` section uses the correct config key path: `persistence.multi_tenancy.enabled` (NOT `persistence.multi_tenancy` as flat boolean)
  — This is the key correction from `research.md §1`

- [X] **6.3** [P] Verify all 3 template files contain `#nullable enable` at top and `using Finbuckle.MultiTenant` directives
  — These are Article II invariants for generated C# code in this codebase

---

## Category 7 — Acceptance Validation & QA Integration

Depends on Categories 2, 3, and 4.

- [X] **7.1** Run validation V6 from `quickstart.md`:
  ```powershell
  $agentPath = "src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-efcore-agent.md"
  $content = Get-Content $agentPath -Raw
  $checks = @{
      "Multi-tenant EF Core Setup heading" = $content -match "## Multi-tenant EF Core Setup"
      "Finbuckle.MultiTenant reference"     = $content -match "Finbuckle\.MultiTenant"
      "migration isolation note"            = $content -match "schema-per-tenant|MigrationInstructions"
  }
  $checks.GetEnumerator() | ForEach-Object { Write-Host "$(if($_.Value){'✅'}else{'❌'}) $($_.Key)" }
  ```
  — Expected: all 3 checks `✅`

- [X] **7.2** [P] Run validation V3 from `quickstart.md` against the TenantResolutionMiddleware template:
  ```powershell
  $tplPath = "src/modules/ava-fabric-agents/tech-stack/templates/multitenant/TenantResolutionMiddleware.cs.tpl"
  $content = Get-Content $tplPath -Raw
  $checks = @{
      "X-Tenant-Id header" = $content -match "X-Tenant-Id"
      "JWT claim tid"       = $content -match '"tid"'
      "400 on no tenant"    = $content -match "400|BadRequest"
  }
  $checks.GetEnumerator() | ForEach-Object { Write-Host "$(if($_.Value){'✅'}else{'❌'}) $($_.Key)" }
  ```
  — Expected: all 3 checks `✅`

- [X] **7.3** [P] Run validation V2 from `quickstart.md` against the AppDbContext template:
  ```powershell
  $tplPath = "src/modules/ava-fabric-agents/tech-stack/templates/multitenant/AppDbContext.multitenant.cs.tpl"
  $content = Get-Content $tplPath -Raw
  $checks = @{
      "EFCoreDbContext<TenantInfo>"    = $content -match "EFCoreDbContext<TenantInfo>"
      "IUnitOfWork"                    = $content -match "IUnitOfWork"
      "base.OnModelCreating first"     = $content -match "base\.OnModelCreating\(modelBuilder\)"
  }
  $checks.GetEnumerator() | ForEach-Object { Write-Host "$(if($_.Value){'✅'}else{'❌'}) $($_.Key)" }
  ```
  — Expected: all 3 checks `✅`

- [X] **7.4** [P] Run validation V5 (regression guard) — confirm that `coder-dotnet-backend.md` skips the MT gate when `multi_tenancy.enabled: false`:
  — Review the `## Multi-tenancy Scaffold Gate` section and confirm the guard clause `SE multi_tenancy.enabled: false (ou ausente): → PULAR esta seção` is present and unambiguous

---

## Category 8 — Documentation

Can run parallel with Category 7.

- [X] **8.1** [P] Add `CHANGELOG.md` entry:
  ```markdown
  ## [MINOR] 2026-07-08 — PBI 2309: multitenant-db-isolation

  ### Modified
  - `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-efcore-agent.md` v1.0.0 → v1.1.0
    — Added Step 1.2c (multi_tenancy config reads), Step 3.1-MT (Finbuckle DbContext variant),
      Finbuckle DI block in Step 3.6, and Step 7 (Multi-tenant EF Core Setup section)
  - `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md` v1.0.0 → v1.1.0
    — Added `## Multi-tenancy Scaffold Gate` section (generic pipeline mode)
  - `src/modules/ava-fabric-agents/tech-stack/module.yaml` v1.3.0 → v1.4.0

  ### Added
  - `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/TenantResolutionMiddleware.cs.tpl`
  - `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/AppDbContext.multitenant.cs.tpl`
  - `src/modules/ava-fabric-agents/tech-stack/templates/multitenant/KeyVaultTenantConnectionStringResolver.cs.tpl`
  ```

- [X] **8.2** [P] Check `docs/agents-catalog.md` for existing entries of `ava-coder-dotnet-backend` and `ava-build-cycle-efcore`
  — If entries exist: update `version` field and add one line to the description: "Suporta `persistence.multi_tenancy.enabled: true` — gera scaffolding Finbuckle.MultiTenant completo."
  — If entries do not exist: skip (no new agent to add)

---

## Completion Checklist

- [X] Category 1 complete — both agents' versions confirmed and bumped
- [X] Category 2 complete — 3 `.cs.tpl` template files created in `templates/multitenant/`
- [X] Category 3 complete — `build-cycle-efcore-agent.md` has Step 1.2c (incl. missing-package warning), Step 3.1-MT, Finbuckle DI in Step 3.6, and `## Multi-tenant EF Core Setup` section
- [X] Category 4 complete — `coder-dotnet-backend.md` has `## Multi-tenancy Scaffold Gate` section
- [X] Category 5 complete — `tech-stack/module.yaml` version bumped to `1.4.0`
- [X] Category 6 complete — Output Contract updated with 3 conditional MT paths (lowercase `{project_name}`)
- [X] Category 7 complete — all 4 PowerShell validation checks pass (V6, V3, V2, V5)
- [X] Category 8 complete — `CHANGELOG.md` entry added; `agents-catalog.md` updated if applicable
- [X] `research.md §1` correction applied — config key uses `persistence.multi_tenancy.enabled` (not flat boolean) in ALL modified files
- [X] Scenario 4 covered — task 3.6 warning path present in Step 1.2c of `build-cycle-efcore-agent.md`
- [X] `AgentResult` JSON marked N/A (added to spec §7 Exclusions — prompt files produce file artifacts, not structured JSON)

---

## Dependency Graph

```
Category 1 (version bumps + file reads)
    │
    ├──► Category 2 (template files)  ←── No dependencies
    │        │
    │        ├──► Category 3 (build-cycle-efcore modifications)
    │        │        └── 3.3, 3.4 read templates from Cat 2
    │        │
    │        └──► Category 4 (coder-dotnet-backend modification)
    │                 └── 4.1 reads templates from Cat 2
    │
    ├──► Category 5 (module.yaml bump)  ←── independent after Cat 1
    │
    └──── (after Cat 2+3+4+5)
              │
              ├──► Category 6 (quality gate verification)
              ├──► Category 7 (acceptance validation)  [parallel with Cat 6]
              └──► Category 8 (documentation)          [parallel with Cat 6+7]
```

## Parallel Execution Guide

| Round | Tasks | Parallelizable with |
|---|---|---|
| 1 | 1.1, 1.2 | Each other (different files) |
| 2 | 1.3, 1.4, 5.1 | All three (different files) |
| 3 | 2.1, then 2.2, 2.3, 2.4 | 2.2/2.3/2.4 parallel after 2.1 |
| 4 | 3.1, 3.2, 4.1 | All three (different files); 3.3–3.5 after 3.1–3.2 |
| 5 | 3.3, 3.4, 3.5 | 3.3/3.4 parallel; 3.5 after both |
| 6 | 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 7.4 | All parallel |
| 7 | 8.1, 8.2 | Both parallel |

## MVP Scope

All tasks are required to satisfy PBI 2309 acceptance criteria. The minimum viable change is:
- **Tasks 2.1–2.4** (template files) + **Task 3.5** (Step 7 in efcore agent) + **Task 1.3** (version bump)

This delivers the primary AC "Seção Multi-tenant EF Core Setup adicionada ao build-cycle-efcore-agent.md" and generates all 3 C# template files. Remaining tasks extend coverage to the generic pipeline mode and validate isolation.
