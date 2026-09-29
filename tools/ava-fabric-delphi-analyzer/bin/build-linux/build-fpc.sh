#!/usr/bin/env bash
# ============================================================
#  AVA Fabric - Build do ava_ast_cli no Linux via FPC
#  Pre-req: Free Pascal 3.2.2+ (fpc no PATH). Debian/Ubuntu: apt install fp-compiler
#           (nome do pacote varia por distro/versao).
#  Uso:  ./build-fpc.sh     (rode de dentro de bin/build-linux/)
#  Gera: ../ava_ast_cli
# ============================================================
set -euo pipefail
SRC="../../examples/DelphiAST/Source"
LPR="../build-windows/ava_ast_cli.lpr"

if ! command -v fpc >/dev/null 2>&1; then
  echo "[ERRO] fpc nao encontrado no PATH. Instale o Free Pascal (ex.: sudo apt install fp-compiler)."
  exit 1
fi

mkdir -p build

if ! fpc -Mdelphi \
  -Fu"$SRC" \
  -Fu"$SRC/SimpleParser" \
  -Fu"$SRC/FreePascalSupport" \
  -Fu"$SRC/FreePascalSupport/FPC_StringBuilder/Src" \
  -Fu"$SRC/FreePascalSupport/Generics.Collection" \
  -Fi"$SRC/SimpleParser" \
  -FUbuild \
  -FE.. \
  "$LPR"; then
  echo "[ERRO] Falha na compilacao. Se reclamar de Generics.Collections,"
  echo "       remova a linha -Fu .../Generics.Collection (o FPC ja traz a sua)."
  exit 1
fi

echo
echo "[OK] Gerado: ../ava_ast_cli"
chmod +x ../ava_ast_cli
../ava_ast_cli || true
