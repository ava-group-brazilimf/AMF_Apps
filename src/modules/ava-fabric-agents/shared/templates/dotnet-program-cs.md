# Program.cs — Template Canônico (.NET Minimal APIs + Carter)

> **Uso:** Referenciado por `@ava-build-cycle-minimal-apis` (Step 2).  
> Substitua `{BCName}`, `{prefix}`, `{bc_name}`, `{solution_prefix}` pelos valores do contexto efetivo.

```csharp
// src/{BCName}/{prefix}.{BCName}.Api/Program.cs
var builder = WebApplication.CreateBuilder(args);

// ── § 1. Configuration ────────────────────────────────────────────────────
builder.Configuration
    .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
    .AddJsonFile($"appsettings.{builder.Environment.EnvironmentName}.json", optional: true)
    .AddEnvironmentVariables();   // env vars override appsettings (CI/CD, containers)

// Azure Key Vault — only loaded in non-Development environments.
// In Development, secrets come from environment variables or user-secrets.
// NEVER add secrets to appsettings.json / appsettings.Development.json.
if (!builder.Environment.IsDevelopment())
{
    var keyVaultUri = builder.Configuration["KeyVaultUri"]
        ?? throw new InvalidOperationException(
            "KeyVaultUri is required in non-Development environments. "
            + "Set the KeyVaultUri environment variable or appsettings value.");
    builder.Configuration.AddAzureKeyVault(
        new Uri(keyVaultUri),
        new DefaultAzureCredential());
}

// ── § 2. Authentication — JWT Bearer via Azure AD (MSAL) ─────────────────
builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddMicrosoftIdentityWebApi(builder.Configuration.GetSection("AzureAd"));

// ── § 3. Authorization ────────────────────────────────────────────────────
builder.Services.AddAuthorization(options =>
{
    // Policy padrão: usuário autenticado
    options.FallbackPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build();

    // Policies específicas por papel — adicionar conforme spec.md
    // options.AddPolicy("Admin", policy => policy.RequireRole("admin"));
});

// ── § 4. Application + Infrastructure ────────────────────────────────────
builder.Services
    .Add{BCName}Application()       // MediatR, Behaviors, Validators
    .Add{BCName}Infrastructure(builder.Configuration);  // DbContext, Repos, Redis

// ── § 5. Carter (Minimal APIs routing) ───────────────────────────────────
builder.Services.AddCarter();

// ── § 6. OpenAPI ──────────────────────────────────────────────────────────
// ⛔ GUARDRAIL: Use AddOpenApi (Microsoft.AspNetCore.OpenApi) — NOT AddSwaggerGen (Swashbuckle).
// Swashbuckle.AspNetCore is incompatible with Microsoft.OpenApi 2.0 required by .NET 10+.
builder.Services.AddOpenApi("v1", options =>
{
    options.AddDocumentTransformer((doc, ctx, _) =>
    {
        doc.Info = new()
        {
            Title = "{solution_prefix} — {BCName} API",
            Version = "v1",
            Description = "API do bounded context {BCName}."
        };
        return Task.CompletedTask;
    });
    // JWT Bearer no Scalar/OpenAPI UI
    options.AddDocumentTransformer<BearerSecuritySchemeTransformer>();
});

// ── § 7. Observabilidade ──────────────────────────────────────────────────
// ⚠️ GUARDRAIL: Use AddApplicationInsightsTelemetry (options-lambda overload).
// The string overload is [Obsolete] in v2.22+ and fails TreatWarningsAsErrors builds.
// ⚠️ GUARDRAIL: If you instead use UseAzureMonitor() from Azure.Monitor.OpenTelemetry.AspNetCore:
//   1. Add `using Azure.Monitor.OpenTelemetry.AspNetCore;` at the top of Program.cs
//   2. Guard the call — it throws InvalidOperationException if the connection string is absent:
//        var appInsightsConn = builder.Configuration["APPLICATIONINSIGHTS_CONNECTION_STRING"];
//        if (!string.IsNullOrEmpty(appInsightsConn)) builder.Services.UseAzureMonitor();
//   Do NOT call UseAzureMonitor() unconditionally in local/dev environments.
builder.Services.AddApplicationInsightsTelemetry(options =>
    options.ConnectionString = builder.Configuration["APPLICATIONINSIGHTS_CONNECTION_STRING"]);
builder.Logging.AddApplicationInsights();

// ── § 8. Health Checks ───────────────────────────────────────────────────
builder.Services.AddHealthChecks()
    // ⚠️ GUARDRAIL: Do NOT use named parameters (name: ...) for AddSqlServer.
    // The AspNetCore.HealthChecks.SqlServer package overload signatures changed;
    // passing name: as a named argument causes CS1739 (no parameter named 'name')
    // on some package versions. Use positional or omit the name argument.
    .AddSqlServer(
        builder.Configuration["{bc_name}-sql-connection-string"]!,
        tags: ["db"])
    .AddRedis(
        builder.Configuration["{bc_name}-redis-connection-string"]!,
        tags: ["cache"]);

// ── § 9. Middleware utilitário ────────────────────────────────────────────
builder.Services.AddProblemDetails();  // RFC 7807
builder.Services.AddHttpContextAccessor();
builder.Services.AddScoped<ICurrentUserService, HttpContextCurrentUserService>();

// ── § 10. CORS ────────────────────────────────────────────────────────────
builder.Services.AddCors(options =>
{
    options.AddPolicy("FrontendPolicy", policy =>
        policy
            .WithOrigins(
                builder.Configuration["Cors:AllowedOrigins"]?.Split(',')
                    ?? ["http://localhost:4200"])   // Angular dev
            .AllowAnyMethod()
            .AllowAnyHeader()
            .AllowCredentials());
});

// ── § 11. Rate Limiting ───────────────────────────────────────────────────
builder.Services.AddRateLimiter(options =>
{
    options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(ctx =>
        RateLimitPartition.GetFixedWindowLimiter(
            partitionKey: ctx.User.Identity?.Name ?? ctx.Connection.RemoteIpAddress?.ToString() ?? "anon",
            factory: _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 100,
                Window = TimeSpan.FromMinutes(1)
            }));
    options.OnRejected = async (ctx, ct) =>
    {
        ctx.HttpContext.Response.StatusCode = StatusCodes.Status429TooManyRequests;
        await ctx.HttpContext.Response.WriteAsJsonAsync(
            new ProblemDetails { Title = "Too Many Requests", Status = 429 }, ct);
    };
});

// ═════════════════════════════════════════════════════════════════════════
var app = builder.Build();
// ═════════════════════════════════════════════════════════════════════════

// ── § Middleware Pipeline (ordem importa) ─────────────────────────────────
app.UseExceptionHandler();          // ProblemDetails global — deve ser primeiro
app.UseStatusCodePages();

if (!app.Environment.IsProduction())
{
    app.MapOpenApi();               // /openapi/v1.json
    // Scalar UI (substitui Swagger UI):
    // app.MapScalarApiReference();
}

app.UseHttpsRedirection();
app.UseCors("FrontendPolicy");
app.UseRateLimiter();
app.UseAuthentication();
app.UseAuthorization();

// ── § Carter (registra todos os ICarterModule automaticamente) ─────────────
app.MapCarter();

// ── § Health Checks ───────────────────────────────────────────────────────
// ⚠️ GUARDRAIL: ALWAYS add .AllowAnonymous() to health check endpoints.
// Health checks must be publicly accessible without auth tokens for liveness/readiness probes.
// Without .AllowAnonymous(), authentication middleware returns 401 before the health response.
// ⚠️ GUARDRAIL: Do NOT use UIResponseWriter.WriteHealthCheckUIResponse — it requires the
// separate AspNetCore.HealthChecks.UI.Client package which is not in the package list.
// Use the default plain-text writer (no ResponseWriter). It returns "Healthy"/"Unhealthy".
app.MapHealthChecks("/health").AllowAnonymous();
app.MapHealthChecks("/health/ready",
    new HealthCheckOptions { Predicate = hc => hc.Tags.Contains("db") }).AllowAnonymous();
app.MapHealthChecks("/health/live",
    new HealthCheckOptions { Predicate = _ => false }).AllowAnonymous();  // sempre alive

await app.RunAsync();

// Para testes de integração
public partial class Program { }
```

## Customizações por Contexto

| Cenário | Customização |
|---------|-------------|
| `auth.provider ≠ azure-ad` | Substituir § 2 por `AddAuthentication().AddJwtBearer(...)` genérico + TODO |
| Redis não habilitado | Remover `.AddRedis(...)` de § 8 |
| `environment = Development` | Key Vault não carregado (guarda em `if (!IsDevelopment())`) |
| Multi-BC único host | Registrar múltiplos `Add{BC}Application()` e `Add{BC}Infrastructure()` em § 4 |
