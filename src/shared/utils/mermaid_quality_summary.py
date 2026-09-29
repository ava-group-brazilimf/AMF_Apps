"""Stable Summary metadata adapter for Mermaid quality artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MermaidQualitySummaryAdapter:
    """Reads the canonical report and gate JSON files for Summary consumers."""

    def __init__(self, summary_directory: str | Path):
        self.directory = Path(summary_directory)

    def read(self) -> dict[str, Any]:
        report = self._read_json("mermaid-quality-report.json")
        gate = self._read_json("mermaid-quality-gate.json")
        return {
            "overallStatus": gate.get("status", report.get("status", "NOT_RUN")),
            "publicationAllowed": bool(gate.get("publicationAllowed", False)),
            "rendererStatus": gate.get("rendererStatus", "NOT_RUN"),
            "executionEnvironment": gate.get("executionEnvironment", "local"),
            "blockingFindings": int(gate.get("blockingFindings", report.get("blockingFindings", 0))),
            "warningFindings": int(gate.get("warningFindings", report.get("warningFindings", 0))),
            "affectedArtifacts": gate.get("affectedArtifactPaths", []),
            "affectedDiagrams": gate.get("affectedDiagramIds", []),
        }

    def _read_json(self, filename: str) -> dict[str, Any]:
        path = self.directory / filename
        if not path.is_file():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}
