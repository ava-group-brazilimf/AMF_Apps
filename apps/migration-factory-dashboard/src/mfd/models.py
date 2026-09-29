# -*- coding: utf-8 -*-
"""Objetos normalizados compartilhados entre descoberta, leitura e cálculo."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ProjectStatus:
    """Classificação da leitura de um projeto (§8.1)."""

    AVAILABLE = "available"
    PARTIALLY_AVAILABLE = "partially_available"
    METRICS_UNAVAILABLE = "metrics_unavailable"
    EMPTY_FILE = "empty_file"
    INVALID_JSON = "invalid_json"
    INCOMPATIBLE_SCHEMA = "incompatible_schema"
    READ_ERROR = "read_error"

    ALL = (AVAILABLE, PARTIALLY_AVAILABLE, METRICS_UNAVAILABLE, EMPTY_FILE,
           INVALID_JSON, INCOMPATIBLE_SCHEMA, READ_ERROR)
    #: estados em que ao menos parte das métricas pôde ser calculada
    USABLE = (AVAILABLE, PARTIALLY_AVAILABLE)


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


@dataclass
class ProjectRecord:
    """Projeto descoberto no diretório raiz.

    `project_directory` e `metrics_file` são caminhos absolutos usados apenas
    internamente e em log de diagnóstico. As respostas HTTP expõem somente o
    caminho relativo (§7, "não expor caminhos internos completos").
    """

    project_id: str
    project_name: str
    project_directory: Path
    metrics_file: Path
    metrics_relative_path: str
    metrics_file_exists: bool = False
    metrics_file_valid: bool = False
    metrics_last_modified: datetime | None = None
    metrics_size_bytes: int | None = None
    status: str = ProjectStatus.METRICS_UNAVAILABLE
    errors: list[str] = field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        return self.status in ProjectStatus.USABLE

    def to_public_dict(self) -> dict[str, Any]:
        """Representação segura para API e template."""
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "status": self.status,
            "metrics_file": self.metrics_relative_path,
            "metrics_file_exists": self.metrics_file_exists,
            "metrics_file_valid": self.metrics_file_valid,
            "metrics_last_modified": _iso(self.metrics_last_modified),
            "errors": list(self.errors),
        }

    def to_diagnostic_dict(self) -> dict[str, Any]:
        """Inclui caminhos absolutos — só para log local, nunca para HTTP."""
        data = self.to_public_dict()
        data["project_directory"] = str(self.project_directory)
        data["metrics_file_absolute"] = str(self.metrics_file)
        return data


@dataclass
class ReadResult:
    """Resultado da leitura de um arquivo de métricas."""

    status: str
    payload: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    last_modified: datetime | None = None
    size_bytes: int | None = None
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return self.payload is not None


@dataclass
class MetricValue:
    """Valor calculado de uma métrica, disponível ou não."""

    id: str
    name: str
    value: Any = None
    available: bool = True
    reason: str | None = None
    description: str = ""
    category: str = ""
    unit: str | None = None
    format: str = "text"
    display_type: str = "table"
    order: int = 0
    scope: str = "project"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "scope": self.scope,
            "value": self.value,
            "available": self.available,
            "reason": self.reason,
            "unit": self.unit,
            "format": self.format,
            "display_type": self.display_type,
            "order": self.order,
        }


@dataclass
class ProjectResult:
    """Projeto + métricas calculadas + o payload que as originou.

    O payload fica retido para que a camada web possa filtrar por campos da
    execução e devolver os runs crus ao dashboard, sem reler o disco.
    """

    record: ProjectRecord
    metrics: list[MetricValue] = field(default_factory=list)
    payload: dict[str, Any] | None = None

    def metric(self, metric_id: str) -> MetricValue | None:
        for item in self.metrics:
            if item.id == metric_id:
                return item
        return None

    def to_dict(self) -> dict[str, Any]:
        data = self.record.to_public_dict()
        data["metrics"] = [m.to_dict() for m in self.metrics]
        return data


@dataclass
class Snapshot:
    """Estado completo de uma leitura do diretório de projetos."""

    generated_at: datetime
    projects: list[ProjectResult] = field(default_factory=list)
    portfolio_metrics: list[MetricValue] = field(default_factory=list)
    added_projects: list[str] = field(default_factory=list)
    removed_projects: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    config_error: str | None = None

    @property
    def generated_at_iso(self) -> str:
        return _iso(self.generated_at) or ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "error" if self.config_error else "success",
            "generated_at": self.generated_at_iso,
            "portfolio_metrics": [m.to_dict() for m in self.portfolio_metrics],
            "projects": [p.to_dict() for p in self.projects],
            "warnings": list(self.warnings),
        }
