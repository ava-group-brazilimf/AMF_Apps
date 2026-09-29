#!/usr/bin/env python3
"""
f4s_feature_discovery.py — Descobre specs/features F4S por stack.

Fontes de verdade, em ordem de prioridade:
  1. `outputs/tobe/speckit/traceability.json` (grupos de tasks por `target_stack`).
  2. `outputs/tobe/speckit/specifications/` (arquivos `*.md` com metadados YAML).
  3. Defaults seguros: scaffold + bounded contexts do AS-IS.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCAFFOLD_SPEC_ID = "000-scaffold"


def _extract_yaml_frontmatter(text: str) -> dict[str, Any]:
    """Extrai YAML frontmatter de um arquivo markdown, se existir."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    # Parser YAML mínimo: chave: valor linhas simples.
    meta: dict[str, Any] = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line and not line.strip().startswith("#"):
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def _read_traceability(traceability_path: Path) -> dict[str, Any]:
    """Lê traceability.json v1 (lista) ou v2 (objeto) e normaliza."""
    if not traceability_path.exists():
        return {"version": None, "entries": [], "execution_order": []}
    try:
        data = json.loads(traceability_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": None, "entries": [], "execution_order": []}

    if isinstance(data, list):
        return {"version": "1", "entries": data, "execution_order": []}

    if isinstance(data, dict) and data.get("schema_version") == "2.0.0":
        return {
            "version": "2",
            "entries": data.get("entries") or [],
            "execution_order": data.get("execution_order") or [],
            "execution_waves": data.get("execution_waves") or [],
            "graph_checksum": data.get("graph_checksum", ""),
        }

    return {"version": None, "entries": [], "execution_order": []}


def _read_specifications(spec_dir: Path) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    if not spec_dir.exists():
        return specs
    for md in sorted(spec_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        meta = _extract_yaml_frontmatter(text)
        if "id" in meta:
            specs[meta["id"]] = {"file": md, **meta}
    return specs


def _to_feature_id(raw: str) -> str:
    """Normaliza um nome de feature para id de spec."""
    raw = raw.lower().strip()
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    raw = re.sub(r"^-+|-+$", "", raw)
    return raw


def discover_features(
    stack: str,
    tobe_outputs: Path,
    project_config_path: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Retorna lista ordenada de specs para a stack.

    O primeiro item é sempre o scaffold. Os demais derivam, em ordem de
    prioridade, de:
      1. Diretórios `outputs/tobe/speckit/specs/*/` com `spec.md`.
      2. Grupos no `traceability.json` cujo `target_stack` case-insensitive
         bata com `stack`.
      3. Bounded contexts listados em `project-config.yaml`.

    Cada feature inclui `spec_path`, `plan_path` e `tasks_path` quando
    disponíveis.
    """
    traceability_path = tobe_outputs / "speckit" / "traceability.json"
    spec_dir = tobe_outputs / "speckit" / "specifications"
    specs_root = tobe_outputs / "speckit" / "specs"

    trace_info = _read_traceability(traceability_path)
    trace_entries = trace_info["entries"]
    execution_order = trace_info.get("execution_order") or []
    spec_meta = _read_specifications(spec_dir)

    def _paths(fid: str) -> dict[str, Any]:
        d = specs_root / fid
        paths: dict[str, Any] = {"spec_path": None, "plan_path": None, "tasks_path": None}
        candidates = {
            "spec_path": d / "spec.md",
            "plan_path": d / "plan.md",
            "tasks_path": d / "tasks.md",
        }
        for key, path in candidates.items():
            if path.exists():
                paths[key] = str(path.as_posix())
        return paths

    # Sempre incluir o scaffold primeiro.
    features: dict[str, dict[str, Any]] = {
        SCAFFOLD_SPEC_ID: {
            "id": SCAFFOLD_SPEC_ID,
            "name": "Scaffold",
            "description": "Estrutura base da solução por stack",
            "source": "internal",
            **_paths(SCAFFOLD_SPEC_ID),
        }
    }

    # 1. Diretórios de spec já existentes.
    if specs_root.exists():
        for d in sorted(specs_root.iterdir()):
            if not d.is_dir() or d.name == SCAFFOLD_SPEC_ID:
                continue
            fid = _to_feature_id(d.name)
            if fid not in features:
                features[fid] = {
                    "id": fid,
                    "name": d.name.replace("-", " ").title(),
                    "description": "",
                    "source": "speckit-specs-dir",
                    **_paths(d.name),
                }

    # 2. Grupos/features únicos por target_stack no traceability.json.
    # v2: usa execution_order para estabelecer a ordem determinística.
    for entry in trace_entries:
        if not isinstance(entry, dict):
            continue
        target = str(entry.get("target_stack", "")).lower()
        if target != stack.lower():
            continue
        feature_key = str(entry.get("feature") or entry.get("group", "")).strip()
        if not feature_key:
            continue
        fid = _to_feature_id(feature_key)
        if fid not in features:
            features[fid] = {
                "id": fid,
                "name": feature_key,
                "description": entry.get("description", ""),
                "trace_entries": [],
                **_paths(fid),
            }
            if fid in spec_meta:
                features[fid]["spec_file"] = str(spec_meta[fid]["file"].as_posix())
                features[fid]["name"] = spec_meta[fid].get("name", features[fid]["name"])
        features[fid].setdefault("trace_entries", []).append(entry)
        features[fid]["source"] = "traceability"

    # Ordem determinística quando traceability v2 trouxer execution_order.
    rank: dict[str, int] = {}
    if execution_order:
        for entry in trace_entries:
            feature_key = str(entry.get("feature") or entry.get("group", "")).strip()
            fid = _to_feature_id(feature_key)
            task_id = str(entry.get("task_id", ""))
            if fid in features and task_id and task_id in execution_order:
                pos = execution_order.index(task_id)
                rank[fid] = min(rank.get(fid, pos), pos)

    ordered_ids = sorted(
        (fid for fid in features if fid != SCAFFOLD_SPEC_ID),
        key=lambda f: (rank.get(f, 9999), f),
    )
    return [features[SCAFFOLD_SPEC_ID]] + [features[fid] for fid in ordered_ids]
