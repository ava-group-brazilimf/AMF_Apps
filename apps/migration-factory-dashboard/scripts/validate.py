# -*- coding: utf-8 -*-
"""Roteiro de validação da §16.1 — gera as evidências do relatório final.

Parte 1: leitura SOMENTE LEITURA do diretório real de projetos.
Parte 2: descoberta dinâmica em diretório temporário (add/remove).

    python scripts/validate.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT / "src"))

from mfd.config import ENV_PROJECTS_ROOT, load_app_config, load_metrics_config  # noqa: E402
from mfd.logging_setup import setup_logging                                     # noqa: E402
from mfd.models import ProjectStatus                                            # noqa: E402
from mfd.service import DashboardService                                        # noqa: E402
from mfd.web import create_app                                                  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    (PASSED if condition else FAILED).append(label)
    print("  [%s] %-58s %s" % ("OK " if condition else "FALHA", label, detail))


def digest(root: Path) -> str:
    parts = []
    for path in sorted(root.glob("*/outputs/pipeline_runner/pipeline-runner-metrics.json")):
        parts.append(path.name.encode() + hashlib.sha256(path.read_bytes()).digest())
    return hashlib.sha256(b"".join(parts)).hexdigest()


def part_one() -> None:
    print("\n=== PARTE 1 — dados reais (somente leitura) ===")
    config = load_app_config(APP_ROOT / "config" / "app.yaml", env={})
    before = digest(config.projects_root)

    service = DashboardService(config, load_metrics_config(APP_ROOT / "config" / "metrics.yaml"))
    snapshot = service.refresh()
    ids = [p.record.project_id for p in snapshot.projects]

    check("1. diretório raiz existe", config.projects_root.is_dir(), str(config.projects_root))
    check("2. nopcommerce-01 descoberto dinamicamente", "nopcommerce-01" in ids,
          "%d projeto(s): %s" % (len(ids), ", ".join(ids)))

    target = next((p for p in snapshot.projects if p.record.project_id == "nopcommerce-01"), None)
    check("3. arquivo de métricas localizado",
          bool(target and target.record.metrics_file_exists),
          target.record.metrics_relative_path if target else "—")
    check("4. JSON interpretado",
          bool(target and target.record.status in ProjectStatus.USABLE),
          target.record.status if target else "—")

    if target:
        available = [m.id for m in target.metrics if m.available]
        unavailable = [(m.id, m.reason) for m in target.metrics if not m.available]
        check("5. métricas calculadas", len(available) > 0,
              "%d de %d" % (len(available), len(target.metrics)))
        check("6. métricas indisponíveis justificadas",
              all(reason for _, reason in unavailable),
              "%d indisponível(is)" % len(unavailable))
        print("       calculadas .....: %s" % ", ".join(available))
        for metric_id, reason in unavailable:
            print("       indisponível ...: %s — %s" % (metric_id, reason))
        print("       valores ........:")
        for metric in target.metrics:
            if metric.available:
                print("           %-32s %s" % (metric.id, metric.value))

    app = create_app(service=service)
    app.config.update(TESTING=True)
    client = app.test_client()

    shell = client.get("/").get_data(as_text=True)
    check("7a. rota principal entregou o Control Tower",
          "Migration Factory Control Tower" in shell and "/api/dashboard-data" in shell,
          "HTTP 200, %d bytes, 7 abas" % len(shell))

    board = client.get("/api/dashboard-data").get_json()
    board_metrics = {m["id"]: m for m in board.get("portfolio_metrics", [])}
    check("7b. dashboard-data alimentou os KPIs do metrics.yaml",
          bool(board.get("runs")) and "total_executions" in board_metrics,
          "%d run(s), %d métrica(s) de portfólio"
          % (len(board.get("runs", [])), len(board_metrics)))

    detail = client.get("/detalhe").get_data(as_text=True)
    check("7c. visão de detalhe renderizou os valores",
          "nopcommerce-01" in detail and "198.257" in detail,
          "HTTP 200, %d bytes" % len(detail))

    projects_body = client.get("/api/projects").get_json()
    check("8. /api/projects retornou nopcommerce-01",
          "nopcommerce-01" in [p["project_id"] for p in projects_body["projects"]],
          "total_projects=%d" % projects_body["total_projects"])

    metrics_body = client.get("/api/metrics?project=nopcommerce-01").get_json()
    tokens = next((m for m in metrics_body["projects"][0]["metrics"]
                   if m["id"] == "project_total_tokens"), None)
    check("9. /api/metrics retornou as métricas calculadas",
          bool(tokens and tokens["value"] == 198257),
          "project_total_tokens=%s" % (tokens or {}).get("value"))

    serialized = json.dumps(metrics_body, ensure_ascii=False)
    check("9b. resposta sem caminho absoluto", str(config.projects_root) not in serialized)

    client.post("/api/refresh")
    check("10. nenhum arquivo de origem modificado", digest(config.projects_root) == before,
          "sha256 idêntico antes e depois")

    print("\n       portfólio consolidado:")
    for metric in snapshot.portfolio_metrics:
        print("           %-32s %s" % (metric.id,
                                       metric.value if metric.available else "indisponível"))


def part_two() -> None:
    print("\n=== PARTE 2 — descoberta dinâmica em diretório temporário ===")
    sample = json.loads((APP_ROOT / "scripts" / "sample-metrics.json").read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects"
        root.mkdir()

        def make(name: str, tokens: int) -> None:
            directory = root / name / "outputs" / "pipeline_runner"
            directory.mkdir(parents=True, exist_ok=True)
            payload = dict(sample, project_name=name)
            payload["token_metrics"] = {"total_tokens": tokens,
                                        "token_in": tokens // 2, "token_out": tokens - tokens // 2}
            (directory / "pipeline-runner-metrics.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        make("temp-alpha", 100)
        make("temp-bravo", 200)

        config = load_app_config(APP_ROOT / "config" / "app.yaml",
                                 env={ENV_PROJECTS_ROOT: str(root)})
        check("19. raiz sobrescrita por variável de ambiente",
              config.projects_root == root and config.projects_root_source.startswith("environment"),
              config.projects_root_source)

        service = DashboardService(config, load_metrics_config(APP_ROOT / "config" / "metrics.yaml"))

        first = service.refresh()
        totals = {m.id: m.value for m in first.portfolio_metrics}
        check("1-4. dois projetos temporários descobertos",
              [p.record.project_id for p in first.projects] == ["temp-alpha", "temp-bravo"])
        check("     consolidação inicial", totals["portfolio_total_tokens"] == 300,
              "portfolio_total_tokens=%s" % totals["portfolio_total_tokens"])

        make("temp-charlie", 400)
        second = service.refresh()
        totals2 = {m.id: m.value for m in second.portfolio_metrics}
        check("5-7. terceiro projeto incluído automaticamente",
              second.added_projects == ["temp-charlie"] and len(second.projects) == 3)
        check("     consolidação recalculada", totals2["portfolio_total_tokens"] == 700,
              "portfolio_total_tokens=%s" % totals2["portfolio_total_tokens"])

        shutil.rmtree(root / "temp-alpha")
        third = service.refresh()
        totals3 = {m.id: m.value for m in third.portfolio_metrics}
        ids = [p.record.project_id for p in third.projects]
        check("8-10. projeto removido não aparece mais",
              third.removed_projects == ["temp-alpha"] and "temp-alpha" not in ids,
              "restantes: %s" % ", ".join(ids))
        check("11. métricas consolidadas recalculadas",
              totals3["portfolio_total_tokens"] == 600
              and totals3["total_discovered_projects"] == 2,
              "portfolio_total_tokens=%s" % totals3["portfolio_total_tokens"])


def main() -> int:
    setup_logging("WARNING")
    part_one()
    part_two()
    print("\n=== RESULTADO: %d verificação(ões) OK, %d falha(s) ===" % (len(PASSED), len(FAILED)))
    for label in FAILED:
        print("  FALHOU: %s" % label)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
