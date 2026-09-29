"""
qa_preflight.py — Validação de pré-requisitos para a fase QA.

Usage:
    python src/shared/utils/qa_preflight.py --project Meu-ERP

Checks:
    1. Container runtime (Docker/Podman) disponível e daemon running
    2. .NET SDK versão >= tobe_stack.backend_version
    3. Node.js versão >= tobe_stack.node_version
    4. npm disponível
    5. NuGet feed acessível (dotnet nuget list source)
    6. Frontend package.json resolve (npm ls --depth 0 não falha)

Output:
    JSON com status por check + overall PASS/FAIL/WARNING
    Exit code: 0 (PASS), 1 (FAIL), 2 (WARNING — parcial)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list, timeout: int = 15) -> tuple:
    """Returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout after {timeout}s"


def _parse_version(version_str: str) -> tuple:
    """Parse a version string like '8.0.100' or 'v22.1.0' into (major, minor, patch)."""
    version_str = version_str.lstrip("v")
    parts = re.findall(r"\d+", version_str)
    if len(parts) >= 3:
        return tuple(int(p) for p in parts[:3])
    if len(parts) == 2:
        return (int(parts[0]), int(parts[1]), 0)
    if len(parts) == 1:
        return (int(parts[0]), 0, 0)
    return (0, 0, 0)


def _read_project_config(project_name: str) -> dict:
    """Read project-config.yaml for the given project."""
    workspace_root = Path(__file__).parent.parent.parent.parent
    config_path = workspace_root / "projects" / project_name / "context" / "project-config.yaml"
    if not config_path.exists():
        return {}
    if not HAS_YAML:
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_container_runtime() -> dict:
    for runtime in ("docker", "podman"):
        rc, out, _ = _run([runtime, "info"])
        if rc == 0:
            return {"id": "container_runtime", "status": "PASS", "detail": f"{runtime} daemon running"}
    return {
        "id": "container_runtime",
        "status": "WARNING",
        "detail": "No container runtime found (Docker/Podman). Integration/DB tests will be NOT_EXECUTED. "
                  "Run 'docker info' or 'podman machine info' to troubleshoot.",
    }


def check_dotnet_sdk(required_version: str) -> dict:
    rc, out, _ = _run(["dotnet", "--version"])
    if rc != 0:
        return {"id": "dotnet_sdk", "status": "FAIL", "detail": ".NET SDK not installed or not in PATH"}

    installed = _parse_version(out)
    required = _parse_version(required_version) if required_version else (0, 0, 0)

    if installed >= required:
        return {
            "id": "dotnet_sdk",
            "status": "PASS",
            "detail": f"dotnet {out} >= required {required_version or 'any'}",
        }
    return {
        "id": "dotnet_sdk",
        "status": "FAIL",
        "detail": f"dotnet {out} < required {required_version}. Install .NET SDK {required_version}+.",
    }


def check_nodejs(required_version: str) -> dict:
    rc, out, _ = _run(["node", "--version"])
    if rc != 0:
        return {"id": "nodejs", "status": "FAIL", "detail": "Node.js not installed or not in PATH"}

    installed = _parse_version(out)
    required = _parse_version(required_version) if required_version else (0, 0, 0)

    if installed >= required:
        return {
            "id": "nodejs",
            "status": "PASS",
            "detail": f"node {out} >= required {required_version or 'any'}",
        }
    return {
        "id": "nodejs",
        "status": "FAIL",
        "detail": f"node {out} < required {required_version}. Install Node.js {required_version}+.",
    }


def check_npm() -> dict:
    rc, out, _ = _run(["npm", "--version"])
    if rc == 0:
        return {"id": "npm", "status": "PASS", "detail": f"npm {out}"}
    return {"id": "npm", "status": "FAIL", "detail": "npm not found. Install Node.js (includes npm)."}


def check_nuget_feed() -> dict:
    rc, out, _ = _run(["dotnet", "nuget", "list", "source"])
    if rc != 0:
        return {
            "id": "nuget_feed",
            "status": "WARNING",
            "detail": "Could not list NuGet sources. Verify dotnet CLI and network access.",
        }
    enabled = [line for line in out.splitlines() if "[Enabled]" in line]
    if enabled:
        return {"id": "nuget_feed", "status": "PASS", "detail": f"{len(enabled)} NuGet source(s) enabled"}
    return {
        "id": "nuget_feed",
        "status": "WARNING",
        "detail": "No enabled NuGet sources found. Run 'dotnet nuget add source' to configure.",
    }


def check_frontend_packages(project_name: str) -> dict:
    workspace_root = Path(__file__).parent.parent.parent.parent
    pkg_path = (
        workspace_root
        / "projects"
        / project_name
        / "outputs"
        / "tobe"
        / "source-code"
        / "frontend"
        / "package.json"
    )
    if not pkg_path.exists():
        return {
            "id": "frontend_packages",
            "status": "WARNING",
            "detail": "frontend/package.json not found — frontend may not have been generated yet",
        }
    rc, _, err = _run(["npm", "ls", "--depth", "0"], timeout=30)
    if rc == 0:
        return {"id": "frontend_packages", "status": "PASS", "detail": "npm ls --depth 0 OK"}
    return {
        "id": "frontend_packages",
        "status": "WARNING",
        "detail": f"npm ls reported issues: {err[:200]}. Run 'npm install' in frontend/.",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="QA Preflight — validate QA phase prerequisites")
    parser.add_argument("--project", required=True, help="Project name (directory under projects/)")
    args = parser.parse_args()

    project_name = args.project
    config = _read_project_config(project_name)
    tobe_stack = config.get("tobe_stack", {})
    backend_version = tobe_stack.get("backend_version", "")
    node_version = tobe_stack.get("node_version", "")

    print(f"🔍 QA Preflight — project: {project_name}")
    print(f"   Expected backend: {backend_version or 'any'}")
    print(f"   Expected Node.js: {node_version or 'any'}")
    print()

    checks = [
        check_container_runtime(),
        check_dotnet_sdk(backend_version),
        check_nodejs(node_version),
        check_npm(),
        check_nuget_feed(),
        check_frontend_packages(project_name),
    ]

    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    warn_count = sum(1 for c in checks if c["status"] == "WARNING")

    if fail_count > 0:
        overall = "FAIL"
    elif warn_count > 0:
        overall = "WARNING"
    else:
        overall = "PASS"

    result = {
        "project": project_name,
        "overall": overall,
        "checks": checks,
    }

    print("┌─────────────────────────────────────────────────────────────┐")
    print(f"│ QA PREFLIGHT RESULT: {overall:<40}│")
    print("├─────────────────────────────────────────────────────────────┤")
    for c in checks:
        icon = "✅" if c["status"] == "PASS" else ("⚠️" if c["status"] == "WARNING" else "❌")
        print(f"│ {icon} {c['id']:<25} {c['status']:<8} {c['detail'][:25]:<25} │")
    print("└─────────────────────────────────────────────────────────────┘")

    print()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    exit_map = {"PASS": 0, "WARNING": 2, "FAIL": 1}
    sys.exit(exit_map.get(overall, 1))


if __name__ == "__main__":
    main()
