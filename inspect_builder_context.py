#!/usr/bin/env python3
from pathlib import Path

BUILDER = (
    Path(r"c:\_git\Fix\imfai-ava-fabric-apps-agents")
    / "src"
    / "modules"
    / "ava-fabric-agents"
    / "summary"
    / "utils"
    / "build_summary_comprehensive.py"
)

lines = BUILDER.read_text(encoding="utf-8").splitlines(keepends=True)

def show(title, center, radius=30):
    print(f"\n{'='*80}\n{title}\n{'='*80}")
    start = max(0, center - 1 - radius)
    end = min(len(lines), center - 1 + radius)
    for i in range(start, end):
        marker = ">>> " if i == center - 1 else "    "
        print(f"{marker}{i+1:5}: {lines[i]}", end="")

# Find _build_seq_panels_html
for i, line in enumerate(lines):
    if "def _build_seq_panels_html" in line:
        show("_build_seq_panels_html", i+1, 50)
        break

# Find renderAllDiagrams / diagram population logic
for i, line in enumerate(lines):
    if "renderAllDiagrams" in line or "staticDiagrams" in line or "SEQ_PANELS_HTML" in line:
        show(f"Keyword match: {line.strip()[:60]}", i+1, 25)

# Find where template is read
for i, line in enumerate(lines):
    if "summary-template.html" in line or ".read_text" in line or "template" in line.lower():
        show(f"Template handling: {line.strip()[:60]}", i+1, 15)
