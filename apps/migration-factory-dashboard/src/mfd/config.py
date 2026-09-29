# -*- coding: utf-8 -*-
"""Carregamento e validação da configuração.

O diretório raiz dos projetos é declarado em UM único lugar (config/app.yaml)
e pode ser sobrescrito pela variável de ambiente. Precedência (§5.2):

    1. MIGRATION_FACTORY_PROJECTS_ROOT
    2. projects.root_directory em config/app.yaml
    3. ConfigurationError — falha controlada
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .errors import ConfigurationError

ENV_PROJECTS_ROOT = "MIGRATION_FACTORY_PROJECTS_ROOT"
ENV_APP_CONFIG = "MIGRATION_FACTORY_APP_CONFIG"
ENV_METRICS_CONFIG = "MIGRATION_FACTORY_METRICS_CONFIG"

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigurationError("arquivo de configuração não encontrado: %s" % path.name)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigurationError("YAML inválido em %s: %s" % (path.name, exc)) from exc
    except OSError as exc:
        raise ConfigurationError("não foi possível ler %s: %s" % (path.name, exc.strerror)) from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigurationError("%s deve conter um mapeamento na raiz" % path.name)
    return data


def _normalize_relative(value: str) -> tuple[str, ...]:
    """`outputs\\pipeline_runner` -> ('outputs', 'pipeline_runner').

    Aceita separador de qualquer plataforma para que a mesma configuração
    funcione no Windows e em runners Linux.
    """
    cleaned = str(value).replace("\\", "/").strip("/")
    return tuple(part for part in cleaned.split("/") if part and part != ".")


@dataclass(frozen=True)
class MetricsFileConfig:
    relative_parts: tuple[str, ...]
    file_name: str
    file_format: str
    encoding: str

    def path_for(self, project_directory: Path) -> Path:
        return project_directory.joinpath(*self.relative_parts) / self.file_name

    @property
    def relative_display(self) -> str:
        return "/".join(self.relative_parts + (self.file_name,))


@dataclass(frozen=True)
class ReadConfig:
    stability_retries: int = 3
    retry_delay_seconds: float = 0.05
    max_file_bytes: int = 32 * 1024 * 1024


@dataclass(frozen=True)
class CacheConfig:
    enabled: bool = True
    max_entries: int = 256


@dataclass(frozen=True)
class SortConfig:
    field: str = "directory_name"
    order: str = "asc"

    @property
    def reverse(self) -> bool:
        return str(self.order).lower() == "desc"


@dataclass(frozen=True)
class AppConfig:
    projects_root: Path
    projects_root_source: str
    discovery_mode: str
    project_name_source: str
    ignored_directories: frozenset[str]
    metrics_file: MetricsFileConfig
    refresh_strategy: str
    refresh_interval_seconds: int
    removed_project_behavior: str
    missing_metrics_file_behavior: str
    invalid_metrics_file_behavior: str
    sort: SortConfig
    read: ReadConfig
    cache: CacheConfig
    logging_level: str
    logging_format: str
    server: Mapping[str, Any] = field(default_factory=dict)

    def is_ignored(self, directory_name: str) -> bool:
        return directory_name.casefold() in self.ignored_directories


def _resolve_root(projects_cfg: Mapping[str, Any], env: Mapping[str, str]) -> tuple[Path, str]:
    env_value = (env.get(ENV_PROJECTS_ROOT) or "").strip()
    if env_value:
        return Path(env_value).expanduser(), "environment:%s" % ENV_PROJECTS_ROOT

    yaml_value = str(projects_cfg.get("root_directory") or "").strip()
    if yaml_value:
        return Path(yaml_value).expanduser(), "app.yaml:projects.root_directory"

    raise ConfigurationError(
        "diretório raiz dos projetos não definido — informe %s ou "
        "projects.root_directory em config/app.yaml" % ENV_PROJECTS_ROOT
    )


def load_app_config(
    config_path: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    *,
    require_existing_root: bool = True,
) -> AppConfig:
    """Carrega config/app.yaml aplicando a precedência do diretório raiz."""
    env = os.environ if env is None else env
    if config_path is None:
        config_path = env.get(ENV_APP_CONFIG) or (DEFAULT_CONFIG_DIR / "app.yaml")
    raw = _read_yaml(Path(config_path))

    projects_cfg = raw.get("projects") or {}
    if not isinstance(projects_cfg, dict):
        raise ConfigurationError("app.yaml: a seção `projects` deve ser um mapeamento")

    root, source = _resolve_root(projects_cfg, env)
    if require_existing_root:
        if not root.exists():
            raise ConfigurationError("diretório raiz de projetos não existe: %s" % root)
        if not root.is_dir():
            raise ConfigurationError("o caminho raiz de projetos não é um diretório: %s" % root)
        if not os.access(root, os.R_OK):
            raise ConfigurationError("sem permissão de leitura no diretório raiz: %s" % root)

    metrics_cfg = projects_cfg.get("metrics") or {}
    if not isinstance(metrics_cfg, dict):
        raise ConfigurationError("app.yaml: `projects.metrics` deve ser um mapeamento")
    relative = _normalize_relative(metrics_cfg.get("relative_directory", "outputs/pipeline_runner"))
    file_name = str(metrics_cfg.get("file_name") or "pipeline-runner-metrics.json")
    if not relative or not file_name:
        raise ConfigurationError("app.yaml: caminho relativo do arquivo de métricas inválido")
    file_format = str(metrics_cfg.get("file_format") or "json").lower()
    if file_format != "json":
        raise ConfigurationError("formato de métricas não suportado: %s" % file_format)

    ignored: Sequence[Any] = projects_cfg.get("ignored_directories") or []
    if not isinstance(ignored, (list, tuple)):
        raise ConfigurationError("app.yaml: `ignored_directories` deve ser uma lista")

    refresh_cfg = projects_cfg.get("refresh") or {}
    sort_cfg = projects_cfg.get("sort") or {}
    read_cfg = projects_cfg.get("read") or {}
    cache_cfg = projects_cfg.get("cache") or {}
    log_cfg = raw.get("logging") or {}

    return AppConfig(
        projects_root=root,
        projects_root_source=source,
        discovery_mode=str(projects_cfg.get("discovery_mode") or "immediate_subdirectories"),
        project_name_source=str(projects_cfg.get("project_name_source") or "directory_name"),
        ignored_directories=frozenset(str(name).casefold() for name in ignored),
        metrics_file=MetricsFileConfig(relative, file_name, file_format,
                                       str(metrics_cfg.get("encoding") or "utf-8")),
        refresh_strategy=str(refresh_cfg.get("strategy") or "request"),
        refresh_interval_seconds=int(refresh_cfg.get("interval_seconds") or 30),
        removed_project_behavior=str(projects_cfg.get("removed_project_behavior")
                                     or "remove_from_dashboard"),
        missing_metrics_file_behavior=str(projects_cfg.get("missing_metrics_file_behavior")
                                          or "show_as_unavailable"),
        invalid_metrics_file_behavior=str(projects_cfg.get("invalid_metrics_file_behavior")
                                          or "show_error_and_continue"),
        sort=SortConfig(str(sort_cfg.get("field") or "directory_name"),
                        str(sort_cfg.get("order") or "asc")),
        read=ReadConfig(max(1, int(read_cfg.get("stability_retries", 3))),
                        float(read_cfg.get("retry_delay_seconds", 0.05)),
                        int(read_cfg.get("max_file_bytes", 32 * 1024 * 1024))),
        cache=CacheConfig(bool(cache_cfg.get("enabled", True)),
                          int(cache_cfg.get("max_entries", 256))),
        logging_level=str(log_cfg.get("level") or "INFO"),
        logging_format=str(log_cfg.get("format") or "%(asctime)s %(levelname)s %(name)s | %(message)s"),
        server=raw.get("server") or {},
    )


def load_metrics_config(
    config_path: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> dict:
    """Carrega config/metrics.yaml (definições de métrica, sem projetos)."""
    env = os.environ if env is None else env
    if config_path is None:
        config_path = env.get(ENV_METRICS_CONFIG) or (DEFAULT_CONFIG_DIR / "metrics.yaml")
    raw = _read_yaml(Path(config_path))

    definitions = raw.get("metrics") or []
    if not isinstance(definitions, list):
        raise ConfigurationError("metrics.yaml: `metrics` deve ser uma lista")

    seen: set[str] = set()
    for item in definitions:
        if not isinstance(item, dict):
            raise ConfigurationError("metrics.yaml: cada métrica deve ser um mapeamento")
        metric_id = item.get("id")
        if not metric_id:
            raise ConfigurationError("metrics.yaml: métrica sem `id`")
        if metric_id in seen:
            raise ConfigurationError("metrics.yaml: id de métrica duplicado: %s" % metric_id)
        seen.add(metric_id)
        if item.get("scope") not in ("project", "portfolio"):
            raise ConfigurationError(
                "metrics.yaml: métrica %s precisa de scope 'project' ou 'portfolio'" % metric_id)
        if "projects" in item or "project_list" in item:
            raise ConfigurationError(
                "metrics.yaml: métrica %s não pode fixar uma lista de projetos" % metric_id)

    raw.setdefault("settings", {})
    raw["metrics"] = definitions
    return raw
