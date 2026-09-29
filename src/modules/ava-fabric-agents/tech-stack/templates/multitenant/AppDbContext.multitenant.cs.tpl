#nullable enable
// Multi-tenant variant — generated when persistence.multi_tenancy.enabled: true
// ⚠️ GUARDRAIL: base.OnModelCreating(modelBuilder) MUST be called FIRST — Finbuckle
//    registers its global TenantId query filter there. Any filters added before the
//    base call will be overwritten.

using Finbuckle.MultiTenant;
using Finbuckle.MultiTenant.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace {SolutionPrefix}.{BCName}.Infrastructure.Persistence;

/// <summary>
/// EF Core DbContext for {BCName} bounded context — multitenant variant.
/// Inherits EFCoreDbContext&lt;TenantInfo&gt; (Finbuckle) which applies a global
/// TenantId query filter automatically to all entities implementing ITenantInfo.
/// </summary>
internal sealed class {BCName}DbContext : EFCoreDbContext<TenantInfo>, IUnitOfWork
{
    private readonly ICurrentUserService _currentUserService;

    public {BCName}DbContext(
        DbContextOptions<{BCName}DbContext> options,
        ICurrentUserService currentUserService,
        IMultiTenantContextAccessor<TenantInfo> multiTenantContextAccessor)
        : base(options, multiTenantContextAccessor)
    {
        _currentUserService = currentUserService;
    }

    // DbSet per entity — internal so EF Core does not leak outside Infrastructure
    // internal DbSet<{Entity1}> {Entity1Plural} => Set<{Entity1}>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // ⚠️ MUST call base FIRST — Finbuckle registers TenantId global filter here
        base.OnModelCreating(modelBuilder);

        modelBuilder.HasDefaultSchema("{bc_name_lower}");
        modelBuilder.ApplyConfigurationsFromAssembly(typeof({BCName}DbContext).Assembly);

        // SE soft_delete: true — apply global query filter for soft-delete
        // foreach (var entityType in modelBuilder.Model.GetEntityTypes())
        // {
        //     if (typeof(SoftDeletableEntity<>).IsAssignableFrom(entityType.ClrType))
        //     {
        //         // HasQueryFilter — IsDeleted == false
        //     }
        // }
    }

    /// <inheritdoc />
    // ⚠️ GUARDRAIL G5 (CS0114): override keyword is required — DbContext already declares
    //    SaveChangesAsync. Omitting 'override' causes CS0114 with TreatWarningsAsErrors=true.
    public override async Task<int> SaveChangesAsync(
        // ⚠️ GUARDRAIL: parameter name MUST be `cancellationToken` (CA1725 — override contract)
        CancellationToken cancellationToken = default)
    {
        // SE audit_fields: true — stamp created/updated timestamps and user
        var now = DateTime.UtcNow;
        var userId = _currentUserService.UserId;

        foreach (var entry in ChangeTracker.Entries<AuditableEntity<>>())
        {
            if (entry.State == EntityState.Added)
                entry.Entity.SetAuditOnCreate(userId, now);

            if (entry.State == EntityState.Modified)
                entry.Entity.SetAuditOnUpdate(userId, now);

            // SE soft_delete: true
            if (entry.State == EntityState.Deleted && entry.Entity is SoftDeletableEntity<> sd)
            {
                entry.State = EntityState.Modified;
                sd.SoftDelete(userId, now);
            }
        }

        // Dispatch Domain Events before saving
        var domainEvents = ChangeTracker.Entries<AggregateRoot<>>()
            .SelectMany(e => e.Entity.PopDomainEvents())
            .ToList();

        var result = await base.SaveChangesAsync(cancellationToken);

        // TODO: replace with Outbox pattern when event_driven: true
        foreach (var domainEvent in domainEvents) { /* publish */ }

        return result;
    }
}
