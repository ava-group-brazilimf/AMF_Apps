#nullable enable
// Multi-tenant variant — generated when persistence.multi_tenancy.enabled: true
// ⛔ GUARDRAIL: DO NOT add using Microsoft.EntityFrameworkCore — Infrastructure only

using System.Globalization;
using System.Security.Claims;
using Finbuckle.MultiTenant;
using Finbuckle.MultiTenant.Abstractions;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace {SolutionPrefix}.{BCName}.Infrastructure.Multitenancy;

/// <summary>
/// Resolves the current tenant from the HTTP request.
/// Resolution order:
///   1. X-Tenant-Id HTTP header
///   2. JWT claim "tid"
/// Returns 400 when no tenant identifier is present.
/// Returns 404 when the tenant identifier cannot be resolved.
/// </summary>
internal sealed class TenantResolutionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<TenantResolutionMiddleware> _logger;

    public TenantResolutionMiddleware(
        RequestDelegate next,
        ILogger<TenantResolutionMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(
        HttpContext context,
        IMultiTenantContextSetter multiTenantContextSetter,
        IMultiTenantStore<TenantInfo> tenantStore)
    {
        // Step 1: resolve tenant identifier from X-Tenant-Id header
        string? tenantId = context.Request.Headers["X-Tenant-Id"].FirstOrDefault();

        // Step 2: fallback to JWT claim "tid"
        if (string.IsNullOrEmpty(tenantId))
        {
            tenantId = context.User.FindFirst("tid")?.Value;
        }

        // Step 3: if no identifier present, return 400
        if (string.IsNullOrEmpty(tenantId))
        {
            _logger.LogWarning("Request received without tenant identifier (X-Tenant-Id header or tid claim).");
            context.Response.StatusCode = StatusCodes.Status400BadRequest;
            context.Response.ContentType = "application/problem+json";
            await context.Response.WriteAsync(
                """{"type":"https://tools.ietf.org/html/rfc7231#section-6.5.1","title":"Bad Request","status":400,"detail":"Tenant identifier required. Provide X-Tenant-Id header or tid JWT claim."}""",
                context.RequestAborted);
            return;
        }

        // Step 4: resolve TenantInfo from store
        TenantInfo? tenantInfo = await tenantStore.TryGetByIdentifierAsync(tenantId);
        if (tenantInfo is null)
        {
            _logger.LogWarning(
                "Tenant '{TenantId}' not found in store.",
                tenantId.ToString(CultureInfo.InvariantCulture));
            context.Response.StatusCode = StatusCodes.Status404NotFound;
            context.Response.ContentType = "application/problem+json";
            await context.Response.WriteAsync(
                string.Create(
                    CultureInfo.InvariantCulture,
                    $"{{\"type\":\"https://tools.ietf.org/html/rfc7231#section-6.5.4\",\"title\":\"Not Found\",\"status\":404,\"detail\":\"Tenant '{tenantId}' not found.\"}}"),
                context.RequestAborted);
            return;
        }

        // Step 5: set tenant context in DI scope and continue
        var multiTenantContext = new MultiTenantContext<TenantInfo> { TenantInfo = tenantInfo };
        multiTenantContextSetter.MultiTenantContext = multiTenantContext;

        await _next(context);
    }
}
