import json
from pathlib import Path

import pytest

from src.shared.utils.diagram_validation_config import (
    DiagramValidationConfigError,
    DiagramValidationConfigLoader,
)
from src.shared.utils.mermaid_quality_auditor import audit
from src.shared.utils.mermaid_quality_summary import MermaidQualitySummaryAdapter


VALID_CONFIG = """diagramValidation:
  mermaid:
    acceptanceBaselineVersion: '11.14.0'
    rendererVersion: '11.14.0'
    strictCompatibility: true
  readability:
    maxNodeLabelLengthChars: 60
    maxRelationshipLabelLengthChars: 80
"""


def test_config_loader_requires_mermaid_section(tmp_path: Path):
    config = tmp_path / ".config" / "diagram-validation.yaml"
    config.parent.mkdir()
    config.write_text("diagramValidation: {}\n", encoding="utf-8")
    with pytest.raises(DiagramValidationConfigError):
        DiagramValidationConfigLoader(tmp_path).load()


def test_config_loader_applies_optional_defaults(tmp_path: Path):
    config = tmp_path / ".config" / "diagram-validation.yaml"
    config.parent.mkdir()
    config.write_text(VALID_CONFIG, encoding="utf-8")
    resolved = DiagramValidationConfigLoader(tmp_path).load().values
    assert resolved["renderingProfile"]["viewportWidth"] == 1440
    assert resolved["readability"]["maxNodeLabelLengthChars"] == 60


def test_auditor_emits_canonical_report_and_gate(tmp_path: Path):
    config = tmp_path / ".config" / "diagram-validation.yaml"
    config.parent.mkdir()
    config.write_text(VALID_CONFIG, encoding="utf-8")
    diagram = tmp_path / "outputs" / "asis" / "diagrams" / "ok.mmd"
    diagram.parent.mkdir(parents=True)
    diagram.write_text('flowchart TB\n  A["Node"] --> B["Target"]\n', encoding="utf-8")

    report, gate = audit(tmp_path, trace_id="trace-1")

    assert report["traceId"] == "trace-1"
    assert report["effectiveRenderingProfile"]["viewportHeight"] == 900
    assert report["artifactsAnalyzed"] == 1
    assert gate["rendererStatus"] == "RENDERER_UNAVAILABLE"
    assert gate["executionEnvironment"] == "local"


def test_auditor_blocks_missing_configuration(tmp_path: Path):
    report, gate = audit(tmp_path, execution_environment="production")
    assert report["findings"][0]["category"] == "CONFIGURATION"
    assert gate["status"] == "FAIL"
    assert gate["publicationAllowed"] is False
    assert gate["humanGateRequired"] is True


def test_summary_adapter_reads_report_and_gate(tmp_path: Path):
    (tmp_path / "mermaid-quality-report.json").write_text(json.dumps({"blockingFindings": 2}), encoding="utf-8")
    (tmp_path / "mermaid-quality-gate.json").write_text(json.dumps({
        "status": "FAIL", "publicationAllowed": False, "rendererStatus": "FAILED",
        "executionEnvironment": "production", "blockingFindings": 2,
        "warningFindings": 1, "affectedArtifactPaths": ["a.mmd"], "affectedDiagramIds": ["a#0"],
    }), encoding="utf-8")
    metadata = MermaidQualitySummaryAdapter(tmp_path).read()
    assert metadata["overallStatus"] == "FAIL"
    assert metadata["affectedArtifacts"] == ["a.mmd"]
