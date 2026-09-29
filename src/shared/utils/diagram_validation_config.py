"""Configuration resolution for Mermaid diagram validation."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

DEFAULTS: dict[str, Any] = {
    "mermaid": {
        "acceptanceBaselineVersion": "11.14.0",
        "rendererVersion": "11.14.0",
        "strictCompatibility": True,
    },
    "renderingProfile": {
        "viewportWidth": 1440, "viewportHeight": 900, "zoomLevel": 1.0,
        "fontFamily": "Arial, sans-serif", "fontSizePx": 14,
        "theme": "default", "deviceScaleFactor": 1,
    },
    "readability": {
        "maxBlockingOverlaps": 0,
        "maxLabelContainerOverlapPercent": 0,
        "maxLabelBoundaryOverlapPercent": 0,
        "maxLabelCardOverlapPercent": 0,
        "maxLabelComponentOverlapPercent": 0,
        "maxCriticalEdgeCrossings": 0,
        "maxTotalEdgeCrossingsWarning": 10,
        "maxNodeLabelLengthChars": 60,
        "maxRelationshipLabelLengthChars": 80,
        "maxNodesPerDiagramWarning": 25,
        "maxEdgesPerDiagramWarning": 35,
        "minLabelToElementSpacingPx": 8,
        "minNodeSpacingPx": 24,
    },
}

@dataclass(frozen=True)
class DiagramValidationConfig:
    values: dict[str, Any]
    source: str

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

class DiagramValidationConfigError(ValueError):
    pass

class DiagramValidationConfigLoader:
    """Loads the project override and applies defaults only to optional keys."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self.path = self.project_root / ".config" / "diagram-validation.yaml"

    def load(self) -> DiagramValidationConfig:
        if yaml is None:
            raise DiagramValidationConfigError("PyYAML is required to load diagram validation configuration")
        if not self.path.is_file():
            raise DiagramValidationConfigError(f"Missing configuration: {self.path}")
        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DiagramValidationConfigError(f"Malformed configuration: {exc}") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("diagramValidation"), dict):
            raise DiagramValidationConfigError("diagramValidation must be an object")
        source = raw["diagramValidation"]
        if not isinstance(source.get("mermaid"), dict):
            raise DiagramValidationConfigError("diagramValidation.mermaid must be an object")
        values = deepcopy(DEFAULTS)
        for section in ("mermaid", "renderingProfile", "readability"):
            if section in source:
                if not isinstance(source[section], dict):
                    raise DiagramValidationConfigError(f"diagramValidation.{section} must be an object")
                values[section].update(source[section])
        self._validate(values)
        return DiagramValidationConfig(values=values, source=str(self.path))

    @staticmethod
    def _validate(values: dict[str, Any]) -> None:
        mermaid = values["mermaid"]
        if not all(isinstance(mermaid[k], str) and mermaid[k] for k in ("acceptanceBaselineVersion", "rendererVersion")):
            raise DiagramValidationConfigError("Mermaid versions must be non-empty strings")
        if not isinstance(mermaid["strictCompatibility"], bool):
            raise DiagramValidationConfigError("strictCompatibility must be boolean")
        profile = values["renderingProfile"]
        ranges = {"viewportWidth": (320, 7680), "viewportHeight": (240, 4320), "fontSizePx": (8, 32)}
        for key, (lo, hi) in ranges.items():
            if not isinstance(profile[key], int) or not lo <= profile[key] <= hi:
                raise DiagramValidationConfigError(f"Invalid renderingProfile.{key}")
        if not isinstance(profile["zoomLevel"], (int, float)) or not .25 <= profile["zoomLevel"] <= 4:
            raise DiagramValidationConfigError("Invalid renderingProfile.zoomLevel")
        if not isinstance(profile["deviceScaleFactor"], (int, float)) or not 1 <= profile["deviceScaleFactor"] <= 4:
            raise DiagramValidationConfigError("Invalid renderingProfile.deviceScaleFactor")
        if not isinstance(profile["fontFamily"], str) or not profile["fontFamily"] or not isinstance(profile["theme"], str) or not profile["theme"]:
            raise DiagramValidationConfigError("Invalid renderingProfile font settings")
        readability = values["readability"]
        for key, value in readability.items():
            if not isinstance(value, int) or value < 0:
                raise DiagramValidationConfigError(f"Invalid readability.{key}")
