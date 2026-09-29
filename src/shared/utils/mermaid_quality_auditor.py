"""Project-wide Mermaid quality audit and canonical report generation."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from diagram_validation_config import DiagramValidationConfigError, DiagramValidationConfigLoader

FENCE_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.IGNORECASE | re.DOTALL)
VALID_TYPES = ("flowchart", "sequenceDiagram", "classDiagram", "erDiagram", "gantt", "C4")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _finding(artifact: str, diagram: str, category: str, severity: str, description: str, root: str, recommendation: str, evidence: dict[str, Any], *, example: str | None = None, reason: str | None = None) -> dict[str, Any]:
    item = {"id": f"MQ-{_hash(artifact + diagram + category + description)[:12]}", "severity": severity, "category": category, "artifactPath": artifact, "diagramId": diagram, "diagramType": "unknown", "description": description, "impact": "Diagram cannot be safely published until corrected.", "rootCause": root, "evidence": evidence, "recommendation": recommendation}
    if example:
        item["correctedMermaidExample"] = example
    else:
        item["notSafelyCorrectableReason"] = reason or "No deterministic correction is available."
    return item


def _validate_source(path: str, diagram_id: str, source: str, profile: dict[str, Any], renderer_status: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    first = next((line.strip() for line in source.splitlines() if line.strip()), "")
    if not first or not first.startswith(VALID_TYPES):
        findings.append(_finding(path, diagram_id, "SYNTAX", "CRITICAL", "Unknown or missing Mermaid diagram declaration.", "The source does not begin with a supported diagram declaration.", "Regenerate using a supported Mermaid declaration.", {"effectiveRenderingProfile": profile, "structuralEvidence": "first non-empty line is not a supported declaration", "rendererStatus": renderer_status}, reason="The diagram type cannot be inferred safely."))
    for line_no, line in enumerate(source.splitlines(), 1):
        node = re.match(r"\s*([A-Za-z0-9_.:/-]+)\s*[\[({>]", line)
        if node and (not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", node.group(1))):
            findings.append(_finding(path, diagram_id, "SANITIZATION", "HIGH", f"Invalid node identifier: {node.group(1)}.", "Node identifier contains unsupported characters or begins with a number.", "Normalize to letters, numbers, and underscores with a node_ prefix when needed.", {"line": line_no, "effectiveRenderingProfile": profile, "structuralEvidence": line.strip(), "rendererStatus": renderer_status}, example="node_1[\"Safe label\"]"))
        if len(line) > profile.get("maxRelationshipLabelLengthChars", 80) + 80:
            findings.append(_finding(path, diagram_id, "LABEL_LENGTH", "MEDIUM", "Relationship line exceeds configured readability length.", "Relationship label or edge definition is too long for default view.", "Wrap or shorten while preserving meaning.", {"line": line_no, "effectiveRenderingProfile": profile, "structuralEvidence": f"line_length={len(line)}", "rendererStatus": renderer_status}, reason="Automatic shortening may alter meaning."))
    return findings


def audit(project_root: str | Path, execution_environment: str = "local", local_development_override: bool = False, trace_id: str = "") -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(project_root)
    try:
        config = DiagramValidationConfigLoader(root).load()
        values = config.values
        config_finding = None
    except DiagramValidationConfigError as exc:
        values = None
        config_finding = _finding(".config/diagram-validation.yaml", "configuration", "CONFIGURATION", "CRITICAL", str(exc), "Missing or malformed mandatory configuration.", "Create a valid diagramValidation.mermaid configuration.", {"effectiveRenderingProfile": {}, "structuralEvidence": str(exc), "rendererStatus": "NOT_RUN"}, reason="Configuration must be corrected before validation can proceed.")
    profile = (values or {}).get("renderingProfile", {})
    artifacts: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    if config_finding:
        findings.append(config_finding)
    else:
        for path in sorted(root.rglob("*.mmd")):
            source = path.read_text(encoding="utf-8", errors="replace")
            rel = path.relative_to(root).as_posix()
            diagram_id = f"{rel}#0"
            local_findings = _validate_source(rel, diagram_id, source, profile, "NOT_RUN")
            findings.extend(local_findings)
            artifacts.append({"artifactPath": rel, "diagramId": diagram_id, "artifactName": path.name, "diagramName": path.stem, "diagramType": source.splitlines()[0].strip() if source.splitlines() else "unknown", "status": "BLOCKED" if local_findings else "WARN", "rendererStatus": "NOT_RUN", "effectiveRenderingProfile": profile})
        for md in sorted(root.rglob("*.md")):
            text = md.read_text(encoding="utf-8", errors="replace")
            for index, match in enumerate(FENCE_RE.finditer(text)):
                rel = md.relative_to(root).as_posix()
                diagram_id = f"{rel}#{index}"
                local_findings = _validate_source(rel, diagram_id, match.group(1), profile, "NOT_RUN")
                findings.extend(local_findings)
                artifacts.append({"artifactPath": rel, "diagramId": diagram_id, "artifactName": md.name, "diagramName": f"{md.stem}#{index}", "diagramType": match.group(1).splitlines()[0].strip() if match.group(1).splitlines() else "unknown", "status": "BLOCKED" if local_findings else "WARN", "rendererStatus": "NOT_RUN", "effectiveRenderingProfile": profile})
    blocking = len([f for f in findings if f["severity"] in ("CRITICAL", "HIGH")])
    warnings = len(findings) - blocking
    renderer_unavailable = True
    gate_status = "FAIL" if blocking or renderer_unavailable and execution_environment != "local" else "APPROVED_WITH_WARNINGS"
    gate = {"schemaVersion": "1.0.0", "status": gate_status, "blocking": gate_status == "FAIL", "acceptanceBaselineVersion": "11.14.0", "checks": {"syntaxValidation": "FAIL" if blocking else "PASS", "compatibilityValidation": "FAIL" if blocking else "PASS", "sanitizationValidation": "FAIL" if blocking else "PASS", "renderValidation": "RENDERER_UNAVAILABLE", "readabilityValidation": "NOT_RUN", "viewerSmokeTest": "RENDERER_UNAVAILABLE"}, "blockingFindings": blocking, "warningFindings": warnings, "publicationAllowed": False, "executionEnvironment": execution_environment, "rendererStatus": "RENDERER_UNAVAILABLE", "humanGateRequired": gate_status == "FAIL", "localDevelopmentOverride": local_development_override, "affectedArtifactPaths": sorted({f["artifactPath"] for f in findings}), "affectedDiagramIds": sorted({f["diagramId"] for f in findings})}
    report = {"schemaVersion": "1.0.0", "feature": "mermaid-diagram-quality", "projectName": root.name, "traceId": trace_id or "generated-locally", "generatedAt": datetime.now(timezone.utc).isoformat(), "acceptanceBaselineVersion": "11.14.0", "rendererVersion": (values or {}).get("mermaid", {}).get("rendererVersion", "11.14.0"), "defaultRenderingProfile": {"viewportWidth": 1440, "viewportHeight": 900, "zoomLevel": 1.0, "fontFamily": "Arial, sans-serif", "fontSizePx": 14, "theme": "default", "deviceScaleFactor": 1}, "effectiveRenderingProfile": profile, "artifactsAnalyzed": len({a["artifactPath"] for a in artifacts}), "diagramsAnalyzed": len(artifacts), "blockingFindings": blocking, "warningFindings": warnings, "findings": findings}
    return report, gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--environment", choices=["production", "staging", "local"], default="local")
    parser.add_argument("--local-development-override", action="store_true")
    parser.add_argument("--trace-id", default="")
    args = parser.parse_args()
    report, gate = audit(args.project_root, args.environment, args.local_development_override, args.trace_id)
    output = Path(args.project_root) / "outputs" / "asis" / "docs"
    output.mkdir(parents=True, exist_ok=True)
    (output / "mermaid-quality-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / "mermaid-quality-gate.json").write_text(json.dumps(gate, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"report": str(output / "mermaid-quality-report.json"), "gate": gate["status"]}, ensure_ascii=False))
    return 1 if gate["status"] == "FAIL" else 0

if __name__ == "__main__":
    raise SystemExit(main())
