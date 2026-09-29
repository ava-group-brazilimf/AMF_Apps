# Contrato Estrutural do F4 Stack .NET

> **Escopo:** agente `ava-stack-dotnet-backend` para projetos com
> `backend_framework == "dotnet"` e `pipeline_mode == "generic"`.
>
> **Objetivo:** garantir que o código backend gerado compile na primeira execução
> de `dotnet build` e suba corretamente via Docker/Podman Compose.

## 1. Modelo de deployment

O modelo padrão é **entrypoint autônomo por Bounded Context (BC)**:

- Cada BC gera sua própria aplicação ASP.NET Core executável.
- Cada BC.Api é um container independente no `docker-compose.yml`.
- Não existe um "Host API único" a menos que `architecture_patterns.host_api: true`
  esteja declarado explicitamente em `project-config.yaml`.

## 2. Contrato de `.csproj`

### 2.1. SDK e tipo de saída

| Projeto | SDK | `<OutputType>` |
|---------|-----|----------------|
| `{BC}.Domain` | `Microsoft.NET.Sdk` | omitido (Class Library) |
| `{BC}.Application` | `Microsoft.NET.Sdk` | omitido (Class Library) |
| `{BC}.Infrastructure` | `Microsoft.NET.Sdk` | omitido (Class Library) |
| `{BC}.Api` | `Microsoft.NET.Sdk.Web` | `Exe` |
| `Shared.Domain` | `Microsoft.NET.Sdk` | omitido (Class Library) |
| `Shared.Infrastructure` | `Microsoft.NET.Sdk` | omitido (Class Library) |

> **Invariante:** projeto `{BC}.Api` nunca pode usar `Microsoft.NET.Sdk` puro.
> Usar `Microsoft.NET.Sdk` em API causa `CS0103: WebApplication does not exist`
> e impede a publicação como executável.

### 2.2. Matriz de referências obrigatórias

| Camada | Referências obrigatórias |
|--------|--------------------------|
| `Api` | `Application`, `Infrastructure`, `Shared.Domain`, `Shared.Infrastructure` |
| `Application` | `Domain`, `Shared.Domain` |
| `Infrastructure` | `Domain`, `Application`, `Shared.Domain`, `Shared.Infrastructure` |
| `Domain` | `Shared.Domain` (quando usar tipos base compartilhados) |

> **Invariante:** nenhuma referência pode ser omitida sob a justificativa de
> "transitividade". Cada camada deve declarar explicitamente todos os projetos
> cujos namespaces referencia no código gerado.

## 3. Entrypoint (`Program.cs`)

Cada `{BC}.Api` DEVE conter `Program.cs` com, no mínimo:

```csharp
using {prefix}.{BC}.Api;
using {prefix}.Shared.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.Add{BC}(builder.Configuration);
builder.Services.AddSharedInfrastructure();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();
app.MapHealthChecks("/health");

app.Run();
```

## 4. Composição de DI do BC.Api

Cada `{BC}.Api` DEVE expor um método de extensão `Add{BC}` e referenciar
`Shared.Infrastructure`:

```csharp
using {prefix}.Shared.Infrastructure;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace {prefix}.{BC}.Api;

public static class DependencyInjection
{
    public static IServiceCollection Add{BC}(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services.Add{BC}Application();
        services.Add{BC}Infrastructure(configuration);
        services.AddSharedInfrastructure();
        return services;
    }
}
```

> **Invariante:** `AddSharedInfrastructure()` é obrigatória. Ela registra os
> interceptors compartilhados (`AuditInterceptor`, `SoftDeleteInterceptor`) e
> outros serviços cross-cutting. Sua omissão causa `InvalidOperationException`
> em runtime e crash dos containers.

## 5. `docker-compose.yml`

O arquivo de desenvolvimento DEVE declarar:

- Serviço `sql` (SQL Server) com healthcheck.
- Serviço `redis` com healthcheck.
- Um serviço backend por BC, com portas mapeadas sequencialmente (`5001`, `5002`, ...).
- Serviço `frontend` dependendo de pelo menos um backend healthy.

Exemplo de serviço backend:

```yaml
{service_name}:
  build:
    context: ./backend
    dockerfile: Dockerfile
    args:
      BC: "{BCName}"
  container_name: {prefix}-{service_name}
  ports:
    - "{port}:8080"
  environment:
    ASPNETCORE_ENVIRONMENT: Development
    ASPNETCORE_URLS: http://+:8080
    ConnectionStrings__SqlServer: "Server=sql,1433;Database={BCName}Db;User Id=sa;Password=${SQL_SA_PASSWORD};TrustServerCertificate=true;"
    ConnectionStrings__Redis: "redis:6379,password=${REDIS_PASSWORD}"
  depends_on:
    sql:
      condition: service_healthy
    redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

## 6. Gates de qualidade

O agente `ava-stack-build-validator` DEVE executar, para backend .NET:

1. `dotnet restore` — FAIL se houver pacotes não resolvidos.
2. `dotnet build` por camada — FAIL em qualquer erro.
3. `dotnet publish` de cada `{BC}.Api` — FAIL se não houver entry point.
4. `dotnet build` da solution toda — FAIL em warnings se `TreatWarningsAsErrors=true`.
5. `dotnet format --verify-no-changes` — WARN apenas.
6. `dotnet list package --vulnerable` — FAIL em CVEs (salvo exceções aprovadas).
7. `grep -r HintPath --include="*.csproj"` — FAIL se houver referências locais.
8. Smoke test em container via `docker compose up` — FAIL se serviços não subirem
   ou não responderem a `/health`.

## 7. Referências

- Agente F4 .NET: `src/modules/ava-fabric-agents/tech-stack/agents/coder-dotnet-backend.md`
- Agente de containerização: `src/modules/ava-fabric-agents/devops-agents/agents/containerize-agent.md`
- Agente de build validation: `src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md`
- Caso de referência: `processaERP-005/outputs/tobe/source-code/relatorio-avaliacao-f4-stack.md`
