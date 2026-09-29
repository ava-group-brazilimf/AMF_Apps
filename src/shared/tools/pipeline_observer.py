"""
pipeline_observer.py — Deterministic observability tool for AVA Fabric agent pipeline.

Designed for direct integration with the master-orchestrator during pipeline execution.
Provides lifecycle tracking, real-time dashboards, multi-format reports, and run comparison.

Architecture:
  - Uses agent_observability.py for low-level state persistence (JSONL + JSON)
  - Adds: dashboard, import-json, compare, report (xlsx+json+md), and track (atomic start+end)
  - All timestamps in BRZ (UTC-3)
  - Costs calculated per-model via MODEL_PRICING (default: Claude Sonnet 4.6);
    unrecognized/unset --model values fall back to the Sonnet-tier rate

Usage during pipeline execution:
  # 1. Initialize run at pipeline start
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 init

  # 2. Track each agent (atomic: records start, waits, records end)
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 track \\
      --agent ava-asis-orchestrator --phase F1 --version 2.18.0 \\
      --status completed --tokens-in 50000 --tokens-out 30000

  # 3. View dashboard anytime
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 dashboard

  # 4. Finalize and generate all reports
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 finalize --auto-report

  # 5. Compare two runs
  python src/shared/tools/pipeline_observer.py compare \\
      --run-a projects/Meu-ERP-001/outputs/observability/pipeline-run-state.json \\
      --run-b projects/Meu-ERP-002/outputs/observability/pipeline-run-state.json

  # 6. Import from external JSON
  python src/shared/tools/pipeline_observer.py -p Meu-ERP-001 import-json \\
      --input docs/optimization/agent-observability-Meu-ERP-001.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import uuid
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ─── Constants ───────────────────────────────────────────────────────────────

BRZ = timezone(timedelta(hours=-3))

# Default model for this pipeline (used when no --model is passed and an
# agent doesn't self-report a different one)
DEFAULT_MODEL = "Claude Sonnet 4.6"

# Per-token pricing by model family (USD). Matched case-insensitively by
# substring against whatever --model string is passed — this is necessarily
# approximate for model names not listed here (see _get_pricing_for_model).
# (cost_per_token_in, cost_per_token_out)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude opus":   (15.0 / 1_000_000, 75.0 / 1_000_000),
    "claude sonnet": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "claude haiku":  (1.0 / 1_000_000, 5.0 / 1_000_000),
    "gpt-4":         (2.5 / 1_000_000, 10.0 / 1_000_000),
    "gpt-3.5":       (0.5 / 1_000_000, 1.5 / 1_000_000),
    "gemini":        (1.25 / 1_000_000, 5.0 / 1_000_000),
}

# Fallback rate for unrecognized model strings — same tier as DEFAULT_MODEL.
FALLBACK_PRICING = MODEL_PRICING["claude sonnet"]


def _get_pricing_for_model(model: str | None) -> tuple[float, float]:
    """Case-insensitive substring match against MODEL_PRICING; falls back to
    the default (Sonnet-tier) rate for unrecognized/empty model strings."""
    if model:
        needle = model.strip().lower()
        for key, rates in MODEL_PRICING.items():
            if key in needle:
                return rates
    return FALLBACK_PRICING

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

# ⚠️ Espelho de agent_registry.PHASE_ORDER / PHASE_NAMES. Mudança aqui exige
# mudança lá — tests/tools/test_agent_registry.py trava a coerência dos dois.
PHASE_ORDER = ["F1", "F2", "F3", "F3S", "F4", "F5", "F6", "F7", "F8"]

PHASE_NAMES = {
    "F1": "AS-IS Diagnostic",
    "F2": "TO-BE Architecture",
    "F3": "Prototype",
    "F3S": "SpecKit Planning",
    "F4": "Stack / Codegen",
    "F5": "QA",
    "F6": "DevOps",
    "F7": "Deliverables",
    "F8": "Summary",
}

# Catálogo de fallback — usado apenas se a varredura de agent_registry falhar
# (execução fora da árvore do repositório). A fonte de verdade é o frontmatter
# dos próprios agentes; ver AGENT_CATALOG logo abaixo e specs/032.
_STATIC_AGENT_CATALOG: list[dict[str, str]] = [
    # F1
    {"agent": "ava-asis-orchestrator",          "phase": "F1", "version": "2.22.0"},
    {"agent": "ava-asis-solution-delphi",       "phase": "F1", "version": "2.8.1"},
    {"agent": "ava-asis-db-analyzer",           "phase": "F1", "version": "1.6.1"},
    {"agent": "ava-asis-events-pubsub",         "phase": "F1", "version": "1.2.1"},
    {"agent": "ava-asis-documentation",         "phase": "F1", "version": "3.1.1"},
    {"agent": "ava-asis-inventory",             "phase": "F1", "version": "1.6.1"},
    {"agent": "ava-asis-security-orchestrator", "phase": "F1", "version": "3.3.0"},
    {"agent": "ava-asis-gaps-risks",            "phase": "F1", "version": "1.4.0"},
    {"agent": "ava-asis-gap-migration-analyzer","phase": "F1", "version": "1.1.0"},
    {"agent": "ava-asis-bridge-fastqa",         "phase": "F1", "version": "4.1.0"},
    {"agent": "ava-summary (F1)",               "phase": "F1", "version": "1.0.0"},
    # F2
    {"agent": "ava-tobe-orchestrator",          "phase": "F2", "version": "2.3.0"},
    {"agent": "ava-tobe-adr",                   "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-architecture-design",   "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-database-design",       "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-security-design",       "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-architecture-technical","phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-measure-size",          "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-migration-plan",        "phase": "F2", "version": "1.2.1"},
    {"agent": "ava-tobe-risk-mitigation",       "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-user-journeys",         "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-summary (F2)",               "phase": "F2", "version": "1.0.0"},
    # F3
    {"agent": "ava-prototype",                  "phase": "F3", "version": "1.0.0"},
    {"agent": "ava-summary (F3)",               "phase": "F3", "version": "1.0.0"},
    # F4
    {"agent": "ava-stack-orchestrator",         "phase": "F4", "version": "1.7.1"},
    {"agent": "ava-stack-docs-researcher",      "phase": "F4", "version": "1.0.0"},
    {"agent": "ava-stack-dotnet-backend",       "phase": "F4", "version": "1.0.0"},
    {"agent": "ava-stack-angular-frontend",     "phase": "F4", "version": "1.0.0"},
    {"agent": "ava-stack-build-validator",      "phase": "F4", "version": "2.3.0"},
    {"agent": "ava-summary (F4)",               "phase": "F4", "version": "1.0.0"},
    # F5
    {"agent": "ava-qa-orchestrator",            "phase": "F5", "version": "1.2.2"},
    {"agent": "ava-qa-behavior-mapping",        "phase": "F5", "version": "1.0.0"},
    {"agent": "ava-qa-gaps-requirements",       "phase": "F5", "version": "1.0.0"},
    {"agent": "ava-qa-scenario-generator",      "phase": "F5", "version": "2.1.0"},
    {"agent": "ava-qa-test-case-generator",     "phase": "F5", "version": "1.0.0"},
    {"agent": "ava-qa-script-generator",        "phase": "F5", "version": "1.2.0"},
    {"agent": "ava-qa-exploratory",             "phase": "F5", "version": "2.0.0"},
    {"agent": "ava-qa-evidence-capture",        "phase": "F5", "version": "2.1.0"},
    {"agent": "ava-qa-defect-identifier",       "phase": "F5", "version": "1.0.0"},
    {"agent": "ava-summary (F5)",               "phase": "F5", "version": "1.0.0"},
    # F6
    {"agent": "ava-devops-iac",                 "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-ci",                  "phase": "F6", "version": "1.2.0"},
    {"agent": "ava-devops-cd",                  "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-containerize",        "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-iac-azure",           "phase": "F6", "version": "2.6.0"},
    {"agent": "ava-devops-cost-estimate",       "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-compare-version",     "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-package-approval",    "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-summary (F6)",               "phase": "F6", "version": "1.0.0"},
    # F7
    {"agent": "ava-deliverable-tech-docs",           "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-migration-plan",      "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-security-compliance", "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-test-evidence",       "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-code-templates",      "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-client-demo",         "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-packager",            "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-summary (F7 — FINAL)",            "phase": "F7", "version": "1.0.0"},
]


def _load_agent_catalog() -> list[dict[str, str]]:
    """Catálogo derivado do frontmatter dos agentes em disco.

    Antes de specs/032 esta lista era mantida à mão aqui E em
    ``generate_observability_report.py``; as duas divergiram entre si e da
    realidade (52 de 101 agentes ausentes). Agora `agent_registry` varre o disco
    e o literal acima fica só como fallback.

    Import defensivo: o catálogo nunca pode derrubar o observer, que é chamado
    por ~100 agentes via ``Bash:``.
    """
    try:
        if str(SCRIPT_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPT_DIR))
        import agent_registry  # noqa: PLC0415
        return agent_registry.catalog_or(_STATIC_AGENT_CATALOG)
    except Exception:  # noqa: BLE001
        return _STATIC_AGENT_CATALOG


#: Catálogo efetivo — derivado do disco, com fallback estático.
AGENT_CATALOG: list[dict[str, str]] = _load_agent_catalog()


# ─── State Management ───────────────────────────────────────────────────────

def _get_data_dir(project_name: str) -> Path:
    d = PROJECT_ROOT / "projects" / project_name / "outputs" / "observability"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_state_file(project_name: str) -> Path:
    return _get_data_dir(project_name) / "pipeline-run-state.json"


def _get_events_file(project_name: str) -> Path:
    return _get_data_dir(project_name) / "agent-events.jsonl"


def _sanitize_agent_name(agent_name: str) -> str:
    """Sanitize an agent name for use as a filesystem directory name."""
    return "".join(c if (c.isalnum() or c in "-_") else "-" for c in agent_name)


def _get_agent_dir(project_name: str, agent_name: str) -> Path:
    """Return the per-agent observability directory for self-reporting agents."""
    d = _get_data_dir(project_name) / _sanitize_agent_name(agent_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_agent_metrics(project_name: str, agent_name: str, run_id: str, agent_data: dict[str, Any]) -> None:
    """Write a self-contained per-agent metrics snapshot and append its event line."""
    agent_dir = _get_agent_dir(project_name, agent_name)
    metrics_file = agent_dir / "metrics.json"
    payload = {"run_id": run_id, "agent": agent_name, **agent_data}
    metrics_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    events_file = agent_dir / "events.jsonl"
    with open(events_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _now_brz() -> str:
    return datetime.now(BRZ).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def _write_headroom_metric(project_name: str, agent_name: str, run_id: str,
                           agent_data: dict[str, Any]) -> None:
    """Espelha o auto-reporte no JSONL do Headroom (specs/032 · D1).

    É isto que dá cobertura de **toda** a esteira sem instruir 100 agentes: os
    ~98 que já chamam `track` passam a alimentar o headroom-metrics.jsonl de
    graça, em qualquer fase.

    Só grava o que o agente realmente sabe — volume e identidade. Os campos de
    compressão ficam ``None`` porque o agente **não** conhece o tamanho
    pré-compressão; quem sabe isso é o proxy, e `headroom_tool.py attribute`
    preenche essas linhas depois com ``source: "proxy"``.

    Silencioso por design: sem a tool instalada, `track` segue normal (IV3).
    """
    try:
        headroom_dir = SCRIPT_DIR / "headroom"
        if not headroom_dir.is_dir():
            return
        if str(headroom_dir) not in sys.path:
            sys.path.insert(0, str(headroom_dir))
        import headroom_config  # noqa: PLC0415

        cfg = headroom_config.load_config(project_name)
        if not cfg.get("enabled", True):
            return
        path = headroom_config.metrics_path(project_name, cfg)
        payload = {
            "ts": _now_brz(),
            "run_id": run_id,
            "agent_id": agent_name,
            "phase": agent_data.get("phase", ""),
            "version": agent_data.get("version", ""),
            "model": agent_data.get("model"),
            "source": "self-report",
            "status": agent_data.get("status"),
            "tokens_in": agent_data.get("tokens_in", 0),
            "tokens_out": agent_data.get("tokens_out", 0),
            "tokens_total": agent_data.get("tokens_total", 0),
            "duration_ms": agent_data.get("duration_ms", 0),
            # Desconhecidos no auto-reporte — preenchidos por `attribute`.
            "original_tokens": None,
            "compressed_tokens": None,
            "tokens_saved": None,
            "savings_pct": None,
            "context_limit": int(cfg.get("context_limit", 200000)),
            "error": agent_data.get("error_detail") or None,
        }
        with open(path, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - observabilidade nunca derruba a esteira
        return


def _load_state(project_name: str) -> dict:
    f = _get_state_file(project_name)
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}


def _save_state(project_name: str, state: dict):
    f = _get_state_file(project_name)
    f.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_event(project_name: str, event: dict):
    f = _get_events_file(project_name)
    with open(f, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(event, ensure_ascii=False) + "\n")


def _calc_cost(tokens_in: int, tokens_out: int, model: str | None = None) -> float:
    cost_in, cost_out = _get_pricing_for_model(model)
    return round(tokens_in * cost_in + tokens_out * cost_out, 6)


def _calc_duration_ms(start_str: str, end_str: str) -> int:
    try:
        s = datetime.fromisoformat(start_str)
        e = datetime.fromisoformat(end_str)
        return max(0, int((e - s).total_seconds() * 1000))
    except (ValueError, TypeError):
        return 0


def _format_duration(ms: int) -> str:
    """Format milliseconds to human-readable duration."""
    if ms <= 0:
        return "—"
    secs = ms / 1000
    if secs < 60:
        return f"{secs:.1f}s"
    mins = secs / 60
    if mins < 60:
        return f"{int(mins)}m {int(secs % 60)}s"
    hours = mins / 60
    return f"{int(hours)}h {int(mins % 60)}m"


def _get_agent_catalog_entry(agent_name: str) -> dict | None:
    for entry in AGENT_CATALOG:
        if entry["agent"] == agent_name:
            return entry
    return None


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a new pipeline run."""
    project = args.project
    run_id = str(uuid.uuid4())[:8].upper()
    run_type = getattr(args, "run_type", "full-pipeline") or "full-pipeline"
    model = getattr(args, "model", DEFAULT_MODEL) or DEFAULT_MODEL

    state = {
        "run_id": run_id,
        "project_name": project,
        "run_type": run_type,
        "model": model,
        "start_time": _now_brz(),
        "end_time": None,
        "status": "running",
        "agents": {},
    }
    _save_state(project, state)

    # Clear previous events
    ef = _get_events_file(project)
    if ef.exists():
        ef.unlink()

    print(json.dumps({
        "run_id": run_id,
        "project": project,
        "status": "initialized",
        "start_time": state["start_time"],
    }, indent=2))


def cmd_track(args: argparse.Namespace) -> None:
    """Atomic agent tracking — records start_time, end_time, tokens, cost in one call.

    This is the primary command used during pipeline execution.
    Called AFTER an agent completes (with measured metrics).
    """
    project = args.project
    state = _load_state(project)
    if not state:
        print("ERROR: No active run. Call 'init' first.", file=sys.stderr)
        sys.exit(1)

    agent = args.agent
    phase = args.phase or ""
    version = args.version or ""
    status = args.status or "completed"
    tokens_in = args.tokens_in or 0
    tokens_out = args.tokens_out or 0
    model = args.model or state.get("model", DEFAULT_MODEL)
    start_time = args.start_time or _now_brz()
    end_time = args.end_time or _now_brz()
    duration_ms = args.duration_ms or _calc_duration_ms(start_time, end_time)
    cost_usd = _calc_cost(tokens_in, tokens_out, model)
    error_detail = args.error_detail or ""

    # If no phase/version provided, look up from catalog
    if not phase or not version:
        catalog_entry = _get_agent_catalog_entry(agent)
        if catalog_entry:
            phase = phase or catalog_entry["phase"]
            version = version or catalog_entry["version"]

    agent_data: dict[str, Any] = {
        "phase": phase,
        "version": version,
        "start_time": start_time,
        "end_time": end_time,
        "duration_ms": duration_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "cost_usd": cost_usd,
        "status": status,
        "model": model,
        "run_type": state.get("run_type", "full-pipeline"),
    }
    if error_detail:
        agent_data["error_detail"] = error_detail

    state["agents"][agent] = agent_data
    _save_state(project, state)

    # Self-reporting agents also get a per-agent snapshot under
    # outputs/observability/{agent_name}/, independent of the shared state.
    _write_agent_metrics(project, agent, state["run_id"], agent_data)

    # E o mesmo evento alimenta o JSONL do Headroom — é o que estende a
    # atribuição de economia a TODOS os agentes da esteira sem exigir uma
    # segunda diretiva Bash em ~100 arquivos .md (specs/032 · D1).
    _write_headroom_metric(project, agent, state["run_id"], agent_data)

    # Append events
    _append_event(project, {
        "type": "agent_tracked",
        "run_id": state["run_id"],
        "agent": agent,
        "phase": phase,
        "version": version,
        "status": status,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "duration_ms": duration_ms,
        "cost_usd": cost_usd,
        "model": model,
        "timestamp": end_time,
    })

    print(json.dumps({
        "agent": agent,
        "phase": phase,
        "status": status,
        "duration": _format_duration(duration_ms),
        "tokens_total": tokens_in + tokens_out,
        "cost_usd": cost_usd,
    }))


def cmd_finalize(args: argparse.Namespace) -> None:
    """Finalize the pipeline run and optionally generate reports."""
    project = args.project
    state = _load_state(project)
    if not state:
        print("ERROR: No active run.", file=sys.stderr)
        sys.exit(1)

    state["end_time"] = _now_brz()

    statuses = [a.get("status", "") for a in state["agents"].values()]
    if all(s == "completed" for s in statuses):
        state["status"] = "complete"
    elif any(s == "failed" for s in statuses):
        state["status"] = "partial"
    else:
        state["status"] = "complete"

    _save_state(project, state)

    result = {
        "run_id": state["run_id"],
        "status": state["status"],
        "end_time": state["end_time"],
        "total_agents": len(state["agents"]),
        "completed": sum(1 for a in state["agents"].values() if a["status"] == "completed"),
        "failed": sum(1 for a in state["agents"].values() if a["status"] == "failed"),
    }

    # Auto-generate reports if requested
    auto_report = getattr(args, "auto_report", False)
    if auto_report:
        xlsx_path = _generate_xlsx(project, state)
        json_path = _generate_json_snapshot(project, state)
        md_path = _generate_markdown_report(project, state)
        result["reports"] = {
            "xlsx": str(xlsx_path),
            "json": str(json_path),
            "markdown": str(md_path),
        }

    print(json.dumps(result, indent=2))


def cmd_dashboard(args: argparse.Namespace) -> None:
    """Print formatted dashboard to terminal for real-time monitoring."""
    project = args.project
    state = _load_state(project)
    if not state:
        print("No active run found.", file=sys.stderr)
        sys.exit(1)

    run_id = state.get("run_id", "?")
    run_status = state.get("status", "?")
    agents = state.get("agents", {})
    total_agents = len(agents)
    completed = sum(1 for a in agents.values() if a.get("status") == "completed")
    failed = sum(1 for a in agents.values() if a.get("status") == "failed")
    running = sum(1 for a in agents.values() if a.get("status") == "running")
    skipped = sum(1 for a in agents.values() if a.get("status") == "skipped")
    pending = total_agents - completed - failed - running - skipped

    total_tokens_in = sum(a.get("tokens_in", 0) for a in agents.values())
    total_tokens_out = sum(a.get("tokens_out", 0) for a in agents.values())
    total_tokens = total_tokens_in + total_tokens_out
    total_cost = sum(a.get("cost_usd", 0.0) for a in agents.values())
    total_duration = sum(a.get("duration_ms", 0) for a in agents.values())

    # Progress bar
    pct = (completed / total_agents * 100) if total_agents > 0 else 0
    bar_len = 40
    filled = int(bar_len * completed / total_agents) if total_agents > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║          AVA FABRIC — PIPELINE OBSERVABILITY DASHBOARD              ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Run ID     : {run_id:<54} ║")
    print(f"║  Project    : {state.get('project_name', '?'):<54} ║")
    print(f"║  Status     : {run_status:<54} ║")
    print(f"║  Model      : {state.get('model', '?'):<54} ║")
    print(f"║  Start      : {state.get('start_time', '—'):<54} ║")
    print(f"║  End        : {state.get('end_time', '—') or '— (running)' :<54} ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Progress   : [{bar}] {pct:5.1f}%      ║")
    print(f"║  Agents     : {completed} ✅  {failed} ❌  {running} 🔄  {skipped} ⏭  {pending} ⏳   (total: {total_agents})  ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Tokens IN  : {total_tokens_in:>12,}                                          ║")
    print(f"║  Tokens OUT : {total_tokens_out:>12,}                                          ║")
    print(f"║  Tokens TOT : {total_tokens:>12,}                                          ║")
    print(f"║  Total Cost : ${total_cost:>11,.4f}                                          ║")
    print(f"║  Duration   : {_format_duration(total_duration):<54} ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  PHASE BREAKDOWN                                                    ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")

    # Phase breakdown
    phases: dict[str, dict] = {}
    for a_name, a_data in agents.items():
        p = a_data.get("phase", "?")
        if p not in phases:
            phases[p] = {"completed": 0, "failed": 0, "total": 0, "cost": 0.0, "duration": 0, "tokens": 0}
        phases[p]["total"] += 1
        if a_data.get("status") == "completed":
            phases[p]["completed"] += 1
        elif a_data.get("status") == "failed":
            phases[p]["failed"] += 1
        phases[p]["cost"] += a_data.get("cost_usd", 0.0)
        phases[p]["duration"] += a_data.get("duration_ms", 0)
        phases[p]["tokens"] += a_data.get("tokens_total", 0)

    print("║  Phase │ Name                 │ Agents │   Cost │ Duration │ Status  ║")
    print("║  ──────┼──────────────────────┼────────┼────────┼──────────┼──────── ║")
    for p in PHASE_ORDER:
        if p in phases:
            d = phases[p]
            name = PHASE_NAMES.get(p, "")[:20]
            status_icon = "✅" if d["completed"] == d["total"] else ("❌" if d["failed"] > 0 else "🔄")
            print(f"║  {p:<5} │ {name:<20} │ {d['completed']:>2}/{d['total']:<3} │ ${d['cost']:>5.2f} │ {_format_duration(d['duration']):>8} │ {status_icon}       ║")

    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  TOP 5 COSTLIEST AGENTS                                             ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")

    # Top 5 costliest agents
    sorted_agents = sorted(agents.items(), key=lambda x: x[1].get("cost_usd", 0), reverse=True)[:5]
    for a_name, a_data in sorted_agents:
        short_name = a_name[:35]
        cost = a_data.get("cost_usd", 0.0)
        dur = _format_duration(a_data.get("duration_ms", 0))
        tokens = a_data.get("tokens_total", 0)
        print(f"║  {short_name:<36} ${cost:>6.3f}  {dur:>8}  {tokens:>7,} tok ║")

    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()


def cmd_report(args: argparse.Namespace) -> None:
    """Generate all report formats: Excel, JSON snapshot, and Markdown."""
    project = args.project
    state = _load_state(project)
    if not state:
        print("ERROR: No run data found.", file=sys.stderr)
        sys.exit(1)

    fmt = getattr(args, "format", "all") or "all"
    output_dir = getattr(args, "output_dir", None)

    results = {}

    if fmt in ("all", "xlsx"):
        results["xlsx"] = str(_generate_xlsx(project, state, output_dir))

    if fmt in ("all", "json"):
        results["json"] = str(_generate_json_snapshot(project, state, output_dir))

    if fmt in ("all", "md"):
        results["markdown"] = str(_generate_markdown_report(project, state, output_dir))

    print(json.dumps(results, indent=2))


def cmd_import_json(args: argparse.Namespace) -> None:
    """Import metrics from an external JSON file into the pipeline state."""
    project = args.project
    input_path = Path(args.input)

    if not input_path.exists():
        # Try relative to PROJECT_ROOT
        input_path = PROJECT_ROOT / args.input
        if not input_path.exists():
            print(f"ERROR: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)

    data = json.loads(input_path.read_text(encoding="utf-8"))

    # Validate structure
    if "agents" not in data or "run_id" not in data:
        print("ERROR: Invalid JSON structure. Expected 'run_id' and 'agents' keys.", file=sys.stderr)
        sys.exit(1)

    _save_state(project, data)

    agent_count = len(data.get("agents", {}))
    completed = sum(1 for a in data["agents"].values() if a.get("status") == "completed")
    print(json.dumps({
        "imported": True,
        "run_id": data["run_id"],
        "agents": agent_count,
        "completed": completed,
        "source": str(input_path),
    }, indent=2))


def cmd_compare(args: argparse.Namespace) -> None:
    """Compare two pipeline runs side by side."""
    path_a = Path(args.run_a)
    path_b = Path(args.run_b)

    for p in (path_a, path_b):
        if not p.exists():
            resolved = PROJECT_ROOT / p
            if resolved.exists():
                if p == path_a:
                    path_a = resolved
                else:
                    path_b = resolved
            else:
                print(f"ERROR: File not found: {p}", file=sys.stderr)
                sys.exit(1)

    state_a = json.loads(path_a.read_text(encoding="utf-8"))
    state_b = json.loads(path_b.read_text(encoding="utf-8"))

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║              PIPELINE RUN COMPARISON                                ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Run A: {state_a.get('run_id', '?'):<20} │ Run B: {state_b.get('run_id', '?'):<20}   ║")
    print("╠═══════════════════════════════╤════════════════╤════════════════════╣")
    print("║  Metric                       │     Run A      │     Run B          ║")
    print("╠═══════════════════════════════╪════════════════╪════════════════════╣")

    def _sum_field(state: dict, field: str) -> float:
        return sum(a.get(field, 0) for a in state.get("agents", {}).values())

    metrics = [
        ("Total Agents", len(state_a.get("agents", {})), len(state_b.get("agents", {}))),
        ("Completed", sum(1 for a in state_a.get("agents", {}).values() if a["status"] == "completed"),
         sum(1 for a in state_b.get("agents", {}).values() if a["status"] == "completed")),
        ("Tokens IN", _sum_field(state_a, "tokens_in"), _sum_field(state_b, "tokens_in")),
        ("Tokens OUT", _sum_field(state_a, "tokens_out"), _sum_field(state_b, "tokens_out")),
        ("Tokens Total", _sum_field(state_a, "tokens_total"), _sum_field(state_b, "tokens_total")),
        ("Total Cost (USD)", round(_sum_field(state_a, "cost_usd"), 4), round(_sum_field(state_b, "cost_usd"), 4)),
        ("Duration (ms)", _sum_field(state_a, "duration_ms"), _sum_field(state_b, "duration_ms")),
    ]

    for label, val_a, val_b in metrics:
        if isinstance(val_a, float):
            a_str = f"${val_a:>11,.4f}"
            b_str = f"${val_b:>11,.4f}"
        else:
            a_str = f"{val_a:>14,}"
            b_str = f"{val_b:>14,}"
        print(f"║  {label:<29} │ {a_str} │ {b_str}     ║")

    print("╚═══════════════════════════════╧════════════════╧════════════════════╝")

    # Delta analysis per agent
    all_agents = set(state_a.get("agents", {}).keys()) | set(state_b.get("agents", {}).keys())
    deltas = []
    for agent in sorted(all_agents):
        a = state_a.get("agents", {}).get(agent, {})
        b = state_b.get("agents", {}).get(agent, {})
        cost_a = a.get("cost_usd", 0)
        cost_b = b.get("cost_usd", 0)
        delta_cost = cost_b - cost_a
        if abs(delta_cost) > 0.01:
            deltas.append((agent, cost_a, cost_b, delta_cost))

    if deltas:
        print()
        print("  Cost Deltas (|Δ| > $0.01):")
        deltas.sort(key=lambda x: abs(x[3]), reverse=True)
        for agent, ca, cb, delta in deltas[:10]:
            arrow = "↑" if delta > 0 else "↓"
            print(f"    {agent:<40} A=${ca:.3f}  B=${cb:.3f}  Δ={arrow}${abs(delta):.3f}")

    print()


def cmd_status(args: argparse.Namespace) -> None:
    """Show current pipeline run status as JSON."""
    project = args.project
    state = _load_state(project)
    if not state:
        print("{}")
        return
    print(json.dumps(state, indent=2, ensure_ascii=False))


# ─── Report Generators ──────────────────────────────────────────────────────

def _generate_xlsx(project_name: str, state: dict, output_dir: str | None = None) -> Path:
    """Generate comprehensive Excel report with 4 sheets."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
        from openpyxl.utils import get_column_letter
        from openpyxl.chart import BarChart, PieChart, Reference
    except ImportError:
        print("ERROR: openpyxl not installed. Run: pip install openpyxl", file=sys.stderr)
        sys.exit(1)

    wb = Workbook()
    run_id = state.get("run_id", "N/A")
    run_type = state.get("run_type", "full-pipeline")

    # Styles
    hdr_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    hdr_fill = PatternFill(start_color="FF6600", end_color="FF6600", fill_type="solid")
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    status_fills = {
        "completed": PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
        "failed": PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
        "running": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
        "skipped": PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"),
        "pending": PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"),
    }

    # ── Sheet 1: Agent Metrics ──────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Agent Metrics"

    headers = [
        "Run ID", "Data/Hora", "Agent Name", "Phase", "Versão",
        "Tokens IN", "Tokens OUT", "Tokens Total", "Duration (ms)",
        "Cost (USD)", "Status", "Model", "Run Type",
    ]
    for ci, h in enumerate(headers, 1):
        c = ws1.cell(row=1, column=ci, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.alignment = hdr_align
        c.border = border

    # Sort agents by phase order then by start_time
    def _agent_sort_key(item: tuple[str, dict]) -> tuple[int, str]:
        name, data = item
        phase = data.get("phase", "Z")
        idx = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else 99
        return (idx, data.get("start_time", ""))

    sorted_agents = sorted(state.get("agents", {}).items(), key=_agent_sort_key)

    row = 2
    for agent_name, m in sorted_agents:
        vals = [
            run_id, m.get("start_time", ""), agent_name, m.get("phase", ""),
            m.get("version", ""), m.get("tokens_in", 0), m.get("tokens_out", 0),
            m.get("tokens_total", 0), m.get("duration_ms", 0),
            m.get("cost_usd", 0.0), m.get("status", ""), m.get("model", ""), run_type,
        ]
        for ci, v in enumerate(vals, 1):
            c = ws1.cell(row=row, column=ci, value=v)
            c.border = border
            c.alignment = Alignment(horizontal="center", vertical="center")
            if ci == 11:
                c.fill = status_fills.get(str(v), PatternFill())
            if ci == 10:
                c.number_format = '$#,##0.000000'
        row += 1

    # Totals
    total_row = row
    ws1.cell(row=total_row, column=1, value="TOTAL").font = Font(bold=True)
    for col in [6, 7, 8, 9, 10]:
        cl = get_column_letter(col)
        c = ws1.cell(row=total_row, column=col, value=f"=SUM({cl}2:{cl}{total_row - 1})")
        c.font = Font(bold=True)
        c.border = border
        if col == 10:
            c.number_format = '$#,##0.000000'

    # Auto-width
    for ci in range(1, len(headers) + 1):
        max_w = len(str(headers[ci - 1]))
        for r in range(2, row + 1):
            v = ws1.cell(row=r, column=ci).value
            if v:
                max_w = max(max_w, len(str(v)))
        ws1.column_dimensions[get_column_letter(ci)].width = min(max_w + 4, 42)
    ws1.freeze_panes = "A2"

    # ── Sheet 2: Pipeline Summary ───────────────────────────────────────
    ws2 = wb.create_sheet("Pipeline Summary")
    agents = state.get("agents", {})
    total_tok_in = sum(a.get("tokens_in", 0) for a in agents.values())
    total_tok_out = sum(a.get("tokens_out", 0) for a in agents.values())
    total_cost = sum(a.get("cost_usd", 0.0) for a in agents.values())
    total_dur = sum(a.get("duration_ms", 0) for a in agents.values())

    summary_rows = [
        ("Run ID", run_id),
        ("Project", state.get("project_name", "")),
        ("Run Type", run_type),
        ("Model", state.get("model", "")),
        ("Start Time", state.get("start_time", "")),
        ("End Time", state.get("end_time", "") or "—"),
        ("Status", state.get("status", "")),
        ("", ""),
        ("Total Agents", len(agents)),
        ("Completed", sum(1 for a in agents.values() if a["status"] == "completed")),
        ("Failed", sum(1 for a in agents.values() if a["status"] == "failed")),
        ("Skipped", sum(1 for a in agents.values() if a.get("status") == "skipped")),
        ("", ""),
        ("Total Tokens IN", f"{total_tok_in:,}"),
        ("Total Tokens OUT", f"{total_tok_out:,}"),
        ("Total Tokens", f"{total_tok_in + total_tok_out:,}"),
        ("Total Cost (USD)", f"${total_cost:,.4f}"),
        ("Total Duration", _format_duration(total_dur)),
        ("", ""),
        ("Avg Tokens/Agent", f"{(total_tok_in + total_tok_out) // max(len(agents), 1):,}"),
        ("Avg Cost/Agent", f"${total_cost / max(len(agents), 1):,.4f}"),
        ("Avg Duration/Agent", _format_duration(total_dur // max(len(agents), 1))),
    ]
    for r, (label, value) in enumerate(summary_rows, 1):
        ws2.cell(row=r, column=1, value=label).font = Font(bold=True) if label else Font()
        ws2.cell(row=r, column=2, value=value)
    ws2.column_dimensions["A"].width = 22
    ws2.column_dimensions["B"].width = 40

    # ── Sheet 3: Phase Breakdown ────────────────────────────────────────
    ws3 = wb.create_sheet("Phase Breakdown")
    ph_headers = ["Phase", "Name", "Agents", "Completed", "Failed",
                  "Tokens IN", "Tokens OUT", "Total Duration (ms)", "Total Cost (USD)", "Avg Cost/Agent"]
    for ci, h in enumerate(ph_headers, 1):
        c = ws3.cell(row=1, column=ci, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.alignment = hdr_align
        c.border = border

    phases: dict[str, dict] = {}
    for a_name, m in agents.items():
        p = m.get("phase", "?")
        if p not in phases:
            phases[p] = {"agents": 0, "completed": 0, "failed": 0,
                         "tokens_in": 0, "tokens_out": 0, "duration": 0, "cost": 0.0}
        phases[p]["agents"] += 1
        if m["status"] == "completed":
            phases[p]["completed"] += 1
        elif m["status"] == "failed":
            phases[p]["failed"] += 1
        phases[p]["tokens_in"] += m.get("tokens_in", 0)
        phases[p]["tokens_out"] += m.get("tokens_out", 0)
        phases[p]["duration"] += m.get("duration_ms", 0)
        phases[p]["cost"] += m.get("cost_usd", 0.0)

    sorted_phases = sorted(phases.keys(),
                           key=lambda p: PHASE_ORDER.index(p) if p in PHASE_ORDER else 99)
    r = 2
    for p in sorted_phases:
        d = phases[p]
        avg_cost = d["cost"] / max(d["agents"], 1)
        vals = [p, PHASE_NAMES.get(p, ""), d["agents"], d["completed"], d["failed"],
                d["tokens_in"], d["tokens_out"], d["duration"], round(d["cost"], 6), round(avg_cost, 6)]
        for ci, v in enumerate(vals, 1):
            c = ws3.cell(row=r, column=ci, value=v)
            c.border = border
            c.alignment = Alignment(horizontal="center", vertical="center")
            if ci in (9, 10):
                c.number_format = '$#,##0.000000'
        r += 1

    for ci in range(1, len(ph_headers) + 1):
        ws3.column_dimensions[get_column_letter(ci)].width = 22
    ws3.freeze_panes = "A2"

    # Add bar chart for cost per phase
    if len(sorted_phases) > 1:
        chart = BarChart()
        chart.type = "col"
        chart.title = "Cost per Phase (USD)"
        chart.y_axis.title = "Cost (USD)"
        chart.x_axis.title = "Phase"
        chart.style = 10
        data_ref = Reference(ws3, min_col=9, min_row=1, max_row=r - 1)
        cats_ref = Reference(ws3, min_col=1, min_row=2, max_row=r - 1)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        chart.shape = 4
        ws3.add_chart(chart, "A" + str(r + 2))

    # ── Sheet 4: Token Analytics ────────────────────────────────────────
    ws4 = wb.create_sheet("Token Analytics")
    ta_headers = ["Agent Name", "Phase", "Tokens IN", "Tokens OUT", "Tokens Total",
                  "IN %", "OUT %", "Cost (USD)", "Cost %", "Tokens/ms"]
    for ci, h in enumerate(ta_headers, 1):
        c = ws4.cell(row=1, column=ci, value=h)
        c.font = hdr_font
        c.fill = hdr_fill
        c.alignment = hdr_align
        c.border = border

    grand_total_tokens = sum(a.get("tokens_total", 0) for a in agents.values())
    grand_total_cost = sum(a.get("cost_usd", 0.0) for a in agents.values())

    r = 2
    for a_name, m in sorted(agents.items(), key=lambda x: x[1].get("tokens_total", 0), reverse=True):
        tok_in = m.get("tokens_in", 0)
        tok_out = m.get("tokens_out", 0)
        tok_total = m.get("tokens_total", 0)
        cost = m.get("cost_usd", 0.0)
        dur = m.get("duration_ms", 0)

        in_pct = (tok_in / grand_total_tokens * 100) if grand_total_tokens > 0 else 0
        out_pct = (tok_out / grand_total_tokens * 100) if grand_total_tokens > 0 else 0
        cost_pct = (cost / grand_total_cost * 100) if grand_total_cost > 0 else 0
        tok_per_ms = tok_total / dur if dur > 0 else 0

        vals = [a_name, m.get("phase", ""), tok_in, tok_out, tok_total,
                round(in_pct, 1), round(out_pct, 1), cost, round(cost_pct, 1), round(tok_per_ms, 2)]
        for ci, v in enumerate(vals, 1):
            c = ws4.cell(row=r, column=ci, value=v)
            c.border = border
            c.alignment = Alignment(horizontal="center", vertical="center")
            if ci == 8:
                c.number_format = '$#,##0.000000'
            if ci in (6, 7, 9):
                c.number_format = '0.0"%"'
        r += 1

    for ci in range(1, len(ta_headers) + 1):
        ws4.column_dimensions[get_column_letter(ci)].width = 22
    ws4.freeze_panes = "A2"

    # Save
    if output_dir:
        out = Path(output_dir) / f"agent-observability-{state.get('project_name', 'unknown')}-{run_id}.xlsx"
    else:
        out = PROJECT_ROOT / "docs" / "optimization" / f"agent-observability-{state.get('project_name', 'unknown')}-{run_id}.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out))
    print(f"✅ Excel report saved: {out}")
    return out


def _generate_json_snapshot(project_name: str, state: dict, output_dir: str | None = None) -> Path:
    """Export full state as JSON snapshot to docs/optimization/."""
    run_id = state.get("run_id", "unknown")
    if output_dir:
        out = Path(output_dir) / f"agent-observability-{project_name}-{run_id}.json"
    else:
        out = PROJECT_ROOT / "docs" / "optimization" / f"agent-observability-{project_name}-{run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ JSON snapshot saved: {out}")
    return out


def _generate_markdown_report(project_name: str, state: dict, output_dir: str | None = None) -> Path:
    """Generate a Markdown summary report."""
    run_id = state.get("run_id", "unknown")
    agents = state.get("agents", {})

    total_tok = sum(a.get("tokens_total", 0) for a in agents.values())
    total_cost = sum(a.get("cost_usd", 0.0) for a in agents.values())
    total_dur = sum(a.get("duration_ms", 0) for a in agents.values())
    completed = sum(1 for a in agents.values() if a["status"] == "completed")
    failed = sum(1 for a in agents.values() if a["status"] == "failed")

    lines = [
        f"# Pipeline Observability Report — {project_name}",
        "",
        f"**Run ID:** `{run_id}`  ",
        f"**Date:** {state.get('start_time', '—')}  ",
        f"**Model:** {state.get('model', '—')}  ",
        f"**Status:** {state.get('status', '—')}  ",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Agents | {len(agents)} |",
        f"| Completed | {completed} |",
        f"| Failed | {failed} |",
        f"| Total Tokens | {total_tok:,} |",
        f"| Total Cost | ${total_cost:,.4f} |",
        f"| Total Duration | {_format_duration(total_dur)} |",
        "",
        "## Agent Details",
        "",
        "| Agent | Phase | Version | Tokens | Cost (USD) | Duration | Status |",
        "|-------|-------|---------|--------|-----------|----------|--------|",
    ]

    def _sort_key(item: tuple[str, dict]) -> tuple[int, str]:
        phase = item[1].get("phase", "Z")
        idx = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else 99
        return (idx, item[1].get("start_time", ""))

    for a_name, m in sorted(agents.items(), key=_sort_key):
        lines.append(
            f"| {a_name} | {m.get('phase', '')} | {m.get('version', '')} "
            f"| {m.get('tokens_total', 0):,} | ${m.get('cost_usd', 0.0):.4f} "
            f"| {_format_duration(m.get('duration_ms', 0))} | {m.get('status', '')} |"
        )

    lines.append("")
    lines.append("## Phase Summary")
    lines.append("")
    lines.append("| Phase | Name | Agents | Cost (USD) | Duration |")
    lines.append("|-------|------|--------|-----------|----------|")

    phases: dict[str, dict] = {}
    for a_name, m in agents.items():
        p = m.get("phase", "?")
        if p not in phases:
            phases[p] = {"agents": 0, "cost": 0.0, "duration": 0}
        phases[p]["agents"] += 1
        phases[p]["cost"] += m.get("cost_usd", 0.0)
        phases[p]["duration"] += m.get("duration_ms", 0)

    for p in PHASE_ORDER:
        if p in phases:
            d = phases[p]
            lines.append(
                f"| {p} | {PHASE_NAMES.get(p, '')} | {d['agents']} "
                f"| ${d['cost']:.4f} | {_format_duration(d['duration'])} |"
            )

    lines.append("")
    lines.append(f"---\n*Generated by pipeline_observer.py — {_now_brz()}*")

    content = "\n".join(lines)

    if output_dir:
        out = Path(output_dir) / f"observability-report-{project_name}-{run_id}.md"
    else:
        out = PROJECT_ROOT / "docs" / "optimization" / f"observability-report-{project_name}-{run_id}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"✅ Markdown report saved: {out}")
    return out


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AVA Fabric Pipeline Observer — Deterministic Observability Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize a pipeline run
  %(prog)s -p Meu-ERP-001 init

  # Track an agent (atomic start+end)
  %(prog)s -p Meu-ERP-001 track --agent ava-asis-orchestrator --phase F1 --version 2.18.0 \\
      --status completed --tokens-in 50000 --tokens-out 30000 --duration-ms 374000

  # View dashboard
  %(prog)s -p Meu-ERP-001 dashboard

  # Finalize with auto-report
  %(prog)s -p Meu-ERP-001 finalize --auto-report

  # Generate reports
  %(prog)s -p Meu-ERP-001 report --format all

  # Import from JSON
  %(prog)s -p Meu-ERP-001 import-json --input docs/optimization/agent-observability-Meu-ERP-001.json

  # Compare runs
  %(prog)s compare --run-a path/to/run-a.json --run-b path/to/run-b.json
""",
    )
    parser.add_argument("--project", "-p", default=None, help="Project name")

    subs = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subs.add_parser("init", help="Initialize a new pipeline run")
    p_init.add_argument("--run-type", default="full-pipeline")
    p_init.add_argument("--model", default=DEFAULT_MODEL)

    # track
    p_track = subs.add_parser("track", help="Track agent execution (atomic start+end)")
    p_track.add_argument("--agent", required=True, help="Agent name")
    p_track.add_argument("--phase", default="", help="Pipeline phase (F1..F8)")
    p_track.add_argument("--version", default="", help="Agent version")
    p_track.add_argument("--status", default="completed", choices=["completed", "failed", "skipped", "running"])
    p_track.add_argument("--tokens-in", type=int, default=0)
    p_track.add_argument("--tokens-out", type=int, default=0)
    p_track.add_argument("--duration-ms", type=int, default=0)
    p_track.add_argument("--start-time", default=None, help="ISO 8601 start time")
    p_track.add_argument("--end-time", default=None, help="ISO 8601 end time")
    p_track.add_argument("--model", default=None)
    p_track.add_argument("--error-detail", default="", help="Error message if failed")

    # finalize
    p_fin = subs.add_parser("finalize", help="Finalize pipeline run")
    p_fin.add_argument("--auto-report", action="store_true", help="Auto-generate all reports")

    # dashboard
    subs.add_parser("dashboard", help="Show formatted dashboard")

    # status
    subs.add_parser("status", help="Show raw JSON status")

    # report
    p_report = subs.add_parser("report", help="Generate reports")
    p_report.add_argument("--format", default="all", choices=["all", "xlsx", "json", "md"])
    p_report.add_argument("--output-dir", default=None, help="Custom output directory")

    # import-json
    p_import = subs.add_parser("import-json", help="Import metrics from external JSON")
    p_import.add_argument("--input", required=True, help="Path to JSON file")

    # compare
    p_compare = subs.add_parser("compare", help="Compare two pipeline runs")
    p_compare.add_argument("--run-a", required=True, help="Path to run A state JSON")
    p_compare.add_argument("--run-b", required=True, help="Path to run B state JSON")

    args = parser.parse_args()

    # Validate --project is set for commands that need it
    needs_project = {"init", "track", "finalize", "dashboard", "status", "report", "import-json"}
    if args.command in needs_project and not args.project:
        parser.error(f"--project is required for '{args.command}' command")

    dispatch = {
        "init": cmd_init,
        "track": cmd_track,
        "finalize": cmd_finalize,
        "dashboard": cmd_dashboard,
        "status": cmd_status,
        "report": cmd_report,
        "import-json": cmd_import_json,
        "compare": cmd_compare,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    # Reports use unicode symbols (checkmarks, emoji) in print() output; on
    # Windows consoles the default encoding is often cp1252, which cannot
    # encode them and crashes after the report has already been saved.
    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
