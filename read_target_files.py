#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(r"c:\_git\Fix\imfai-ava-fabric-apps-agents")
BUILDER = ROOT / "src" / "modules" / "ava-fabric-agents" / "summary" / "utils" / "build_summary_comprehensive.py"
TEMPLATE = ROOT / "src" / "modules" / "ava-fabric-agents" / "summary" / "templates" / "html" / "summary-template.html"

for label, path in [("BUILDER", BUILDER), ("TEMPLATE", TEMPLATE)]:
    print(f"\n\n{'='*80}")
    print(f"{label}: {path}")
    print(f"{'='*80}")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    for kw in ["SEQ_PANELS_HTML", "diag-tobe-c4ctx-detail", "renderMmdBlocks", "mermaid.run", "seqContent", "staticDiagrams"]:
        print(f"\n--- occurrences of '{kw}' ---")
        for i, line in enumerate(lines, 1):
            if kw in line:
                print(f"{i:>5}: {line.rstrip()[:220]}")
