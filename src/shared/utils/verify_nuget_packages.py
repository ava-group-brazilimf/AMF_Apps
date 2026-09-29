#!/usr/bin/env python3
"""
verify_nuget_packages.py — Deterministic NuGet package duplicate checker.

Detects duplicate PackageReference entries between Directory.Build.props (or any
*.props imported at solution level) and individual *.csproj files. The most common
source of this problem is declaring an analyzer package such as
Microsoft.CodeAnalysis.NetAnalyzers in Directory.Build.props and then repeating it
in one or more .csproj files, which causes NU1504.

Usage:
    python src/shared/utils/verify_nuget_packages.py --root projects/MyProject/outputs/tobe/source-code/dotnet

Output (JSON to stdout):
    {
      "status": "PASS" | "FAIL" | "ERROR",
      "root": "/abs/path/to/dotnet",
      "central_props": ["Directory.Build.props", ...],
      "projects_checked": 5,
      "duplicates": [
        {
          "package": "Microsoft.CodeAnalysis.NetAnalyzers",
          "central_file": "Directory.Build.props",
          "project_file": "src/Shared/MyProject.Domain/MyProject.Domain.csproj"
        }
      ]
    }

Exit codes:
    0 — PASS (no duplicate package references)
    1 — FAIL (one or more duplicate package references)
    2 — ERROR (invalid args, unreadable XML, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"msbuild": "http://schemas.microsoft.com/developer/msbuild/2003"}


def _find_central_props(root: Path) -> list[Path]:
    """Return the central .props files that apply to all projects under root."""
    central: list[Path] = []
    candidates = ["Directory.Build.props", "Directory.Build.targets"]
    for name in candidates:
        path = root / name
        if path.is_file():
            central.append(path)
    return central


def _find_project_files(root: Path) -> list[Path]:
    """Return all SDK-style project files under root."""
    return sorted(root.rglob("*.csproj"))


def _parse_package_references(path: Path) -> set[str]:
    """Extract PackageReference/@Include values from an MSBuild file."""
    refs: set[str] = set()
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML in {path}: {exc}") from exc

    # Try with namespace first (legacy MSBuild format), then without.
    for package_ref in tree.iter(f"{{{NS['msbuild']}}}PackageReference"):
        include = package_ref.get("Include")
        if include:
            refs.add(include.strip())
    for package_ref in tree.iter("PackageReference"):
        include = package_ref.get("Include")
        if include:
            refs.add(include.strip())
    return refs


def verify_nuget_packages(root_path: str) -> dict:
    """Main verification logic. Returns result dict."""
    # `.resolve()` desfaz o mapeamento `subst` que contorna MAX_PATH no
    # Windows (ver src/shared/tools/short_path_root.py). Caminho ja
    # absoluto passa intacto; so o relativo e resolvido.
    _bruto = Path(root_path)
    root = _bruto if _bruto.is_absolute() else _bruto.resolve()

    if not root.exists():
        return {
            "status": "ERROR",
            "root": str(root),
            "error": f"Root directory does not exist: {root}",
            "central_props": [],
            "projects_checked": 0,
            "duplicates": [],
        }

    if not root.is_dir():
        return {
            "status": "ERROR",
            "root": str(root),
            "error": f"Root path is not a directory: {root}",
            "central_props": [],
            "projects_checked": 0,
            "duplicates": [],
        }

    central_files = _find_central_props(root)
    central_refs: dict[str, str] = {}
    for central in central_files:
        try:
            for ref in _parse_package_references(central):
                central_refs[ref] = central.name
        except ValueError as exc:
            return {
                "status": "ERROR",
                "root": str(root),
                "error": str(exc),
                "central_props": [c.name for c in central_files],
                "projects_checked": 0,
                "duplicates": [],
            }

    projects = _find_project_files(root)
    duplicates: list[dict] = []

    for project in projects:
        try:
            project_refs = _parse_package_references(project)
        except ValueError as exc:
            return {
                "status": "ERROR",
                "root": str(root),
                "error": str(exc),
                "central_props": [c.name for c in central_files],
                "projects_checked": len(projects),
                "duplicates": duplicates,
            }

        for ref in project_refs:
            if ref in central_refs:
                duplicates.append(
                    {
                        "package": ref,
                        "central_file": central_refs[ref],
                        "project_file": project.relative_to(root).as_posix(),
                    }
                )

    status = "FAIL" if duplicates else "PASS"
    return {
        "status": status,
        "root": str(root),
        "central_props": [c.name for c in central_files],
        "projects_checked": len(projects),
        "duplicates": duplicates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify no duplicate PackageReference between central .props and .csproj files."
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Root directory of the generated .NET project to verify",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output status line (no full JSON)",
    )

    args = parser.parse_args()

    result = verify_nuget_packages(args.root)

    if args.quiet:
        if result["status"] == "PASS":
            print(
                f"NUGET PACKAGES PASS — {result['projects_checked']} projects checked, "
                "no duplicate PackageReference"
            )
        elif result["status"] == "FAIL":
            packages = sorted({d["package"] for d in result["duplicates"]})
            print(
                f"NUGET PACKAGES FAIL — {len(packages)} duplicate package(s): "
                f"{', '.join(packages)}"
            )
        else:
            print(f"NUGET PACKAGES ERROR — {result.get('error', 'unknown error')}")
    else:
        print(json.dumps(result, indent=2))

    if result["status"] == "ERROR":
        return 2
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
