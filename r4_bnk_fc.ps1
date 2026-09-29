$base = "projects\Meu-ERP\outputs\tobe\source-code"
function W { param($rel,$content)
  $abs = Join-Path $base $rel
  $p = Split-Path $abs -Parent
  if (!(Test-Path $p)) { New-Item $p -ItemType Directory -Force | Out-Null }
  Set-Content $abs $content -Encoding UTF8
}
# ── Banking ───────────────────────────────────────────────────────────────────
W "src\Banking\MeuERP.Banking.Domain\Aggregates\BankAccount.cs" @'
using MeuERP.SharedKernel.Domain.Primitives;
using MeuERP.Banking.Domain.Events;
namespace MeuERP.Banking.Domain.Aggregates;
public enum AccountType { Checking, Savings, Investment }
public sealed class BankAccount : AggregateRoot
{
    public string AccountNumber { get; private set; } = string.Empty;
    public string BankName { get; private set; } = string.Empty;
    public AccountType Type { get; private set; }
    public decimal Balance { get; private set; }
    public bool IsActive { get; private set; }
    public DateTime CreatedAt { get; private set; }
    private BankAccount() { }
    public static BankAccount Create(string accountNumber, string bankName, AccountType type, decimal initialBalance = 0)
    {
        var a = new BankAccount { AccountNumber = accountNumber, BankName = bankName, Type = type, Balance = initialBalance, IsActive = true, CreatedAt = DateTime.UtcNow };
        a.AddDomainEvent(new BankAccountCreatedEvent(a.Id, accountNumber, bankName));
        return a;
    }
    public void Credit(decimal amount, string description)
    {
        if (amount <= 0) throw new ArgumentOutOfRangeException(nameof(amount));
        Balance += amount;
        AddDomainEvent(new BankAccountCreditedEvent(Id, amount, Balance, description));
    }
    public void Debit(decimal amount, string description)
    {
        if (amount <= 0) throw new ArgumentOutOfRangeException(nameof(amount));
        if (amount > Balance) throw new InvalidOperationException("Insufficient balance.");
        Balance -= amount;
        AddDomainEvent(new BankAccountDebitedEvent(Id, amount, Balance, description));
    }
    public void Deactivate() => IsActive = false;
}
'@
W "src\Banking\MeuERP.Banking.Domain\Events\BankAccountCreatedEvent.cs" @'
using MeuERP.SharedKernel.Domain.Primitives;
namespace MeuERP.Banking.Domain.Events;
public sealed record BankAccountCreatedEvent(Guid AccountId, string AccountNumber, string BankName) : IDomainEvent;
'@
W "src\Banking\MeuERP.Banking.Domain\Events\BankAccountCreditedEvent.cs" @'
using MeuERP.SharedKernel.Domain.Primitives;
namespace MeuERP.Banking.Domain.Events;
public sealed record BankAccountCreditedEvent(Guid AccountId, decimal Amount, decimal NewBalance, string Description) : IDomainEvent;
'@
W "src\Banking\MeuERP.Banking.Domain\Events\BankAccountDebitedEvent.cs" @'
using MeuERP.SharedKernel.Domain.Primitives;
namespace MeuERP.Banking.Domain.Events;
public sealed record BankAccountDebitedEvent(Guid AccountId, decimal Amount, decimal NewBalance, string Description) : IDomainEvent;
'@
W "src\Banking\MeuERP.Banking.Domain\Repositories\IBankAccountRepository.cs" @'
using MeuERP.Banking.Domain.Aggregates;
namespace MeuERP.Banking.Domain.Repositories;
public interface IBankAccountRepository
{
    Task<BankAccount?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IEnumerable<BankAccount>> GetAllAsync(CancellationToken ct = default);
    Task AddAsync(BankAccount account, CancellationToken ct = default);
    Task UpdateAsync(BankAccount account, CancellationToken ct = default);
}
'@
W "src\Banking\MeuERP.Banking.Application\DTOs\BankAccountDto.cs" @'
using MeuERP.Banking.Domain.Aggregates;
namespace MeuERP.Banking.Application.DTOs;
public sealed record BankAccountDto(Guid Id, string AccountNumber, string BankName, AccountType Type, decimal Balance, bool IsActive, DateTime CreatedAt);
public sealed record CreateBankAccountRequest(string AccountNumber, string BankName, AccountType Type, decimal InitialBalance);
public sealed record TransactionRequest(decimal Amount, string Description);
'@
W "src\Banking\MeuERP.Banking.Application\Interfaces\IBankAccountService.cs" @'
using MeuERP.Banking.Application.DTOs;
using MeuERP.SharedKernel.Domain.Common;
namespace MeuERP.Banking.Application.Interfaces;
public interface IBankAccountService
{
    Task<Result<IEnumerable<BankAccountDto>>> GetAllAsync(CancellationToken ct = default);
    Task<Result<BankAccountDto>> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<Result<BankAccountDto>> CreateAsync(CreateBankAccountRequest request, CancellationToken ct = default);
    Task<Result> CreditAsync(Guid id, TransactionRequest request, CancellationToken ct = default);
    Task<Result> DebitAsync(Guid id, TransactionRequest request, CancellationToken ct = default);
}
'@
W "src\Banking\MeuERP.Banking.Application\Services\BankAccountService.cs" @'
using MeuERP.Banking.Application.DTOs;
using MeuERP.Banking.Application.Interfaces;
using MeuERP.Banking.Domain.Aggregates;
using MeuERP.Banking.Domain.Repositories;
using MeuERP.SharedKernel.Domain.Common;
namespace MeuERP.Banking.Application.Services;
public sealed class BankAccountService(IBankAccountRepository repo) : IBankAccountService
{
    public async Task<Result<IEnumerable<BankAccountDto>>> GetAllAsync(CancellationToken ct)
        => Result.Success((await repo.GetAllAsync(ct)).Select(ToDto));
    public async Task<Result<BankAccountDto>> GetByIdAsync(Guid id, CancellationToken ct)
    { var a = await repo.GetByIdAsync(id, ct); return a is null ? Result.Failure<BankAccountDto>(Error.NotFound("BankAccount")) : Result.Success(ToDto(a)); }
    public async Task<Result<BankAccountDto>> CreateAsync(CreateBankAccountRequest req, CancellationToken ct)
    { var a = BankAccount.Create(req.AccountNumber, req.BankName, req.Type, req.InitialBalance); await repo.AddAsync(a, ct); return Result.Success(ToDto(a)); }
    public async Task<Result> CreditAsync(Guid id, TransactionRequest req, CancellationToken ct)
    { var a = await repo.GetByIdAsync(id, ct); if (a is null) return Result.Failure(Error.NotFound("BankAccount")); a.Credit(req.Amount, req.Description); await repo.UpdateAsync(a, ct); return Result.Success(); }
    public async Task<Result> DebitAsync(Guid id, TransactionRequest req, CancellationToken ct)
    { var a = await repo.GetByIdAsync(id, ct); if (a is null) return Result.Failure(Error.NotFound("BankAccount")); a.Debit(req.Amount, req.Description); await repo.UpdateAsync(a, ct); return Result.Success(); }
    private static BankAccountDto ToDto(BankAccount a) => new(a.Id, a.AccountNumber, a.BankName, a.Type, a.Balance, a.IsActive, a.CreatedAt);
}
'@
W "src\Banking\MeuERP.Banking.Infrastructure\Persistence\BankingDbContext.cs" @'
using MeuERP.Banking.Domain.Aggregates;
using Microsoft.EntityFrameworkCore;
namespace MeuERP.Banking.Infrastructure.Persistence;
public sealed class BankingDbContext(DbContextOptions<BankingDbContext> options) : DbContext(options)
{
    public DbSet<BankAccount> BankAccounts => Set<BankAccount>();
    protected override void OnModelCreating(ModelBuilder mb)
    {
        mb.HasDefaultSchema("bnk");
        mb.Entity<BankAccount>(e => { e.HasKey(x => x.Id); e.Property(x => x.AccountNumber).HasMaxLength(50).IsRequired(); e.HasIndex(x => x.AccountNumber).IsUnique(); e.Property(x => x.BankName).HasMaxLength(200).IsRequired(); e.Property(x => x.Type).HasConversion<string>(); e.Property(x => x.Balance).HasColumnType("decimal(18,2)"); e.Ignore(x => x.DomainEvents); });
    }
}
'@
W "src\Banking\MeuERP.Banking.Infrastructure\Repositories\BankAccountRepository.cs" @'
using MeuERP.Banking.Domain.Aggregates;
using MeuERP.Banking.Domain.Repositories;
using MeuERP.Banking.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
namespace MeuERP.Banking.Infrastructure.Repositories;
public sealed class BankAccountRepository(BankingDbContext db) : IBankAccountRepository
{
    public Task<BankAccount?> GetByIdAsync(Guid id, CancellationToken ct) => db.BankAccounts.FirstOrDefaultAsync(x => x.Id == id, ct);
    public async Task<IEnumerable<BankAccount>> GetAllAsync(CancellationToken ct) => await db.BankAccounts.ToListAsync(ct);
    public async Task AddAsync(BankAccount a, CancellationToken ct) { db.BankAccounts.Add(a); await db.SaveChangesAsync(ct); }
    public async Task UpdateAsync(BankAccount a, CancellationToken ct) { db.BankAccounts.Update(a); await db.SaveChangesAsync(ct); }
}
'@
W "src\Banking\MeuERP.Banking.Infrastructure\DependencyInjection.cs" @'
using MeuERP.Banking.Application.Interfaces;
using MeuERP.Banking.Application.Services;
using MeuERP.Banking.Domain.Repositories;
using MeuERP.Banking.Infrastructure.Persistence;
using MeuERP.Banking.Infrastructure.Repositories;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
namespace MeuERP.Banking.Infrastructure;
public static class DependencyInjection
{
    public static IServiceCollection AddBankingInfrastructure(this IServiceCollection services, IConfiguration cfg)
    {
        services.AddDbContext<BankingDbContext>(o => o.UseSqlServer(cfg.GetConnectionString("Default")));
        services.AddScoped<IBankAccountRepository, BankAccountRepository>();
        services.AddScoped<IBankAccountService, BankAccountService>();
        return services;
    }
}
'@
W "src\Banking\MeuERP.Banking.Api\Modules\BankAccountModule.cs" @'
using Carter;
using MeuERP.Banking.Application.DTOs;
using MeuERP.Banking.Application.Interfaces;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
namespace MeuERP.Banking.Api.Modules;
public sealed class BankAccountModule : ICarterModule
{
    public void AddRoutes(IEndpointRouteBuilder app)
    {
        var grp = app.MapGroup("/api/bank-accounts").RequireAuthorization();
        grp.MapGet("/", async (IBankAccountService svc, CancellationToken ct) => Results.Ok((await svc.GetAllAsync(ct)).Value));
        grp.MapGet("/{id:guid}", async (Guid id, IBankAccountService svc, CancellationToken ct) => { var r = await svc.GetByIdAsync(id, ct); return r.IsSuccess ? Results.Ok(r.Value) : Results.NotFound(r.Error.Description); });
        grp.MapPost("/", async (CreateBankAccountRequest req, IBankAccountService svc, CancellationToken ct) => { var r = await svc.CreateAsync(req, ct); return r.IsSuccess ? Results.Created($"/api/bank-accounts/{r.Value.Id}", r.Value) : Results.BadRequest(r.Error.Description); });
        grp.MapPost("/{id:guid}/credit", async (Guid id, TransactionRequest req, IBankAccountService svc, CancellationToken ct) => { var r = await svc.CreditAsync(id, req, ct); return r.IsSuccess ? Results.NoContent() : Results.NotFound(r.Error.Description); });
        grp.MapPost("/{id:guid}/debit", async (Guid id, TransactionRequest req, IBankAccountService svc, CancellationToken ct) => { var r = await svc.DebitAsync(id, req, ct); return r.IsSuccess ? Results.NoContent() : Results.NotFound(r.Error.Description); });
    }
}
'@
foreach ($layer in @("Domain","Application","Infrastructure","Api")) {
  $name = "MeuERP.Banking.$layer"; $path = "src\Banking\$name\$name.csproj"
  $refs = switch ($layer) {
    "Domain" { '<ProjectReference Include="..\..\Shared\MeuERP.SharedKernel\MeuERP.SharedKernel.csproj" />' }
    "Application" { '<ProjectReference Include="..\MeuERP.Banking.Domain\MeuERP.Banking.Domain.csproj" />' }
    "Infrastructure" { '<PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="10.0.0" /><PackageReference Include="Dapper" Version="2.1.66" /></ItemGroup><ItemGroup><ProjectReference Include="..\MeuERP.Banking.Application\MeuERP.Banking.Application.csproj" />' }
    "Api" { '<PackageReference Include="Carter" Version="9.2.0" /></ItemGroup><ItemGroup><ProjectReference Include="..\MeuERP.Banking.Infrastructure\MeuERP.Banking.Infrastructure.csproj" />' }
  }
  W $path "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup>$refs</ItemGroup></Project>"
}
# ── FinancialConfig ───────────────────────────────────────────────────────────
W "src\FinancialConfig\MeuERP.FinancialConfig.Domain\Aggregates\CostCenter.cs" @'
using MeuERP.SharedKernel.Domain.Primitives;
namespace MeuERP.FinancialConfig.Domain.Aggregates;
public sealed class CostCenter : AggregateRoot
{
    public string Code { get; private set; } = string.Empty;
    public string Name { get; private set; } = string.Empty;
    public bool IsActive { get; private set; }
    public DateTime CreatedAt { get; private set; }
    private CostCenter() { }
    public static CostCenter Create(string code, string name)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(code);
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        return new CostCenter { Code = code, Name = name, IsActive = true, CreatedAt = DateTime.UtcNow };
    }
    public void Update(string name) => Name = name;
    public void Deactivate() => IsActive = false;
}
'@
W "src\FinancialConfig\MeuERP.FinancialConfig.Domain\Repositories\ICostCenterRepository.cs" @'
using MeuERP.FinancialConfig.Domain.Aggregates;
namespace MeuERP.FinancialConfig.Domain.Repositories;
public interface ICostCenterRepository
{
    Task<CostCenter?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IEnumerable<CostCenter>> GetAllAsync(CancellationToken ct = default);
    Task AddAsync(CostCenter costCenter, CancellationToken ct = default);
    Task UpdateAsync(CostCenter costCenter, CancellationToken ct = default);
}
'@
W "src\FinancialConfig\MeuERP.FinancialConfig.Application\DTOs\CostCenterDto.cs" @'
namespace MeuERP.FinancialConfig.Application.DTOs;
public sealed record CostCenterDto(Guid Id, string Code, string Name, bool IsActive, DateTime CreatedAt);
public sealed record CreateCostCenterRequest(string Code, string Name);
public sealed record UpdateCostCenterRequest(string Name);
'@
W "src\FinancialConfig\MeuERP.FinancialConfig.Application\Interfaces\ICostCenterService.cs" @'
using MeuERP.FinancialConfig.Application.DTOs;
using MeuERP.SharedKernel.Domain.Common;
namespace MeuERP.FinancialConfig.Application.Interfaces;
public interface ICostCenterService
{
    Task<Result<IEnumerable<CostCenterDto>>> GetAllAsync(CancellationToken ct = default);
    Task<Result<CostCenterDto>> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<Result<CostCenterDto>> CreateAsync(CreateCostCenterRequest request, CancellationToken ct = default);
    Task<Result> UpdateAsync(Guid id, UpdateCostCenterRequest request, CancellationToken ct = default);
}
'@
W "src\FinancialConfig\MeuERP.FinancialConfig.Application\Services\CostCenterService.cs" @'
using MeuERP.FinancialConfig.Application.DTOs;
using MeuERP.FinancialConfig.Application.Interfaces;
using MeuERP.FinancialConfig.Domain.Aggregates;
using MeuERP.FinancialConfig.Domain.Repositories;
using MeuERP.SharedKernel.Domain.Common;
namespace MeuERP.FinancialConfig.Application.Services;
public sealed class CostCenterService(ICostCenterRepository repo) : ICostCenterService
{
    public async Task<Result<IEnumerable<CostCenterDto>>> GetAllAsync(CancellationToken ct)
        => Result.Success((await repo.GetAllAsync(ct)).Select(ToDto));
    public async Task<Result<CostCenterDto>> GetByIdAsync(Guid id, CancellationToken ct)
    { var c = await repo.GetByIdAsync(id, ct); return c is null ? Result.Failure<CostCenterDto>(Error.NotFound("CostCenter")) : Result.Success(ToDto(c)); }
    public async Task<Result<CostCenterDto>> CreateAsync(CreateCostCenterRequest req, CancellationToken ct)
    { var c = CostCenter.Create(req.Code, req.Name); await repo.AddAsync(c, ct); return Result.Success(ToDto(c)); }
    public async Task<Result> UpdateAsync(Guid id, UpdateCostCenterRequest req, CancellationToken ct)
    { var c = await repo.GetByIdAsync(id, ct); if (c is null) return Result.Failure(Error.NotFound("CostCenter")); c.Update(req.Name); await repo.UpdateAsync(c, ct); return Result.Success(); }
    private static CostCenterDto ToDto(CostCenter c) => new(c.Id, c.Code, c.Name, c.IsActive, c.CreatedAt);
}
'@
W "src\FinancialConfig\MeuERP.FinancialConfig.Infrastructure\Persistence\FinancialConfigDbContext.cs" @'
using MeuERP.FinancialConfig.Domain.Aggregates;
using Microsoft.EntityFrameworkCore;
namespace MeuERP.FinancialConfig.Infrastructure.Persistence;
public sealed class FinancialConfigDbContext(DbContextOptions<FinancialConfigDbContext> options) : DbContext(options)
{
    public DbSet<CostCenter> CostCenters => Set<CostCenter>();
    protected override void OnModelCreating(ModelBuilder mb)
    {
        mb.HasDefaultSchema("fc");
        mb.Entity<CostCenter>(e => { e.HasKey(x => x.Id); e.Property(x => x.Code).HasMaxLength(20).IsRequired(); e.HasIndex(x => x.Code).IsUnique(); e.Property(x => x.Name).HasMaxLength(200).IsRequired(); e.Ignore(x => x.DomainEvents); });
    }
}
'@
W "src\FinancialConfig\MeuERP.FinancialConfig.Infrastructure\Repositories\CostCenterDapperRepository.cs" @'
using Dapper;
using MeuERP.FinancialConfig.Domain.Aggregates;
using MeuERP.FinancialConfig.Domain.Repositories;
using MeuERP.FinancialConfig.Infrastructure.Persistence;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;
namespace MeuERP.FinancialConfig.Infrastructure.Repositories;
public sealed class CostCenterDapperRepository(IConfiguration cfg, FinancialConfigDbContext db) : ICostCenterRepository
{
    private SqlConnection CreateConnection() => new(cfg.GetConnectionString("Default"));
    public async Task<CostCenter?> GetByIdAsync(Guid id, CancellationToken ct)
    {
        using var conn = CreateConnection();
        var row = await conn.QueryFirstOrDefaultAsync<dynamic>("SELECT Code, Name FROM fc.CostCenters WHERE Id = @Id", new { Id = id });
        return row is null ? null : CostCenter.Create((string)row.Code, (string)row.Name);
    }
    public async Task<IEnumerable<CostCenter>> GetAllAsync(CancellationToken ct)
    {
        using var conn = CreateConnection();
        var rows = await conn.QueryAsync<dynamic>("SELECT Code, Name FROM fc.CostCenters WHERE IsActive = 1 ORDER BY Code");
        return rows.Select(r => CostCenter.Create((string)r.Code, (string)r.Name)).ToList();
    }
    public async Task AddAsync(CostCenter c, CancellationToken ct) { db.CostCenters.Add(c); await db.SaveChangesAsync(ct); }
    public async Task UpdateAsync(CostCenter c, CancellationToken ct) { db.CostCenters.Update(c); await db.SaveChangesAsync(ct); }
}
'@
W "src\FinancialConfig\MeuERP.FinancialConfig.Infrastructure\DependencyInjection.cs" @'
using MeuERP.FinancialConfig.Application.Interfaces;
using MeuERP.FinancialConfig.Application.Services;
using MeuERP.FinancialConfig.Domain.Repositories;
using MeuERP.FinancialConfig.Infrastructure.Persistence;
using MeuERP.FinancialConfig.Infrastructure.Repositories;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
namespace MeuERP.FinancialConfig.Infrastructure;
public static class DependencyInjection
{
    public static IServiceCollection AddFinancialConfigInfrastructure(this IServiceCollection services, IConfiguration cfg)
    {
        services.AddDbContext<FinancialConfigDbContext>(o => o.UseSqlServer(cfg.GetConnectionString("Default")));
        services.AddScoped<ICostCenterRepository, CostCenterDapperRepository>();
        services.AddScoped<ICostCenterService, CostCenterService>();
        return services;
    }
}
'@
W "src\FinancialConfig\MeuERP.FinancialConfig.Api\Modules\CostCenterModule.cs" @'
using Carter;
using MeuERP.FinancialConfig.Application.DTOs;
using MeuERP.FinancialConfig.Application.Interfaces;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
namespace MeuERP.FinancialConfig.Api.Modules;
public sealed class CostCenterModule : ICarterModule
{
    public void AddRoutes(IEndpointRouteBuilder app)
    {
        var grp = app.MapGroup("/api/cost-centers").RequireAuthorization();
        grp.MapGet("/", async (ICostCenterService svc, CancellationToken ct) => Results.Ok((await svc.GetAllAsync(ct)).Value));
        grp.MapGet("/{id:guid}", async (Guid id, ICostCenterService svc, CancellationToken ct) => { var r = await svc.GetByIdAsync(id, ct); return r.IsSuccess ? Results.Ok(r.Value) : Results.NotFound(r.Error.Description); });
        grp.MapPost("/", async (CreateCostCenterRequest req, ICostCenterService svc, CancellationToken ct) => { var r = await svc.CreateAsync(req, ct); return r.IsSuccess ? Results.Created($"/api/cost-centers/{r.Value.Id}", r.Value) : Results.BadRequest(r.Error.Description); });
        grp.MapPut("/{id:guid}", async (Guid id, UpdateCostCenterRequest req, ICostCenterService svc, CancellationToken ct) => { var r = await svc.UpdateAsync(id, req, ct); return r.IsSuccess ? Results.NoContent() : Results.NotFound(r.Error.Description); });
    }
}
'@
foreach ($layer in @("Domain","Application","Infrastructure","Api")) {
  $name = "MeuERP.FinancialConfig.$layer"; $path = "src\FinancialConfig\$name\$name.csproj"
  $refs = switch ($layer) {
    "Domain" { '<ProjectReference Include="..\..\Shared\MeuERP.SharedKernel\MeuERP.SharedKernel.csproj" />' }
    "Application" { '<ProjectReference Include="..\MeuERP.FinancialConfig.Domain\MeuERP.FinancialConfig.Domain.csproj" />' }
    "Infrastructure" { '<PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="10.0.0" /><PackageReference Include="Dapper" Version="2.1.66" /><PackageReference Include="Microsoft.Data.SqlClient" Version="5.2.2" /></ItemGroup><ItemGroup><ProjectReference Include="..\MeuERP.FinancialConfig.Application\MeuERP.FinancialConfig.Application.csproj" />' }
    "Api" { '<PackageReference Include="Carter" Version="9.2.0" /></ItemGroup><ItemGroup><ProjectReference Include="..\MeuERP.FinancialConfig.Infrastructure\MeuERP.FinancialConfig.Infrastructure.csproj" />' }
  }
  W $path "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup>$refs</ItemGroup></Project>"
}
$bnk = (Get-ChildItem "$base\src\Banking" -Recurse -Filter "*.cs" | Where-Object { $_.FullName -notlike '*obj*' }).Count
$fc  = (Get-ChildItem "$base\src\FinancialConfig" -Recurse -Filter "*.cs" | Where-Object { $_.FullName -notlike '*obj*' }).Count
Write-Host "Banking .cs=$bnk  FC .cs=$fc"
