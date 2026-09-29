"""Unit tests for sql_ir_generator.py."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

# Adjust import path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "modules" / "ava-fabric-agents" / "asis-diagnostic" / "utils"))

from sql_ir_generator import SqlIrBuilder, SqlIrGenerator, _normalize_type


class TestNormalizeType(unittest.TestCase):
    def test_integer(self):
        self.assertEqual(_normalize_type("Integer"), "integer")
        self.assertEqual(_normalize_type("INT"), "integer")
        self.assertEqual(_normalize_type("BIGINT"), "integer")

    def test_string(self):
        self.assertEqual(_normalize_type("VARCHAR(255)"), "string")
        self.assertEqual(_normalize_type("NVARCHAR"), "string")

    def test_decimal(self):
        self.assertEqual(_normalize_type("NUMERIC(18,2)"), "decimal")
        self.assertEqual(_normalize_type("MONEY"), "decimal")

    def test_unknown(self):
        self.assertEqual(_normalize_type("XYZ"), "unknown")
        self.assertEqual(_normalize_type(None), "unknown")


class TestSqlIrBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = SqlIrBuilder("Test-Project")

    def test_ingest_database_schemas(self):
        data = {
            "payload": {
                "tables": [
                    {"name": "clientes", "unit": "uClientes.pas", "columns_count": 5}
                ],
                "inferred_tables": [
                    {
                        "name": "pedidos",
                        "origin": "inferred_from_sql",
                        "accessed_columns": ["id", "cliente_id", "valor"],
                        "operations": ["insert", "select"],
                        "used_in": ["uPedidos.pas"]
                    }
                ],
                "dataset_fields": []
            }
        }
        self.builder.ingest_database_schemas(data)
        self.assertEqual(len(self.builder.entities), 2)
        names = {e["name"] for e in self.builder.entities.values()}
        self.assertIn("clientes", names)
        self.assertIn("pedidos", names)

    def test_ingest_database_rules(self):
        data = {
            "payload": {
                "rules": [
                    {
                        "type": "write_operation",
                        "operation": "insert",
                        "tables": ["pedidos"],
                        "source_ref": {"file": "uPedidos.pas", "line": 42}
                    }
                ]
            }
        }
        self.builder.ingest_database_rules(data)
        self.assertEqual(len(self.builder.entities), 1)
        ent = list(self.builder.entities.values())[0]
        self.assertIn("insert", ent["operations"])

    def test_inferred_table_kept_when_used_in_scope(self):
        """Tabelas inferidas devem ser mantidas se usadas por unidade em escopo,
        mesmo quando source_ref primário está fora de escopo."""
        builder = SqlIrBuilder("Scoped-Project")
        builder.manifest = {
            "scope_modules": ["vendas"],
            "included_units": ["uVendas.pas"],
            "_included_set": {"uvendas.pas"},
        }
        data = {
            "payload": {
                "tables": [],
                "inferred_tables": [
                    {
                        "name": "pedidos",
                        "source_ref": {"file": "uLegacy.pas", "line": 10},
                        "accessed_columns": ["id", "cliente_id", "valor"],
                        "used_in": ["uVendas.pas"]
                    }
                ],
                "dataset_fields": []
            }
        }
        builder.ingest_database_schemas(data)
        self.assertEqual(len(builder.entities), 1)
        ent = list(builder.entities.values())[0]
        self.assertEqual(ent["name"], "pedidos")
        self.assertEqual(ent["sources"][0]["file"], "uVendas.pas")

    def test_infer_relationships(self):
        # Create two entities: pedidos with FK to clientes
        self.builder.entities["ent-1"] = {
            "id": "ent-1", "name": "pedidos",
            "module_owners": ["vendas"],
            "attributes": [
                {"name": "id", "type": "integer", "is_pk": True, "is_fk": False},
                {"name": "id_cliente", "type": "integer", "is_pk": False, "is_fk": True}
            ]
        }
        self.builder.entities["ent-2"] = {
            "id": "ent-2", "name": "cliente",
            "module_owners": ["cadastro"],
            "attributes": [
                {"name": "id", "type": "integer", "is_pk": True, "is_fk": False}
            ]
        }
        self.builder.infer_relationships()
        self.assertEqual(len(self.builder.relationships), 1)
        rel = list(self.builder.relationships.values())[0]
        self.assertEqual(rel["source_entity"], "ent-1")
        self.assertEqual(rel["target_entity"], "ent-2")
        self.assertEqual(rel["cardinality"], "many-to-one")

    def test_build_adds_synthetic_pk(self):
        self.builder.entities["ent-1"] = {
            "id": "ent-1", "name": "x",
            "attributes": [{"name": "nome", "is_pk": False, "is_fk": False}]
        }
        ir = self.builder.build()
        attrs = ir["entities"][0]["attributes"]
        self.assertTrue(any(a["name"] == "id" and a["is_pk"] for a in attrs))


class TestSqlIrGeneratorEndToEnd(unittest.TestCase):
    def test_run_produces_sql_ir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ast_dir = Path(tmpdir) / "compressed"
            ast_dir.mkdir()
            out_dir = ast_dir

            # create minimal AST artifacts
            schemas = {
                "payload": {
                    "tables": [
                        {"name": "clientes", "unit": "uClientes.pas", "columns_count": 3}
                    ],
                    "inferred_tables": [],
                    "dataset_fields": []
                }
            }
            rules = {
                "payload": {
                    "rules": [
                        {"type": "write_operation", "operation": "insert", "tables": ["clientes"], "source_ref": {"file": "uClientes.pas", "line": 10}}
                    ]
                }
            }
            procs = {
                "payload": {
                    "stored_procedures": [],
                    "code_procedures": []
                }
            }
            (ast_dir / "04_database_schemas.json").write_text(json.dumps(schemas), encoding="utf-8")
            (ast_dir / "03_database_rules.json").write_text(json.dumps(rules), encoding="utf-8")
            (ast_dir / "05_procedures.json").write_text(json.dumps(procs), encoding="utf-8")

            gen = SqlIrGenerator("Test-Proj", ast_dir=ast_dir, output_dir=out_dir)
            ret = gen.run()
            self.assertEqual(ret, 0)

            ir_path = out_dir / "sql-ir.json"
            self.assertTrue(ir_path.exists())
            ir = json.loads(ir_path.read_text(encoding="utf-8"))
            self.assertEqual(ir["schema_version"], "1.0.0")
            self.assertEqual(ir["project_name"], "Test-Proj")
            self.assertEqual(len(ir["entities"]), 1)
            self.assertEqual(ir["entities"][0]["name"], "clientes")


if __name__ == "__main__":
    unittest.main()
