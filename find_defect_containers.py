#!/usr/bin/env python3
"""Find which <pre class="mermaid"> containers contain the JS source defects."""
from pathlib import Path
import re

ROOT = Path(r"c:\_git\Fix\imfai-ava-fabric-apps-agents")
summary_dir = ROOT / "projects" / "MeuERP-001" / "outputs" / "summary"
html_path = sorted(summary_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)[0]

text = html_path.read_text(encoding="utf-8", errors="ignore")

# Find all <pre class="mermaid"> blocks
pre_pattern = re.compile(
    r'<pre\s+class="mermaid"(?:\s+id="([^"]+)")?[^>]*>(.*?)</pre>',
    re.DOTALL | re.IGNORECASE,
)

print("=== Searching for defect markers inside <pre class=\"mermaid\"> ===\n")
for m in pre_pattern.finditer(text):
    pre_id = m.group(1) or "(no id)"
    content = m.group(2)
    if "Renders all static" in content or "Sources are merged" in content:
        print(f"[DEFECT 1] id={pre_id} offset={m.start()}")
        print(f"  Content start: {content[:200]!r}")
        print()
    if "'+seqContent+'" in content:
        print(f"[DEFECT 2] id={pre_id} offset={m.start()}")
        print(f"  Content: {content[:200]!r}")
        print()
    if not content.strip():
        print(f"[EMPTY] id={pre_id} offset={m.start()}")

# Also find the <pre> start positions backward from the known offsets
for label, off in [("D1", 16213238), ("D2", 16311241)]:
    # search backward for <pre class="mermaid"
    start_search = text.rfind('<pre class="mermaid"', 0, off)
    print(f"\n[{label}] nearest <pre class=\"mermaid\"> before offset {off}: at {start_search}")
    if start_search != -1:
        snippet = text[start_search:start_search+300]
        print(f"  {snippet[:300]!r}")
