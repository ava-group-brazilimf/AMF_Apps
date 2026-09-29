#!/usr/bin/env python3
"""Deterministic scaffold output-path guardrail.

Verifies that generated source code is written to the canonical location
``projects/{project_name}/outputs/tobe/source-code/{stack}/`` and detects
common LLM/agent path hallucinations such as:

* ``outputs/tobe/frontend/`` or ``outputs/tobe/backend/`` (legacy paths)
* project-named folders like ``outputs/tobe/source-code/<name>-spa/``
* stray project-named folders directly under ``outputs/tobe/``

The tool is framework-agnostic: the caller supplies the allowed stack names
and the canonical root. It can run in ``check`` mode (fail fast) or ``fix``
mode (move misplaced folders to the expected location).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


def _fail(message: str) -> None:
    print(f"[verify-scaffold-paths] ERROR: {message}", file=sys.stderr)


def _resolve_project_root(project_name: str, workspace: Path | None) -> Path:
    """Resolve ``projects/{project_name}/outputs/tobe`` relative to workspace."""
    if workspace is None:
        workspace = Path(__file__).resolve().parents[3]
    return workspace / "projects" / project_name / "outputs" / "tobe"


def _is_expected_stack_folder(name: str, allowed_stacks: set[str]) -> bool:
    return name in allowed_stacks


def _looks_like_project_named_folder(name: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return True
    return False


def _detect_violations(
    tobe_root: Path,
    allowed_stacks: set[str],
    forbidden_root_names: set[str],
    project_named_patterns: list[str],
) -> list[dict[str, Any]]:
    """Return a list of path violations under ``tobe_root``."""
    violations: list[dict[str, Any]] = []

    if not tobe_root.exists():
        return violations

    source_code_root = tobe_root / "source-code"

    # 1. Forbidden top-level directories (legacy paths)
    for name in forbidden_root_names:
        path = tobe_root / name
        if path.exists() and path.is_dir():
            violations.append(
                {
                    "type": "forbidden_top_level_directory",
                    "path": str(path),
                    "reason": f"'{name}' is a legacy output path; generated code must live under source-code/<stack>/",
                    "suggested_fix": str(source_code_root / name),
                }
            )

    # 2. Misplaced project-named folders directly under tobe/
    for child in tobe_root.iterdir():
        if child.is_dir() and child.name not in forbidden_root_names and child.name != "source-code":
            if _looks_like_project_named_folder(child.name, project_named_patterns):
                violations.append(
                    {
                        "type": "project_named_top_level_folder",
                        "path": str(child),
                        "reason": "project-named folder detected at top level; generated code must live under source-code/<stack>/",
                        "suggested_fix": str(source_code_root / "frontend"),
                    }
                )

    if not source_code_root.exists():
        return violations

    # 3. Unexpected folders inside source-code/
    for child in source_code_root.iterdir():
        if not child.is_dir():
            continue
        if _is_expected_stack_folder(child.name, allowed_stacks):
            continue
        if _looks_like_project_named_folder(child.name, project_named_patterns):
            violations.append(
                {
                    "type": "project_named_source_code_folder",
                    "path": str(child),
                    "reason": f"project-named folder '{child.name}' inside source-code/ does not match allowed stacks: {sorted(allowed_stacks)}",
                    "suggested_fix": str(source_code_root / "frontend"),
                }
            )
        else:
            violations.append(
                {
                    "type": "unexpected_source_code_folder",
                    "path": str(child),
                    "reason": f"folder '{child.name}' inside source-code/ does not match allowed stacks: {sorted(allowed_stacks)}",
                    "suggested_fix": None,
                }
            )

    return violations


def _apply_fix(violations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Move fixable violations to their suggested location."""
    results: list[dict[str, Any]] = []
    for v in violations:
        if not v.get("suggested_fix"):
            results.append({**v, "fix_status": "skipped_no_suggested_fix"})
            continue
        src = Path(v["path"])
        dst = Path(v["suggested_fix"])
        if not src.exists():
            results.append({**v, "fix_status": "skipped_source_missing"})
            continue
        if dst.exists():
            results.append({**v, "fix_status": "skipped_target_exists"})
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            results.append({**v, "fix_status": "moved"})
        except Exception as exc:  # noqa: BLE001
            results.append({**v, "fix_status": "failed", "fix_error": str(exc)})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify generated scaffold/source-code is written to the canonical path."
    )
    parser.add_argument("--project", required=True, help="Project name (kebab-case).")
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Repository root. Defaults to the repo containing this script.",
    )
    parser.add_argument(
        "--allowed-stacks",
        default="frontend,backend,dotnet,angular,react,vue,blazor,spring-boot,fastapi,gin,nestjs",
        help="Comma-separated list of allowed stack folder names under source-code/.",
    )
    parser.add_argument(
        "--forbidden-root-names",
        default="frontend,backend",
        help="Comma-separated list of forbidden top-level directory names under tobe/.",
    )
    parser.add_argument(
        "--project-named-patterns",
        default=r"-(spa|app|ui|web|client|fe|site)$",
        help="Regex patterns (comma-separated) used to flag project-named folders.",
    )
    parser.add_argument(
        "--mode",
        choices=["check", "fix"],
        default="check",
        help="check = report and exit non-zero; fix = move misplaced folders.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable text.",
    )
    args = parser.parse_args(argv)

    tobe_root = _resolve_project_root(args.project, args.workspace)
    allowed_stacks = {s.strip() for s in args.allowed_stacks.split(",") if s.strip()}
    forbidden_root_names = {s.strip() for s in args.forbidden_root_names.split(",") if s.strip()}
    project_named_patterns = [p.strip() for p in args.project_named_patterns.split(",") if p.strip()]

    violations = _detect_violations(
        tobe_root, allowed_stacks, forbidden_root_names, project_named_patterns
    )

    if args.mode == "fix":
        violations = _apply_fix(violations)

    if args.json:
        print(json.dumps({"tobe_root": str(tobe_root), "violations": violations}, indent=2))
    else:
        if not violations:
            print(f"[verify-scaffold-paths] OK: no path violations under {tobe_root}")
        else:
            print(f"[verify-scaffold-paths] FOUND {len(violations)} violation(s) under {tobe_root}:")
            for v in violations:
                fix_note = ""
                if args.mode == "fix":
                    fix_note = f" [fix: {v.get('fix_status', 'n/a')}]"
                print(f"  - {v['type']}: {v['path']}")
                print(f"    {v['reason']}{fix_note}")

    return 0 if not violations or all(v.get("fix_status") == "moved" for v in violations) else 1


if __name__ == "__main__":
    raise SystemExit(main())
