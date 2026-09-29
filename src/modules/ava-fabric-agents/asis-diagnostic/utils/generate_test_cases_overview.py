#!/usr/bin/env python3
"""
generate_test_cases_overview.py

CLI wrapper for build_test_cases_overview().
Generates projects/{project_name}/outputs/asis/qa/test-cases-overview.md.
Always overwrites the output file.

Usage:
    python generate_test_cases_overview.py --project <project_name>
"""
import sys
import argparse
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR.parent.parent / "summary" / "utils"))

from build_summary_comprehensive import build_test_cases_overview  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate test-cases-overview.md from test-cases.md"
    )
    ap.add_argument("--project", required=True, help="Project name (e.g. processaERP)")
    args = ap.parse_args()

    asis_dir = Path("projects") / args.project / "outputs" / "asis"
    if not (asis_dir / "qa" / "test-cases.md").exists():
        print(f"[ERROR] test-cases.md not found at {asis_dir / 'qa' / 'test-cases.md'}")
        return 1

    content = build_test_cases_overview(asis_dir)
    if content:
        print(f"[OK] test-cases-overview.md generated")
        print(f"     Output: {asis_dir / 'qa' / 'test-cases-overview.md'}")
        return 0
    print(f"[ERROR] build_test_cases_overview() returned empty — check test-cases.md format")
    return 2


if __name__ == "__main__":
    sys.exit(main())
