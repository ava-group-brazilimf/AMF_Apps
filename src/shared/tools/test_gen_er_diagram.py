#!/usr/bin/env python3
"""Unit tests for gen_er_diagram.py including recursive lower-level diagrams."""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "gen_er_diagram", _MODULE_DIR / "gen_er_diagram.py"
)
gen_er_diagram = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_er_diagram)


BC_MAP = """# Bounded Context Map — MeuERP

## BC-01: Customer
**Key tables**: CLIENTE, CLIENTE_ENDERECO

## BC-02: Catalog
**Key tables**: PRODUTO, PRODUTO_CATEGORIA, PRODUTO_PRECO
"""


class TestErDiagramEndToEnd(unittest.TestCase):
    def _run_script(self, payload, bc_map_content=None):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmpdir, ignore_errors=True))

        input_path = Path(tmpdir) / "schema.json"
        input_path.write_text(json.dumps(payload), encoding="utf-8")

        output_path = Path(tmpdir) / "er-diagram.mmd"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bc_map_path = None
        if bc_map_content:
            bc_map_path = Path(tmpdir) / "bounded-context-map.md"
            bc_map_path.write_text(bc_map_content, encoding="utf-8")

        argv = [
            "gen_er_diagram.py",
            "--project",
            "testproject",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ]
        if bc_map_path:
            argv.extend(["--bc-map", str(bc_map_path)])

        old_argv = list(gen_er_diagram.sys.argv)
        try:
            gen_er_diagram.sys.argv = argv
            with self.assertRaises(SystemExit) as cm:
                gen_er_diagram.main()
        finally:
            gen_er_diagram.sys.argv = old_argv
        self.assertEqual(cm.exception.code, 0)

        self.assertTrue(output_path.exists())
        content = output_path.read_text(encoding="utf-8")
        self.assertIn("erDiagram", content)
        return Path(tmpdir)

    def test_end_to_end_small(self):
        payload = {
            "payload": {
                "tables": [
                    {"name": "CLIENTE", "columns": [{"name": "ID", "data_type": "Integer"}]},
                    {"name": "PRODUTO", "columns": [{"name": "ID", "data_type": "Integer"}]},
                ]
            }
        }
        tmpdir = self._run_script(payload, BC_MAP)
        self.assertTrue((tmpdir / "er-diagram-BC-01--Customer.mmd").exists())
        self.assertTrue((tmpdir / "er-diagram-BC-02--Catalog.mmd").exists())
        manifest = json.loads((tmpdir / "er-diagram-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["total_tables"], 2)
        self.assertGreaterEqual(manifest["pass_count"], 3)

    def test_end_to_end_recursive_split(self):
        """Large BC should produce recursive subgroup diagrams."""
        tables = [
            {"name": f"PRODUTO_{i:03d}", "columns": [{"name": "ID", "data_type": "Integer"}]}
            for i in range(60)
        ]
        payload = {"payload": {"tables": tables}}
        tmpdir = self._run_script(payload, BC_MAP)
        files = list(tmpdir.glob("er-diagram-*.mmd"))
        self.assertGreater(len(files), 2)  # overview + per-BC + subgroups
        manifest = json.loads((tmpdir / "er-diagram-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["total_tables"], 60)
        self.assertEqual(manifest["fail_count"], 0)


class TestPartitionHelpers(unittest.TestCase):
    def test_partition_tables_by_prefix(self):
        tables = [
            {"name": "CLIENTE_01"},
            {"name": "CLIENTE_02"},
            {"name": "PRODUTO_01"},
        ]
        groups = gen_er_diagram.partition_tables_by_prefix(tables, prefix_len=4)
        self.assertIn("clie", groups)
        self.assertIn("prod", groups)
        self.assertEqual(len(groups["clie"]), 2)

    def test_choose_prefix_partition(self):
        tables = [{"name": f"T{i:03d}"} for i in range(100)]
        groups = gen_er_diagram.choose_prefix_partition(tables, threshold=30)
        self.assertIsNotNone(groups)
        self.assertLessEqual(max(len(g) for g in groups.values()), 30)


if __name__ == "__main__":
    unittest.main()
