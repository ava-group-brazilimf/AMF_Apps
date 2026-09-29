# -*- coding: utf-8 -*-
"""Fixtures compartilhadas.

Todo teste que cria, altera ou remove arquivos usa `tmp_path`. O diretório real
`projects/` é usado apenas em test_real_data.py, e somente para leitura.
"""
from __future__ import annotations

import json
import zlib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parents[1]
REAL_PROJECTS_ROOT = REPO_ROOT / "projects"
REAL_APP_CONFIG = APP_ROOT / "config" / "app.yaml"
REAL_METRICS_CONFIG = APP_ROOT / "config" / "metrics.yaml"


def sample_payload(project_name: str = "demo", **overrides) -> dict:
    """Payload no mesmo formato do pipeline-runner-metrics.json real."""
    # execution_id distinto por projeto: dois projetos com o mesmo id são
    # tratados como a MESMA execução (deduplicada na consolidação)
    payload = {
        "execution_id": "runner19-%d" % (1700000000 + zlib.crc32(project_name.encode()) % 100000),
        "project_name": project_name,
        "execution_mode": "full",
        "execution_status": "completed_with_warnings",
        "start_time_utc": "2026-08-26T14:42:43Z",
        "end_time_utc": "2026-08-26T20:29:38Z",
        "total_duration_seconds": 20815.0,
        "total_hours": "05:46:55",
        "token_metrics": {"total_tokens": 300, "token_in": 200, "token_out": 100},
        "phase_metrics": [
            {"phase_name": "F0", "status": "executed",
             "start_time_utc": "2026-08-26T14:42:43Z", "end_time_utc": "2026-08-26T14:45:31Z",
             "duration_seconds": 168.0, "total_hours": "00:02:48",
             "token_usage": {"total_tokens": 0, "token_in": 0, "token_out": 0}},
            {"phase_name": "F1", "status": "executed",
             "start_time_utc": "2026-08-26T14:45:38Z", "end_time_utc": "2026-08-26T14:54:02Z",
             "duration_seconds": 504.0, "total_hours": "00:08:24",
             "token_usage": {"total_tokens": 300, "token_in": 200, "token_out": 100}},
            {"phase_name": "F2", "status": "degraded",
             "start_time_utc": "", "end_time_utc": "",
             "duration_seconds": 0.0, "total_hours": "00:00:00",
             "token_usage": {"total_tokens": 0, "token_in": 0, "token_out": 0}},
        ],
    }
    payload.update(overrides)
    return payload


def write_project(root: Path, name: str, payload: dict | str | None,
                  relative=("outputs", "pipeline_runner"),
                  file_name: str = "pipeline-runner-metrics.json") -> Path:
    """Cria um projeto temporário. `payload=None` cria o projeto sem o arquivo."""
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    if payload is None:
        return directory
    metrics_dir = directory.joinpath(*relative)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    target = metrics_dir / file_name
    content = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2)
    target.write_text(content, encoding="utf-8")
    return target


@pytest.fixture
def projects_root(tmp_path: Path) -> Path:
    root = tmp_path / "projects"
    root.mkdir()
    return root


@pytest.fixture
def app_config_factory(tmp_path: Path, projects_root: Path):
    """Gera um config/app.yaml temporário apontando para o root temporário."""
    def _make(**overrides) -> Path:
        projects: dict = {
            "root_directory": str(projects_root),
            "discovery_mode": "immediate_subdirectories",
            "project_name_source": "directory_name",
            "ignored_directories": [".git", ".github", ".idea", ".vscode",
                                    ".venv", "venv", "__pycache__", "node_modules"],
            "metrics": {
                "relative_directory": "outputs\\pipeline_runner",
                "file_name": "pipeline-runner-metrics.json",
                "file_format": "json",
                "encoding": "utf-8",
            },
            "refresh": {"strategy": "request", "interval_seconds": 30},
            "removed_project_behavior": "remove_from_dashboard",
            "missing_metrics_file_behavior": "show_as_unavailable",
            "invalid_metrics_file_behavior": "show_error_and_continue",
            "sort": {"field": "directory_name", "order": "asc"},
            "read": {"stability_retries": 3, "retry_delay_seconds": 0.0},
            "cache": {"enabled": True, "max_entries": 64},
        }
        projects.update(overrides)
        path = tmp_path / "app.yaml"
        path.write_text(yaml.safe_dump({"projects": projects,
                                        "logging": {"level": "CRITICAL"}}),
                        encoding="utf-8")
        return path
    return _make


@pytest.fixture
def metrics_config() -> dict:
    from mfd.config import load_metrics_config
    return load_metrics_config(REAL_METRICS_CONFIG)


@pytest.fixture
def build_service(app_config_factory, metrics_config):
    """Fábrica de DashboardService já apontado ao root temporário."""
    from mfd.config import load_app_config
    from mfd.service import DashboardService

    def _make(env=None, **config_overrides):
        config = load_app_config(app_config_factory(**config_overrides), env=env or {})
        return DashboardService(config, metrics_config)
    return _make
