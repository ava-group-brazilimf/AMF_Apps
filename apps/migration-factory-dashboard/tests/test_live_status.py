# -*- coding: utf-8 -*-
"""Acompanhamento em tempo real por `execution_status`.

O painel usa esse atributo como sinal de acompanhamento: enquanto houver
`running`, o cliente repolla; ao clicar em Atualizar, a mudança aparece.
"""
from __future__ import annotations

import json

import pytest

from conftest import sample_payload, write_project


@pytest.fixture
def live_client(projects_root, build_service):
    from mfd.web import create_app
    app = create_app(service=build_service())
    app.config.update(TESTING=True)
    return app.test_client()


def _board(client, **params):
    query = "&".join("%s=%s" % (k, v) for k, v in params.items())
    return client.get("/api/dashboard-data" + ("?" + query if query else "")).get_json()


def test_running_execution_is_reported_as_in_progress(projects_root, live_client):
    write_project(projects_root, "em-curso",
                  sample_payload("em-curso", execution_status="running"))
    write_project(projects_root, "pronto",
                  sample_payload("pronto", execution_status="completed"))

    body = _board(live_client)
    assert body["in_progress"] == ["em-curso"]
    assert body["statuses"] == {"em-curso": "running", "pronto": "completed"}
    assert body["refresh_interval_seconds"] == 30

    metrics = {m["id"]: m["value"] for m in body["portfolio_metrics"]}
    assert metrics["executions_in_progress"] == 1
    assert metrics["successful_executions"] == 1


def test_running_is_not_counted_as_failure(projects_root, live_client):
    """Uma execução em andamento não é falha — era o defeito do painel."""
    write_project(projects_root, "em-curso",
                  sample_payload("em-curso", execution_status="running"))
    metrics = {m["id"]: m["value"] for m in _board(live_client)["portfolio_metrics"]}
    assert metrics["failed_executions"] == 0
    assert metrics["executions_in_progress"] == 1


def test_status_change_is_visible_on_next_refresh(projects_root, live_client):
    """Grava running, relê, troca para completed e relê: o valor acompanha."""
    target = write_project(projects_root, "em-curso",
                           sample_payload("em-curso", execution_status="running"))

    first = _board(live_client)
    assert first["statuses"]["em-curso"] == "running"
    assert first["in_progress"] == ["em-curso"]

    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["execution_status"] = "completed_with_warnings"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    second = _board(live_client)
    assert second["statuses"]["em-curso"] == "completed_with_warnings"
    assert second["in_progress"] == []
    metrics = {m["id"]: m["value"] for m in second["portfolio_metrics"]}
    assert metrics["executions_in_progress"] == 0
    assert metrics["executions_with_warnings"] == 1


def test_tokens_follow_a_running_execution(projects_root, live_client):
    """Enquanto roda, os números crescem a cada leitura."""
    target = write_project(projects_root, "em-curso",
                           sample_payload("em-curso", execution_status="running"))
    first = _board(live_client)
    assert first["runs"][0]["token_metrics"]["total_tokens"] == 300

    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["token_metrics"] = {"total_tokens": 900, "token_in": 600, "token_out": 300}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    second = _board(live_client)
    assert second["runs"][0]["token_metrics"]["total_tokens"] == 900
    metrics = {m["id"]: m["value"] for m in second["portfolio_metrics"]}
    assert metrics["portfolio_total_tokens"] == 900


def test_filters_do_not_hide_the_live_signal(projects_root, live_client):
    write_project(projects_root, "em-curso",
                  sample_payload("em-curso", execution_status="running"))
    write_project(projects_root, "pronto",
                  sample_payload("pronto", execution_status="completed"))

    only_running = _board(live_client, status="running")
    assert [r["project_id"] for r in only_running["runs"]] == ["em-curso"]
    assert only_running["in_progress"] == ["em-curso"]

    only_done = _board(live_client, status="completed")
    assert only_done["in_progress"] == []


def test_new_running_project_appears_without_restart(projects_root, live_client):
    write_project(projects_root, "pronto",
                  sample_payload("pronto", execution_status="completed"))
    assert _board(live_client)["in_progress"] == []

    write_project(projects_root, "recem-iniciado",
                  sample_payload("recem-iniciado", execution_status="running"))
    body = _board(live_client)
    assert body["in_progress"] == ["recem-iniciado"]
    assert len(body["runs"]) == 2


def test_client_receives_polling_cadence_from_config(projects_root, build_service):
    """A cadência do repolling vem de refresh.interval_seconds no app.yaml."""
    from mfd.web import create_app
    write_project(projects_root, "em-curso",
                  sample_payload("em-curso", execution_status="running"))
    service = build_service(refresh={"strategy": "request", "interval_seconds": 7})
    app = create_app(service=service)
    app.config.update(TESTING=True)
    body = app.test_client().get("/api/dashboard-data").get_json()
    assert body["refresh_interval_seconds"] == 7


def test_responses_are_never_cached(projects_root, live_client):
    """Sem no-store o navegador serve a casca antiga e o status congela."""
    write_project(projects_root, "em-curso",
                  sample_payload("em-curso", execution_status="running"))
    for route in ("/", "/api/dashboard-data", "/api/metrics", "/api/projects"):
        headers = live_client.get(route).headers
        assert "no-store" in headers.get("Cache-Control", "")
        assert headers.get("Pragma") == "no-cache"


def test_running_label_is_not_interrupted():
    """`running` e `interrupted` são estados distintos em cada idioma.

    O rótulo sai do dicionário de i18n, portanto o que se verifica é a
    tradução de cada chave — nunca a de `running` valendo "interrompida".
    """
    from pathlib import Path
    template = (Path(__file__).resolve().parents[1]
                / "src" / "mfd" / "web" / "templates" / "control_tower.html")
    text = template.read_text(encoding="utf-8")
    assert 'running:{key:"run.running"' in text
    assert 'interrupted:{key:"run.interrupted"' in text
    for pair in ('"run.running":"Running"', '"run.interrupted":"Interrupted"',
                 '"run.running":"Em execução"', '"run.interrupted":"Interrompida"'):
        assert pair in text, pair
