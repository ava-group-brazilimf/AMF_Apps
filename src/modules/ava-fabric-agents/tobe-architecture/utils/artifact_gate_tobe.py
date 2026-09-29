#!/usr/bin/env python3
"""
AVA Fabric – TO-BE (F2) Artifact Gate
=====================================
Verifica, de forma **determinística e sem custo de LLM**, se os artefatos de
**entrada** de cada fase da esteira TO-BE existem em disco.

Enquanto ``asis-diagnostic/utils/artifact_gate.py`` responde *"este agente já
entregou?"* (contrato de **saída**), este módulo responde a pergunta espelhada
do lado F2:

    "Esta fase pode começar? Os artefatos que ela consome existem?"

Motivação (incidente MeuERP-002 · ISSUE-003 §5.2 e §5.3)
--------------------------------------------------------
A F1 tem gate executável desde a ISSUE-002; a F2 nunca teve. A pré-condição de
entrada da F2 era **prosa** em ``agents/orchestrator-tobe.md`` (linhas 199 e
1722), citando três artefatos apenas pelo nome de arquivo, sem diretório, e
apontando para uma seção *"Gate SD"* que nunca foi escrita.

Em ``MeuERP-002`` o orquestrador declarou os três ausentes e registrou **os 21
agentes TO-BE como SKIPPED**. Os três arquivos estavam em disco o tempo todo —
o gate da F1, rodado no mesmo instante, reportava ``12/12 artefatos (100.0%)``.

Dois defeitos independentes, ambos endereçados aqui:

1. ``db-analysis-report.md`` mora em ``outputs/asis/**db/**`` — a prosa omitia o
   subdiretório. É o mesmo erro que a ISSUE-002 §RC-2 já causou na F1 (retry
   storm) e que ``artifact_gate.py`` corrigiu com um comentário explícito.
2. Nenhum verificador da F2 ancorava em ``REPO_ROOT``. Path relativo resolve
   contra o cwd; num segundo checkout do repo sem aquele projeto, os três
   artefatos "somem". Aqui tudo resolve a partir de ``REPO_ROOT``.

Fonte da verdade
----------------
``GATES`` abaixo espelha 1:1 os ``Gate de entrada`` de
``agents/orchestrator-tobe.md``. Alterar um lado exige alterar o outro —
``tests/ava-fabric-agents/tobe-architecture/test_artifact_gate_tobe.py`` falha
se divergirem.

Uso
---
    # Gate de entrada da fase (o que faltava)
    python artifact_gate_tobe.py --project MeuERP-002 --gate entry

    # Matriz completa em 1 chamada (evita serialização — ISSUE-003 RC-3)
    python artifact_gate_tobe.py --project MeuERP-002 --all --json

    # Listar os gates declarados
    python artifact_gate_tobe.py --project MeuERP-002 --list

Exit codes
----------
    0 — COMPLETE   : pré-requisitos presentes  → **prosseguir com a fase**
    1 — INCOMPLETE : falta ao menos 1          → `skip_phase` / `abort_f2`
    2 — ERROR      : projeto/gate desconhecido, ou uso inválido

⚠️ **Semântica invertida em relação ao gate da F1.** Nos dois módulos ``0``
significa "o contrato verificado está COMPLETO". Na F1 o contrato é a *saída*
de um agente, logo ``0`` = *não despachar*. Aqui o contrato é a *entrada* de uma
fase, logo ``0`` = *prosseguir*. Nunca inverter.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[5]

# ---------------------------------------------------------------------------
# Reuso da lógica de existência/tamanho/glob da F1
# ---------------------------------------------------------------------------
# O módulo da F1 é carregado por CAMINHO, sob o nome `ava_artifact_gate_asis`, e
# **não** é registrado em `sys.modules`.
#
# Por quê: `src/shared/tools/agent_runner.py` faz `sys.path.insert(0, ASIS_UTILS)`
# seguido de `import artifact_gate` (flat). Se este arquivo se chamasse
# `artifact_gate.py`, ou se registrasse essa chave em `sys.modules`, o runner
# passaria a resolver o contrato AS-IS para o contrato TO-BE dependendo da ordem
# do sys.path — falha silenciosa, não exceção. Daí o sufixo `_tobe` no nome do
# arquivo, contra a sugestão literal da ISSUE-003 §5.2.
_ASIS_GATE_PATH = (
    REPO_ROOT / "src" / "modules" / "ava-fabric-agents"
    / "asis-diagnostic" / "utils" / "artifact_gate.py"
)
_asis_spec = importlib.util.spec_from_file_location("ava_artifact_gate_asis", _ASIS_GATE_PATH)
if _asis_spec is None or _asis_spec.loader is None:  # pragma: no cover - defesa
    raise ImportError(f"não foi possível carregar o gate AS-IS em {_ASIS_GATE_PATH}")
asis_gate = importlib.util.module_from_spec(_asis_spec)
_asis_spec.loader.exec_module(asis_gate)

#: `check_item` resolve os paths contra o `REPO_ROOT` **do módulo AS-IS**. Testes
#: que apontam para um repo falso precisam de monkeypatch nos DOIS — daí
#: `asis_gate` ser público.
check_item = asis_gate.check_item

# ---------------------------------------------------------------------------
# Gates — espelho de § Gate de entrada de agents/orchestrator-tobe.md
# ---------------------------------------------------------------------------
# Cada item herda o vocabulário de `check_item`:
#   {"path": str, "base": "asis"|"tobe"|"context"|"workspace",
#    "min_count": int (globs), "min_size": int (bytes), "kind": "dir",
#    "advisory": bool, "produced_by": str}
#
# `kind` do gate:
#   "root"  → pré-condição de ENTRADA da fase F2 inteira. A ordem 0-Pre → 0 → 1
#             → … (§ ADR-First Protocol) é inviolável, logo NENHUM dos 21 agentes
#             é independente deste gate. Reprovar aqui significa "a F2 não
#             começou" — NÃO significa 21 skips independentes.
#   "phase" → gate de fase intermediária. Reprovar = pular os agentes de
#             `blocks` e seguir com as demais fases (Non-Blocking Gate Protocol).

#: Proxy em disco para os gates que a spec expressa como
#: `ava-tobe-adr.status == "completed"` no Agent Completion Registry. O registry
#: é memória do LLM; o disco é fato — e é o disco que a fase seguinte consome.
_ADR_ITEMS: list[dict[str, Any]] = [
    {"path": "docs/decisions/ADR-*.md", "base": "tobe", "min_count": 8,
     "produced_by": "ava-tobe-adr (F2 · Fase 0)"},
    {"path": "docs/decisions/INDEX.md", "base": "tobe",
     "produced_by": "ava-tobe-adr (F2 · Fase 0)"},
]

#: Os 13 arquivos do Output Contract do migration-plan agent, distribuídos entre
#: as Fases 2.7, 3 e 4 — tabela de orchestrator-tobe.md § Fase 4.5.
_MIGRATION_OUTPUT_CONTRACT: list[dict[str, Any]] = [
    {"path": "migration/wave-model.json", "base": "tobe", "produced_by": "Fase 2.7 (trigger WM), atualizado na Fase 3"},
    {"path": "docs/integration-matrix.md", "base": "tobe", "produced_by": "Fase 2.7 (trigger WM)"},
    {"path": "docs/tshirt-sizing-rationale.md", "base": "tobe", "produced_by": "Fase 2.7 (trigger WM)"},
    {"path": "migration/migration-priority-matrix.md", "base": "tobe", "produced_by": "Fase 2.7 (trigger WM)"},
    {"path": "docs/ai-estimation-report.md", "base": "tobe", "produced_by": "Fase 4 (migration-plan-tobe)"},
    {"path": "docs/manual-gap-list.md", "base": "tobe", "produced_by": "Fase 4 (migration-plan-tobe)"},
    {"path": "docs/migration-executive-summary.md", "base": "tobe", "produced_by": "Fase 4 (migration-plan-tobe)"},
    {"path": "docs/migration-plan.md", "base": "tobe", "produced_by": "Fase 4 (migration-plan-tobe)"},
    {"path": "docs/wave-plan.md", "base": "tobe", "produced_by": "Fase 4 (migration-plan-tobe)"},
    {"path": "docs/ado-work-items.md", "base": "tobe", "produced_by": "Fase 4 (migration-plan-tobe)"},
    {"path": "diagrams/migration-gantt.mmd", "base": "tobe", "produced_by": "Fase 4 (migration-plan-tobe)"},
    {"path": "migration/migration-activity-plan.md", "base": "tobe", "produced_by": "Fase 4 (migration-plan-tobe)"},
    {"path": "migration/activity-dependency-graph.md", "base": "tobe", "produced_by": "Fase 4 (migration-plan-tobe)"},
]

#: Output Contract da Fase 4.3 — 3 arquivos.
_COEXISTENCE_OUTPUT_CONTRACT: list[dict[str, Any]] = [
    {"path": "docs/coexistence-strategy.md", "base": "tobe", "produced_by": "Fase 4.3 (coexistence-strategy-tobe)"},
    {"path": "docs/coexistence-matrix.md", "base": "tobe", "produced_by": "Fase 4.3 (coexistence-strategy-tobe)"},
    {"path": "diagrams/coexistence-architecture.mmd", "base": "tobe", "produced_by": "Fase 4.3 (coexistence-strategy-tobe)"},
]

_BC_MAP_TOBE: dict[str, Any] = {
    "path": "docs/bounded-context-map.md", "base": "tobe",
    "produced_by": "Fase 1 (architecture-design-tobe · trigger BC)",
}
_BLUEPRINT_TOBE: dict[str, Any] = {
    "path": "docs/architecture-blueprint.md", "base": "tobe",
    "produced_by": "Fase 1 (architecture-design-tobe · trigger CB)",
}
_TECH_FRAMEWORK: dict[str, Any] = {
    "path": "docs/tech-framework-document.md", "base": "tobe",
    "produced_by": "Fase 2 (architecture-technical-tobe)",
}

GATES: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------
    # RAIZ — a pré-condição que faltava. Substitui a referência histórica
    # «Gate SD» (orchestrator-tobe.md:199), que nunca existiu como seção.
    # -------------------------------------------------------------------
    "entry": {
        "phase": "0-Pre",
        "kind": "root",
        "title": "Pré-condição de entrada F2 — artefatos AS-IS essenciais",
        "spec_ref": "orchestrator-tobe.md § Gate de Entrada F2",
        "items": [
            {"path": "bounded-context-map.md", "base": "asis",
             "produced_by": "ava-asis-solution-{legacy_technology} (F1)"},
            {"path": "architecture-blueprint.md", "base": "asis",
             "produced_by": "ava-asis-solution-{legacy_technology} (F1)"},
            # ⚠️ `db/` — NÃO a raiz de asis/. ISSUE-003 §6.1: o path da raiz nunca
            # existiu em disco. A prosa de :199/:1722 omitia o subdiretório, e foi
            # exatamente essa omissão que produziu o falso negativo em MeuERP-002.
            {"path": "db/db-analysis-report.md", "base": "asis",
             "produced_by": "ava-asis-db-analyzer (F1)"},
            # Advisory por decisão de produto (specs/022-tobe-master-report-optional):
            # aparece no relatório, NÃO reprova o gate.
            {"path": "master-report.md", "base": "asis", "advisory": True,
             "produced_by": "ava-asis-orchestrator (F1)"},
            {"path": "project-config.yaml", "base": "context",
             "produced_by": "setup do projeto"},
            {"path": "src/shared/data/reference-architecture.yaml", "base": "workspace",
             "produced_by": "repositório (Canonical Input)"},
        ],
        "blocks": ["f2_pipeline"],
        "on_fail": "abort_f2",
    },
    # -------------------------------------------------------------------
    # Fases intermediárias
    # -------------------------------------------------------------------
    "bc_td": {
        "phase": "1 (inter-trigger BC → TD)",
        "kind": "phase",
        "title": "BC Map TO-BE + Context Map antes do trigger TD",
        "spec_ref": "orchestrator-tobe.md § Fase 1 — INTER-TRIGGER GATE",
        "items": [
            _BC_MAP_TOBE,
            {"path": "diagrams/context-map.mmd", "base": "tobe",
             "produced_by": "Fase 1 (architecture-design-tobe · trigger BC)"},
        ],
        "blocks": ["ava-tobe-arch-design (TD)"],
        "on_fail": "skip_phase",
    },
    "phase_1_4": {
        "phase": "1.4",
        "kind": "phase",
        "title": "Database Policy TO-BE — ADRs da Fase 0 presentes",
        "spec_ref": "orchestrator-tobe.md § Fase 1.4 — Gate de entrada",
        "items": list(_ADR_ITEMS),
        "blocks": ["ava-tobe-db-policy", "ava-tobe-db-design"],
        "on_fail": "skip_phase",
    },
    "phase_1_5": {
        "phase": "1.5",
        "kind": "phase",
        "title": "Database Design TO-BE — ADRs + sql-strategy da Fase 1.4",
        "spec_ref": "orchestrator-tobe.md § Fase 1.5 — Gates de entrada",
        "items": [
            *_ADR_ITEMS,
            {"path": "db/sql-strategy.md", "base": "tobe",
             "produced_by": "Fase 1.4 (database-policy-tobe · trigger DBP)"},
            {"path": "db/sql-strategy.manifest.json", "base": "tobe",
             "produced_by": "Fase 1.4 (database-policy-tobe · trigger DBP)"},
        ],
        "blocks": ["ava-tobe-db-design"],
        "on_fail": "skip_phase",
    },
    "phase_1_6": {
        "phase": "1.6",
        "kind": "phase",
        "title": "Security Architecture Design — ADRs da Fase 0",
        "spec_ref": "orchestrator-tobe.md § Fase 1.6 — Gate de entrada",
        "items": list(_ADR_ITEMS),
        "blocks": ["ava-tobe-security-design"],
        "on_fail": "skip_phase",
    },
    "phase_2_5": {
        "phase": "2.5",
        "kind": "phase",
        "title": "Backlog TO-BE — Tech Framework + BC Map TO-BE",
        "spec_ref": "orchestrator-tobe.md § Fase 2.5 — Gate de entrada",
        "items": [_TECH_FRAMEWORK, _BC_MAP_TOBE],
        "blocks": ["ava-tobe-backlog"],
        "on_fail": "skip_phase",
    },
    "phase_3": {
        "phase": "3 (Gate 2.5→3)",
        "kind": "phase",
        "title": "Sizing — backlog-tobe.md obrigatório",
        "spec_ref": "orchestrator-tobe.md § Gate 2.5→3",
        "items": [
            {"path": "docs/backlog-tobe.md", "base": "tobe",
             "produced_by": "Fase 2.5 (migration-plan-tobe · trigger backlog-tobe)"},
        ],
        "blocks": ["ava-tobe-measure-size"],
        "on_fail": "skip_phase",
    },
    "phase_2_7": {
        "phase": "2.7",
        "kind": "phase",
        "title": "Wave Composition — BC Map TO-BE + artefatos AS-IS",
        "spec_ref": "orchestrator-tobe.md § Fase 2.7 — Gate de entrada",
        "items": [
            _BC_MAP_TOBE,
            {"path": "project-config.yaml", "base": "context", "produced_by": "setup do projeto"},
            {"path": "inventory-report.md", "base": "asis", "produced_by": "ava-asis-inventory (F1)"},
            {"path": "bounded-context-map.md", "base": "asis",
             "produced_by": "ava-asis-solution-{legacy_technology} (F1)"},
            {"path": "gaps-risks-report.md", "base": "asis", "produced_by": "ava-asis-gaps-risks (F1)"},
            {"path": "docs/business-rules.md", "base": "asis", "produced_by": "doc:BRF (F1)"},
            {"path": "api-map.md", "base": "asis", "advisory": True,
             "produced_by": "ava-asis-solution-{legacy_technology} (F1)"},
            {"path": "db/data-structure.md", "base": "asis", "advisory": True,
             "produced_by": "ava-asis-db-analyzer (F1)"},
        ],
        "blocks": ["ava-tobe-migration-plan (WM)"],
        "on_fail": "skip_phase",
    },
    "phase_4": {
        "phase": "4 (Gate 4-A)",
        "kind": "phase",
        "title": "Migration Plan — pré-requisitos das Fases 2.5, 2.7 e 3",
        "spec_ref": "orchestrator-tobe.md § Gate de Entrada 4-A",
        "items": [
            {"path": "migration/wave-model.json", "base": "tobe", "produced_by": "Fase 2.7 (trigger WM)"},
            {"path": "docs/sizing-report.md", "base": "tobe", "produced_by": "Fase 3 (measure-size-tobe)"},
            {"path": "docs/effort-calculator.md", "base": "tobe", "produced_by": "Fase 3 (measure-size-tobe)"},
            {"path": "docs/backlog-tobe.md", "base": "tobe", "produced_by": "Fase 2.5 (trigger backlog-tobe)"},
            _BC_MAP_TOBE,
            {"path": "docs/integration-matrix.md", "base": "tobe", "produced_by": "Fase 2.7 (trigger WM)"},
            {"path": "docs/tshirt-sizing-rationale.md", "base": "tobe", "produced_by": "Fase 2.7 (trigger WM)"},
            {"path": "migration/migration-priority-matrix.md", "base": "tobe", "produced_by": "Fase 2.7 (trigger WM)"},
        ],
        "blocks": ["ava-tobe-migration-plan"],
        "on_fail": "skip_phase",
    },
    "phase_4_3": {
        "phase": "4.3",
        "kind": "phase",
        "title": "Coexistence Strategy — Output Contract da Fase 4 + Fase 1",
        "spec_ref": "orchestrator-tobe.md § Fase 4.3 — Gate de entrada",
        "items": [*_MIGRATION_OUTPUT_CONTRACT, _BC_MAP_TOBE, _BLUEPRINT_TOBE],
        "blocks": ["ava-tobe-coexistence-strategy"],
        "on_fail": "skip_phase",
    },
    "phase_4_5": {
        "phase": "4.5",
        "kind": "phase",
        "title": "Risk Mitigation — Output Contract da Fase 4 + da Fase 4.3",
        "spec_ref": "orchestrator-tobe.md § Fase 4.5 — Gate de entrada",
        "items": [*_MIGRATION_OUTPUT_CONTRACT, *_COEXISTENCE_OUTPUT_CONTRACT],
        "blocks": ["ava-tobe-risk-mitigation"],
        "on_fail": "skip_phase",
    },
    "phase_4_6": {
        "phase": "4.6",
        "kind": "phase",
        "title": "Riscos Residuais — plano de mitigação da Fase 4.5",
        "spec_ref": "orchestrator-tobe.md § Fase 4.6 — Gate de entrada",
        "items": [
            {"path": "risk-mitigation-plan.md", "base": "tobe",
             "produced_by": "Fase 4.5 (risk-mitigation-tobe)"},
            {"path": "risk-register.json", "base": "asis", "produced_by": "ava-asis-gaps-risks (F1)"},
        ],
        "blocks": ["ava-tobe-gaps-risks-residual"],
        "on_fail": "skip_phase",
    },
    "phase_4_61": {
        "phase": "4.61",
        "kind": "phase",
        "title": "OpenAPI por BC — BC Map + Blueprint TO-BE",
        "spec_ref": "orchestrator-tobe.md § Fase 4.61 — Gate de entrada",
        "items": [_BC_MAP_TOBE, _BLUEPRINT_TOBE],
        "blocks": ["openapi-spec-tobe"],
        "on_fail": "skip_phase",
    },
    "phase_5_oa": {
        "phase": "5",
        "kind": "phase",
        "title": "OpenAPI Unificado — specs por BC da Fase 4.61 + BC Map",
        "spec_ref": "orchestrator-tobe.md § Fase 5 — Gate de entrada",
        "items": [
            {
                "path": "docs/openapi/bc*.yaml", "base": "tobe", "min_count": 1,
                "produced_by": "Fase 4.61 (openapi-spec-tobe · trigger OA-BC)",
            },
            _BC_MAP_TOBE,
        ],
        "blocks": ["ava-docs-tobe"],
        "on_fail": "skip_phase",
    },
    "phase_5_1": {
        "phase": "5.1",
        "kind": "phase",
        "title": "Developer Guide — Tech Framework da Fase 2",
        "spec_ref": "orchestrator-tobe.md § Fase 5.1 — Gate de entrada",
        "items": [_TECH_FRAMEWORK],
        "blocks": ["ava-developer-guide-tobe"],
        "on_fail": "skip_phase",
    },
    "phase_5_2": {
        "phase": "5.2",
        "kind": "phase",
        "title": "Regras de Negócio TO-BE — Fase 1 + regras AS-IS",
        "spec_ref": "orchestrator-tobe.md § Fase 5.2 — Gate de entrada",
        "items": [
            _BC_MAP_TOBE,
            _BLUEPRINT_TOBE,
            {"path": "docs/business-rules.md", "base": "asis", "produced_by": "doc:BRF (F1)"},
            {"path": "docs/screen-rules.md", "base": "asis", "produced_by": "doc:RT (F1)"},
        ],
        "blocks": ["ava-tobe-docs (RN)"],
        "on_fail": "skip_phase",
    },
    "phase_6": {
        "phase": "6",
        "kind": "phase",
        "title": "User Journeys — Blueprint + BC Map TO-BE",
        "spec_ref": "orchestrator-tobe.md § Fase 6 — Gate de entrada",
        "items": [_BLUEPRINT_TOBE, _BC_MAP_TOBE],
        "blocks": ["ava-tobe-user-journeys"],
        "on_fail": "skip_phase",
    },
    "phase_6_5": {
        "phase": "6.5",
        "kind": "phase",
        "title": "Design System — ADRs da Fase 0",
        "spec_ref": "orchestrator-tobe.md § Fase 6.5 — Gate de entrada",
        "items": list(_ADR_ITEMS),
        "blocks": ["ava-tobe-designer-system"],
        "on_fail": "skip_phase",
    },
    "phase_7": {
        "phase": "7",
        "kind": "phase",
        "title": "Azure Infra Estimator — Fase 1 + Fase 2 + wave-model",
        "spec_ref": "orchestrator-tobe.md § Fase 7 — Inputs obrigatórios",
        "items": [
            {"path": "project-config.yaml", "base": "context", "produced_by": "setup do projeto"},
            _BLUEPRINT_TOBE,
            _BC_MAP_TOBE,
            # ⚠️ `migration/` — ISSUE-003 §6.2. A tabela de inputs da Fase 7 era o
            # único ponto do repo apontando `outputs/tobe/wave-model.json`; o
            # escritor (migration-plan-tobe.md) e outras 19 referências usam
            # `outputs/tobe/migration/wave-model.json`.
            {"path": "migration/wave-model.json", "base": "tobe",
             "produced_by": "Fase 2.7 (trigger WM), atualizado na Fase 3"},
            _TECH_FRAMEWORK,
        ],
        "blocks": ["ava-tobe-azure-infra-estimator"],
        "on_fail": "skip_phase",
    },
}

# Artefatos F2 mandatórios do contrato de saída da fase — espelho do
# `F1_OUTPUT_CONTRACT`. Os 12 primeiros são o gate mínimo de F2 declarado pelo
# `master-orchestrator.md` § Step 2.3; `docs/bounded-context-map.md` é
# acrescentado porque é input bloqueante de 8 dos gates acima — sua ausência
# invalida a fase mesmo que os 12 existam.
F2_OUTPUT_CONTRACT: list[str] = [
    "docs/architecture-blueprint.md",
    "docs/bounded-context-map.md",
    "docs/tech-framework-document.md",
    "diagrams/architecture-blueprint.mmd",
    "diagrams/c4-context.mmd",
    "diagrams/c4-container.mmd",
    "diagrams/class-diagram.mmd",
    "diagrams/seq-arquitetural-tobe.mmd",
    "diagrams/mer-diagram-tobe.mmd",
    "diagrams/security-architecture.mmd",
    "diagrams/migration-gantt.mmd",
    "docs/openapi/openapi-spec.yaml",
    "docs/api-map.md",
    "docs/regras-negocio.md",
]


# ---------------------------------------------------------------------------
# Verificação
# ---------------------------------------------------------------------------
def check_gate(project: str, gate: str) -> dict[str, Any]:
    """Avalia UM gate de entrada de fase.

    Espelho de ``artifact_gate.check_agent``, com a diferença semântica que dá
    nome a este módulo: a F1 verifica **saídas** de um agente, a F2 verifica
    **entradas** de uma fase.

    Itens ``advisory`` entram no relatório mas **não** decidem ``passed`` — um
    ausente ali gera ``[AVISO]``, não reprovação.
    """
    spec = GATES[gate]
    checks: list[dict[str, Any]] = []
    for item in spec["items"]:
        res = check_item(project, item)
        res["advisory"] = bool(item.get("advisory"))
        res["produced_by"] = item.get("produced_by", "—")
        checks.append(res)

    missing = [c for c in checks if not c["present"]]
    blocking = [c for c in missing if not c["advisory"]]
    passed = not blocking
    kind = spec["kind"]

    if passed:
        action, skip_scope = "proceed", "none"
    elif kind == "root":
        action, skip_scope = "abort_f2", "pipeline"
    else:
        action, skip_scope = "skip_phase", "phase"

    return {
        "project": project,
        "gate": gate,
        "phase": spec["phase"],
        "kind": kind,
        "title": spec["title"],
        "spec_ref": spec["spec_ref"],
        "status": "pass" if passed else "fail",
        "passed": passed,
        "present": [c["path"] for c in checks if c["present"]],
        "missing": [
            {
                "path": c["path"],
                "reason": c["reason"],
                "advisory": c["advisory"],
                "produced_by": c["produced_by"],
            }
            for c in missing
        ],
        "blocks": [] if passed else list(spec["blocks"]),
        "action": action,
        "skip_scope": skip_scope,
    }


def check_f2_contract(project: str) -> dict[str, Any]:
    """Completude do contrato de saída da F2 — espelho de ``check_f1_contract``."""
    base = REPO_ROOT / "projects" / project / "outputs" / "tobe"
    present, missing = [], []
    for rel in F2_OUTPUT_CONTRACT:
        (present if (base / rel).is_file() else missing).append(rel)
    return {
        "total": len(F2_OUTPUT_CONTRACT),
        "present": present,
        "missing": missing,
        "completeness_pct": round(100.0 * len(present) / len(F2_OUTPUT_CONTRACT), 1),
    }


def check_all_gates(project: str) -> dict[str, Any]:
    """Avalia **todos** os gates em uma única chamada.

    Mesma motivação do ``--wave`` da F1 (ISSUE-003 · RC-3): N chamadas de shell
    intercaladas fazem o orquestrador processar output entre elas e serializam a
    fase. Com uma chamada só, ele recebe a matriz inteira antes de decidir.
    """
    results = {gid: check_gate(project, gid) for gid in GATES}
    root_failed = any(r["kind"] == "root" and not r["passed"] for r in results.values())
    return {
        "project": project,
        "gates": results,
        "f2_output_contract": check_f2_contract(project),
        "root_failed": root_failed,
        "failed": [g for g, r in results.items() if not r["passed"]],
        "passed": [g for g, r in results.items() if r["passed"]],
    }


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------
def render_gate(res: dict[str, Any]) -> None:
    """Espelho de ``render_agent``. Numa falha de raiz emite o bloco
    ``⛔ [GATE ROOT FAILED]`` — nunca a lista dos 21 agentes TO-BE."""
    if res["passed"]:
        print(f"✅ {res['gate']:<14} (Fase {res['phase']}) → PROSSEGUIR — {res['title']}")
        for m in res["missing"]:  # só advisory chega aqui
            print(f"      ℹ {m['path']} — {m['reason']} [advisory]")
        return

    if res["kind"] == "root":
        print("⛔ [GATE ROOT FAILED] F2 não iniciada — pré-condição de entrada não satisfeita")
        print(f"     Gate            : {res['gate']} ({res['phase']}) · kind=root")
        print(f"     Spec            : {res['spec_ref']}")
        print("     Artefatos ausentes (com produtor da F1):")
        for m in res["missing"]:
            mark = "ℹ" if m["advisory"] else "✗"
            print(f"       {mark} {m['path']} — {m['reason']}  ← produzido por {m['produced_by']}")
        print("     Agentes TO-BE bloqueados: 21 (a fase não começou — NÃO são 21 skips)")
        print("     Ação recomendada: reexecutar a fase F1 para os artefatos acima e re-executar a F2.")
        return

    print(f"⚠️ {res['gate']:<14} (Fase {res['phase']}) → SKIP FASE — {res['title']}")
    for m in res["missing"]:
        mark = "ℹ" if m["advisory"] else "✗"
        suffix = " [advisory]" if m["advisory"] else f"  ← produzido por {m['produced_by']}"
        print(f"      {mark} {m['path']} — {m['reason']}{suffix}")
    print(f"      ↳ SKIPPED: {', '.join(res['blocks'])}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate de entrada das fases TO-BE: verifica em disco os artefatos que cada fase consome."
    )
    parser.add_argument("--project", required=True, help="Nome do projeto (projects/{project})")
    parser.add_argument("--gate", default=None, choices=sorted(GATES), help="ID do gate (ex: entry)")
    parser.add_argument("--all", action="store_true", help="Avalia todos os gates + contrato F2")
    parser.add_argument("--list", action="store_true", dest="list_gates", help="Lista os gates declarados")
    parser.add_argument("--json", action="store_true", help="Emite JSON (consumo pelo orquestrador)")
    parser.add_argument(
        "--recheck-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Reservado para gates de fase. PROIBIDO no gate `entry`: o único falso "
            "negativo documentado do repo foi path errado (ISSUE-003 §6.1) e um sleep "
            "cego o teria escondido em vez de expor."
        ),
    )
    args = parser.parse_args()

    if args.list_gates:
        for gid, spec in GATES.items():
            print(f"{gid:<14} Fase {spec['phase']:<22} kind={spec['kind']:<6} {spec['title']}")
        return 0

    if not (REPO_ROOT / "projects" / args.project).is_dir():
        msg = f"projeto inexistente: projects/{args.project}"
        print(json.dumps({"status": "error", "detail": msg}) if args.json else f"❌ ERRO: {msg}")
        return 2

    if args.gate == "entry" and args.recheck_ms > 0:
        msg = "--recheck-ms é proibido no gate `entry` (ver ISSUE-003 §6.1)"
        print(json.dumps({"status": "error", "detail": msg}) if args.json else f"❌ ERRO: {msg}")
        return 2

    if args.all:
        res = check_all_gates(args.project)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            line = "─" * 78
            print(line)
            print(f"🚦 TO-BE Artifact Gate — {args.project}")
            print(line)
            for gid in GATES:
                render_gate(res["gates"][gid])
            c = res["f2_output_contract"]
            print(line)
            print(f"📦 Contrato F2: {len(c['present'])}/{c['total']} artefatos ({c['completeness_pct']}%)")
            print(line)
        return 0 if not res["failed"] else 1

    if not args.gate:
        msg = "informe --gate ID, --all ou --list"
        print(json.dumps({"status": "error", "detail": msg}) if args.json else f"❌ ERRO: {msg}")
        return 2

    res = check_gate(args.project, args.gate)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        render_gate(res)
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
