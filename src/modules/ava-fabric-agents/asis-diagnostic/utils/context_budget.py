#!/usr/bin/env python3
"""
AVA Fabric – Context Budget Analyzer
=====================================
Calcula, de forma **determinística e sem custo de LLM**, o orçamento de contexto
(tokens comprimidos) de um projeto AS-IS e decide o `execution_mode` que o
``orchestrator-asis.md`` deve usar ao despachar os agentes da Phase A · Wave 2.

Motivação (ISSUE-002)
---------------------
Em ``processaERP-008`` (363 units, 174.375 LOC) a saída AST comprimida somou
**761.376 tokens**.  Cada ``runSubagent`` carregava o payload inteiro, o que
produziu chamadas de 34, 5 e 62 minutos e deixou 8 dos 19 artefatos F1 sem
gerar.  Este utilitário fecha a lacuna: o orquestrador passa a **medir antes
de despachar** e a enviar para cada agente apenas a fatia de artefatos que ele
realmente consome (§ M-1), caindo para execução inline (§ M-2) ou exigindo
recorte por bounded context (§ M-3) quando o volume ultrapassa os limiares.

Fonte de dados
--------------
``projects/{project}/outputs/asis/ast-raw/{language}/compressed/manifest.json``
(fallback legado: ``.../asis/delphi-ast-raw/compressed/manifest.json``), campo
``artifacts[].tokens_out`` — os mesmos números que o motor ``headroom`` grava
em ``metrics.jsonl``.

Uso
---
    python context_budget.py --project processaERP-008
    python context_budget.py --project processaERP-008 --json
    python context_budget.py --project processaERP-008 --agent ava-asis-db-analyzer

Exit codes
----------
    0 — OK        : total <= inline_threshold  → execution_mode = "subagent"
    1 — WARNING   : total >  inline_threshold  → execution_mode = "inline"
    2 — CRITICAL  : total >  bc_scoped_threshold → execution_mode = "bc_scoped"
    3 — ERROR     : manifest ausente/ilegível (o orquestrador degrada e continua)

Limiares (configuráveis por projeto — Art. I da Constituição)
-------------------------------------------------------------
``projects/{project}/context/project-config.yaml``::

    context_budget_inline_threshold: 400000     # default
    context_budget_bc_scoped_threshold: 700000  # default
"""
from __future__ import annotations

import argparse
import json
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

REPO_ROOT = Path(__file__).resolve().parents[5]

DEFAULT_INLINE_THRESHOLD = 400_000
DEFAULT_BC_SCOPED_THRESHOLD = 700_000

# ---------------------------------------------------------------------------
# § M-1 — AST Artifact Slice per Agent (FONTE CANÔNICA)
# ---------------------------------------------------------------------------
# Quais artefatos ``compressed/*.json`` cada agente despachado pelo
# ``ava-asis-orchestrator`` realmente consome.  Derivado dos ``## Input
# Contract`` reais de cada agente (ver specs/010).  O orquestrador passa esta
# lista no dispatch para que nenhum agente receba o payload completo.
#
# ``[]`` = agente de consolidação: lê apenas os .md/.json produzidos por outros
# agentes, nunca os artefatos AST.
AGENT_ARTIFACT_SLICE: dict[str, list[str]] = {
    # Wave 1 — único agente que legitimamente cobre todos os artefatos.
    # Mitigação aqui NÃO é slicing e sim o LARGE ARTIFACT PROTOCOL (extração
    # seletiva via Bash) + resume idempotente por artefato (ver solution-delphi.md).
    "ava-asis-solution-delphi": [
        "01_business_rules",
        "02_form_business_rules",
        "03_database_rules",
        "04_database_schemas",
        "05_procedures",
        "06_integrations",
        "07_apis",
        "08_code_overview",
        "09_test_coverage",
    ],
    # Java tem contrato próprio (10 artefatos — inclui 10_sql_functions, ausente em Delphi).
    # Mesma mitigação do delphi acima: LARGE ARTIFACT PROTOCOL + resume idempotente
    # (ver solution-java.md Step 0.6) — não é slicing.
    "ava-asis-solution-java": [
        "01_business_rules",
        "02_form_business_rules",
        "03_database_rules",
        "04_database_schemas",
        "05_procedures",
        "06_integrations",
        "07_apis",
        "08_code_overview",
        "09_test_coverage",
        "10_sql_functions",
    ],
    # Wave 2
    "ava-asis-inventory": ["08_code_overview", "02_form_business_rules"],
    "ava-asis-db-analyzer": ["03_database_rules", "04_database_schemas", "05_procedures"],
    "ava-asis-events-pubsub": ["06_integrations"],
    "doc:FT": ["02_form_business_rules"],
    "doc:VC": ["01_business_rules", "08_code_overview"],
    # Phase B
    "doc:RT": ["02_form_business_rules"],
    # ava-asis-business-rules-generator consome 10_business_rule_cases.json quando disponível,
    # mas pode cair em 01_business_rules em legados sem esse artefato (fallback condicional).
    "ava-asis-business-rules-generator": ["10_business_rule_cases", "01_business_rules", "08_code_overview"],
    "doc:PR": [],
    "ava-asis-bridge-fastqa": [],
    "ava-asis-gap-migration-analyzer": [],
    # Phase C
    "ava-asis-gaps-risks": [],
    # Segurança — domínio próprio, não consome artefatos AST
    "ava-asis-security-orchestrator": [],
}

# Agentes com contrato idêntico ao solution-delphi (mesma fatia)
for _alias in (
    "ava-asis-solution-vb",
    "ava-asis-solution-cobol",
    "ava-asis-solution-vbnet",
    "ava-asis-solution-powerbuilder",
):
    AGENT_ARTIFACT_SLICE[_alias] = list(AGENT_ARTIFACT_SLICE["ava-asis-solution-delphi"])


# ---------------------------------------------------------------------------
# Resolução de paths / config
# ---------------------------------------------------------------------------
def _project_dir(project: str) -> Path:
    return REPO_ROOT / "projects" / project


def load_project_config(project: str) -> dict[str, Any]:
    """Lê ``context/project-config.yaml``; devolve ``{}`` se ausente/ilegível."""
    cfg_path = _project_dir(project) / "context" / "project-config.yaml"
    if not cfg_path.is_file() or yaml is None:
        return {}
    try:
        with cfg_path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001 - config inválida não pode derrubar o gate
        return {}


def resolve_compressed_dir(project: str, language: str | None) -> Path | None:
    """
    Resolve o diretório ``compressed/`` do projeto.

    Ordem: ``ast-raw/{language}/compressed`` → qualquer ``ast-raw/*/compressed``
    → path legado ``delphi-ast-raw/compressed``.  Devolve ``None`` se nenhum
    existir.
    """
    base = _project_dir(project) / "outputs" / "asis"
    candidates: list[Path] = []
    if language:
        candidates.append(base / "ast-raw" / language / "compressed")
    ast_raw = base / "ast-raw"
    if ast_raw.is_dir():
        candidates.extend(sorted(p / "compressed" for p in ast_raw.iterdir() if p.is_dir()))
    candidates.append(base / "delphi-ast-raw" / "compressed")

    for cand in candidates:
        if (cand / "manifest.json").is_file():
            return cand
    return None


def read_manifest(compressed_dir: Path) -> dict[str, int]:
    """Devolve ``{artifact_name: tokens_out}`` a partir de ``manifest.json``."""
    with (compressed_dir / "manifest.json").open(encoding="utf-8") as fh:
        manifest = json.load(fh)
    per_artifact: dict[str, int] = {}
    for entry in manifest.get("artifacts", []):
        name = entry.get("artifact")
        if name:
            per_artifact[name] = int(entry.get("tokens_out") or 0)
    return per_artifact


# ---------------------------------------------------------------------------
# Cálculo
# ---------------------------------------------------------------------------
def classify(tokens: int, inline_threshold: int, bc_threshold: int) -> str:
    if tokens > bc_threshold:
        return "bc_scoped"
    if tokens > inline_threshold:
        return "inline"
    return "subagent"


def build_budget(
    project: str,
    language: str | None = None,
    inline_threshold: int | None = None,
    bc_threshold: int | None = None,
) -> dict[str, Any]:
    config = load_project_config(project)
    language = language or str(config.get("legacy_technology") or "").strip().lower() or None
    inline_threshold = int(
        inline_threshold
        if inline_threshold is not None
        else config.get("context_budget_inline_threshold", DEFAULT_INLINE_THRESHOLD)
    )
    bc_threshold = int(
        bc_threshold
        if bc_threshold is not None
        else config.get("context_budget_bc_scoped_threshold", DEFAULT_BC_SCOPED_THRESHOLD)
    )

    compressed_dir = resolve_compressed_dir(project, language)
    if compressed_dir is None:
        return {
            "project": project,
            "language": language,
            "status": "manifest_missing",
            "execution_mode": "subagent",
            "detail": (
                "manifest.json não encontrado em outputs/asis/ast-raw/*/compressed/ "
                "nem no path legado delphi-ast-raw/compressed/ — Step 0 (AST) não rodou "
                "ou falhou. Orquestrador deve prosseguir em modo degradado."
            ),
        }

    per_artifact = read_manifest(compressed_dir)
    total = sum(per_artifact.values())

    agents: dict[str, Any] = {}
    for agent_id, slice_names in sorted(AGENT_ARTIFACT_SLICE.items()):
        slice_tokens = sum(per_artifact.get(name, 0) for name in slice_names)
        agents[agent_id] = {
            "artifacts": slice_names,
            "tokens": slice_tokens,
            "pct_of_total": round(100.0 * slice_tokens / total, 1) if total else 0.0,
            "mode": classify(slice_tokens, inline_threshold, bc_threshold),
        }

    return {
        "project": project,
        "language": language,
        "status": "ok",
        "compressed_dir": str(compressed_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "thresholds": {"inline": inline_threshold, "bc_scoped": bc_threshold},
        "total_tokens": total,
        "per_artifact": per_artifact,
        "execution_mode": classify(total, inline_threshold, bc_threshold),
        "agents": agents,
    }


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------
_MODE_ICON = {"subagent": "✅", "inline": "⚠️", "bc_scoped": "⛔"}


def render_human(budget: dict[str, Any], agent_filter: str | None) -> None:
    if budget["status"] != "ok":
        print(f"⚠️  Context Budget INDISPONÍVEL — projeto {budget['project']}")
        print(f"    {budget['detail']}")
        print("    execution_mode assumido: subagent (default)")
        return

    total = budget["total_tokens"]
    thr = budget["thresholds"]
    mode = budget["execution_mode"]
    print("─" * 78)
    print(f"🧮 Context Budget — {budget['project']} ({budget['language'] or 'n/a'})")
    print("─" * 78)
    print(f"  Fonte           : {budget['compressed_dir']}/manifest.json")
    print(f"  Total comprimido: {total:,} tokens".replace(",", "."))
    print(
        "  Limiares        : inline > {:,} | bc_scoped > {:,}".format(
            thr["inline"], thr["bc_scoped"]
        ).replace(",", ".")
    )
    print(f"  execution_mode  : {_MODE_ICON[mode]} {mode.upper()}")
    print()
    print("  Artefatos (tokens comprimidos):")
    for name, tokens in sorted(budget["per_artifact"].items()):
        print(f"    {name:<26} {tokens:>10,}".replace(",", "."))
    print()
    print("  Fatia por agente (§ M-1 — Artifact-Level Context Slicing):")
    header = f"    {'Agente':<34} {'Tokens':>10}  {'%':>6}  Modo"
    print(header)
    print("    " + "-" * (len(header) - 4))
    for agent_id, info in budget["agents"].items():
        if agent_filter and agent_id != agent_filter:
            continue
        tokens_fmt = f"{info['tokens']:,}".replace(",", ".")
        print(
            f"    {agent_id:<34} {tokens_fmt:>10}  {info['pct_of_total']:>5.1f}%  "
            f"{_MODE_ICON[info['mode']]} {info['mode']}"
        )
    print("─" * 78)
    if mode != "subagent":
        print(
            "  ⚠️  Payload acima do limiar — o orquestrador DEVE aplicar M-1 (slicing),\n"
            "      M-2 (execução inline) e, em bc_scoped, M-3 (1 dispatch por bounded\n"
            "      context via module-partition.json). Ver ISSUE-002 §5."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calcula o orçamento de contexto AS-IS e o execution_mode do orquestrador."
    )
    parser.add_argument("--project", required=True, help="Nome do projeto (projects/{project})")
    parser.add_argument("--language", default=None, help="Tecnologia legada (default: legacy_technology do project-config)")
    parser.add_argument("--agent", default=None, help="Filtra a saída humana para um único agente")
    parser.add_argument("--inline-threshold", type=int, default=None, help="Override do limiar inline")
    parser.add_argument("--bc-scoped-threshold", type=int, default=None, help="Override do limiar bc_scoped")
    parser.add_argument("--json", action="store_true", help="Emite JSON (consumo pelo orquestrador)")
    args = parser.parse_args()

    try:
        budget = build_budget(
            args.project,
            language=args.language,
            inline_threshold=args.inline_threshold,
            bc_threshold=args.bc_scoped_threshold,
        )
    except Exception as exc:  # noqa: BLE001
        payload = {"project": args.project, "status": "error", "detail": str(exc), "execution_mode": "subagent"}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else f"❌ ERRO: {exc}")
        return 3

    if args.json:
        print(json.dumps(budget, ensure_ascii=False, indent=2))
    else:
        render_human(budget, args.agent)

    if budget["status"] != "ok":
        return 3
    return {"subagent": 0, "inline": 1, "bc_scoped": 2}[budget["execution_mode"]]


if __name__ == "__main__":
    sys.exit(main())
