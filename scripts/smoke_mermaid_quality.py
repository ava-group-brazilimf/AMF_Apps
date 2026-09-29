from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

sys.path.insert(0, "src/shared/utils")
from mermaid_quality_auditor import audit
from mermaid_quality_markdown import generate

with TemporaryDirectory() as directory:
    root = Path(directory)
    config = root / ".config"
    config.mkdir()
    (config / "diagram-validation.yaml").write_text(
        "diagramValidation:\n"
        "  mermaid:\n"
        "    acceptanceBaselineVersion: 11.14.0\n"
        "    rendererVersion: 11.14.0\n"
        "    strictCompatibility: true\n",
        encoding="utf-8",
    )
    diagrams = root / "outputs" / "asis" / "diagrams"
    diagrams.mkdir(parents=True)
    (diagrams / "a.mmd").write_text('flowchart TB\n A[Node] --> B[Target]\n', encoding="utf-8")
    report, gate = audit(root, trace_id="t-1")
    assert report["traceId"] == "t-1"
    assert gate["rendererStatus"] == "RENDERER_UNAVAILABLE"
    report_path = root / "report.json"
    gate_path = root / "gate.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    gate_path.write_text(json.dumps(gate), encoding="utf-8")
    output = generate(report_path, gate_path, root / "report.md")
    assert output.exists()
print("SMOKE_OK")
