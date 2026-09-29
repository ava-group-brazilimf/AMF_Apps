#!/usr/bin/env python3
"""
Aplica as 3 correções de renderização Mermaid no Summary.
"""
from pathlib import Path
import re
import sys

ROOT = Path(r"c:\_git\Fix\imfai-ava-fabric-apps-agents")

def find_summary_template():
    """Prefer the canonical template under src/modules/ava-fabric-agents/summary/templates/html/."""
    canonical = (
        ROOT
        / "src"
        / "modules"
        / "ava-fabric-agents"
        / "summary"
        / "templates"
        / "html"
        / "summary-template.html"
    )
    if canonical.exists():
        return canonical

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
    summary_candidates = [c for c in candidates if "summary" in str(c).lower()]
    if summary_candidates:
        return max(summary_candidates, key=lambda x: x.stat().st_size)
    if candidates:
        return max(candidates, key=lambda x: x.stat().st_size)
    return None

def find_summary_builder():
    builders = list(ROOT.rglob("build_summary_comprehensive.py"))
    if builders:
        return builders[0]
    return None

def fix_template_jsdoc_inside_pre(html: str) -> str:
    """
    Remove JSDoc comments placed inside <pre class="mermaid"> containers.
    Finds <pre class="mermaid" id="diag-*"> ... </pre> where inner content
    starts with /* or * and replaces it with a harmless Mermaid comment.
    """
    # Pattern 1: <pre class="mermaid" id="diag-...">\n  /** ... */
    pattern = re.compile(
        r'(<pre\s+class="mermaid"\s+id="diag-[^"]+">\s*)'
        r'(\s*/\*\*.*?\*/\s*)'
        r'(\s*</pre>)',
        re.DOTALL | re.IGNORECASE,
    )

    def repl(m):
        opening = m.group(1)
        closing = m.group(3)
        return f'{opening.strip()}\n%% diagram placeholder\n{closing}'

    html, count1 = pattern.subn(repl, html)

    # Pattern 2: content starting with raw '*' lines (standalone JSDoc fragments)
    pattern2 = re.compile(
        r'(<pre\s+class="mermaid"\s+id="diag-[^"]+">\s*)'
        r'(\s*\n\s*\*.*?)(?=\s*</pre>)',
        re.DOTALL | re.IGNORECASE,
    )

    def repl2(m):
        opening = m.group(1)
        return f'{opening.strip()}\n%% diagram placeholder\n'

    html, count2 = pattern2.subn(repl2, html)
    return html, count1 + count2

def fix_template_empty_pre(html: str) -> str:
    """
    Converts empty <pre class="mermaid" id="..."> dynamic containers
    to <pre data-mermaid-pending id="..."> and adjusts the JS that fills them.
    """
    # Find empty-ish <pre class="mermaid" id="..."> </pre>
    # We'll do a conservative replacement for known TO-BE IDs first.
    tobe_ids = [
        "c4-context-tobe", "c4-container-tobe", "c4-component-tobe",
        "component-diagram-tobe", "db-tobe", "database-tobe",
    ]

    count = 0
    for tid in tobe_ids:
        for quote in ['"', "'"]:
            regex = re.compile(
                rf'<pre\s+class={quote}mermaid{quote}\s+id={quote}{re.escape(tid)}{quote}\s*>\s*</pre>',
                re.IGNORECASE,
            )
            html, c = regex.subn(
                f'<pre data-mermaid-pending id={quote}{tid}{quote}></pre>', html
            )
            count += c

    # Generic fallback: any empty <pre class="mermaid" id="..."> becomes data-mermaid-pending
    generic = re.compile(
        r'<pre\s+class=["\']mermaid["\']\s+id=["\']([^"\']+)["\']\s*>\s*</pre>',
        re.IGNORECASE,
    )

    def generic_repl(m):
        cid = m.group(1)
        return f'<pre data-mermaid-pending id="{cid}"></pre>'

    html, c = generic.subn(generic_repl, html)
    count += c

    # Adjust JS: wherever mermaid.run() is called after DOMContentLoaded,
    # add a guard that skips empty/pending containers and only promotes
    # data-mermaid-pending after content is injected.
    if "data-mermaid-pending" in html:
        # Insert a helper before the first mermaid.run() call if not present
        helper = """
function renderPendingDiagrams() {
  document.querySelectorAll('pre[data-mermaid-pending]').forEach(function(el) {
    var source = (window.D && D.staticDiagrams && D.staticDiagrams[el.id]) || '';
    if (!source.trim()) return;
    el.classList.add('mermaid');
    el.removeAttribute('data-mermaid-pending');
    el.textContent = source;
  });
}
"""
        if "renderPendingDiagrams" not in html:
            # Insert before first mermaid.run(
            html = re.sub(
                r'(mermaid\.run\()',
                helper + r'\1',
                html,
                count=1,
            )
            # Also wrap run to call renderPendingDiagrams first, if possible
            html = re.sub(
                r'(document\.addEventListener\(["\']DOMContentLoaded["\'],\s*function\s*\(\)\s*\{)',
                r'\1\n    renderPendingDiagrams();',
                html,
                count=1,
            )

    return html, count

def fix_builder_seq_literal(builder_text: str) -> str:
    """
    Removes literal <pre class="mermaid">'+seqContent+'</pre> from static HTML
    and ensures the sequence content is interpolated in Python or emitted via JS
    only after the DOM is present.
    """
    count = 0

    # Generic catch-all: any occurrence of <pre class="mermaid">'+seqContent+'</pre>
    # regardless of Python quoting. We replace the literal with a Python placeholder
    # that interpolates a variable named seq_content.
    pat = re.compile(
        r'(<pre\s+class=["\']mermaid["\'][^>]*>)\'+seqContent\+(</pre>)',
        re.IGNORECASE,
    )

    def repl(m):
        return f'{m.group(1)}' + "{seq_content}" + f'{m.group(2)}'

    builder_text, c = pat.subn(repl, builder_text)
    count += c

    # Also catch bare '+seqContent+' left in HTML strings.
    bare_pat = re.compile(r"(?<![A-Za-z0-9_])\'+seqContent\+'")
    builder_text, c2 = bare_pat.subn("{seq_content}", builder_text)
    count += c2

    return builder_text, count

def main():
    template = find_summary_template()
    builder = find_summary_builder()

    if not template:
        print("ERRO: template HTML do Summary não encontrado.", file=sys.stderr)
        sys.exit(1)
    if not builder:
        print("ERRO: build_summary_comprehensive.py não encontrado.", file=sys.stderr)
        sys.exit(1)

    print(f"Template encontrado: {template}")
    print(f"Builder encontrado: {builder}")

    html = template.read_text(encoding="utf-8")
    html, c1 = fix_template_jsdoc_inside_pre(html)
    print(f"  -> JSDoc dentro de <pre class=\"mermaid\"> corrigidos: {c1}")

    html, c3 = fix_template_empty_pre(html)
    print(f"  -> Containers vazios convertidos para data-mermaid-pending: {c3}")

    if c1 or c3:
        template.write_text(html, encoding="utf-8")
        print(f"  -> Template salvo: {template}")
    else:
        print("  -> Nenhuma alteração no template.")

    builder_text = builder.read_text(encoding="utf-8")
    builder_text, c2 = fix_builder_seq_literal(builder_text)
    print(f"  -> Literal '+seqContent+' corrigidos: {c2}")

    if c2:
        builder.write_text(builder_text, encoding="utf-8")
        print(f"  -> Builder salvo: {builder}")
    else:
        print("  -> Nenhuma alteração no builder.")

if __name__ == "__main__":
    main()
