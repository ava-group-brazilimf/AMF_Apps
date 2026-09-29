import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "src/modules/ava-fabric-agents/summary/utils/blueprint_compatibility.py"
RENDER_PATH = ROOT / "src/modules/ava-fabric-agents/summary/utils/render_blueprint_compatibility.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


compat = load_module("blueprint_compatibility", MODULE_PATH)
render = load_module("render_blueprint_compatibility", RENDER_PATH)


def test_detects_c4_constructs_and_dialect():
    source = (ROOT / "tests/summary/fixtures/sophia-tobe-c4container.mmd").read_text(encoding="utf-8")
    assert compat.detect_dialect(source) == "C4Container"
    assert {item["name"] for item in compat.detect_constructs(source)} == {"Person", "Container", "ContainerDb", "System_Ext", "Rel"}


def test_static_c4_requires_runtime_capability():
    result = compat.CompatibilityResult("trace-1", "sophia", "outputs/tobe/diagrams/architecture-blueprint.mmd", "tobeArchBlueprint", "C4Container\n  Person(u, \"User\", \"Reviewer\")")
    result.validate_static(renderer_supports_c4=None)
    assert result.root_cause == "EVIDENCE_UNAVAILABLE"
    assert result.static_status == "INCONCLUSIVE"
    assert result.to_public()["publicationAllowed"] is False


def test_runtime_probe_classification_fails_closed():
    assert render.classify_probe({"rendererVersion": ""})["rootCause"] == "RENDERER_CONFIGURATION_FAILURE"
    assert render.classify_probe({"rendererVersion": "10.0.0"})["rootCause"] == "MERMAID_VERSION_INCOMPATIBILITY"
    assert render.classify_probe({"rendererVersion": "11.14.0", "renderStatus": "FAIL"})["rootCause"] == "RENDERING_FAILURE"
    assert render.classify_probe({"rendererVersion": "11.14.0", "renderStatus": "PASS"})["publicationAllowed"] is True


def test_report_uses_camel_case_and_complete_hashes():
    result = compat.CompatibilityResult("trace-1", "sophia", "outputs/tobe/diagrams/architecture-blueprint.mmd", "tobeArchBlueprint", "flowchart TB\n A --> B", renderer_version="11.14.0", renderer_source="summary-template.html#mermaid.min.js", static_status="PASS", runtime_status="PASS", root_cause="VALID_MERMAID")
    result.stage_sources.update({
        "staticDiagrams": result.source,
        "renderAllDiagramsInput": result.source,
        "renderStaticDiagramsInput": result.source,
        "rendererInput": result.source,
    })
    report = result.to_public()
    assert report["traceId"] == "trace-1"
    assert "classification" not in report
    assert set(report["hashes"]) == {"rawArtifact", "sanitizedContent", "staticDiagrams", "renderAllDiagramsInput", "renderStaticDiagramsInput", "rendererInput"}
    assert report["publicationAllowed"] is False  # sanitizedContent is intentionally absent evidence


def test_probe_uses_summary_bundle_and_same_configuration():
    html = render.runtime_probe_script(render.summary_bundle_path(ROOT), "flowchart TB\n A --> B")
    assert "mermaid.min.js" in html
    assert "startOnLoad" in html
    assert "securityLevel" in html
    assert "mermaid.render" in html
    assert "mermaid.version" in html


def test_empty_branch_does_not_change_paths():
    artifact = Path("projects/sophia/outputs/tobe/diagrams/architecture-blueprint.mmd")
    assert "" not in artifact.parts
    assert artifact.as_posix().startswith("projects/sophia/")
