"""Phase 3 builder assertions for dual-language Architectural Patterns rows."""
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


def test_builder_emits_english_and_pt_pattern_rows() -> None:
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    shutil.copytree(FIXTURE, RUNTIME)
    try:
        result = subprocess.run(
            [sys.executable, "src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py", "--project", PROJECT],
            cwd=REPO,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, result.stderr[-4000:]
        html = next((RUNTIME / "outputs" / "summary").glob("AVA-FABRIC-SUMMARY-*.html")).read_text(encoding="utf-8")
        assert "A abstração de repositório" in html
        assert "Abstração adicional" in html
        assert "A regra é publicada no domínio" in html
        assert 'id="tb-tobe-patterns-pt"' in html
        assert 'var lang = "en"' in html
        source = json.loads((RUNTIME / "outputs" / "tobe" / "patterns-applied.json").read_text(encoding="utf-8"))["patterns"]
        for pattern in source:
            assert pattern["reference_artifact"] in html
            assert pattern["adr_reference"] in html
    finally:
        if RUNTIME.exists():
            shutil.rmtree(RUNTIME)
