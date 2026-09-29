"""
qa_test_runner.py — Execução local orquestrada de todos os tipos de teste QA.

Usage:
    python src/shared/utils/qa_test_runner.py --project Meu-ERP
    python src/shared/utils/qa_test_runner.py --project Meu-ERP --types unit,integration
    python src/shared/utils/qa_test_runner.py --project Meu-ERP --mode ci

Arguments:
    --project   Nome do projeto (obrigatório)
    --types     Tipos de teste: unit,integration,contract,db,frontend,playwright (default: all)
    --mode      local  — executa tudo exceto playwright-api se Docker indisponível
                ci     — executa tudo, falha se dependência ausente
    --output    Path do JSON de resultados
                (default: projects/{project}/outputs/qa/test-results.json)

Output JSON schema:
{
  "execution_timestamp": "ISO-8601",
  "container_runtime": "docker" | "podman" | "none",
  "suites": [
    {
      "type": "unit" | "integration" | "contract" | "db" | "frontend" | "playwright",
      "framework": "xunit" | "jest" | "playwright",
      "project": "<project name>",
      "total": N,
      "passed": N,
      "failed": N,
      "skipped": N,
      "coverage_line": float | null,
      "coverage_branch": float | null,
      "duration_ms": N,
      "status": "PASS" | "FAIL" | "NOT_EXECUTED",
      "trx_path": "<path to .trx or junit xml>" | null
    }
  ],
  "summary": {
    "total": N,
    "passed": N,
    "failed": N,
    "skipped": N,
    "not_executed": N,
    "success_rate": float,
    "overall_status": "PASS" | "FAIL" | "PARTIAL"
  }
}
"""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from glob import glob
from pathlib import Path


# ---------------------------------------------------------------------------
# Container runtime detection (reuses build_runner.py logic inline)
# ---------------------------------------------------------------------------

def detect_container_runtime() -> str:
    """Returns 'docker', 'podman', or 'none'."""
    for runtime in ("docker", "podman"):
        try:
            result = subprocess.run(
                [runtime, "info"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                return runtime
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return "none"


# ---------------------------------------------------------------------------
# TRX / JUnit XML parsing
# ---------------------------------------------------------------------------

def parse_trx(trx_path: str) -> dict:
    """Parse a .trx file and return aggregated counts."""
    counts = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0}
    try:
        tree = ET.parse(trx_path)
        root = tree.getroot()
        ns = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
        counters = root.find(".//t:Counters", ns)
        if counters is not None:
            counts["total"] = int(counters.get("total", 0))
            counts["passed"] = int(counters.get("passed", 0))
            counts["failed"] = int(counters.get("failed", 0))
            counts["skipped"] = int(counters.get("notExecuted", 0))
        times = root.find(".//t:Times", ns)
        if times is not None:
            start = times.get("start", "")
            finish = times.get("finish", "")
            if start and finish:
                try:
                    fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
                    t0 = datetime.strptime(start[:26] + "+00:00", fmt)
                    t1 = datetime.strptime(finish[:26] + "+00:00", fmt)
                    counts["duration_ms"] = int((t1 - t0).total_seconds() * 1000)
                except Exception:
                    pass
    except Exception:
        pass
    return counts


def parse_junit_xml(xml_path: str) -> dict:
    """Parse a JUnit-compatible XML and return aggregated counts."""
    counts = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0}
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
        for suite in suites:
            counts["total"] += int(suite.get("tests", 0))
            counts["failed"] += int(suite.get("failures", 0)) + int(suite.get("errors", 0))
            counts["skipped"] += int(suite.get("skipped", 0))
            duration = float(suite.get("time", 0))
            counts["duration_ms"] += int(duration * 1000)
        counts["passed"] = counts["total"] - counts["failed"] - counts["skipped"]
    except Exception:
        pass
    return counts


# ---------------------------------------------------------------------------
# .NET test runners
# ---------------------------------------------------------------------------

def run_dotnet_tests(
    csproj_glob: str,
    filter_expr: str,
    suite_type: str,
    project_outputs_dir: str,
    container_runtime: str,
    mode: str,
) -> list:
    """Run dotnet test for matching csproj files, return suite result dicts."""
    results = []
    csproj_files = glob(csproj_glob, recursive=True)

    needs_docker = suite_type in ("integration", "db")
    if needs_docker and container_runtime == "none":
        if mode == "ci":
            print(f"⛔ ERROR: container runtime unavailable for {suite_type} tests (mode=ci)")
            sys.exit(1)
        print(f"⚠️ CONTAINER_RUNTIME_UNAVAILABLE — {suite_type} tests NOT_EXECUTED (Docker/Podman required)")
        for csproj in csproj_files:
            results.append({
                "type": suite_type,
                "framework": "xunit",
                "project": Path(csproj).stem,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "coverage_line": None,
                "coverage_branch": None,
                "duration_ms": 0,
                "status": "NOT_EXECUTED",
                "trx_path": None,
            })
        return results

    for csproj in csproj_files:
        proj_name = Path(csproj).stem
        trx_dir = os.path.join(project_outputs_dir, "qa", "test-results", suite_type)
        os.makedirs(trx_dir, exist_ok=True)
        trx_path = os.path.join(trx_dir, f"{proj_name}.trx")

        cmd = [
            "dotnet", "test", csproj,
            "--logger", f"trx;LogFileName={trx_path}",
            "--no-build",
        ]
        if filter_expr:
            cmd += ["--filter", filter_expr]

        print(f"▶ Running {suite_type} tests: {proj_name}")
        proc = subprocess.run(cmd, capture_output=True, text=True)

        counts = parse_trx(trx_path) if os.path.exists(trx_path) else {
            "total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0
        }
        status = "PASS" if proc.returncode == 0 else "FAIL"

        results.append({
            "type": suite_type,
            "framework": "xunit",
            "project": proj_name,
            **counts,
            "coverage_line": None,
            "coverage_branch": None,
            "status": status,
            "trx_path": trx_path if os.path.exists(trx_path) else None,
        })

    return results


# ---------------------------------------------------------------------------
# Frontend tests (Jest)
# ---------------------------------------------------------------------------

def run_frontend_tests(frontend_pkg_json: str, project_outputs_dir: str, mode: str) -> list:
    """Run npm test for the frontend project."""
    if not os.path.exists(frontend_pkg_json):
        return []

    frontend_dir = os.path.dirname(frontend_pkg_json)
    junit_path = os.path.join(project_outputs_dir, "qa", "test-results", "frontend", "jest-results.xml")
    os.makedirs(os.path.dirname(junit_path), exist_ok=True)

    cmd = [
        "npm", "test", "--", "--ci", "--passWithNoTests",
        f"--reporters=default",
        f"--reporters=jest-junit",
    ]
    env = os.environ.copy()
    env["JEST_JUNIT_OUTPUT_FILE"] = junit_path

    print(f"▶ Running frontend tests in: {frontend_dir}")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=frontend_dir, env=env)

    counts = parse_junit_xml(junit_path) if os.path.exists(junit_path) else {
        "total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0
    }
    status = "PASS" if proc.returncode == 0 else "FAIL"

    return [{
        "type": "frontend",
        "framework": "jest",
        "project": "frontend",
        **counts,
        "coverage_line": None,
        "coverage_branch": None,
        "status": status,
        "trx_path": junit_path if os.path.exists(junit_path) else None,
    }]


# ---------------------------------------------------------------------------
# Playwright API tests
# ---------------------------------------------------------------------------

def run_playwright_tests(
    api_pkg_json: str, project_outputs_dir: str, container_runtime: str, mode: str
) -> list:
    """Run npx playwright test for the API black-box test suite."""
    if not os.path.exists(api_pkg_json):
        return []

    api_dir = os.path.dirname(api_pkg_json)
    junit_path = os.path.join(project_outputs_dir, "qa", "test-results", "playwright", "results.xml")
    os.makedirs(os.path.dirname(junit_path), exist_ok=True)

    cmd = [
        "npx", "playwright", "test",
        "--reporter=list",
        f"--reporter=junit",
    ]
    env = os.environ.copy()
    env["PLAYWRIGHT_JUNIT_OUTPUT_NAME"] = junit_path

    print(f"▶ Running Playwright/TS API tests in: {api_dir}")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=api_dir, env=env)

    counts = parse_junit_xml(junit_path) if os.path.exists(junit_path) else {
        "total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0
    }
    status = "PASS" if proc.returncode == 0 else "FAIL"

    return [{
        "type": "playwright",
        "framework": "playwright",
        "project": "automated_test/api",
        **counts,
        "coverage_line": None,
        "coverage_branch": None,
        "status": status,
        "trx_path": junit_path if os.path.exists(junit_path) else None,
    }]


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------

def compute_summary(suites: list) -> dict:
    total = sum(s["total"] for s in suites)
    passed = sum(s["passed"] for s in suites)
    failed = sum(s["failed"] for s in suites)
    skipped = sum(s["skipped"] for s in suites)
    not_executed = sum(1 for s in suites if s["status"] == "NOT_EXECUTED")

    executed = total - skipped
    success_rate = round((passed / executed * 100), 2) if executed > 0 else 0.0

    if failed > 0:
        overall = "FAIL"
    elif not_executed > 0:
        overall = "PARTIAL"
    else:
        overall = "PASS"

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "not_executed": not_executed,
        "success_rate": success_rate,
        "overall_status": overall,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="QA Test Runner — local orchestrated test execution")
    parser.add_argument("--project", required=True, help="Project name (directory under projects/)")
    parser.add_argument(
        "--types",
        default="all",
        help="Comma-separated types: unit,integration,contract,db,frontend,playwright (default: all)",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "ci"],
        default="local",
        help="Execution mode: local (lenient) or ci (strict)",
    )
    parser.add_argument("--output", default=None, help="Output JSON path")
    args = parser.parse_args()

    project_name = args.project
    requested_types = {t.strip() for t in args.types.split(",")} if args.types != "all" else None
    mode = args.mode

    # Resolve project paths
    workspace_root = Path(__file__).parent.parent.parent.parent  # repo root
    project_outputs_dir = str(workspace_root / "projects" / project_name / "outputs")
    source_dir = os.path.join(project_outputs_dir, "tobe", "source-code")
    frontend_pkg = os.path.join(source_dir, "frontend", "package.json")
    api_pkg = str(workspace_root / "automated_test" / "api" / "package.json")

    output_path = args.output or os.path.join(project_outputs_dir, "qa", "test-results.json")

    def should_run(t: str) -> bool:
        return requested_types is None or t in requested_types

    # Detect container runtime
    print("🔍 Detecting container runtime...")
    container_runtime = detect_container_runtime()
    print(f"   Container runtime: {container_runtime}")
    if container_runtime == "none":
        print("⚠️ CONTAINER_RUNTIME_UNAVAILABLE — integration/db tests will be marked NOT_EXECUTED")
        print("   Run 'docker info' or 'podman machine info' to troubleshoot.")

    suites = []

    # Unit tests
    if should_run("unit"):
        unit_glob = os.path.join(source_dir, "tests", "Unit", "**", "*.csproj")
        suites += run_dotnet_tests(unit_glob, "Category=Unit", "unit", project_outputs_dir, container_runtime, mode)

    # Integration tests
    if should_run("integration"):
        int_glob = os.path.join(source_dir, "tests", "Integration", "**", "*.csproj")
        suites += run_dotnet_tests(int_glob, "Category=Integration", "integration", project_outputs_dir, container_runtime, mode)

    # Contract tests
    if should_run("contract"):
        ct_glob = os.path.join(source_dir, "tests", "Contract", "**", "*.csproj")
        suites += run_dotnet_tests(ct_glob, "Category=Contract", "contract", project_outputs_dir, container_runtime, mode)

    # DB integrity tests
    if should_run("db"):
        db_glob = os.path.join(source_dir, "tests", "DatabaseIntegrity", "**", "*.csproj")
        suites += run_dotnet_tests(db_glob, "", "db", project_outputs_dir, container_runtime, mode)

    # Frontend tests
    if should_run("frontend"):
        suites += run_frontend_tests(frontend_pkg, project_outputs_dir, mode)

    # Playwright API tests
    if should_run("playwright"):
        suites += run_playwright_tests(api_pkg, project_outputs_dir, container_runtime, mode)

    # Build result
    result = {
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "container_runtime": container_runtime,
        "suites": suites,
        "summary": compute_summary(suites),
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Test execution complete:")
    print(f"   Total:        {result['summary']['total']}")
    print(f"   Passed:       {result['summary']['passed']}")
    print(f"   Failed:       {result['summary']['failed']}")
    print(f"   Skipped:      {result['summary']['skipped']}")
    print(f"   Not executed: {result['summary']['not_executed']}")
    print(f"   Success rate: {result['summary']['success_rate']}%")
    print(f"   Status:       {result['summary']['overall_status']}")
    print(f"   Output:       {output_path}")

    exit_code = 0 if result["summary"]["overall_status"] in ("PASS", "PARTIAL") else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
