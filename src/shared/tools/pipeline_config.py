#!/usr/bin/env python3
"""
AVA Fabric — CLI da esteira · Resolução de configuração
========================================================
Fonte única de verdade para *toda* a configuração do ``ava_pipeline``. Nenhum
outro módulo lê ``os.environ`` ou ``ava-pipeline.yaml`` diretamente (Artigo I da
Constituição — nada de endpoint/modelo hardcoded em código).

Precedência (forte → fraco)
---------------------------
1. **Flags do CLI** — resolvidas em ``ava_pipeline.py``, não aqui
2. **Ambiente** — ``AVA_PIPELINE_*`` / ``AVA_FOUNDRY_*``
3. **Projeto** — ``projects/{project}/context/project-config.yaml`` → ``pipeline:``
4. **Defaults** — ``src/shared/data/ava-pipeline.yaml``
5. **Último recurso** — ``_FALLBACK_DEFAULTS`` (só se o YAML sumir ou faltar pyyaml)

Uso
---
    from pipeline_config import load_config, resolve_model, proxy_url

    cfg = load_config("MeuERP-002")
    cfg["foundry"]["endpoint"]
    resolve_model(cfg, "sonnet")     # "claude-sonnet-4-6"

Degradação
----------
``load_config`` **nunca levanta**: YAML ilegível ou pyyaml ausente caem no
fallback com aviso em stderr. Env malformada é ignorada, mantendo a camada de
baixo. Mesmo contrato de ``headroom_config.py`` (invariante IV3).
"""
from __future__ import annotations

import copy
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover — pyyaml está disponível no venv do repo
    yaml = None

# Força UTF-8 no Windows (padrão do repo)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# SCRIPT_DIR = src/shared/tools → parents: shared, src, repo
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
TOOL_CONFIG = REPO_ROOT / "src" / "shared" / "data" / "ava-pipeline.yaml"
HEADROOM_DIR = REPO_ROOT / "src" / "shared" / "tools" / "headroom"

# ─── Defaults de último recurso ──────────────────────────────────────────────
# Espelham ava-pipeline.yaml. Só entram em cena se o YAML sumir ou pyyaml faltar;
# ava-pipeline.yaml continua sendo a fonte de verdade editável.
_FALLBACK_DEFAULTS: dict[str, Any] = {
    "foundry": {
        "endpoint": "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic",
        "api_key_file": ".copilot-key",
        "anthropic_version": "2023-06-01",
        "max_tokens": 32768,
    },
    "models": {
        "default": "claude-sonnet-4-6",
        "provider_model_id": "claude-sonnet-4",
        "aliases": {"sonnet": "claude-sonnet-4-6"},
    },
    "proxy": {
        "mode": "auto",
        "url_command": ["src/shared/tools/headroom/headroom_config.py", "--proxy-url"],
        "status_command": ["src/shared/tools/headroom/headroom_tool.py", "proxy", "status"],
        "prefer_tool_venv": True,
    },
    "execution": {
        "engine": "sdk",
        "confirm": "manual",
        "timeout_s": 900,
        "output_subdir": "outputs/pipeline_runner",
    },
    "context": {
        "skill_chars": 500_000,
        "file_chars": 500_000,
        "max_artifacts": 500,
        "max_artifact_bodies": 30,
        "artifact_body_chars": 20_000,
    },
    "dns_overrides": {"enabled": False, "hosts": {}},
    # Sem espelho da esteira aqui de propósito: uma lista de 12 passos duplicada
    # em código seria o sexto espelho manual que este CLI existe para eliminar.
    # Sem o YAML, build_plan() falha alto em vez de rodar uma esteira inventada.
    "steps": [],
}

# ─── Mapa env → caminho na config ────────────────────────────────────────────
# (variável de ambiente, caminho pontilhado, conversor)
_ENV_MAP: list[tuple[str, str, str]] = [
    ("AVA_FOUNDRY_ENDPOINT", "foundry.endpoint", "str"),
    ("AVA_FOUNDRY_MODEL", "models.default", "str"),
    ("AVA_FOUNDRY_API_KEY_FILE", "foundry.api_key_file", "str"),
    ("AVA_PIPELINE_MAX_TOKENS", "foundry.max_tokens", "int"),
    ("AVA_PIPELINE_PROVIDER_MODEL_ID", "models.provider_model_id", "str"),
    ("AVA_PIPELINE_PROXY_MODE", "proxy.mode", "str"),
    ("AVA_PIPELINE_ENGINE", "execution.engine", "str"),
    ("AVA_PIPELINE_CONFIRM", "execution.confirm", "str"),
    ("AVA_PIPELINE_TIMEOUT_S", "execution.timeout_s", "int"),
    ("AVA_PIPELINE_DNS_OVERRIDES", "dns_overrides.enabled", "bool"),
]

_TRUTHY = {"1", "true", "yes", "on", "sim"}
_FALSY = {"0", "false", "no", "off", "nao", "não"}

PROXY_MODES = ("auto", "require", "off")
ENGINES = ("sdk", "copilot")


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
        return None if _is_none(raw) else float(raw)
    return raw


def _is_none(raw: str) -> bool:
    """``null``/``none``/vazio em variável de ambiente significa 'não definido'."""
    return raw.strip().lower() in ("", "null", "none")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge recursivo: ``override`` vence, dicts aninhados são fundidos.

    Listas são substituídas por inteiro, nunca fundidas item a item — é o que
    permite um projeto declarar sua própria ``steps:`` sem herdar posições da
    esteira padrão.
    """
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _set_path(cfg: dict[str, Any], dotted: str, value: Any) -> None:
    """Grava ``value`` em ``cfg`` seguindo um caminho pontilhado (``proxy.mode``)."""
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
    except Exception as exc:  # noqa: BLE001 — config ruim não derruba a esteira
        print(f"[pipeline_config] aviso: {path.name} ilegível ({exc}); usando a camada abaixo",
              file=sys.stderr)
        return {}


# ─── API pública ─────────────────────────────────────────────────────────────

def project_config_path(project_name: str) -> Path:
    """Caminho do ``project-config.yaml`` do projeto.

    Mesma convenção de ``headroom_config.project_config_path`` e
    ``context_budget.load_project_config``.
    """
    return REPO_ROOT / "projects" / project_name / "context" / "project-config.yaml"


def project_dir(project_name: str) -> Path:
    return REPO_ROOT / "projects" / project_name


def load_config(project_name: str | None = None) -> dict[str, Any]:
    """Resolve a configuração efetiva do CLI.

    ``project_name`` ausente = só defaults + ambiente (usado por ``config`` e
    ``list``, que rodam sem nenhum projeto existir).
    """
    cfg = _deep_merge(_FALLBACK_DEFAULTS, _read_yaml(TOOL_CONFIG).get("pipeline", {}))

    if project_name:
        project_block = _read_yaml(project_config_path(project_name)).get("pipeline", {})
        if isinstance(project_block, dict):
            cfg = _deep_merge(cfg, project_block)

    for env_name, dotted, kind in _ENV_MAP:
        raw = os.environ.get(env_name)
        if raw is None or raw == "":
            continue
        try:
            _set_path(cfg, dotted, _coerce(raw, kind))
        except (TypeError, ValueError):
            # Env malformada não derruba o CLI — mantém o valor da camada abaixo.
            print(f"[pipeline_config] aviso: {env_name}={raw!r} ignorado (esperado {kind})",
                  file=sys.stderr)

    return cfg


def resolve_model(cfg: dict[str, Any], cli_model: str | None = None) -> str:
    """Wire model efetivo. ``--model`` vence tudo; aliases são expandidos."""
    models = cfg.get("models", {})
    raw = cli_model or models.get("default") or "claude-sonnet-4-6"
    aliases = models.get("aliases") or {}
    return str(aliases.get(raw, raw))


def api_key_path(cfg: dict[str, Any]) -> Path:
    """Caminho absoluto do arquivo com a API Key do Foundry."""
    rel = cfg.get("foundry", {}).get("api_key_file", ".copilot-key")
    path = Path(rel)
    return path if path.is_absolute() else REPO_ROOT / rel


def api_key(cfg: dict[str, Any]) -> str:
    """Lê a API Key. Levanta ``SystemExit(2)`` com instrução se faltar."""
    path = api_key_path(cfg)
    if not path.is_file():
        raise SystemExit(
            f"ERRO: {path.name} não encontrado em {path}\n"
            f"      Crie o arquivo contendo apenas a API Key do Foundry (sem newline)."
        )
    key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit(f"ERRO: {path} está vazio.")
    return key


def _tool_python(cfg: dict[str, Any]) -> str:
    """Interpretador para os comandos do Headroom.

    Prefere o venv isolado da tool. Com o `python` do PATH, um Python
    ausente/incompatível devolve exit != 0 e o CLI concluiria "proxy fora do ar",
    rodando a esteira inteira SEM compressão — o defeito corrigido em
    copilot-cli-headroom.bat L39-45.
    """
    if cfg.get("proxy", {}).get("prefer_tool_venv", True):
        for candidate in (HEADROOM_DIR / ".venv" / "Scripts" / "python.exe",
                          HEADROOM_DIR / ".venv" / "bin" / "python"):
            if candidate.exists():
                return str(candidate)
    return sys.executable


def _run_tool(cfg: dict[str, Any], key: str, timeout: int = 30) -> subprocess.CompletedProcess | None:
    """Roda um dos comandos declarados no bloco ``proxy:``. Nunca levanta."""
    parts = cfg.get("proxy", {}).get(key) or []
    if not parts:
        return None
    argv = [_tool_python(cfg), str(REPO_ROOT / parts[0]), *parts[1:]]
    try:
        return subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, cwd=str(REPO_ROOT))
    except Exception:  # noqa: BLE001 — tool ausente/travada = proxy indisponível
        return None


def proxy_url(cfg: dict[str, Any]) -> str | None:
    """URL efetiva do proxy Headroom, resolvida pela própria tool.

    NUNCA hardcodar host/porta aqui: com a porta duplicada, subir o proxy em
    8788 faria o CLI sondar 8787, falhar e degradar em silêncio.
    """
    out = _run_tool(cfg, "url_command")
    if out is None or out.returncode != 0:
        return None
    return out.stdout.strip() or None


def proxy_alive(cfg: dict[str, Any]) -> bool:
    """``headroom_tool.py proxy status`` — exit 0 = no ar."""
    out = _run_tool(cfg, "status_command")
    return out is not None and out.returncode == 0


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(
        description="Mostra a configuração efetiva do CLI da esteira AVA Fabric",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  pipeline_config.py --show
  pipeline_config.py --show -p MeuERP-002
  pipeline_config.py --model            # linha crua, consumível por .bat
  pipeline_config.py --endpoint
""",
    )
    ap.add_argument("-p", "--project", help="Aplica o bloco pipeline: do project-config.yaml")
    ap.add_argument("--show", action="store_true", help="Emite a configuração efetiva (default)")
    ap.add_argument("--json", action="store_true", help="Força saída JSON")
    ap.add_argument("--model", action="store_true", help="Emite só o wire model, sem JSON")
    ap.add_argument("--endpoint", action="store_true", help="Emite só o endpoint, sem JSON")
    args = ap.parse_args()

    config = load_config(args.project)
    if args.model:
        # Texto puro, uma linha: consumido por `for /f` em .bat, que não parseia JSON.
        print(resolve_model(config))
    elif args.endpoint:
        print(config.get("foundry", {}).get("endpoint", ""))
    else:
        print(json.dumps(config, indent=2, ensure_ascii=False))
