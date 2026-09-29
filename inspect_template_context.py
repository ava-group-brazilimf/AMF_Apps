#!/usr/bin/env python3
from pathlib import Path

TEMPLATE = (
    Path(r"c:\_git\Fix\imfai-ava-fabric-apps-agents")
    / "src"
    / "modules"
    / "ava-fabric-agents"
    / "summary"
    / "templates"
    / "html"
    / "summary-template.html"
)

lines = TEMPLATE.read_text(encoding="utf-8").splitlines(keepends=True)

def show(title, center, radius=25):
    print(f"\n{'='*80}\n{title}\n{'='*80}")
    start = max(0, center - 1 - radius)
    end = min(len(lines), center - 1 + radius)
    for i in range(start, end):
        marker = ">>> " if i == center - 1 else "    "
        print(f"{marker}{i+1:5}: {lines[i]}", end="")

show("Context around JSDoc / renderMmdBlocks (line ~6890)", 6890, 30)
show("Context around empty TO-BE containers (line ~3704)", 3704, 40)
show("Context around seqContent fallback (line ~8702)", 8702, 30)
