"""Phase 1 baseline for the isolated feature-038 Summary fixture.

This test intentionally runs the current, unmodified Summary builder and
validator. It copies the fixture into the builder's required ``projects/``
layout, then removes only generated outputs after the run.
"""
from __future__ import annotations

import hashlib
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "038-portuguese-manual-view" / "project"
PROJECT_NAME = "fixture-038-portuguese-manual-view"
RUNTIME_PROJECT = REPO_ROOT / "projects" / PROJECT_NAME


def _sha256_files(root: Path) -> dict[str, str]:
    # The unmodified builder materializes a derived security projection under
    # outputs/asis/security/; exclude generated outputs as well as the summary
    # directory from source-integrity checks.
    excluded = {"outputs/summary", "outputs/asis/security"}
    result: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        if any(relative == item or relative.startswith(item + "/") for item in excluded):
            continue
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _run(script: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / script), "--project", PROJECT_NAME],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env=env,
    )


def _ensure_fixture_mermaid_bundle() -> None:
    """Ensure the baseline fixture uses the repository's local Mermaid bundle.

    The current builder resolves its template-relative bundle from the
    repository root, while the fixture's copied project only supplies source
    artifacts. This helper makes the baseline precondition explicit without
    modifying the production template or builder.
    """
    bundle = REPO_ROOT / "src/modules/ava-fabric-agents/summary/templates/html/mermaid.min.js"
    assert bundle.exists(), f"Required local Mermaid bundle is missing: {bundle}"


def test_fixture_baseline_generate_and_validate_without_feature_changes() -> None:
    """The fixture must complete the current generate → validate cycle."""
    if RUNTIME_PROJECT.exists():
        shutil.rmtree(RUNTIME_PROJECT)
    shutil.copytree(FIXTURE_ROOT, RUNTIME_PROJECT)
    before = _sha256_files(RUNTIME_PROJECT)

    try:
        # This fixture is intentionally minimal and scoped to language/normalization testing (feature 038).
        # It does not include AS-IS/TO-BE diagrams, QA/evidence artifacts, database policy artifacts, or
        # complete phase-status metadata, so unrelated structural/completeness validator checks are expected
        # to fail. Only C8 (language consistency) and Mermaid/build success are relevant success criteria.
        _ensure_fixture_mermaid_bundle()
        build = _run("src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py")
        assert build.returncode == 0, (
            "Unmodified Summary builder failed for the isolated fixture.\n"
            f"stdout:\n{build.stdout[-6000:]}\n"
            f"stderr:\n{build.stderr[-6000:]}"
        )

        summary_dir = RUNTIME_PROJECT / "outputs" / "summary"
        html_files = list(summary_dir.glob("AVA-FABRIC-SUMMARY-*.html"))
        assert html_files, "Builder did not create the expected Summary HTML artifact."
        html = html_files[0].read_text(encoding="utf-8", errors="replace")
        assert 'var lang = "en"' in html, "Generated Summary does not default to English."
        validate = _run("src/modules/ava-fabric-agents/summary/utils/validate_summary.py")
        validation_report = summary_dir / "validation-report.json"
        validation_data = json.loads(validation_report.read_text(encoding="utf-8"))
        expected_errors = {"C2.9", "C6.2", "C11.1", "C11.2", "C11.7", "C11.8", "C11.25", "C11.30"}
        actual_errors = {
            check["id"]
            for check in validation_data["checks"]
            if check["status"] == "fail" and check["level"] == "error"
        }
        assert actual_errors == expected_errors, (
            f"Unexpected validator error set: {sorted(actual_errors)}; "
            f"expected only {sorted(expected_errors)}.\n"
            f"stdout:\n{validate.stdout[-6000:]}\n"
            f"stderr:\n{validate.stderr[-6000:]}"
        )
        c8 = {check["id"]: check for check in validation_data["checks"] if check["id"].startswith("C8.")}
        assert c8["C8.1"]["status"] == "pass", f"C8.1 language check failed: {c8['C8.1']}"
        assert (summary_dir / "validation-report.json").exists(), "Validator report JSON is missing."
        assert (summary_dir / "validation-report.md").exists(), "Validator report Markdown is missing."
    finally:
        after = _sha256_files(RUNTIME_PROJECT)
        assert after == before, "Fixture source/config artifacts changed during baseline execution."
        if RUNTIME_PROJECT.exists():
            shutil.rmtree(RUNTIME_PROJECT)


if __name__ == "__main__":
    try:
        test_fixture_baseline_generate_and_validate_without_feature_changes()
    except AssertionError as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
    except Exception as error:
        print(f"FAIL: {type(error).__name__}: {error}")
        raise SystemExit(1)
    else:
        print("PASS: feature-038 fixture baseline generate + validate cycle")
