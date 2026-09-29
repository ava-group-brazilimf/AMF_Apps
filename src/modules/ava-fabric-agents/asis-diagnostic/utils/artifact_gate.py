#!/usr/bin/env python3
"""
AVA Fabric – Artifact Dispatch Gate
====================================
Verifica, de forma **determinística e sem custo de LLM**, se os artefatos
obrigatórios de um agente AS-IS já existem em disco — respondendo à única
pergunta que o ``ava-asis-orchestrator`` precisa fazer **antes** de gastar um
``runSubagent``:

    "Este agente já entregou? Se sim, não despache."

Motivação (ISSUE-002 · RC-2 e RC-4)
-----------------------------------
Em ``processaERP-008`` o orquestrador disparou 3 ``runSubagent`` para o mesmo
agente em 16 segundos (20:26:21, 20:26:37, 20:27:09) porque não detectou que
as duas primeiras chamadas haviam retornado cedo — multiplicando por 3× o
custo de inferência de um agente que já custava 777s.  Além disso, a esteira
morreu com 8 dos 19 artefatos F1 ausentes, sem forma barata de retomar
apenas o que faltava.

Este utilitário implementa a mitigação **M-4 (Retry Guard)** e habilita o
**resume** por artefato: o mesmo contrato serve para o guard pré-dispatch e
para o relatório de completude F1 na retomada.

Fonte da verdade
----------------
``ARTIFACT_CONTRACTS`` abaixo espelha 1:1 a tabela
``§ Artifact Output Contract per Agent`` de ``agents/orchestrator-asis.md``.
Alterar um lado exige alterar o outro.

Uso
---
    # Guard pré-dispatch (1 agente)
    python artifact_gate.py --project processaERP-008 --agent ava-asis-db-analyzer

    # Varredura de completude / resume (todos os agentes)
    python artifact_gate.py --project processaERP-008 --all

    # Consumo pelo orquestrador
    python artifact_gate.py --project processaERP-008 --all --json

Exit codes
----------
    0 — COMPLETE   : todos os artefatos presentes → **NÃO despachar** (skip)
    1 — INCOMPLETE : falta ao menos 1 artefato    → **despachar**
    2 — ERROR      : agente desconhecido / projeto inexistente
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[5]

# ---------------------------------------------------------------------------
# Contratos de artefatos — espelho de § Artifact Output Contract per Agent
# ---------------------------------------------------------------------------
# Cada item: {"path": str, "min_count": int (globs), "min_size": int (bytes),
#             "base": "asis" | "workspace" | "dir"}
#   base="asis"      → relativo a projects/{p}/outputs/asis/   (default)
#   base="workspace" → relativo à raiz do repositório
#   kind="dir"       → diretório que deve existir e conter >= min_count arquivos

_SOLUTION_CONTRACT: list[dict[str, Any]] = [
    {"path": "architecture-blueprint.md"},
    {"path": "pattern-classifications.json"},
    {"path": "bounded-context-map.md"},
    {"path": "diagrams/architecture-blueprint.mmd"},
    {"path": "diagrams/c4-context.mmd"},
    {"path": "diagrams/c4-container.mmd"},
    {"path": "diagrams/c4-component.mmd"},
    {"path": "diagrams/component-diagram.mmd"},
    {"path": "diagrams/diagrama-sequencia-*.mmd", "min_count": 2},
]

ARTIFACT_CONTRACTS: dict[str, list[dict[str, Any]]] = {
    "ava-asis-solution-delphi": _SOLUTION_CONTRACT,
    "ava-asis-solution-vb": _SOLUTION_CONTRACT,
    "ava-asis-solution-cobol": _SOLUTION_CONTRACT,
    "ava-asis-solution-vbnet": _SOLUTION_CONTRACT,
    "ava-asis-solution-powerbuilder": _SOLUTION_CONTRACT,
    "ava-asis-solution-java": _SOLUTION_CONTRACT,
    "ava-asis-solution-dotnet": _SOLUTION_CONTRACT,
    "ava-asis-inventory": [
        {"path": "inventory-report.md"},
        {"path": "metrics.json"},
        {"path": "complexity-map.md"},
        {"path": ".internal/form-registry.json"},
    ],
    "ava-asis-db-analyzer": [
        # `db/` (não a raiz de asis/): o path da raiz nunca existia em disco, então o
        # guard jamais confirmava o db-analyzer e o re-despachava a cada iteração do
        # COLLECT loop (retry storm — ISSUE-002 § RC-2). Fonte: output-paths.md,
        # db-analyzer.md § Output Contract e build_summary_comprehensive.py.
        {"path": "db/db-analysis-report.md"},
        {"path": "db/schema-inventory.md"},
        {"path": "db/er-diagram.mmd"},
    ],
    "ava-asis-events-pubsub": [
        {"path": "events-pubsub-inventory.md"},
        {"path": "events-pubsub-grid.json"},
        {"path": "diagrams/events-pubsub-flow.mmd"},
        {"path": "events-pubsub-risks.md"},
    ],
    "doc:FT": [
        {"path": "docs/screen-navigation-map.md"},
        {"path": "docs/screen-flow.mmd"},
    ],
    "doc:VC": [{"path": "docs/value-chain.md"}],
    "doc:RT": [{"path": "docs/screen-rules.md"}],
    "ava-asis-business-rules-generator": [
        {"path": "docs/business-rules.md"},
        {"path": "docs/business-rules.json"},
    ],
    "doc:PR": [{"path": "docs/prototype-asis", "kind": "dir", "min_count": 1}],
    "ava-asis-gap-migration-analyzer": [
        {"path": "gap-list-report.md"},
        {"path": "gap-register.json"},
        {"path": "gap-analysis-summary.md"},
    ],
    "ava-asis-gaps-risks": [
        {"path": "gaps-risks-report.md"},
        {"path": "risk-register.json"},
        {"path": "migration-risks-summary.md"},
    ],
    "ava-asis-bridge-fastqa": [
        {"path": "qa/test-plan.md", "min_size": 3000},
        {"path": "qa/test-gaps.md"},
        {"path": "qa/test-cases.md"},
        # ⚠️ `fastqa/manual_test/` é global do workspace (não é por projeto). Estes
        # globs são **advisory**: aparecem no relatório mas NÃO decidem `complete`,
        # pois um PBI de outro projeto produziria um falso "presente" e faria o
        # guard pular um dispatch necessário. A decisão real fica com `qa/*` acima,
        # que são project-scoped.
        {"path": "US/PBI-*.md", "base": "fastqa", "min_count": 1, "advisory": True},
        {"path": "gap_analysis/PBI-*_gaps.md", "base": "fastqa", "min_count": 1, "advisory": True},
        {"path": "requirements_analysis/PBI-*_requirements.md", "base": "fastqa", "min_count": 1, "advisory": True},
        {"path": "behavior_analysis/PBI-*_behaviors.md", "base": "fastqa", "min_count": 1, "advisory": True},
        {"path": "test_cases/**/PBI-*.md", "base": "fastqa", "min_count": 1, "advisory": True},
        {"path": "test_cases/PBI-*_test_plan.md", "base": "fastqa", "min_count": 1, "advisory": True},
    ],
    "ava-asis-orchestrator": [{"path": "master-report.md"}],
}

# Artefatos F1 mandatórios do contrato de saída da fase — usados no modo
# ``--all`` para o relatório de completude/resume (ISSUE-002 § RC-4).
F1_OUTPUT_CONTRACT: list[str] = [
    "master-report.md",
    "architecture-blueprint.md",
    "bounded-context-map.md",
    "inventory-report.md",
    "gaps-risks-report.md",
    "db/db-analysis-report.md",
    "docs/value-chain.md",
    "docs/business-rules.md",
    "docs/business-rules.json",
    "docs/screen-navigation-map.md",
    "docs/screen-rules.md",
    "db/schema-inventory.md",
    "db/er-diagram.mmd",
]

_BASE_DIRS = {"fastqa": "fastqa/manual_test", "workspace": ""}

# Bases relativas a `projects/{project}/`. A F2 (`tobe-architecture/utils/
# artifact_gate_tobe.py`) reusa `check_item` deste módulo e precisa de `tobe`/
# `context`; `asis` resolve para o mesmo caminho de sempre — adição pura.
_PROJECT_BASES = {"asis": "outputs/asis", "tobe": "outputs/tobe", "context": "context"}

# ---------------------------------------------------------------------------
# Waves — espelho de § Dispatch Schedule (orchestrator-asis.md)
# ---------------------------------------------------------------------------
# `{solution}` é resolvido em runtime via ``legacy_technology`` do project-config.
#
# Motivação (ISSUE-002 · RC-3): a Regra 11 exige ``should_dispatch()`` antes de
# **cada** dispatch. Com 5 agentes na Wave 2 isso vira 5 chamadas ``Bash``
# separadas, e o orquestrador processa output entre elas — serializando a wave,
# que é exatamente a violação da Regra 3 apontada em orchestrator-asis.md.
# ``--wave`` colapsa o guard inteiro em **uma** chamada: o orquestrador recebe a
# lista elegível completa e despacha todos antes de ler qualquer output.
WAVES: dict[str, list[str]] = {
    "phase_a_wave1": ["{solution}"],
    "phase_a_wave2": [
        "ava-asis-inventory",
        "ava-asis-db-analyzer",
        "ava-asis-events-pubsub",
        "doc:FT",
        "doc:VC",
        "ava-asis-business-rules-generator",
    ],
    "phase_b": [
        "doc:RT",
        "doc:PR",
        "ava-asis-bridge-fastqa",
        "ava-asis-gap-migration-analyzer",
    ],
    "phase_c": ["ava-asis-gaps-risks"],
}


def check_wave(project: str, wave: str) -> dict[str, Any]:
    """Avalia **todos** os agentes de uma wave em uma única chamada.

    Devolve a lista elegível (``dispatch``) e a de artefatos já presentes
    (``skip``), mais o ``dispatch_manifest`` que o orquestrador deve preencher e
    conferir antes de processar qualquer output — se
    ``len(dispatched) != len(dispatch)``, a wave foi serializada e o master-report
    recebe ``DISPATCH_SERIALIZATION``.
    """
    agent_ids = list(WAVES[wave])
    warnings: list[str] = []
    if "{solution}" in agent_ids:
        resolved = resolve_solution_agent(project)
        if not resolved:
            # Sem `legacy_technology` resolvível não dá para saber qual agente de solução
            # roda. Silenciar isso devolveria `dispatch: []`, que o orquestrador leria
            # como "nada a fazer" — e a Wave 1 inteira seria pulada sem erro.
            warnings.append(
                "SOLUTION_AGENT_UNRESOLVED: `legacy_technology` ausente ou desconhecido em "
                f"projects/{project}/context/project-config.yaml — wave incompleta"
            )
        agent_ids = [resolved if a == "{solution}" else a for a in agent_ids]
        agent_ids = [a for a in agent_ids if a]

    results = {aid: check_agent(project, aid) for aid in agent_ids}
    dispatch = [a for a, r in results.items() if r["should_dispatch"]]
    return {
        "project": project,
        "wave": wave,
        "agents": results,
        "warnings": warnings,
        "dispatch": dispatch,
        "skip": [a for a, r in results.items() if r["complete"]],
        "dispatch_manifest": {
            "expected_count": len(dispatch),
            "expected_agents": dispatch,
            "dispatched": [],
            "rule": (
                "Despachar TODOS os agentes de `expected_agents` antes de processar "
                "o output de qualquer um (Regra 3). Conferir "
                "len(dispatched) == expected_count ANTES do primeiro COLLECT; "
                "divergência = DISPATCH_SERIALIZATION no master-report."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Verificação
# ---------------------------------------------------------------------------
def _resolve_base(project: str, base: str) -> Path:
    rel = _PROJECT_BASES.get(base)
    if rel is not None:
        return REPO_ROOT / "projects" / project / rel
    return REPO_ROOT / _BASE_DIRS[base] if _BASE_DIRS[base] else REPO_ROOT


def check_item(project: str, item: dict[str, Any]) -> dict[str, Any]:
    base = _resolve_base(project, item.get("base", "asis"))
    rel = item["path"]
    min_count = int(item.get("min_count", 1))
    min_size = int(item.get("min_size", 1))  # >= 1 byte: rejeita arquivo vazio
    result: dict[str, Any] = {"path": rel, "present": False, "found": 0, "reason": ""}

    if item.get("kind") == "dir":
        target = base / rel
        files = [p for p in target.rglob("*") if p.is_file()] if target.is_dir() else []
        result["found"] = len(files)
        result["present"] = len(files) >= min_count
        if not result["present"]:
            result["reason"] = f"diretório ausente ou com < {min_count} arquivo(s)"
        return result

    if any(ch in rel for ch in "*?["):
        matches = [p for p in base.glob(rel) if p.is_file() and p.stat().st_size >= min_size]
        result["found"] = len(matches)
        result["present"] = len(matches) >= min_count
        if not result["present"]:
            result["reason"] = f"glob encontrou {len(matches)}/{min_count} arquivo(s)"
        return result

    target = base / rel
    if not target.is_file():
        result["reason"] = "arquivo ausente"
        return result
    size = target.stat().st_size
    result["found"] = 1
    result["size"] = size
    if size < min_size:
        result["reason"] = f"tamanho {size}B < mínimo {min_size}B (placeholder)"
        return result
    result["present"] = True
    return result


def check_agent(project: str, agent_id: str) -> dict[str, Any]:
    contract = ARTIFACT_CONTRACTS.get(agent_id)
    if contract is None:
        return {
            "agent": agent_id,
            "status": "no_contract",
            "complete": False,
            "should_dispatch": True,
            "missing": [],
            "present": [],
            "detail": "sem contrato definido — dispatch permitido (não bloquear)",
        }

    checks = []
    for item in contract:
        res = check_item(project, item)
        res["advisory"] = bool(item.get("advisory"))
        checks.append(res)

    missing = [c for c in checks if not c["present"]]
    # Itens `advisory` (paths globais do workspace) informam, mas nunca decidem —
    # um falso "presente" ali faria o guard pular um dispatch necessário.
    blocking = [c for c in missing if not c["advisory"]]
    complete = not blocking
    return {
        "agent": agent_id,
        "status": "complete" if complete else "incomplete",
        "complete": complete,
        "should_dispatch": not complete,
        "present": [c["path"] for c in checks if c["present"]],
        "missing": [
            {"path": c["path"], "reason": c["reason"], "advisory": c["advisory"]} for c in missing
        ],
    }


def check_f1_contract(project: str) -> dict[str, Any]:
    base = REPO_ROOT / "projects" / project / "outputs" / "asis"
    present, missing = [], []
    for rel in F1_OUTPUT_CONTRACT:
        (present if (base / rel).is_file() else missing).append(rel)
    return {
        "total": len(F1_OUTPUT_CONTRACT),
        "present": present,
        "missing": missing,
        "completeness_pct": round(100.0 * len(present) / len(F1_OUTPUT_CONTRACT), 1),
    }


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------
def render_agent(res: dict[str, Any]) -> None:
    icon = "✅" if res["complete"] else "🔄"
    verb = "SKIP (artefatos presentes)" if res["complete"] else "DISPATCH"
    print(f"{icon} {res['agent']:<34} → {verb}")
    for m in res["missing"]:
        mark = "ℹ" if m["advisory"] else "✗"
        suffix = " [advisory]" if m["advisory"] else ""
        print(f"      {mark} {m['path']} — {m['reason']}{suffix}")


# Roteamento idêntico ao § Step 2 (Decompose) do orchestrator-asis.md
SOLUTION_AGENTS = {
    "delphi": "ava-asis-solution-delphi",
    "vb6": "ava-asis-solution-vb",
    "cobol": "ava-asis-solution-cobol",
    "vbnet": "ava-asis-solution-vbnet",
    "powerbuilder": "ava-asis-solution-powerbuilder",
    "java": "ava-asis-solution-java",
    "dotnet": "ava-asis-solution-dotnet",
}


def resolve_solution_agent(project: str) -> str | None:
    """Resolve o agente de solução ativo via ``legacy_technology`` do project-config."""
    cfg = REPO_ROOT / "projects" / project / "context" / "project-config.yaml"
    if not cfg.is_file():
        return None
    try:
        import yaml  # import tardio: só necessário no modo --all

        with cfg.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001
        return None
    tech = str(data.get("legacy_technology") or "").strip().lower()
    return SOLUTION_AGENTS.get(tech)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guard de dispatch: verifica se os artefatos de um agente AS-IS já existem."
    )
    parser.add_argument("--project", required=True, help="Nome do projeto (projects/{project})")
    parser.add_argument("--agent", default=None, help="ID do agente (ex: ava-asis-db-analyzer)")
    parser.add_argument("--all", action="store_true", help="Verifica todos os agentes + contrato F1")
    parser.add_argument(
        "--wave",
        choices=sorted(WAVES),
        default=None,
        help="Guard de uma wave inteira em 1 chamada (evita serialização — RC-3)",
    )
    parser.add_argument("--json", action="store_true", help="Emite JSON (consumo pelo orquestrador)")
    parser.add_argument(
        "--recheck-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Se o resultado vier INCOMPLETO, aguarda N ms e re-verifica UMA vez. "
            "Use SÓ na verificação pós-execução — no guard pré-dispatch 'incompleto' "
            "é o estado normal e isto atrasaria todo agente."
        ),
    )
    args = parser.parse_args()

    if not (REPO_ROOT / "projects" / args.project).is_dir():
        msg = f"projeto não encontrado: projects/{args.project}"
        print(json.dumps({"status": "error", "detail": msg}) if args.json else f"❌ ERRO: {msg}")
        return 2
    if not args.agent and not args.all and not args.wave:
        print("❌ ERRO: informe --agent <id>, --wave <nome> ou --all", file=sys.stderr)
        return 2

    if args.wave:
        res = check_wave(args.project, args.wave)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print("─" * 78)
            print(f"🌊 Wave Dispatch Gate — {args.project} · {args.wave}")
            print("─" * 78)
            for item in res["agents"].values():
                render_agent(item)
            for warning in res["warnings"]:
                print(f"   ⚠️  {warning}")
            print("─" * 78)
            print(f"⚡ DESPACHAR EM PARALELO ({len(res['dispatch'])}): "
                  f"{', '.join(res['dispatch']) or '(nenhum)'}")
            if res["skip"]:
                print(f"⏭️  SKIP (já presentes): {', '.join(res['skip'])}")
            print(f"   {res['dispatch_manifest']['rule']}")
            print("─" * 78)
        # Warnings também reprovam: uma wave incompleta não pode sair como "nada a fazer".
        return 0 if not (res["dispatch"] or res["warnings"]) else 1

    if args.agent:
        if args.agent not in ARTIFACT_CONTRACTS:
            msg = f"agente sem contrato conhecido: {args.agent}"
            print(json.dumps({"status": "error", "detail": msg}) if args.json else f"❌ ERRO: {msg}")
            return 2
        res = check_agent(args.project, args.agent)
        # Re-check APENAS no caminho negativo, e só se pedido explicitamente.
        # Converte um falso negativo transitório (arquivo de 0 byte recém-criado)
        # em confirmação, sem mascarar bug de path — se o arquivo não existe mesmo,
        # continua reprovando. Ver ISSUE-003 §6.1: o único falso negativo já
        # documentado era path errado, e um sleep cego o teria escondido.
        if not res["complete"] and args.recheck_ms > 0:
            time.sleep(args.recheck_ms / 1000.0)
            segunda = check_agent(args.project, args.agent)
            if segunda["complete"]:
                segunda["rescued_on_recheck"] = args.recheck_ms
            res = segunda
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            render_agent(res)
            if res.get("rescued_on_recheck"):
                print(f"   ↻ confirmado só no 2º check (+{res['rescued_on_recheck']}ms) — "
                      f"latência de escrita real")
        return 0 if res["complete"] else 1

    # Somente o agente de solução resolvido para a tecnologia legada do projeto
    # entra no relatório — os demais compartilham o mesmo contrato e produziriam
    # linhas duplicadas e enganosas.
    resolved = resolve_solution_agent(args.project)
    inactive = {a for a in SOLUTION_AGENTS.values() if resolved and a != resolved}
    results = {
        aid: check_agent(args.project, aid)
        for aid in ARTIFACT_CONTRACTS
        if aid not in inactive
    }
    f1 = check_f1_contract(args.project)
    payload = {
        "project": args.project,
        "agents": results,
        "f1_output_contract": f1,
        "dispatch_needed": sorted(a for a, r in results.items() if r["should_dispatch"]),
        "skip": sorted(a for a, r in results.items() if r["complete"]),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("─" * 78)
        print(f"🚦 Artifact Dispatch Gate — {args.project}")
        print("─" * 78)
        for res in results.values():
            render_agent(res)
        print("─" * 78)
        print(
            f"📦 Contrato F1: {len(f1['present'])}/{f1['total']} artefatos "
            f"({f1['completeness_pct']}%)"
        )
        for rel in f1["missing"]:
            print(f"      ✗ {rel}")
        print("─" * 78)

    return 0 if not payload["dispatch_needed"] else 1


if __name__ == "__main__":
    sys.exit(main())
