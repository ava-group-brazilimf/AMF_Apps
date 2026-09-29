"""Summary provenance tests for feature 039."""
from pathlib import Path
import importlib.util
import json


REPO = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO.parent / "src" / "modules" / "ava-fabric-agents" / "summary" / "utils" / "build_summary_comprehensive.py"
SPEC = importlib.util.spec_from_file_location("summary_builder", BUILDER_PATH)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)



def test_provenance_loader_supports_client_fallback_invalid_and_legacy(tmp_path: Path) -> None:
    prototype = tmp_path / "outputs" / "tobe" / "prototype"
    prototype.mkdir(parents=True)

    assert builder._load_prototype_design_provenance(tmp_path / "outputs")["source"] == "legacy-unavailable"

    traceability = prototype / "design-input-traceability.json"
    traceability.write_text(json.dumps({
        "source": "client",
        "used_file": "inputs/design/figma-export.json",
        "format": "figma-json",
        "mapped_categories": ["colors"],
        "unmapped_fields": [],
        "limitation_severity": "none",
    }), encoding="utf-8")
    client = builder._load_prototype_design_provenance(tmp_path / "outputs")
    assert client["source"] == "client"
    assert "figma-export.json" in client["detail"]

    traceability.write_text(json.dumps({
        "source": "fallback-design-system",
        "fallback_reason": "client input unavailable",
        "mapped_categories": [],
        "unmapped_fields": [],
        "limitation_severity": "medium",
    }), encoding="utf-8")
    fallback = builder._load_prototype_design_provenance(tmp_path / "outputs")
    assert fallback["source"] == "fallback-design-system"
    assert "client input unavailable" in fallback["detail"]

    traceability.write_text("{invalid", encoding="utf-8")
    assert builder._load_prototype_design_provenance(tmp_path / "outputs")["source"] == "invalid"


def test_provenance_loader_redacts_raw_secret_like_payload() -> None:
    prototype = Path("tests") / "_tmp-provenance-security"
    outputs = prototype / "outputs"
    traceability = outputs / "tobe" / "prototype" / "design-input-traceability.json"
    traceability.parent.mkdir(parents=True, exist_ok=True)
    try:
        traceability.write_text(json.dumps({
            "source": "fallback-generic",
            "fallback_reason": "sk-secret postgres://user:pass@host AKIA123",
            "mapped_categories": [],
            "unmapped_fields": [],
            "limitation_severity": "medium",
        }), encoding="utf-8")
        provenance = builder._load_prototype_design_provenance(outputs)
        html = builder._prototype_design_provenance_html(provenance)
        assert "sk-secret" not in html
        assert "postgres://user:pass@host" not in html
        assert "AKIA123" not in html
    finally:
        import shutil
        shutil.rmtree(prototype, ignore_errors=True)
    assert "<script" not in html.lower()
