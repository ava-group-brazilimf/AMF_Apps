# -*- coding: utf-8 -*-
"""Leitura, validação e cálculo — cenários 3, 7, 8, 9, 12, 14, 15, 16, 17, 18 da §15.1."""
from __future__ import annotations

import json

from conftest import sample_payload, write_project
from mfd.config import load_app_config
from mfd.metrics import MetricsEngine, json_path
from mfd.models import ProjectStatus
from mfd.reader import MetricsFileReader


def _read(projects_root, app_config_factory, name):
    from mfd.discovery import ProjectDiscoveryService
    config = load_app_config(app_config_factory(), env={})
    record = next(p for p in ProjectDiscoveryService(config).discover().projects
                  if p.project_id == name)
    return MetricsFileReader(config).read(record), record


# 3 — arquivo válido
def test_reads_valid_metrics_file(projects_root, app_config_factory):
    write_project(projects_root, "alpha", sample_payload("alpha"))
    result, _ = _read(projects_root, app_config_factory, "alpha")
    assert result.status == ProjectStatus.AVAILABLE
    assert result.payload["project_name"] == "alpha"
    assert result.errors == []


# 7 — arquivo vazio
def test_empty_file(projects_root, app_config_factory):
    write_project(projects_root, "alpha", "")
    result, _ = _read(projects_root, app_config_factory, "alpha")
    assert result.status == ProjectStatus.EMPTY_FILE
    assert result.payload is None


def test_whitespace_only_file(projects_root, app_config_factory):
    write_project(projects_root, "alpha", "   \n\t ")
    result, _ = _read(projects_root, app_config_factory, "alpha")
    assert result.status == ProjectStatus.EMPTY_FILE


# 8 — JSON inválido
def test_invalid_json(projects_root, app_config_factory):
    write_project(projects_root, "alpha", '{"execution_id": "x",,}')
    result, _ = _read(projects_root, app_config_factory, "alpha")
    assert result.status == ProjectStatus.INVALID_JSON
    assert "JSON inválido" in result.errors[0]


def test_root_element_must_be_object(projects_root, app_config_factory):
    write_project(projects_root, "alpha", "[1, 2, 3]")
    result, _ = _read(projects_root, app_config_factory, "alpha")
    assert result.status == ProjectStatus.INCOMPATIBLE_SCHEMA


def test_missing_required_fields_is_incompatible(projects_root, app_config_factory):
    write_project(projects_root, "alpha", {"foo": "bar"})
    result, _ = _read(projects_root, app_config_factory, "alpha")
    assert result.status == ProjectStatus.INCOMPATIBLE_SCHEMA


# 9 — dois projetos com versões diferentes do esquema
def test_schema_variation_is_tolerated(projects_root, app_config_factory, metrics_config):
    write_project(projects_root, "novo", sample_payload("novo"))
    antigo = sample_payload("antigo")
    del antigo["phase_metrics"]              # versão antiga não tinha fases
    antigo["execution_mode"] = "manual"      # valor real observado no acervo
    write_project(projects_root, "antigo", antigo)

    novo_result, _ = _read(projects_root, app_config_factory, "novo")
    antigo_result, _ = _read(projects_root, app_config_factory, "antigo")

    assert novo_result.status == ProjectStatus.AVAILABLE
    assert antigo_result.status == ProjectStatus.PARTIALLY_AVAILABLE
    assert any("phase_metrics" in e for e in antigo_result.errors)

    engine = MetricsEngine(metrics_config)
    metrics = {m.id: m for m in engine.compute_project(antigo_result.payload)}
    assert metrics["project_total_tokens"].available is True
    assert metrics["project_phase_count"].available is False


def test_unknown_phase_status_is_reported_not_fatal(projects_root, app_config_factory):
    payload = sample_payload("alpha")
    payload["phase_metrics"][0]["status"] = "algo_novo"
    write_project(projects_root, "alpha", payload)
    result, _ = _read(projects_root, app_config_factory, "alpha")
    assert result.status == ProjectStatus.AVAILABLE       # não derruba
    assert any("não reconhecido" in e for e in result.errors)


# 12 / 17 — arquivo alterado invalida o cache
def test_cache_is_invalidated_when_file_changes(projects_root, app_config_factory):
    from mfd.discovery import ProjectDiscoveryService
    write_project(projects_root, "alpha", sample_payload("alpha"))
    config = load_app_config(app_config_factory(), env={})
    reader = MetricsFileReader(config)
    discovery = ProjectDiscoveryService(config)

    record = discovery.discover().projects[0]
    first = reader.read(record)
    assert first.payload["token_metrics"]["total_tokens"] == 300
    assert first.from_cache is False

    again = reader.read(discovery.discover().projects[0])
    assert again.from_cache is True                        # nada mudou

    updated = sample_payload("alpha")
    updated["token_metrics"] = {"total_tokens": 999, "token_in": 600, "token_out": 399}
    write_project(projects_root, "alpha", updated)

    third = reader.read(discovery.discover().projects[0])
    assert third.payload["token_metrics"]["total_tokens"] == 999
    assert third.from_cache is False


def test_clear_cache(projects_root, app_config_factory):
    from mfd.discovery import ProjectDiscoveryService
    write_project(projects_root, "alpha", sample_payload("alpha"))
    config = load_app_config(app_config_factory(), env={})
    reader = MetricsFileReader(config)
    record = ProjectDiscoveryService(config).discover().projects[0]
    reader.read(record)
    assert reader.cache_size == 1
    reader.clear_cache()
    assert reader.cache_size == 0


def test_cache_can_be_disabled(projects_root, app_config_factory):
    from mfd.discovery import ProjectDiscoveryService
    write_project(projects_root, "alpha", sample_payload("alpha"))
    config = load_app_config(app_config_factory(cache={"enabled": False}), env={})
    reader = MetricsFileReader(config)
    record = ProjectDiscoveryService(config).discover().projects[0]
    reader.read(record)
    assert reader.read(record).from_cache is False


# 18 — arquivo alterado durante a leitura
def test_file_changing_during_read_is_retried_then_reported(projects_root, app_config_factory,
                                                            monkeypatch):
    from mfd.discovery import ProjectDiscoveryService
    write_project(projects_root, "alpha", sample_payload("alpha"))
    config = load_app_config(app_config_factory(), env={})
    reader = MetricsFileReader(config)
    record = ProjectDiscoveryService(config).discover().projects[0]

    from pathlib import Path as _Path
    real_stat = _Path.stat
    calls = {"n": 0}

    class _FakeStat:
        def __init__(self, base, mtime_ns):
            self.st_size = base.st_size
            self.st_mtime = base.st_mtime
            self.st_mtime_ns = mtime_ns

    def unstable_stat(self, *args, **kwargs):
        base = real_stat(self, *args, **kwargs)
        if self == record.metrics_file:
            calls["n"] += 1
            return _FakeStat(base, base.st_mtime_ns + calls["n"])   # muda a cada chamada
        return base

    monkeypatch.setattr(_Path, "stat", unstable_stat)
    result = reader.read(record)
    assert result.status == ProjectStatus.READ_ERROR
    assert "temporariamente indisponível" in result.errors[0]
    assert calls["n"] >= config.read.stability_retries * 2


# 15 — cálculo de métricas por projeto
def test_project_metrics_are_computed(metrics_config):
    engine = MetricsEngine(metrics_config)
    metrics = {m.id: m for m in engine.compute_project(sample_payload("alpha"))}

    assert str(metrics["project_execution_id"].value).startswith("runner19-")
    assert metrics["project_pipeline_duration"].value == 20815.0
    assert metrics["project_effective_phase_time"].value == 672.0        # 168 + 504 + 0
    assert metrics["project_total_tokens"].value == 300
    assert metrics["project_phase_count"].value == 3
    assert metrics["project_executed_phase_count"].value == 2
    assert metrics["project_degraded_phase_count"].value == 1
    assert metrics["project_health_score"].value == 66.7                 # 2/3
    assert metrics["project_token_efficiency"].value == 0.5              # 100/200
    assert metrics["project_longest_phase"].value == "F1"
    assert metrics["project_shortest_measured_phase"].value == "F0"      # ignora a de 0s
    assert metrics["project_estimated_cost"].value == round(200 * 3 / 1e6 + 100 * 15 / 1e6, 2)


def test_metrics_unavailable_when_payload_missing(metrics_config):
    engine = MetricsEngine(metrics_config)
    metrics = engine.compute_project(None)
    assert metrics and all(m.available is False for m in metrics)
    assert all(m.reason for m in metrics)


def test_division_by_zero_marks_metric_unavailable(metrics_config):
    payload = sample_payload("zerado")
    payload["token_metrics"] = {"total_tokens": 0, "token_in": 0, "token_out": 0}
    payload["phase_metrics"] = []
    metrics = {m.id: m for m in MetricsEngine(metrics_config).compute_project(payload)}
    assert metrics["project_token_efficiency"].available is False
    assert metrics["project_health_score"].available is False
    assert metrics["project_phase_count"].value == 0        # essa continua calculável


def test_json_path_helper():
    assert json_path({"a": {"b": 1}}, "a.b") == 1
    assert json_path({"a": {"b": 1}}, "a.c") is None
    assert json_path(None, "a") is None
    assert json_path({"a": 1}, "") is None
