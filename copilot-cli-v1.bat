@echo off
REM Copilot CLI BYOK configuration for Azure AI Foundry
REM
REM SECURITY WARNING: This file reads an API key from .copilot-key.
REM Do not commit .copilot-key to Git. It is listed in .gitignore.
REM
REM EXAMPLE / TEMPLATE: Copy this file to copilot-cli.bat, fill in your
REM endpoint and deployment name, then create a .copilot-key file containing
REM your Azure AI Foundry API key.
REM
REM Variables are scoped to this process only. Run this script before each
REM copilot session; it will set the env vars and launch copilot.

REM -------------------------------------------------------------------------
REM EDIT THESE VALUES
REM -------------------------------------------------------------------------
set ENDPOINT=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
set DEPLOYMENT_NAME=claude-sonnet-4-6
REM -------------------------------------------------------------------------

REM Read API key from .copilot-key (avoids batch escaping issues with %%/=/etc.)
if not exist "%~dp0.copilot-key" (
    echo ERROR: .copilot-key not found.
    echo Create it in the same folder as this script, containing only your API key.
    exit /b 1
)
set /p API_KEY=<"%~dp0.copilot-key"

set "COPILOT_PROVIDER_TYPE=anthropic"
set "COPILOT_PROVIDER_BASE_URL=%ENDPOINT%"
set "COPILOT_PROVIDER_BEARER_TOKEN=%API_KEY%"
set "COPILOT_PROVIDER_MODEL_ID=claude-sonnet-4"
set "COPILOT_PROVIDER_WIRE_MODEL=%DEPLOYMENT_NAME%"
set "COPILOT_PROVIDER_HEADERS=anthropic-version: 2023-06-01"
set "COPILOT_ALLOW_ALL=true"

echo.
echo Environment variables configured:
echo   COPILOT_PROVIDER_TYPE=%COPILOT_PROVIDER_TYPE%
echo   COPILOT_PROVIDER_BASE_URL=%COPILOT_PROVIDER_BASE_URL%
echo   COPILOT_PROVIDER_BEARER_TOKEN=****%COPILOT_PROVIDER_BEARER_TOKEN:~-4%
echo   COPILOT_PROVIDER_MODEL_ID=%COPILOT_PROVIDER_MODEL_ID%
echo   COPILOT_PROVIDER_WIRE_MODEL=%COPILOT_PROVIDER_WIRE_MODEL%
echo   COPILOT_PROVIDER_HEADERS=%COPILOT_PROVIDER_HEADERS%

where copilot >nul 2>&1
if errorlevel 1 (
    echo.
    echo Warning: copilot not found on PATH.
    exit /b 1
)

echo.
copilot --autopilot --no-ask-user