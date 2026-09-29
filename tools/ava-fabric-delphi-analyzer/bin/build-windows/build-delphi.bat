@echo off
REM ============================================================
REM  AVA Fabric - Build do ava_ast_cli.exe no Windows via Delphi
REM  Pre-req: RAD Studio/Delphi com dcc64.exe no PATH
REM           (rode em "RAD Studio Command Prompt" para ter o PATH pronto).
REM  Uso:  build-delphi.bat   (de dentro de bin\build-windows\)
REM  Gera: ..\ava_ast_cli.exe
REM ============================================================
setlocal
set SRC=..\..\examples\DelphiAST\Source

where dcc64 >nul 2>&1
if errorlevel 1 (
  echo [ERRO] dcc64.exe nao encontrado. Abra o "RAD Studio Command Prompt".
  exit /b 1
)

REM Delphi compila .dpr; o wrapper e' compativel (o {$MODE} fica sob {$IFDEF FPC})
copy /Y ava_ast_cli.lpr ava_ast_cli.dpr >nul
if not exist build mkdir build

dcc64 -B ^
  -U"%SRC%;%SRC%\SimpleParser" ^
  -I"%SRC%\SimpleParser" ^
  -NU"build" ^
  -E".." ^
  ava_ast_cli.dpr

if errorlevel 1 (
  echo [ERRO] Falha na compilacao. Para 32-bit use dcc32 no lugar de dcc64.
  exit /b 1
)
echo.
echo [OK] Gerado: ..\ava_ast_cli.exe
..\ava_ast_cli.exe 2>&1
endlocal
