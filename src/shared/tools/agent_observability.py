"""
agent_observability.py — Deterministic observability tool for AVA Fabric agent pipeline.

Tracks execution metrics per agent run: timestamps, duration, token estimates,
cost, status, model, and run type. Persists as JSONL for durability and exports
to Excel (.xlsx) for reporting.

Usage:
  # Initialize a pipeline run
  python src/shared/tools/agent_observability.py init --project Meu-ERP-001 --run-type full-pipeline

  # Record agent start
  python src/shared/tools/agent_observability.py start --agent ava-asis-orchestrator --phase F1 --version 1.0.0

  # Record agent end (success)
  python src/shared/tools/agent_observability.py end --agent ava-asis-orchestrator --status completed \
      --tokens-in 12000 --tokens-out 8500 --model "Claude Sonnet 4.6"

  # Record agent end (failure)
  python src/shared/tools/agent_observability.py end --agent ava-asis-orchestrator --status failed

  # Export to Excel
  python src/shared/tools/agent_observability.py export --format xlsx

  # Show current status (JSON)
  python src/shared/tools/agent_observability.py status
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# BRZ timezone (UTC-3)
BRZ = timezone(timedelta(hours=-3))

# Default model for this pipeline
DEFAULT_MODEL = "Claude Sonnet 4.6"

# Per-token pricing by model family (USD), matched case-insensitively by
# substring against whatever --model string is passed. Kept in sync with
# pipeline_observer.py's MODEL_PRICING table.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude opus":   (15.0 / 1_000_000, 75.0 / 1_000_000),
    "claude sonnet": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "claude haiku":  (1.0 / 1_000_000, 5.0 / 1_000_000),
    "gpt-4":         (2.5 / 1_000_000, 10.0 / 1_000_000),
    "gpt-3.5":       (0.5 / 1_000_000, 1.5 / 1_000_000),
    "gemini":        (1.25 / 1_000_000, 5.0 / 1_000_000),
}
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

# Resolve project root (4 levels up from this file: tools/ → shared/ → src/ → root)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent


def _get_data_dir(project_name: str) -> Path:
    """Return the observability data directory for a project."""
    d = PROJECT_ROOT / "projects" / project_name / "outputs" / "observability"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_state_file(project_name: str) -> Path:
    return _get_data_dir(project_name) / "pipeline-run-state.json"


def _get_events_file(project_name: str) -> Path:
    return _get_data_dir(project_name) / "agent-events.jsonl"


def _now_brz() -> str:
    return datetime.now(BRZ).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def _now_brz_dt() -> datetime:
    return datetime.now(BRZ)


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


def _load_events(project_name: str) -> list[dict]:
    f = _get_events_file(project_name)
    if not f.exists():
        return []
    events = []
    for line in f.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            events.append(json.loads(line))
    return events


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_init(args):
    """Initialize a new pipeline run."""
    project_name = args.project
    run_id = str(uuid.uuid4())[:8].upper()
    run_type = args.run_type or "full-pipeline"
    model = args.model or DEFAULT_MODEL

    state = {
        "run_id": run_id,
        "project_name": project_name,
        "run_type": run_type,
        "model": model,
        "start_time": _now_brz(),
        "end_time": None,
        "status": "running",
        "agents": {},
    }
    _save_state(project_name, state)

    # Clear previous events file for a fresh run
    ef = _get_events_file(project_name)
    if ef.exists():
        ef.unlink()

    print(json.dumps({"run_id": run_id, "project": project_name, "status": "initialized"}, indent=2))
    return run_id


def cmd_start(args):
    """Record agent start event."""
    project_name = args.project
    state = _load_state(project_name)
    if not state:
        print("ERROR: No active run. Call 'init' first.", file=sys.stderr)
        sys.exit(1)

    agent = args.agent
    phase = args.phase or ""
    version = args.version or ""
    now = _now_brz()

    state["agents"][agent] = {
        "phase": phase,
        "version": version,
        "start_time": now,
        "end_time": None,
        "duration_ms": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_total": 0,
        "cost_usd": 0.0,
        "status": "running",
        "model": state.get("model", ""),
        "run_type": state.get("run_type", ""),
    }
    _save_state(project_name, state)

    event = {
        "type": "agent_start",
        "run_id": state["run_id"],
        "agent": agent,
        "phase": phase,
        "version": version,
        "timestamp": now,
    }
    _append_event(project_name, event)

    print(json.dumps({"agent": agent, "phase": phase, "status": "started", "time": now}))


def cmd_end(args):
    """Record agent end event."""
    project_name = args.project
    state = _load_state(project_name)
    if not state:
        print("ERROR: No active run.", file=sys.stderr)
        sys.exit(1)

    agent = args.agent
    if agent not in state["agents"]:
        print(f"ERROR: Agent '{agent}' not started.", file=sys.stderr)
        sys.exit(1)

    status = args.status or "completed"
    tokens_in = args.tokens_in or 0
    tokens_out = args.tokens_out or 0
    model = args.model or state["agents"][agent].get("model", state.get("model", DEFAULT_MODEL))
    now = _now_brz()

    # Calculate duration
    start_str = state["agents"][agent]["start_time"]
    try:
        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(now)
        duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
    except (ValueError, TypeError):
        duration_ms = 0

    # Calculate cost (model-aware)
    cost_per_token_in, cost_per_token_out = _get_pricing_for_model(model)
    cost_usd = round(tokens_in * cost_per_token_in + tokens_out * cost_per_token_out, 6)

    state["agents"][agent].update({
        "end_time": now,
        "duration_ms": duration_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "cost_usd": cost_usd,
        "status": status,
        "model": model,
    })
    _save_state(project_name, state)

    event = {
        "type": "agent_end",
        "run_id": state["run_id"],
        "agent": agent,
        "status": status,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "duration_ms": duration_ms,
        "cost_usd": cost_usd,
        "model": model,
        "timestamp": now,
    }
    _append_event(project_name, event)

    print(json.dumps({
        "agent": agent,
        "status": status,
        "duration_ms": duration_ms,
        "tokens_total": tokens_in + tokens_out,
        "cost_usd": cost_usd,
    }))


def cmd_finalize(args):
    """Finalize the pipeline run."""
    project_name = args.project
    state = _load_state(project_name)
    if not state:
        print("ERROR: No active run.", file=sys.stderr)
        sys.exit(1)

    state["end_time"] = _now_brz()

    # Determine overall status
    statuses = [a["status"] for a in state["agents"].values()]
    if all(s == "completed" for s in statuses):
        state["status"] = "complete"
    elif any(s == "failed" for s in statuses):
        state["status"] = "partial"
    else:
        state["status"] = "complete"

    _save_state(project_name, state)
    print(json.dumps({"run_id": state["run_id"], "status": state["status"], "end_time": state["end_time"]}))


def cmd_status(args):
    """Print current run status."""
    project_name = args.project
    state = _load_state(project_name)
    if not state:
        print("{}")
        return
    print(json.dumps(state, indent=2, ensure_ascii=False))


def cmd_export(args):
    """Export metrics to Excel (.xlsx)."""
    project_name = args.project
    state = _load_state(project_name)
    if not state:
        print("ERROR: No run data to export.", file=sys.stderr)
        sys.exit(1)

    fmt = args.format or "xlsx"
    if fmt == "xlsx":
        _export_xlsx(project_name, state, args.output)
    elif fmt == "json":
        _export_json(project_name, state, args.output)
    else:
        print(f"ERROR: Unsupported format: {fmt}", file=sys.stderr)
        sys.exit(1)


def _export_xlsx(project_name: str, state: dict, output_path: str | None):
    """Generate Excel report with agent metrics."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("ERROR: openpyxl not installed. Run: pip install openpyxl", file=sys.stderr)
        sys.exit(1)

    wb = Workbook()

    # ── Sheet 1: Agent Metrics ──
    ws = wb.active
    ws.title = "Agent Metrics"

    # Header style
    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="FF6600", end_color="FF6600", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    headers = [
        "Run ID", "Data/Hora", "Agent Name", "Phase", "Versão",
        "Tokens IN", "Tokens OUT", "Tokens Total", "Duration (ms)",
        "Cost (USD)", "Status", "Model", "Run Type",
    ]

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # Data rows
    row_idx = 2
    status_colors = {
        "completed": "C6EFCE",
        "failed": "FFC7CE",
        "running": "FFEB9C",
        "skipped": "D9E1F2",
    }

    run_id = state.get("run_id", "N/A")
    run_type = state.get("run_type", "full-pipeline")

    for agent_name, metrics in state.get("agents", {}).items():
        row_data = [
            run_id,
            metrics.get("start_time", ""),
            agent_name,
            metrics.get("phase", ""),
            metrics.get("version", ""),
            metrics.get("tokens_in", 0),
            metrics.get("tokens_out", 0),
            metrics.get("tokens_total", 0),
            metrics.get("duration_ms", 0),
            metrics.get("cost_usd", 0.0),
            metrics.get("status", ""),
            metrics.get("model", ""),
            run_type,
        ]

        status_val = metrics.get("status", "")
        fill_color = status_colors.get(status_val, "FFFFFF")
        data_fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")

        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if col_idx == 11:  # Status column
                cell.fill = data_fill
            if col_idx == 10:  # Cost column
                cell.number_format = '$#,##0.000000'

        row_idx += 1

    # Totals row
    total_row = row_idx
    ws.cell(row=total_row, column=1, value="TOTAL").font = Font(bold=True)
    for col in [6, 7, 8, 9, 10]:
        col_letter = get_column_letter(col)
        formula = f"=SUM({col_letter}2:{col_letter}{total_row - 1})"
        cell = ws.cell(row=total_row, column=col, value=formula)
        cell.font = Font(bold=True)
        cell.border = thin_border
        if col == 10:
            cell.number_format = '$#,##0.000000'

    # Auto-width columns
    for col_idx in range(1, len(headers) + 1):
        max_len = len(str(headers[col_idx - 1]))
        for row in range(2, row_idx + 1):
            val = ws.cell(row=row, column=col_idx).value
            if val:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 40)

    # Freeze header row
    ws.freeze_panes = "A2"

    # ── Sheet 2: Pipeline Summary ──
    ws2 = wb.create_sheet("Pipeline Summary")
    summary_data = [
        ("Run ID", run_id),
        ("Project", project_name),
        ("Run Type", run_type),
        ("Model", state.get("model", "")),
        ("Start Time", state.get("start_time", "")),
        ("End Time", state.get("end_time", "")),
        ("Status", state.get("status", "")),
        ("Total Agents", len(state.get("agents", {}))),
        ("Completed", sum(1 for a in state.get("agents", {}).values() if a["status"] == "completed")),
        ("Failed", sum(1 for a in state.get("agents", {}).values() if a["status"] == "failed")),
        ("Skipped", sum(1 for a in state.get("agents", {}).values() if a["status"] == "skipped")),
    ]

    for r, (label, value) in enumerate(summary_data, 1):
        ws2.cell(row=r, column=1, value=label).font = Font(bold=True)
        ws2.cell(row=r, column=2, value=value)
    ws2.column_dimensions["A"].width = 20
    ws2.column_dimensions["B"].width = 40

    # ── Sheet 3: Phase Breakdown ──
    ws3 = wb.create_sheet("Phase Breakdown")
    phase_headers = ["Phase", "Agents", "Completed", "Failed", "Total Duration (ms)", "Total Cost (USD)"]
    for col_idx, h in enumerate(phase_headers, 1):
        cell = ws3.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    phases = {}
    for agent_name, m in state.get("agents", {}).items():
        phase = m.get("phase", "?")
        if phase not in phases:
            phases[phase] = {"agents": 0, "completed": 0, "failed": 0, "duration": 0, "cost": 0.0}
        phases[phase]["agents"] += 1
        if m["status"] == "completed":
            phases[phase]["completed"] += 1
        elif m["status"] == "failed":
            phases[phase]["failed"] += 1
        phases[phase]["duration"] += m.get("duration_ms", 0)
        phases[phase]["cost"] += m.get("cost_usd", 0.0)

    phase_order = ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]
    sorted_phases = sorted(phases.keys(), key=lambda p: phase_order.index(p) if p in phase_order else 99)

    for r, phase in enumerate(sorted_phases, 2):
        d = phases[phase]
        ws3.cell(row=r, column=1, value=phase).border = thin_border
        ws3.cell(row=r, column=2, value=d["agents"]).border = thin_border
        ws3.cell(row=r, column=3, value=d["completed"]).border = thin_border
        ws3.cell(row=r, column=4, value=d["failed"]).border = thin_border
        ws3.cell(row=r, column=5, value=d["duration"]).border = thin_border
        cell = ws3.cell(row=r, column=6, value=round(d["cost"], 6))
        cell.border = thin_border
        cell.number_format = '$#,##0.000000'

    for col_idx in range(1, 7):
        ws3.column_dimensions[get_column_letter(col_idx)].width = 22
    ws3.freeze_panes = "A2"

    # Save
    if output_path:
        out = Path(output_path)
    else:
        out = PROJECT_ROOT / "docs" / "optimization" / f"agent-observability-{project_name}-{run_id}.xlsx"

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out))
    print(f"✅ Excel report saved: {out}")
    return str(out)


def _export_json(project_name: str, state: dict, output_path: str | None):
    """Export metrics as JSON."""
    if output_path:
        out = Path(output_path)
    else:
        out = _get_data_dir(project_name) / f"metrics-{state.get('run_id', 'unknown')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ JSON report saved: {out}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AVA Fabric Agent Observability Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", "-p", required=True, help="Project name (e.g. Meu-ERP-001)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize a pipeline run")
    p_init.add_argument("--run-type", default="full-pipeline")
    p_init.add_argument("--model", default=DEFAULT_MODEL)

    # start
    p_start = subparsers.add_parser("start", help="Record agent start")
    p_start.add_argument("--agent", required=True)
    p_start.add_argument("--phase", default="")
    p_start.add_argument("--version", default="")

    # end
    p_end = subparsers.add_parser("end", help="Record agent end")
    p_end.add_argument("--agent", required=True)
    p_end.add_argument("--status", default="completed", choices=["completed", "failed", "skipped"])
    p_end.add_argument("--tokens-in", type=int, default=0)
    p_end.add_argument("--tokens-out", type=int, default=0)
    p_end.add_argument("--model", default=None)

    # finalize
    subparsers.add_parser("finalize", help="Finalize the pipeline run")

    # status
    subparsers.add_parser("status", help="Show current run status")

    # export
    p_export = subparsers.add_parser("export", help="Export metrics report")
    p_export.add_argument("--format", default="xlsx", choices=["xlsx", "json"])
    p_export.add_argument("--output", default=None, help="Custom output file path")

    args = parser.parse_args()

    dispatch = {
        "init": cmd_init,
        "start": cmd_start,
        "end": cmd_end,
        "finalize": cmd_finalize,
        "status": cmd_status,
        "export": cmd_export,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    # Reports use unicode symbols (checkmarks) in print() output; on Windows
    # consoles the default encoding is often cp1252, which cannot encode them
    # and crashes after the report has already been saved.
    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
