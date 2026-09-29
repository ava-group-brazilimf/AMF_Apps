#!/usr/bin/env python3
"""
verify_scaffold.py — Deterministic scaffold file-existence checker.

Reads a YAML manifest listing mandatory files for a given stack (angular, dotnet)
and verifies each file exists relative to a given root directory.

Usage:
    python src/shared/utils/verify_scaffold.py --manifest angular --root projects/Meu-ERP/outputs/tobe/source-code/frontend
    python src/shared/utils/verify_scaffold.py --manifest dotnet  --root projects/Meu-ERP/outputs/tobe/source-code/backend

Output (JSON to stdout):
    {
      "status": "PASS" | "FAIL",
      "manifest_id": "angular",
      "root": "/abs/path/to/frontend",
      "total": 14,
      "found": 14,
      "missing": [],
      "blocking_missing": 0,
      "details": [
        {"path": "package.json", "exists": true, "blocking": true, "category": "config"},
        ...
      ]
    }

Exit codes:
    0 — PASS (all blocking files present)
    1 — FAIL (one or more blocking files missing)
    2 — ERROR (manifest not found, invalid args, etc.)
"""

import argparse
import glob as globmod
import json
import os
import sys
from pathlib import Path

# Resolve manifest directory relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
MANIFESTS_DIR = SCRIPT_DIR.parent / "shared" / "data" / "scaffold-manifests"

# Fallback: try relative to workspace root (when invoked from repo root)
WORKSPACE_MANIFESTS_DIR = Path("src/shared/data/scaffold-manifests")


def find_manifest(manifest_id: str) -> Path:
    """Locate the manifest YAML file by ID."""
    filename = f"{manifest_id}-scaffold-manifest.yaml"

    # Try relative to script location first
    candidate = MANIFESTS_DIR / filename
    if candidate.exists():
        return candidate

    # Try relative to CWD (workspace root)
    candidate = WORKSPACE_MANIFESTS_DIR / filename
    if candidate.exists():
        return candidate.resolve()

    # Try absolute path if manifest_id looks like a path
    candidate = Path(manifest_id)
    if candidate.exists():
        return candidate.resolve()

    raise FileNotFoundError(
        f"Manifest '{filename}' not found. Searched:\n"
        f"  - {MANIFESTS_DIR}\n"
        f"  - {WORKSPACE_MANIFESTS_DIR.resolve()}\n"
    )


def load_manifest(manifest_path: Path) -> dict:
    """Load and parse the YAML manifest. Uses simple YAML parsing (no PyYAML dependency)."""
    try:
        import yaml
        with open(manifest_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        # Fallback: minimal YAML parser for our simple manifest format
        return _parse_simple_yaml(manifest_path)


def _parse_simple_yaml(path: Path) -> dict:
    """Minimal YAML parser for the manifest format (no external deps)."""
    import re

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {"files": []}

    # Extract top-level scalar fields
    for match in re.finditer(r"^(manifest_id|version|description):\s*\"?([^\"\n]+)\"?", content, re.MULTILINE):
        result[match.group(1)] = match.group(2).strip().strip('"')

    # Extract file entries
    current_file = None
    for line in content.split("\n"):
        stripped = line.strip()

        if stripped.startswith("- path:"):
            if current_file:
                result["files"].append(current_file)
            path_val = stripped.split(":", 1)[1].strip().strip('"')
            current_file = {"path": path_val, "category": "", "blocking": True, "error_if_missing": "", "glob": False}

        elif current_file:
            if stripped.startswith("category:"):
                current_file["category"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("blocking:"):
                val = stripped.split(":", 1)[1].strip().lower()
                current_file["blocking"] = val == "true"
            elif stripped.startswith("error_if_missing:"):
                current_file["error_if_missing"] = stripped.split(":", 1)[1].strip().strip('"')
            elif stripped.startswith("glob:"):
                val = stripped.split(":", 1)[1].strip().lower()
                current_file["glob"] = val == "true"
            elif stripped.startswith("fallback_path:"):
                current_file["fallback_path"] = stripped.split(":", 1)[1].strip().strip('"')

    if current_file:
        result["files"].append(current_file)

    return result


def check_file_exists(root: Path, entry: dict) -> bool:
    """Check if a file exists, supporting glob patterns."""
    file_path = entry["path"]

    if entry.get("glob", False):
        # Use glob pattern matching
        pattern = str(root / file_path)
        matches = globmod.glob(pattern, recursive=True)
        if matches:
            return True
        # Try fallback_path if glob found nothing
        fallback = entry.get("fallback_path")
        if fallback:
            return (root / fallback).exists()
        return False
    else:
        return (root / file_path).exists()


def verify_scaffold(manifest_id: str, root_path: str) -> dict:
    """Main verification logic. Returns result dict."""
    # `.resolve()` desfaz o mapeamento `subst` que contorna MAX_PATH no
    # Windows (ver src/shared/tools/short_path_root.py). Caminho ja
    # absoluto passa intacto; so o relativo e resolvido.
    _bruto = Path(root_path)
    root = _bruto if _bruto.is_absolute() else _bruto.resolve()

    if not root.exists():
        return {
            "status": "FAIL",
            "manifest_id": manifest_id,
            "root": str(root),
            "error": f"Root directory does not exist: {root}",
            "total": 0,
            "found": 0,
            "missing": [],
            "blocking_missing": 0,
            "details": [],
        }

    # Load manifest
    manifest_path = find_manifest(manifest_id)
    manifest = load_manifest(manifest_path)

    files = manifest.get("files", [])
    details = []
    missing = []
    blocking_missing = 0
    found_count = 0

    for entry in files:
        exists = check_file_exists(root, entry)
        detail = {
            "path": entry["path"],
            "exists": exists,
            "blocking": entry.get("blocking", True),
            "category": entry.get("category", "unknown"),
        }
        details.append(detail)

        if exists:
            found_count += 1
        else:
            missing_entry = {
                "path": entry["path"],
                "blocking": entry.get("blocking", True),
                "error_if_missing": entry.get("error_if_missing", ""),
            }
            missing.append(missing_entry)
            if entry.get("blocking", True):
                blocking_missing += 1

    status = "PASS" if blocking_missing == 0 else "FAIL"

    return {
        "status": status,
        "manifest_id": manifest.get("manifest_id", manifest_id),
        "root": str(root),
        "total": len(files),
        "found": found_count,
        "missing": missing,
        "blocking_missing": blocking_missing,
        "details": details,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Verify scaffold file existence against a manifest."
    )
    parser.add_argument(
        "--manifest", required=True,
        help="Manifest ID (e.g., 'angular', 'dotnet') or path to manifest YAML"
    )
    parser.add_argument(
        "--root", required=True,
        help="Root directory of the generated project to verify"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Only output status line (no full JSON)"
    )

    args = parser.parse_args()

    try:
        result = verify_scaffold(args.manifest, args.root)
    except FileNotFoundError as e:
        error_result = {"status": "ERROR", "error": str(e)}
        print(json.dumps(error_result, indent=2))
        sys.exit(2)
    except Exception as e:
        error_result = {"status": "ERROR", "error": f"Unexpected error: {e}"}
        print(json.dumps(error_result, indent=2))
        sys.exit(2)

    if args.quiet:
        # Summary line only
        if result["status"] == "PASS":
            print(f"SCAFFOLD PASS — {result['found']}/{result['total']} files present")
        else:
            missing_paths = [m["path"] for m in result["missing"] if m["blocking"]]
            print(f"SCAFFOLD FAIL — {result['blocking_missing']} blocking files missing: {', '.join(missing_paths)}")
    else:
        print(json.dumps(result, indent=2))

    sys.exit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
