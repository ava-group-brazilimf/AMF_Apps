@echo off
REM AVA Fabric - CLI de orquestracao da esteira
REM
REM Atalho de raiz para src\shared\tools\ava_pipeline.py. Existe para que o CLI
REM seja chamavel de qualquer lugar sem lembrar o caminho, do mesmo jeito que
REM copilot-cli-headroom.bat e o ponto de entrada da sessao interativa.
REM
REM Toda a configuracao (modelo, endpoint, proxy, ordem da esteira) vive em
REM src\shared\data\ava-pipeline.yaml. NAO adicionar valores aqui: um segundo
REM lugar com a porta/modelo e exatamente o defeito que esta entrega elimina.
REM
REM Exemplos:
REM   ava-pipeline.bat list --phases
REM   ava-pipeline.bat run -p MeuERP-002 --all --dry-run
REM   ava-pipeline.bat run -p MeuERP-002 --phase F2b --yes
REM   ava-pipeline.bat doctor -p MeuERP-002

setlocal

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python nao encontrado no PATH.
    exit /b 2
)

REM %* repassa os argumentos verbatim, inclusive os que tem espaco.
python "%~dp0src\shared\tools\ava_pipeline.py" %*
exit /b %ERRORLEVEL%
