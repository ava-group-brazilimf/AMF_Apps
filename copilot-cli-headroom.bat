@echo off
REM Copilot CLI BYOK via proxy Headroom -> Azure AI Foundry
REM
REM Variante de copilot-cli-v1.bat que roteia 100%% das requisicoes pelo proxy
REM Headroom em 127.0.0.1:8787 antes de chegarem ao endpoint do Foundry
REM (invariante I3). O proxy comprime o contexto e registra tokens_before /
REM tokens_after / latency_ms no JSONL configurado em headroom.yaml.
REM
REM Se o proxy nao estiver no ar, este script DEGRADA para o endpoint direto
REM com aviso -- nunca bloqueia a sessao (invariante IV3). Para rodar sempre
REM sem proxy, use copilot-cli-v1.bat, que fica intacto.
REM
REM SECURITY WARNING: le a chave de .copilot-key. Nao commitar (esta no .gitignore).
REM
REM Pre-requisitos:
REM   1) .\src\shared\tools\headroom\setup.ps1
REM   2) .\src\shared\tools\headroom\run_standalone.ps1   (noutra aba)
REM      -- ou --
REM      python src\shared\tools\headroom\headroom_tool.py proxy start

REM -------------------------------------------------------------------------
REM EDIT THESE VALUES
REM -------------------------------------------------------------------------
set ENDPOINT=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
set DEPLOYMENT_NAME=claude-sonnet-4-6
REM PROXY_URL nao e mais hardcoded: vem de headroom_config.py --proxy-url (host+port
REM efetivos, ja com env e project-config aplicados). Este valor e so o fallback
REM usado quando a resolucao falha.
set PROXY_URL=http://127.0.0.1:8787
REM -------------------------------------------------------------------------

if not exist "%~dp0.copilot-key" (
    echo ERROR: .copilot-key not found.
    echo Create it in the same folder as this script, containing only your API key.
    exit /b 1
)
set /p API_KEY=<"%~dp0.copilot-key"

REM ---- Interpretador: venv isolado da tool, nunca o python do PATH ---------
REM Com `python` puro, um Python ausente/incompativel devolvia errorlevel 1 e o
REM script anunciava "proxy nao respondeu", rodando a fase inteira SEM compressao
REM mesmo com o proxy no ar. run_standalone.ps1 e .vscode/mcp.json sempre
REM resolveram o venv explicitamente; este script era o unico fora do padrao.
set "HEADROOM_PY=%~dp0src\shared\tools\headroom\.venv\Scripts\python.exe"
if not exist "%HEADROOM_PY%" set "HEADROOM_PY=python"

REM ---- Porta/host efetivos (nunca hardcoded) ------------------------------
REM `cmd /s /c "<tudo entre aspas>"` e obrigatorio: com o interpretador E o script
REM entre aspas, o parser do for /f quebra ("The filename, directory name, or volume
REM label syntax is incorrect") e PROXY_URL ficaria silenciosamente no fallback.
REM O 2^>nul fica FORA das aspas internas, senao vira argumento do python.
set "HR_CFG=%~dp0src\shared\tools\headroom\headroom_config.py"
for /f "usebackq delims=" %%U in (`cmd /s /c ""%HEADROOM_PY%" "%HR_CFG%" --proxy-url" 2^>nul`) do set "PROXY_URL=%%U"

REM ---- O proxy esta no ar? -------------------------------------------------
set "BASE_URL=%PROXY_URL%"
set "VIA_PROXY=yes"
"%HEADROOM_PY%" "%~dp0src\shared\tools\headroom\headroom_tool.py" proxy status >nul 2>&1
if errorlevel 1 (
    echo.
    if "%HEADROOM_PY%"=="python" (
        echo WARNING: venv da tool nao encontrado -- usando o python do PATH.
        echo          Se o proxy estiver no ar, rode:  .\src\shared\tools\headroom\setup.ps1
    )
    echo WARNING: Headroom proxy nao respondeu em %PROXY_URL%.
    echo          Degradando para o endpoint direto -- SEM compressao de contexto.
    echo          Para ativar:  .\src\shared\tools\headroom\run_standalone.ps1
    echo.
    set "BASE_URL=%ENDPOINT%"
    set "VIA_PROXY=no"
)

REM ---- BYOK: identico a copilot-cli-v1.bat, exceto BASE_URL ----------------
set "COPILOT_PROVIDER_TYPE=anthropic"
set "COPILOT_PROVIDER_BASE_URL=%BASE_URL%"
set "COPILOT_PROVIDER_BEARER_TOKEN=%API_KEY%"
set "COPILOT_PROVIDER_MODEL_ID=claude-sonnet-4"
set "COPILOT_PROVIDER_WIRE_MODEL=%DEPLOYMENT_NAME%"
set "COPILOT_PROVIDER_HEADERS=anthropic-version: 2023-06-01"
set "COPILOT_ALLOW_ALL=true"

REM O proxy encaminha para este upstream (o headroom nao tem flag --upstream).
set "ANTHROPIC_TARGET_API_URL=%ENDPOINT%"

echo.
echo Environment variables configured:
echo   COPILOT_PROVIDER_TYPE=%COPILOT_PROVIDER_TYPE%
echo   COPILOT_PROVIDER_BASE_URL=%COPILOT_PROVIDER_BASE_URL%
echo   COPILOT_PROVIDER_BEARER_TOKEN=****%COPILOT_PROVIDER_BEARER_TOKEN:~-4%
echo   COPILOT_PROVIDER_MODEL_ID=%COPILOT_PROVIDER_MODEL_ID%
echo   COPILOT_PROVIDER_WIRE_MODEL=%COPILOT_PROVIDER_WIRE_MODEL%
echo   COPILOT_PROVIDER_HEADERS=%COPILOT_PROVIDER_HEADERS%
echo   ANTHROPIC_TARGET_API_URL=%ANTHROPIC_TARGET_API_URL%
echo   headroom compression=%VIA_PROXY%

where copilot >nul 2>&1
if errorlevel 1 (
    echo.
    echo Warning: copilot not found on PATH.
    exit /b 1
)

REM =========================================================================
REM Configuracao de agentes customizados (specs/033)
REM
REM O Copilot CLI descobre `.github\agents\*.agent.md` e `AGENTS.md` a partir da
REM RAIZ DO REPO. Por isso o `-C` no comando final: sem ele, abrir o CLI de outro
REM diretorio carrega ZERO agentes customizados -- e sem aviso nenhum.
REM
REM O preflight so avisa, nunca bloqueia (degradar, nunca quebrar). Mas um
REM `.github\agents` divergente significa rodar a esteira com guardrails
REM desatualizados, entao o aviso e alto.
REM =========================================================================

set "AGENTS_STATUS=nao verificado (python ausente no PATH)"
where python >nul 2>&1
if errorlevel 1 goto :agents_done
python "%~dp0src\shared\tools\generate_agent_wrappers.py" --check >nul 2>&1
if errorlevel 1 goto :agents_drift
set "AGENTS_STATUS=em dia com o agent_registry"
goto :agents_done
:agents_drift
set "AGENTS_STATUS=DIVERGENTE -- guardrails desatualizados!"
:agents_done

REM Contagem com o `for` intrinseco do cmd, sem binario externo: `find /c /v ""`
REM resolve para o `find` do Git Bash quando ele vem antes do System32 no PATH,
REM e ai o script trava em vez de contar.
REM So os da esteira: `*.agent.md` incluiria os 10 do Spec Kit e o numero nao
REM bateria com o do agent_registry.
set /a AGENT_COUNT=0
for %%F in ("%~dp0.github\agents\ava-*.agent.md") do set /a AGENT_COUNT+=1

REM "presente", nao "carregado": este teste so prova que o ARQUIVO existe. A prova
REM de carregamento e o comando /instructions dentro da sessao (lista os arquivos
REM de custom instruction ativos), ou o systemTokens (~23.7K com AGENTS.md contra
REM ~21.7K sem -- docs/copilot-cli-runtime-facts.md secao 10.1).
set "AGENTS_MD=AUSENTE"
if exist "%~dp0AGENTS.md" set "AGENTS_MD=presente (confirme com /instructions na sessao)"

echo   agentes customizados=%AGENT_COUNT% (%AGENTS_STATUS%)
echo   AGENTS.md=%AGENTS_MD%
if "%AGENTS_STATUS%"=="DIVERGENTE -- guardrails desatualizados!" (
    echo.
    echo   ^>^> Corrija antes de rodar a fase:
    echo      python src\shared\tools\generate_agent_wrappers.py
)

REM ---- Fase opcional: copilot-cli-headroom.bat F1 --------------------------
REM Resolve o orquestrador pelo agent_registry, NUNCA por um mapa local -- um
REM sexto espelho manual de fase->agente e o defeito que originou aquele modulo.
set "START_AGENT="
if "%~1"=="" goto :launch
for /f "usebackq delims=" %%A in (`python "%~dp0src\shared\tools\agent_registry.py" --orchestrator %~1 2^>nul`) do set "START_AGENT=%%A"
if not defined START_AGENT (
    echo.
    echo WARNING: fase "%~1" sem orquestrador registrado ^(F3, F7 e F8 nao tem^).
    echo          Abrindo a sessao sem agente inicial -- use /agent para escolher.
)
:launch

echo.
REM --allow-all        : = --allow-all-tools --allow-all-paths --allow-all-urls
REM --no-ask-user      : desliga a tool ask_user (nao pergunta ao usuario)
REM -C "%~dp0."        : raiz do repo -- OBRIGATORIO para descobrir .github\agents
REM                      e AGENTS.md independente de onde o .bat foi chamado
if defined START_AGENT (
    echo Sessao iniciando no orquestrador: %START_AGENT%
    echo.
    copilot --allow-all --no-ask-user -C "%~dp0." --agent "%START_AGENT%"
) else (
    copilot --allow-all --no-ask-user -C "%~dp0."
)

