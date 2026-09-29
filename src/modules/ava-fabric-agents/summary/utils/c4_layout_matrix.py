"""Minimal C4Component relationship compatibility matrix runner."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from render_blueprint_compatibility import execute_probe, sanitize_c4_source

CASES = [
    ("Component", "Component", 'Component(target, "Target", "Runtime", "Target")'),
    ("Component", "System_Ext", 'System_Ext(target, "External System", "Target")'),
    ("Component", "Container_Ext", 'Container_Ext(target, "External Container", "Runtime", "Target")'),
    ("Component", "Person_Ext", 'Person_Ext(target, "External Person", "Target")'),
    ("Component", "System", 'System(target, "Internal System", "Target")'),
]


def source_for(target_declaration: str, label: str) -> str:
    return f'''C4Component
  title {label}
  Container_Boundary(app, "Application") {{
    Component(source, "Source", "Runtime", "Source component")
  }}
  {target_declaration}
  Rel(source, target, "{label}", "HTTPS")
'''


def run(repo_root: str | Path) -> dict:
    rows = []
    for source_type, target_type, declaration in CASES:
        source = sanitize_c4_source(source_for(declaration, f"{source_type} to {target_type}"))
        result = execute_probe(repo_root, source)
        rows.append({
            "sourceType": source_type,
            "targetType": target_type,
            "renderStatus": result.get("renderStatus"),
            "runtimeRenderSucceeded": result.get("runtimeRenderSucceeded", False),
            "rendererVersion": result.get("rendererVersion", ""),
            "error": result.get("error"),
            "stack": result.get("stack", ""),
            "rootCause": result.get("rootCause"),
            "stage": result.get("stage"),
        })
    defect = any(row["rootCause"] == "RENDERING_FAILURE" and "getIntersectPoints" in row["stack"] for row in rows)
    return {
        "diagramType": "C4Component",
        "runtime": "Summary Mermaid bundle via Playwright Chromium",
        "cases": rows,
        "rendererDefectConfirmed": defect,
        "rootCause": "MERMAID_C4_RENDERER_DEFECT" if defect else "NOT_CONFIRMED",
        "recommendedRemediation": "SEGMENT_C4_COMPONENT" if defect else "NONE",
        "publicationAllowed": not defect and all(row["renderStatus"] == "PASS" for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run(args.repo_root)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["publicationAllowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
