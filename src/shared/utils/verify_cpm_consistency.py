#!/usr/bin/env python3
"""
verify_cpm_consistency.py — Deterministic Central Package Management (CPM) consistency checker.

Verifies that, when Directory.Packages.props declares
ManagePackageVersionsCentrally=true, every PackageReference in every *.csproj
under the root has a matching PackageVersion entry in Directory.Packages.props.

This prevents build errors such as:
    NU1009: The packages PackageId are implicitly referenced. You do not typically need to reference them.
    NU1101: Unable to find package PackageId. No packages exist with this id...
    CS1061: 'Type' does not contain a definition for 'ExtensionMethod'...
      (when the extension method's package is missing from CPM and therefore not restored)

Usage:
    python src/shared/utils/verify_cpm_consistency.py --root projects/MyProject/outputs/tobe/source-code/dotnet

Output (JSON to stdout):
    {
      "status": "PASS" | "FAIL" | "ERROR" | "SKIPPED",
      "root": "/abs/path/to/dotnet",
      "cpm_enabled": true | false,
      "central_packages_file": "Directory.Packages.props" | null,
      "projects_checked": 5,
      "missing_versions": [
        {
          "package": "Serilog.Enrichers.CorrelationId",
          "project_file": "src/Host/MyProject.API/MyProject.API.csproj"
        }
      ]
    }

Exit codes:
    0 — PASS or SKIPPED (CPM not enabled; nothing to verify)
    1 — FAIL (one or more PackageReference entries lack a PackageVersion in CPM)
    2 — ERROR (invalid args, unreadable XML, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"msbuild": "http://schemas.microsoft.com/developer/msbuild/2003"}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Central Package Management consistency for .NET projects."
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Root directory containing Directory.Packages.props and *.csproj files.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the JSON result or a short message.",
    )
    return parser.parse_args()


def _find_central_packages_file(root: Path) -> Path | None:
    """Return Directory.Packages.props if it exists under root."""
    candidate = root / "Directory.Packages.props"
    return candidate if candidate.is_file() else None


def _cpm_enabled(props_path: Path) -> bool:
    """Return True if Directory.Packages.props enables CPM."""
    try:
        tree = ET.parse(props_path)
    except ET.ParseError:
        return False
    root = tree.getroot()
    for prop_group in root.findall("msbuild:PropertyGroup", NS) or root.findall("PropertyGroup"):
        for prop in prop_group:
            tag = prop.tag.split("}")[-1] if prop.tag.startswith("{") else prop.tag
            if tag == "ManagePackageVersionsCentrally":
                value = (prop.text or "").strip().lower()
                return value in ("true", "1")
    return False


def _read_package_versions(props_path: Path) -> set[str]:
    """Return the set of package IDs declared as PackageVersion in CPM file."""
    package_versions: set[str] = set()
    try:
        tree = ET.parse(props_path)
    except ET.ParseError as exc:
        raise RuntimeError(f"Cannot parse {props_path}: {exc}") from exc

    root = tree.getroot()
    item_groups = root.findall("msbuild:ItemGroup", NS) or root.findall("ItemGroup")
    for item_group in item_groups:
        for package_version in item_group:
            tag = package_version.tag.split("}")[-1] if package_version.tag.startswith("{") else package_version.tag
            if tag != "PackageVersion":
                continue
            include = package_version.get("Include")
            if include:
                package_versions.add(include.strip())
    return package_versions


def _find_project_files(root: Path) -> list[Path]:
    """Return all SDK-style project files under root."""
    return sorted(root.rglob("*.csproj"))


def _read_package_references(project_path: Path) -> list[str]:
    """Return the list of PackageReference Include values in a project file."""
    references: list[str] = []
    try:
        tree = ET.parse(project_path)
    except ET.ParseError as exc:
        raise RuntimeError(f"Cannot parse {project_path}: {exc}") from exc

    root = tree.getroot()
    item_groups = root.findall("msbuild:ItemGroup", NS) or root.findall("ItemGroup")
    for item_group in item_groups:
        for package_ref in item_group:
            tag = package_ref.tag.split("}")[-1] if package_ref.tag.startswith("{") else package_ref.tag
            if tag != "PackageReference":
                continue
            include = package_ref.get("Include")
            if include:
                references.append(include.strip())
    return references


def verify_cpm_consistency(root: Path) -> dict:
    """Run the CPM consistency check and return a result dictionary."""
    result: dict = {
        "status": "SKIPPED",
        "root": str(root.resolve()),
        "cpm_enabled": False,
        "central_packages_file": None,
        "projects_checked": 0,
        "missing_versions": [],
    }

    central_file = _find_central_packages_file(root)
    if central_file is None:
        return result

    result["central_packages_file"] = central_file.name

    if not _cpm_enabled(central_file):
        return result

    result["cpm_enabled"] = True

    try:
        central_packages = _read_package_versions(central_file)
        project_files = _find_project_files(root)
        result["projects_checked"] = len(project_files)

        for project_path in project_files:
            package_refs = _read_package_references(project_path)
            for package in package_refs:
                if package not in central_packages:
                    result["missing_versions"].append({
                        "package": package,
                        "project_file": str(project_path.relative_to(root)).replace("\\", "/"),
                    })
    except RuntimeError as exc:
        result["status"] = "ERROR"
        result["error"] = str(exc)
        return result

    if result["missing_versions"]:
        result["status"] = "FAIL"
    else:
        result["status"] = "PASS"

    return result


def main() -> int:
    args = _parse_args()
    root = Path(args.root)

    if not root.is_dir():
        print(json.dumps({
            "status": "ERROR",
            "root": str(root),
            "error": f"Root directory does not exist: {root}",
        }), file=sys.stdout)
        return 2

    result = verify_cpm_consistency(root)

    if args.quiet:
        if result["status"] == "PASS":
            print("OK")
        elif result["status"] == "SKIPPED":
            print("SKIPPED")
        else:
            print(f"{result['status']}: {len(result.get('missing_versions', []))} missing")
    else:
        print(json.dumps(result, indent=2))

    if result["status"] == "ERROR":
        return 2
    if result["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
