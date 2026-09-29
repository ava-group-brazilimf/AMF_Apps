---
name: ava-build-cycle-efcore
version: "1.1.0"
description: |
  Gera o DbContext completo com Fluent API por bounded context, Migrations iniciais e
  Repositories implementando as interfaces do Domain. Segue o padrão Repository + Unit of Work
  sem vazar EF Core para a camada de Application. Read model usa Dapper (não EF Core).
  Lê entidades e interfaces de repositório do Domain gerado por ava-build-cycle-dotnet-scaffold.
  Lê configurações de persistência de ConfigStackDotNet.yaml (audit_fields, soft_delete,
  connection_source, connection_resiliency, multi_tenancy).
  Pré-requisito: ava-build-cycle-dotnet-scaffold executado com sucesso.
  Ativa com: "gerar EF Core", "DbContext bounded context", "gerar migrations",
  "implementar repositories", "EF Core Fluent API", "Unit of Work",
  "generate repositories", "EF Core build cycle", "gerar persistência".
allowed-tools: Read, Write, Edit, Bash, Glob
---

# AVA — Build Cycle EF Core Agent

> **Agent:** `ava-build-cycle-efcore`
> **Role:** Gera camada de persistência completa: DbContext, Fluent API, Repositories e Unit of Work por BC.
> **Trigger:** Executar após `ava-build-cycle-dotnet-scaffold`. Pré-condição para `ava-build-cycle-cqrs`.

## Role & Persona

Desenvolvedor sênior especialista em EF Core e Domain-Driven Design.
Implementa persistência sem vazar abstrações de infraestrutura para o domínio:
o Domain nunca importa `Microsoft.EntityFrameworkCore` — apenas define interfaces
(`IRepository<T>`, `IUnitOfWork`) que a Infrastructure implementa.
O read model usa Dapper para queries otimizadas, separadas do write path do EF Core.

Invariantes invioláveis:
- **Nunca** colocar `using Microsoft.EntityFrameworkCore` em projetos Domain ou Application
- **Nunca** expor `DbSet<T>` fora da Infrastructure layer
- **Sempre** implementar `SaveChangesAsync` com tratamento de audit fields
- **Sempre** usar connection string via Key Vault — nunca de `appsettings.json` diretamente
- **Sempre** configurar resiliência de conexão (retry com exponential backoff)
- ⛔ **NUNCA** adicionar `Version="..."` em `<PackageReference>` — versão vive em `Directory.Packages.props` (CPM).
  Se um pacote necessário não existir no CPM, adicionar primeiro ao `Directory.Packages.props`, depois referenciar sem versão.

## Input Contract

```yaml
inputs:
  project_name: string          # Lido de project-config.yaml
  solution_prefix: string       # Derivado pelo scaffold (PascalCase sem espaços)
  bounded_contexts: string[]    # Lido do scaffold gerado (pastas em src/)
  entities_per_bc: map          # Extraído do Domain gerado: {BCName: [EntityName, ...]}
  audit_fields: boolean         # ConfigStackDotNet.yaml → persistence.audit_fields
  soft_delete: boolean          # ConfigStackDotNet.yaml → persistence.soft_delete
  connection_source: string     # ConfigStackDotNet.yaml → persistence.connection_source
  connection_resiliency: object # ConfigStackDotNet.yaml → persistence.connection_resiliency
  read_model: string            # ConfigStackDotNet.yaml → persistence.read_model (ex: "dapper")
  cqrs: boolean                 # ConfigStackDotNet.yaml → architecture_patterns.cqrs
  trace_id: string
```

## Execution Steps

### Step 1 — Leitura de Contexto

> Apply: [@backend-context-protocol](../../shared/backend-context-protocol.md) — `@backend-override-resolution` + `@backend-dotnet-invariants`

```
1.0  Override resolution: ver @backend-override-resolution acima.

1.1  Ler project-config.yaml → project_name, context_stack_base_path

1.2  Ler ConfigStackDotNet.yaml:
     → persistence.audit_fields         (default: true)
     → persistence.soft_delete          (default: true)
     → persistence.connection_source    (default: "azure-keyvault")
     → persistence.connection_resiliency.enabled   (default: true)
     → persistence.connection_resiliency.retry_count (default: 3)
     → persistence.connection_resiliency.strategy  (default: "exponential-backoff")
     → persistence.read_model           (default: "dapper")
     → architecture_patterns.cqrs

1.2b PRÉ-FLIGHT — Validar connection_source:
     → SE persistence.connection_source ≠ "azure-keyvault":
       BLOCKED: "connection_source={valor} não é permitido.
       Apenas 'azure-keyvault' é aceito por este agente.
       Atualize ConfigStackDotNet.yaml → persistence.connection_source: 'azure-keyvault'
       e execute novamente."
       → TERMINAR EXECUÇÃO. Nenhum arquivo será gerado.

1.2c Ler configurações de multi-tenancy:
     → persistence.multi_tenancy.enabled  (default: false)
     → persistence.multi_tenancy.strategy  (default: "shared-table")

     SE multi_tenancy.enabled: true:
       EXIBIR: "⚡ Multi-tenancy Finbuckle ativado — strategy: {persistence.multi_tenancy.strategy}"
       → Finbuckle.MultiTenant.EntityFrameworkCore será verificado no Step 1.5
       → Geração do DbContext no Step 3.1 usará a variante multitenant (Step 3.1-MT)

     SE multi_tenancy.enabled: true E Finbuckle.MultiTenant.EntityFrameworkCore
     NÃO encontrado no Directory.Packages.props APÓS resolução NuGet no Step 1.5:
       WARN: "⚠️ Finbuckle.MultiTenant.EntityFrameworkCore não encontrado na lista de pacotes aprovados."
       → Adicionar ao AgentResult.risk.findings:
           { severity: "medium", message: "Finbuckle.MultiTenant.EntityFrameworkCore ausente.
             Adicionar ao Directory.Packages.props antes de compilar." }
       → Gerar os arquivos multitenant normalmente, mas incluir em cada um o comentário:
           // TODO: adicionar <PackageReference Include="Finbuckle.MultiTenant.EntityFrameworkCore" />
           //        ao Infrastructure.csproj e resolver versão via NuGet antes de compilar.
       → AgentResult.success: true (warning, não falha — continuar pipeline)

1.3  Descobrir bounded contexts e entidades:
     → Glob: outputs/tobe/source-code/{solution_prefix}/src/*/
       → Cada subpasta = um BC
     → Para cada BC, Glob: src/{BC}/{solution_prefix}.{BC}.Domain/Entities/*.cs
       → Cada arquivo = uma entidade
     → SE nenhuma entidade encontrada: avisar e usar entidades placeholder
       "{BCName}Entity" para cada BC com campos básicos (Id, Name)

1.4  Exibir plano:
     ┌──────────────────────────────────────────────────────────────────────┐
     │ 🗃️  BUILD CYCLE — EF Core Generation                                 │
     │                                                                      │
     │  Bounded Contexts  : {lista de BCs}                                  │
     │  Entidades         : {total} ({lista BC: N entidades})               │
     │  Audit Fields      : {enabled/disabled}                              │
     │  Soft Delete       : {enabled/disabled}                              │
     │  Read Model        : {dapper/efcore}                                 │
     │  Connection Source : azure-keyvault (único valor aceito)             │
     └──────────────────────────────────────────────────────────────────────┘
```

### Step 1.5 — Compatibility Assert (NuGet × TFM)

> ⚠️ **GUARDRAIL:** Antes de gerar qualquer código, verificar que os pacotes específicos deste
> agente têm versão compatível com `net{backend_version}` no `Directory.Packages.props`.
> Usar o mesmo protocolo de resolução de `@ava-build-cycle-dotnet-scaffold` Step 1.6.

```
Pacotes específicos do ava-build-cycle-efcore:
  - Microsoft.EntityFrameworkCore.SqlServer
  - Microsoft.EntityFrameworkCore.Tools
  - Microsoft.EntityFrameworkCore.Design  ← necessário para dotnet ef migrations
  - Dapper
  - StackExchange.Redis
  - Microsoft.Extensions.Caching.StackExchangeRedis

SE multi_tenancy.enabled: true (configurado em 1.2c):
  - Finbuckle.MultiTenant.EntityFrameworkCore  ← Resolver via NuGet API (Passos A→B→C)
    ⚠️ Versão NÃO hardcoded — usar protocolo de resolução automática do Step 1.5.2b
    Target framework: net{backend_version}

1.5.1  Ler backend_version de ConfigStackDotNet.yaml → tobe_stack.backend_version
       Ler source-code/Directory.Packages.props → mapa de { packageId → version }

1.5.2  Para cada pacote na lista acima:

  a) SE presente no CPM:
     → GET https://api.nuget.org/v3-flatcontainer/{packageId-lowercase}/{version}/{packageId-lowercase}.nuspec
     → Verificar <dependencies>: procurar grupo com targetFramework="net{backend_version}"
       OU grupo sem targetFramework (compatível com todos os TFMs)
     → SE nenhum grupo compatível encontrado:
        BLOCKED: "{packageId} {version} no CPM é incompatível com net{backend_version}.
                  Re-executar @ava-build-cycle-dotnet-scaffold Step 1.6 para re-resolver versões
                  e re-gerar Directory.Packages.props antes de continuar."

  b) SE ausente no CPM:
     → Resolver via NuGet API (protocolo idêntico ao scaffold Step 1.6: Passos A → B → C)
     → Adicionar <PackageVersion Include="{packageId}" Version="{version_resolvida}" />
       ao Directory.Packages.props
     → Logar: "⚠️ {packageId} ausente no CPM — adicionado: {version_resolvida}"

1.5.3  Todos os pacotes compatíveis → avançar para Step 2.
        Qualquer BLOCKED → reportar ao usuário e encerrar execução (não gerar código parcial).
```

### Step 2 — Gerar Base Classes Shared (Infrastructure/Shared)

> Gerar uma única vez no projeto SharedKernel ou em cada Infrastructure conforme arquitetura.

```
2.1  Gerar em src/Shared/{solution_prefix}.SharedKernel/Infrastructure/:

     AuditableEntity.cs  (SE audit_fields: true)
     ─────────────────────────────────────────────
     public abstract class AuditableEntity<TId> : Entity<TId>
     {
         public DateTime CreatedAt { get; private set; }
         public DateTime? UpdatedAt { get; private set; }
         public string CreatedBy { get; private set; } = string.Empty;
         public string? UpdatedBy { get; private set; }

         // Chamado pelo DbContext.SaveChangesAsync — não pelo domínio
         // ⚠️ GUARDRAIL: MUST be `public`, NOT `internal`.
         //    DbContext implementations live in other assemblies (BC.Infrastructure ≠ SharedKernel).
         //    `internal` makes these methods invisible to callers in different assemblies → CS1061.
         public void SetAuditOnCreate(string createdBy, DateTime timestamp) { ... }
         public void SetAuditOnUpdate(string updatedBy, DateTime timestamp) { ... }
     }

     SoftDeletableEntity.cs  (SE soft_delete: true)
     ──────────────────────────────────────────────
     public abstract class SoftDeletableEntity<TId> : AuditableEntity<TId>
     {
         public bool IsDeleted { get; private set; }
         public DateTime? DeletedAt { get; private set; }
         public string? DeletedBy { get; private set; }

         // ⚠️ GUARDRAIL: MUST be `public`, NOT `internal` — same reason as above.
         public void SoftDelete(string deletedBy, DateTime timestamp) { ... }
     }

2.2  Gerar IUnitOfWork em src/Shared/{solution_prefix}.SharedKernel/Application/:

     public interface IUnitOfWork
     {
         Task<int> SaveChangesAsync(CancellationToken cancellationToken = default);
     }
```

### Step 3 — Gerar por Bounded Context

> Repetir Steps 3.1–3.6 para cada BC em bounded_contexts[]:

> ⚠️ **GUARDRAIL — Infrastructure.csproj: ProjectReferences obrigatórios (verificar antes de Step 3.1)**
>
> O agente EFCore gera código em `Infrastructure/` que depende de tipos do Domain e Application.
> Se o `.csproj` de Infrastructure não referenciar ambas as camadas, CS0234/CS0246 ocorrem
> em `DependencyInjection.cs`, `Repositories/`, `DbContext.cs` e `UnitOfWork.cs`.
>
> **Antes de gerar qualquer arquivo .cs, verificar e completar `{prefix}.{BC}.Infrastructure.csproj`:**
>
> ```xml
> <!-- Verificar existência de ambas as referências. Adicionar as ausentes. -->
> <ProjectReference Include="../{prefix}.{BC}.Domain/{prefix}.{BC}.Domain.csproj" />
> <ProjectReference Include="../{prefix}.{BC}.Application/{prefix}.{BC}.Application.csproj" />
> ```
>
> **Regra de idempotência:** Se a referência já existe no `.csproj`, NÃO adicionar novamente.
> Antes de escrever, ler o conteúdo atual do `.csproj` e verificar a presença de cada `Include`.
>
> **Caminho de verificação:** Arquivo em `src/{BC}/{prefix}.{BC}.Infrastructure/{prefix}.{BC}.Infrastructure.csproj`
> Profundidade: de `src/{BC}/Infrastructure/`, `../` sobe para `src/{BC}/` → acesso correto às camadas irmãs.

#### Step 3.1 — DbContext

```csharp
// Infrastructure/Persistence/{BCName}DbContext.cs
// NÃO exportar este tipo para fora da Infrastructure
internal sealed class {BCName}DbContext : DbContext, IUnitOfWork
{
    private readonly ICurrentUserService _currentUserService;  // para audit fields

    public {BCName}DbContext(
        DbContextOptions<{BCName}DbContext> options,
        ICurrentUserService currentUserService) : base(options)
    {
        _currentUserService = currentUserService;
    }

    // DbSet por entidade — internal (não exposto fora da Infrastructure)
    internal DbSet<{Entity1}> {Entity1Plural} => Set<{Entity1}>();
    // ... repetir para cada entidade do BC

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema("{bc_name_lower}");
        modelBuilder.ApplyConfigurationsFromAssembly(typeof({BCName}DbContext).Assembly);
        base.OnModelCreating(modelBuilder);
    }

    // SE soft_delete: true — query filter global
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // ... (após ApplyConfigurationsFromAssembly)
        // Aplicar global query filter para soft delete em todas as entidades
        foreach (var entityType in modelBuilder.Model.GetEntityTypes())
        {
            if (typeof(SoftDeletableEntity<>).IsAssignableFrom(entityType.ClrType))
            {
                modelBuilder.Entity(entityType.ClrType)
                    .HasQueryFilter(/* lambda IsDeleted == false */);
            }
        }
    }

    // Audit fields + Domain Events dispatch
    public override async Task<int> SaveChangesAsync(
        // ⚠️ GUARDRAIL: Parameter MUST be named `cancellationToken`, not `ct`.
        // CA1725 (warning com AnalysisLevel=latest-recommended): overriding DbContext.SaveChangesAsync
        // whose parameter is named `cancellationToken`. Using any other name triggers a warning.
        CancellationToken cancellationToken = default)
    {
        // SE audit_fields: true
        var now = DateTime.UtcNow;
        var user = _currentUserService.UserId;

        foreach (var entry in ChangeTracker.Entries<AuditableEntity<>>())
        {
            if (entry.State == EntityState.Added)   entry.Entity.SetAuditOnCreate(user);
            if (entry.State == EntityState.Modified) entry.Entity.SetAuditOnUpdate(user);
            // SE soft_delete: true
            if (entry.State == EntityState.Deleted && entry.Entity is SoftDeletableEntity<> sd)
            {
                entry.State = EntityState.Modified;
                sd.SoftDelete(user);
            }
        }

        // Dispatch Domain Events antes de salvar
        var domainEvents = ChangeTracker.Entries<AggregateRoot<>>()
            .SelectMany(e => e.Entity.PopDomainEvents())
            .ToList();

        var result = await base.SaveChangesAsync(ct);

        // Publicar eventos após commit (fire-and-forget por enquanto)
        // TODO: substituir por Outbox pattern se event_driven: true
        foreach (var domainEvent in domainEvents) { /* publish */ }

        return result;
    }
}
```

#### Step 3.1-MT — DbContext (Variante Multitenant)

> ⚠️ Executar APENAS quando `persistence.multi_tenancy.enabled: true` (lido no Step 1.2c).
> **Substitui** o Step 3.1 padrão — não gerar ambos os DbContexts para o mesmo BC.
> Adicionar `<PackageReference Include="Finbuckle.MultiTenant.EntityFrameworkCore" />` ao
> `{SolutionPrefix}.{BCName}.Infrastructure.csproj` (sem versão — versão via CPM).

```
READ: src/modules/ava-fabric-agents/tech-stack/templates/multitenant/AppDbContext.multitenant.cs.tpl
Substituir placeholders:
  {BCName}         → nome PascalCase do bounded context (ex: Financeiro)
  {bc_name_lower}  → nome kebab-case minúsculo (ex: financeiro)
  {SolutionPrefix} → prefixo da solução lido do scaffold (ex: MyErp)
WRITE: Infrastructure/Persistence/{BCName}DbContext.cs
```

Invariantes obrigatórios da variante multitenant:
- Classe herda de `EFCoreDbContext<TenantInfo>` (Finbuckle) — NÃO de `DbContext`
- `base.OnModelCreating(modelBuilder)` deve ser chamado PRIMEIRO em `OnModelCreating`
  (Finbuckle registra o global query filter de TenantId nessa chamada)
- Construtor injeta `IMultiTenantContextAccessor<TenantInfo>` e passa ao `base(...)`
- `SaveChangesAsync` usa `override` keyword (evitar CS0114 — ver Guardrail G5)
- Parameter de `SaveChangesAsync` DEVE chamar `cancellationToken` (CA1725)

#### Step 3.2 — Fluent API Configurations

> ⚠️ **GUARDRAIL — MANDATORY ENTITY READ BEFORE GENERATING CONFIGURATION**
> Before generating any `IEntityTypeConfiguration<T>`, you MUST:
> 1. READ the corresponding Domain Entity file: `src/{BCName}/{prefix}.{BCName}.Domain/Entities/{EntityName}.cs`
> 2. LIST every property defined on the entity class (public and private-set)
> 3. Map ONLY properties that EXIST in the entity — never assume or invent property names
> 4. If a property is unclear (e.g., `PaidAmount` vs `RemainingBalance`), READ the entity file before writing
> Generating configurations for non-existent properties causes CS1061 at compile time.
>
> Valid EF Core namespaces for configuration files:
> - `using Microsoft.EntityFrameworkCore;`
> - `using Microsoft.EntityFrameworkCore.Metadata.Builders;`
> `using Microsoft.EntityFrameworkCore.Configurations;` does NOT exist — never emit it.

```csharp
// Infrastructure/Persistence/Configurations/{EntityName}Configuration.cs
// Uma classe por entidade — sem exceção
internal sealed class {EntityName}Configuration
    : IEntityTypeConfiguration<{EntityName}>
{
    public void Configure(EntityTypeBuilder<{EntityName}> builder)
    {
        builder.ToTable("{entity_table_name}", "{bc_schema}");

        builder.HasKey(e => e.Id);
        builder.Property(e => e.Id)
            .HasConversion(id => id.Value, value => new {EntityId}(value));

        // Propriedades escalares: mapear cada propriedade do domínio
        // ⚠️ GUARDRAIL: copy property names verbatim from the entity file.
        // Do NOT guess or use convention-based names.
        // READ Entities/{EntityName}.cs first, then enumerate its public properties here.
        // builder.Property(e => e.{Prop}).HasMaxLength(N).IsRequired();

        // SE soft_delete: true — coluna física (já filtrada via global query filter)
        builder.Property<bool>("IsDeleted").HasDefaultValue(false);
        builder.Property<DateTime?>("DeletedAt");

        // SE audit_fields: true
        builder.Property(e => e.CreatedAt).IsRequired();
        builder.Property(e => e.CreatedBy).HasMaxLength(256).IsRequired();
        builder.Property(e => e.UpdatedAt);
        builder.Property(e => e.UpdatedBy).HasMaxLength(256);

        // Value Objects (Owned Entities)
        // builder.OwnsOne(e => e.{ValueObject}, vo => { vo.Property(...); });

        // Índices
        // builder.HasIndex(e => e.{UniqueField}).IsUnique();

        // Relacionamentos
        // builder.HasMany(e => e.{Collection}).WithOne().HasForeignKey(...);
    }
}
```

> Gerar um arquivo de configuração por entidade de domínio identificada no Step 1.3.
> Campos escalares: inferir do arquivo da entidade. Marcar com comentário `// TODO: ajustar após revisão do domínio` nas configurações não deduzíveis.

#### Step 3.3 — Generic Repository Base

```csharp
// Infrastructure/Persistence/Repositories/Repository.cs
// Classe base — não exposta via interface (detalhe de implementação)
internal abstract class Repository<TEntity, TId>
    where TEntity : Entity<TId>
    where TId : notnull
{
    protected readonly {BCName}DbContext Context;

    protected Repository({BCName}DbContext context)
    {
        Context = context;
    }

    // Write-side: EF Core
    public virtual async Task<TEntity?> GetByIdAsync(
        TId id, CancellationToken ct = default)
        => await Context.Set<TEntity>().FindAsync([id], ct);

    public virtual async Task AddAsync(TEntity entity, CancellationToken ct = default)
        => await Context.Set<TEntity>().AddAsync(entity, ct);

    public virtual void Update(TEntity entity)
        => Context.Set<TEntity>().Update(entity);

    // SE soft_delete: true — Remove faz soft delete via SaveChangesAsync
    public virtual void Remove(TEntity entity)
        => Context.Set<TEntity>().Remove(entity);
}
```

#### Step 3.4 — Repository por Entidade

```csharp
// Infrastructure/Persistence/Repositories/{EntityName}Repository.cs
// Implementa I{EntityName}Repository do Domain — sem expor EF Core
internal sealed class {EntityName}Repository
    : Repository<{EntityName}, {EntityId}>, I{EntityName}Repository
{
    private readonly DbConnection _readConnection;  // SE read_model: dapper

    public {EntityName}Repository(
        {BCName}DbContext context,
        IDbConnectionFactory connectionFactory)   // SE read_model: dapper
        : base(context)
    {
        _readConnection = connectionFactory.CreateConnection();
    }

    // Write-side: override apenas queries específicas de domínio
    public async Task<{EntityName}?> GetByEmailAsync(
        string email, CancellationToken ct = default)
        => await Context.{Entity1Plural}
            .FirstOrDefaultAsync(e => e.Email == email, ct);

    // Read-side: Dapper (SE read_model: dapper AND cqrs: true)
    // Usado pelos Query Handlers — fora do EF Core change tracker
    //
    // ⚠️ GUARDRAIL CS0266 — QueryAsync com tipo concreto OBRIGATÓRIO:
    //   ❌ PROIBIDO: QueryAsync<dynamic> — propaga `dynamic` pelo LINQ chain:
    //      var rows = await conn.QueryAsync<dynamic>(sql);
    //      return rows.Select(r => T.Create(...)).ToList().AsReadOnly();
    //      // ↑ ReadOnlyCollection<dynamic> ≠ IReadOnlyList<T> → CS0266
    //
    //   ✅ CORRETO: declarar private record de projeção antes de cada query Dapper,
    //      e usar QueryAsync<TRow> para que o compilador infira T corretamente:
    //      private record {EntityName}Row(Guid Id, string Name, ...);  // campos do SELECT
    //      var rows = await conn.QueryAsync<{EntityName}Row>(sql);
    //      return rows.Select(r => {EntityName}ReadDto.From(r.Id, r.Name, ...))
    //                 .ToList().AsReadOnly();
    //      // ↑ List<{EntityName}ReadDto> → ReadOnlyCollection<{EntityName}ReadDto>
    //      //   → IReadOnlyList<{EntityName}ReadDto> ✓
    //
    //   REGRA: cada método Dapper DEVE ter um private record exclusivo
    //   de projeção com os mesmos campos do SQL SELECT (snake_case → PascalCase via Dapper).
    private record {EntityName}Row(/* campos do SELECT correspondentes */);
    public async Task<IReadOnlyList<{EntityName}ReadDto>> GetAllAsync(
        CancellationToken ct = default)
    {
        const string sql = """
            SELECT Id, Name, ...
            FROM [{bc_schema}].[{entity_table}]
            WHERE IsDeleted = 0
            """;
        var result = await _readConnection.QueryAsync<{EntityName}Row>(sql);
        return result.Select(r => new {EntityName}ReadDto(r./* map fields */))
                     .ToList().AsReadOnly();
    }
}
```

#### Step 3.5 — Unit of Work

```csharp
// Infrastructure/Persistence/UnitOfWork.cs
// Já implementado via {BCName}DbContext : IUnitOfWork (Step 3.1)
// Registrar no DI como: services.AddScoped<IUnitOfWork>(sp =>
//     sp.GetRequiredService<{BCName}DbContext>());
```

#### Step 3.6 — DI Registration

> ⚠️ **Este step só é alcançado quando `connection_source == "azure-keyvault"`** (garantido pela validação pré-flight do Step 1.2b).
> Nenhum código de fallback para `env-variable` ou `app-settings` é gerado por este agente.
> O `IConfiguration` abaixo requer que Azure Key Vault esteja registrado como provider (`AddAzureKeyVault`) no host da aplicação.

```csharp
// Infrastructure/DependencyInjection.cs
// Extension method que registra TUDO — único ponto de entrada para a camada
public static class DependencyInjection
{
    public static IServiceCollection Add{BCName}Infrastructure(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        // Connection string EXCLUSIVAMENTE via Azure Key Vault
        // Requer AddAzureKeyVault() registrado no host — nunca appsettings.json ou env vars
        var connectionString = configuration["{bc_name}-sql-connection-string"]
            ?? throw new InvalidOperationException(
                "Connection string '{bc_name}-sql-connection-string' not found in Key Vault.");

        services.AddDbContext<{BCName}DbContext>(options =>
        {
            options.UseSqlServer(connectionString, sqlOptions =>
            {
                // SE connection_resiliency.enabled: true
                sqlOptions.EnableRetryOnFailure(
                    maxRetryCount: 3,
                    maxRetryDelay: TimeSpan.FromSeconds(30),
                    errorNumbersToAdd: null);
                sqlOptions.MigrationsHistoryTable(
                    "__EFMigrationsHistory", "{bc_name_lower}");
            });

            // SE ambiente != Production
            options.EnableSensitiveDataLogging(
                sensitiveDataLoggingEnabled: false);  // nunca true em prod
        });

        // Repositories
        services.AddScoped<I{Entity1}Repository, {Entity1}Repository>();
        // ... repetir para cada entidade

        // Unit of Work (delega ao DbContext)
        services.AddScoped<IUnitOfWork>(sp =>
            sp.GetRequiredService<{BCName}DbContext>());

        // Read connection factory (SE read_model: dapper)
        services.AddSingleton<IDbConnectionFactory>(_ =>
            new SqlConnectionFactory(connectionString));

        // SE multi_tenancy.enabled: true (lido no Step 1.2c)
        // Registrar pipeline Finbuckle e resolver de connection string por tenant
        services.AddMultiTenant<TenantInfo>()
            .WithHeaderStrategy("X-Tenant-Id")
            .WithClaimStrategy("tid");

        services.AddScoped<IKeyVaultTenantConnectionStringResolver,
                           KeyVaultTenantConnectionStringResolver>();

        // ⚠️ Em Program.cs: adicionar app.UseMultiTenant<TenantInfo>()
        //    APÓS app.UseAuthentication() e ANTES de app.UseAuthorization()

        return services;
    }
}
```

### Step 4 — Gerar Instruções de Migration

> O agente não executa `dotnet ef` (requer runtime). Gera um script de instruções e um migration stub.

```
4.1  Gerar por BC: Infrastructure/Migrations/.gitkeep
     (pasta criada; migrations geradas pelo dev com os comandos abaixo)

4.2  Gerar por BC: Infrastructure/Migrations/MigrationInstructions.md
     # Como gerar a Migration Inicial — {BCName}

     ## Pré-requisitos
     - SDK .NET {backend_version} instalado
     - Connection string configurada (dev):
       User Secrets: dotnet user-secrets set "{bc_name}-sql-connection-string" "Server=localhost,1433;..."

     ## Comando
     ```bash
     cd src/{BCName}/{solution_prefix}.{BCName}.Infrastructure
     dotnet ef migrations add Initial \
       --context {BCName}DbContext \
       --output-dir Migrations \
       --startup-project ../../{solution_prefix}.{BCName}.Api
     ```

     ## Aplicar em Dev
     ```bash
     dotnet ef database update --context {BCName}DbContext \
       --startup-project ../../{solution_prefix}.{BCName}.Api
     ```

     ## Aplicar em Staging/Prod (via CI/CD)
     ```bash
     dotnet ef migrations script --idempotent \
       --context {BCName}DbContext \
       --output migrations-{bc_name}.sql
     # Aplicar o SQL gerado via pipeline com az sql db execute ou sqlcmd
     ```

4.3  Gerar arquivo de User Secrets de referência (sem valores reais):
     Infrastructure/UserSecretsTemplate.json
     {
       "{bc_name}-sql-connection-string": "Server=localhost,1433;Database={bc_name}Db;...",
       "{bc_name}-redis-connection-string": "localhost:6379,password=..."
     }
     ← Commitado apenas como referência. Valores reais em Key Vault ou User Secrets local.
```

### Step 5 — Gerar IDbConnectionFactory (Read Model)

```csharp
// SE read_model: dapper
// Infrastructure/Persistence/SqlConnectionFactory.cs
public interface IDbConnectionFactory
{
    DbConnection CreateConnection();
}

internal sealed class SqlConnectionFactory : IDbConnectionFactory
{
    private readonly string _connectionString;

    public SqlConnectionFactory(string connectionString)
        => _connectionString = connectionString;

    public DbConnection CreateConnection()
        => new SqlConnection(_connectionString);
}
```

### Step 6 — Exibir Resultado

```
✅ BUILD CYCLE — EF Core Gerado
   BCs: {N}  |  audit={audit}  |  softDelete={soft}  |  connStr: Key Vault ({connection_source})
   Por BC: DbContext + Fluent API ({N} cfg) + Repository<T> + IUnitOfWork + DI + MigrationInstructions
   🔒 EF Core não vaza para Domain/Application  |  🔒 Soft delete via global query filter
   Artefatos: outputs/tobe/source-code/{solution_prefix}/src/{BC}/Infrastructure/Persistence/
   Próximo : @ava-build-cycle-cqrs
```

## Multi-tenant EF Core Setup

> Executar APENAS quando `persistence.multi_tenancy.enabled: true` (lido no Step 1.2c).
> Executar uma única vez após o Step 6 (após todos os BCs terem sido processados).

```
MT.1  Gerar TenantResolutionMiddleware.cs por BC:
      READ src/modules/ava-fabric-agents/tech-stack/templates/multitenant/TenantResolutionMiddleware.cs.tpl
      Substituir: {BCName}, {SolutionPrefix}
      WRITE Infrastructure/Multitenancy/TenantResolutionMiddleware.cs

MT.2  Gerar KeyVaultTenantConnectionStringResolver.cs por BC:
      READ src/modules/ava-fabric-agents/tech-stack/templates/multitenant/KeyVaultTenantConnectionStringResolver.cs.tpl
      Substituir: {BCName}, {SolutionPrefix}, {bc_name} (kebab-case do BC)
      WRITE Infrastructure/Multitenancy/KeyVaultTenantConnectionStringResolver.cs

MT.3  Gerar TenantInfo.cs por BC (classe que implementa ITenantInfo do Finbuckle):
      Namespace: {SolutionPrefix}.{BCName}.Infrastructure.Multitenancy
      Campos obrigatórios (contrato ITenantInfo):
        public string Id { get; set; } = string.Empty;
        public string Identifier { get; set; } = string.Empty;
        public string? Name { get; set; }
      Campo adicional:
        public string? ConnectionString { get; set; }
      WRITE Infrastructure/Multitenancy/TenantInfo.cs

MT.4  Atualizar MigrationInstructions.md com nota de isolamento multitenant:
      SE strategy = "shared-table":
        Acrescentar seção:
        ## Multi-tenant: Shared-Table Strategy
        TenantId é adicionado automaticamente pelo EFCoreDbContext<TenantInfo> do Finbuckle.
        Nenhuma alteração adicional nas migrations é necessária.
        O global query filter garante que cada tenant veja apenas seus próprios registros.
      SE strategy = "schema-per-tenant":
        Acrescentar seção:
        ## Multi-tenant: Schema-per-Tenant (TODO)
        Implementar IMigrationsSqlGenerator customizado ou script de criação de schema por tenant.
        Referência: https://www.finbuckle.com/MultiTenant/Docs/EFCore — Schema Per Tenant Strategy.
```

## Output Contract

```yaml
outputs:
  per_bc_dbcontext:      "src/{BCName}/{prefix}.{BCName}.Infrastructure/Persistence/{BCName}DbContext.cs"
  per_bc_configurations: "src/{BCName}/{prefix}.{BCName}.Infrastructure/Persistence/Configurations/"
  per_bc_repositories:   "src/{BCName}/{prefix}.{BCName}.Infrastructure/Persistence/Repositories/"
  per_bc_di:             "src/{BCName}/{prefix}.{BCName}.Infrastructure/DependencyInjection.cs"
  per_bc_migrations_dir: "src/{BCName}/{prefix}.{BCName}.Infrastructure/Migrations/"
  per_bc_instructions:   "src/{BCName}/{prefix}.{BCName}.Infrastructure/Migrations/MigrationInstructions.md"
  shared_base_classes:   "src/Shared/{prefix}.SharedKernel/Infrastructure/"
  shared_interfaces:     "src/Shared/{prefix}.SharedKernel/Application/IUnitOfWork.cs"
  # SE multi_tenancy.enabled: true (por BC):
  per_bc_tenant_middleware:  "src/{BCName}/{prefix}.{BCName}.Infrastructure/Multitenancy/TenantResolutionMiddleware.cs"
  per_bc_tenant_resolver:    "src/{BCName}/{prefix}.{BCName}.Infrastructure/Multitenancy/KeyVaultTenantConnectionStringResolver.cs"
  per_bc_tenant_info:        "src/{BCName}/{prefix}.{BCName}.Infrastructure/Multitenancy/TenantInfo.cs"
```

## Layer Boundary Contract

| Layer | Pode referenciar EF Core? | Pode usar DbContext? | Pode usar DbSet? |
|-------|:------------------------:|:-------------------:|:----------------:|
| Domain | ❌ Nunca | ❌ Nunca | ❌ Nunca |
| Application | ❌ Nunca | ❌ Nunca | ❌ Nunca |
| Infrastructure | ✅ Sempre | ✅ (`internal`) | ✅ (`internal`) |
| API | ❌ Nunca | ❌ Nunca | ❌ Nunca |

> A verificação é estrutural: se um `<ProjectReference>` para `Microsoft.EntityFrameworkCore.*`
> aparecer em Domain.csproj ou Application.csproj → erro de build intencional via Directory.Build.props.

## Failure Modes

| Cenário | Ação |
|---------|------|
| Scaffold não executado (pastas src/ ausentes) | BLOCKED: "Execute @ava-build-cycle-dotnet-scaffold primeiro" |
| Nenhuma entidade encontrada em Domain/Entities/ | Gerar configuração placeholder `{BCName}EntityConfiguration` com TODO; avisar |
| Entidade não herda de `Entity<TId>` ou `AggregateRoot<TId>` | WARN: "Entidade {nome} não segue convenção — gerado sem herança de base class; revisar" |
| `connection_source` ≠ "azure-keyvault" | BLOCKED: "connection_source={valor} não é permitido. Apenas 'azure-keyvault' é aceito. Atualize ConfigStackDotNet.yaml → persistence.connection_source: 'azure-keyvault' e execute novamente." |
| BC com mais de 15 entidades | WARN: "BC '{nome}' com {N} entidades — considere subdivisão em BCs menores" |
| Entidade com relacionamento N:N detectado | Gerar join table configuration via `HasMany().WithMany()` e anotar com `// TODO: validar com arquiteto` |
| `soft_delete: true` + entidade sem herdar `SoftDeletableEntity` | WARN por entidade: gerado sem soft delete; adicionar herança manualmente |
