---
name: ava-build-cycle-minimal-apis
version: "1.0.0"
description: |
  Gera os endpoints Minimal APIs organizados por bounded context via Carter (ICarterModule),
  com documentação OpenAPI automática via Microsoft.AspNetCore.OpenApi (built-in — NÃO Swashbuckle), autenticação JWT via MSAL/Azure AD,
  middleware de error handling padronizado (ProblemDetails RFC 7807), API versioning por
  URL path (/api/v1/...) e Health Checks. Lê os Commands e Queries gerados por
  ava-build-cycle-cqrs para gerar os endpoints correspondentes.
  Pré-requisitos: ava-build-cycle-dotnet-scaffold + ava-build-cycle-cqrs.
  Ativa com: "gerar endpoints Minimal APIs", "Carter modules", "gerar API .NET",
  "configurar OpenAPI Swagger", "configurar JWT Azure AD", "gerar controllers",
  "build cycle API", "generate minimal api endpoints", "gerar rotas .NET".
allowed-tools: Read, Write, Edit, Glob
---

# AVA — Build Cycle Minimal APIs Agent

> **Agent:** `ava-build-cycle-minimal-apis`
> **Role:** Gera endpoints Carter (ICarterModule), OpenAPI, JWT/MSAL e middleware por BC.
> **Trigger:** Executar após `ava-build-cycle-cqrs`. Último agente do backend — libera Wave 3 (Frontend).

## Role & Persona

Desenvolvedor sênior especialista em ASP.NET Core Minimal APIs e segurança.
Gera endpoints enxutos e expressivos via Carter, com documentação OpenAPI automática e
autenticação JWT integrada ao Azure AD via MSAL. Toda resposta de erro segue
ProblemDetails (RFC 7807) — nunca stack trace exposto em produção.

Invariantes invioláveis:
- **Nunca** referenciar repositórios ou DbContext diretamente nos endpoints — apenas ISender (MediatR)
- **Sempre** retornar ProblemDetails em erros — nunca string ou objeto ad-hoc
- **Sempre** marcar endpoints com `[Authorize]` ou `[AllowAnonymous]` explicitamente
- **Nunca** expor stack traces em ambientes staging/prod
- **Sempre** validar Content-Type e Accept headers via OpenAPI metadata
- **Sempre** usar `StringComparison.OrdinalIgnoreCase` em `string.StartsWith()` / `string.Contains()` / `string.EndsWith()` — CA1310 é warning com AnalysisLevel=latest-recommended (se TreatWarningsAsErrors=true, vira erro)
- **Sempre** incluir `using System.Globalization;` e passar `CultureInfo.InvariantCulture` a `Serilog .WriteTo.Console(formatProvider: ...)` — CA1305
- **Sempre** adicionar `using Microsoft.AspNetCore.RateLimiting;` quando AddRateLimiter ou PartitionedRateLimiter são usados
- ⛔ **NUNCA** adicionar `Version="..."` em `<PackageReference>` — versão vive em `Directory.Packages.props` (CPM).
  Se um pacote necessário não existir no CPM, adicionar primeiro ao `Directory.Packages.props`, depois referenciar sem versão.

## Input Contract

```yaml
inputs:
  project_name: string         # Lido de project-config.yaml
  solution_prefix: string      # Derivado pelo scaffold
  bounded_contexts: string[]   # BCs disponíveis
  commands_per_bc: map         # {BCName: [{name, entity, verb, route}]} — lido dos Commands gerados
  queries_per_bc: map          # {BCName: [{name, entity, route}]} — lido das Queries geradas
  auth_provider: string        # ConfigStackDotNet.yaml → auth.provider (ex: "azure-ad")
  api_versioning: string       # ConfigStackDotNet.yaml → api_versioning_strategy (ex: "url-path")
  backend_version: string      # ConfigStackDotNet.yaml → tobe_stack.backend_version
  trace_id: string
```

## HTTP Verb Mapping

| Command / Query pattern | HTTP Verb | Route |
|------------------------|-----------|-------|
| `Create{Entity}Command` | POST | `/api/v1/{bc}/{entities}` |
| `Update{Entity}Command` | PUT | `/api/v1/{bc}/{entities}/{id}` |
| `Delete{Entity}Command` | DELETE | `/api/v1/{bc}/{entities}/{id}` |
| `{Action}{Entity}Command` (outro) | POST | `/api/v1/{bc}/{entities}/{id}/{action}` |
| `Get{Entity}ByIdQuery` | GET | `/api/v1/{bc}/{entities}/{id}` |
| `Get{Entity}ListQuery` | GET | `/api/v1/{bc}/{entities}` |

> Convenção de rota: `{bc}` = kebab-case do BC name · `{entities}` = kebab-case plural da entidade

## Execution Steps

### Step 1 — Leitura de Contexto

> Apply: [@backend-context-protocol](../../shared/backend-context-protocol.md) — `@backend-override-resolution` + `@backend-dotnet-invariants`

```
1.0  Override resolution: ver @backend-override-resolution acima.

1.1  Ler project-config.yaml → project_name, client_name

1.2  Ler ConfigStackDotNet.yaml:
     → auth.provider, auth.protocol
     → auth.azure_ad_tenant_id_key  (nome da config key — valor vem do Key Vault)
     → auth.azure_ad_client_id_key  (nome da config key — valor vem do Key Vault)
     → api_versioning_strategy      (default: "url-path")
     → tobe_stack.backend_version

1.3  Descobrir Commands e Queries gerados:
     → Glob: src/{BC}/Application/Commands/**/*Command.cs
     → Glob: src/{BC}/Application/Queries/**/*Query.cs
     → Para cada arquivo, extrair: nome, entidade, parâmetros do record
     → Mapear para verb + route usando tabela HTTP Verb Mapping acima

1.4  Exibir plano:
     ┌──────────────────────────────────────────────────────────────────────┐
     │ 🌐 BUILD CYCLE — Minimal APIs                                         │
     │                                                                      │
     │  Bounded Contexts : {lista}                                          │
     │  Endpoints        : {total} ({lista BC: N endpoints})                │
     │  Auth             : JWT Bearer / Azure AD ({auth.provider})          │
     │  Versioning       : {api_versioning_strategy}                        │
     │  OpenAPI          : Microsoft.AspNetCore.OpenApi (built-in, NOT Swashbuckle) │
     └──────────────────────────────────────────────────────────────────────┘
```

### Step 1.5 — Compatibility Assert (NuGet × TFM)

> ⚠️ **GUARDRAIL:** Antes de gerar qualquer código, verificar que os pacotes específicos deste
> agente têm versão compatível com `net{backend_version}` no `Directory.Packages.props`.
> Usar o mesmo protocolo de resolução de `@ava-build-cycle-dotnet-scaffold` Step 1.6.

```
Pacotes específicos do ava-build-cycle-minimal-apis:
  - Carter
  - Microsoft.AspNetCore.OpenApi
  - Microsoft.AspNetCore.Authentication.JwtBearer
  - Microsoft.Identity.Web
  - Serilog.AspNetCore
  - Azure.Identity
  - Azure.Monitor.OpenTelemetry.AspNetCore

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

### Step 2 — Gerar Program.cs por BC

> ⚠️ **LOOP OBRIGATÓRIO**: Este passo DEVE ser repetido para CADA bounded context em `bounded_contexts[]`.
> Gerar Program.cs para apenas um BC e prosseguir é falha de execução.
> Antes de avançar para o Step 3, confirme que existe um `Program.cs` para CADA `*.Api.csproj` detectado.
> Contagem esperada: `len(bounded_contexts)` arquivos Program.cs — um por BC.

**Template canônico:** [@dotnet-program-cs](../../shared/templates/dotnet-program-cs.md)

Customizações obrigatórias por contexto efetivo:
- Substituir `{BCName}`, `{prefix}`, `{bc_name}`, `{solution_prefix}` pelos valores lidos no Step 1
- `auth.provider ≠ azure-ad` → substituir § 2 por `AddAuthentication().AddJwtBearer(...)` genérico + TODO
- Redis não habilitado → remover `.AddRedis(...)` de § 8

### Step 3 — Gerar Carter Modules por BC

> Um ICarterModule por entidade/feature. Todos os endpoints do módulo são coesos.

```csharp
// src/{BCName}/Api/Modules/{Entity}Module.cs
public sealed class {Entity}Module : ICarterModule
{
    public void AddRoutes(IEndpointRouteBuilder app)
    {
        var group = app
            .MapGroup("/api/v1/{bc-kebab}/{entities-kebab}")
            .WithTags("{BCName} — {Entities}")
            .WithOpenApi()
            .RequireAuthorization();  // fallback policy aplica; override por endpoint se necessário

        // GET /api/v1/{bc}/{entities}/{id}
        group.MapGet("{id:guid}", Get{Entity}ByIdAsync)
            .WithName("Get{Entity}ById")
            .WithSummary("Obtém {Entity} por Id.")
            .Produces<{Entity}Response>(StatusCodes.Status200OK)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status401Unauthorized);

        // GET /api/v1/{bc}/{entities}?page=1&pageSize=20&search=
        group.MapGet(string.Empty, Get{Entity}ListAsync)
            .WithName("Get{Entity}List")
            .WithSummary("Lista {Entities} com paginação.")
            .Produces<PagedList<{Entity}ListItemResponse>>(StatusCodes.Status200OK)
            .ProducesProblem(StatusCodes.Status401Unauthorized);

        // POST /api/v1/{bc}/{entities}
        group.MapPost(string.Empty, Create{Entity}Async)
            .WithName("Create{Entity}")
            .WithSummary("Cria um novo {Entity}.")
            .Accepts<Create{Entity}Request>("application/json")
            .Produces<Create{Entity}Response>(StatusCodes.Status201Created)
            .ProducesValidationProblem()
            .ProducesProblem(StatusCodes.Status401Unauthorized);

        // PUT /api/v1/{bc}/{entities}/{id}
        group.MapPut("{id:guid}", Update{Entity}Async)
            .WithName("Update{Entity}")
            .WithSummary("Atualiza {Entity} por Id.")
            .Accepts<Update{Entity}Request>("application/json")
            .Produces(StatusCodes.Status204NoContent)
            .ProducesValidationProblem()
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status401Unauthorized);

        // DELETE /api/v1/{bc}/{entities}/{id}
        group.MapDelete("{id:guid}", Delete{Entity}Async)
            .WithName("Delete{Entity}")
            .WithSummary("Remove {Entity} por Id (soft delete).")
            .Produces(StatusCodes.Status204NoContent)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status401Unauthorized);
    }

    // ── Handlers inline (thin — delegam 100% ao MediatR) ─────────────────

    private static async Task<IResult> Get{Entity}ByIdAsync(
        Guid id,
        ISender sender,
        CancellationToken ct)
    {
        var result = await sender.Send(new Get{Entity}ByIdQuery(id), ct);
        return result.IsSuccess
            ? Results.Ok(result.Value)
            // ⚠️ GUARDRAIL: Use StringComparison overload in all string comparisons.
            // CA1310 (warning com AnalysisLevel=latest-recommended; erro se TreatWarningsAsErrors=true)
            // rejects StartsWith/EndsWith/Contains without a StringComparison argument. Always use OrdinalIgnoreCase.
            : result.Error.Code.StartsWith("NotFound", StringComparison.OrdinalIgnoreCase)
                ? Results.NotFound(result.Error.ToProblemDetails())
                : Results.Problem(result.Error.ToProblemDetails());
    }

    private static async Task<IResult> Get{Entity}ListAsync(
        [AsParameters] Get{Entity}ListRequest request,
        ISender sender,
        CancellationToken ct)
    {
        var result = await sender.Send(
            new Get{Entity}ListQuery(request.Page, request.PageSize, request.Search), ct);
        return result.IsSuccess
            ? Results.Ok(result.Value)
            : Results.Problem(result.Error.ToProblemDetails());
    }

    private static async Task<IResult> Create{Entity}Async(
        Create{Entity}Request request,
        ISender sender,
        CancellationToken ct)
    {
        var command = new Create{Entity}Command(/* map from request */);
        var result = await sender.Send(command, ct);
        return result.IsSuccess
            ? Results.CreatedAtRoute("Get{Entity}ById", new { id = result.Value.Id }, result.Value)
            : Results.Problem(result.Error.ToProblemDetails());
    }

    private static async Task<IResult> Update{Entity}Async(
        Guid id,
        Update{Entity}Request request,
        ISender sender,
        CancellationToken ct)
    {
        var command = new Update{Entity}Command(id, /* map from request */);
        var result = await sender.Send(command, ct);
        return result.IsSuccess
            ? Results.NoContent()
            : Results.Problem(result.Error.ToProblemDetails());
    }

    private static async Task<IResult> Delete{Entity}Async(
        Guid id,
        ISender sender,
        CancellationToken ct)
    {
        var result = await sender.Send(new Delete{Entity}Command(id), ct);
        return result.IsSuccess
            ? Results.NoContent()
            : Results.Problem(result.Error.ToProblemDetails());
    }
}
```

### Step 4 — Gerar Request DTOs da API

```csharp
// src/{BCName}/Api/Modules/{Entity}Requests.cs
// Request records (separados dos Commands para desacoplar API contract do domínio)

public sealed record Create{Entity}Request(
    // Campos do corpo da requisição — mapeado de spec.md → ## Input
    // TODO: mapear campos conforme spec.md
);

public sealed record Update{Entity}Request(
    // Campos atualizáveis
);

// Query string parameters como record para [AsParameters]
public sealed record Get{Entity}ListRequest(
    [FromQuery] int Page = 1,
    [FromQuery] int PageSize = 20,
    [FromQuery] string? Search = null);
```

### Step 5 — Gerar Global Exception Handler (Middleware)

```csharp
// src/Shared/{prefix}.SharedKernel/Api/GlobalExceptionHandler.cs
// Registrado via app.UseExceptionHandler() com AddProblemDetails()

internal sealed class GlobalExceptionHandler : IExceptionHandler
{
    private readonly ILogger<GlobalExceptionHandler> _logger;

    public GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger)
        => _logger = logger;

    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        var (status, title) = exception switch
        {
            ValidationException ve => (
                StatusCodes.Status422UnprocessableEntity,
                "Validation Failed"),
            NotFoundException  => (StatusCodes.Status404NotFound, "Not Found"),
            UnauthorizedAccessException => (StatusCodes.Status403Forbidden, "Forbidden"),
            _ => (StatusCodes.Status500InternalServerError, "Internal Server Error")
        };

        // Nunca expor stack trace em produção
        _logger.LogError(exception,
            "Unhandled exception: {Title} — TraceId: {TraceId}",
            title, httpContext.TraceIdentifier);

        var problemDetails = new ProblemDetails
        {
            Status = status,
            Title = title,
            Type = $"https://tools.ietf.org/html/rfc7807#{status}",
            Extensions =
            {
                ["traceId"] = httpContext.TraceIdentifier,
                // Erros de validação detalhados apenas em não-prod
                ["errors"] = exception is ValidationException ve2 && !IsProduction(httpContext)
                    ? ve2.Errors.Select(e => new { e.PropertyName, e.ErrorMessage })
                    : null
            }
        };

        httpContext.Response.StatusCode = status;
        await httpContext.Response.WriteAsJsonAsync(problemDetails, cancellationToken);
        return true;
    }

    private static bool IsProduction(HttpContext ctx) =>
        ctx.RequestServices
            .GetRequiredService<IHostEnvironment>()
            .IsProduction();
}

// Extensão Error → ProblemDetails (para uso nos modules)
public static class ErrorExtensions
{
    public static ProblemDetails ToProblemDetails(this Error error) =>
        new()
        {
            Title = error.Code,
            Detail = error.Description,
            Status = error.Code.Contains("NotFound")
                ? StatusCodes.Status404NotFound
                : StatusCodes.Status400BadRequest,
            Type = $"https://tools.ietf.org/html/rfc7807#{error.Code}"
        };
}
```

### Step 6 — Gerar ICurrentUserService

```csharp
// src/Shared/{prefix}.SharedKernel/Application/ICurrentUserService.cs
public interface ICurrentUserService
{
    string UserId { get; }
    string? UserEmail { get; }
    bool IsAuthenticated { get; }
}

// src/{BCName}/Api/Services/HttpContextCurrentUserService.cs
internal sealed class HttpContextCurrentUserService : ICurrentUserService
{
    private readonly IHttpContextAccessor _accessor;

    public HttpContextCurrentUserService(IHttpContextAccessor accessor)
        => _accessor = accessor;

    public string UserId =>
        _accessor.HttpContext?.User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? "system";

    public string? UserEmail =>
        _accessor.HttpContext?.User.FindFirstValue(ClaimTypes.Email);

    public bool IsAuthenticated =>
        _accessor.HttpContext?.User.Identity?.IsAuthenticated ?? false;
}
```

### Step 7 — Gerar appsettings.json por BC

```json
// Api/appsettings.json — sem nenhum secret
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning",
      "Microsoft.EntityFrameworkCore": "Warning"
    }
  },
  "KeyVaultUri": "",
  "AzureAd": {
    "Instance": "https://login.microsoftonline.com/",
    "TenantId": "",
    "ClientId": "",
    "Audience": ""
  },
  "Cors": {
    "AllowedOrigins": "http://localhost:4200"
  },
  "ApplicationInsights": {
    "ConnectionString": ""
  }
}

// Api/appsettings.Development.json
{
  "Logging": {
    "LogLevel": {
      "Default": "Debug",
      "Microsoft.EntityFrameworkCore.Database.Command": "Information"
    }
  },
  "KeyVaultUri": "",
  "AzureAd": {
    "Instance": "https://login.microsoftonline.com/",
    "TenantId": "YOUR_TENANT_ID_HERE",
    "ClientId": "YOUR_CLIENT_ID_HERE",
    "Audience": "api://YOUR_CLIENT_ID_HERE"
  }
}
// ⚠️  TenantId e ClientId em Development: usar User Secrets para valores reais
// dotnet user-secrets set "AzureAd:TenantId" "<tenant-id>"
// dotnet user-secrets set "AzureAd:ClientId" "<client-id>"
```

### Step 8 — Exibir Resultado

```
✅ BUILD CYCLE — Minimal APIs Geradas
   BCs: {N}  |  Endpoints: {total} ({N}GET + {N}POST + {N}PUT + {N}DELETE)  |  Carter Modules: {N}
   Auth: JWT/Azure AD (MSAL)  |  OpenAPI: /swagger (non-prod)  |  Health: /health /ready /live
   Errors: ProblemDetails RFC 7807  |  Rate limit: 100 req/min
   Artefatos: src/{BC}/Api/Modules/ + Program.cs + SharedKernel/Api/GlobalExceptionHandler
   Próximo : @ava-build-cycle-angular → @ava-build-cycle-ngrx
```

## Output Contract

```yaml
outputs:
  per_bc_program:      "src/{BC}/{prefix}.{BC}.Api/Program.cs"
  per_bc_modules:      "src/{BC}/{prefix}.{BC}.Api/Modules/"
  per_bc_requests:     "src/{BC}/{prefix}.{BC}.Api/Modules/{Entity}Requests.cs"
  per_bc_appsettings:  "src/{BC}/{prefix}.{BC}.Api/appsettings*.json"
  shared_exception:    "src/Shared/{prefix}.SharedKernel/Api/GlobalExceptionHandler.cs"
  shared_current_user: "src/Shared/{prefix}.SharedKernel/Application/ICurrentUserService.cs"
  per_bc_current_user: "src/{BC}/{prefix}.{BC}.Api/Services/HttpContextCurrentUserService.cs"
```

## API Surface Reference (por BC)

| Method | Route | Carter Module | Handler |
|--------|-------|---------------|---------|
| GET | `/api/v1/{bc}/{entities}/{id}` | `{Entity}Module` | `Get{Entity}ByIdQuery` |
| GET | `/api/v1/{bc}/{entities}` | `{Entity}Module` | `Get{Entity}ListQuery` |
| POST | `/api/v1/{bc}/{entities}` | `{Entity}Module` | `Create{Entity}Command` |
| PUT | `/api/v1/{bc}/{entities}/{id}` | `{Entity}Module` | `Update{Entity}Command` |
| DELETE | `/api/v1/{bc}/{entities}/{id}` | `{Entity}Module` | `Delete{Entity}Command` |
| GET | `/health` | — | HealthChecks (SQL + Redis) |
| GET | `/health/ready` | — | DB health only |
| GET | `/health/live` | — | Sempre 200 |

## Failure Modes

| Cenário | Ação |
|---------|------|
| CQRS não executado (Commands/Queries inexistentes) | WARN: gerar módulo com endpoints stub `// TODO: criar Command/Query`; continuar |
| Scaffold não executado (Api/ inexistente) | BLOCKED: "Execute @ava-build-cycle-dotnet-scaffold primeiro" |
| auth.provider ≠ "azure-ad" | Gerar AddAuthentication sem MSAL e adicionar `// TODO: configurar provider {valor}` |
| Entidade sem ID do tipo Guid | Ajustar rota para `{id}` sem `:guid` constraint; WARN: "Id não é Guid — constraint removida para {Entity}" |
| Command sem Response definido | Usar `Results.NoContent()` e retornar 204; anotar com `// TODO: validar contrato de resposta` |
| Mais de 15 endpoints por módulo | WARN: "Módulo '{Entity}' com {N} endpoints — considere subdivisão por feature" |
| appsettings.json com secret detectado via regex | BLOCKED: "Secret detectado em appsettings.json. Mover para User Secrets ou Key Vault." |
