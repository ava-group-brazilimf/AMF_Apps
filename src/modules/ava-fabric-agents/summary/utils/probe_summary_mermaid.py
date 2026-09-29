"""CLI diagnostic for executing the exact Summary Mermaid runtime probe."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from render_blueprint_compatibility import execute_probe, inspect_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source", required=True)
    parser.add_argument("--runner", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    source_path = Path(args.source)
    source = source_path.read_text(encoding="utf-8", errors="replace")
    result = execute_probe(args.repo_root, source, runner=args.runner)
    if not result.get("probeExecuted") and result.get("rendererVersion") == "":
        result.update(inspect_bundle(args.repo_root))
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if result.get("rendererVersion") else 1


if __name__ == "__main__":
    raise SystemExit(main())
