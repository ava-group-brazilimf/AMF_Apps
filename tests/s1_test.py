import sys
import shutil
from pathlib import Path

sys.path.insert(0, 'src/modules/ava-fabric-agents/summary/utils')
from mermaid_playwright_gate import run_playwright_mermaid_gate

test_dir = Path('projects/t2TiERP/outputs/summary/test_s1')
test_dir.mkdir(parents=True, exist_ok=True)

html = """<!doctype html><html><head><title>test</title></head><body>
<pre class="mermaid" id="diag-test">flowchart TB\n  A[Start] --> B[End]</pre>
<script src="mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true});</script>
</body></html>"""

(test_dir / 'test.html').write_text(html, encoding='utf-8')

src_js = Path('src/modules/ava-fabric-agents/summary/templates/html/mermaid.min.js')
if src_js.exists():
    shutil.copy(src_js, test_dir / 'mermaid.min.js')

result = run_playwright_mermaid_gate(
    html_path=test_dir / 'test.html',
    max_attempts=1,
    timeout_ms=15000
)
print('=== S1 Nominal Path Result ===')
print(f'overall_status: {result.overall_status}')
print(f'total_diagrams: {result.total_diagrams}')
print(f'total_valid: {result.total_valid}')
print(f'total_fixed: {result.total_fixed}')
print(f'total_unresolved: {result.total_unresolved}')
for d in result.diagrams:
    print(f'  - {d.diagram_id}: {d.status}')
