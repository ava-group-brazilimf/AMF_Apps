#!/usr/bin/env python3
"""
AVA Fabric – Headroom Tool · Resolução de configuração
=======================================================
Fonte única de verdade para *toda* a configuração da tool. Nenhum outro módulo
lê ``os.environ`` ou ``headroom.yaml`` diretamente (Artigo I da Constituição —
nada de endpoint/limiar hardcoded em código).

Precedência (forte → fraco)
---------------------------
1. **Ambiente** — ``HEADROOM_*``, ``AVA_FOUNDRY_*``, ``ANTHROPIC_TARGET_API_URL``
2. **Projeto** — ``projects/{project}/context/project-config.yaml`` → ``headroom:``
3. **Defaults da tool** — ``src/shared/tools/headroom/headroom.yaml``

Uso
---
    from headroom_config import load_config, proxy_env

    cfg = load_config("Meu-ERP")
    cfg["model"]            # "claude-sonnet-4-6"
    cfg["proxy"]["port"]    # 8787

Degradação
----------
Sem ``pyyaml`` instalado, ou com YAML ilegível, ``load_config`` devolve
``_FALLBACK_DEFAULTS`` e nunca levanta exceção — a esteira não pode parar por
causa desta tool (invariante IV3).
"""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - pyyaml vem no requirements da tool
    yaml = None

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# src/shared/tools/headroom/headroom_config.py → headroom → tools → shared → src → repo
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
VENDOR_DIR = SCRIPT_DIR / "vendor"
VENV_DIR = SCRIPT_DIR / ".venv"
TOOL_CONFIG = SCRIPT_DIR / "headroom.yaml"

# ─── Defaults de último recurso ──────────────────────────────────────────────
# Espelham headroom.yaml. Só entram em cena se o YAML sumir ou pyyaml faltar;
# headroom.yaml continua sendo a fonte de verdade editável.
_FALLBACK_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "model": "claude-sonnet-4-6",
    "context_limit": 200000,
    "detect_backend": "auto",
    "compress": {
        "target_ratio": None,
        "min_tokens_to_compress": 250,
        "compress_user_messages": True,
        "protect_recent": 0,
    },
    "proxy": {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8787,
        "upstream": "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic",
        "backend": "anthropic",
        "log_file": ".headroom/proxy-requests.jsonl",
        "mode": "token",
        "http2": False,
        "request_timeout_seconds": 600,
    },
    "observability": {
        "metrics_file": "outputs/observability/headroom-metrics.jsonl",
    },
    "fallback_on_error": True,
}

# ─── Mapa env → caminho na config ────────────────────────────────────────────
# (variável de ambiente, caminho pontilhado, conversor)
_ENV_MAP: list[tuple[str, str, str]] = [
    ("HEADROOM_ENABLED", "enabled", "bool"),
    ("AVA_FOUNDRY_MODEL", "model", "str"),
    ("AVA_FOUNDRY_CONTEXT_LIMIT", "context_limit", "int"),
    ("HEADROOM_DETECT_BACKEND", "detect_backend", "str"),
    ("HEADROOM_TARGET_RATIO", "compress.target_ratio", "float"),
    ("HEADROOM_HOST", "proxy.host", "str"),
    ("HEADROOM_PORT", "proxy.port", "int"),
    ("ANTHROPIC_TARGET_API_URL", "proxy.upstream", "str"),
    ("HEADROOM_BACKEND", "proxy.backend", "str"),
    ("HEADROOM_LOG_FILE", "proxy.log_file", "str"),
    ("HEADROOM_MODE", "proxy.mode", "str"),
    ("HEADROOM_METRICS_FILE", "observability.metrics_file", "str"),
]

_TRUTHY = {"1", "true", "yes", "on", "sim"}
_FALSY = {"0", "false", "no", "off", "nao", "não"}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _coerce(raw: str, kind: str) -> Any:
    """Converte um valor de ambiente (sempre str) para o tipo alvo."""
    raw = raw.strip()
    if kind == "bool":
        low = raw.lower()
        if low in _TRUTHY:
            return True
        if low in _FALSY:
            return False
        return bool(raw)
    if kind == "int":
        return int(raw)
    if kind == "float":
        return None if low_is_none(raw) else float(raw)
    return raw


def low_is_none(raw: str) -> bool:
    """``null``/``none``/vazio em variável de ambiente significa 'não definido'."""
    return raw.strip().lower() in ("", "null", "none")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge recursivo: ``override`` vence, dicts aninhados são fundidos."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _set_path(cfg: dict[str, Any], dotted: str, value: Any) -> None:
    """Grava ``value`` em ``cfg`` seguindo um caminho pontilhado (``proxy.port``)."""
    parts = dotted.split(".")
    node = cfg
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def _read_yaml(path: Path) -> dict[str, Any]:
    """Lê um YAML devolvendo ``{}`` em qualquer falha (nunca levanta)."""
    if yaml is None or not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ─── API pública ─────────────────────────────────────────────────────────────

def project_config_path(project_name: str) -> Path:
    """Caminho do ``project-config.yaml`` do projeto.

    Mesma convenção de ``qa_preflight.load_project_config`` e
    ``context_budget._load_thresholds``.
    """
    return REPO_ROOT / "projects" / project_name / "context" / "project-config.yaml"


def load_config(project_name: str | None = None) -> dict[str, Any]:
    """Resolve a configuração efetiva da tool.

    ``project_name`` ausente = só defaults da tool + ambiente (modo standalone,
    invariante I1: o proxy sobe sem nenhum projeto da esteira existir).
    """
    cfg = _deep_merge(_FALLBACK_DEFAULTS, _read_yaml(TOOL_CONFIG).get("headroom", {}))

    if project_name:
        project_block = _read_yaml(project_config_path(project_name)).get("headroom", {})
        if isinstance(project_block, dict):
            cfg = _deep_merge(cfg, project_block)

    for env_name, dotted, kind in _ENV_MAP:
        raw = os.environ.get(env_name)
        if raw is None or raw == "":
            continue
        try:
            _set_path(cfg, dotted, _coerce(raw, kind))
        except (TypeError, ValueError):
            # Env malformada não derruba a tool — mantém o valor da camada abaixo.
            print(f"[headroom_config] aviso: {env_name}={raw!r} ignorado (esperado {kind})",
                  file=sys.stderr)

    return cfg


def metrics_path(project_name: str, cfg: dict[str, Any] | None = None) -> Path:
    """Caminho absoluto do JSONL de métricas do projeto (cria o diretório)."""
    cfg = cfg or load_config(project_name)
    rel = cfg.get("observability", {}).get(
        "metrics_file", "outputs/observability/headroom-metrics.jsonl")
    path = REPO_ROOT / "projects" / project_name / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def proxy_log_path(cfg: dict[str, Any] | None = None) -> Path:
    """Caminho absoluto do JSONL nativo do proxy (cria o diretório)."""
    cfg = cfg or load_config()
    rel = cfg.get("proxy", {}).get("log_file", ".headroom/proxy-requests.jsonl")
    path = Path(rel)
    if not path.is_absolute():
        path = REPO_ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def proxy_env(cfg: dict[str, Any] | None = None) -> dict[str, str]:
    """Variáveis de ambiente que configuram ``headroom proxy``.

    O headroom **não tem** flag ``--upstream``: o upstream Anthropic é
    ``--anthropic-api-url`` / ``ANTHROPIC_TARGET_API_URL`` (verificado em
    ``headroom proxy --help``, v0.33.0).
    """
    cfg = cfg or load_config()
    proxy = cfg.get("proxy", {})
    env = {
        "HEADROOM_HOST": str(proxy.get("host", "127.0.0.1")),
        "HEADROOM_PORT": str(proxy.get("port", 8787)),
        "HEADROOM_BACKEND": str(proxy.get("backend", "anthropic")),
        "ANTHROPIC_TARGET_API_URL": str(proxy.get("upstream", "")),
        "HEADROOM_MODE": str(proxy.get("mode", "token")),
        "HEADROOM_LOG_FILE": str(proxy_log_path(cfg)),
        "HEADROOM_REQUEST_TIMEOUT": str(proxy.get("request_timeout_seconds", 600)),
        "HEADROOM_TELEMETRY": "off",
    }
    backend = cfg.get("detect_backend", "auto")
    if backend and backend != "auto":
        env["HEADROOM_DETECT_BACKEND"] = str(backend)
    return {k: v for k, v in env.items() if v}


def proxy_url(cfg: dict[str, Any] | None = None) -> str:
    """URL efetiva do proxy (``http://host:port``), já com env e project-config aplicados.

    Existe para que os launchers parem de hardcodar ``127.0.0.1:8787``: com a porta
    duplicada entre ``headroom.yaml`` e ``copilot-cli-headroom.bat``, subir o proxy em
    8788 fazia o ``.bat`` sondar 8787, falhar e degradar silenciosamente para o endpoint
    direto — rodando a fase inteira sem compressão.
    """
    cfg = cfg or load_config()
    proxy = cfg.get("proxy", {})
    return f"http://{proxy.get('host', '127.0.0.1')}:{proxy.get('port', 8787)}"


def venv_python() -> Path | None:
    """Interpretador do venv isolado da tool, se já criado por setup.*."""
    for candidate in (VENV_DIR / "Scripts" / "python.exe", VENV_DIR / "bin" / "python"):
        if candidate.exists():
            return candidate
    return None


def venv_headroom() -> Path | None:
    """Executável ``headroom`` do venv isolado, se já criado por setup.*."""
    for candidate in (VENV_DIR / "Scripts" / "headroom.exe", VENV_DIR / "bin" / "headroom"):
        if candidate.exists():
            return candidate
    return None


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Mostra a configuração efetiva da tool Headroom")
    ap.add_argument("-p", "--project", help="Projeto para aplicar o bloco headroom: do project-config.yaml")
    ap.add_argument("--env", action="store_true",
                    help="Emite só as variáveis de ambiente do proxy (consumido por run_standalone.*)")
    ap.add_argument("--proxy-url", action="store_true",
                    help="Emite só a URL do proxy, sem JSON (consumido por copilot-cli-headroom.bat)")
    args = ap.parse_args()
    config = load_config(args.project)
    if args.proxy_url:
        # Texto puro, uma linha: consumido por `for /f` em .bat, que não parseia JSON.
        print(proxy_url(config))
    else:
        print(json.dumps(proxy_env(config) if args.env else config, indent=2, ensure_ascii=False))
