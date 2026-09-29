#!/usr/bin/env python3
"""
AVA Fabric – Task Dispatch Payload Builder
============================================
Gera, de forma **determinística e sem custo de LLM**, os 3 campos obrigatórios
da tool call `task` do GitHub Copilot CLI — `description`, `agent_type` e
`prompt` — para o `ava-asis-orchestrator` despachar qualquer subagente.

Motivação
---------
`orchestrator-asis.md` despachava subagentes via pseudocódigo abstrato
("Dispatch: @agent", "Despachar como SubAgent com prompt: ...") que nunca
nomeava os 3 campos obrigatórios da tool `task`. O LLM ocasionalmente omitia
um campo ao montar a tool call real, produzindo:

    Multiple validation errors: "description" Required / "prompt" Required /
    "agent_type" Required

(3 ocorrências medidas em docs/copilot-cli-runtime-facts.md §12.2, de 345
falhas de `task`). Este utilitário fecha a lacuna: o orquestrador roda o
script ANTES de cada dispatch e usa os campos retornados verbatim — nunca
compõe `description`/`agent_type`/`prompt` livremente.

`agent_type` == o campo `name:` do `.github/agents/{agent_id}.agent.md`
correspondente (mesmo valor usado como `resolved_solution_agent` e demais
`agent_id` do DAG) — o script valida a existência do wrapper antes de emitir
o payload, então um `agent_type` inválido nunca chega à tool call.

Uso
---
    python build_dispatch_payload.py --agent ava-asis-solution-java --project meu-erp --json
    python build_dispatch_payload.py --agent ava-asis-inventory --project meu-erp \
        --missing metrics.json,inventory-report.md --json
    python build_dispatch_payload.py --list

Exit codes
----------
    0 — OK       : payload emitido com os 3 campos preenchidos
    1 — ERROR    : --agent/--project ausentes
    2 — NOT_FOUND: agent_id não corresponde a nenhum `.github/agents/*.agent.md`
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - pyyaml é dependência do módulo
    yaml = None

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# src/modules/ava-fabric-agents/asis-diagnostic/utils/ -> repo root (5 níveis acima)
REPO_ROOT = Path(__file__).resolve().parents[5]
AGENTS_DIR = REPO_ROOT / ".github" / "agents"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)

FILE_PERSISTENCE_REMINDER = (
    "FILE_PERSISTENCE_RULE: para toda escrita de arquivos, usar Bash + PowerShell "
    "batch (BatchWriteProtocol) — $files=[ordered]@{...} + loop Set-Content em UMA "
    "ÚNICA chamada Bash. NUNCA usar Write tool por arquivo individual."
)


def list_agent_ids() -> list[str]:
    """Enumera todo agent_id válido a partir dos wrappers .agent.md."""
    if not AGENTS_DIR.is_dir():
        return []
    ids = []
    for path in AGENTS_DIR.glob("*.agent.md"):
        ids.append(path.name[: -len(".agent.md")])
    return sorted(ids)


def read_agent_frontmatter(agent_id: str) -> dict[str, Any] | None:
    """Lê e faz parse do frontmatter YAML do wrapper .agent.md do agente."""
    path = AGENTS_DIR / f"{agent_id}.agent.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    if yaml is None:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def build_prompt(
    agent_id: str,
    project_name: str,
    spec_path: str | None,
    missing: list[str],
    ast_slice: list[str],
    execution_mode: str | None,
    extra: str | None,
) -> str:
    """Monta o skeleton de prompt — nunca instrui o agente a "ler tudo"."""
    lines: list[str] = []
    if spec_path:
        lines.append(
            f"Leia por inteiro {spec_path} antes de qualquer outra ação e siga "
            "todos os Execution Steps literalmente."
        )
    else:
        lines.append(
            f"Leia por inteiro sua spec canônica (metadata.spec do wrapper "
            f"{agent_id}.agent.md) antes de qualquer outra ação."
        )
    lines.append(f"Projeto: {project_name}.")
    lines.append(FILE_PERSISTENCE_REMINDER)

    if missing:
        lines.append(
            "Artefatos ausentes a regenerar (NÃO refazer o restante): "
            + ", ".join(missing)
            + "."
        )
    if ast_slice:
        lines.append(
            "Fatia de artefatos AST autorizada (NUNCA carregar o payload completo): "
            + ", ".join(ast_slice)
            + "."
        )
    if execution_mode:
        lines.append(f"execution_mode: {execution_mode}.")
    if extra:
        lines.append(extra)

    return "\n".join(lines)


def build_payload(
    agent_id: str,
    project_name: str,
    missing: list[str] | None = None,
    ast_slice: list[str] | None = None,
    execution_mode: str | None = None,
    extra: str | None = None,
) -> dict[str, Any]:
    frontmatter = read_agent_frontmatter(agent_id)
    if frontmatter is None:
        candidates = difflib.get_close_matches(agent_id, list_agent_ids(), n=5)
        raise LookupError(
            f"agent_id desconhecido: '{agent_id}'. Não existe "
            f"{AGENTS_DIR / (agent_id + '.agent.md')}. "
            f"Próximos por similaridade: {candidates or list_agent_ids()[:5]}"
        )

    metadata = frontmatter.get("metadata") or {}
    spec_path = metadata.get("spec")
    phase = metadata.get("phase", "F1")

    prompt = build_prompt(
        agent_id,
        project_name,
        spec_path,
        missing or [],
        ast_slice or [],
        execution_mode,
        extra,
    )

    return {
        "description": f"Executar {agent_id} (Fase {phase}) para o projeto {project_name}",
        "agent_type": agent_id,
        "prompt": prompt,
        "spec_path": spec_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera o payload {description, agent_type, prompt} para a tool call task."
    )
    parser.add_argument("--agent", help="agent_id alvo (== agent_type == name: do .agent.md)")
    parser.add_argument("--project", help="Nome do projeto (projects/{project})")
    parser.add_argument("--missing", default="", help="Lista de artefatos ausentes, separados por vírgula")
    parser.add_argument("--ast-slice", default="", help="Lista de artefatos compressed/*.json autorizados, separados por vírgula")
    parser.add_argument("--execution-mode", choices=["subagent", "inline", "bc_scoped"], default=None)
    parser.add_argument("--extra", default=None, help="Instrução adicional específica deste dispatch")
    parser.add_argument("--list", action="store_true", help="Lista todos os agent_id válidos e sai")
    parser.add_argument("--json", action="store_true", help="Emite JSON (consumo pelo orquestrador)")
    args = parser.parse_args()

    if args.list:
        ids = list_agent_ids()
        print(json.dumps(ids, ensure_ascii=False, indent=2) if args.json else "\n".join(ids))
        return 0

    if not args.agent or not args.project:
        print("ERROR: --agent e --project são obrigatórios (ou use --list)", file=sys.stderr)
        return 1

    missing = [m.strip() for m in args.missing.split(",") if m.strip()]
    ast_slice = [a.strip() for a in args.ast_slice.split(",") if a.strip()]

    try:
        payload = build_payload(
            args.agent,
            args.project,
            missing=missing,
            ast_slice=ast_slice,
            execution_mode=args.execution_mode,
            extra=args.extra,
        )
    except LookupError as exc:
        error = {"status": "not_found", "detail": str(exc), "valid_agent_ids": list_agent_ids()}
        print(json.dumps(error, ensure_ascii=False, indent=2) if args.json else f"❌ {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"description: {payload['description']}")
        print(f"agent_type : {payload['agent_type']}")
        print(f"prompt     :\n{payload['prompt']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
