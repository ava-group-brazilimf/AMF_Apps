# -*- coding: utf-8 -*-
"""Descoberta dinâmica de projetos (§7).

Serviço isolado: as rotas Flask nunca tocam o sistema de arquivos. Aqui só há
listagem de diretório e verificação de existência — a leitura e a interpretação
do JSON ficam em reader.py, e o cálculo em metrics.py.

Não existe cache da LISTA de projetos: cada `discover()` relê o diretório, de
modo que inclusões e remoções aparecem sem reiniciar a aplicação.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig
from .errors import DiscoveryError
from .models import ProjectRecord, ProjectStatus

LOGGER = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    projects: list[ProjectRecord] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    scanned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectDiscoveryService:
    """Lista os subdiretórios imediatos do diretório raiz configurado."""

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._log = logger or LOGGER
        self._previous_ids: set[str] = set()

    # -- API pública ----------------------------------------------------
    def discover(self) -> DiscoveryResult:
        root = self._config.projects_root
        directories = self._list_project_directories(root)

        records = [self._build_record(path) for path in directories]
        records.sort(key=self._sort_key, reverse=self._config.sort.reverse)

        current_ids = {r.project_id for r in records}
        added = sorted(current_ids - self._previous_ids) if self._previous_ids else []
        removed = sorted(self._previous_ids - current_ids)
        first_scan = not self._previous_ids
        self._previous_ids = current_ids

        for project_id in added:
            self._log.info("projeto adicionado desde a leitura anterior: %s", project_id)
        for project_id in removed:
            self._log.info("projeto removido desde a leitura anterior: %s", project_id)
        if first_scan:
            self._log.info("primeira leitura: %d projeto(s) em %s", len(records), root)

        return DiscoveryResult(projects=records, added=added, removed=removed)

    # -- internos -------------------------------------------------------
    def _list_project_directories(self, root: Path) -> list[Path]:
        if not root.exists():
            raise DiscoveryError("diretório raiz de projetos não existe: %s" % root)
        if not root.is_dir():
            raise DiscoveryError("o caminho raiz de projetos não é um diretório: %s" % root)
        try:
            entries = list(os.scandir(root))
        except PermissionError as exc:
            raise DiscoveryError("sem permissão de leitura no diretório raiz: %s"
                                 % (exc.strerror or root)) from exc
        except OSError as exc:
            raise DiscoveryError("falha ao listar o diretório raiz: %s"
                                 % (exc.strerror or exc)) from exc

        found: list[Path] = []
        for entry in entries:
            try:
                if not entry.is_dir():
                    continue                       # arquivos soltos não são projeto
            except OSError:
                continue
            if self._config.is_ignored(entry.name):
                self._log.debug("diretório ignorado por configuração: %s", entry.name)
                continue
            found.append(Path(entry.path))
        return found

    def _build_record(self, directory: Path) -> ProjectRecord:
        name = directory.name
        metrics_file = self._config.metrics_file.path_for(directory)
        relative = "%s/%s" % (name, self._config.metrics_file.relative_display)

        record = ProjectRecord(
            project_id=name,
            project_name=name if self._config.project_name_source == "directory_name" else name,
            project_directory=directory,
            metrics_file=metrics_file,
            metrics_relative_path=relative,
        )

        try:
            stat = metrics_file.stat()
        except FileNotFoundError:
            record.status = ProjectStatus.METRICS_UNAVAILABLE
            record.errors.append("arquivo de métricas não encontrado")
            self._log.info("projeto %s | %s | arquivo AUSENTE", name, relative)
            return record
        except PermissionError:
            record.metrics_file_exists = True
            record.status = ProjectStatus.READ_ERROR
            record.errors.append("sem permissão de leitura no arquivo de métricas")
            self._log.warning("projeto %s | %s | sem permissão de leitura", name, relative)
            return record
        except OSError as exc:
            record.status = ProjectStatus.READ_ERROR
            record.errors.append("falha ao acessar o arquivo de métricas")
            self._log.warning("projeto %s | %s | erro de acesso: %s", name, relative, exc.strerror)
            return record

        record.metrics_file_exists = True
        record.metrics_size_bytes = stat.st_size
        record.metrics_last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        self._log.info("projeto %s | %s | arquivo encontrado (%d bytes, mtime %s)",
                       name, relative, stat.st_size,
                       record.metrics_last_modified.isoformat())
        return record

    def _sort_key(self, record: ProjectRecord):
        field_name = self._config.sort.field
        if field_name == "status":
            return (record.status.casefold(), record.project_id.casefold())
        if field_name == "project_name":
            return (record.project_name.casefold(),)
        return (record.project_id.casefold(),)     # directory_name (padrão)
