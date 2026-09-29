"""
schemas.py — Envelope comum e contrato dos 8 artefatos JSON do AVA Fabric.

Cada ponto do levantamento Delphi gera UM arquivo JSON estruturado, todos com
o mesmo envelope. Detalhe de design importante para o Headroom:

    O bloco `_volatile` (timestamp, run_id) fica ISOLADO e por ÚLTIMO.
    Isso mantém o prefixo estável entre execuções — exatamente o que o
    CacheAligner do Headroom precisa para maximizar cache-hit no provider.
    O agente raciocina sobre `payload`; `_volatile` nunca muda a semântica.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "0.1.0"
ANALYZER = "delphi_ast_analyzer/0.1.0"

# Nome de arquivo -> descrição do artefato (mapeamento 1:1 com os 8 pontos)
ARTIFACTS = {
    "01_business_rules":       "Regras de negócio (validações, cálculos, workflow no código)",
    "02_form_business_rules":  "Regras de negócio em telas/forms com tratamento de campos",
    "03_database_rules":       "Regras de banco (constraints, transações, integridade)",
    "04_database_schemas":     "Schemas de banco (tabelas, colunas, chaves, índices) — inclui DDL de .sql",
    "05_procedures":           "Procedures (stored procedures + procedures/functions do código)",
    "06_integrations":         "Integrações (DLL, COM, sockets, e-mail, arquivos, filas)",
    "07_apis":                 "APIs usadas (REST/SOAP/HTTP clients e endpoints)",
    "08_code_overview":        "Levantamento geral (LOC, módulos, forms, telas, métricas)",
    "09_test_coverage":        "Cobertura de testes (frameworks DUnit/DUnitX, fixtures, testes e indicadores auxiliares de teste)",
}


def envelope(artifact: str, payload: dict[str, Any], source_root: str,
             run_id: str) -> dict[str, Any]:
    """Empacota o payload no envelope padrão, com voláteis isolados no fim."""
    return {
        "artifact": artifact,
        "schema_version": SCHEMA_VERSION,
        "project": "AVA Fabric - Legacy Delphi Migration",
        "description": ARTIFACTS.get(artifact, artifact),
        "payload": payload,
        # ---- tudo que muda a cada run fica aqui, por último (CacheAligner) ----
        "_volatile": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "analyzer": ANALYZER,
            "source_root": source_root,
        },
    }


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]
