#nullable enable
// Multi-tenant variant — generated when persistence.multi_tenancy.enabled: true
// ⛔ GUARDRAIL: DO NOT add using Microsoft.EntityFrameworkCore — Infrastructure only

using Azure;
using Azure.Security.KeyVault.Secrets;
using Microsoft.Extensions.Caching.Memory;

namespace {SolutionPrefix}.{BCName}.Infrastructure.Multitenancy;

/// <summary>
/// Resolves per-tenant database connection strings from Azure Key Vault.
/// Key Vault secret naming convention: {tenantId}--{bcName}-sql-connection-string
/// Connection strings are cached for 5 minutes to avoid repeated Key Vault calls.
/// </summary>
public interface IKeyVaultTenantConnectionStringResolver
{
    /// <summary>
    /// Resolves the SQL connection string for the given tenant and bounded context.
    /// </summary>
    Task<string> ResolveAsync(string tenantId, string bcName, CancellationToken ct = default);
}

internal sealed class KeyVaultTenantConnectionStringResolver : IKeyVaultTenantConnectionStringResolver
{
    private static readonly TimeSpan CacheTtl = TimeSpan.FromMinutes(5);

    private readonly SecretClient _secretClient;
    private readonly IMemoryCache _cache;

    public KeyVaultTenantConnectionStringResolver(
        SecretClient secretClient,
        IMemoryCache cache)
    {
        _secretClient = secretClient;
        _cache = cache;
    }

    /// <inheritdoc />
    public async Task<string> ResolveAsync(
        string tenantId,
        string bcName,
        CancellationToken ct = default)
    {
        // Step 1: build cache key
        var cacheKey = $"connstr:{tenantId}:{bcName}";

        // Step 2: return from cache if present
        if (_cache.TryGetValue(cacheKey, out string? cached) && cached is not null)
        {
            return cached;
        }

        // Step 3: build Key Vault secret name
        // Convention: {tenantId}--{bcName}-sql-connection-string
        // Double-dash (--) is the Key Vault hierarchical separator.
        var secretName = $"{tenantId}--{bcName}-sql-connection-string";

        // Step 4: fetch from Key Vault
        Response<KeyVaultSecret> response = await _secretClient.GetSecretAsync(
            secretName,
            version: null,
            cancellationToken: ct);

        var connectionString = response.Value.Value
            ?? throw new InvalidOperationException(
                $"Key Vault secret '{secretName}' resolved to null.");

        // Step 5: cache the result
        _cache.Set(cacheKey, connectionString, CacheTtl);

        return connectionString;
    }
}
