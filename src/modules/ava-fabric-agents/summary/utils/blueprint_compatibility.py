"""Fail-closed Architecture Blueprint Mermaid compatibility checks.

This module owns static classification, provenance, hash checkpoints, report
normalization, and publication decisions. Runtime parsing is delegated to the
Summary renderer adapter in ``render_blueprint_compatibility``.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASELINE = "11.14.0"
ROOT_CAUSES = {
    "VALID_MERMAID", "INVALID_MERMAID", "UNSUPPORTED_DIALECT",
    "UNSUPPORTED_C4_SYNTAX", "RENDERER_CONFIGURATION_FAILURE",
    "MERMAID_VERSION_INCOMPATIBILITY", "RENDERING_FAILURE",
    "SOURCE_INTEGRITY_MISMATCH", "EVIDENCE_UNAVAILABLE",
}
STAGES = {
    "STATIC_VALIDATION", "RUNTIME_VERSION_PROBE", "C4_CAPABILITY_PROBE",
    "RUNTIME_RENDER", "SOURCE_INTEGRITY", "PUBLICATION_GATE",
    "SUMMARY_SMOKE_TEST",
}
C4_CONSTRUCTS = ("Person", "Container", "ContainerDb", "System_Ext", "Rel")
PRODUCERS = {
    "asis": ("ava-asis-solution-delphi", "AS-IS architecture solution", "F1"),
    "tobe": ("ava-tobe-architecture-design", "TO-BE architecture design", "F2"),
}


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def first_directive(source: str) -> str:
    return next((line.strip().split()[0] for line in source.splitlines() if line.strip()), "")


def detect_dialect(source: str) -> str:
    directive = first_directive(source)
    if directive == "C4Container":
        return "C4Container"
    if directive in {"flowchart", "graph"}:
        return "flowchart"
    if directive in {"C4Context", "C4Component", "C4Dynamic", "C4Deployment"}:
        return directive
    if directive in {"sequenceDiagram", "classDiagram", "erDiagram", "gantt"}:
        return directive
    return "unknown"


def detect_constructs(source: str) -> list[dict[str, Any]]:
    result = []
    for line_no, line in enumerate(source.splitlines(), 1):
        for name in C4_CONSTRUCTS:
            if re.search(rf"\b{re.escape(name)}\s*\(", line):
                result.append({"name": name, "line": line_no, "source": line.strip()})
    return result


def producer_for(artifact_path: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    if metadata.get("producingAgent"):
        return {**metadata, "confidence": metadata.get("confidence", "HIGH")}
    role = "tobe" if "/tobe/" in artifact_path.replace("\\", "/") else "asis"
    agent, agent_role, phase = PRODUCERS[role]
    return {
        "producingAgent": agent,
        "producingAgentRole": agent_role,
        "sourceContractPath": f"src/modules/ava-fabric-agents/{'tobe-architecture' if role == 'tobe' else 'asis-diagnostic'}/agents",
        "artifactContractPath": artifact_path,
        "generationPhase": phase,
        "confidence": "MEDIUM",
    }


@dataclass
class CompatibilityResult:
    trace_id: str
    project_name: str
    artifact_path: str
    diagram_id: str
    source: str
    renderer_version: str = ""
    version_source: str = "unavailable"
    version_discovery_method: str = "unavailable"
    version_discovery_status: str = "UNAVAILABLE"
    version_confidence: str = "LOW"
    renderer_source: str = ""
    c4_supported: bool | None = None
    static_status: str = "INCONCLUSIVE"
    runtime_status: str = "NOT_RUN"
    root_cause: str = "EVIDENCE_UNAVAILABLE"
    stage: str = "STATIC_VALIDATION"
    confidence: str = "LOW"
    construct: str = ""
    exact_error: str = ""
    recommended_fix: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    sanitized: str | None = None
    stage_sources: dict[str, str | None] = field(default_factory=dict)
    producer: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.producer = self.producer or producer_for(self.artifact_path)
        self.stage_sources.setdefault("rawArtifact", self.source)
        self.stage_sources.setdefault("sanitizedContent", self.sanitized)
        self.stage_sources.setdefault("staticDiagrams", None)
        self.stage_sources.setdefault("renderAllDiagramsInput", None)
        self.stage_sources.setdefault("renderStaticDiagramsInput", None)
        self.stage_sources.setdefault("rendererInput", None)

    def hashes(self) -> dict[str, str | None]:
        return {name: sha256(value) if value is not None else None for name, value in self.stage_sources.items()}

    def validate_static(self, renderer_supports_c4: bool | None = None) -> None:
        dialect = detect_dialect(self.source)
        constructs = detect_constructs(self.source)
        self.evidence["detectedDialect"] = dialect
        self.evidence["constructs"] = constructs
        if dialect == "unknown":
            self.static_status, self.root_cause, self.stage = "FAIL", "UNSUPPORTED_DIALECT", "STATIC_VALIDATION"
            self.recommended_fix = "Regenerate using a supported Mermaid diagram declaration."
            return
        if dialect == "C4Container":
            self.c4_supported = renderer_supports_c4
            if renderer_supports_c4 is not True:
                self.static_status = "INCONCLUSIVE" if renderer_supports_c4 is None else "FAIL"
                self.root_cause = "EVIDENCE_UNAVAILABLE" if renderer_supports_c4 is None else "UNSUPPORTED_C4_SYNTAX"
                self.stage = "C4_CAPABILITY_PROBE"
                self.recommended_fix = "Prove C4 support with the Summary runtime or regenerate with a supported dialect."
                return
            for item in constructs:
                if not re.search(rf"\b{re.escape(item['name'])}\s*\([^\n]*\)", item["source"]):
                    self.static_status, self.root_cause = "FAIL", "INVALID_MERMAID"
                    self.construct, self.stage = item["name"], "STATIC_VALIDATION"
                    return
        self.static_status = "PASS"
        self.root_cause, self.stage, self.confidence = "VALID_MERMAID", "STATIC_VALIDATION", "HIGH"

    def set_runtime(self, *, version: str | None, source: str, ok: bool, error: str = "", stage: str = "RUNTIME_RENDER") -> None:
        self.renderer_version = version or ""
        self.stage_sources["rendererInput"] = source
        self.exact_error = error
        self.runtime_status = "PASS" if ok else "FAIL"
        if not version and ok:
            self.root_cause, self.stage = "VERSION_METADATA_UNAVAILABLE", "RUNTIME_VERSION_PROBE"
            self.recommended_fix = "Expose Mermaid version metadata or provide an authoritative bundle metadata marker."
        elif not version:
            self.root_cause, self.stage = "RENDERER_CONFIGURATION_FAILURE", "RUNTIME_VERSION_PROBE"
            self.recommended_fix = "Execute the loaded Summary runtime and expose version metadata."
        elif version != BASELINE:
            self.root_cause, self.stage = "MERMAID_VERSION_INCOMPATIBILITY", "RUNTIME_VERSION_PROBE"
            self.recommended_fix = f"Use the Summary Mermaid baseline {BASELINE}."
        elif not ok:
            self.root_cause, self.stage = "RENDERING_FAILURE", stage
            self.recommended_fix = "Fix the reported Mermaid source or renderer failure."
        else:
            self.root_cause, self.stage, self.confidence = "VALID_MERMAID", stage, "HIGH"

    def to_public(self) -> dict[str, Any]:
        hashes = self.hashes()
        blocked = self.root_cause != "VALID_MERMAID" or self.static_status != "PASS" or self.runtime_status != "PASS" or self.renderer_version != BASELINE or any(value is None for value in hashes.values())
        if any(hashes.get(key) != hashes.get("rendererInput") for key in ("staticDiagrams", "renderAllDiagramsInput", "renderStaticDiagramsInput") if hashes.get(key) is not None):
            self.root_cause, self.stage, blocked = "SOURCE_INTEGRITY_MISMATCH", "SOURCE_INTEGRITY", True
        return {
            "schemaVersion": "1.0.0", "traceId": self.trace_id, "projectName": self.project_name,
            "artifactPath": self.artifact_path, "diagramId": self.diagram_id,
            "artifactRole": "tobe" if "/tobe/" in self.artifact_path.replace("\\", "/") else "asis",
            **self.producer, "rendererVersion": self.renderer_version, "rendererSource": self.renderer_source,
            "detectedDialect": detect_dialect(self.source), "c4Detected": detect_dialect(self.source).startswith("C4") or bool(detect_constructs(self.source)),
            "c4SupportedByRenderer": self.c4_supported, "staticValidationStatus": self.static_status,
            "runtimeRenderStatus": self.runtime_status, "rootCause": self.root_cause, "stage": self.stage,
            "confidence": self.confidence, "construct": self.construct, "diagnosticEvidence": {**self.evidence, "exactErrorMessage": self.exact_error, "versionSource": self.version_source, "versionDiscoveryMethod": self.version_discovery_method, "versionDiscoveryStatus": self.version_discovery_status, "versionConfidence": self.version_confidence, "runtimeRenderSucceeded": self.runtime_status == "PASS"},
            "hashes": hashes, "exactErrorMessage": self.exact_error, "recommendedFix": self.recommended_fix,
            "publicationAllowed": not blocked,
        }


def write_reports(result: CompatibilityResult, output_dir: str | Path) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = result.to_public()
    json_path = output / "blueprint-compatibility-report.json"
    md_path = output / "blueprint-compatibility-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("# Blueprint Compatibility Report\n\n```json\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    return json_path, md_path


def validate_blueprint_artifact(
    repo_root: str | Path,
    project_name: str,
    artifact: str | Path,
    *,
    trace_id: str = "generated-locally",
    runtime_probe: dict[str, Any] | None = None,
    renderer_source: str = "src/modules/ava-fabric-agents/summary/templates/html/mermaid.min.js",
) -> dict[str, Any]:
    """Validate one real Blueprint artifact and return the public report."""
    root = Path(repo_root)
    path = root / artifact if not Path(artifact).is_absolute() else Path(artifact)
    if not path.is_file():
        result = CompatibilityResult(trace_id, project_name, path.as_posix(), path.stem, "")
        result.root_cause, result.stage, result.recommended_fix = "EVIDENCE_UNAVAILABLE", "STATIC_VALIDATION", "Upstream artifact generation/discovery must provide the Blueprint."
        result.evidence["boundary"] = "missing-artifact-upstream"
        return result.to_public()
    source = path.read_text(encoding="utf-8", errors="replace")
    relative = path.relative_to(root).as_posix()
    result = CompatibilityResult(trace_id, project_name, relative, path.stem, source, renderer_source=renderer_source)
    result.sanitized = source
    result.stage_sources["sanitizedContent"] = source
    probe = runtime_probe or {"rendererVersion": "", "renderStatus": "FAIL", "error": "Runtime probe was not executed"}
    result.validate_static(renderer_supports_c4=probe.get("c4SupportedByRenderer"))
    result.evidence["runtimeProbe"] = {
        key: probe.get(key) for key in (
            "probeExecuted", "bundleLoaded", "mermaidObjectAvailable", "initialized",
            "runtimeRenderSucceeded", "versionSource", "versionDiscoveryMethod",
            "versionDiscoveryStatus", "probeEntryPoint", "stack", "error", "c4GraphIntegrity",
        ) if key in probe
    }
    result.set_runtime(version=probe.get("rendererVersion"), source=source, ok=probe.get("renderStatus") == "PASS", error=probe.get("error", ""), stage=probe.get("stage", "RUNTIME_RENDER"))
    result.version_source = probe.get("versionSource", "unavailable")
    result.version_discovery_method = probe.get("versionDiscoveryMethod", "unavailable")
    result.version_discovery_status = probe.get("versionDiscoveryStatus", "UNAVAILABLE")
    result.version_confidence = probe.get("versionConfidence", "LOW")
    result.renderer_source = renderer_source
    for key in ("staticDiagrams", "renderAllDiagramsInput", "renderStaticDiagramsInput"):
        result.stage_sources[key] = source
    return result.to_public()


def validate_project_blueprints(repo_root: str | Path, project_name: str, *, trace_id: str = "generated-locally", runtime_probe: dict[str, Any] | None = None, runtime_probes: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Validate architecture Blueprint and all TO-BE C4 diagram paths."""
    paths = (
        f"projects/{project_name}/outputs/asis/diagrams/architecture-blueprint.mmd",
        f"projects/{project_name}/outputs/tobe/diagrams/architecture-blueprint.mmd",
        f"projects/{project_name}/outputs/tobe/diagrams/c4-context.mmd",
        f"projects/{project_name}/outputs/tobe/diagrams/c4-container.mmd",
        f"projects/{project_name}/outputs/tobe/diagrams/c4-component.mmd",
    )
    runtime_probes = runtime_probes or {}
    return [validate_blueprint_artifact(repo_root, project_name, path, trace_id=trace_id, runtime_probe=runtime_probes.get(path, runtime_probe)) for path in paths]


def publication_allowed(reports: list[dict[str, Any]]) -> bool:
    """Return true only when every required Blueprint report explicitly allows publication."""
    return bool(reports) and all(report.get("publicationAllowed") is True for report in reports)
