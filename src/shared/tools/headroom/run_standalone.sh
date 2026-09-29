#!/usr/bin/env bash
# AVA Fabric :: Headroom proxy :: modo standalone (invariante I1)
#
# Sobe o proxy sem nenhuma dependência da esteira de agentes — não exige
# projeto, artefato AST nem agente rodando, só o venv da tool.
#
# Toda a configuração vem de headroom_config.py, que resolve
# env > projects/<p>/context/project-config.yaml > headroom.yaml.
#
# Nota sobre o upstream: o headroom NÃO tem flag `--upstream`. O destino real
# das requisições Anthropic é ANTHROPIC_TARGET_API_URL (equivalente à flag
# --anthropic-api-url). É isso que headroom_config.proxy_env() emite.
#
# Uso:
#   bash src/shared/tools/headroom/run_standalone.sh
#   bash src/shared/tools/headroom/run_standalone.sh --project Meu-ERP --port 8788
set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$TOOL_DIR/.venv"

PROJECT=""
PORT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --port)    PORT="$2"; shift 2 ;;
    *) echo "argumento desconhecido: $1" >&2; exit 2 ;;
  esac
done

VENV_PY="$VENV_DIR/bin/python"
[ -x "$VENV_PY" ] || VENV_PY="$VENV_DIR/Scripts/python.exe"
[ -x "$VENV_PY" ] || { echo "ERRO: venv ausente. Rode: bash src/shared/tools/headroom/setup.sh" >&2; exit 1; }

VENV_HEADROOM="$VENV_DIR/bin/headroom"
[ -x "$VENV_HEADROOM" ] || VENV_HEADROOM="$VENV_DIR/Scripts/headroom.exe"
[ -x "$VENV_HEADROOM" ] || { echo "ERRO: CLI headroom ausente no venv. Rode setup.sh --force" >&2; exit 1; }

# Exporta as variáveis emitidas por headroom_config.py --env
CONFIG_ARGS=("$TOOL_DIR/headroom_config.py" "--env")
[ -n "$PROJECT" ] && CONFIG_ARGS+=("-p" "$PROJECT")
while IFS='=' read -r key value; do
  [ -n "$key" ] && export "$key=$value"
done < <("$VENV_PY" "${CONFIG_ARGS[@]}" | "$VENV_PY" -c \
  'import json,sys; [print(f"{k}={v}") for k, v in json.load(sys.stdin).items()]')

[ -n "$PORT" ] && export HEADROOM_PORT="$PORT"

echo
echo "=== Headroom proxy :: modo standalone ==="
echo "  escutando : http://${HEADROOM_HOST}:${HEADROOM_PORT}"
echo "  upstream  : ${ANTHROPIC_TARGET_API_URL}"
echo "  backend   : ${HEADROOM_BACKEND}"
echo "  modo      : ${HEADROOM_MODE}"
echo "  log       : ${HEADROOM_LOG_FILE}"
echo
echo "  Aponte um cliente para o proxy com uma destas:"
echo "    ANTHROPIC_BASE_URL=http://${HEADROOM_HOST}:${HEADROOM_PORT}     (Claude Code)"
echo "    COPILOT_PROVIDER_BASE_URL=http://${HEADROOM_HOST}:${HEADROOM_PORT}  (Copilot CLI)"
echo
echo "  Noutra aba:  headroom doctor | headroom perf | headroom savings"
echo "  Ctrl+C encerra."
echo

# --no-http2 evita corrupção TLS quando muitos streams concorrentes são cancelados
exec "$VENV_HEADROOM" proxy --host "$HEADROOM_HOST" --port "$HEADROOM_PORT" --no-http2
