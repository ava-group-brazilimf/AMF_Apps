#!/usr/bin/env python3
"""Unit tests for check_diagram_completeness.py."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parent / "check_diagram_completeness.py"


def run_checker(tmp_path: Path, registry: dict, diagram: str, manifest: dict, type_: str, threshold: int = 80):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(registry), encoding="utf-8")

    diagram_path = tmp_path / "screen-flow.mmd" if type_ == "screen-flow" else tmp_path / "er-diagram.mmd"
    diagram_path.write_text(diagram, encoding="utf-8")

    manifest_path = tmp_path / f"{diagram_path.stem}-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    out_path = tmp_path / "assertion.json"
    cmd = [
        sys.executable,
        str(CHECKER),
        "--type", type_,
        "--project", "TestProject",
        "--diagram", str(diagram_path),
        "--registry", str(reg_path),
        "--output", str(out_path),
        "--threshold", str(threshold),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert out_path.exists(), result.stderr or result.stdout
    return json.loads(out_path.read_text(encoding="utf-8"))


def test_screen_flow_passes_with_detail_manifest(tmp_path):
    registry = {
        "forms": [
            {"form_name": "frmMain"},
            {"form_name": "frmProduct001"},
            {"form_name": "frmProduct002"},
        ]
    }
    overview = "flowchart TD\n    N_frmMain[\"frmMain\"]\n"
    detail = "flowchart TD\n    N_frmProduct001[\"frmProduct001\"]\n    N_frmProduct002[\"frmProduct002\"]\n"
    manifest = {
        "generated_files": [
            {"file": "screen-flow.mmd", "size": 100, "status": "PASS"},
            {"file": "screen-flow-products.mmd", "size": 100, "status": "PASS"},
        ]
    }
    (tmp_path / "screen-flow-products.mmd").write_text(detail, encoding="utf-8")
    assertion = run_checker(tmp_path, registry, overview, manifest, "screen-flow", threshold=80)
    assert assertion["status"] == "PASS"
    assert assertion["coverage_pct"] == 100.0
    assert assertion["missing_count"] == 0


def test_screen_flow_fails_when_detail_missing(tmp_path):
    registry = {
        "forms": [
            {"form_name": "frmMain"},
            {"form_name": "frmProduct001"},
            {"form_name": "frmProduct002"},
        ]
    }
    overview = "flowchart TD\n    N_frmMain[\"frmMain\"]\n"
    manifest = {
        "generated_files": [
            {"file": "screen-flow.mmd", "size": 100, "status": "PASS"},
        ]
    }
    assertion = run_checker(tmp_path, registry, overview, manifest, "screen-flow", threshold=80)
    assert assertion["status"] == "FAIL"
    assert assertion["coverage_pct"] == pytest.approx(33.33, 0.01)
    assert set(assertion["missing_items"]) == {"N_frmProduct001", "N_frmProduct002"}


def test_screen_flow_penalizes_unregistered_nodes(tmp_path):
    registry = {"forms": [{"form_name": "frmMain"}]}
    overview = "flowchart TD\n    N_frmMain[\"frmMain\"]\n    N_other[\"other\"]\n"
    manifest = {"generated_files": [{"file": "screen-flow.mmd", "size": 100, "status": "PASS"}]}
    assertion = run_checker(tmp_path, registry, overview, manifest, "screen-flow", threshold=80)
    assert assertion["status"] == "PASS"
    assert assertion["coverage_pct"] == 100.0
    assert assertion["N_nodes"] == 2


def test_er_diagram_passes_with_detail_manifest(tmp_path):
    registry = {
        "tables": [
            {"name": "USERS"},
            {"name": "PRODUCTS_001"},
            {"name": "PRODUCTS_002"},
        ]
    }
    overview = "erDiagram\n    USERS { int id }\n"
    detail = "erDiagram\n    PRODUCTS_001 { int id }\n    PRODUCTS_002 { int id }\n"
    manifest = {
        "generated_files": [
            {"file": "er-diagram.mmd", "size": 100, "status": "PASS"},
            {"file": "er-diagram-products.mmd", "size": 100, "status": "PASS"},
        ]
    }
    (tmp_path / "er-diagram-products.mmd").write_text(detail, encoding="utf-8")
    assertion = run_checker(tmp_path, registry, overview, manifest, "er-diagram", threshold=80)
    assert assertion["status"] == "PASS"
    assert assertion["coverage_pct"] == 100.0
    assert assertion["missing_count"] == 0


def test_er_diagram_reports_missing_entities(tmp_path):
    registry = {
        "tables": [
            {"name": "USERS"},
            {"name": "PRODUCTS_001"},
        ]
    }
    overview = "erDiagram\n    USERS { int id }\n"
    manifest = {"generated_files": [{"file": "er-diagram.mmd", "size": 100, "status": "PASS"}]}
    assertion = run_checker(tmp_path, registry, overview, manifest, "er-diagram", threshold=80)
    assert assertion["status"] == "FAIL"
    assert assertion["missing_items"] == ["PRODUCTS_001"]
