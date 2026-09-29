#!/usr/bin/env python3
"""
AVA Fabric – Headroom Context · decodificador e montador de contexto
=====================================================================
**Único** lugar do repositório que conhece o formato de saída do Headroom
(invariante IV2).  Qualquer consumidor de ``outputs/asis/ast-raw/*/compressed/``
passa por aqui — nunca reimplementa o unwrap.

Por que isto existe
-------------------
A pré-compressão (``headroom_precompress.py``, no analisador externo) grava os
9 artefatos AST em dois formatos, conforme o motor disponível:

**[A] Motor real** (``headroom.compress`` → SmartCrusher).  Arrays de objetos
homogêneos viram uma *string* tabular::

    "[400]{columns:int,kind:string,loc:int,name:string,pk:string,schema:string}\\n"
    "3,table,100,TBL_000,ID_0,dbo\\n4,table,101,TBL_001,ID_1,dbo\\n…"

Cabeçalho ``[N]{chave:tipo,…}`` (chaves em ordem alfabética) + linhas **CSV
RFC 4180** — aspas duplas, escape ``""``, quebras de linha dentro de campo
citado, campo vazio = ``null``.  Tipos: ``string`` · ``int`` · ``float`` ·
``bool`` · ``json``; sufixo ``?`` = nullable.  É **lossless**.

**[B] Motor fallback** (``fallback-smartcrusher-lite``, sem ``headroom-ai``)::

    {"__headroom__": "factored_array", "schema": [...], "count": 400,
     "kept": 90, "sampled": true, "rows": [[...], ...]}

Aqui ``sampled: true`` significa **perda real** (``kept`` < ``count``) — a
decodificação devolve as linhas mantidas e sinaliza a perda em
``decode_report()``.

Foi exatamente o formato [A] que obrigou ``sql_ir_generator.py`` a voltar para
``extraction/`` (``table.get(...)`` estourando ``AttributeError`` sobre uma
``str``).  Com este módulo, o consumidor lê ``compressed/`` sem risco.

Uso
---
    from headroom_context import decode_headroom, read_artifact, build_agent_context

    schemas = read_artifact("processaERP-008", "04_database_schemas")
    ctx     = build_agent_context("processaERP-008", "ava-asis-db-analyzer")

Fatia por agente
----------------
A lista de artefatos de cada agente vem de ``AGENT_ARTIFACT_SLICE`` em
``asis-diagnostic/utils/context_budget.py`` — **fonte canônica única**
(specs/030).  Este módulo importa aquele dict; nunca mantém uma cópia.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
VENDOR_DIR = SCRIPT_DIR / "vendor"

_CONTEXT_BUDGET_PATH = (
    REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "asis-diagnostic"
    / "utils" / "context_budget.py"
)

FACTORED_MARKER = "__headroom__"
FACTORED_KIND = "factored_array"


# ─── Import defensivo do motor (IV3) ─────────────────────────────────────────
# A esteira roda sem headroom-ai instalado: só a compressão fica indisponível,
# a decodificação é 100% stdlib.
def _probe_headroom() -> bool:
    try:
        import headroom  # noqa: F401
        return True
    except Exception:
        if VENDOR_DIR.is_dir() and str(VENDOR_DIR) not in sys.path:
            sys.path.insert(0, str(VENDOR_DIR))
            try:
                import headroom  # noqa: F401
                return True
            except Exception:
                return False
        return False


HEADROOM_AVAILABLE: bool = _probe_headroom()


# ─── Import da fonte canônica de fatias (IV1) ────────────────────────────────

def _load_context_budget():
    """Importa ``context_budget.py`` por path — não é um pacote importável."""
    if not _CONTEXT_BUDGET_PATH.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            "ava_context_budget", _CONTEXT_BUDGET_PATH)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 - ausência do módulo degrada, não quebra
        return None


_CB = _load_context_budget()

#: Fatia de artefatos por agente. Vazio se ``context_budget.py`` sumir.
AGENT_ARTIFACT_SLICE: dict[str, list[str]] = (
    dict(getattr(_CB, "AGENT_ARTIFACT_SLICE", {})) if _CB else {}
)


# ─── Decodificação do formato [A] — string tabular do SmartCrusher ───────────

def _parse_table_header(header: str) -> tuple[int, list[str], list[str]] | None:
    """Interpreta ``[N]{k1:t1,k2:t2,…}``.

    Devolve ``(count, chaves, tipos)`` ou ``None`` se a linha não for um
    cabeçalho tabular do SmartCrusher.
    """
    if not header.startswith("[") or "]{" not in header or not header.endswith("}"):
        return None
    count_part, _, schema_part = header.partition("]{")
    try:
        count = int(count_part[1:])
    except ValueError:
        return None
    keys: list[str] = []
    types: list[str] = []
    for field in schema_part[:-1].split(","):
        name, _, kind = field.partition(":")
        if not name:
            return None
        keys.append(name)
        types.append(kind or "string")
    return (count, keys, types) if keys else None


def _coerce_cell(raw: str, kind: str) -> Any:
    """Converte uma célula CSV para o tipo declarado no cabeçalho."""
    nullable = kind.endswith("?")
    base = kind[:-1] if nullable else kind
    if raw == "":
        # Campo vazio é ``null`` em coluna nullable; string vazia caso contrário.
        return None if nullable or base != "string" else ""
    try:
        if base == "int":
            return int(raw)
        if base == "float":
            return float(raw)
        if base == "bool":
            return raw.strip().lower() == "true"
        if base == "json":
            return json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        # Célula fora do tipo declarado: preserva o texto em vez de perder o dado.
        return raw
    return raw


def _is_table_string(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("[")
        and "]{" in value[:400]
        and "\n" in value
    )


def decode_table_string(value: str) -> list[dict[str, Any]] | None:
    """Reverte a string tabular do SmartCrusher para ``list[dict]``.

    Devolve ``None`` se ``value`` não estiver no formato — o chamador mantém o
    valor original (degradar, nunca corromper).
    """
    header, sep, body = value.partition("\n")
    if not sep:
        return None
    parsed = _parse_table_header(header)
    if parsed is None:
        return None
    _count, keys, types = parsed

    # csv.reader trata aspas, ``""`` e newline dentro de campo citado.
    rows: list[dict[str, Any]] = []
    for cells in csv.reader(io.StringIO(body)):
        if not cells or (len(cells) == 1 and cells[0] == ""):
            continue
        record: dict[str, Any] = {}
        for idx, key in enumerate(keys):
            record[key] = _coerce_cell(cells[idx], types[idx]) if idx < len(cells) else None
        rows.append(record)
    return rows


# ─── Decodificação do formato [B] — factored_array do fallback ───────────────

def _decode_factored_array(node: dict[str, Any]) -> list[dict[str, Any]]:
    """Reverte ``{"__headroom__": "factored_array", …}`` para ``list[dict]``."""
    schema = node.get("schema") or []
    rows = node.get("rows") or []
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):          # já decodificado
            out.append(row)
        elif isinstance(row, (list, tuple)):
            out.append(dict(zip(schema, row)))
    return out


# ─── API pública de decodificação ────────────────────────────────────────────

def decode_headroom(node: Any) -> Any:
    """Decodifica recursivamente qualquer envelope Headroom em ``node``.

    Idempotente: conteúdo já decodificado (ou nunca comprimido) volta igual.
    """
    if isinstance(node, dict):
        if node.get(FACTORED_MARKER) == FACTORED_KIND:
            return _decode_factored_array(node)
        return {key: decode_headroom(value) for key, value in node.items()}
    if isinstance(node, list):
        return [decode_headroom(item) for item in node]
    if _is_table_string(node):
        decoded = decode_table_string(node)
        return decoded if decoded is not None else node
    return node


def decode_report(node: Any) -> dict[str, Any]:
    """Audita um documento decodificado: quantos envelopes e quanta perda.

    ``rows_dropped > 0`` só acontece no motor fallback com ``sampled: true``.
    """
    report = {"factored_arrays": 0, "table_strings": 0, "rows_total": 0, "rows_dropped": 0}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get(FACTORED_MARKER) == FACTORED_KIND:
                report["factored_arrays"] += 1
                count = int(value.get("count") or 0)
                kept = int(value.get("kept") or len(value.get("rows") or []))
                report["rows_total"] += count
                report["rows_dropped"] += max(0, count - kept)
                return
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif _is_table_string(value):
            report["table_strings"] += 1
            parsed = _parse_table_header(value.partition("\n")[0])
            if parsed:
                report["rows_total"] += parsed[0]

    walk(node)
    return report


# ─── Leitura de artefatos ────────────────────────────────────────────────────

def resolve_compressed_dir(project: str, language: str | None = None) -> Path | None:
    """Delegado para ``context_budget.resolve_compressed_dir`` (fonte única)."""
    if _CB is not None:
        return _CB.resolve_compressed_dir(project, language)
    return None


def resolve_extraction_dir(project: str, language: str | None = None) -> Path | None:
    """Diretório ``extraction/`` (JSON cru) correspondente ao ``compressed/``."""
    compressed = resolve_compressed_dir(project, language)
    if compressed is not None:
        candidate = compressed.parent / "extraction"
        if candidate.is_dir():
            return candidate
    base = REPO_ROOT / "projects" / project / "outputs" / "asis"
    if language:
        candidate = base / "ast-raw" / language / "extraction"
        if candidate.is_dir():
            return candidate
    ast_raw = base / "ast-raw"
    if ast_raw.is_dir():
        for child in sorted(ast_raw.iterdir()):
            if (child / "extraction").is_dir():
                return child / "extraction"
    return None


def read_artifact(
    project: str,
    artifact: str,
    language: str | None = None,
    *,
    prefer_compressed: bool = True,
) -> dict[str, Any]:
    """Lê um artefato AST **já decodificado**.

    ``artifact`` é o nome sem extensão (``"04_database_schemas"``).  Tenta
    ``compressed/`` primeiro (economia de contexto) e cai para ``extraction/``
    quando o comprimido não existe.  Devolve ``{}`` se nenhum existir.
    """
    name = artifact if artifact.endswith(".json") else f"{artifact}.json"
    order: list[Path | None] = (
        [resolve_compressed_dir(project, language), resolve_extraction_dir(project, language)]
        if prefer_compressed
        else [resolve_extraction_dir(project, language), resolve_compressed_dir(project, language)]
    )
    for directory in order:
        if directory is None:
            continue
        path = directory / name
        if not path.is_file():
            continue
        try:
            return decode_headroom(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def read_artifact_payload(project: str, artifact: str, language: str | None = None) -> Any:
    """Atalho para ``read_artifact(...)["payload"]`` (os 9 artefatos usam esse envelope)."""
    doc = read_artifact(project, artifact, language)
    return doc.get("payload", doc) if isinstance(doc, dict) else doc


# ─── Métricas de compressão ──────────────────────────────────────────────────

def read_compression_metrics(project: str, language: str | None = None) -> dict[str, Any]:
    """Lê o ``manifest.json`` da pré-compressão (motor, tokens, transforms)."""
    compressed = resolve_compressed_dir(project, language)
    if compressed is None:
        return {}
    try:
        return json.loads((compressed / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def estimate_agent_tokens(project: str, agent_id: str, language: str | None = None) -> int:
    """Soma ``tokens_out`` dos artefatos da fatia do agente."""
    manifest = read_compression_metrics(project, language)
    per_artifact = {
        entry.get("artifact"): int(entry.get("tokens_out") or 0)
        for entry in manifest.get("artifacts", [])
        if entry.get("artifact")
    }
    return sum(per_artifact.get(name, 0) for name in AGENT_ARTIFACT_SLICE.get(agent_id, []))


# ─── Montagem do contexto do agente ──────────────────────────────────────────

def build_agent_context(
    project: str,
    agent_id: str,
    language: str | None = None,
    *,
    include_payloads: bool = True,
) -> dict[str, Any]:
    """Monta o contexto de **um** agente: só a fatia que ele consome.

    Nunca devolve o payload inteiro do projeto — foi a causa-raiz RC-1 da
    ISSUE-002 (761.376 tokens por ``runSubagent``).  Fatia ``[]`` significa
    agente de consolidação: lê artefatos de outros agentes, nenhum AST.
    """
    slice_names = AGENT_ARTIFACT_SLICE.get(agent_id)
    known = slice_names is not None
    slice_names = slice_names or []

    context: dict[str, Any] = {
        "project": project,
        "agent_id": agent_id,
        "known_agent": known,
        "artifacts": slice_names,
        "tokens_estimated": estimate_agent_tokens(project, agent_id, language),
        "compressed_dir": str(resolve_compressed_dir(project, language) or ""),
        "headroom_available": HEADROOM_AVAILABLE,
    }
    if include_payloads:
        context["payloads"] = {
            name: read_artifact_payload(project, name, language) for name in slice_names
        }
    return context


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Decodifica artefatos Headroom e monta o contexto de um agente")
    ap.add_argument("-p", "--project", required=True)
    ap.add_argument("--agent", help="Monta o contexto deste agent_id")
    ap.add_argument("--artifact", help="Decodifica e imprime este artefato")
    ap.add_argument("--language")
    ap.add_argument("--no-payloads", action="store_true",
                    help="Com --agent: omite os payloads (só a fatia e os tokens)")
    args = ap.parse_args()

    if args.artifact:
        doc = read_artifact(args.project, args.artifact, args.language)
        print(json.dumps(doc, indent=2, ensure_ascii=False))
    elif args.agent:
        ctx = build_agent_context(args.project, args.agent, args.language,
                                  include_payloads=not args.no_payloads)
        print(json.dumps(ctx, indent=2, ensure_ascii=False))
    else:
        ap.error("informe --agent ou --artifact")
