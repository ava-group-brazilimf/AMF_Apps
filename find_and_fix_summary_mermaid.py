#!/usr/bin/env python3
"""
Localiza e corrige os 3 defeitos de renderização Mermaid no Summary.
"""
from pathlib import Path
import re

ROOT = Path(r"c:\_git\Fix\imfai-ava-fabric-apps-agents")

def find_summary_template():
    """Encontra o template HTML do Summary que contém mermaid."""
    candidates = []
    for p in ROOT.rglob("*.html"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if ('class="mermaid"' in text or "class='mermaid'" in text) and (
                "renderMmdBlocks" in text or "mermaid.run" in text or "diag-" in text
            ):
                candidates.append(p)
        except Exception:
            pass
    return candidates

def find_summary_builder():
    """Encontra build_summary_comprehensive.py."""
    return list(ROOT.rglob("build_summary_comprehensive.py"))

def main():
    templates = find_summary_template()
    builders = find_summary_builder()

    print("=== SUMMARY TEMPLATES ===")
    for t in templates:
        print(t)
    print("\n=== SUMMARY BUILDERS ===")
    for b in builders:
        print(b)

if __name__ == "__main__":
    main()
