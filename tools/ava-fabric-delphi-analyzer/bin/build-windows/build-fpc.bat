@echo off
REM ============================================================
REM  AVA Fabric - Build do ava_ast_cli.exe no Windows via FPC
REM  Pre-req: Free Pascal 3.2.2+ (fpc.exe no PATH) - instale o Lazarus
REM           (https://www.lazarus-ide.org) que ja traz o FPC.
REM  Uso:  build-fpc.bat     (rode de dentro de bin\build-windows\)
REM  Gera: ..\ava_ast_cli.exe
REM ============================================================
setlocal
set SRC=..\..\examples\DelphiAST\Source

where fpc >nul 2>&1
if errorlevel 1 (
  echo [ERRO] fpc.exe nao encontrado no PATH. Instale o Lazarus/FPC.
  exit /b 1
)

if not exist build mkdir build

fpc -Mdelphi ^
  -Fu"%SRC%" ^
  -Fu"%SRC%\SimpleParser" ^
  -Fu"%SRC%\FreePascalSupport" ^
  -Fu"%SRC%\FreePascalSupport\FPC_StringBuilder\Src" ^
  -Fu"%SRC%\FreePascalSupport\Generics.Collection" ^
  -Fi"%SRC%\SimpleParser" ^
  -FUbuild ^
  -FE.. ^
  ava_ast_cli.lpr

if errorlevel 1 (
  echo [ERRO] Falha na compilacao. Se reclamar de Generics.Collections,
  echo        remova a linha -Fu ...Generics.Collection (o FPC ja traz a sua^).
  exit /b 1
)
echo.
echo [OK] Gerado: ..\ava_ast_cli.exe
..\ava_ast_cli.exe 2>&1
endlocal
