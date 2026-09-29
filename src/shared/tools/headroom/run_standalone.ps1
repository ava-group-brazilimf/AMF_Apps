<#
.SYNOPSIS
    Sobe o proxy Headroom de forma INDEPENDENTE da esteira de agentes (invariante I1).

.DESCRIPTION
    Não exige projeto, artefato AST, nem agente rodando — só o venv da tool.
    Roda em primeiro plano para que os logs fiquem visíveis; Ctrl+C encerra.

    Toda a configuração vem de headroom_config.py, que resolve
    env > projects/<p>/context/project-config.yaml > headroom.yaml.

    Nota sobre o upstream: o headroom NÃO tem flag `--upstream`. O destino real
    das requisições Anthropic é ANTHROPIC_TARGET_API_URL (equivalente à flag
    --anthropic-api-url). É isso que headroom_config.proxy_env() emite.

.PARAMETER Project
    Aplica o bloco `headroom:` do project-config.yaml deste projeto.

.PARAMETER Port
    Sobrescreve a porta (default: a de headroom.yaml, 8787).

.EXAMPLE
    .\src\shared\tools\headroom\run_standalone.ps1
    .\src\shared\tools\headroom\run_standalone.ps1 -Project Meu-ERP -Port 8788
#>
[CmdletBinding()]
param(
    [string]$Project,
    [int]$Port
)

$ErrorActionPreference = 'Stop'

$ToolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ToolDir '.venv'

$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-Path $VenvPy)) { $VenvPy = Join-Path $VenvDir 'bin/python' }
if (-not (Test-Path $VenvPy)) {
    Write-Error "venv ausente. Rode primeiro: .\src\shared\tools\headroom\setup.ps1"
}
$VenvHeadroom = Join-Path $VenvDir 'Scripts\headroom.exe'
if (-not (Test-Path $VenvHeadroom)) { $VenvHeadroom = Join-Path $VenvDir 'bin/headroom' }
if (-not (Test-Path $VenvHeadroom)) {
    Write-Error "CLI headroom ausente no venv. Rode: .\src\shared\tools\headroom\setup.ps1 -Force"
}

# ── Configuração efetiva ─────────────────────────────────────────────────────
$configArgs = @((Join-Path $ToolDir 'headroom_config.py'), '--env')
if ($Project) { $configArgs += @('-p', $Project) }
$envJson = & $VenvPy @configArgs | Out-String
$envMap = $envJson | ConvertFrom-Json

foreach ($property in $envMap.PSObject.Properties) {
    Set-Item -Path "env:$($property.Name)" -Value $property.Value
}
if ($Port) { $env:HEADROOM_PORT = "$Port" }

$listenHost = $env:HEADROOM_HOST
$listenPort = $env:HEADROOM_PORT

Write-Host ''
Write-Host '=== Headroom proxy :: modo standalone ===' -ForegroundColor Cyan
Write-Host "  escutando : http://${listenHost}:${listenPort}"
Write-Host "  upstream  : $($env:ANTHROPIC_TARGET_API_URL)"
Write-Host "  backend   : $($env:HEADROOM_BACKEND)"
Write-Host "  modo      : $($env:HEADROOM_MODE)"
Write-Host "  log       : $($env:HEADROOM_LOG_FILE)"
Write-Host ''
Write-Host '  Aponte um cliente para o proxy com uma destas:' -ForegroundColor DarkGray
Write-Host "    ANTHROPIC_BASE_URL=http://${listenHost}:${listenPort}     (Claude Code)" -ForegroundColor DarkGray
Write-Host "    COPILOT_PROVIDER_BASE_URL=http://${listenHost}:${listenPort}  (Copilot CLI — use copilot-cli-headroom.bat)" -ForegroundColor DarkGray
Write-Host ''
Write-Host '  Noutra aba:  headroom doctor | headroom perf | headroom savings' -ForegroundColor DarkGray
Write-Host '  Ctrl+C encerra.' -ForegroundColor DarkGray
Write-Host ''

# --no-http2 evita corrupção TLS quando muitos streams concorrentes são cancelados
& $VenvHeadroom proxy --host $listenHost --port $listenPort --no-http2
