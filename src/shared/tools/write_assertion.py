#!/usr/bin/env python3
"""Generic completeness assertion writer for AVA Fabric artifacts.

Usage:
    python src/shared/tools/write_assertion.py \
        --project {project_name} \
        --artifact {screen-flow|er-diagram|...} \
        --status {PASS|FAIL} \
        --coverage {coverage_pct} \
        --nodes {N_nodes} \
        --registry {N_registry} \
        [--missing-items "item1,item2,..."] \
        [--threshold 80] \
        [--retry-count 0] \
        --output projects/{project_name}/outputs/asis/docs/{artifact}-completeness.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "1.0.0"
DEFAULT_THRESHOLD = 80


def main():
    parser = argparse.ArgumentParser(description="Write a completeness assertion JSON.")
    parser.add_argument("--project", required=True, help="Project name (kebab-case).")
    parser.add_argument("--artifact", required=True, help="Artifact identifier, e.g. screen-flow or er-diagram.")
    parser.add_argument("--status", required=True, choices=["PASS", "FAIL"], help="Assertion status.")
    parser.add_argument("--coverage", required=True, type=float, help="Coverage percentage (0-100).")
    parser.add_argument("--nodes", required=True, type=int, help="Number of nodes/entities found in the diagram.")
    parser.add_argument("--registry", required=True, type=int, help="Number of items in the source registry.")
    parser.add_argument("--missing-items", default="", help="Comma-separated list of missing item identifiers.")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="Pass threshold percentage.")
    parser.add_argument("--retry-count", type=int, default=0, help="Number of retries already attempted.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    args = parser.parse_args()

    missing = [m.strip() for m in args.missing_items.split(",") if m.strip()] if args.missing_items else []

    assertion = {
        "assertion_id": f"{args.artifact}-completeness",
        "version": SCHEMA_VERSION,
        "project_name": args.project,
        "artifact": args.artifact,
        "status": args.status,
        "threshold_pct": args.threshold,
        "coverage_pct": round(args.coverage, 2),
        "N_nodes": args.nodes,
        "N_registry": args.registry,
        "missing_items": missing,
        "missing_count": len(missing),
        "retry_count": args.retry_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(assertion, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[write_assertion] {args.artifact}: {args.status} ({assertion['coverage_pct']}% coverage) -> {out_path}")
    sys.exit(0 if args.status == "PASS" else 1)


if __name__ == "__main__":
    main()
