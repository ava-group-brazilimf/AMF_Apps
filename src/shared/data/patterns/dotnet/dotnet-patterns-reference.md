---
name: dotnet-patterns-reference
description: "Referência de padrões .NET 10 / Clean Architecture para geração de código"
version: "1.0.0"
used_by: [ava-coder-dotnet, ava-stack-dotnet-backend, ava-tobe-architecture-technical]
---

# .NET 10 Patterns Reference

## Clean Architecture — Estrutura Padrão
```
{Module}.Domain/
├── Entities/
│   └── {Entity}.cs              # Aggregate Root ou Entity
├── ValueObjects/
│   └── {VO}.cs                  # abstract record ValueObject — imutável, sem identidade, structural equality via record
├── Events/
│   └── {Entity}{Action}Event.cs # INotification (MediatR)
└── Interfaces/
    └── I{Entity}Repository.cs   # Contrato de persistência

{Module}.Application/
├── Commands/
│   └── {Action}{Entity}Command.cs  # record + IRequest<Result>
├── Queries/
│   └── Get{Entity}Query.cs         # record + IRequest<Response>
├── Handlers/
│   ├── {Action}{Entity}Handler.cs  # IRequestHandler<Command, Result>
│   └── Get{Entity}Handler.cs
├── Validators/
│   └── {Action}{Entity}Validator.cs # AbstractValidator<Command>
└── Services/
    └── I{Service}.cs

{Module}.Infrastructure/
├── Persistence/
│   ├── {Module}DbContext.cs
│   ├── Configurations/
│   │   └── {Entity}Configuration.cs # IEntityTypeConfiguration<T>
│   └── Repositories/
│       └── {Entity}Repository.cs
└── Services/
    └── {Service}.cs

{Module}.API/
├── Endpoints/
│   └── {Entity}Endpoints.cs    # Minimal API extension methods
└── Models/
    └── {Entity}Request.cs
```

## Template: Command + Handler + Validator
```csharp
// Command
public record MatricularAlunoCommand(
    Guid AlunoId,
    Guid CursoId,
    DateOnly DataInicio
) : IRequest<MatriculaResult>;

// Handler
public sealed class MatricularAlunoHandler(
    IMatriculaRepository repo,
    IUnitOfWork uow,
    IPublisher publisher
) : IRequestHandler<MatricularAlunoCommand, MatriculaResult>
{
    public async Task<MatriculaResult> Handle(
        MatricularAlunoCommand cmd, CancellationToken ct)
    {
        var matricula = Matricula.Create(cmd.AlunoId, cmd.CursoId, cmd.DataInicio);
        await repo.AddAsync(matricula, ct);
        await uow.SaveChangesAsync(ct);
        await publisher.Publish(new MatriculaCriadaEvent(matricula.Id), ct);
        return new MatriculaResult(matricula.Id, matricula.Status.ToString());
    }
}

// Validator
public sealed class MatricularAlunoValidator
    : AbstractValidator<MatricularAlunoCommand>
{
    public MatricularAlunoValidator()
    {
        RuleFor(x => x.AlunoId).NotEmpty();
        RuleFor(x => x.CursoId).NotEmpty();
        RuleFor(x => x.DataInicio).GreaterThanOrEqualTo(DateOnly.FromDateTime(DateTime.Today));
    }
}
```

## Template: Value Object (abstract record)
```csharp
// SharedKernel — base para todos os VOs
public abstract record ValueObject;

// VO concreto — positional record herda de ValueObject
// Structural equality é nativa do record (não precisa de GetEqualityComponents)
public record Money(decimal Amount, string Currency) : ValueObject
{
    public static Money Zero(string currency) => new(0m, currency);

    public static Money Create(decimal amount, string currency)
    {
        if (amount < 0) throw new DomainException("Amount cannot be negative.");
        if (string.IsNullOrWhiteSpace(currency)) throw new DomainException("Currency is required.");
        return new(amount, currency);
    }

    public Money Add(Money other)
    {
        if (Currency != other.Currency)
            throw new DomainException($"Cannot add {Currency} and {other.Currency}.");
        return new(Amount + other.Amount, Currency);
    }
}

// VO com campo único (ex: TaxId, Email)
public record TaxId(string Value) : ValueObject
{
    public static TaxId Create(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) throw new DomainException("TaxId is required.");
        return new(raw.Trim());
    }
}

// EF Core — configuração de owned entity para record VO
// Em IEntityTypeConfiguration<Party>:
builder.OwnsOne(p => p.TaxId, nav =>
{
    nav.Property(t => t.Value)
       .HasColumnName("TaxIdEncrypted")
       .HasMaxLength(512);
});

builder.OwnsOne(p => p.Balance, nav =>
{
    nav.Property(m => m.Amount).HasColumnName("BalanceAmount").HasColumnType("decimal(18,4)");
    nav.Property(m => m.Currency).HasColumnName("BalanceCurrency").HasMaxLength(3);
});
```

> **Invariants de VO:**
> - SEMPRE herdar de `ValueObject` (abstract record em SharedKernel)
> - NUNCA adicionar `{ get; set; }` — use positional constructor ou `init`
> - Validação via factory method estático `Create(...)` — nunca no constructor diretamente
> - EF Core: configurar como `OwnsOne` em `IEntityTypeConfiguration<T>` — NUNCA como entidade separada
> - `abstract record ValueObject` substitui `abstract class ValueObject<T>` — não usar a versão class

## Template: Entity com Domain Logic
```csharp
public sealed class Matricula : AggregateRoot<MatriculaId>
{
    public AlunoId AlunoId { get; private set; }
    public CursoId CursoId { get; private set; }
    public StatusMatricula Status { get; private set; }
    public DateOnly DataInicio { get; private set; }

    private Matricula() { } // EF Core

    public static Matricula Create(Guid alunoId, Guid cursoId, DateOnly dataInicio)
    {
        var matricula = new Matricula
        {
            Id = MatriculaId.New(),
            AlunoId = new AlunoId(alunoId),
            CursoId = new CursoId(cursoId),
            Status = StatusMatricula.Ativa,
            DataInicio = dataInicio
        };
        matricula.AddDomainEvent(new MatriculaCriadaEvent(matricula.Id));
        return matricula;
    }

    public void Aprovar()
    {
        if (Status != StatusMatricula.Ativa)
            throw new DomainException("Somente matrículas ativas podem ser aprovadas.");
        Status = StatusMatricula.Aprovada;
        AddDomainEvent(new MatriculaAprovadaEvent(Id));
    }
}
```
