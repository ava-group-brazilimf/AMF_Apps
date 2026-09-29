# -*- coding: utf-8 -*-
"""Orquestração: descobrir -> ler -> calcular (§9.1).

Cada `refresh()` refaz a descoberta, relê apenas o que mudou (o cache é
invalidado por mtime/tamanho) e recalcula. Projetos removidos do disco somem
do snapshot; projetos novos entram — sem reiniciar a aplicação.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import AppConfig
from .discovery import ProjectDiscoveryService
from .errors import DiscoveryError
from .metrics import MetricsEngine
from .models import ProjectResult, ProjectStatus, Snapshot
from .reader import MetricsFileReader

LOGGER = logging.getLogger(__name__)


@dataclass
class Filters:
    """Escopo aplicado pelo dashboard. Vazio significa "tudo"."""

    projects: frozenset[str] = frozenset()
    statuses: frozenset[str] = frozenset()
    modes: frozenset[str] = frozenset()
    date_from: str = ""
    date_to: str = ""

    @classmethod
    def from_mapping(cls, values) -> "Filters":
        def many(key: str) -> frozenset[str]:
            raw = values.getlist(key) if hasattr(values, "getlist") else values.get(key)
            if raw is None:
                return frozenset()
            if isinstance(raw, str):
                raw = [raw]
            return frozenset(part.strip() for item in raw
                             for part in str(item).split(",") if part.strip())
        return cls(projects=many("project"), statuses=many("status"), modes=many("mode"),
                   date_from=str(values.get("from") or "").strip(),
                   date_to=str(values.get("to") or "").strip())

    @property
    def active(self) -> bool:
        return bool(self.projects or self.statuses or self.modes
                    or self.date_from or self.date_to)

    def matches(self, result: ProjectResult) -> bool:
        payload = result.payload or {}
        if self.projects and result.record.project_id not in self.projects:
            return False
        if self.statuses and str(payload.get("execution_status") or "") not in self.statuses:
            return False
        if self.modes and str(payload.get("execution_mode") or "") not in self.modes:
            return False
        started = str(payload.get("start_time_utc") or "")[:10]
        if self.date_from and (not started or started < self.date_from):
            return False
        if self.date_to and (not started or started > self.date_to):
            return False
        return True

    def to_dict(self) -> dict:
        return {"project": sorted(self.projects), "status": sorted(self.statuses),
                "mode": sorted(self.modes), "from": self.date_from, "to": self.date_to}


@dataclass
class DashboardView:
    """Recorte do snapshot já filtrado, com o portfólio recalculado."""

    generated_at_iso: str
    filters: Filters
    projects: list[ProjectResult] = field(default_factory=list)
    excluded: list[ProjectResult] = field(default_factory=list)
    portfolio_metrics: list = field(default_factory=list)
    facets: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    duplicates: list[dict] = field(default_factory=list)
    total_projects: int = 0


class DashboardService:
    def __init__(self, config: AppConfig, metrics_config: dict,
                 logger: logging.Logger | None = None) -> None:
        self._config = config
        self._log = logger or LOGGER
        self._discovery = ProjectDiscoveryService(config, self._log)
        self._reader = MetricsFileReader(config, self._log)
        self._engine = MetricsEngine(metrics_config, self._log)
        self._last: Snapshot | None = None

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def last_snapshot(self) -> Snapshot | None:
        return self._last

    def clear_cache(self) -> None:
        self._reader.clear_cache()

    @property
    def settings(self) -> dict:
        return dict(self._engine.settings)

    def view(self, filters: Filters | None = None) -> tuple[DashboardView | None, str | None]:
        """Redescobre, aplica o filtro e recalcula o portfólio sobre o recorte.

        O portfólio é sempre recalculado a partir dos projetos que sobraram,
        de modo que os KPIs concordam com os gráficos, e projetos removidos do
        disco nunca entram na consolidação.
        """
        snapshot = self.refresh()
        if snapshot.config_error:
            return None, snapshot.config_error

        filters = filters or Filters()
        # execuções duplicadas (mesmo execution_id em pastas diferentes)
        seen: dict[str, str] = {}
        unique, duplicates = [], []
        for result in snapshot.projects:
            execution_id = (result.payload or {}).get("execution_id")
            if result.record.is_usable and execution_id:
                if execution_id in seen:
                    duplicates.append({"project_id": result.record.project_id,
                                       "duplicate_of": seen[execution_id],
                                       "execution_id": execution_id})
                    continue
                seen[execution_id] = result.record.project_id
            unique.append(result)

        selected = [r for r in unique if filters.matches(r)]
        excluded = [r for r in unique if r not in selected]
        portfolio = self._engine.compute_portfolio(selected)

        usable = [r for r in unique if r.record.is_usable]
        facets = {
            "projects": sorted({r.record.project_id for r in unique}),
            "statuses": sorted({str((r.payload or {}).get("execution_status"))
                                for r in usable if (r.payload or {}).get("execution_status")}),
            "modes": sorted({str((r.payload or {}).get("execution_mode"))
                             for r in usable if (r.payload or {}).get("execution_mode")}),
        }

        view = DashboardView(
            generated_at_iso=snapshot.generated_at_iso,
            filters=filters,
            projects=selected,
            excluded=excluded,
            portfolio_metrics=portfolio,
            facets=facets,
            warnings=snapshot.warnings,
            duplicates=duplicates,
            total_projects=len(unique),
        )
        return view, None

    def refresh(self) -> Snapshot:
        started = datetime.now(timezone.utc)
        self._log.info("descoberta iniciada em %s (raiz definida por %s)",
                       self._config.projects_root, self._config.projects_root_source)

        try:
            discovery = self._discovery.discover()
        except DiscoveryError as exc:
            self._log.error("descoberta falhou: %s", exc)
            snapshot = Snapshot(generated_at=started, config_error=str(exc))
            self._last = snapshot
            return snapshot

        results: list[ProjectResult] = []
        warnings: list[str] = []

        for record in discovery.projects:
            read = self._reader.read(record)
            record.status = read.status
            record.metrics_file_valid = read.ok
            if read.last_modified is not None:
                record.metrics_last_modified = read.last_modified
            if read.size_bytes is not None:
                record.metrics_size_bytes = read.size_bytes
            for message in read.errors:
                if message not in record.errors:
                    record.errors.append(message)

            metrics = self._engine.compute_project(read.payload)
            results.append(ProjectResult(record=record, metrics=metrics,
                                         payload=read.payload))

            self._log.info("projeto %s | leitura %s%s | %s",
                           record.project_id, read.status,
                           " (cache)" if read.from_cache else "",
                           "; ".join(read.errors) or "sem ressalvas")

            if record.status not in ProjectStatus.USABLE:
                warnings.append("%s: %s" % (record.project_id,
                                            record.errors[0] if record.errors else record.status))
            elif record.status == ProjectStatus.PARTIALLY_AVAILABLE:
                warnings.append("%s: métricas parcialmente disponíveis" % record.project_id)

        portfolio = self._engine.compute_portfolio(results)

        snapshot = Snapshot(
            generated_at=datetime.now(timezone.utc),
            projects=results,
            portfolio_metrics=portfolio,
            added_projects=discovery.added,
            removed_projects=discovery.removed,
            warnings=warnings,
        )
        self._last = snapshot
        self._log.info("descoberta concluída: %d projeto(s), %d utilizável(is), "
                       "%d adicionado(s), %d removido(s)",
                       len(results), sum(1 for r in results if r.record.is_usable),
                       len(discovery.added), len(discovery.removed))
        return snapshot
