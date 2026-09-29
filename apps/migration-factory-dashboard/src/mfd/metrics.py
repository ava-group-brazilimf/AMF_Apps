# -*- coding: utf-8 -*-
"""Cálculo das métricas dirigido por metrics.yaml (§9).

Separado da leitura: o motor recebe payloads já interpretados e nunca toca o
sistema de arquivos. Nenhum cálculo conhece um projeto específico.

Cada `calculation.type` é um método registrado — não há `eval`, então uma
métrica mal configurada falha de forma controlada e vira "indisponível".
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Callable, Iterable, Mapping, Sequence

from .models import MetricValue, ProjectResult, ProjectStatus

LOGGER = logging.getLogger(__name__)

NOT_AVAILABLE = "not_available"


def json_path(payload: Mapping[str, Any] | None, path: str) -> Any:
    """Resolve 'token_metrics.token_in' em um dicionário aninhado."""
    if payload is None or not path:
        return None
    current: Any = payload
    for part in str(path).split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return None
    return current


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_number(value: Any) -> float | None:
    return float(value) if _is_number(value) else None


def _coerce(value: Any, fmt: Any) -> Any:
    """`format: integer` nunca deve sair como 6185288.0 na API."""
    if not _is_number(value):
        return value
    if fmt == "integer" and float(value).is_integer():
        return int(value)
    return value


def _round(value: float | None, precision: Any) -> float | None:
    if value is None:
        return None
    try:
        digits = int(precision)
    except (TypeError, ValueError):
        return value
    rounded = round(value, digits)
    return int(rounded) if digits <= 0 else rounded


class MetricsEngine:
    """Aplica as definições de metrics.yaml a um payload ou a um portfólio."""

    def __init__(self, metrics_config: Mapping[str, Any],
                 logger: logging.Logger | None = None) -> None:
        self._settings: Mapping[str, Any] = metrics_config.get("settings") or {}
        definitions = [d for d in (metrics_config.get("metrics") or []) if d.get("enabled", True)]
        self._project_defs = sorted([d for d in definitions if d.get("scope") == "project"],
                                    key=lambda d: d.get("order", 0))
        self._portfolio_defs = sorted([d for d in definitions if d.get("scope") == "portfolio"],
                                      key=lambda d: d.get("order", 0))
        self._log = logger or LOGGER

        self._project_ops: dict[str, Callable] = {
            "field": self._op_field,
            "duration": self._op_duration,
            "count_items": self._op_count_items,
            "count_items_where": self._op_count_items_where,
            "sum_items": self._op_sum_items,
            "ratio": self._op_ratio,
            "percentage": self._op_percentage,
            "max_item_by": self._op_max_item_by,
            "min_item_by": self._op_min_item_by,
            "token_cost": self._op_token_cost,
        }
        self._portfolio_ops: dict[str, Callable] = {
            "count_projects": self._agg_count_projects,
            "count_by_status": self._agg_count_by_status,
            "sum_metric": self._agg_sum,
            "average_metric": self._agg_average,
            "minimum_metric": self._agg_minimum,
            "maximum_metric": self._agg_maximum,
            "ratio_metrics": self._agg_ratio,
            "percentage_metrics": self._agg_percentage,
            "weighted_average_metric": self._agg_weighted_average,
            "count_by_project_field": self._agg_count_by_project_field,
            "count_metric_value": self._agg_count_metric_value,
            "latest_value": self._agg_latest_value,
        }

    # ── identificação ───────────────────────────────────────────────────
    @property
    def settings(self) -> Mapping[str, Any]:
        return self._settings

    @property
    def project_metric_ids(self) -> list[str]:
        return [d["id"] for d in self._project_defs]

    @property
    def portfolio_metric_ids(self) -> list[str]:
        return [d["id"] for d in self._portfolio_defs]

    # ── escopo: projeto ────────────────────────────────────────────────
    def compute_project(self, payload: Mapping[str, Any] | None) -> list[MetricValue]:
        computed: dict[str, MetricValue] = {}
        results: list[MetricValue] = []
        for definition in self._project_defs:
            metric = self._build(definition, "project")
            if payload is None:
                self._mark_unavailable(metric, definition, "arquivo de métricas indisponível")
            else:
                self._evaluate_project(metric, definition, payload, computed)
            computed[metric.id] = metric
            results.append(metric)
        return results

    def _evaluate_project(self, metric: MetricValue, definition: Mapping[str, Any],
                          payload: Mapping[str, Any], computed: Mapping[str, MetricValue]) -> None:
        calc = definition.get("calculation") or {}
        op = self._project_ops.get(calc.get("type"))
        if op is None:
            self._mark_unavailable(metric, definition,
                                   "tipo de cálculo não suportado: %s" % calc.get("type"))
            return
        try:
            value = op(calc, definition, payload, computed)
        except Exception as exc:                     # noqa: BLE001 — nunca derruba o dashboard
            self._log.warning("falha ao calcular %s: %s", metric.id, exc)
            self._mark_unavailable(metric, definition, "erro ao calcular a métrica")
            return
        if value is None:
            self._mark_unavailable(metric, definition,
                                   "não calculável com os dados disponíveis")
            return
        metric.value = _coerce(value, definition.get("format"))

    # ── escopo: portfólio ──────────────────────────────────────────────
    def compute_portfolio(self, projects: Sequence[ProjectResult]) -> list[MetricValue]:
        usable = [p for p in projects if p.record.is_usable]
        computed: dict[str, MetricValue] = {}
        results: list[MetricValue] = []
        for definition in self._portfolio_defs:
            metric = self._build(definition, "portfolio")
            calc = definition.get("calculation") or {}
            op = self._portfolio_ops.get(calc.get("type"))
            if op is None:
                self._mark_unavailable(metric, definition,
                                       "agregação não suportada: %s" % calc.get("type"))
            else:
                try:
                    value = op(calc, projects, usable, computed)
                except Exception as exc:             # noqa: BLE001
                    self._log.warning("falha ao agregar %s: %s", metric.id, exc)
                    value = None
                if value is None:
                    self._mark_unavailable(metric, definition, "sem dados suficientes")
                elif _is_number(value):
                    metric.value = _coerce(_round(value, definition.get("precision")),
                                           definition.get("format"))
                else:
                    metric.value = value
            computed[metric.id] = metric
            results.append(metric)
        return results

    # ── helpers ────────────────────────────────────────────────────────
    def _build(self, definition: Mapping[str, Any], scope: str) -> MetricValue:
        return MetricValue(
            id=definition["id"],
            name=definition.get("name") or definition["id"],
            description=definition.get("description") or "",
            category=definition.get("category") or "",
            unit=definition.get("unit"),
            format=definition.get("format") or "text",
            display_type=definition.get("display_type") or "table",
            order=int(definition.get("order") or 0),
            scope=scope,
        )

    def _mark_unavailable(self, metric: MetricValue, definition: Mapping[str, Any],
                          reason: str) -> None:
        metric.available = False
        metric.value = None
        behavior = definition.get("missing_value_behavior", NOT_AVAILABLE)
        metric.reason = reason if behavior == NOT_AVAILABLE else "%s (%s)" % (reason, behavior)

    def _settings_list(self, key: str) -> list[str]:
        values = self._settings.get(key) or []
        return [str(v) for v in values] if isinstance(values, (list, tuple)) else []

    @staticmethod
    def _items(payload: Mapping[str, Any], calc: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
        items = json_path(payload, calc.get("items_path", ""))
        if not isinstance(items, list):
            return None
        return [i for i in items if isinstance(i, Mapping)]

    @staticmethod
    def _numbers(computed: Mapping[str, MetricValue], projects: Iterable[ProjectResult],
                 metric_id: str) -> list[float]:
        values: list[float] = []
        for project in projects:
            metric = project.metric(metric_id)
            if metric is not None and metric.available and _is_number(metric.value):
                values.append(float(metric.value))
        return values

    # ── operações de projeto ───────────────────────────────────────────
    def _op_field(self, calc, definition, payload, computed):
        value = json_path(payload, (definition.get("source") or {}).get("path", ""))
        if _is_number(value):
            return _round(float(value), definition.get("precision"))
        return value if value not in ("", None) else None

    def _op_duration(self, calc, definition, payload, computed):
        seconds = _as_number(json_path(payload, calc.get("seconds_field", "")))
        if seconds is not None:
            return _round(seconds, definition.get("precision", 2))
        # sem campo direto: deriva de início/fim
        from .reader import _parse_iso                       # reuso do parser validado
        start = _parse_iso(str(json_path(payload, calc.get("start_field", "")) or ""))
        end = _parse_iso(str(json_path(payload, calc.get("end_field", "")) or ""))
        if start is None or end is None:
            return None
        return _round((end - start).total_seconds(), definition.get("precision", 2))

    def _op_count_items(self, calc, definition, payload, computed):
        items = self._items(payload, calc)
        return None if items is None else len(items)

    def _op_count_items_where(self, calc, definition, payload, computed):
        items = self._items(payload, calc)
        if items is None:
            return None
        wanted = calc.get("values")
        if wanted is None:
            wanted = self._settings_list(calc.get("values_from_settings", ""))
        wanted = {str(v) for v in (wanted or [])}
        field_name = calc.get("field", "status")
        return sum(1 for item in items if str(item.get(field_name)) in wanted)

    def _op_sum_items(self, calc, definition, payload, computed):
        items = self._items(payload, calc)
        if items is None:
            return None
        field_name = calc.get("value_field")
        total = sum(float(i[field_name]) for i in items
                    if field_name in i and _is_number(i[field_name]))
        return _round(total, definition.get("precision", 2))

    def _op_ratio(self, calc, definition, payload, computed):
        num = _as_number(json_path(payload, calc.get("numerator_path", "")))
        den = _as_number(json_path(payload, calc.get("denominator_path", "")))
        if num is None or den is None or den == 0:
            return None
        return _round(num / den, definition.get("precision", 3))

    def _op_percentage(self, calc, definition, payload, computed):
        num = self._resolve_operand(calc, "numerator", payload, computed)
        den = self._resolve_operand(calc, "denominator", payload, computed)
        if num is None or den is None or den == 0:
            return None
        return _round(num / den * 100.0, definition.get("precision", 1))

    def _resolve_operand(self, calc, role, payload, computed) -> float | None:
        metric_id = calc.get("%s_metric" % role)
        if metric_id:
            metric = computed.get(metric_id)
            if metric is None or not metric.available:
                return None
            return _as_number(metric.value)
        return _as_number(json_path(payload, calc.get("%s_path" % role, "")))

    def _op_max_item_by(self, calc, definition, payload, computed):
        return self._extreme(calc, payload, prefer_max=True)

    def _op_min_item_by(self, calc, definition, payload, computed):
        return self._extreme(calc, payload, prefer_max=False)

    def _extreme(self, calc, payload, prefer_max: bool):
        items = self._items(payload, calc)
        if not items:
            return None
        value_field, label_field = calc.get("value_field"), calc.get("label_field")
        candidates = [i for i in items if _is_number(i.get(value_field))]
        if calc.get("ignore_zero"):
            candidates = [i for i in candidates if float(i[value_field]) > 0]
        if not candidates:
            return None
        chosen = (max if prefer_max else min)(candidates, key=lambda i: float(i[value_field]))
        return chosen.get(label_field)

    def _op_token_cost(self, calc, definition, payload, computed):
        rates = self._settings.get("token_cost") or {}
        rate_in = _as_number(rates.get("input_per_million"))
        rate_out = _as_number(rates.get("output_per_million"))
        tokens_in = _as_number(json_path(payload, calc.get("input_path", "")))
        tokens_out = _as_number(json_path(payload, calc.get("output_path", "")))
        if None in (rate_in, rate_out) or tokens_in is None or tokens_out is None:
            return None
        cost = tokens_in * rate_in / 1e6 + tokens_out * rate_out / 1e6
        return _round(cost, definition.get("precision", 2))

    # ── agregações de portfólio ────────────────────────────────────────
    def _agg_count_projects(self, calc, projects, usable, computed):
        return len(projects)

    def _agg_count_by_status(self, calc, projects, usable, computed):
        wanted = {str(s) for s in (calc.get("statuses") or ProjectStatus.USABLE)}
        return sum(1 for p in projects if p.record.status in wanted)

    def _agg_sum(self, calc, projects, usable, computed):
        values = self._numbers(computed, usable, calc.get("metric_id", ""))
        return sum(values) if values else 0

    def _agg_average(self, calc, projects, usable, computed):
        values = self._numbers(computed, usable, calc.get("metric_id", ""))
        return sum(values) / len(values) if values else None

    def _agg_minimum(self, calc, projects, usable, computed):
        values = self._numbers(computed, usable, calc.get("metric_id", ""))
        return min(values) if values else None

    def _agg_maximum(self, calc, projects, usable, computed):
        values = self._numbers(computed, usable, calc.get("metric_id", ""))
        return max(values) if values else None

    def _agg_ratio(self, calc, projects, usable, computed):
        """Razão entre somas. `scale` converte unidade (ex.: 3600 = por hora)."""
        num_id = calc.get("numerator_metric", "")
        den_id = calc.get("denominator_metric", "")
        num_metric, den_metric = computed.get(num_id), computed.get(den_id)
        # opera sobre métricas de portfólio já calculadas, quando existirem
        if num_metric is not None and den_metric is not None:
            if not (num_metric.available and den_metric.available):
                return None
            num, den = _as_number(num_metric.value), _as_number(den_metric.value)
        else:
            num = sum(self._numbers(computed, usable, num_id))
            den = sum(self._numbers(computed, usable, den_id))
        if num is None or den in (None, 0):
            return None
        return num / den * float(calc.get("scale", 1))

    def _agg_count_metric_value(self, calc, projects, usable, computed):
        """Conta projetos cuja métrica está entre os valores informados."""
        metric_id = calc.get("metric_id", "")
        wanted = {str(v) for v in (calc.get("values") or [])}
        total = 0
        for project in usable:
            metric = project.metric(metric_id)
            if metric is not None and metric.available and str(metric.value) in wanted:
                total += 1
        return total

    def _agg_percentage(self, calc, projects, usable, computed):
        num = computed.get(calc.get("numerator_metric", ""))
        den = computed.get(calc.get("denominator_metric", ""))
        if num is None or den is None or not (num.available and den.available):
            return None
        num_v, den_v = _as_number(num.value), _as_number(den.value)
        if num_v is None or den_v in (None, 0):
            return None
        return num_v / den_v * 100.0

    def _agg_weighted_average(self, calc, projects, usable, computed):
        metric_id = calc.get("metric_id", "")
        weight_id = calc.get("weight_metric_id", "")
        total_weight = 0.0
        accumulated = 0.0
        for project in usable:
            value = project.metric(metric_id)
            weight = project.metric(weight_id)
            if not (value and weight and value.available and weight.available):
                continue
            v, w = _as_number(value.value), _as_number(weight.value)
            if v is None or w is None or w <= 0:
                continue
            accumulated += v * w
            total_weight += w
        return accumulated / total_weight if total_weight else None

    def _agg_count_by_project_field(self, calc, projects, usable, computed):
        metric_id = calc.get("metric_id", "")
        counter: Counter[str] = Counter()
        for project in usable:
            metric = project.metric(metric_id)
            if metric is not None and metric.available and metric.value is not None:
                counter[str(metric.value)] += 1
        return dict(sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))) or None

    def _agg_latest_value(self, calc, projects, usable, computed):
        from .reader import _parse_iso
        order_metric = calc.get("order_by_metric", "")
        value_key = calc.get("value", "project_name")
        best, best_when = None, None
        for project in usable:
            metric = project.metric(order_metric)
            if metric is None or not metric.available or not metric.value:
                continue
            when = _parse_iso(str(metric.value))
            if when is None:
                continue
            if best_when is None or when > best_when:
                best_when = when
                best = (project.record.project_name if value_key == "project_name"
                        else project.record.project_id)
        return best
