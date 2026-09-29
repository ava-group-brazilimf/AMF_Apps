"""Unit tests for business_rules_catalog_generator.py canonical rules support."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "src"
        / "modules"
        / "ava-fabric-agents"
        / "asis-diagnostic"
        / "utils"
    ),
)

from business_rules_catalog_generator import BusinessRulesCatalogGenerator


class TestBusinessRulesCatalogGenerator(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.project_name = "test-proj"
        self.compressed = self.tmpdir / "compressed"
        self.compressed.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        parent = Path(__file__).resolve().parents[2] / "projects" / self.project_name / "outputs" / "asis" / "docs"
        shutil.rmtree(parent.parent.parent.parent, ignore_errors=True)

    def _write_01(self, data: dict) -> None:
        (self.compressed / "01_business_rules.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    def _write_02(self, data: dict) -> None:
        (self.compressed / "02_form_business_rules.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    def test_canonical_java_business_rules(self):
        self._write_01({
            "artifact": "business_rules",
            "schema_version": "1.0.0",
            "payload": {
                "rules": [
                    {
                        "id": "BR-00001",
                        "type": "calculation",
                        "category": "customer",
                        "unit": "OrderService",
                        "method": "calculateTotal",
                        "target": "Total",
                        "expression": "price * quantity",
                        "source_ref": {"file": "OrderService.java", "line": 42},
                    }
                ],
                "counts": {"total": 1},
            },
        })
        self._write_02({
            "artifact": "form_business_rules",
            "schema_version": "1.0.0",
            "payload": {
                "counts": {"forms": 1, "fields": 1},
                "forms": [
                    {
                        "form_name": "LoginFrame",
                        "form_class": "LoginFrame",
                        "source_file": "LoginFrame.java",
                        "fields": [
                            {
                                "name": "btnOk",
                                "component_class": "JButton",
                                "event_handlers": {"actionPerformed": "doLogin"},
                                "has_validation": False,
                            }
                        ],
                    }
                ],
            },
        })
        gen = BusinessRulesCatalogGenerator(self.project_name, compressed_dir=self.compressed)
        self.assertEqual(gen.run(), 0)
        catalog_path = (
            Path(__file__).resolve().parents[2]
            / "projects"
            / self.project_name
            / "outputs"
            / "asis"
            / "docs"
            / "business-rules-catalog.json"
        )
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(catalog["counts"]["total"], 2)
        self.assertEqual(catalog["counts"]["from_01"], 1)
        self.assertEqual(catalog["counts"]["from_02_validations"], 1)
        rule = next(r for r in catalog["rules"] if r["origin"] == "01_business_rules.json")
        self.assertEqual(rule["source"], "OrderService.java:42")
        self.assertEqual(rule["expression"], "price * quantity")

    def test_legacy_bucketed_string_still_works(self):
        raw = (
            "__buckets:type\n"
            "__key:calculation\n"
            "[1]{id:str,unit:str,method:str,expression:str,source_ref.file:str,source_ref.line:int}\n"
            "BR-00001,OrderService,calcTotal,price * qty,OrderService.pas,10\n"
        )
        self._write_01({
            "artifact": "business_rules",
            "schema_version": "1.0.0",
            "payload": {"rules": raw, "counts": {"total": 1}},
        })
        gen = BusinessRulesCatalogGenerator(self.project_name, compressed_dir=self.compressed)
        self.assertEqual(gen.run(), 0)
        catalog_path = (
            Path(__file__).resolve().parents[2]
            / "projects"
            / self.project_name
            / "outputs"
            / "asis"
            / "docs"
            / "business-rules-catalog.json"
        )
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(catalog["counts"]["total"], 1)
        rule = catalog["rules"][0]
        self.assertEqual(rule["source"], "OrderService.pas:10")


if __name__ == "__main__":
    unittest.main()
