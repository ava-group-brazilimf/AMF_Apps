#!/usr/bin/env python3
"""
AVA Fabric – SQL Intermediate Representation (IR) Generator
=============================================================
Normaliza os artefatos AST de banco de dados (03_database_rules.json,
04_database_schemas.json, 05_procedures.json) em um único ``sql-ir.json``
que pode ser consumido por agentes downstream para gerar MER/ERD e designs
de banco TO-BE.

Respeita o ``scope-filter-manifest.json`` gerado pelo ModulePartitioner
(Step 0.5) para que o IR reflita apenas os módulos em escopo quando
``scope_modules != "all"``.

Uso standalone
--------------
    python sql_ir_generator.py --project Meu-ERP
    python sql_ir_generator.py --project Meu-ERP --language dotnet

Uso integrado (run_ast_analysis.py)
-----------------------------------
    from sql_ir_generator import SqlIrGenerator
    gen = SqlIrGenerator(project_name, language="delphi")
    gen.run()

Dependências
------------
    pip install pyyaml
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Decodificação de artefatos pré-comprimidos pelo Headroom (specs/031).
# `headroom_context` é o ÚNICO lugar do repo que conhece esse formato.
# Import defensivo: sem a tool, o gerador continua lendo `extraction/` normalmente.
_HEADROOM_TOOL_DIR = (
    Path(__file__).resolve().parents[4] / "shared" / "tools" / "headroom"
)
if _HEADROOM_TOOL_DIR.is_dir() and str(_HEADROOM_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_HEADROOM_TOOL_DIR))
try:
    from headroom_context import decode_headroom
except ImportError:  # pragma: no cover - tool ausente degrada, não quebra
    def decode_headroom(node):
        """No-op quando src/shared/tools/headroom/ não está disponível."""
        return node

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------
_RE_FK_CONVENTION = re.compile(r"^id_(\w+)$", re.IGNORECASE)
_RE_ID_PK = re.compile(r"^id$", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Type normalisation map (Delphi / SQL → IR)
# ---------------------------------------------------------------------------
_TYPE_MAP: dict[str, str] = {
    "integer": "integer",
    "int": "integer",
    "bigint": "integer",
    "smallint": "integer",
    "tinyint": "integer",
    "varchar": "string",
    "nvarchar": "string",
    "char": "string",
    "nchar": "string",
    "string": "string",
    "text": "text",
    "memo": "text",
    "blob": "text",
    "date": "datetime",
    "datetime": "datetime",
    "timestamp": "datetime",
    "time": "datetime",
    "numeric": "decimal",
    "decimal": "decimal",
    "money": "decimal",
    "currency": "decimal",
    "float": "float",
    "real": "float",
    "double": "float",
    "boolean": "boolean",
    "bit": "boolean",
    "bool": "boolean",
}


def _normalize_type(raw: str | None) -> str:
    if not raw:
        return "unknown"
    lowered = raw.lower().strip()
    # strip size qualifiers e.g. VARCHAR(255)
    base = re.split(r"[\s(]", lowered)[0]
    return _TYPE_MAP.get(base, "unknown")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"   ⚠️  falha ao ler {path}: {exc}", file=sys.stderr)
        return None


def _load_scope_manifest(project_name: str, language: str = "delphi") -> dict[str, Any] | None:
    path = Path(f"projects/{project_name}/outputs/asis/ast-raw/{language}/compressed/scope-filter-manifest.json")
    data = _load_json(path)
    if data is None:
        return None
    # Normaliza included_units para lower-case set para matching rápido
    raw = data.get("included_units", [])
    data["_included_set"] = {u.lower() for u in raw}
    return data


def _unit_from_source_ref(source_ref: dict[str, Any] | None) -> str | None:
    if not source_ref:
        return None
    file_name = source_ref.get("file", "")
    # normaliza para nome do arquivo
    return Path(file_name).name if file_name else None


def _is_in_scope(unit_name: str | None, manifest: dict[str, Any] | None) -> bool:
    if manifest is None:
        return True
    if manifest.get("scope_modules") == "all":
        return True
    if unit_name is None:
        return False
    return unit_name.lower() in manifest.get("_included_set", set())


def _table_unit_candidates(table: dict[str, Any]) -> list[str]:
    """Retorna todos os arquivos de unidade candidatos para filtro de escopo."""
    candidates: list[str] = []
    primary = _unit_from_source_ref(table.get("source_ref")) or table.get("unit", "")
    if primary:
        candidates.append(primary)
    for used in table.get("used_in", []):
        if isinstance(used, str) and used:
            candidates.append(used)
        elif isinstance(used, dict):
            file_name = used.get("file", "")
            if file_name:
                candidates.append(Path(file_name).name)
    return candidates


# ---------------------------------------------------------------------------
# IR Builder
# ---------------------------------------------------------------------------

class SqlIrBuilder:
    def __init__(self, project_name: str, language: str = "delphi") -> None:
        self.project_name = project_name
        self.language = language
        self.manifest = _load_scope_manifest(project_name, language)
        self.config = self._load_config()

        # containers
        self.entities: dict[str, dict[str, Any]] = {}
        self.relationships: dict[str, dict[str, Any]] = {}
        self.procedures: dict[str, dict[str, Any]] = {}
        self._entity_counter = 0
        self._rel_counter = 0
        self._proc_counter = 0

        # reverse lookup: unit name -> module(s)
        self._unit_to_modules: dict[str, list[str]] = defaultdict(list)
        if self.manifest and self.manifest.get("module_partition"):
            for mod, units in self.manifest["module_partition"].items():
                for u in units:
                    self._unit_to_modules[u.lower()].append(mod)

    def _load_config(self) -> dict[str, Any]:
        path = Path(f"projects/{self.project_name}/context/project-config.yaml")
        if path.exists():
            try:
                return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception:
                pass
        return {}

    def _next_entity_id(self) -> str:
        self._entity_counter += 1
        return f"ent-{self._entity_counter:04d}"

    def _next_rel_id(self) -> str:
        self._rel_counter += 1
        return f"rel-{self._rel_counter:04d}"

    def _next_proc_id(self) -> str:
        self._proc_counter += 1
        return f"proc-{self._proc_counter:04d}"

    # ------------------------------------------------------------------
    # Step 1 — Entities from 04_database_schemas.json
    # ------------------------------------------------------------------

    def ingest_database_schemas(self, data: dict[str, Any] | None) -> None:
        if data is None:
            return
        payload = data.get("payload", {})

        # 1.1 DDL-derived tables
        for table in payload.get("tables", []):
            self._ingest_table(table, origin="ddl")

        # 1.2 Inferred tables (from SQL inline)
        for table in payload.get("inferred_tables", []):
            self._ingest_table(table, origin="inferred_from_sql")

        # 1.3 Dataset fields enrichment
        self._enrich_from_dataset_fields(payload.get("dataset_fields", []))

    def _ingest_table(self, table: dict[str, Any], origin: str) -> None:
        name = table.get("name", "")
        if not name:
            return
        candidates = _table_unit_candidates(table)

        # scope filter: mantém a entidade se pelo menos uma das fontes
        # (source_ref/unit ou used_in) estiver no escopo. Isso evita que
        # tabelas referenciadas por código do módulo em escopo sejam perdidas
        # apenas porque a inferência primária aponta para outro arquivo.
        in_scope_files = [u for u in candidates if _is_in_scope(u, self.manifest)]
        if candidates and not in_scope_files:
            return
        unit_file = in_scope_files[0] if in_scope_files else (candidates[0] if candidates else "")

        ent_id = self._entity_id_for_name(name)
        if ent_id not in self.entities:
            self.entities[ent_id] = self._make_entity_skeleton(ent_id, name, origin)

        ent = self.entities[ent_id]
        ent["sources"].append({
            "file": unit_file or "",
            "line": table.get("source_ref", {}).get("line", 0),
            "ref_type": "table_definition" if origin == "ddl" else "sql_inline",
        })
        ent["module_owners"] = sorted(set(ent["module_owners"] + self._modules_for(unit_file)))

        # attributes from inferred_tables
        for col in table.get("accessed_columns", []):
            self._ensure_attribute(ent, col, "inferred")

        # operations
        for op in table.get("operations", []):
            if op not in ent["operations"]:
                ent["operations"].append(op)

    def _enrich_from_dataset_fields(self, dataset_fields: list[dict[str, Any]]) -> None:
        for ds in dataset_fields:
            dataset_name = ds.get("dataset", "")
            unit = ds.get("unit", "")
            unit_file = _unit_from_source_ref(ds.get("source_ref")) or unit
            if unit_file and not _is_in_scope(unit_file, self.manifest):
                continue

            # tenta mapear dataset -> entidade existente (heurística por nome)
            ent_id = self._entity_id_for_name(dataset_name)
            if ent_id not in self.entities:
                # cria entidade implícita se ainda não existir
                self.entities[ent_id] = self._make_entity_skeleton(ent_id, dataset_name, "dataset")

            ent = self.entities[ent_id]
            for field in ds.get("fields", []):
                attr_name = field.get("name", "")
                if not attr_name:
                    continue
                attr_type = _normalize_type(field.get("delphi_type"))
                self._ensure_attribute(ent, attr_name, attr_type, override_type=True)
            ent["module_owners"] = sorted(set(ent["module_owners"] + self._modules_for(unit_file)))

    def _make_entity_skeleton(self, ent_id: str, name: str, origin: str) -> dict[str, Any]:
        return {
            "id": ent_id,
            "name": name,
            "display_name": self._snake_to_title(name),
            "origin": origin,
            "sources": [],
            "module_owners": [],
            "attributes": [],
            "operations": [],
            "risk_level": "MEDIUM",
        }

    def _ensure_attribute(
        self,
        entity: dict[str, Any],
        attr_name: str,
        attr_type: str,
        *,
        override_type: bool = False,
    ) -> None:
        attrs = entity["attributes"]
        existing = next((a for a in attrs if a["name"] == attr_name), None)
        if existing is None:
            attrs.append({
                "name": attr_name,
                "type": attr_type if override_type else _normalize_type(None),
                "nullable": True,
                "is_pk": bool(_RE_ID_PK.match(attr_name)),
                "is_fk": bool(_RE_FK_CONVENTION.match(attr_name)),
                "source": "dataset" if override_type else "inferred",
            })
        elif override_type and existing["type"] == "unknown":
            existing["type"] = attr_type

    def _entity_id_for_name(self, name: str) -> str:
        # lookup por nome normalizado para evitar duplicatas
        key = name.lower().strip()
        for ent_id, ent in self.entities.items():
            if ent["name"].lower().strip() == key:
                return ent_id
        return self._next_entity_id()

    def _modules_for(self, unit_file: str | None) -> list[str]:
        if not unit_file:
            return []
        return self._unit_to_modules.get(unit_file.lower(), [])

    @staticmethod
    def _snake_to_title(name: str) -> str:
        return " ".join(word.capitalize() for word in name.split("_"))

    # ------------------------------------------------------------------
    # Step 2 — Operations from 03_database_rules.json
    # ------------------------------------------------------------------

    def ingest_database_rules(self, data: dict[str, Any] | None) -> None:
        if data is None:
            return
        for rule in data.get("payload", {}).get("rules", []):
            if rule.get("type") != "write_operation":
                continue
            unit_file = _unit_from_source_ref(rule.get("source_ref"))
            if unit_file and not _is_in_scope(unit_file, self.manifest):
                continue

            tables = rule.get("tables", [])
            operation = rule.get("operation", "")
            for tbl in tables:
                ent_id = self._entity_id_for_name(tbl)
                if ent_id not in self.entities:
                    self.entities[ent_id] = self._make_entity_skeleton(ent_id, tbl, "inferred_from_sql")
                ent = self.entities[ent_id]
                if operation and operation not in ent["operations"]:
                    ent["operations"].append(operation)
                # rastreabilidade
                ent["sources"].append({
                    "file": unit_file or "",
                    "line": rule.get("source_ref", {}).get("line", 0),
                    "ref_type": f"write_operation:{operation}",
                })
                ent["module_owners"] = sorted(set(ent["module_owners"] + self._modules_for(unit_file)))

    # ------------------------------------------------------------------
    # Step 3 — Procedures from 05_procedures.json
    # ------------------------------------------------------------------

    def ingest_procedures(self, data: dict[str, Any] | None) -> None:
        if data is None:
            return
        payload = data.get("payload", {})

        # 3.1 stored procedures (DB-side)
        for sp in payload.get("stored_procedures", []):
            self._ingest_procedure(sp, kind="stored_procedure")

        # 3.2 code procedures (Delphi-side)
        for cp in payload.get("code_procedures", []):
            unit_file = _unit_from_source_ref(cp.get("source_ref"))
            if unit_file and not _is_in_scope(unit_file, self.manifest):
                continue
            self._ingest_procedure(cp, kind="code_procedure")

    def _ingest_procedure(self, proc: dict[str, Any], kind: str) -> None:
        name = proc.get("name", "")
        if not name:
            return
        unit_file = _unit_from_source_ref(proc.get("source_ref")) or proc.get("unit", "")
        proc_id = self._next_proc_id()
        self.procedures[proc_id] = {
            "id": proc_id,
            "name": name,
            "kind": kind,
            "language": "sql" if kind == "stored_procedure" else "delphi",
            "source_unit": unit_file,
            "source_ref": proc.get("source_ref", {}),
            "module_owners": self._modules_for(unit_file),
            "operations": [],  # será inferido se possível
            "affected_entities": [],
            "loc": proc.get("loc", 0),
            "complexity": self._complexity_from_loc(proc.get("loc", 0)),
        }

    def _complexity_from_loc(self, loc: int) -> str:
        if loc == 0:
            return "unknown"
        if loc <= 20:
            return "low"
        if loc <= 60:
            return "medium"
        return "high"

    # ------------------------------------------------------------------
    # Step 4 — Relationship inference
    # ------------------------------------------------------------------

    def infer_relationships(self) -> None:
        for ent_id, ent in self.entities.items():
            for attr in ent["attributes"]:
                if not attr.get("is_fk"):
                    continue
                m = _RE_FK_CONVENTION.match(attr["name"])
                if not m:
                    continue
                target_name = m.group(1)
                # procura entidade alvo
                target_id = None
                for tid, tent in self.entities.items():
                    if tent["name"].lower().strip() == target_name.lower().strip():
                        target_id = tid
                        break
                if target_id is None:
                    continue  # entidade alvo não está no escopo

                rel_key = (ent_id, target_id, attr["name"])
                if rel_key in self.relationships:
                    continue
                rel_id = self._next_rel_id()
                self.relationships[rel_key] = {
                    "id": rel_id,
                    "source_entity": ent_id,
                    "target_entity": target_id,
                    "cardinality": "many-to-one",
                    "type": "foreign_key_convention",
                    "source_columns": [attr["name"]],
                    "target_columns": ["id"],
                    "confidence": "medium",
                }

    # ------------------------------------------------------------------
    # Build final IR
    # ------------------------------------------------------------------

    def build(self) -> dict[str, Any]:
        # garante PK em toda entidade que não tenha uma
        for ent in self.entities.values():
            has_pk = any(a.get("is_pk") for a in ent["attributes"])
            if not has_pk:
                ent["attributes"].insert(0, {
                    "name": "id",
                    "type": "integer",
                    "nullable": False,
                    "is_pk": True,
                    "is_fk": False,
                    "source": "synthetic",
                })

        # módulos aggregados
        modules: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"entities": [], "relationships": [], "procedures": []})
        for ent_id, ent in self.entities.items():
            for mod in ent.get("module_owners", []):
                modules[mod]["entities"].append(ent_id)
        for rel in self.relationships.values():
            # atribui relação aos módulos da entidade source
            src_ent = self.entities.get(rel["source_entity"], {})
            for mod in src_ent.get("module_owners", []):
                if rel["id"] not in modules[mod]["relationships"]:
                    modules[mod]["relationships"].append(rel["id"])
        for pid, proc in self.procedures.items():
            for mod in proc.get("module_owners", []):
                modules[mod]["procedures"].append(pid)

        scope_info: dict[str, Any] = {"mode": "full", "modules": [], "included_units": []}
        if self.manifest:
            scope_info = {
                "mode": "partial" if self.manifest.get("scope_modules") != "all" else "full",
                "modules": self.manifest.get("scope_modules", []),
                "included_units": self.manifest.get("included_units", []),
            }

        stats = {
            "entities_total": len(self.entities),
            "entities_in_scope": len(self.entities),  # já filtramos na ingestão
            "relationships_in_scope": len(self.relationships),
            "procedures_in_scope": len(self.procedures),
            "attributes_total": sum(len(e["attributes"]) for e in self.entities.values()),
        }

        return {
            "schema_version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": f"{self.language}-ast-extraction",
            "project_name": self.project_name,
            "scope": scope_info,
            "statistics": stats,
            "entities": list(self.entities.values()),
            "relationships": list(self.relationships.values()),
            "procedures": list(self.procedures.values()),
            "modules": {k: v for k, v in modules.items()},
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

class SqlIrGenerator:
    def __init__(
        self,
        project_name: str,
        *,
        language: str = "delphi",
        output_dir: Path | None = None,
        ast_dir: Path | None = None,
    ) -> None:
        self.project_name = project_name
        self.language = language
        # `extraction/` (JSON cru) continua sendo a fonte PREFERIDA: este gerador
        # é determinístico e precisa de 100% das entidades. O motor de fallback da
        # pré-compressão amostra linhas (`sampled: true`), então ler `compressed/`
        # por padrão poderia perder entidades em silêncio.
        #
        # Antes de specs/031, `compressed/` era simplesmente inutilizável — o
        # SmartCrusher reescreve arrays como string tabular e `table.get(...)`
        # estourava AttributeError sobre uma str. Agora `_load_ast()` decodifica
        # via headroom_context e usa `compressed/` como FALLBACK, para o caso de
        # `extraction/` ter sido descartado (antes disso o gerador produzia um
        # sql-ir.json vazio, sem avisar).
        #
        # sql-ir.json continua sendo escrito em `compressed/` (output_dir padrão),
        # que é onde os agentes downstream procuram.
        self.ast_dir = ast_dir or Path(
            f"projects/{project_name}/outputs/asis/ast-raw/{language}/extraction"
        )
        self.output_dir = output_dir or Path(
            f"projects/{project_name}/outputs/asis/ast-raw/{language}/compressed"
        )
        self.compressed_dir = Path(
            f"projects/{project_name}/outputs/asis/ast-raw/{language}/compressed"
        )
        self.manifest = _load_scope_manifest(project_name, language)

    def _load_ast(self, filename: str) -> dict[str, Any] | None:
        """Lê um artefato AST: `extraction/` primeiro, `compressed/` decodificado depois."""
        data = _load_json(self.ast_dir / filename)
        if data is not None:
            return data
        fallback = self.compressed_dir / filename
        if not fallback.exists():
            return None
        raw = _load_json(fallback)
        if raw is None:
            return None
        print(f"   ℹ️  {filename}: extraction/ ausente — usando compressed/ decodificado")
        return decode_headroom(raw)

    def run(self) -> int:
        print(f"\n🔧 SqlIrGenerator :: {self.project_name} :: {self.language}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        builder = SqlIrBuilder(self.project_name, self.language)

        # Step 1
        schemas = self._load_ast("04_database_schemas.json")
        builder.ingest_database_schemas(schemas)
        print(f"   📦 Entities from schemas: {len(builder.entities)}")

        # Step 2
        rules = self._load_ast("03_database_rules.json")
        builder.ingest_database_rules(rules)
        print(f"   📦 Entities after rules: {len(builder.entities)}")

        # Step 3
        procs = self._load_ast("05_procedures.json")
        builder.ingest_procedures(procs)
        print(f"   📦 Procedures: {len(builder.procedures)}")

        # Step 4 – inference
        builder.infer_relationships()
        print(f"   🔗 Relationships inferred: {len(builder.relationships)}")

        ir = builder.build()

        out_path = self.output_dir / "sql-ir.json"
        out_path.write_text(json.dumps(ir, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   ✅ {out_path}")

        # Write extraction/10_sql_functions.json so downstream validators see it.
        # Content: stored procedures extracted from 05_procedures.json, in the
        # standard artifact envelope used by all other extraction artefacts.
        stored_procs = [p for p in ir["procedures"] if p.get("kind") == "stored_procedure"]
        sql_funcs_artifact = {
            "artifact": "sql_functions",
            "schema_version": "1.0.0",
            "payload": {
                "functions": stored_procs,
                "counts": {"total": len(stored_procs)},
            },
        }
        sql_funcs_path = self.ast_dir / "10_sql_functions.json"
        sql_funcs_path.parent.mkdir(parents=True, exist_ok=True)
        sql_funcs_path.write_text(
            json.dumps(sql_funcs_artifact, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"   ✅ {sql_funcs_path}  ({len(stored_procs)} stored procedures)")

        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera SQL-IR a partir dos artefatos AST")
    ap.add_argument("--project", required=True, help="Nome do projeto")
    ap.add_argument("--language", default="delphi", help="Linguagem legada (default: delphi)")
    ap.add_argument("--ast-dir", type=Path, default=None, help="Diretório dos JSONs AST")
    ap.add_argument("--output-dir", type=Path, default=None, help="Diretório de saída")
    a = ap.parse_args()

    gen = SqlIrGenerator(
        project_name=a.project,
        language=a.language,
        ast_dir=a.ast_dir,
        output_dir=a.output_dir,
    )
    return gen.run()


if __name__ == "__main__":
    sys.exit(main())
