"""Phase 4 explicit PT validation tests."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "038-portuguese-manual-view" / "project"
PROJECT = "fixture-038-portuguese-manual-view"
RUNTIME = REPO / "projects" / PROJECT
SCHEMA = REPO / "specs/037-enforce-english-summary/contracts/language-compliance.schema.json"


def _build() -> Path:
    if RUNTIME.exists(): shutil.rmtree(RUNTIME)
    shutil.copytree(FIXTURE, RUNTIME)
    result = subprocess.run([sys.executable, "src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py", "--project", PROJECT], cwd=REPO, env={**os.environ, "PYTHONIOENCODING":"utf-8"}, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stderr[-3000:]
    return next((RUNTIME / "outputs/summary").glob("AVA-FABRIC-SUMMARY-*.html"))


def test_explicit_pt_compliant_result_uses_canonical_schema() -> None:
    try:
        _build()
        result = subprocess.run([sys.executable, "src/modules/ava-fabric-agents/summary/utils/validate_summary.py", "--project", PROJECT, "--language-target", "pt"], cwd=REPO, env={**os.environ, "PYTHONIOENCODING":"utf-8"}, capture_output=True, text=True, encoding="utf-8", errors="replace")
        report = json.loads((RUNTIME / "outputs/summary/validation-report.json").read_text(encoding="utf-8"))
        pt = next(c for c in report["checks"] if c["id"] == "C8.PT")
        assert pt["status"] == "pass"
        assert SCHEMA.exists()
        assert not (REPO / "specs/038-portuguese-manual-view/contracts/language-compliance.schema.json").exists()
    finally:
        if RUNTIME.exists(): shutil.rmtree(RUNTIME)


def test_default_validation_keeps_english_c8_behavior() -> None:
    try:
        _build()
        result = subprocess.run([sys.executable, "src/modules/ava-fabric-agents/summary/utils/validate_summary.py", "--project", PROJECT], cwd=REPO, env={**os.environ, "PYTHONIOENCODING":"utf-8"}, capture_output=True, text=True, encoding="utf-8", errors="replace")
        report = json.loads((RUNTIME / "outputs/summary/validation-report.json").read_text(encoding="utf-8"))
        assert not any(c["id"] == "C8.PT" for c in report["checks"])
    finally:
        if RUNTIME.exists(): shutil.rmtree(RUNTIME)
