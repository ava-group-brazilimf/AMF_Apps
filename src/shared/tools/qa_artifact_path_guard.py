"""
qa_artifact_path_guard.py — Deterministic Output Contract path checker for QA agents.

Problem: completion gates described in agent specs as prose/pseudocode
("Verificar X", loose Glob) get interpreted loosely by the LLM executing them,
so an artifact written to the wrong path (but findable by a broader search)
is silently accepted as present. This tool replaces that prose check with a
real command: it validates the *exact* paths declared in an agent's Output
Contract and fails loudly when they are not honored.

Usage:
  # Exact path(s) must exist
  python src/shared/tools/qa_artifact_path_guard.py -p Meu-ERP-001 check \\
      --agent ava-qa-bridge-fastqa-tobe \\
      --exact "outputs/qa/scenario-generator/scenario-register.json" \\
      --exact "outputs/qa/scenario-generator-report.md"

  # Glob pattern must match at least N files
  python src/shared/tools/qa_artifact_path_guard.py -p Meu-ERP-001 check \\
      --agent ava-qa-script-generator \\
      --glob-min "outputs/qa/parity-evidence/*.json" 1

Exit code 0 + "✅ ALL PATHS OK" when every check passes.
Exit code 1 + one "❌ MISSING: {path}" / "❌ GLOB_MIN_NOT_MET: {pattern} (found {n}, need {min})"
line per failure.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent


def _project_dir(project_name: str) -> Path:
    return PROJECT_ROOT / "projects" / project_name


def check(project_name: str, agent: str, exact_paths: list[str], glob_min: list[tuple[str, int]]) -> int:
    base = _project_dir(project_name)
    failures: list[str] = []

    for rel_path in exact_paths:
        target = base / rel_path
        if not target.is_file() or target.stat().st_size == 0:
            failures.append(f"❌ MISSING: {rel_path}")

    for pattern, minimum in glob_min:
        matches = list(base.glob(pattern))
        if len(matches) < minimum:
            failures.append(f"❌ GLOB_MIN_NOT_MET: {pattern} (found {len(matches)}, need {minimum})")

    print(f"── qa_artifact_path_guard — agent={agent} project={project_name} ──")
    if failures:
        for line in failures:
            print(line)
        print(f"RESULT: FAIL ({len(failures)} issue(s))")
        return 1

    print("✅ ALL PATHS OK")
    print("RESULT: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-p", "--project", required=True, help="Project name under projects/")
    sub = parser.add_subparsers(dest="command", required=True)

    check_cmd = sub.add_parser("check", help="Validate Output Contract paths for an agent")
    check_cmd.add_argument("--agent", required=True, help="Agent id (for log context only)")
    check_cmd.add_argument(
        "--exact", action="append", default=[], metavar="PATH",
        help="Exact relative path (from projects/{project}/) that must exist and be non-empty. Repeatable.",
    )
    check_cmd.add_argument(
        "--glob-min", nargs=2, action="append", default=[], metavar=("PATTERN", "N"),
        help="Glob pattern (relative to projects/{project}/) that must match at least N files. Repeatable.",
    )

    args = parser.parse_args()

    if args.command == "check":
        glob_min = [(pattern, int(n)) for pattern, n in args.glob_min]
        return check(args.project, args.agent, args.exact, glob_min)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
