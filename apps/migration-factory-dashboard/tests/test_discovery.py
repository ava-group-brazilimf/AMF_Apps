# -*- coding: utf-8 -*-
"""Descoberta dinâmica — cenários 1, 2, 4, 5, 6, 10, 11, 19, 20, 21, 22, 23, 24 da §15.1."""
from __future__ import annotations

import os
import stat
import sys

import pytest

from conftest import sample_payload, write_project
from mfd.config import ENV_PROJECTS_ROOT, load_app_config
from mfd.discovery import ProjectDiscoveryService
from mfd.errors import ConfigurationError, DiscoveryError
from mfd.models import ProjectStatus


def _service(app_config_factory, env=None, **overrides):
    return ProjectDiscoveryService(load_app_config(app_config_factory(**overrides), env=env or {}))


# 1 — raiz com um projeto válido
def test_discovers_single_valid_project(projects_root, app_config_factory):
    write_project(projects_root, "alpha", sample_payload("alpha"))
    result = _service(app_config_factory).discover()
    assert [p.project_id for p in result.projects] == ["alpha"]
    assert result.projects[0].metrics_file_exists is True
    assert result.projects[0].metrics_last_modified is not None


# 2 — raiz com múltiplos projetos válidos, em ordem alfabética (§7.14)
def test_discovers_multiple_projects_sorted(projects_root, app_config_factory):
    for name in ("charlie", "alpha", "bravo"):
        write_project(projects_root, name, sample_payload(name))
    result = _service(app_config_factory).discover()
    assert [p.project_id for p in result.projects] == ["alpha", "bravo", "charlie"]


def test_sort_order_is_configurable(projects_root, app_config_factory):
    for name in ("alpha", "bravo"):
        write_project(projects_root, name, sample_payload(name))
    result = _service(app_config_factory, sort={"field": "directory_name", "order": "desc"}).discover()
    assert [p.project_id for p in result.projects] == ["bravo", "alpha"]


# 4 — projeto sem a pasta outputs
def test_project_without_outputs_directory(projects_root, app_config_factory):
    write_project(projects_root, "alpha", None)
    result = _service(app_config_factory).discover()
    record = result.projects[0]
    assert record.status == ProjectStatus.METRICS_UNAVAILABLE
    assert record.metrics_file_exists is False


# 5 — projeto sem a pasta pipeline_runner
def test_project_without_pipeline_runner_directory(projects_root, app_config_factory):
    (projects_root / "alpha" / "outputs").mkdir(parents=True)
    result = _service(app_config_factory).discover()
    assert result.projects[0].status == ProjectStatus.METRICS_UNAVAILABLE


# 6 — projeto sem o arquivo de métricas, mas ainda registrado (§7.7)
def test_project_without_metrics_file_is_still_registered(projects_root, app_config_factory):
    (projects_root / "alpha" / "outputs" / "pipeline_runner").mkdir(parents=True)
    result = _service(app_config_factory).discover()
    assert len(result.projects) == 1
    assert result.projects[0].status == ProjectStatus.METRICS_UNAVAILABLE


# 10 — inclusão de novo projeto após a primeira leitura
def test_new_project_is_detected_on_next_discovery(projects_root, app_config_factory):
    write_project(projects_root, "alpha", sample_payload("alpha"))
    service = _service(app_config_factory)
    assert [p.project_id for p in service.discover().projects] == ["alpha"]

    write_project(projects_root, "bravo", sample_payload("bravo"))
    second = service.discover()
    assert [p.project_id for p in second.projects] == ["alpha", "bravo"]
    assert second.added == ["bravo"]
    assert second.removed == []


# 11 — remoção de um projeto após a primeira leitura
def test_removed_project_disappears(projects_root, app_config_factory):
    import shutil
    write_project(projects_root, "alpha", sample_payload("alpha"))
    write_project(projects_root, "bravo", sample_payload("bravo"))
    service = _service(app_config_factory)
    service.discover()

    shutil.rmtree(projects_root / "bravo")
    result = service.discover()
    assert [p.project_id for p in result.projects] == ["alpha"]
    assert result.removed == ["bravo"]


# 19 — diretório definido por variável de ambiente (precedência sobre o YAML)
def test_environment_variable_overrides_yaml(tmp_path, projects_root, app_config_factory):
    other_root = tmp_path / "outra-raiz"
    other_root.mkdir()
    write_project(other_root, "from-env", sample_payload("from-env"))
    write_project(projects_root, "from-yaml", sample_payload("from-yaml"))

    config = load_app_config(app_config_factory(), env={ENV_PROJECTS_ROOT: str(other_root)})
    assert config.projects_root == other_root
    assert config.projects_root_source.startswith("environment:")
    assert [p.project_id for p in ProjectDiscoveryService(config).discover().projects] == ["from-env"]


def test_empty_environment_variable_falls_back_to_yaml(projects_root, app_config_factory):
    write_project(projects_root, "from-yaml", sample_payload())
    config = load_app_config(app_config_factory(), env={ENV_PROJECTS_ROOT: "   "})
    assert config.projects_root == projects_root
    assert config.projects_root_source.startswith("app.yaml")


# 20 — diretório raiz inexistente: falha controlada, não exceção crua
def test_missing_root_directory_raises_configuration_error(tmp_path, app_config_factory):
    path = app_config_factory(root_directory=str(tmp_path / "nao-existe"))
    with pytest.raises(ConfigurationError) as exc:
        load_app_config(path, env={})
    assert "não existe" in str(exc.value)


def test_missing_root_directory_at_discovery_time(projects_root, app_config_factory):
    import shutil
    service = _service(app_config_factory)
    shutil.rmtree(projects_root)
    with pytest.raises(DiscoveryError):
        service.discover()


def test_no_root_configured_raises_configuration_error(tmp_path, app_config_factory):
    path = app_config_factory(root_directory="")
    with pytest.raises(ConfigurationError):
        load_app_config(path, env={})


# 21 — diretório raiz sem permissão de leitura
@pytest.mark.skipif(sys.platform == "win32",
                    reason="chmod não remove leitura de diretório no Windows")
def test_root_without_read_permission(projects_root, app_config_factory):
    config = load_app_config(app_config_factory(), env={})
    os.chmod(projects_root, stat.S_IWUSR | stat.S_IXUSR)
    try:
        with pytest.raises(DiscoveryError):
            ProjectDiscoveryService(config).discover()
    finally:
        os.chmod(projects_root, stat.S_IRWXU)


# 22 — pastas técnicas ignoradas
def test_technical_directories_are_ignored(projects_root, app_config_factory):
    for ignored in (".git", ".venv", "__pycache__", "node_modules", ".vscode"):
        write_project(projects_root, ignored, sample_payload(ignored))
    write_project(projects_root, "alpha", sample_payload("alpha"))
    result = _service(app_config_factory).discover()
    assert [p.project_id for p in result.projects] == ["alpha"]


def test_loose_files_are_not_projects(projects_root, app_config_factory):
    write_project(projects_root, "alpha", sample_payload("alpha"))
    (projects_root / "relatorio.html").write_text("<html></html>", encoding="utf-8")
    (projects_root / "pacote.zip").write_bytes(b"PK\x03\x04")
    result = _service(app_config_factory).discover()
    assert [p.project_id for p in result.projects] == ["alpha"]


# 23 — nome de projeto com espaços
def test_project_name_with_spaces(projects_root, app_config_factory):
    write_project(projects_root, "projeto com espaços", sample_payload("projeto com espaços"))
    result = _service(app_config_factory).discover()
    assert result.projects[0].project_id == "projeto com espaços"
    assert result.projects[0].metrics_file_exists is True


# 24 — nome de projeto longo
# O comprimento é limitado pelo MAX_PATH do Windows: o caminho completo já
# inclui `outputs/pipeline_runner/pipeline-runner-metrics.json` (52 chars).
# Ver README, seção "Limites conhecidos".
def test_very_long_project_name(projects_root, app_config_factory):
    name = "projeto-" + "x" * 48
    write_project(projects_root, name, sample_payload(name))
    result = _service(app_config_factory).discover()
    assert result.projects[0].project_id == name
    assert len(name) > 50
    assert result.projects[0].metrics_file_exists is True


def test_relative_metrics_path_is_configurable(projects_root, app_config_factory):
    write_project(projects_root, "alpha", sample_payload("alpha"),
                  relative=("saida", "runner"), file_name="metricas.json")
    result = _service(app_config_factory,
                      metrics={"relative_directory": "saida/runner",
                               "file_name": "metricas.json",
                               "file_format": "json", "encoding": "utf-8"}).discover()
    assert result.projects[0].metrics_file_exists is True
