#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Gate de validação pré-entrega para projetos .NET gerados pelo AVA.
    Executar do root do source-code (onde MeuERP.sln ou equivalente reside).

.DESCRIPTION
    5 gates sequenciais obrigatórios antes de declarar COMPLETED no trigger SC.
    Saída: ✅ GO (exit 0) ou ❌ BLOCKED com lista de issues (exit 1).

.EXAMPLE
    pwsh src/shared/checks/validate-dotnet-build.ps1
    # executar do root do source-code (pasta que contém o .sln)
#>

param(
    [string]$SolutionRoot = $PWD
)

Set-Location $SolutionRoot

$issues = @()
$passed = @()

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  AVA .NET Build Gate — validação pré-entrega"
Write-Host "  Root: $SolutionRoot"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# ─────────────────────────────────────────────────────────────────────────────
# GATE 1 — Directory.Packages.props existe e CPM está ativo
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "Gate 1 — Directory.Packages.props + ManagePackageVersionsCentrally..."
if (-not (Test-Path "Directory.Packages.props")) {
    $issues += "GATE1: Directory.Packages.props AUSENTE — CPM inativo. Criar com ManagePackageVersionsCentrally=true antes de qualquer .csproj."
} else {
    $cpmContent = Get-Content "Directory.Packages.props" -Raw
    if ($cpmContent -notmatch "ManagePackageVersionsCentrally\s*>\s*true") {
        $issues += "GATE1: ManagePackageVersionsCentrally=true ausente em Directory.Packages.props — CPM não está ativo."
    } elseif ($cpmContent -notmatch "NuGetAudit\s*>\s*true") {
        $issues += "GATE1: NuGetAudit=true ausente em Directory.Packages.props — vulnerabilidades não serão detectadas no build."
    } else {
        $passed += "Gate 1 ✅ — CPM ativo + NuGetAudit=true"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE 2 — Zero Version= inline em qualquer .csproj (exceto VersionOverride)
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "Gate 2 — Version= inline nos .csproj..."
$inlineVersions = Get-ChildItem -Recurse -Filter "*.csproj" |
    Select-String 'Version=' |
    Where-Object { $_.Line -notmatch 'VersionOverride' -and $_.Line -match 'PackageReference' }

if ($inlineVersions.Count -gt 0) {
    $detail = $inlineVersions | ForEach-Object { "  $($_.Filename):$($_.LineNumber) → $($_.Line.Trim())" }
    $issues += "GATE2: $($inlineVersions.Count) PackageReference(s) com Version= inline encontrados (Regra #18 + #21):`n$($detail -join "`n")"
} else {
    $passed += "Gate 2 ✅ — Zero Version= inline"
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE 3 — Domain.csproj: SharedKernel com exatamente 2 níveis (..\..\)
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "Gate 3 — SharedKernel path nos Domain.csproj (2 níveis exatos)..."
$domainFiles = Get-ChildItem -Recurse -Filter "*.csproj" | Where-Object { $_.Name -match '\.Domain\.csproj$' }
$badPaths = @()
foreach ($f in $domainFiles) {
    $content = Get-Content $f.FullName -Raw
    # Detecta 3 ou mais níveis ..\ antes de SharedKernel
    if ($content -match '\.\.[/\\]\.\.[/\\]\.\.[/\\].*SharedKernel') {
        $badPaths += "  $($f.Name) → 3+ níveis detectados (deve ser ..\..\SharedKernel\)"
    }
}
if ($badPaths.Count -gt 0) {
    $issues += "GATE3: $($badPaths.Count) Domain.csproj(s) com path errado para SharedKernel (Regra #20):`n$($badPaths -join "`n")"
} else {
    $passed += "Gate 3 ✅ — SharedKernel com 2 níveis em todos os Domain.csproj"
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE 4 — dotnet build: zero NU1605, NU1603, NU1902, NU1903, error CS
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "Gate 4 — dotnet restore + build (NU1605|NU1603|NU1902|NU1903|error CS)..."
Write-Host "  (pode levar alguns minutos...)"
$restoreOut = dotnet restore 2>&1
$buildOut = dotnet build --no-incremental 2>&1
$buildIssues = $buildOut | Where-Object { $_ -match "NU1605|NU1603|NU1902|NU1903|error CS" }
$errorCount = ($buildOut | Where-Object { $_ -match "Error\(s\)" } | ForEach-Object {
    if ($_ -match '(\d+) Error') { [int]$matches[1] } else { 0 }
} | Measure-Object -Sum).Sum

if ($buildIssues.Count -gt 0 -or $errorCount -gt 0) {
    $detail = $buildIssues | Select-Object -First 20 | ForEach-Object { "  $_" }
    $issues += "GATE4: Build com $errorCount erro(s) e $($buildIssues.Count) warning(s) NU/CS bloqueantes:`n$($detail -join "`n")"
} else {
    $passed += "Gate 4 ✅ — Build limpo (0 NU1603/NU1605/NU1902/NU1903/CS errors)"
}

# ─────────────────────────────────────────────────────────────────────────────
# GATE 5 — Zero CVEs em qualquer pacote (direto ou transitivo)
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "Gate 5 — dotnet list package --vulnerable --include-transitive..."
$vulnOut = dotnet list package --vulnerable --include-transitive 2>&1
$hasVuln = $vulnOut | Where-Object { $_ -match "has the following vulnerable packages" -or ($_ -match '(Critical|High|Moderate|Low)' -and $_ -match '>') }

if ($hasVuln.Count -gt 0) {
    $detail = $vulnOut | Where-Object { $_ -match 'Critical|High|Moderate|Low|GHSA' } | Select-Object -First 20 | ForEach-Object { "  $_" }
    $issues += "GATE5: CVEs detectados (zero tolerância — toda severidade bloqueia):`n$($detail -join "`n")"
} else {
    $passed += "Gate 5 ✅ — No vulnerable packages"
}

# ─────────────────────────────────────────────────────────────────────────────
# RESULTADO FINAL
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
foreach ($p in $passed) { Write-Host "  $p" }

if ($issues.Count -eq 0) {
    Write-Host ""
    Write-Host "  ✅ GO — todos os $($passed.Count) gates passaram"
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host ""
    exit 0
} else {
    Write-Host ""
    Write-Host "  ❌ BLOCKED — $($issues.Count) gate(s) falharam:"
    Write-Host ""
    foreach ($issue in $issues) {
        Write-Host "  $issue"
        Write-Host ""
    }
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host "  ⛔ NUNCA declarar COMPLETED com saída BLOCKED"
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host ""
    exit 1
}
