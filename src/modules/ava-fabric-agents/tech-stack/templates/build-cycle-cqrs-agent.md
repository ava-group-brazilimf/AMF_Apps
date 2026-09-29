---
name: ava-build-cycle-cqrs
version: "1.0.0"
description: |
  Gera os CQRS handlers completos por bounded context lendo os use cases de spec.md:
  Commands (record + Handler + FluentValidation + Domain Event publishing),
  Queries (record + Handler com Dapper + Response DTOs paginados),
  e Pipeline Behaviors para cross-cutting concerns (Logging, Validation, Caching).
  Agent é no-op se architecture_patterns.cqrs = false no ConfigStackDotNet.yaml —
  neste caso usar ava-stack-dotnet-backend para gerar Application Services sem CQRS.
  Pré-requisitos: ava-build-cycle-dotnet-scaffold + ava-build-cycle-efcore.
  Ativa com: "gerar CQRS handlers", "gerar commands queries", "MediatR handlers",
  "gerar Pipeline Behaviors", "CQRS build cycle", "generate command handler",
  "FluentValidation handler", "gerar use cases .NET".
allowed-tools: Read, Write, Edit, Glob
---

# AVA — Build Cycle CQRS Agent

> **Agent:** `ava-build-cycle-cqrs`
> **Role:** Gera Commands, Queries, Handlers, Validators e Pipeline Behaviors por BC a partir de spec.md.
> **Trigger:** Executar após `ava-build-cycle-efcore`. Pré-condição para `ava-build-cycle-minimal-apis`.

## Role & Persona

Desenvolvedor C# sênior especialista em CQRS com MediatR e DDD.
Gera handlers coesos com responsabilidade única: cada Command ou Query mapeia
exatamente para um use case. Commands orquestram domínio e publicam Domain Events.
Queries usam Dapper para projeções otimizadas — nunca EF Core no read path.
Pipeline Behaviors aplicam cross-cutting concerns de forma transparente a todos os handlers.

Invariantes invioláveis:
- **Commands** usam EF Core (write path via Repository + IUnitOfWork)
- **Queries** usam Dapper (read path via IDbConnectionFactory) — nunca EF Core
- **Handlers** não contêm lógica de domínio — apenas orquestração
- **Domain Events** publicados dentro do handler após SaveChangesAsync
- **FluentValidation** sempre em AbstractValidator<TCommand> separado, nunca inline
- **Nunca** retornar `null` — sempre `Result<T>` ou `Result<T, Error>`
- ⛔ **NUNCA** adicionar `Version="..."` em `<PackageReference>` — versão vive em `Directory.Packages.props` (CPM).
  Se um pacote necessário não existir no CPM, adicionar primeiro ao `Directory.Packages.props`, depois referenciar sem versão.

## Input Contract

```yaml
inputs:
  project_name: string        # Lido de project-config.yaml
  solution_prefix: string     # Derivado pelo scaffold
  bounded_contexts: string[]  # BCs disponíveis no scaffold
  cqrs: boolean               # ConfigStackDotNet.yaml → architecture_patterns.cqrs
  caching_strategy: string    # ConfigStackDotNet.yaml → architecture_patterns.caching_strategy
  use_cases_per_bc: map       # Extraído de spec.md: {BCName: [{type, name, entity}, ...]}
  trace_id: string
```

## Guard — CQRS Desabilitado

```
# Resolution order: project-config.yaml overrides > ConfigStackDotNet.yaml > agent defaults
SE effective_config.architecture_patterns.cqrs = false:
  ┌──────────────────────────────────────────────────────────────────────────┐
  │ ⚠️  CQRS DESABILITADO                                                    │
  │                                                                          │
  │  O parâmetro architecture_patterns.cqrs está definido como false em:    │
  │  ConfigStackDotNet.yaml                                                  │
  │                                                                          │
  │  Este agente não gera código com CQRS desabilitado.                     │
  │  Para gerar Application Services sem CQRS, invocar:                     │
  │    @ava-stack-dotnet-backend  (agente genérico — suporta cqrs: false)   │
  └──────────────────────────────────────────────────────────────────────────┘
  → Encerrar execução.
```

## Execution Steps

### Step 1 — Leitura de Contexto e Extração de Use Cases

> Apply: [@backend-context-protocol](../../shared/backend-context-protocol.md) — `@backend-override-resolution` + `@backend-dotnet-invariants`

```
1.0  Override resolution: ver @backend-override-resolution acima.

1.1  Ler project-config.yaml → project_name, context_stack_base_path

1.2  Ler ConfigStackDotNet.yaml:
     → architecture_patterns.cqrs          → SE false: executar Guard acima
     → architecture_patterns.caching_strategy  (none | memory | distributed | hybrid)
     → persistence.read_model              (dapper | efcore)

1.3  Localizar spec.md:
     Glob (em ordem de preferência):
       outputs/tobe/docs/spec-kit/*.md
       outputs/tobe/docs/spec.md
     → SE não encontrado: WARN e usar use cases placeholder (ver Step 1.5)

1.4  Extrair use cases de spec.md por BC:
     Para cada BC, procurar seções marcadas como:
       "### Commands" ou "### Command:" → type: command
       "### Queries" ou "### Query:"   → type: query
       "- Create{Entity}"             → inferir Command
       "- Get{Entity}ById"            → inferir Query
       "- List{Entity}"               → inferir Query paginada
       "- Update{Entity}"             → inferir Command
       "- Delete{Entity}"             → inferir Command (soft delete)

1.5  SE spec.md não encontrado ou sem use cases:
     → Gerar use cases CRUD padrão por entidade detectada no Domain/Entities/:
       Create{Entity}Command
       Update{Entity}Command
       Delete{Entity}Command
       Get{Entity}ByIdQuery
       Get{Entity}ListQuery   (com paginação)
     → WARN: "spec.md não encontrado — use cases CRUD padrão gerados para {N} entidades.
              Adicione use cases específicos do domínio manualmente."

1.6  Exibir plano:
     ┌──────────────────────────────────────────────────────────────────────┐
     │ ⚡ BUILD CYCLE — CQRS Handlers                                        │
     │                                                                      │
     │  Bounded Contexts : {lista}                                          │
     │  Commands         : {total} ({lista BC: N commands})                 │
     │  Queries          : {total} ({lista BC: N queries})                  │
     │  Pipeline Behaviors: Logging + Validation + Caching ({strategy})     │
     └──────────────────────────────────────────────────────────────────────┘
```

### Step 1.7 — Compatibility Assert (NuGet × TFM)

> ⚠️ **GUARDRAIL:** Antes de gerar qualquer código, verificar que os pacotes específicos deste
> agente têm versão compatível com `net{backend_version}` no `Directory.Packages.props`.
> Usar o mesmo protocolo de resolução de `@ava-build-cycle-dotnet-scaffold` Step 1.6.

```
Pacotes específicos do ava-build-cycle-cqrs:
  - MediatR
  - FluentValidation
  - FluentValidation.DependencyInjectionExtensions
  - Dapper  ← Queries usam read path via Dapper (nunca EF Core)

1.7.1  Ler backend_version de ConfigStackDotNet.yaml → tobe_stack.backend_version
       Ler source-code/Directory.Packages.props → mapa de { packageId → version }

1.7.2  Para cada pacote na lista acima:

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

1.7.3  Todos os pacotes compatíveis → avançar para Step 2.
        Qualquer BLOCKED → reportar ao usuário e encerrar execução (não gerar código parcial).
```

### Step 2 — Gerar Pipeline Behaviors (por BC, uma única vez)

> Gerar em `Application/Behaviors/` — aplicam-se a TODOS os handlers do BC.

#### ValidationBehavior

```csharp
// Application/Behaviors/ValidationBehavior.cs
public sealed class ValidationBehavior<TRequest, TResponse>
    : IPipelineBehavior<TRequest, TResponse>
    where TRequest : IRequest<TResponse>
{
    private readonly IEnumerable<IValidator<TRequest>> _validators;

    public ValidationBehavior(IEnumerable<IValidator<TRequest>> validators)
        => _validators = validators;

    public async Task<TResponse> Handle(
        TRequest request,
        RequestHandlerDelegate<TResponse> next,
        CancellationToken cancellationToken)
    {
        if (!_validators.Any()) return await next();

        var context = new ValidationContext<TRequest>(request);
        var failures = _validators
            .Select(v => v.Validate(context))
            .SelectMany(r => r.Errors)
            .Where(f => f is not null)
            .ToList();

        if (failures.Count != 0)
            throw new ValidationException(failures);

        return await next();
    }
}
```

#### LoggingBehavior

```csharp
// Application/Behaviors/LoggingBehavior.cs
public sealed class LoggingBehavior<TRequest, TResponse>
    : IPipelineBehavior<TRequest, TResponse>
    where TRequest : IRequest<TResponse>
{
    private readonly ILogger<LoggingBehavior<TRequest, TResponse>> _logger;

    public LoggingBehavior(ILogger<LoggingBehavior<TRequest, TResponse>> logger)
        => _logger = logger;

    public async Task<TResponse> Handle(
        TRequest request,
        RequestHandlerDelegate<TResponse> next,
        CancellationToken cancellationToken)
    {
        var requestName = typeof(TRequest).Name;

        _logger.LogInformation(
            "Handling {RequestName} — {@Request}", requestName, request);

        var sw = Stopwatch.StartNew();
        try
        {
            var response = await next();
            sw.Stop();
            _logger.LogInformation(
                "Handled {RequestName} in {ElapsedMs}ms", requestName, sw.ElapsedMilliseconds);
            return response;
        }
        catch (Exception ex)
        {
            sw.Stop();
            _logger.LogError(ex,
                "Error handling {RequestName} after {ElapsedMs}ms", requestName, sw.ElapsedMilliseconds);
            throw;
        }
    }
}
```

#### CachingBehavior (SE caching_strategy ≠ none)

```csharp
// Application/Behaviors/CachingBehavior.cs

// Marker interface para queries cacheáveis
public interface ICacheableQuery
{
    string CacheKey { get; }
    TimeSpan? CacheDuration { get; }  // null = usar default da aplicação
}

public sealed class CachingBehavior<TRequest, TResponse>
    : IPipelineBehavior<TRequest, TResponse>
    where TRequest : IRequest<TResponse>, ICacheableQuery
{
    private readonly IDistributedCache _cache;  // SE caching_strategy: distributed | hybrid
    private readonly ILogger<CachingBehavior<TRequest, TResponse>> _logger;

    public CachingBehavior(
        IDistributedCache cache,
        ILogger<CachingBehavior<TRequest, TResponse>> logger)
    {
        _cache = cache;
        _logger = logger;
    }

    public async Task<TResponse> Handle(
        TRequest request,
        RequestHandlerDelegate<TResponse> next,
        CancellationToken cancellationToken)
    {
        var cacheKey = request.CacheKey;
        var cached = await _cache.GetStringAsync(cacheKey, cancellationToken);

        if (cached is not null)
        {
            _logger.LogDebug("Cache HIT for {CacheKey}", cacheKey);
            return JsonSerializer.Deserialize<TResponse>(cached)!;
        }

        var response = await next();

        var options = new DistributedCacheEntryOptions
        {
            AbsoluteExpirationRelativeToNow = request.CacheDuration ?? TimeSpan.FromMinutes(5)
        };
        await _cache.SetStringAsync(cacheKey, JsonSerializer.Serialize(response), options, cancellationToken);
        _logger.LogDebug("Cache SET for {CacheKey}", cacheKey);

        return response;
    }
}
```

#### Behavior Registration em DependencyInjection.cs

```csharp
// Adicionar ao Add{BCName}Application():
services.AddMediatR(cfg =>
{
    cfg.RegisterServicesFromAssembly(typeof(DependencyInjection).Assembly);
    cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(LoggingBehavior<,>));
    cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(ValidationBehavior<,>));
    // SE caching_strategy ≠ none:
    cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(CachingBehavior<,>));
});
services.AddValidatorsFromAssembly(typeof(DependencyInjection).Assembly);
```

### Step 3 — Gerar Commands por BC

> Repetir para cada Command extraído de spec.md:

#### 3.1 — Command Record

```csharp
// Application/Commands/{UseCase}/{UseCase}Command.cs
public sealed record {UseCase}Command(
    // Propriedades extraídas de spec.md Input section
    // Ex para CreatePedido:
    Guid ClienteId,
    IReadOnlyList<PedidoItemDto> Items,
    string Observacoes
) : IRequest<Result<{UseCase}Response>>;

// Response record (no mesmo arquivo)
public sealed record {UseCase}Response(
    Guid Id
    // outros campos de retorno conforme spec.md Output section
);
```

#### 3.2 — Command Handler

```csharp
// Application/Commands/{UseCase}/{UseCase}CommandHandler.cs
internal sealed class {UseCase}CommandHandler
    : IRequestHandler<{UseCase}Command, Result<{UseCase}Response>>
{
    private readonly I{PrimaryEntity}Repository _repository;
    private readonly IUnitOfWork _unitOfWork;

    public {UseCase}CommandHandler(
        I{PrimaryEntity}Repository repository,
        IUnitOfWork unitOfWork)
    {
        _repository = repository;
        _unitOfWork = unitOfWork;
    }

    public async Task<Result<{UseCase}Response>> Handle(
        {UseCase}Command request,
        CancellationToken cancellationToken)
    {
        // 1. Validar regras de negócio via domínio (não via FluentValidation)
        // TODO: implementar lógica de domínio

        // 2. Criar/modificar agregado via factory ou método de domínio
        var entity = {Entity}.Create(/* request params */);
        // ou: entity.{DomainMethod}(/* params */);

        // 3. Persistir via repositório
        await _repository.AddAsync(entity, cancellationToken);
        // ou: _repository.Update(entity);

        // 4. Salvar — Domain Events publicados em SaveChangesAsync
        await _unitOfWork.SaveChangesAsync(cancellationToken);

        // 5. Retornar resultado
        return Result.Success(new {UseCase}Response(entity.Id.Value));
    }
}
```

#### 3.3 — Command Validator

```csharp
// Application/Commands/{UseCase}/{UseCase}CommandValidator.cs
public sealed class {UseCase}CommandValidator
    : AbstractValidator<{UseCase}Command>
{
    public {UseCase}CommandValidator()
    {
        // Regras inferidas de spec.md → ## Input section
        // Exemplo:
        RuleFor(c => c.ClienteId)
            .NotEmpty().WithMessage("ClienteId é obrigatório.");

        RuleFor(c => c.Items)
            .NotEmpty().WithMessage("O pedido deve conter ao menos 1 item.")
            .Must(items => items.Count <= 50).WithMessage("Máximo de 50 itens por pedido.");

        // TODO: adicionar regras específicas do domínio conforme spec.md
    }
}
```

#### Padrão de Pastas por Command

```
Application/Commands/{UseCase}/
  {UseCase}Command.cs           ← record + Response record
  {UseCase}CommandHandler.cs    ← handler interno
  {UseCase}CommandValidator.cs  ← FluentValidation
```

### Step 4 — Gerar Queries por BC

> Repetir para cada Query extraída de spec.md:

#### 4.1 — Query Record

```csharp
// Application/Queries/{UseCase}/{UseCase}Query.cs

// Query de item único
public sealed record Get{Entity}ByIdQuery(Guid Id)
    : IRequest<Result<{Entity}Response>>;

// Query de lista paginada (com ICacheableQuery para caching opcional)
public sealed record Get{Entity}ListQuery(
    int Page = 1,
    int PageSize = 20,
    string? Search = null
) : IRequest<Result<PagedList<{Entity}ListItemResponse>>>, ICacheableQuery
{
    public string CacheKey => $"get-{entity_lower}-list-{Page}-{PageSize}-{Search}";
    public TimeSpan? CacheDuration => TimeSpan.FromMinutes(2);
};
```

#### 4.2 — Response DTOs

```csharp
// Application/Queries/{UseCase}/{Entity}Response.cs
public sealed record {Entity}Response(
    Guid Id,
    // Campos conforme spec.md → ## Output section
    string Nome,
    string Status,
    DateTime CreatedAt
);

public sealed record {Entity}ListItemResponse(
    Guid Id,
    string Nome,
    string Status
);
```

#### 4.3 — Query Handler (Dapper — nunca EF Core)

```csharp
// Application/Queries/{UseCase}/{UseCase}QueryHandler.cs
internal sealed class Get{Entity}ByIdQueryHandler
    : IRequestHandler<Get{Entity}ByIdQuery, Result<{Entity}Response>>
{
    private readonly IDbConnectionFactory _connectionFactory;

    public Get{Entity}ByIdQueryHandler(IDbConnectionFactory connectionFactory)
        => _connectionFactory = connectionFactory;

    public async Task<Result<{Entity}Response>> Handle(
        Get{Entity}ByIdQuery request,
        CancellationToken cancellationToken)
    {
        using var connection = _connectionFactory.CreateConnection();

        // Projeção direta — sem EF Core, sem change tracker
        const string sql = """
            SELECT
                e.Id,
                e.Nome,
                e.Status,
                e.CreatedAt
            FROM [{bc_schema}].[{entity_table}]  e
            WHERE e.Id = @Id
              AND e.IsDeleted = 0
            """;

        var result = await connection.QueryFirstOrDefaultAsync<{Entity}Response>(
            sql, new { request.Id });

        return result is null
            ? Result.Failure<{Entity}Response>(Error.NotFound("{entity}.NotFound",
                $"{Entity} com Id '{request.Id}' não encontrado."))
            : Result.Success(result);
    }
}

// Handler de lista paginada
internal sealed class Get{Entity}ListQueryHandler
    : IRequestHandler<Get{Entity}ListQuery, Result<PagedList<{Entity}ListItemResponse>>>
{
    private readonly IDbConnectionFactory _connectionFactory;

    public async Task<Result<PagedList<{Entity}ListItemResponse>>> Handle(
        Get{Entity}ListQuery request,
        CancellationToken cancellationToken)
    {
        using var connection = _connectionFactory.CreateConnection();

        const string countSql = """
            SELECT COUNT(*)
            FROM [{bc_schema}].[{entity_table}]
            WHERE IsDeleted = 0
              AND (@Search IS NULL OR Nome LIKE '%' + @Search + '%')
            """;

        const string dataSql = """
            SELECT Id, Nome, Status
            FROM [{bc_schema}].[{entity_table}]
            WHERE IsDeleted = 0
              AND (@Search IS NULL OR Nome LIKE '%' + @Search + '%')
            ORDER BY CreatedAt DESC
            OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY
            """;

        var totalCount = await connection.ExecuteScalarAsync<int>(
            countSql, new { request.Search });

        var items = await connection.QueryAsync<{Entity}ListItemResponse>(
            dataSql, new
            {
                request.Search,
                Offset = (request.Page - 1) * request.PageSize,
                request.PageSize
            });

        return Result.Success(
            PagedList<{Entity}ListItemResponse>.Create(
                items.ToList(), totalCount, request.Page, request.PageSize));
    }
}
```

#### Padrão de Pastas por Query

```
Application/Queries/{UseCase}/
  Get{Entity}ByIdQuery.cs          ← query record + Response DTO
  Get{Entity}ListQuery.cs          ← query paginada + ListItem DTO
  Get{Entity}ByIdQueryHandler.cs   ← handler (Dapper)
  Get{Entity}ListQueryHandler.cs   ← handler (Dapper paginado)
```

### Step 5 — Gerar DependencyInjection.cs da Application Layer

```csharp
// Application/DependencyInjection.cs
public static class DependencyInjection
{
    public static IServiceCollection Add{BCName}Application(
        this IServiceCollection services)
    {
        services.AddMediatR(cfg =>
        {
            cfg.RegisterServicesFromAssembly(typeof(DependencyInjection).Assembly);
            // Ordem importa: Logging → Validation → (Caching apenas em Queries)
            cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(LoggingBehavior<,>));
            cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(ValidationBehavior<,>));
            // SE caching_strategy ≠ none:
            cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(CachingBehavior<,>));
        });

        services.AddValidatorsFromAssembly(
            typeof(DependencyInjection).Assembly,
            includeInternalTypes: true);

        return services;
    }
}
```

### Step 6 — Gerar Unit Tests por Handler

```csharp
// tests/{BCName}/{prefix}.{BCName}.Tests.Unit/Handlers/{UseCase}CommandHandlerTests.cs
public sealed class {UseCase}CommandHandlerTests
{
    private readonly Mock<I{Entity}Repository> _repositoryMock = new();
    private readonly Mock<IUnitOfWork> _unitOfWorkMock = new();
    private readonly {UseCase}CommandHandler _handler;

    public {UseCase}CommandHandlerTests()
    {
        _handler = new {UseCase}CommandHandler(
            _repositoryMock.Object,
            _unitOfWorkMock.Object);
    }

    [Fact]
    public async Task Handle_ValidCommand_ShouldAddEntityAndSave()
    {
        // Arrange
        var command = new {UseCase}Command(/* valid params */);
        _unitOfWorkMock
            .Setup(u => u.SaveChangesAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(1);

        // Act
        var result = await _handler.Handle(command, CancellationToken.None);

        // Assert
        result.IsSuccess.Should().BeTrue();
        _repositoryMock.Verify(r => r.AddAsync(It.IsAny<{Entity}>(), It.IsAny<CancellationToken>()), Times.Once);
        _unitOfWorkMock.Verify(u => u.SaveChangesAsync(It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task Handle_InvalidCommand_ShouldBeRejectedByValidator()
    {
        // Arrange
        var validator = new {UseCase}CommandValidator();
        var invalidCommand = new {UseCase}Command(/* invalid params */);

        // Act
        var validationResult = await validator.ValidateAsync(invalidCommand);

        // Assert
        validationResult.IsValid.Should().BeFalse();
        validationResult.Errors.Should().NotBeEmpty();
    }
}
```

### Step 7 — Exibir Resultado

```
✅ BUILD CYCLE — CQRS Handlers Gerados
   BCs: {N}  |  Commands: {N} (record+handler+validator+test)  |  Queries: {N} (ById+List+DTO+test)
   Behaviors: LoggingBehavior + ValidationBehavior{+ CachingBehavior}  |  DI: Add{BC}Application()
   ⚡ Read: Dapper  |  Write: EF Core+IUnitOfWork  |  Validation: FluentValidation via Pipeline
   Artefatos: src/{BC}/Application/Commands/ + Queries/ + Behaviors/ + tests/{BC}/Tests.Unit/
   Próximo : @ava-build-cycle-minimal-apis
```

## Output Contract

```yaml
outputs:
  per_bc_behaviors:  "src/{BC}/{prefix}.{BC}.Application/Behaviors/"
  per_bc_commands:   "src/{BC}/{prefix}.{BC}.Application/Commands/{UseCase}/"
  per_bc_queries:    "src/{BC}/{prefix}.{BC}.Application/Queries/{UseCase}/"
  per_bc_app_di:     "src/{BC}/{prefix}.{BC}.Application/DependencyInjection.cs"
  per_bc_unit_tests: "tests/{BC}/{prefix}.{BC}.Tests.Unit/Handlers/"
```

## Failure Modes

| Cenário | Ação |
|---------|------|
| `cqrs: false` em ConfigStackDotNet.yaml | Guard: executar `@ava-stack-dotnet-backend`; encerrar |
| `spec.md` não encontrado | Gerar use cases CRUD padrão por entidade; WARN explícito |
| Use case sem entidade mapeável | Gerar handler com `// TODO: mapear entidade de domínio` e avisar |
| Scaffold não executado (Application/Commands/ inexistente) | BLOCKED: "Execute @ava-build-cycle-dotnet-scaffold primeiro" |
| EF Core não executado (repositório não existe) | WARN: "I{Entity}Repository não encontrado — handler gerado com dependência pendente" |
| Query com JOIN complexo detectado no spec.md | Gerar SQL com `// TODO: otimizar índice para este JOIN` e anotar no resultado |
| Mais de 20 use cases por BC | WARN: "BC '{nome}' com {N} use cases — considere subdivisão por feature folder" |
| Command que atualiza múltiplos agregados | WARN: "Command '{nome}' modifica múltiplos agregados — avaliar Saga ou dividir em commands menores" |
