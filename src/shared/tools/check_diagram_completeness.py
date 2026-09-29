#!/usr/bin/env python3
"""Check diagram completeness against a registry and emit an assertion JSON.

Supports:
  --type screen-flow : flowchart TD with nodes like N_id["label"]
  --type er-diagram  : erDiagram with entities like ENTITY { ... }

Usage:
    python src/shared/tools/check_diagram_completeness.py \
        --type {screen-flow|er-diagram} \
        --project {project_name} \
        --diagram projects/{project_name}/outputs/asis/docs/screen-flow.mmd \
        --registry projects/{project_name}/outputs/asis/.internal/form-registry.json \
        --output projects/{project_name}/outputs/asis/docs/screen-flow-completeness.json \
        [--threshold 80]
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def count_flowchart_nodes(content):
    """Return unique node IDs in a flowchart TD/LR diagram.

    Nodes may be declared explicitly (N_id["label"]) or referenced only in edges
    (A --> B). Subgraph declarations, styles, classes and comments are ignored.
    """
    node_ids = set()
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if stripped.startswith(("flowchart ", "graph ", "subgraph", "end", "style", "classDef", "class ", "click ", "direction ")):
            continue
        # Explicit declaration: ID["label"] or ID[(label)] or ID{...} etc.
        m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*["\[(\{<]', stripped)
        if m:
            node_ids.add(m.group(1))
            continue
        # Edge statement: source --> target
        m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*[-=.]+[->]', stripped)
        if m:
            node_ids.add(m.group(1))
        for target in re.findall(r'[-=.]+[->]\s*([A-Za-z_][A-Za-z0-9_]*)', stripped):
            node_ids.add(target)
    return node_ids


def count_er_entities(content):
    """Return unique entity declarations in an erDiagram."""
    entities = set()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("%%") or stripped.startswith("erDiagram"):
            continue
        m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*\{', stripped)
        if m:
            entities.add(m.group(1))
    return entities


def _registry_items(data, registry_type):
    """Return raw item dicts/lists from a registry payload."""
    if registry_type == "screen-flow":
        payload = data.get("payload", data)
        if isinstance(payload, dict):
            items = payload.get("forms", []) or payload.get("tables", [])
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        return items
    elif registry_type == "er-diagram":
        payload = data.get("payload", data)
        if isinstance(payload, dict):
            items = payload.get("tables", []) + payload.get("inferred_tables", [])
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        return items
    raise ValueError(f"Unknown registry type: {registry_type}")


def _item_id(item, registry_type):
    """Normalize a registry item into the same ID space used by the diagram scripts.

    screen-flow node IDs are prefixed with N_ by gen_screen_flow.py.
    er-diagram entity IDs use the sanitized table name directly.
    """
    if isinstance(item, str):
        name = item
    elif isinstance(item, dict):
        if registry_type == "screen-flow":
            name = item.get("form_name") or item.get("form_id") or item.get("Name") or item.get("name", "")
        else:
            name = item.get("name") or item.get("Name", "")
    else:
        name = str(item)
    prefix = "N_" if registry_type == "screen-flow" else ""
    return (prefix + re.sub(r'[^A-Za-z0-9_]', '_', str(name)))[:55]


def registry_ids(registry_path, registry_type):
    """Return normalized IDs for every item in the registry."""
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return {_item_id(item, registry_type) for item in _registry_items(data, registry_type)}


def main():
    parser = argparse.ArgumentParser(description="Check diagram completeness against a registry.")
    parser.add_argument("--type", required=True, choices=["screen-flow", "er-diagram"], help="Diagram type.")
    parser.add_argument("--project", required=True, help="Project name.")
    parser.add_argument("--diagram", required=True, type=Path, help="Path to the main .mmd file.")
    parser.add_argument("--registry", required=True, type=Path, help="Path to the registry JSON file.")
    parser.add_argument("--output", required=True, type=Path, help="Output assertion JSON path.")
    parser.add_argument("--threshold", type=int, default=80, help="Coverage pass threshold.")
    args = parser.parse_args()

    if not args.diagram.exists():
        print(f"ERROR: Diagram not found: {args.diagram}", file=sys.stderr)
        sys.exit(1)
    if not args.registry.exists():
        print(f"ERROR: Registry not found: {args.registry}", file=sys.stderr)
        sys.exit(1)

    diagram_dir = args.diagram.parent
    stem = args.diagram.stem
    manifest_path = diagram_dir / f"{stem}-manifest.json"

    # Aggregate node/entity IDs across the main diagram and all detail files
    # listed in the manifest. Detail files cover lower-level subgroups; the
    # overview only contains synthetic BC nodes and is excluded from coverage.
    found_ids: set[str] = set()
    if args.type == "screen-flow":
        found_ids = count_flowchart_nodes(args.diagram.read_text(encoding="utf-8"))
    else:
        found_ids = count_er_entities(args.diagram.read_text(encoding="utf-8"))

    detail_files = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        detail_files = [
            entry["file"]
            for entry in manifest.get("generated_files", [])
            if entry.get("file", "").endswith(".mmd") and entry.get("file") != args.diagram.name
        ]

    for fname in detail_files:
        fpath = diagram_dir / fname
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")
        if args.type == "screen-flow":
            found_ids.update(count_flowchart_nodes(content))
        else:
            found_ids.update(count_er_entities(content))

    reg_ids = registry_ids(args.registry, args.type)
    matched_ids = found_ids & reg_ids
    n_nodes = len(found_ids)
    n_matched = len(matched_ids)
    n_registry = len(reg_ids)
    coverage = (n_matched / n_registry * 100) if n_registry else 0.0
    status = "PASS" if coverage >= args.threshold else "FAIL"
    missing = sorted(reg_ids - found_ids)

    writer = Path(__file__).resolve().parent / "write_assertion.py"
    cmd = [
        sys.executable,
        str(writer),
        "--project", args.project,
        "--artifact", args.type,
        "--status", status,
        "--coverage", str(round(coverage, 2)),
        "--nodes", str(n_nodes),
        "--registry", str(n_registry),
        "--threshold", str(args.threshold),
        "--output", str(args.output),
    ]
    if missing:
        cmd.extend(["--missing-items", ",".join(missing)])
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
