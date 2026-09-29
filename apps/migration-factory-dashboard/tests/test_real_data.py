# -*- coding: utf-8 -*-
"""Validação contra os dados REAIS, somente leitura (§16.1).

Estes testes não criam, alteram nem removem nada em `projects/`. Eles
verificam integridade (hash) antes e depois para provar que a aplicação
não tocou nos arquivos do pipeline.
"""
from __future__ import annotations

import hashlib

import pytest

from conftest import REAL_APP_CONFIG, REAL_METRICS_CONFIG, REAL_PROJECTS_ROOT
from mfd.config import load_app_config, load_metrics_config
from mfd.models import ProjectStatus
from mfd.service import DashboardService

pytestmark = pytest.mark.skipif(not REAL_PROJECTS_ROOT.is_dir(),
                                reason="diretório real de projetos indisponível")


@pytest.fixture(scope="module")
def real_snapshot():
    config = load_app_config(REAL_APP_CONFIG, env={})
    service = DashboardService(config, load_metrics_config(REAL_METRICS_CONFIG))
    return config, service, service.refresh()


def _digest(root):
    """Hash de todos os arquivos de métricas reais."""
    parts = []
    for path in sorted(root.glob("*/outputs/pipeline_runner/pipeline-runner-metrics.json")):
        parts.append(path.name.encode() + hashlib.sha256(path.read_bytes()).digest())
    return hashlib.sha256(b"".join(parts)).hexdigest()


# 1 — o diretório raiz existe e é o configurado
def test_real_root_is_configured_and_exists(real_snapshot):
    config, _, _ = real_snapshot
    assert config.projects_root == REAL_PROJECTS_ROOT
    assert config.projects_root.is_dir()


# 2 / 3 — nopcommerce-01 é descoberto dinamicamente, com o arquivo localizado
def test_nopcommerce_is_discovered_without_being_hardcoded(real_snapshot):
    _, _, snapshot = real_snapshot
    ids = [p.record.project_id for p in snapshot.projects]
    assert "nopcommerce-01" in ids, "esperado descobrir nopcommerce-01 em %s" % ids

    project = next(p for p in snapshot.projects if p.record.project_id == "nopcommerce-01")
    assert project.record.metrics_file_exists is True
    assert project.record.metrics_relative_path == \
        "nopcommerce-01/outputs/pipeline_runner/pipeline-runner-metrics.json"


def test_project_id_is_not_hardcoded_in_source():
    """Nenhum módulo pode citar um projeto específico (§19.1)."""
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "src"
    for module in src.rglob("*.py"):
        text = module.read_text(encoding="utf-8")
        assert "nopcommerce" not in text.lower(), "%s cita um projeto específico" % module.name
    for config in (REAL_APP_CONFIG, REAL_METRICS_CONFIG):
        assert "nopcommerce" not in config.read_text(encoding="utf-8").lower()


# 4 / 5 — o JSON foi interpretado e as métricas calculadas
def test_nopcommerce_metrics_are_computed(real_snapshot):
    _, _, snapshot = real_snapshot
    project = next(p for p in snapshot.projects if p.record.project_id == "nopcommerce-01")
    assert project.record.status in ProjectStatus.USABLE

    values = {m.id: m for m in project.metrics}
    assert values["project_execution_id"].value == "runner19-1787956593"
    assert values["project_execution_mode"].value == "manual"
    assert values["project_total_tokens"].value == 198257
    assert values["project_input_tokens"].value == 84234
    assert values["project_output_tokens"].value == 114023
    assert values["project_pipeline_duration"].value == 1444.04
    assert values["project_phase_count"].value == 1
    assert values["project_longest_phase"].value == "F6"
    # a única fase reprovou validação: nenhuma "executed", health 0%
    assert values["project_executed_phase_count"].value == 0
    assert values["project_degraded_phase_count"].value == 1
    assert values["project_health_score"].value == 0.0


# 6 — quais métricas ficaram indisponíveis
def test_unavailable_metrics_are_explained(real_snapshot):
    _, _, snapshot = real_snapshot
    for project in snapshot.projects:
        for metric in project.metrics:
            if not metric.available:
                assert metric.reason, "%s/%s sem justificativa" % (
                    project.record.project_id, metric.id)
                assert metric.value is None


def test_projects_without_metrics_file_are_listed_as_unavailable(real_snapshot):
    _, _, snapshot = real_snapshot
    missing = [p for p in snapshot.projects
               if p.record.status == ProjectStatus.METRICS_UNAVAILABLE]
    for project in missing:
        assert project.record.metrics_file_exists is False
        assert project.metrics and all(m.available is False for m in project.metrics)


# 7 / 8 / 9 — rota principal e APIs respondem com os dados reais
@pytest.fixture(scope="module")
def real_client(real_snapshot):
    from mfd.web import create_app
    _, service, _ = real_snapshot
    app = create_app(service=service)
    app.config.update(TESTING=True)
    return app.test_client()


def test_dashboard_route_renders_real_values(real_client):
    html = real_client.get("/detalhe").get_data(as_text=True)
    assert "nopcommerce-01" in html
    assert "198.257" in html          # tokens formatados em pt-BR
    assert str(REAL_PROJECTS_ROOT) not in html   # sem caminho absoluto no HTML
    shell = real_client.get("/").get_data(as_text=True)
    assert "Migration Factory Control Tower" in shell
    assert str(REAL_PROJECTS_ROOT) not in shell


def test_api_projects_returns_nopcommerce(real_client):
    body = real_client.get("/api/projects").get_json()
    assert body["status"] == "success"
    ids = [p["project_id"] for p in body["projects"]]
    assert "nopcommerce-01" in ids


def test_api_metrics_returns_computed_values(real_client):
    body = real_client.get("/api/metrics?project=nopcommerce-01").get_json()
    assert body["status"] == "success"
    project = body["projects"][0]
    tokens = next(m for m in project["metrics"] if m["id"] == "project_total_tokens")
    assert tokens["value"] == 198257
    assert "portfolio_total_tokens" in {m["id"] for m in body["portfolio_metrics"]}


def test_api_does_not_expose_real_absolute_paths(real_client):
    body = str(real_client.get("/api/metrics").get_json())
    assert str(REAL_PROJECTS_ROOT) not in body
    assert "C:\\\\Desenv" not in body


# 10 — nenhum arquivo de origem foi modificado
def test_source_files_are_untouched(real_snapshot, real_client):
    before = _digest(REAL_PROJECTS_ROOT)
    _, service, _ = real_snapshot
    service.refresh()
    real_client.get("/")
    real_client.get("/api/metrics")
    real_client.post("/api/refresh")
    assert _digest(REAL_PROJECTS_ROOT) == before


def test_portfolio_consolidates_only_current_projects(real_snapshot):
    _, _, snapshot = real_snapshot
    portfolio = {m.id: m for m in snapshot.portfolio_metrics}
    usable = [p for p in snapshot.projects if p.record.is_usable]
    assert portfolio["total_discovered_projects"].value == len(snapshot.projects)
    assert portfolio["projects_with_valid_metrics"].value == len(usable)
    expected = sum(p.metric("project_total_tokens").value for p in usable
                   if p.metric("project_total_tokens").available)
    assert portfolio["portfolio_total_tokens"].value == expected
