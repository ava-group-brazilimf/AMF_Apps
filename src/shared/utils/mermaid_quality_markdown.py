"""Markdown projection for the canonical Mermaid quality report."""
from __future__ import annotations

import json
from pathlib import Path


def generate(report_path: str | Path, gate_path: str | Path, output_path: str | Path) -> Path:
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    gate = json.loads(Path(gate_path).read_text(encoding="utf-8"))
    findings = report.get("findings", [])
    blocking = [f for f in findings if f.get("severity") in {"CRITICAL", "HIGH"}]
    warnings = [f for f in findings if f not in blocking]
    lines = [
        "# Mermaid Quality Report", "", "## Summary",
        f"- Project: `{report.get('projectName', '')}`",
        f"- Status: **{gate.get('status', report.get('status', 'UNKNOWN'))}**",
        f"- Artifacts: {report.get('artifactsAnalyzed', 0)}",
        f"- Diagrams: {report.get('diagramsAnalyzed', 0)}", "",
        "## Configuration Resolution", f"- Acceptance baseline: `{report.get('acceptanceBaselineVersion', '')}`", "",
        "## Rendering Profile", "```json", json.dumps(report.get("effectiveRenderingProfile", {}), indent=2), "```", "",
        "## Quality Gate Result", f"- Publication allowed: `{gate.get('publicationAllowed', False)}`", f"- Renderer: `{gate.get('rendererStatus', '')}`", "",
        "## Blocking Findings", *[_finding_line(f) for f in blocking], "",
        "## Warning Findings", *[_finding_line(f) for f in warnings], "",
        "## Diagram-Level Results", "See canonical JSON for complete artifact-level results.", "",
        "## Corrected Mermaid Examples", *[_example_line(f) for f in findings if "correctedMermaidExample" in f], "",
        "## Not Safely Correctable Items", *[_example_line(f) for f in findings if "notSafelyCorrectableReason" in f], "",
        "## Viewer Smoke Test Results", json.dumps(gate.get("checks", {}).get("viewerSmokeTest", "NOT_RUN")), "",
        "## Fixture Matrix Results", "Fixture results are recorded by the validation test suite.", "",
    ]
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def _finding_line(finding: dict) -> str:
    return f"- `{finding.get('id')}` [{finding.get('severity')}] {finding.get('category')}: {finding.get('description')} ({finding.get('artifactPath')} / {finding.get('diagramId')})"


def _example_line(finding: dict) -> str:
    return f"- `{finding.get('id')}`: {finding.get('correctedMermaidExample') or finding.get('notSafelyCorrectableReason')}"
