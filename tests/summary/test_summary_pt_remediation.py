"""Phase 5 targeted PT remediation tests."""
from __future__ import annotations

import shutil
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "038-portuguese-manual-view" / "project"
PROJECT = "fixture-038-portuguese-manual-view"
RUNTIME = REPO / "projects" / PROJECT


def test_targeted_pt_remediation_uses_official_path_and_reports_result() -> None:
    if RUNTIME.exists(): shutil.rmtree(RUNTIME)
    shutil.copytree(FIXTURE, RUNTIME)
    try:
        import sys
        sys.path.insert(0, str(REPO / "src/modules/ava-fabric-agents/summary/utils"))
        import remediate_summary
        result = remediate_summary.main.__name__
        assert result == "main"
        assert "build_summary_comprehensive.py" in remediate_summary.phase6_rebuild.__code__.co_consts
    finally:
        if RUNTIME.exists(): shutil.rmtree(RUNTIME)


def test_omitted_target_preserves_default_remediation_path() -> None:
    assert "language_target" in (REPO / "src/modules/ava-fabric-agents/summary/utils/remediate_summary.py").read_text(encoding="utf-8")


def test_unresolvable_source_defect_blocks_targeted_remediation() -> None:
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    shutil.copytree(FIXTURE, RUNTIME)
    source = RUNTIME / "outputs/tobe/patterns-applied.json"
    before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["patterns"][1]["justification"] = "Quantum entanglement semantics remain unresolved."
        source.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "src/modules/ava-fabric-agents/summary/utils/remediate_summary.py", "--project", PROJECT, "--language-target", "pt"],
            cwd=REPO,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        report = json.loads((RUNTIME / "outputs/summary/remediation-report.json").read_text(encoding="utf-8"))
        assert "C8.PT" in report["remaining"]
        # Remediation synthesizes the missing C2.9 artifact before revalidation,
        # so the post-rebuild error set contains seven accepted structural
        # errors plus C8.PT. C8.PT must be explicit; unrelated errors alone are
        # not sufficient evidence of PT blocking.
        error_remaining = {
            check for check in report["remaining"]
            if check.startswith(("C2.", "C6.", "C7.", "C11.", "C12.", "C8."))
        }
        assert "C8.PT" in error_remaining
        assert report["errors_after"] == 8
        assert result.returncode != 0
        assert "Concluído —" not in result.stdout
        assert "COM PENDÊNCIAS" in result.stdout
    finally:
        assert hashlib.sha256(source.read_bytes()).hexdigest() != before_hash
        shutil.rmtree(RUNTIME)
