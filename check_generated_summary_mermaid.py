#!/usr/bin/env python3
"""Check the three Mermaid rendering defects in the generated Summary HTML."""
from pathlib import Path
import re

ROOT = Path(r"c:\_git\Fix\imfai-ava-fabric-apps-agents")


def strip_script_and_style_tags(html: str) -> str:
    """Return a copy of html with <script>...</script> and <style>...</style> removed.

    The defects D1 and D2 are caused by literal strings inside the template's
    own JavaScript (e.g. JSDoc references to `id="diag-*"` and the dynamic seq
    panel builder string). Those are not real <pre class="mermaid"> elements in
    the rendered DOM, so they must be excluded from the check.
    """
    stripped = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    stripped = re.sub(r'<style\b[^>]*>.*?</style>', '', stripped, flags=re.DOTALL | re.IGNORECASE)
    return stripped


# Find most recent generated Summary HTML for MeuERP-001
summary_dir = ROOT / "projects" / "MeuERP-001" / "outputs" / "summary"
if not summary_dir.exists():
    print(f"Summary dir not found: {summary_dir}")
    raise SystemExit(1)

html_files = sorted(summary_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
if not html_files:
    print("No HTML files found in summary dir")
    raise SystemExit(1)

html_path = html_files[0]
print(f"Checking: {html_path}\n")

text = html_path.read_text(encoding="utf-8", errors="ignore")
check_text = strip_script_and_style_tags(text)

# Defect 1: <pre class="mermaid" id="diag-*"> containing JSDoc-like content
print("=== DEFECT 1: JSDoc inside <pre class=\"mermaid\"> ===")
pattern1 = re.compile(
    r'<pre\s+class="mermaid"\s+id="([^"]+)"[^>]*>(.*?)</pre>',
    re.DOTALL | re.IGNORECASE,
)
count1 = 0
for m in pattern1.finditer(check_text):
    content = m.group(2).strip()
    if content.startswith("/*") or content.startswith("*") or "Sources are merged" in content or "Renders all static" in content:
        count1 += 1
        print(f"  id={m.group(1)} offset={m.start()}: {content[:120]!r}")
print(f"  Found: {count1}\n")

# Defect 2: literal '+seqContent+' inside <pre class="mermaid">
print("=== DEFECT 2: literal '+seqContent+' inside <pre class=\"mermaid\"> ===")
pattern2 = re.compile(
    r'<pre\s+class="mermaid"[^>]*>(.*?)</pre>',
    re.DOTALL | re.IGNORECASE,
)
count2 = 0
for m in pattern2.finditer(check_text):
    content = m.group(1)
    if "'+seqContent+'" in content:
        count2 += 1
        print(f"  offset={m.start()}: {content[:120]!r}")
print(f"  Found: {count2}\n")

# Defect 3: empty <pre class="mermaid">
print("=== DEFECT 3: empty <pre class=\"mermaid\"> ===")
pattern3 = re.compile(
    r'<pre\s+class="mermaid"\s+id="([^"]+)"[^>]*>\s*</pre>',
    re.IGNORECASE,
)
count3 = 0
for m in pattern3.finditer(check_text):
    count3 += 1
    print(f"  id={m.group(1)} offset={m.start()}")
print(f"  Found: {count3}\n")

print(f"Summary: D1={count1}, D2={count2}, D3={count3}")
