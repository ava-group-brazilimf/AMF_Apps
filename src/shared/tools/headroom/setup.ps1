<#
.SYNOPSIS
    Cria o venv isolado da tool Headroom e instala o motor.

.DESCRIPTION
    O venv fica em src/shared/tools/headroom/.venv e NAO contamina o venv
    principal do repositorio (invariante IV7 - o repo e stdlib-only).

    O fork embedded (./vendor, git subtree de headroom-ai 0.33.0) usa maturin
    como build backend, que exige toolchain Rust. Este script:

    * com `cargo` no PATH  -> instala o fork em modo editavel (`pip install -e ./vendor`),
                                de modo que patches locais no vendor valem imediatamente;
    * sem `cargo`          -> instala o wheel PyPI da MESMA versao do vendor.
                      O fork continua versionado e serve de referencia/patch
                      source, mas o que roda e o wheel pre-compilado.

.PARAMETER SkipML
    Nao instala o extra [ml] (torch + transformers, ~3 GB). A compressao
    estrutural e o proxy continuam funcionando; so o Kompress ML fica de fora.

.PARAMETER Force
    Recria o venv do zero.

.EXAMPLE
    .\src\shared\tools\headroom\setup.ps1
    .\src\shared\tools\headroom\setup.ps1 -SkipML
#>
[CmdletBinding()]
param(
    [switch]$SkipML,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$ToolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ToolDir '.venv'
$Vendor  = Join-Path $ToolDir 'vendor'
$Reqs    = Join-Path $ToolDir 'requirements.txt'

Write-Host ''
Write-Host '=== AVA Fabric :: Headroom Tool :: setup ===' -ForegroundColor Cyan
Write-Host "  tool   : $ToolDir"
Write-Host "  venv   : $VenvDir"
Write-Host "  vendor : $Vendor"

if (-not (Test-Path (Join-Path $Vendor 'pyproject.toml'))) {
    Write-Error "Fork ausente em $Vendor. Restaure com: git subtree add --prefix src/shared/tools/headroom/vendor https://github.com/headroomlabs-ai/headroom.git main --squash"
}

# -- Versao do Python ----------------------------------------------------------
$pyVersion = (python -c "import sys; print('%d.%d' % sys.version_info[:2])").Trim()
Write-Host "  python : $pyVersion"
if ([version]$pyVersion -lt [version]'3.10') {
    Write-Error "Python >= 3.10 exigido pelo headroom-ai (encontrado $pyVersion)."
}

# -- venv ----------------------------------------------------------------------
if ($Force -and (Test-Path $VenvDir)) {
    Write-Host '  removendo venv existente (-Force)...' -ForegroundColor Yellow
    Remove-Item -Recurse -Force $VenvDir
}
if (-not (Test-Path $VenvDir)) {
    Write-Host '  criando venv...' -ForegroundColor Yellow
    python -m venv $VenvDir
}

$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-Path $VenvPy)) { $VenvPy = Join-Path $VenvDir 'bin/python' }
if (-not (Test-Path $VenvPy)) { Write-Error "Interpretador do venv nao encontrado em $VenvDir" }

& $VenvPy -m pip install --upgrade pip setuptools wheel --quiet

# -- Extras --------------------------------------------------------------------
$extras = if ($SkipML) { 'proxy,mcp,code,memory,otel' } else { 'proxy,mcp,ml,code,memory,otel' }
if ($SkipML) {
    Write-Host '  extras : sem [ml] (-SkipML) - Kompress ML indisponivel' -ForegroundColor Yellow
} else {
    Write-Host "  extras : $extras  (inclui torch, ~3 GB - use -SkipML para pular)"
}

# -- Instalacao: fork editavel se houver Rust, senao wheel PyPI ----------------
$hasCargo = $null -ne (Get-Command cargo -ErrorAction SilentlyContinue)
if ($hasCargo) {
    Write-Host '  modo   : fork EDITAVEL (cargo encontrado - build via maturin)' -ForegroundColor Green
    & $VenvPy -m pip install -e "$Vendor[$extras]"
} else {
    $vendorVersion = (Select-String -Path (Join-Path $Vendor 'pyproject.toml') -Pattern '^version\s*=\s*"([^"]+)"' |
        Select-Object -First 1).Matches.Groups[1].Value
    Write-Host "  modo   : wheel PyPI headroom-ai==$vendorVersion (cargo ausente)" -ForegroundColor Yellow
    Write-Host '           O fork em ./vendor fica como referencia/patch source.'
    Write-Host '           Instale Rust (https://rustup.rs) e rode de novo para buildar o fork.'
    & $VenvPy -m pip install "headroom-ai[$extras]==$vendorVersion"
}

& $VenvPy -m pip install pyyaml>=6.0 pytest>=8.0 --quiet

# -- Verificacao ---------------------------------------------------------------
Write-Host ''
Write-Host '=== verificacao ===' -ForegroundColor Cyan
& $VenvPy -c "import headroom; print('  headroom  :', headroom.__file__)"
$VenvHeadroom = Join-Path $VenvDir 'Scripts\headroom.exe'
if (-not (Test-Path $VenvHeadroom)) { $VenvHeadroom = Join-Path $VenvDir 'bin/headroom' }
if (Test-Path $VenvHeadroom) { & $VenvHeadroom --version } else { Write-Host '  aviso: CLI headroom nao encontrada no venv' -ForegroundColor Yellow }

Write-Host ''
Write-Host 'Proximos passos:' -ForegroundColor Cyan
Write-Host '  python src/shared/tools/headroom/headroom_tool.py doctor'
Write-Host '  .\src\shared\tools\headroom\run_standalone.ps1      # sobe o proxy 8787'
Write-Host '  .\copilot-cli-headroom.bat                          # Copilot CLI via proxy'
Write-Host ''
