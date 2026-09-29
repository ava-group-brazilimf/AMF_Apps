"""Phase 3 template switching regression tests."""
from __future__ import annotations

from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[2] / "src" / "modules" / "ava-fabric-agents" / "summary" / "templates" / "html" / "summary-template.html"


def test_selector_and_dual_pattern_rows_are_wired() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="lsel" onchange="setLang(this.value)"' in html
    assert '<option value="en" selected>' in html
    assert '<option value="pt">' in html
    assert 'var lang = "en"' in html
    assert 'id="tb-tobe-patterns"' in html
    assert 'id="tb-tobe-patterns-pt"' in html
    assert "patternsEn.style.display = l === 'pt' ? 'none' : '';" in html
    assert "patternsPt.style.display = l === 'pt' ? '' : 'none';" in html
    assert '"hdr-scope":"Scope"' in html
    assert '"hdr-scope":"Escopo"' in html
    assert '"card-tobe-patterns":"TO-BE Architecture Patterns"' in html
    assert '"card-tobe-patterns":"Padrões Arquiteturais TO-BE"' in html


def test_set_lang_still_processes_all_i18n_elements() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "document.querySelectorAll('[data-i18n]').forEach" in html
    assert "function setLang(l)" in html
