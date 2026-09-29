import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "specs/036-architecture-blueprint-mermaid-compatibility/contracts/blueprint-compatibility-report.schema.json"


def test_public_schema_requires_camel_case_fields():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    required = set(schema["required"])
    assert {"traceId", "projectName", "artifactPath", "diagramId", "rendererVersion", "rootCause", "hashes", "publicationAllowed"} <= required
    assert "classification" not in required
    assert "trace_id" not in required


def test_hash_schema_has_all_pipeline_checkpoints():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    required = set(schema["properties"]["hashes"]["required"])
    assert required == {"rawArtifact", "sanitizedContent", "staticDiagrams", "renderAllDiagramsInput", "renderStaticDiagramsInput", "rendererInput"}
