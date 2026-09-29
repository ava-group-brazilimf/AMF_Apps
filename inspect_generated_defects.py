#!/usr/bin/env python3
"""Inspect the three Mermaid rendering defects in the generated Summary HTML."""
from pathlib import Path

ROOT = Path(r"c:\_git\Fix\imfai-ava-fabric-apps-agents")
summary_dir = ROOT / "projects" / "MeuERP-001" / "outputs" / "summary"
html_path = sorted(summary_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)[0]

text = html_path.read_text(encoding="utf-8", errors="ignore")

offsets = [16213238, 16311241]
for off in offsets:
    print(f"\n{'='*80}\nOffset {off}\n{'='*80}")
    start = max(0, off - 500)
    end = min(len(text), off + 500)
    snippet = text[start:end]
    for i, line in enumerate(snippet.splitlines(keepends=True), start=1):
        marker = ">>> " if start + sum(len(l) for l in snippet.splitlines(keepends=True)[:i-1]) <= off < start + sum(len(l) for l in snippet.splitlines(keepends=True)[:i]) else "    "
        print(f"{marker}{start + sum(len(l) for l in snippet.splitlines(keepends=True)[:i-1]):>10}: {line}", end="")
