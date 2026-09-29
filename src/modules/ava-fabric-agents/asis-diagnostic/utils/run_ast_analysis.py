#!/usr/bin/env python3
"""
AVA Fabric – Multi-Language AST Analysis Router
================================================
Detects the legacy source language from file extensions (or configuration) and
dispatches the appropriate AST analyzer:

    * Delphi   -> ava-fabric-delphi-analyzer
    * .NET     -> ava-fabric-dotnet-analyzer (C#/VB)
    * Java     -> ava-fabric-java-analyzer

Outputs are written to language-specific subfolders under
``projects/{PROJECT_NAME}/outputs/asis/ast-raw/{language}/`` so that results are
human-auditable and multiple languages can coexist in the same workspace.

Usage
-----
    python run_ast_analysis.py --project Meu-ERP
    python run_ast_analysis.py --project Meu-ERP --language dotnet
    python run_ast_analysis.py --project Meu-ERP --language delphi --brs-llm
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = {"delphi", "dotnet", "java"}
LEGACY_STUB_LANGUAGES = {"cobol", "vb6", "powerbuilder"}

LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "delphi": [".pas", ".dfm", ".dpr", ".dpk", ".dproj"],
    "dotnet": [".cs", ".vb", ".sln", ".csproj", ".vbproj", ".resx"],
    "java": [".java"],
    "cobol": [".cob", ".cbl", ".cpy"],
    "vb6": [".frm", ".bas", ".cls", ".vbp"],
    "powerbuilder": [".srd", ".sru", ".srw", ".srm", ".pbl"],
}

LANGUAGE_BUILD_FILES: dict[str, list[str]] = {
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "dotnet": [],
    "delphi": [],
}

_ENV_VAR_MAP: dict[str, str] = {
    "delphi": "AVA_DELPHI_ANALYZER_HOME",
    "dotnet": "AVA_DOTNET_ANALYZER_HOME",
    "java": "AVA_JAVA_ANALYZER_HOME",
}

# Raiz do repositório: este arquivo mora em
# src/modules/ava-fabric-agents/asis-diagnostic/utils/, logo parents[5] é a raiz.
_REPO_ROOT = Path(__file__).resolve().parents[5]

# Credenciais da etapa 5 do pipeline BRS (--brs-llm). Os nomes espelham
# `_resolve_settings` do analyzer (src/brs/llm_extract.py) — não inventar outros.
_BRS_ENV_KEYS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_LLM_MODEL",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_API_VERSION",
)


def _mask_secret(value: str | None) -> str:
    """Mask secrets while still indicating whether a value is present."""
    if not value:
        return "(missing)"
    return "***"


def _mask_value(key: str, value: str | None) -> str:
    """Mask sensitive values and keep non-sensitive values visible for diagnostics."""
    if key.endswith("_API_KEY"):
        return _mask_secret(value)
    return value if value else "(missing)"

# Files expected in extraction and compressed directories for validation
_EXPECTED_EXTRACTION_FILES = [
    f"{i:02d}_{name}.json"
    for i, name in enumerate(
        [
            "business_rules",
            "form_business_rules",
            "database_rules",
            "database_schemas",
            "procedures",
            "integrations",
            "apis",
            "code_overview",
            "test_coverage",
            "sql_functions",
        ],
        start=1,
    )
]
_EXPECTED_COMPRESSED_FILES = ["manifest.json", "metrics.jsonl"]

# Analyzer-specific extraction files that are allowed to be absent
_OPTIONAL_EXTRACTION_FILES: dict[str, set[str]] = {
    "java": {"10_sql_functions.json"},
}

# Canonical business-rule categories used as fallback when the analyzer did not
# classify a rule or only emitted a generic placeholder.
_DOMAIN_CATEGORIES = {
    "validation",
    "calculation",
    "threshold_condition",
    "state_classification",
    "workflow_decision",
    "data_access",
    "authorization",
    "exception_handling",
    "ui_event",
}

# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------
def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _payload_any(data: dict[str, Any]) -> dict[str, Any]:
    """Return the payload dictionary regardless of its key casing."""
    if not isinstance(data, dict):
        return {}
    return data.get("payload") or data.get("Payload") or {}


def _classify_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Enrich a rule with a meaningful domain category when missing/generic."""
    rule = dict(rule)
    typ = str(rule.get("type") or "").lower()
    category = str(rule.get("category") or "").lower()
    expression = str(rule.get("expression") or rule.get("summary") or "").lower()
    method = str(rule.get("method") or "").lower()
    target = str(rule.get("target") or "").lower()

    if category and category not in {"general", "unknown", ""}:
        return rule

    # Map analyzer-native types to canonical categories
    type_map = {
        "calculation": "calculation",
        "conditional_logic": "threshold_condition",
        "case_decision": "state_classification",
        "validation_guard": "validation",
        "guard_clause": "validation",
        "loop_aggregation": "calculation",
        "data_access": "data_access",
        "exception_handling": "exception_handling",
        "authorization": "authorization",
        "workflow_decision": "workflow_decision",
        "ui_event": "ui_event",
    }
    category = type_map.get(typ, "")
    if not category:
        if any(k in expression or k in target for k in
               ("== null", "!= null", "is null", "is nothing", "isnot", "is not nothing",
                "isnullorempty", "string.isnullor", "null ", "!= """, "== """)):
            category = "validation"
        elif any(k in expression for k in
                 (" + ", " - ", " * ", " / ", "%", ".sum", ".count", ".avg", ".min", ".max")):
            category = "calculation"
        elif any(k in expression for k in ("if ", "then", "else", "?", "switch", "select case")):
            category = "threshold_condition"
        elif any(k in method for k in ("validate", "check", "assert", "guard")):
            category = "validation"
        elif any(k in method for k in ("calculate", "compute", "sum", "total")):
            category = "calculation"
        elif any(k in method for k in ("save", "insert", "update", "delete", "persist")):
            category = "data_access"
        elif any(k in method for k in ("authorize", "allow", "deny", "permission", "role")):
            category = "authorization"
        else:
            category = "workflow_decision"

    rule["category"] = category
    # Backfill type when absent so downstream consumers see a stable shape
    if not rule.get("type"):
        rule["type"] = category
    return rule


def _normalize_source_ref(rule: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested source_ref.* keys into a standard source_ref dict."""
    rule = dict(rule)
    if isinstance(rule.get("source_ref"), dict):
        return rule
    src: dict[str, Any] = {}
    for key in list(rule.keys()):
        if key.startswith("source_ref."):
            src[key.split(".", 1)[1]] = rule.pop(key)
        elif key == "source" and isinstance(rule[key], str):
            src.setdefault("file", rule[key])
        elif key in ("line", "column"):
            src[key] = rule[key]
    if src:
        rule.setdefault("source_ref", src)
    return rule


def _normalize_business_rules(path: Path) -> None:
    """Ensure 01_business_rules.json exposes payload.rules[] with totals."""
    data = _read_json(path)
    if data is None:
        return
    payload = _payload_any(data)

    # Recent analyzers emit the rules list directly in the payload slot
    rules: list[dict[str, Any]] = []
    if isinstance(payload, list):
        rules = [r for r in payload if isinstance(r, dict)]
    elif isinstance(payload, dict) and isinstance(payload.get("rules"), list):
        rules = [r for r in payload["rules"] if isinstance(r, dict)]
    elif isinstance(payload, dict) and isinstance(payload.get("rules"), str):
        # Legacy Delphi bucketed string — leave untouched
        return
    else:
        rules = []

    normalized = []
    for r in rules:
        r = _normalize_source_ref(_classify_rule(r))
        r.setdefault("id", r.get("ast_ref", ""))
        r.setdefault("type", r.get("category", "workflow_decision"))
        r.setdefault("unit", r.get("unit", "") or r.get("containing_type", ""))
        r.setdefault("method", r.get("method", "") or r.get("containing_member", ""))
        r.setdefault("target", r.get("target", "") or r.get("variable", "") or r.get("action", ""))
        r.setdefault("expression", r.get("expression", "") or r.get("condition", ""))
        r.setdefault("source_ref", r.get("source_ref", {}))
        normalized.append(r)

    new_payload: dict[str, Any] = {
        "rules": normalized,
        "counts": {"total": len(normalized)},
    }
    out = {
        "artifact": str(data.get("Artifact", data.get("artifact", "business_rules"))),
        "schema_version": str(data.get("SchemaVersion", data.get("schema_version", "1.0.0"))),
        "payload": new_payload,
    }
    if isinstance(data, dict) and data.get("_Volatile"):
        out["_volatile"] = data["_Volatile"]
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_form_business_rules(path: Path) -> None:
    """Ensure 02_form_business_rules.json exposes payload.forms[] with counts.

    Accepts:
      - .NET flat list of FormInfo objects in Payload
      - Java canonical object {counts, forms[]}
      - legacy string/table-compacted payloads (left untouched)
    """
    data = _read_json(path)
    if data is None:
        return
    payload = _payload_any(data)

    # Legacy string payloads are produced by the Delphi analyzer pre-compression.
    if isinstance(payload, str):
        return

    if isinstance(payload, list):
        raw_forms = [f for f in payload if isinstance(f, dict)]
    elif isinstance(payload, dict) and isinstance(payload.get("forms"), list):
        raw_forms = [f for f in payload["forms"] if isinstance(f, dict)]
    else:
        return

    forms = [_normalize_form(f) for f in raw_forms]
    counts = {
        "forms": len(forms),
        "fields": sum(f.get("field_count", len(f.get("fields", []))) for f in forms),
    }

    out = {
        "artifact": str(data.get("Artifact", data.get("artifact", "form_business_rules"))),
        "schema_version": str(data.get("SchemaVersion", data.get("schema_version", "1.0.0"))),
        "payload": {"counts": counts, "forms": forms},
    }
    if isinstance(data, dict) and data.get("_Volatile"):
        out["_volatile"] = data["_Volatile"]
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def _distribute_form_handlers(
    fields: list[dict[str, Any]], handlers_raw: Any
) -> list[dict[str, Any]]:
    """Merge form-level .NET handler entries (``ctrl.Event => method``) into the matching control."""
    handlers: list[str] = []
    if isinstance(handlers_raw, dict):
        handlers = [f"{k} => {v}" for k, v in handlers_raw.items() if v not in (None, "", {}, [])]
    elif isinstance(handlers_raw, list):
        handlers = [str(h) for h in handlers_raw if h not in (None, "", {}, [])]

    for entry in handlers:
        if "=>" not in entry:
            continue
        left, method = entry.split("=>", 1)
        left = left.strip()
        method = method.strip()
        if "." not in left:
            continue
        control_name, event = left.rsplit(".", 1)
        for field in fields:
            if field.get("name") == control_name:
                field["event_handlers"][event] = method
                if "valid" in event.lower():
                    field["has_validation"] = True
    return handlers


def _normalize_form(form: dict[str, Any]) -> dict[str, Any]:
    """Flatten a single analyzer-native form record into the canonical shape."""
    form = dict(form)
    if isinstance(form.get("fields"), list):
        raw_fields = form["fields"]
    elif isinstance(form.get("Fields"), list):
        raw_fields = form["Fields"]
    else:
        raw_fields = form.get("Controls") or form.get("controls") or []
    fields = [_normalize_control(c) for c in raw_fields if isinstance(c, dict)]

    handlers_raw = form.get("EventHandlers") or form.get("event_handlers") or []
    event_handlers = _distribute_form_handlers(fields, handlers_raw)

    source_ref = _normalize_source_ref_dict(form.get("SourceRef") or form.get("source_ref") or {})

    return {
        "form_name": str(form.get("Name") or form.get("name") or form.get("form_name") or "").strip(),
        "form_class": str(form.get("form_class") or form.get("Name") or form.get("name") or "").strip(),
        "form_type": str(form.get("FormType") or form.get("form_type") or "").strip(),
        "source_file": str(form.get("source_file") or source_ref.get("file") or "").strip(),
        "source_ref": source_ref,
        "field_count": len(fields),
        "fields": fields,
        "event_handlers": event_handlers,
    }


def _normalize_control(control: dict[str, Any]) -> dict[str, Any]:
    """Flatten a single analyzer-native control into the canonical field shape."""
    control = dict(control)
    props: dict[str, Any] = {}
    if isinstance(control.get("properties"), dict):
        props.update(control["properties"])
    if isinstance(control.get("Properties"), dict):
        props.update(control["Properties"])
    text = control.get("Text") or control.get("text")
    if text not in (None, ""):
        props["text"] = text

    data_bindings = control.get("DataBindings") or control.get("data_bindings") or []
    if isinstance(data_bindings, str):
        data_bindings = [data_bindings] if data_bindings else []

    handlers_raw = control.get("EventHandlers") or control.get("event_handlers") or {}
    event_handlers: dict[str, str] = {}
    if isinstance(handlers_raw, dict):
        for k, v in handlers_raw.items():
            if v not in (None, "", {}, []):
                event_handlers[str(k)] = str(v)
    elif isinstance(handlers_raw, list):
        for h in handlers_raw:
            if isinstance(h, str) and "=>" in h:
                k, v = h.split("=>", 1)
                event_handlers[k.strip()] = v.strip()
            elif h not in (None, "", {}, []):
                event_handlers[str(h)] = str(h)

    has_validation = any(
        "valid" in k.lower() or "valid" in str(v).lower()
        for k, v in event_handlers.items()
    )

    return {
        "name": str(control.get("Name") or control.get("name") or "").strip(),
        "component_class": str(control.get("ControlType") or control.get("component_class") or control.get("type") or "").strip(),
        "properties": props,
        "data_bindings": [str(b) for b in data_bindings],
        "event_handlers": event_handlers,
        "has_validation": has_validation,
    }


def _normalize_source_ref_dict(src: Any) -> dict[str, Any]:
    """Normalize a source-ref object to lowercase canonical keys."""
    if not isinstance(src, dict):
        return {}
    key_map = {
        "File": "file",
        "Line": "line",
        "Column": "column",
        "ContainingType": "containing_type",
        "ContainingMember": "containing_member",
    }
    out: dict[str, Any] = {}
    for k, v in src.items():
        out[key_map.get(k, k)] = v
    return out


def _normalize_overview(path: Path) -> None:
    """Ensure 08_code_overview.json exposes payload.totals consistently."""
    data = _read_json(path)
    if data is None:
        return
    payload = _payload_any(data)
    if not isinstance(payload, dict):
        payload = {}

    totals = payload.get("totals") or payload.get("Totals")
    if not isinstance(totals, dict):
        totals = {}

    # Derive canonical totals from legacy/recent field names when not present
    if not totals:
        totals = {
            "units_total": payload.get("TotalFiles") or payload.get("totalFiles") or payload.get("units_total") or 0,
            "lines_of_code": payload.get("TotalLoc") or payload.get("totalLinesOfCode") or payload.get("lines_of_code") or 0,
            "classes": payload.get("TotalClasses") or payload.get("totalClasses") or payload.get("classes") or 0,
            "modules": payload.get("TotalModules") or payload.get("modules") or 0,
            "forms": payload.get("TotalForms") or payload.get("totalForms") or payload.get("forms") or 0,
            "procedures": payload.get("TotalProcedures") or payload.get("totalMethods") or payload.get("procedures") or 0,
            "methods": payload.get("TotalProcedures") or payload.get("totalMethods") or payload.get("methods") or 0,
            "business_rules": payload.get("BusinessRules") or payload.get("business_rules") or 0,
            "db_tables": payload.get("DatabaseTables") or payload.get("db_tables") or 0,
            "db_relationships": payload.get("DatabaseRelationships") or payload.get("db_relationships") or 0,
            "integrations": payload.get("Integrations") or payload.get("integrations") or 0,
            "apis": payload.get("Apis") or payload.get("apis") or 0,
            "sql_functions": payload.get("SqlFunctions") or payload.get("sql_functions") or 0,
            "tests": payload.get("TotalTests") or payload.get("totalTests") or payload.get("tests") or 0,
        }

    payload = dict(payload)
    payload["totals"] = totals

    out = {
        "artifact": str(data.get("Artifact", data.get("artifact", "code_overview"))),
        "schema_version": str(data.get("SchemaVersion", data.get("schema_version", "1.0.0"))),
        "payload": payload,
    }
    if isinstance(data, dict) and data.get("_Volatile"):
        out["_volatile"] = data["_Volatile"]
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_manifest_metrics(compressed_dir: Path, extraction_dir: Path) -> None:
    """For analyzers that do not emit manifest.json / metrics.jsonl, synthesize them."""
    overview_path = extraction_dir / "08_code_overview.json"
    overview = _read_json(overview_path) or {}
    payload = _payload_any(overview)
    totals = payload.get("totals", {}) if isinstance(payload, dict) else {}

    if not (compressed_dir / "manifest.json").exists():
        manifest = {
            "source_root": str(extraction_dir.parent / "source"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "ratio": 1.0,
        }
        for json_file in sorted(compressed_dir.glob("*.json")):
            text = json_file.read_text(encoding="utf-8")
            data = json.loads(text)
            manifest["files"].append({
                "file": json_file.name,
                "artifact": data.get("artifact") or data.get("Artifact"),
                "tokens_in": 0,
                "tokens_out": len(text),
            })
            manifest["tokens_out"] += len(text)
        compressed_dir.mkdir(parents=True, exist_ok=True)
        (compressed_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    if not (compressed_dir / "metrics.jsonl").exists():
        line = {
            "run_id": "unknown",
            "exec_date": datetime.now(timezone.utc).isoformat(),
            "source_root": str(extraction_dir.parent / "source"),
            "ast_mode": "code_overview",
            "engine": "normalized",
            "language": extraction_dir.parent.name,
            "extraction_duration_ms": 0,
            "precompress_duration_ms": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "reduction_pct": 0,
            "artifact_counts": {
                "units_total": totals.get("units_total", 0),
                "business_rules": totals.get("business_rules", 0),
                "forms": totals.get("forms", 0),
                "db_tables": totals.get("db_tables", 0),
                "db_relationships": totals.get("db_relationships", 0),
                "integrations": totals.get("integrations", 0),
                "apis": totals.get("apis", 0),
                "sql_functions": totals.get("sql_functions", 0),
            },
            "status": "ok",
        }
        (compressed_dir / "metrics.jsonl").write_text(
            json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8"
        )


def _normalize_ast_artifacts(extraction_dir: Path, compressed_dir: Path) -> None:
    """Rewrite rules/overview/forms so downstream agents see a stable lowercase envelope."""
    for base in (extraction_dir, compressed_dir):
        br = base / "01_business_rules.json"
        if br.exists():
            _normalize_business_rules(br)
        fr = base / "02_form_business_rules.json"
        if fr.exists():
            _normalize_form_business_rules(fr)
        ov = base / "08_code_overview.json"
        if ov.exists():
            _normalize_overview(ov)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
def _load_config(project_name: str) -> dict[str, Any]:
    config_path = Path(f"projects/{project_name}/context/project-config.yaml")
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_analyzer_home(config: dict[str, Any], language: str) -> Path | None:
    """Resolve analyzer home: config map -> env var -> sibling repo."""
    raw: str | None = None

    # 1. New-style map
    analyzers = config.get("ava_ast_analyzers") or {}
    if isinstance(analyzers, dict):
        raw = analyzers.get(language)

    # 2. Legacy alias for Delphi
    if not raw and language == "delphi":
        raw = config.get("ava_ast_analyzer_path")

    # 3. Environment variable
    if not raw:
        raw = os.environ.get(_ENV_VAR_MAP.get(language, ""))

    if raw:
        p = Path(raw)
        return p if p.is_absolute() else p.resolve()

    # 4. Sibling repo in the multi-root workspace: try CWD first, then script dir
    #    and keep walking up to the filesystem root (supports repos nested in
    #    a parent workspace folder such as C:\_git\fix next to C:\_git\imfai-ava-tools).
    candidates = []
    candidates.append(Path(f"../imfai-ava-tools/ava-fabric-{language}-analyzer").resolve())
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir
    while True:
        sibling_candidate = repo_root.parent / "imfai-ava-tools" / f"ava-fabric-{language}-analyzer"
        candidates.append(sibling_candidate.resolve())
        if repo_root.parent == repo_root:
            break
        repo_root = repo_root.parent
    for sibling in candidates:
        if sibling.exists():
            return sibling

    return None


# ---------------------------------------------------------------------------
# Credenciais do pipeline BRS (--brs-llm)
# ---------------------------------------------------------------------------
def _read_env_file(path: Path) -> dict[str, str]:
    """Lê um arquivo .env e devolve seus pares chave=valor ({} se não existir)."""
    if not path.is_file():
        return {}

    try:
        from dotenv import dotenv_values
    except ImportError:
        dotenv_values = None

    if dotenv_values is not None:
        return {k: v for k, v in dotenv_values(path).items() if v is not None}

    # Fallback sem python-dotenv: parser mínimo (suficiente para KEY=VALUE).
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _resolve_brs_env(analyzer_home: Path) -> tuple[dict[str, str], list[Path], dict[str, str]]:
    """Resolve as credenciais Azure OpenAI da etapa BRS/LLM.

    Precedência: ambiente já exportado > .env da raiz deste repo > .env do analyzer.
    Não altera ``os.environ`` — devolve um dict para ser aplicado no processo filho.
    Devolve também os caminhos .env consultados (para mensagens de erro).
    """
    repo_env = _REPO_ROOT / ".env"
    analyzer_env = analyzer_home / ".env"
    searched = [repo_env, analyzer_env]

    repo_values = _read_env_file(repo_env)
    analyzer_values = _read_env_file(analyzer_env)

    merged: dict[str, str] = {}
    sources: dict[str, str] = {}

    for key in _BRS_ENV_KEYS:
        ambient = os.environ.get(key)
        repo_val = repo_values.get(key)
        analyzer_val = analyzer_values.get(key)

        if ambient:
            merged[key] = ambient
            sources[key] = "process-env"
        elif repo_val:
            merged[key] = repo_val
            sources[key] = str(repo_env)
        elif analyzer_val:
            merged[key] = analyzer_val
            sources[key] = str(analyzer_env)
        else:
            sources[key] = "(missing)"

    return merged, searched, sources


def _print_brs_preflight_trace(
    analyzer_home: Path,
    brs_env: dict[str, str],
    searched: list[Path],
    sources: dict[str, str],
) -> None:
    """Emit detailed, user-facing diagnostics for BRS-LLM credential resolution."""
    print("   ── BRS-LLM Preflight Trace ─────────────────────────────────")
    print(f"   analyzer_home : {analyzer_home}")
    print("   env files     :")
    for env_path in searched:
        status = "found" if env_path.is_file() else "missing"
        print(f"      - {env_path}  [{status}]")
    print("   resolved vars :")
    for key in _BRS_ENV_KEYS:
        value = brs_env.get(key)
        source = sources.get(key, "(unknown)")
        print(f"      - {key} = {_mask_value(key, value)}  (source: {source})")
    req_file = analyzer_home / "requirements-brs-llm.txt"
    req_status = "found" if req_file.is_file() else "missing"
    print(f"   deps file     : {req_file}  [{req_status}]")


def _preflight_brs_llm(analyzer_home: Path) -> tuple[dict[str, str], dict[str, str], int]:
    """Valida credenciais e dependências antes de gastar a extração AST inteira.

    A etapa 5 do BRS é envolvida por um ``except Exception`` no analyzer, que
    achata qualquer falha (credencial ausente, dependência faltando) em um único
    aviso — e o artefato 10 resultante não passa no schema (``catalog`` é
    obrigatório). Falhar aqui evita ~13 min de extração jogados fora.
    """
    brs_env, searched, sources = _resolve_brs_env(analyzer_home)
    _print_brs_preflight_trace(analyzer_home, brs_env, searched, sources)

    if not brs_env.get("AZURE_OPENAI_API_KEY"):
        locations = "\n".join(f"       - {p}" for p in searched)
        print(
            "   ❌ --brs-llm solicitado, mas AZURE_OPENAI_API_KEY não foi encontrada.\n"
            f"      Defina-a no ambiente ou em um destes arquivos .env:\n{locations}",
            file=sys.stderr,
        )
        return brs_env, sources, 1

    if importlib.util.find_spec("langchain_openai") is None:
        print(
            "   ❌ --brs-llm solicitado, mas o pacote langchain_openai não está instalado.\n"
            f"      Python atual: {sys.executable}\n"
            f"      Instale: pip install -r {analyzer_home / 'requirements-brs-llm.txt'}",
            file=sys.stderr,
        )
        return brs_env, sources, 1

    # endpoint/model têm fallback no brs_config.yml do analyzer — apenas avisar.
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_LLM_MODEL"):
        if not brs_env.get(key):
            print(f"   ⚠️  {key} não definida; o analyzer usará o default de brs_config.yml.")

    print(
        "   brs-llm  : endpoint="
        f"{brs_env.get('AZURE_OPENAI_ENDPOINT') or '(brs_config.yml)'} "
        f"model={brs_env.get('AZURE_OPENAI_LLM_MODEL') or '(brs_config.yml)'} "
        f"api_version={brs_env.get('AZURE_OPENAI_API_VERSION') or '(default)'} "
        "api_key=***"
    )
    return brs_env, sources, 0


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
def _detect_language(repository_path: Path) -> str:
    """Score file extensions and build files to pick a language."""
    counts: collections.Counter[str] = collections.Counter()

    # Sampling cap to keep detection fast on huge repos
    max_files = 2000
    scanned = 0

    for root, _dirs, files in os.walk(repository_path):
        for name in files:
            if scanned >= max_files:
                break
            scanned += 1
            lower = name.lower()
            ext = Path(lower).suffix

            for lang, exts in LANGUAGE_EXTENSIONS.items():
                if ext in exts:
                    counts[lang] += 1

            # Build files strongly imply a language even if extension counts are low
            for lang, build_files in LANGUAGE_BUILD_FILES.items():
                if lower in build_files:
                    counts[lang] += 5

    if not counts:
        return "unknown"

    # Tie-break by deterministic alphabetical order of language id
    best = max(
        counts.keys(),
        key=lambda k: (counts[k], -ord(k[0]) if k else 0),
    )
    return best


def resolve_language(project_name: str, cli_language: str | None) -> tuple[str, bool]:
    """Return (language, is_auto_detected)."""
    config = _load_config(project_name)

    legacy = config.get("legacy_technology", "")
    repository_path_raw = config.get("repository_path", "")

    # CLI wins over everything
    if cli_language:
        return cli_language.lower(), False

    # Configured legacy technology overrides auto-detection when it is supported
    if legacy in SUPPORTED_LANGUAGES | LEGACY_STUB_LANGUAGES:
        return legacy, False

    # Legacy alias: vbnet is treated as dotnet for compatibility
    if legacy == "vbnet":
        return "dotnet", False

    # Auto-detect from source tree
    if repository_path_raw:
        repo = Path(repository_path_raw)
        if repo.exists() and repo.is_dir():
            detected = _detect_language(repo)
            if detected != "unknown":
                return detected, True

    return "unknown", True


def resolve_dotnet_language(config: dict[str, Any], repository_path: Path | None = None) -> str:
    """Map a dotnet project to the Roslyn language flag (vb, cs, both).

    Resolution order:
    1. ``legacy_technology == "vbnet"`` -> ``vb`` (backward compatibility).
    2. ``ava_ast_analyzers.dotnet_language`` config value (``vb``/``cs``/``both``).
    3. File detection in ``repository_path`` for ``.cs`` / ``.csproj`` vs ``.vb`` / ``.vbproj``.
    4. Default to ``both`` to maximize discovery on mixed repos.
    """
    legacy = config.get("legacy_technology", "")

    # Explicit legacy marker still supported for backward compatibility
    if legacy == "vbnet":
        return "vb"

    analyzers = config.get("ava_ast_analyzers", {}) or {}
    dotnet_language = analyzers.get("dotnet_language") if isinstance(analyzers, dict) else None
    if dotnet_language in ("vb", "cs", "both"):
        return dotnet_language

    if repository_path and repository_path.exists() and repository_path.is_dir():
        has_vb = _has_dotnet_files(repository_path, "vb")
        has_cs = _has_dotnet_files(repository_path, "cs")
        if has_vb and has_cs:
            return "both"
        if has_cs:
            return "cs"
        if has_vb:
            return "vb"

    return "both"


def _has_dotnet_files(repository_path: Path, dotnet_language: str) -> bool:
    """Return True if the repository contains files matching the requested language set."""
    if dotnet_language == "both":
        exts = (".cs", ".csproj", ".vb", ".vbproj")
    elif dotnet_language == "cs":
        exts = (".cs", ".csproj")
    elif dotnet_language == "vb":
        exts = (".vb", ".vbproj")
    else:
        return False
    return any(
        next(repository_path.rglob(f"*{ext}"), None) is not None
        for ext in exts
    )


# ---------------------------------------------------------------------------
# Per-analyzer dispatch
# ---------------------------------------------------------------------------
def _run_delphi_analyzer(
    analyzer_home: Path,
    repository_path: Path,
    extraction_dir: Path,
    compressed_dir: Path,
    log_path: Path,
    *,
    brs_llm: bool = False,
    brs_env: dict[str, str] | None = None,
    brs_env_sources: dict[str, str] | None = None,
) -> int:
    run_pipeline = analyzer_home / "src" / "run_pipeline.py"
    ava_ast_cli = analyzer_home / "bin" / "ava_ast_cli.exe"
    if not run_pipeline.exists():
        print(f"   ❌ run_pipeline.py não encontrado em {run_pipeline}", file=sys.stderr)
        return 1

    env = dict(os.environ)
    env["AVA_AST_CLI"] = str(ava_ast_cli)
    env["PYTHONUNBUFFERED"] = "1"
    # Credenciais vindas do .env; um valor não-vazio já exportado tem precedência
    # (setdefault não serve: uma variável definida como "" bloquearia o .env).
    for key, value in (brs_env or {}).items():
        if not env.get(key):
            env[key] = value

    cmd = [
        sys.executable,
        str(run_pipeline),
        str(repository_path),
        "--extraction",
        str(extraction_dir),
        "--compressed",
        str(compressed_dir),
    ]
    if brs_llm:
        # --brs-env-file default do analyzer é o caminho RELATIVO ".env", que não
        # resolve porque o processo roda com cwd=<analyzer_home>/src. Passar absoluto.
        cmd += ["--brs-llm", "--brs-env-file", str(analyzer_home / ".env")]

    print("   ── Delphi analyzer dispatch ─────────────────────────────────")
    print(f"   run_pipeline : {run_pipeline}")
    print(f"   working_dir  : {analyzer_home / 'src'}")
    print(f"   brs_llm      : {'ON' if brs_llm else 'OFF'}")
    if brs_llm:
        brs_env_file = analyzer_home / ".env"
        file_status = "found" if brs_env_file.is_file() else "missing"
        print(f"   brs_env_file : {brs_env_file}  [{file_status}]")
        for key in _BRS_ENV_KEYS:
            value = env.get(key)
            source = (brs_env_sources or {}).get(key, "(unknown)")
            print(f"   env[{key}]    : {_mask_value(key, value)}  (source: {source})")
    print(f"   cmd          : {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        cwd=str(analyzer_home / "src"),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    # BRS-LLM pode processar centenas de dossiês em lotes com fallback individual;
    # 1800s (30 min) é insuficiente. Usa 4h quando LLM está ativo.
    delphi_timeout = 14400 if brs_llm else 1800
    return _stream_process(proc, log_path, timeout=delphi_timeout)


def _run_dotnet_analyzer(
    analyzer_home: Path,
    repository_path: Path,
    extraction_dir: Path,
    compressed_dir: Path,
    log_path: Path,
    *,
    dotnet_language: str = "both",
    brs_llm: bool = False,
    brs_env: dict[str, str] | None = None,
    brs_env_file: Path | None = None,
) -> int:
    run_pipeline = analyzer_home / "src" / "run_pipeline.py"
    if not run_pipeline.exists():
        print(f"   ❌ run_pipeline.py não encontrado em {run_pipeline}", file=sys.stderr)
        return 1

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    for key, value in (brs_env or {}).items():
        if not env.get(key):
            env[key] = value

    cmd = [
        sys.executable,
        str(run_pipeline),
        str(repository_path),
        "--extraction",
        str(extraction_dir),
        "--compressed",
        str(compressed_dir),
        "--language",
        dotnet_language,
    ]
    if brs_llm:
        cmd += ["--brs-llm"]
        if brs_env_file is not None:
            cmd += ["--brs-env-file", str(brs_env_file)]

    print("   ── DotNet analyzer dispatch ─────────────────────────────────")
    print(f"   run_pipeline : {run_pipeline}")
    print(f"   working_dir  : {analyzer_home / 'src'}")
    print(f"   dotnet_lang  : {dotnet_language}")
    print(f"   brs_llm      : {'ON' if brs_llm else 'OFF'}")
    if brs_llm:
        if brs_env_file is not None:
            file_status = "found" if brs_env_file.is_file() else "missing"
            print(f"   brs_env_file : {brs_env_file}  [{file_status}]")
        else:
            print("   brs_env_file : (not provided)")
        for key in _BRS_ENV_KEYS:
            print(f"   env[{key}]    : {_mask_value(key, env.get(key))}")
    print(f"   cmd          : {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        cwd=str(analyzer_home / "src"),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    # BRS-LLM pode processar centenas de dossiês em lotes com fallback individual;
    # 1800s (30 min) é insuficiente. Usa 4h quando LLM está ativo.
    dotnet_timeout = 14400 if brs_llm else 1800
    return _stream_process(proc, log_path, timeout=dotnet_timeout)


def _run_java_analyzer(
    analyzer_home: Path,
    repository_path: Path,
    extraction_dir: Path,
    compressed_zip: Path,
    log_path: Path,
    *,
    brs_llm: bool = False,
    brs_env: dict[str, str] | None = None,
    brs_env_file: Path | None = None,
) -> int:
    run_pipeline = analyzer_home / "src" / "run_pipeline.py"
    if not run_pipeline.exists():
        print(f"   ❌ run_pipeline.py não encontrado em {run_pipeline}", file=sys.stderr)
        return 1

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    for key, value in (brs_env or {}).items():
        if not env.get(key):
            env[key] = value

    cmd = [
        sys.executable,
        str(run_pipeline),
        str(repository_path),
        "--extraction",
        str(extraction_dir),
        "--compressed",
        str(compressed_zip),
    ]
    if brs_llm:
        # Java analyzer defaults --brs-env-file to a relative .env. Since we run
        # with cwd=<analyzer_home>/src, pass the absolute root .env explicitly.
        cmd += ["--brs-llm"]
        if brs_env_file is not None:
            cmd += ["--brs-env-file", str(brs_env_file)]

    print("   ── Java analyzer dispatch ───────────────────────────────────")
    print(f"   run_pipeline : {run_pipeline}")
    print(f"   working_dir  : {analyzer_home / 'src'}")
    print(f"   brs_llm      : {'ON' if brs_llm else 'OFF'}")
    if brs_llm:
        if brs_env_file is not None:
            file_status = "found" if brs_env_file.is_file() else "missing"
            print(f"   brs_env_file : {brs_env_file}  [{file_status}]")
        else:
            print("   brs_env_file : (not provided)")
        for key in _BRS_ENV_KEYS:
            print(f"   env[{key}]    : {_mask_value(key, env.get(key))}")
    print(f"   cmd          : {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        cwd=str(analyzer_home / "src"),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    # BRS-LLM pode processar centenas de dossiês em lotes com fallback individual;
    # 1800s (30 min) é insuficiente. Usa 4h quando LLM está ativo.
    java_timeout = 14400 if brs_llm else 1800
    return _stream_process(proc, log_path, timeout=java_timeout)


def _stream_process(
    proc: subprocess.Popen[str], log_path: Path, timeout: int
) -> int:
    _timed_out = False

    def _kill_on_timeout() -> None:
        nonlocal _timed_out
        _timed_out = True
        print(
            f"\n   ⏱️  TIMEOUT: processo excedeu {timeout}s e foi encerrado."
            " Use --brs-llm em uma execução dedicada com timeout maior.",
            flush=True,
        )
        proc.kill()

    timer = threading.Timer(timeout, _kill_on_timeout)
    timer.start()
    output_lines: list[str] = []
    try:
        for line in proc.stdout or []:
            print(f"   | {line}", end="", flush=True)
            output_lines.append(line)
        proc.wait()
    finally:
        timer.cancel()

    log_path.parent.mkdir(parents=True, exist_ok=True)
    if _timed_out:
        output_lines.append(f"\n[TIMEOUT] Processo encerrado após {timeout}s pelo runner.\n")
    log_path.write_text("".join(output_lines), encoding="utf-8")
    return proc.returncode


def _validate_output(language: str, extraction_dir: Path, compressed_dir: Path) -> list[str]:
    missing: list[str] = []
    optional = _OPTIONAL_EXTRACTION_FILES.get(language, set())
    for name in _EXPECTED_EXTRACTION_FILES:
        if name in optional and not (extraction_dir / name).exists():
            continue
        if not (extraction_dir / name).exists():
            missing.append(f"extraction/{name}")
    for name in _EXPECTED_COMPRESSED_FILES:
        if not (compressed_dir / name).exists():
            missing.append(f"compressed/{name}")
    return missing


def _check_brs_business_rule_cases(path: Path) -> tuple[bool, str]:
    """Validate BRS-enriched business_rule_cases artifact with detailed diagnostics."""
    if not path.exists():
        return False, f"{path.name}: arquivo ausente"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"{path.name}: JSON inválido ({type(exc).__name__}: {exc})"

    payload = _payload_any(raw)
    if not isinstance(payload, dict):
        return False, f"{path.name}: payload ausente ou inválido"

    catalog = payload.get("catalog")
    if not isinstance(catalog, dict):
        return False, f"{path.name}: payload.catalog ausente ou inválido (esperado para --brs-llm)"

    rules = catalog.get("rules")
    if not isinstance(rules, list):
        return False, f"{path.name}: payload.catalog.rules[] ausente (esperado para --brs-llm)"

    return True, f"{path.name}: catalog.rules ok ({len(rules)} itens)"


def _report_brs_post_run(extraction_dir: Path, compressed_dir: Path) -> None:
    """Emit explicit BRS post-run health for faster troubleshooting."""
    print("   ── BRS-LLM Post-Run Check ───────────────────────────────────")
    targets = [
        extraction_dir / "10_business_rule_cases.json",
        compressed_dir / "10_business_rule_cases.json",
    ]
    ok_any = False
    for target in targets:
        ok, detail = _check_brs_business_rule_cases(target)
        icon = "✅" if ok else "⚠️"
        print(f"   {icon} {detail}")
        ok_any = ok_any or ok
    if not ok_any:
        print(
            "   ❌ Nenhum artefato business_rule_cases válido encontrado para a etapa BRS/LLM. "
            "Verifique credenciais, dependências e logs do analyzer."
        )


def _write_language_meta(
    language: str,
    analyzer_home: Path,
    repository_path: Path,
    detected: bool,
    meta_path: Path,
) -> None:
    meta = {
        "language": language,
        "auto_detected": detected,
        "analyzer_home": str(analyzer_home),
        "repository_path": str(repository_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _mirror_to_legacy_delphi_path(out_base: Path, legacy_base: Path) -> None:
    """Copy ast-raw/delphi contents into legacy delphi-ast-raw for compatibility."""
    if legacy_base.exists():
        shutil.rmtree(legacy_base)
    shutil.copytree(out_base, legacy_base)


def _unzip_java_compressed(compressed_zip: Path, compressed_dir: Path, extraction_dir: Path) -> None:
    """Java analyzer emits a zip; expand it into the compressed folder and duplicate
    JSONs into extraction so downstream consumers have a consistent view."""
    compressed_dir.mkdir(parents=True, exist_ok=True)
    extraction_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(compressed_zip, "r") as zf:
        zf.extractall(compressed_dir)

    # Duplicate JSONs into extraction/ for downstream readers
    for json_file in sorted(compressed_dir.rglob("*.json")):
        rel = json_file.relative_to(compressed_dir)
        dst = extraction_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(json_file, dst)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run_ast_analysis(
    project_name: str,
    cli_language: str | None = None,
    *,
    mirror_legacy_delphi: bool = False,
    brs_llm: bool = False,
) -> int:
    language, detected = resolve_language(project_name, cli_language)
    print(f"\n🔧 run_ast_analysis :: {project_name}")
    print(f"   language : {language} ({'auto-detected' if detected else 'from config/cli'})")

    if language == "unknown":
        print("   ⚠️  Não foi possível detectar linguagem. Configure legacy_technology ou forneça --language.",
              file=sys.stderr)
        return 1

    if language in LEGACY_STUB_LANGUAGES:
        print(f"   ⏭️  legacy_technology='{language}' não possui analyzer AST implementado — pulando Step 0.")
        return 0

    if language not in SUPPORTED_LANGUAGES:
        print(f"   ❌ Linguagem não suportada: {language}", file=sys.stderr)
        return 1

    config = _load_config(project_name)
    repository_path_raw = config.get("repository_path")
    if not repository_path_raw:
        print(f"   ❌ repository_path não encontrado em project-config.yaml", file=sys.stderr)
        return 1

    repository_path = Path(repository_path_raw).resolve()
    if not repository_path.exists():
        print(f"   ❌ repository_path não existe: {repository_path}", file=sys.stderr)
        return 1

    analyzer_home = _get_analyzer_home(config, language)
    if analyzer_home is None:
        print(f"   ❌ Caminho do analyzer {language} não configurado. "
              f"Use ava_ast_analyzers.{language} ou {_ENV_VAR_MAP[language]}.", file=sys.stderr)
        return 1
    if not analyzer_home.exists():
        print(f"   ❌ analyzer_home não existe: {analyzer_home}", file=sys.stderr)
        return 1

    print(f"   analyzer : {analyzer_home}")
    print(f"   source   : {repository_path}")

    if brs_llm:
        print("   brs_llm  : ON (etapas 5-8 de interpretação por LLM habilitadas)")
    elif language == "delphi":
        print("   brs_llm  : OFF (pipeline BRS/LLM desabilitado para esta execução)")

    # Valida credenciais/dependências do BRS ANTES da extração (que leva minutos).
    brs_env: dict[str, str] = {}
    brs_env_sources: dict[str, str] = {}
    if brs_llm and language == "delphi":
        brs_env, brs_env_sources, rc_preflight = _preflight_brs_llm(analyzer_home)
        if rc_preflight != 0:
            return rc_preflight

    out_base = Path(f"projects/{project_name}/outputs/asis/ast-raw/{language}").resolve()
    extraction_dir = out_base / "extraction"
    compressed_dir = out_base / "compressed"
    log_path = out_base / f"run_ast_analysis.{language}.log"
    out_base.mkdir(parents=True, exist_ok=True)

    java_brs_env: dict[str, str] = {}
    java_brs_env_file: Path | None = None
    dotnet_brs_env: dict[str, str] = {}
    dotnet_brs_env_file: Path | None = None
    if brs_llm and language == "java":
        java_brs_env, searched, _sources = _resolve_brs_env(analyzer_home)
        for env_path in searched:
            if env_path.is_file():
                java_brs_env_file = env_path
                break
    if brs_llm and language == "dotnet":
        dotnet_brs_env, searched, _sources = _resolve_brs_env(analyzer_home)
        for env_path in searched:
            if env_path.is_file():
                dotnet_brs_env_file = env_path
                break

    if language == "delphi":
        rc = _run_delphi_analyzer(
            analyzer_home,
            repository_path,
            extraction_dir,
            compressed_dir,
            log_path,
            brs_llm=brs_llm,
            brs_env=brs_env,
            brs_env_sources=brs_env_sources,
        )
    elif language == "dotnet":
        dotnet_language = resolve_dotnet_language(config, repository_path)
        print(f"   dotnet_language : {dotnet_language}")
        rc = _run_dotnet_analyzer(
            analyzer_home, repository_path, extraction_dir, compressed_dir, log_path,
            dotnet_language=dotnet_language,
            brs_llm=brs_llm,
            brs_env=dotnet_brs_env,
            brs_env_file=dotnet_brs_env_file,
        )
    elif language == "java":
        compressed_zip = out_base / "compressed.zip"
        rc = _run_java_analyzer(
            analyzer_home,
            repository_path,
            extraction_dir,
            compressed_zip,
            log_path,
            brs_llm=brs_llm,
            brs_env=java_brs_env,
            brs_env_file=java_brs_env_file,
        )
        if rc == 0:
            _unzip_java_compressed(compressed_zip, compressed_dir, extraction_dir)
    else:
        return 1  # unreachable

    if rc != 0:
        print(f"   ❌ Analyzer {language} falhou (exit {rc}). Ver {log_path}", file=sys.stderr)
        return rc

    # Normalize analyzer output to a stable lowercase envelope + payload shape
    print("   ⏳ Normalizing AST artifacts...")
    _normalize_ast_artifacts(extraction_dir, compressed_dir)
    _ensure_manifest_metrics(compressed_dir, extraction_dir)

    if brs_llm and language == "delphi":
        _report_brs_post_run(extraction_dir, compressed_dir)

    # Language tag for auditability
    _write_language_meta(language, analyzer_home, repository_path, detected, out_base / "meta" / "language.json")

    # Shared post-processors: module partitioner + SQL IR generator
    print("   ⏳ Running module partitioner...")
    from module_partitioner import ModulePartitioner

    partitioner = ModulePartitioner(
        project_name,
        language=language,
        output_dir=compressed_dir,
        source_dir=repository_path,
    )
    try:
        partitioner_rc = partitioner.run()
        if partitioner_rc != 0:
            print(f"   ⚠️  ModulePartitioner retornou {partitioner_rc} — prosseguindo.")
    except Exception as exc:
        print(f"   ⚠️  ModulePartitioner falhou: {exc} — prosseguindo.")

    print("   ⏳ Running SQL IR generator...")
    from sql_ir_generator import SqlIrGenerator

    gen = SqlIrGenerator(
        project_name,
        language=language,
        ast_dir=extraction_dir,
        output_dir=compressed_dir,
    )
    try:
        gen.run()
    except Exception as exc:
        print(f"   ⚠️  SqlIrGenerator falhou: {exc} — prosseguindo.")

    # Validate
    missing = _validate_output(language, extraction_dir, compressed_dir)
    if missing:
        print(f"   ❌ Artefatos ausentes após a extração: {missing}", file=sys.stderr)
        return 1

    # Legacy mirror only for Delphi
    if language == "delphi" and mirror_legacy_delphi:
        legacy_base = Path(f"projects/{project_name}/outputs/asis/delphi-ast-raw").resolve()
        print(f"   ⏳ Mirror legacy path: {legacy_base}")
        _mirror_to_legacy_delphi_path(out_base, legacy_base)

    # Summary
    overview_path = extraction_dir / "08_code_overview.json"
    if overview_path.exists():
        overview = json.loads(overview_path.read_text(encoding="utf-8"))
        payload = _payload_any(overview)
        totals = payload.get("totals", {}) if isinstance(payload, dict) else {}
        print(f"   ✅ modo: {totals.get('mode')}  |  unidades: {totals.get('units_total')}  |  "
              f"classes: {totals.get('classes')}  |  regras: {totals.get('business_rules')}  |  "
              f"sql functions: {totals.get('sql_functions', 0)}")

    print(f"   ✅ output: {out_base}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Roteia extração AST determinística para Delphi, .NET ou Java"
    )
    ap.add_argument("--project", required=True, help="Nome do projeto (ex: Meu-ERP)")
    ap.add_argument(
        "--language",
        choices=sorted(SUPPORTED_LANGUAGES | LEGACY_STUB_LANGUAGES | {"unknown"}),
        default=None,
        help="Força linguagem (senão detecta por legacy_technology ou extensões)",
    )
    ap.add_argument(
        "--mirror-legacy-delphi",
        action="store_true",
        help="Copia ast-raw/delphi para delphi-ast-raw (compatibilidade)",
    )
    ap.add_argument(
        "--brs-llm",
        action="store_true",
        help="Ao executar Delphi, repassa --brs-llm para o analyzer run_pipeline.py",
    )
    a = ap.parse_args()

    return run_ast_analysis(
        project_name=a.project,
        cli_language=a.language,
        mirror_legacy_delphi=a.mirror_legacy_delphi,
        brs_llm=a.brs_llm,
    )


if __name__ == "__main__":
    sys.exit(main())
