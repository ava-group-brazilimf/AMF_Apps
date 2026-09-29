# -*- coding: utf-8 -*-
"""Leitura e validação do pipeline-runner-metrics.json (§8, §8.1, §9.2).

O arquivo é aberto somente para leitura. Nada é bloqueado, renomeado, movido
ou modificado — ele pertence ao pipeline runner.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from .config import AppConfig
from .models import ProjectRecord, ProjectStatus, ReadResult

LOGGER = logging.getLogger(__name__)

#: campos sem os quais nenhuma métrica de projeto faz sentido
REQUIRED_FIELDS = ("execution_id", "project_name")

#: campos esperados; ausência degrada para partially_available, não derruba
EXPECTED_NUMERIC = ("total_duration_seconds",)
EXPECTED_DATETIME = ("start_time_utc", "end_time_utc")

KNOWN_EXECUTION_STATUSES = {
    "completed", "completed_with_warnings", "aborted", "running",
    "interrupted", "failed",
}
KNOWN_PHASE_STATUSES = {
    "executed", "degraded", "aborted", "skipped", "validation_failed", "pending",
}


def _parse_iso(value: str) -> datetime | None:
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class MetricsFileReader:
    """Lê, valida e normaliza o arquivo de métricas de um projeto.

    Cache opcional com chave (caminho, mtime, tamanho): um arquivo alterado
    produz outra chave e portanto é relido. O cache guarda apenas conteúdo já
    lido — nunca a lista de projetos —, então não impede a descoberta de
    projetos novos nem preserva projetos removidos.
    """

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._log = logger or LOGGER
        self._cache: dict[tuple[str, float, int], dict[str, Any]] = {}

    # -- API pública ----------------------------------------------------
    def read(self, record: ProjectRecord) -> ReadResult:
        if not record.metrics_file_exists:
            return ReadResult(status=ProjectStatus.METRICS_UNAVAILABLE,
                              errors=["arquivo de métricas não encontrado"])
        if record.status == ProjectStatus.READ_ERROR and record.errors:
            return ReadResult(status=ProjectStatus.READ_ERROR, errors=list(record.errors))

        raw, meta, error = self._read_stable(record)
        if error is not None:
            return error

        mtime, size = meta
        last_modified = datetime.fromtimestamp(mtime, tz=timezone.utc)

        if not raw.strip():
            self._log.warning("projeto %s | arquivo vazio", record.project_id)
            return ReadResult(status=ProjectStatus.EMPTY_FILE, errors=["arquivo vazio"],
                              last_modified=last_modified, size_bytes=size)

        cache_key = (str(record.metrics_file), mtime, size)
        cached = self._cache.get(cache_key) if self._config.cache.enabled else None
        if cached is not None:
            return ReadResult(status=cached["status"], payload=cached["payload"],
                              errors=list(cached["errors"]), last_modified=last_modified,
                              size_bytes=size, from_cache=True)

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._log.warning("projeto %s | JSON inválido na linha %d", record.project_id, exc.lineno)
            return ReadResult(status=ProjectStatus.INVALID_JSON,
                              errors=["JSON inválido (linha %d, coluna %d)" % (exc.lineno, exc.colno)],
                              last_modified=last_modified, size_bytes=size)

        if not isinstance(payload, dict):
            self._log.warning("projeto %s | raiz do JSON é %s, esperado objeto",
                              record.project_id, type(payload).__name__)
            return ReadResult(status=ProjectStatus.INCOMPATIBLE_SCHEMA,
                              errors=["o elemento raiz do JSON deve ser um objeto"],
                              last_modified=last_modified, size_bytes=size)

        status, errors = self._validate(record, payload)
        if status == ProjectStatus.INCOMPATIBLE_SCHEMA:
            return ReadResult(status=status, errors=errors,
                              last_modified=last_modified, size_bytes=size)

        if self._config.cache.enabled:
            self._store(cache_key, {"status": status, "payload": payload, "errors": errors})

        return ReadResult(status=status, payload=payload, errors=errors,
                          last_modified=last_modified, size_bytes=size)

    def clear_cache(self) -> None:
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    # -- internos -------------------------------------------------------
    def _read_stable(self, record: ProjectRecord):
        """Lê garantindo que o arquivo não mudou durante a leitura (§9.2)."""
        path = record.metrics_file
        encoding = self._config.metrics_file.encoding
        attempts = self._config.read.stability_retries

        for attempt in range(1, attempts + 1):
            try:
                before = path.stat()
                if before.st_size > self._config.read.max_file_bytes:
                    return None, None, ReadResult(
                        status=ProjectStatus.READ_ERROR,
                        errors=["arquivo de métricas excede o tamanho máximo permitido"])
                with path.open("r", encoding=encoding, errors="strict") as fh:
                    raw = fh.read()
                after = path.stat()
            except FileNotFoundError:
                return None, None, ReadResult(status=ProjectStatus.METRICS_UNAVAILABLE,
                                              errors=["arquivo de métricas não encontrado"])
            except PermissionError:
                return None, None, ReadResult(status=ProjectStatus.READ_ERROR,
                                              errors=["sem permissão de leitura no arquivo"])
            except UnicodeDecodeError:
                return None, None, ReadResult(
                    status=ProjectStatus.READ_ERROR,
                    errors=["arquivo não está em %s" % encoding])
            except OSError as exc:
                return None, None, ReadResult(status=ProjectStatus.READ_ERROR,
                                              errors=["falha de leitura: %s" % (exc.strerror or "erro de E/S")])

            if (before.st_mtime_ns, before.st_size) == (after.st_mtime_ns, after.st_size):
                return raw, (after.st_mtime, after.st_size), None

            self._log.info("projeto %s | arquivo alterado durante a leitura (tentativa %d/%d)",
                           record.project_id, attempt, attempts)
            time.sleep(self._config.read.retry_delay_seconds)

        self._log.warning("projeto %s | arquivo instável após %d tentativas — métrica "
                          "temporariamente indisponível", record.project_id, attempts)
        return None, None, ReadResult(
            status=ProjectStatus.READ_ERROR,
            errors=["arquivo sendo gravado pelo pipeline; leitura temporariamente indisponível"])

    def _validate(self, record: ProjectRecord, payload: dict) -> tuple[str, list[str]]:
        """Valida campos e tipos. Retorna (status, avisos)."""
        errors: list[str] = []

        missing_required = [f for f in REQUIRED_FIELDS if f not in payload]
        if missing_required:
            return ProjectStatus.INCOMPATIBLE_SCHEMA, [
                "campos obrigatórios ausentes: %s" % ", ".join(missing_required)]

        degraded = False

        for name in EXPECTED_NUMERIC:
            if name not in payload:
                errors.append("campo ausente: %s" % name)
                degraded = True
            elif not isinstance(payload[name], (int, float)) or isinstance(payload[name], bool):
                errors.append("campo %s não é numérico" % name)
                degraded = True

        for name in EXPECTED_DATETIME:
            value = payload.get(name)
            if value in (None, ""):
                continue                            # vazio é legítimo: fase sem horário
            if not isinstance(value, str) or _parse_iso(value) is None:
                errors.append("campo %s não é uma data/hora ISO válida" % name)
                degraded = True

        tokens = payload.get("token_metrics")
        if tokens is None:
            errors.append("campo ausente: token_metrics")
            degraded = True
        elif not isinstance(tokens, dict):
            errors.append("token_metrics deveria ser um objeto")
            degraded = True
        else:
            for key in ("total_tokens", "token_in", "token_out"):
                if key in tokens and (not isinstance(tokens[key], (int, float))
                                      or isinstance(tokens[key], bool)):
                    errors.append("token_metrics.%s não é numérico" % key)
                    degraded = True

        phases = payload.get("phase_metrics")
        if phases is None:
            errors.append("campo ausente: phase_metrics")
            degraded = True
        elif not isinstance(phases, list):
            errors.append("phase_metrics deveria ser uma lista")
            degraded = True
        else:
            bad_phases = 0
            for phase in phases:
                if not isinstance(phase, dict):
                    bad_phases += 1
                    continue
                duration = phase.get("duration_seconds")
                if duration is not None and (not isinstance(duration, (int, float))
                                             or isinstance(duration, bool)):
                    bad_phases += 1
            if bad_phases:
                errors.append("%d fase(s) com estrutura inesperada" % bad_phases)
                degraded = True

        status_value = payload.get("execution_status")
        if isinstance(status_value, str) and status_value not in KNOWN_EXECUTION_STATUSES:
            errors.append("status de execução não reconhecido: %s" % status_value)

        unknown_phase = {
            p.get("status") for p in (phases or []) if isinstance(p, dict)
            and isinstance(p.get("status"), str) and p.get("status") not in KNOWN_PHASE_STATUSES
        }
        if unknown_phase:
            errors.append("status de fase não reconhecido: %s" % ", ".join(sorted(unknown_phase)))

        if errors:
            self._log.info("projeto %s | validação com ressalvas: %s",
                           record.project_id, "; ".join(errors))
        return (ProjectStatus.PARTIALLY_AVAILABLE if degraded else ProjectStatus.AVAILABLE), errors

    def _store(self, key, value) -> None:
        if len(self._cache) >= self._config.cache.max_entries:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value
