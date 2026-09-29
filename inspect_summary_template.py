#!/usr/bin/env python3
"""Inspect the summary template around known Mermaid rendering defects."""
from pathlib import Path
import re

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

text = TEMPLATE.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

print(f"Total lines: {len(lines)} | Size: {len(text)} bytes")
print(f"File: {TEMPLATE}\n")

# Find seqContent
for i, line in enumerate(lines):
    if "seqContent" in line or "renderMmdBlocks" in line or 'class="mermaid"' in line:
        print(f"--- line {i+1}: {line.rstrip()[:200]}")

print("\n=== SNIPPET around seqContent ===")
for i, line in enumerate(lines):
    if "seqContent" in line:
        start = max(0, i - 15)
        end = min(len(lines), i + 15)
        for j in range(start, end):
            marker = ">>> " if j == i else "    "
            print(f"{marker}{j+1:4}: {lines[j]}", end="")
        print("\n---")

print("\n=== EMPTY <pre class=\"mermaid\"> containers ===")
for i, line in enumerate(lines):
    if re.search(r'<pre\s+class=["\']mermaid["\'][^>]*>\s*</pre>', line, re.IGNORECASE):
        print(f"line {i+1}: {line.rstrip()[:200]}")

print("\n=== <pre class=\"mermaid\"> with comment-like content ===")
for i, line in enumerate(lines):
    if re.search(r'<pre\s+class=["\']mermaid["\']', line, re.IGNORECASE):
        next_lines = "".join(lines[i+1:i+6])
        if re.search(r'^\s*(/\*|\*\*)', next_lines, re.MULTILINE):
            print(f"line {i+1}: {line.rstrip()[:200]}")
            for j in range(i, min(len(lines), i+8)):
                print(f"    {j+1}: {lines[j]}", end="")
            print("---")
