<#
.SYNOPSIS
    Remonta artefatos HTML quebrados em *.partN.html num arquivo unico, valida e loga.

.DESCRIPTION
    Wrapper PowerShell de src/shared/tools/merge_html_parts.py.

    Agentes que emitem HTML grande (ava-summary / F8, ava-prototype / F3) estouram o
    limite de tokens de saida e gravam o artefato em fragmentos `*.partN.html`. Nenhum
    fragmento abre corretamente no browser. Este script:

      1. Recebe a pasta com os fragmentos          (-InputDir)
      2. Reagrupa os fragmentos num arquivo unico  (deteccao automatica da modalidade
                                                    de quebra: sequential ou splice)
      3. Valida o arquivo unico                    (aninhamento de tags, singletons,
                                                    ids duplicados, handlers inline sem
                                                    funcao, alvos de navegacao quebrados)
      4. Grava o resultado na pasta de destino     (-OutputDir, padrao = -InputDir)
      5. Imprime o log completo do processo        (+ -LogFile e -Report opcionais)

    O wrapper localiza o Python, resolve o caminho do .py relativo a si mesmo,
    valida os argumentos antes de chamar e traduz o exit code do Python.

.PARAMETER InputDir
    Pasta que contem os fragmentos *.partN.html. Obrigatorio.

.PARAMETER OutputDir
    Pasta onde o arquivo unico sera gravado. Padrao: a propria pasta dos fragmentos.

.PARAMETER Recursive
    Varre tambem as subpastas de -InputDir procurando grupos de fragmentos.

.PARAMETER DryRun
    Executa a remontagem e a validacao sem gravar nada em disco.

.PARAMETER Force
    Grava o arquivo unico mesmo se a validacao encontrar erros.

.PARAMETER LogFile
    Alem do console, grava o log do processo neste arquivo.

.PARAMETER Report
    Grava um relatorio JSON (grupos, metricas, log completo) neste arquivo.

.PARAMETER PythonExe
    Executavel Python a usar. Padrao: autodeteccao (py -3 -> python -> python3).

.EXAMPLE
    .\Merge-HtmlParts.ps1 -InputDir projects\MeuERP-004-cli-ava\outputs\summary

.EXAMPLE
    .\Merge-HtmlParts.ps1 -InputDir projects\MeuERP-004-cli-ava\outputs `
                          -Recursive -Report merge-report.json

.EXAMPLE
    .\Merge-HtmlParts.ps1 -InputDir .\outputs\tobe\prototype -OutputDir .\dist -DryRun

.OUTPUTS
    Exit code 0 = todos os grupos remontados e validados
               1 = falha de remontagem ou de validacao
               2 = nenhum fragmento *.partN.html encontrado
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$InputDir,

    [Parameter()]
    [string]$OutputDir,

    [Parameter()]
    [switch]$Recursive,

    [Parameter()]
    [switch]$DryRun,

    [Parameter()]
    [switch]$Force,

    [Parameter()]
    [string]$LogFile,

    [Parameter()]
    [string]$Report,

    [Parameter()]
    [string]$PythonExe
)

$ErrorActionPreference = 'Stop'

function Write-Head([string]$Text) {
    Write-Host ""
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "  $('-' * $Text.Length)" -ForegroundColor DarkGray
}

function Resolve-Python {
    param([string]$Preferred)

    if ($Preferred) {
        $cmd = Get-Command $Preferred -ErrorAction SilentlyContinue
        if (-not $cmd) { throw "PythonExe '$Preferred' nao encontrado no PATH." }
        return @($cmd.Source)
    }
    # 'py -3' primeiro: no Windows e o launcher oficial e resolve versoes multiplas
    if (Get-Command 'py' -ErrorAction SilentlyContinue) { return @('py', '-3') }
    foreach ($c in 'python', 'python3') {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if ($cmd) { return @($cmd.Source) }
    }
    throw "Python nao encontrado no PATH. Instale Python 3.10+ ou informe -PythonExe."
}

Write-Head "Merge-HtmlParts — remontagem de artefatos HTML fragmentados"

# ── 1. Localizar o script Python (relativo a este .ps1) ──────────────────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyScript = Join-Path $scriptDir 'merge_html_parts.py'
if (-not (Test-Path -LiteralPath $pyScript -PathType Leaf)) {
    Write-Host "  [ERRO] motor Python nao encontrado: $pyScript" -ForegroundColor Red
    exit 1
}

# ── 2. Validar a pasta de entrada ────────────────────────────────────────────
if (-not (Test-Path -LiteralPath $InputDir -PathType Container)) {
    Write-Host "  [ERRO] pasta de entrada nao existe: $InputDir" -ForegroundColor Red
    exit 1
}
$inputFull = (Resolve-Path -LiteralPath $InputDir).Path

$partFilter = @{ Path = $inputFull; Filter = '*.part*.html'; File = $true }
if ($Recursive) { $partFilter.Recurse = $true }
$found = @(Get-ChildItem @partFilter -ErrorAction SilentlyContinue)
if ($found.Count -eq 0) {
    Write-Host "  [AVISO] nenhum arquivo *.partN.html em $inputFull" -ForegroundColor Yellow
    Write-Host "          use -Recursive para varrer as subpastas." -ForegroundColor DarkGray
    exit 2
}

# ── 3. Resolver Python ───────────────────────────────────────────────────────
try { $python = Resolve-Python -Preferred $PythonExe }
catch { Write-Host "  [ERRO] $_" -ForegroundColor Red; exit 1 }

$pyVersion = (& $python[0] $python[1..($python.Count - 1)] --version 2>&1 | Select-Object -First 1)

Write-Host "  Entrada  : $inputFull"
Write-Host "  Saida    : $(if ($OutputDir) { $OutputDir } else { '<a propria pasta dos fragmentos>' })"
Write-Host "  Fragmentos: $($found.Count) arquivo(s) *.partN.html"
Write-Host "  Motor    : $pyScript"
Write-Host "  Python   : $($python -join ' ')  ($pyVersion)"
if ($DryRun) { Write-Host "  Modo     : DRY-RUN (nada sera gravado)" -ForegroundColor Yellow }
if ($Force) { Write-Host "  Modo     : FORCE (grava mesmo com erro de validacao)" -ForegroundColor Yellow }

# ── 4. Montar argumentos e invocar ───────────────────────────────────────────
$pyArgs = @($pyScript, '--input-dir', $inputFull)
if ($OutputDir) { $pyArgs += @('--output-dir', $OutputDir) }
if ($Recursive) { $pyArgs += '--recursive' }
if ($DryRun) { $pyArgs += '--dry-run' }
if ($Force) { $pyArgs += '--force' }
if ($LogFile) { $pyArgs += @('--log-file', $LogFile) }
if ($Report) { $pyArgs += @('--report', $Report) }

Write-Head "Log do processo"

$env:PYTHONIOENCODING = 'utf-8'
& $python[0] @($python[1..($python.Count - 1)] + $pyArgs)
$code = $LASTEXITCODE

# ── 5. Traduzir o resultado ──────────────────────────────────────────────────
Write-Head "Resultado"
switch ($code) {
    0 {
        Write-Host "  [OK] Todos os grupos foram remontados e validados." -ForegroundColor Green
        if (-not $DryRun) {
            $dest = if ($OutputDir) { $OutputDir } else { $inputFull }
            if (Test-Path -LiteralPath $dest) {
                Get-ChildItem -LiteralPath $dest -Filter '*.html' -File |
                    Where-Object { $_.Name -notlike '*.part*.html' } |
                    Sort-Object LastWriteTime -Descending | Select-Object -First 5 |
                    ForEach-Object { Write-Host ("       {0,10:N0} bytes  {1}" -f $_.Length, $_.FullName) }
            }
        }
    }
    1 { Write-Host "  [FALHA] Remontagem ou validacao falhou — veja os [ERROR] acima." -ForegroundColor Red }
    2 { Write-Host "  [NOOP] Nenhum grupo *.partN.html encontrado." -ForegroundColor Yellow }
    default { Write-Host "  [FALHA] Python terminou com exit code $code." -ForegroundColor Red }
}
if ($LogFile) { Write-Host "  Log     : $LogFile" }
if ($Report) { Write-Host "  Relatorio: $Report" }
Write-Host ""

exit $code
