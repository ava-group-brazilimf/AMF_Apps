"""Regression tests for the deterministic anchor-stripping repair (CHK-SK-006).

Reproduces the two hallucination patterns found in `nopcommerce-04-cli-ava`
(ISSUE-004 WI-19/WI-20): a `DEC-NNN` cited one past the last real id in the
constitution, and an invented `Section-N` anchor that never matches a real
Markdown heading slug. Both must be stripped by
`speckit_fragment_repair.py`'s anchor validation, which already implements
the same resolution logic as `speckit_traceability.py`'s CHK-SK-006 — this
guards that behavior against regression.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import speckit_fragment_repair as repair  # noqa: E402

CONSTITUTION_MD = """# Project Constitution

## 10. Mandatory Decisions

| ID | Decision |
|----|----------|
| DEC-001 | Strangler Fig migration |
| DEC-020 | Multi-store support via EF Core global query filter |
"""

SPEC_MD = """# Specification — W2 Core Write

## 3. Modelo de Domínio

### 3.1 BC-03 Customers

Conteúdo do BC-03.
"""


def test_dec_id_one_past_the_real_ceiling_is_stripped():
    """`DEC-021` does not exist when the constitution stops at `DEC-020`."""
    assert not repair._anchor_exists_in_content("DEC-021", CONSTITUTION_MD)


def test_dec_id_within_range_resolves():
    assert repair._anchor_exists_in_content("DEC-020", CONSTITUTION_MD)
    assert repair._anchor_exists_in_content("DEC-001", CONSTITUTION_MD)


def test_invented_section_scheme_is_stripped():
    """`Section-N` never matches the real heading slug (`3-modelo-de-domínio`)."""
    assert not repair._anchor_exists_in_content("Section-3", SPEC_MD)
    assert not repair._anchor_exists_in_content("Section-7", SPEC_MD)


def test_real_heading_slug_resolves():
    assert repair._anchor_exists_in_content("3-modelo-de-domínio", SPEC_MD)
    # Partial slug cut at a segment boundary (§3.1) also resolves.
    assert repair._anchor_exists_in_content("3.1-bc-03-customers", SPEC_MD)


def test_strip_invalid_source_ref_anchors_removes_both_patterns(tmp_path):
    project_root = tmp_path / "projects" / "P"
    speckit = project_root / "outputs" / "tobe" / "speckit"
    (speckit).mkdir(parents=True)
    (speckit / "constitution.md").write_text(CONSTITUTION_MD, encoding="utf-8")
    specs_dir = speckit / "specs" / "003-w2-core-write"
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.md").write_text(SPEC_MD, encoding="utf-8")

    good_ref = {"artifact": "outputs/tobe/speckit/constitution.md", "anchor": "DEC-020"}
    bad_dec_ref = {"artifact": "outputs/tobe/speckit/constitution.md", "anchor": "DEC-021"}
    bad_section_ref = {
        "artifact": "outputs/tobe/speckit/specs/003-w2-core-write/spec.md",
        "anchor": "Section-3",
    }

    plan = {"files": [{"path": "x.cs", "source_refs": [good_ref, bad_dec_ref]}]}
    fragment = {
        "entries": [
            {"task_id": "T-SHD-001", "source_refs": [good_ref, bad_dec_ref, bad_section_ref]},
        ]
    }

    changes, warnings = repair._strip_invalid_source_ref_anchors(
        "003-w2-core-write", plan, fragment, project_root, REPO_ROOT, {}
    )

    assert len(changes) == 3  # 1 in plan (bad_dec_ref) + 2 in fragment
    assert any("DEC-021" in w for w in warnings)
    assert any("Section-3" in w for w in warnings)

    remaining_plan_refs = plan["files"][0]["source_refs"]
    assert remaining_plan_refs == [good_ref]

    remaining_frag_refs = fragment["entries"][0]["source_refs"]
    assert remaining_frag_refs == [good_ref]
