# -*- coding: utf-8 -*-
"""Camada web (§11.1).

As rotas não acessam o sistema de arquivos: toda leitura passa pelo
DashboardService. As respostas nunca expõem stack trace, caminho absoluto,
variável de ambiente ou mensagem crua do sistema operacional.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

from flask import Flask, jsonify, render_template, request

from ..config import AppConfig, load_app_config, load_metrics_config
from ..errors import ConfigurationError
from ..logging_setup import setup_logging
from ..models import Snapshot
from ..service import DashboardService, Filters

LOGGER = logging.getLogger("mfd.web")


def _snapshot_projects_payload(snapshot: Snapshot) -> dict[str, Any]:
    return {
        "status": "success",
        "generated_at": snapshot.generated_at_iso,
        "total_projects": len(snapshot.projects),
        "projects": [p.record.to_public_dict() for p in snapshot.projects],
    }


def _error_response(message: str, http_status: int = 500):
    """Resposta sanitizada — sem stack trace nem caminho interno."""
    return jsonify({"status": "error", "error": message}), http_status


def _thousands(value: float, decimals: int = 0) -> str:
    text = ("{:,.%df}" % decimals).format(value)
    return text.replace(",", " ").replace(".", ",").replace(" ", ".")


def format_metric_value(value: Any, metric: Any) -> str:
    """Formata um MetricValue para exibição, conforme `format` do metrics.yaml."""
    if value is None:
        return "—"
    kind = getattr(metric, "format", "text")
    if kind == "integer" and isinstance(value, (int, float)):
        return _thousands(float(value))
    if kind == "decimal" and isinstance(value, (int, float)):
        return _thousands(float(value), 3)
    if kind == "percentage" and isinstance(value, (int, float)):
        return _thousands(float(value), 1) + "%"
    if kind == "currency" and isinstance(value, (int, float)):
        return "US$ " + _thousands(float(value), 2)
    if kind == "duration" and isinstance(value, (int, float)):
        seconds = int(round(float(value)))
        return "%02d:%02d:%02d" % (seconds // 3600, seconds % 3600 // 60, seconds % 60)
    if kind == "breakdown" and isinstance(value, dict):
        return " · ".join("%s: %s" % (k, v) for k, v in value.items())
    return str(value)


def create_app(config: AppConfig | None = None,
               metrics_config: Mapping[str, Any] | None = None,
               service: DashboardService | None = None) -> Flask:
    """Fábrica da aplicação. Aceita injeção para os testes."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    startup_error: str | None = None
    if service is None:
        try:
            config = config or load_app_config()
            metrics_config = metrics_config or load_metrics_config()
            logger = setup_logging(config.logging_level, config.logging_format)
            service = DashboardService(config, dict(metrics_config), logger)
        except ConfigurationError as exc:
            startup_error = str(exc)
            LOGGER.error("falha de configuração: %s", exc)

    app.config["MFD_SERVICE"] = service
    app.config["MFD_STARTUP_ERROR"] = startup_error
    app.jinja_env.filters["metric_format"] = format_metric_value

    @app.after_request
    def _no_store(response):
        """O painel acompanha execuções em andamento: nada pode vir de cache.

        Sem isto o navegador serve uma casca antiga e o status congela na tela
        mesmo com o servidor devolvendo o valor novo.
        """
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    def _refresh() -> tuple[Snapshot | None, str | None]:
        if service is None:
            return None, startup_error or "aplicação não configurada"
        snapshot = service.refresh()
        return snapshot, snapshot.config_error

    # ── UI ─────────────────────────────────────────────────────────────
    @app.get("/")
    def dashboard():
        """Control Tower. O HTML é uma casca; os dados vêm de /api/dashboard-data."""
        return render_template(
            "control_tower.html",
            root_source=(service.config.projects_root_source if service else "não configurado"),
        )

    @app.get("/detalhe")
    def detail():
        """Visão tabular por projeto, útil para diagnóstico da descoberta."""
        snapshot, error = _refresh()
        return render_template(
            "dashboard.html",
            snapshot=snapshot,
            error=error,
            metrics_relative=(service.config.metrics_file.relative_display if service else ""),
            root_source=(service.config.projects_root_source if service else ""),
            refresh_strategy=(service.config.refresh_strategy if service else ""),
        )

    @app.get("/api/dashboard-data")
    def api_dashboard_data():
        """Runs do escopo + métricas do metrics.yaml recalculadas sobre ele.

        Fonte única: os KPIs e os gráficos saem do mesmo recorte, portanto
        nunca discordam entre si.
        """
        if service is None:
            return _error_response(startup_error or "aplicação não configurada", 503)
        view, error = service.view(Filters.from_mapping(request.args))
        if error:
            return _error_response(error, 503)

        runs = []
        for result in view.projects:
            if not (result.record.is_usable and result.payload):
                continue
            run = dict(result.payload)
            run["project_id"] = result.record.project_id
            run.setdefault("project_name", result.record.project_name)
            runs.append(run)

        # execution_status é o atributo de acompanhamento: enquanto houver
        # "running", o cliente repolla na cadência de refresh.interval_seconds
        in_progress = sorted(r["project_id"] for r in runs
                             if str(r.get("execution_status")) == "running")

        return jsonify({
            "status": "success",
            "generated_at": view.generated_at_iso,
            "refresh_interval_seconds": service.config.refresh_interval_seconds,
            "in_progress": in_progress,
            "statuses": {r["project_id"]: r.get("execution_status") for r in runs},
            "filters": view.filters.to_dict(),
            "facets": view.facets,
            "total_projects": view.total_projects,
            "runs": runs,
            "portfolio_metrics": [m.to_dict() for m in view.portfolio_metrics],
            "projects": [p.to_dict() for p in view.projects],
            "unavailable": [p.record.to_public_dict() for p in view.projects
                            if not p.record.is_usable],
            "duplicates": view.duplicates,
            "warnings": view.warnings,
            "settings": service.settings,
        })

    # ── APIs ───────────────────────────────────────────────────────────
    @app.get("/api/projects")
    def api_projects():
        snapshot, error = _refresh()
        if error:
            return _error_response(error, 503)
        return jsonify(_snapshot_projects_payload(snapshot))

    @app.get("/api/metrics")
    def api_metrics():
        snapshot, error = _refresh()
        if error:
            return _error_response(error, 503)

        payload = snapshot.to_dict()
        wanted = request.args.get("project")
        if wanted:
            selected = [p for p in payload["projects"] if p["project_id"] == wanted]
            if not selected:
                return _error_response("projeto não encontrado", 404)
            payload["projects"] = selected
        scope = (request.args.get("scope") or "").lower()
        if scope == "portfolio":
            payload["projects"] = []
        elif scope == "project":
            payload["portfolio_metrics"] = []

        payload["available_metrics"] = sorted({
            m["id"] for p in payload["projects"] for m in p["metrics"] if m["available"]
        } | {m["id"] for m in payload["portfolio_metrics"] if m["available"]})
        payload["unavailable_metrics"] = sorted({
            m["id"] for p in payload["projects"] for m in p["metrics"] if not m["available"]
        } | {m["id"] for m in payload["portfolio_metrics"] if not m["available"]})
        return jsonify(payload)

    @app.route("/api/refresh", methods=["POST", "GET"])
    def api_refresh():
        # POST é a forma preferida (§11.1). GET permanece por compatibilidade
        # com navegador e healthcheck; a operação é somente leitura, portanto
        # não modifica nenhum arquivo de origem.
        snapshot, error = _refresh()
        if error:
            return _error_response(error, 503)
        return jsonify({
            "status": "success",
            "method": request.method,
            "generated_at": snapshot.generated_at_iso,
            "total_projects": len(snapshot.projects),
            "projects_with_metrics": sum(1 for p in snapshot.projects if p.record.is_usable),
            "added_projects": snapshot.added_projects,
            "removed_projects": snapshot.removed_projects,
            "warnings": snapshot.warnings,
        })

    @app.get("/api/health")
    def api_health():
        if service is None:
            return _error_response(startup_error or "aplicação não configurada", 503)
        return jsonify({"status": "success", "version": _version()})

    @app.errorhandler(404)
    def not_found(_exc):
        return _error_response("recurso não encontrado", 404)

    @app.errorhandler(Exception)
    def unhandled(exc):                              # pragma: no cover - rede de segurança
        LOGGER.exception("erro não tratado: %s", exc)
        return _error_response("erro interno ao processar a requisição", 500)

    return app


def _version() -> str:
    from .. import __version__
    return __version__
