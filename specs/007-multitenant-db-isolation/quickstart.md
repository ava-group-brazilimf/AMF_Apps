# Quickstart: multitenant-db-isolation (PBI 2309)

**Phase 1 — Validation Guide**
**Date**: 2026-07-08

This guide describes how to validate that the multitenant scaffolding was generated correctly and that tenant isolation is enforced. It does not contain implementation code — see `data-model.md` for type definitions and `tasks.md` for implementation steps.

---

## Prerequisites

Before running validation:

1. A project with `pipeline_mode: build-cycle` configured in `project-config.yaml`
2. `persistence.multi_tenancy.enabled: true` and `persistence.multi_tenancy.strategy: "shared-table"` set
3. `ava-build-cycle-dotnet-scaffold` has already executed (bounded contexts exist under `outputs/tobe/source-code/`)
4. `ava-build-cycle-efcore` has been invoked with the multitenant step

---

## Validation 1 — File Existence Check

All 3 C# template files must exist per bounded context.

```powershell
# Run from repo root — substitute {PROJECT} and {BC} with real values
$base = "projects/{PROJECT}/outputs/tobe/source-code"
$bc   = "{BC}"          # e.g. "Financeiro"
$pfx  = "{Prefix}"      # e.g. "MyErp"

$expected = @(
    "$base/$bc/src/$bc/$pfx.$bc.Infrastructure/Multitenancy/TenantResolutionMiddleware.cs",
    "$base/$bc/src/$bc/$pfx.$bc.Infrastructure/Persistence/$($bc)DbContext.cs",
    "$base/$bc/src/$bc/$pfx.$bc.Infrastructure/Multitenancy/KeyVaultTenantConnectionStringResolver.cs"
)

$missing = $expected | Where-Object { -not (Test-Path $_) }
if ($missing.Count -eq 0) {
    Write-Host "✅ All 3 multitenant files found" -ForegroundColor Green
} else {
    Write-Host "❌ Missing files:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" }
}
```

**Expected output**: `✅ All 3 multitenant files found`

---

## Validation 2 — AppDbContext Inheritance Check

Verify that `AppDbContext.cs` inherits from `EFCoreDbContext<TenantInfo>`.

```powershell
$dbCtxPath = "projects/{PROJECT}/outputs/tobe/source-code/{BC}/src/{BC}/{Prefix}.{BC}.Infrastructure/Persistence/{BC}DbContext.cs"

$content = Get-Content $dbCtxPath -Raw
$checks = @{
    "Inherits EFCoreDbContext<TenantInfo>"    = $content -match "EFCoreDbContext<TenantInfo>"
    "Implements IUnitOfWork"                   = $content -match "IUnitOfWork"
    "base.OnModelCreating first"               = $content -match "base\.OnModelCreating\(modelBuilder\)"
    "No EF Core import in Domain/Application"  = $true   # structural check — see Validation 4
}

$checks.GetEnumerator() | ForEach-Object {
    $icon = if ($_.Value) { "✅" } else { "❌" }
    Write-Host "$icon $($_.Key)"
}
```

**Expected output**: All 4 lines with `✅`.

---

## Validation 3 — TenantResolutionMiddleware Header + JWT Coverage

Verify both resolution strategies are present in the middleware.

```powershell
$mwPath = "projects/{PROJECT}/outputs/tobe/source-code/{BC}/src/{BC}/{Prefix}.{BC}.Infrastructure/Multitenancy/TenantResolutionMiddleware.cs"

$content = Get-Content $mwPath -Raw
$checks = @{
    "X-Tenant-Id header resolution" = $content -match "X-Tenant-Id"
    "JWT claim tid fallback"         = $content -match '"tid"'
    "400 Bad Request on no tenant"   = $content -match "400|BadRequest"
}

$checks.GetEnumerator() | ForEach-Object {
    $icon = if ($_.Value) { "✅" } else { "❌" }
    Write-Host "$icon $($_.Key)"
}
```

**Expected output**: All 3 lines with `✅`.

---

## Validation 4 — EF Core Layer Boundary (No Leakage)

Verify that `Microsoft.EntityFrameworkCore` does NOT appear in Domain or Application `.csproj` files.

```powershell
$srcBase = "projects/{PROJECT}/outputs/tobe/source-code/{BC}/src/{BC}"

Get-ChildItem -Path $srcBase -Include "*.csproj" -Recurse |
    Where-Object { $_.FullName -match "\.Domain\." -or $_.FullName -match "\.Application\." } |
    ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        if ($content -match "EntityFrameworkCore|Finbuckle") {
            Write-Host "❌ EF/Finbuckle reference in: $($_.Name)" -ForegroundColor Red
        } else {
            Write-Host "✅ Clean boundary: $($_.Name)" -ForegroundColor Green
        }
    }
```

**Expected output**: All files with `✅ Clean boundary`.

---

## Validation 5 — Regression: Non-Multitenant Project Unaffected

Verify that a project with `persistence.multi_tenancy.enabled: false` generates NO multitenant files.

```powershell
# In a test project with multi_tenancy.enabled: false
$mtFiles = Get-ChildItem -Path "projects/{NON_MT_PROJECT}/outputs/tobe/source-code" -Recurse |
    Where-Object { $_.Name -match "TenantResolution|KeyVaultTenant|EFCoreDbContext" }

if ($mtFiles.Count -eq 0) {
    Write-Host "✅ No multitenant files generated in non-MT project" -ForegroundColor Green
} else {
    Write-Host "❌ Unexpected multitenant files found:" -ForegroundColor Red
    $mtFiles | ForEach-Object { Write-Host "  - $($_.FullName)" }
}
```

**Expected output**: `✅ No multitenant files generated in non-MT project`

---

## Validation 6 — Multi-tenant EF Core Setup Section in efcore agent

Verify the documentation section was added to `build-cycle-efcore-agent.md`.

```powershell
$agentPath = "src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-efcore-agent.md"
$content = Get-Content $agentPath -Raw

$checks = @{
    "Multi-tenant EF Core Setup heading" = $content -match "## Multi-tenant EF Core Setup"
    "Finbuckle.MultiTenant reference"     = $content -match "Finbuckle\.MultiTenant"
    "Migration isolation note"            = $content -match "schema-per-tenant|migration.*tenant"
}

$checks.GetEnumerator() | ForEach-Object {
    $icon = if ($_.Value) { "✅" } else { "❌" }
    Write-Host "$icon $($_.Key)"
}
```

**Expected output**: All 3 lines with `✅`.

---

## Validation 7 — Build Smoke Test (Optional, requires .NET SDK)

If a generated project is available:

```bash
# From the generated solution root
dotnet build --no-restore --verbosity quiet
# Expected: Build succeeded with 0 error(s), 0 warning(s)
```

---

## Pass Criteria

| Validation | Required | Notes |
|---|---|---|
| V1 — File existence | ✅ Mandatory | Gates all other validations |
| V2 — DbContext inheritance | ✅ Mandatory | Core isolation mechanism |
| V3 — Middleware coverage | ✅ Mandatory | AC: header + JWT resolution |
| V4 — Layer boundary | ✅ Mandatory | Constitution Article IX |
| V5 — Regression guard | ✅ Mandatory | AC: non-MT projects unaffected |
| V6 — Documentation section | ✅ Mandatory | AC: EF Core Setup section present |
| V7 — Build smoke test | Optional | Only if .NET SDK available |

All mandatory validations must pass before tasks are considered complete.
