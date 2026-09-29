# -*- coding: utf-8 -*-
"""Serviço, portfólio e APIs — cenários 13, 14, 16, 25 da §15.1 e §11.1."""
from __future__ import annotations

import shutil

import pytest

from conftest import sample_payload, write_project
from mfd.models import ProjectStatus


def _portfolio(snapshot):
    return {m.id: m for m in snapshot.portfolio_metrics}


# 16 — métricas de portfólio
def test_portfolio_metrics(projects_root, build_service):
    write_project(projects_root, "alpha", sample_payload("alpha"))
    beta = sample_payload("beta")
    beta["token_metrics"] = {"total_tokens": 700, "token_in": 400, "token_out": 300}
    beta["total_duration_seconds"] = 1000.0
    write_project(projects_root, "beta", beta)
    write_project(projects_root, "sem-metrica", None)

    snapshot = build_service().refresh()
    p = _portfolio(snapshot)

    assert p["total_discovered_projects"].value == 3
    assert p["projects_with_valid_metrics"].value == 2
    assert p["projects_without_metrics"].value == 1
    assert p["projects_with_errors"].value == 0
    assert p["portfolio_total_tokens"].value == 1000          # 300 + 700
    assert p["portfolio_total_duration"].value == 21815.0     # 20815 + 1000
    assert p["portfolio_average_duration"].value == 10907.5
    assert p["portfolio_min_duration"].value == 1000.0
    assert p["portfolio_max_duration"].value == 20815.0
    assert p["portfolio_token_efficiency"].value == round(400 / 600, 3)
    assert p["portfolio_coverage_percentage"].value == round(2 / 3 * 100, 1)
    assert p["portfolio_weighted_health"].value == 66.7       # ambos 2/3 de 3 fases
    assert p["portfolio_executions_by_status"].value == {"completed_with_warnings": 2}
    assert p["portfolio_latest_execution"].available is True


def test_portfolio_ignores_projects_without_metrics(projects_root, build_service):
    write_project(projects_root, "alpha", sample_payload("alpha"))
    write_project(projects_root, "vazio", None)
    p = _portfolio(build_service().refresh())
    assert p["portfolio_total_tokens"].value == 300           # só o alpha


# 13 — projeto removido não aparece nas métricas consolidadas
def test_removed_project_is_excluded_from_portfolio(projects_root, build_service):
    write_project(projects_root, "alpha", sample_payload("alpha"))
    write_project(projects_root, "beta", sample_payload("beta"))
    service = build_service()

    first = _portfolio(service.refresh())
    assert first["total_discovered_projects"].value == 2
    assert first["portfolio_total_tokens"].value == 600

    shutil.rmtree(projects_root / "beta")

    second = service.refresh()
    assert [p.record.project_id for p in second.projects] == ["alpha"]
    assert second.removed_projects == ["beta"]
    assert _portfolio(second)["portfolio_total_tokens"].value == 300


# 14 — um arquivo inválido não impede a leitura dos demais
def test_invalid_file_does_not_block_other_projects(projects_root, build_service):
    write_project(projects_root, "bom", sample_payload("bom"))
    write_project(projects_root, "quebrado", "{ nao e json")
    write_project(projects_root, "vazio", "")

    snapshot = build_service().refresh()
    by_id = {p.record.project_id: p for p in snapshot.projects}

    assert by_id["bom"].record.status == ProjectStatus.AVAILABLE
    assert by_id["bom"].metric("project_total_tokens").value == 300
    assert by_id["quebrado"].record.status == ProjectStatus.INVALID_JSON
    assert by_id["vazio"].record.status == ProjectStatus.EMPTY_FILE
    assert _portfolio(snapshot)["portfolio_total_tokens"].value == 300
    assert _portfolio(snapshot)["projects_with_errors"].value == 2


# 25 — dados de projetos diferentes não se misturam
def test_project_data_is_not_mixed(projects_root, build_service):
    alpha = sample_payload("alpha")
    alpha["token_metrics"] = {"total_tokens": 111, "token_in": 100, "token_out": 11}
    beta = sample_payload("beta")
    beta["token_metrics"] = {"total_tokens": 222, "token_in": 200, "token_out": 22}
    beta["phase_metrics"] = beta["phase_metrics"][:1]
    write_project(projects_root, "alpha", alpha)
    write_project(projects_root, "beta", beta)

    snapshot = build_service().refresh()
    by_id = {p.record.project_id: p for p in snapshot.projects}
    assert by_id["alpha"].metric("project_total_tokens").value == 111
    assert by_id["beta"].metric("project_total_tokens").value == 222
    assert by_id["alpha"].metric("project_phase_count").value == 3
    assert by_id["beta"].metric("project_phase_count").value == 1
    assert by_id["alpha"].metric("project_execution_id").value != \
        by_id["beta"].metric("project_execution_id").value
    assert by_id["alpha"].record.project_name == "alpha"
    assert by_id["beta"].record.project_name == "beta"


# 10 + 11 no nível de serviço: novo projeto entra, removido sai, sem reiniciar
def test_service_reflects_added_and_removed_projects(projects_root, build_service):
    write_project(projects_root, "alpha", sample_payload("alpha"))
    service = build_service()
    assert len(service.refresh().projects) == 1

    write_project(projects_root, "bravo", sample_payload("bravo"))
    second = service.refresh()
    assert second.added_projects == ["bravo"]
    assert len(second.projects) == 2

    shutil.rmtree(projects_root / "alpha")
    third = service.refresh()
    assert third.removed_projects == ["alpha"]
    assert [p.record.project_id for p in third.projects] == ["bravo"]


# ─────────────────────────────── APIs ───────────────────────────────
@pytest.fixture
def client(projects_root, build_service):
    from mfd.web import create_app
    write_project(projects_root, "alpha", sample_payload("alpha"))
    write_project(projects_root, "sem-metrica", None)
    app = create_app(service=build_service())
    app.config.update(TESTING=True)
    return app.test_client()


def test_api_projects(client):
    response = client.get("/api/projects")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["total_projects"] == 2
    ids = [p["project_id"] for p in body["projects"]]
    assert ids == ["alpha", "sem-metrica"]
    alpha = body["projects"][0]
    assert alpha["metrics_file_exists"] is True
    assert alpha["metrics_file_valid"] is True
    assert alpha["status"] == "available"
    assert alpha["metrics_last_modified"]


def test_api_projects_does_not_leak_absolute_paths(client, projects_root):
    body = client.get("/api/projects").get_json()
    serialized = str(body)
    assert str(projects_root) not in serialized
    assert "project_directory" not in serialized
    assert body["projects"][0]["metrics_file"] == \
        "alpha/outputs/pipeline_runner/pipeline-runner-metrics.json"


def test_api_metrics(client):
    body = client.get("/api/metrics").get_json()
    assert body["status"] == "success"
    assert body["generated_at"]
    assert body["portfolio_metrics"]
    assert len(body["projects"]) == 2
    assert "project_total_tokens" in body["available_metrics"]
    assert body["unavailable_metrics"]
    assert body["warnings"]

    alpha = next(p for p in body["projects"] if p["project_id"] == "alpha")
    tokens = next(m for m in alpha["metrics"] if m["id"] == "project_total_tokens")
    assert tokens["value"] == 300 and tokens["available"] is True


def test_api_metrics_filters(client):
    only = client.get("/api/metrics?project=alpha").get_json()
    assert [p["project_id"] for p in only["projects"]] == ["alpha"]

    assert client.get("/api/metrics?project=nao-existe").status_code == 404

    portfolio = client.get("/api/metrics?scope=portfolio").get_json()
    assert portfolio["projects"] == [] and portfolio["portfolio_metrics"]


def test_api_refresh_post_and_get(client):
    posted = client.post("/api/refresh")
    assert posted.status_code == 200
    body = posted.get_json()
    assert body["status"] == "success" and body["method"] == "POST"
    assert body["total_projects"] == 2
    assert body["projects_with_metrics"] == 1

    got = client.get("/api/refresh")
    assert got.status_code == 200 and got.get_json()["method"] == "GET"


def test_api_refresh_does_not_modify_source_files(client, projects_root):
    target = projects_root / "alpha" / "outputs" / "pipeline_runner" / "pipeline-runner-metrics.json"
    before = (target.read_bytes(), target.stat().st_mtime_ns)
    client.post("/api/refresh")
    client.get("/api/metrics")
    client.get("/")
    assert (target.read_bytes(), target.stat().st_mtime_ns) == before


def test_control_tower_shell_renders(client):
    """A rota / entrega a casca do Control Tower; os dados vêm por fetch."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Migration Factory Control Tower" in html
    assert "/api/dashboard-data" in html
    for page in ("Executive Overview", "Pipeline Performance", "Token Analytics",
                 "FinOps", "Quality & Operations", "Factory Operations", "Custo por Modelo"):
        assert page in html


def test_detail_view_renders(client):
    response = client.get("/detalhe")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "alpha" in html
    assert "sem-metrica" in html
    assert "metrics_unavailable" in html


def test_dashboard_html_does_not_leak_absolute_paths(client, projects_root):
    for route in ("/", "/detalhe"):
        html = client.get(route).get_data(as_text=True)
        assert str(projects_root) not in html
    detail = client.get("/detalhe").get_data(as_text=True)
    assert "alpha/outputs/pipeline_runner/pipeline-runner-metrics.json" in detail


def test_unknown_route_returns_sanitized_error(client):
    response = client.get("/nao-existe")
    assert response.status_code == 404
    assert response.get_json() == {"status": "error", "error": "recurso não encontrado"}


def test_api_reports_configuration_failure_without_leaking(projects_root, build_service, tmp_path):
    from mfd.web import create_app
    service = build_service()
    app = create_app(service=service)
    app.config.update(TESTING=True)
    client = app.test_client()
    shutil.rmtree(projects_root)

    response = client.get("/api/projects")
    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "error"
    assert "Traceback" not in body["error"]


def _control_tower_source() -> str:
    from pathlib import Path
    return (Path(__file__).resolve().parents[1] / "src" / "mfd" / "web"
            / "templates" / "control_tower.html").read_text(encoding="utf-8")


def test_i18n_dictionaries_cover_the_same_keys():
    """`en` e `pt` precisam declarar exatamente as mesmas chaves.

    Uma chave só em `en` faz o painel cair para o inglês no meio da tela em
    português; uma chave só em `pt` é tradução que nunca aparece.
    """
    import re
    source = _control_tower_source()
    start = source.index("const I18N = {")
    blocks = {}
    for lang in ("en", "pt"):
        head = source.index("\n%s:{" % lang, start)
        tail = source.index("\n}", head + 1)
        blocks[lang] = set(re.findall(r'"([^"]+)":', source[head:tail]))
    assert blocks["en"], "dicionário en vazio"
    assert blocks["en"] == blocks["pt"], (
        "divergência entre idiomas: só em en=%s | só em pt=%s"
        % (sorted(blocks["en"] - blocks["pt"]), sorted(blocks["pt"] - blocks["en"])))


def test_dashboard_defaults_to_english():
    """A casca sai do servidor em inglês e oferece a troca para português."""
    source = _control_tower_source()
    assert '<html lang="en">' in source
    assert 'let LANG = "en";' in source
    assert 'data-lang="pt"' in source and 'data-lang="en"' in source
