#!/usr/bin/env bash
# AVA Fabric :: Headroom Tool :: setup (paridade Linux/macOS do setup.ps1)
#
# Cria o venv isolado em src/shared/tools/headroom/.venv — NÃO contamina o venv
# principal do repositório (invariante IV7).
#
# O fork embedded (./vendor) usa maturin como build backend, que exige Rust.
# Com `cargo` no PATH instala o fork em modo editável; sem, cai para o wheel
# PyPI da MESMA versão do vendor.
#
# Uso:
#   bash src/shared/tools/headroom/setup.sh            # completo
#   bash src/shared/tools/headroom/setup.sh --skip-ml  # sem torch (~3 GB)
#   bash src/shared/tools/headroom/setup.sh --force    # recria o venv
set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$TOOL_DIR/.venv"
VENDOR="$TOOL_DIR/vendor"

SKIP_ML=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --skip-ml) SKIP_ML=1 ;;
    --force)   FORCE=1 ;;
    *) echo "argumento desconhecido: $arg" >&2; exit 2 ;;
  esac
done

echo
echo "=== AVA Fabric :: Headroom Tool :: setup ==="
echo "  tool   : $TOOL_DIR"
echo "  venv   : $VENV_DIR"
echo "  vendor : $VENDOR"

[ -f "$VENDOR/pyproject.toml" ] || {
  echo "ERRO: fork ausente em $VENDOR." >&2
  echo "Restaure com: git subtree add --prefix src/shared/tools/headroom/vendor \\" >&2
  echo "  https://github.com/headroomlabs-ai/headroom.git main --squash" >&2
  exit 1
}

PY="${PYTHON:-python3}"
PY_VERSION="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
echo "  python : $PY_VERSION"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' || {
  echo "ERRO: Python >= 3.10 exigido pelo headroom-ai (encontrado $PY_VERSION)." >&2
  exit 1
}

if [ "$FORCE" -eq 1 ] && [ -d "$VENV_DIR" ]; then
  echo "  removendo venv existente (--force)..."
  rm -rf "$VENV_DIR"
fi
[ -d "$VENV_DIR" ] || { echo "  criando venv..."; "$PY" -m venv "$VENV_DIR"; }

VENV_PY="$VENV_DIR/bin/python"
[ -x "$VENV_PY" ] || VENV_PY="$VENV_DIR/Scripts/python.exe"

"$VENV_PY" -m pip install --upgrade pip setuptools wheel --quiet

if [ "$SKIP_ML" -eq 1 ]; then
  EXTRAS="proxy,mcp,code,memory,otel"
  echo "  extras : sem [ml] (--skip-ml) — Kompress ML indisponível"
else
  EXTRAS="proxy,mcp,ml,code,memory,otel"
  echo "  extras : $EXTRAS  (inclui torch, ~3 GB — use --skip-ml para pular)"
fi

if command -v cargo >/dev/null 2>&1; then
  echo "  modo   : fork EDITÁVEL (cargo encontrado — build via maturin)"
  "$VENV_PY" -m pip install -e "$VENDOR[$EXTRAS]"
else
  VENDOR_VERSION="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$VENDOR/pyproject.toml" | head -1)"
  echo "  modo   : wheel PyPI headroom-ai==$VENDOR_VERSION (cargo ausente)"
  echo "           O fork em ./vendor fica como referência/patch source."
  echo "           Instale Rust (https://rustup.rs) e rode de novo para buildar o fork."
  "$VENV_PY" -m pip install "headroom-ai[$EXTRAS]==$VENDOR_VERSION"
fi

"$VENV_PY" -m pip install 'pyyaml>=6.0' 'pytest>=8.0' --quiet

echo
echo "=== verificação ==="
"$VENV_PY" -c "import headroom; print('  headroom  :', headroom.__file__)"
if [ -x "$VENV_DIR/bin/headroom" ]; then "$VENV_DIR/bin/headroom" --version; fi

echo
echo "Próximos passos:"
echo "  python src/shared/tools/headroom/headroom_tool.py doctor"
echo "  bash src/shared/tools/headroom/run_standalone.sh     # sobe o proxy 8787"
echo
