"""
generate_observability_report.py — Generates the agent observability Excel report.

Can either:
  1. Export existing run data from agent_observability.py state files
  2. Generate a baseline report with all pipeline agents pre-populated

Usage:
  # Export from existing run
  python src/shared/tools/generate_observability_report.py --project Meu-ERP-001 --mode export

  # Generate baseline catalog (for planning / empty pipeline)
  python src/shared/tools/generate_observability_report.py --project Meu-ERP-001 --mode baseline
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

# Catálogo de fallback — usado apenas se a varredura de agent_registry falhar.
# A fonte de verdade é o frontmatter dos agentes; ver AGENT_CATALOG abaixo.
_STATIC_AGENT_CATALOG = [
    # F1 — AS-IS Diagnostic
    {"agent": "ava-asis-orchestrator",        "phase": "F1", "version": "2.22.0"},
    {"agent": "ava-asis-solution-delphi",     "phase": "F1", "version": "2.8.0"},
    {"agent": "ava-asis-db-analyzer",         "phase": "F1", "version": "1.6.0"},
    {"agent": "ava-asis-events-pubsub",       "phase": "F1", "version": "1.2.0"},
    {"agent": "ava-asis-documentation",       "phase": "F1", "version": "3.1.0"},
    {"agent": "ava-asis-inventory",           "phase": "F1", "version": "1.6.0"},
    {"agent": "ava-asis-security-orchestrator","phase": "F1", "version": "1.0.0"},
    {"agent": "ava-asis-gaps-risks",          "phase": "F1", "version": "1.4.0"},
    {"agent": "ava-asis-bridge-fastqa",       "phase": "F1", "version": "1.0.0"},
    {"agent": "ava-summary (F1)",             "phase": "F1", "version": "1.0.0"},

    # F2 — TO-BE Architecture
    {"agent": "ava-tobe-orchestrator",        "phase": "F2", "version": "2.1.0"},
    {"agent": "ava-tobe-adr",                 "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-architecture-design", "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-database-design",     "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-security-design",     "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-architecture-technical","phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-measure-size",        "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-migration-plan",      "phase": "F2", "version": "1.2.1"},
    {"agent": "ava-tobe-risk-mitigation",     "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-tobe-user-journeys",       "phase": "F2", "version": "1.0.0"},
    {"agent": "ava-summary (F2)",             "phase": "F2", "version": "1.0.0"},

    # F3 — Prototype
    {"agent": "ava-prototype",                "phase": "F3", "version": "1.0.0"},
    {"agent": "ava-summary (F3)",             "phase": "F3", "version": "1.0.0"},

    # F4 — Stack / Codegen
    {"agent": "ava-stack-orchestrator",       "phase": "F4", "version": "1.7.1"},
    {"agent": "ava-stack-docs-researcher",    "phase": "F4", "version": "1.0.0"},
    {"agent": "ava-stack-dotnet-backend",     "phase": "F4", "version": "1.0.0"},
    {"agent": "ava-stack-angular-frontend",   "phase": "F4", "version": "1.0.0"},
    {"agent": "ava-stack-build-validator",    "phase": "F4", "version": "2.3.0"},
    {"agent": "ava-summary (F4)",             "phase": "F4", "version": "1.0.0"},

    # F5 — QA
    {"agent": "ava-qa-orchestrator",          "phase": "F5", "version": "1.2.2"},
    {"agent": "ava-qa-behavior-mapping",      "phase": "F5", "version": "1.0.0"},
    {"agent": "ava-qa-gaps-requirements",     "phase": "F5", "version": "1.0.0"},
    {"agent": "ava-qa-scenario-generator",    "phase": "F5", "version": "2.1.0"},
    {"agent": "ava-qa-test-case-generator",   "phase": "F5", "version": "1.0.0"},
    {"agent": "ava-qa-script-generator",      "phase": "F5", "version": "1.2.0"},
    {"agent": "ava-qa-exploratory",           "phase": "F5", "version": "2.0.0"},
    {"agent": "ava-qa-evidence-capture",      "phase": "F5", "version": "2.1.0"},
    {"agent": "ava-qa-defect-identifier",     "phase": "F5", "version": "1.0.0"},
    {"agent": "ava-summary (F5)",             "phase": "F5", "version": "1.0.0"},

    # F6 — DevOps
    {"agent": "ava-devops-iac",               "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-ci",                "phase": "F6", "version": "1.2.0"},
    {"agent": "ava-devops-cd",                "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-containerize",      "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-iac-azure",         "phase": "F6", "version": "2.6.0"},
    {"agent": "ava-devops-cost-estimate",     "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-compare-version",   "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-devops-package-approval",  "phase": "F6", "version": "1.0.0"},
    {"agent": "ava-summary (F6)",             "phase": "F6", "version": "1.0.0"},

    # F7 — Deliverables
    {"agent": "ava-deliverable-tech-docs",          "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-migration-plan",     "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-security-compliance","phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-test-evidence",      "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-code-templates",     "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-client-demo",        "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-deliverable-packager",           "phase": "F7", "version": "1.0.0"},
    {"agent": "ava-summary (F7 — FINAL)",           "phase": "F7", "version": "1.0.0"},
]


def _load_agent_catalog():
    """Catálogo derivado do frontmatter dos agentes em disco (specs/032).

    Antes desta mudança o literal acima divergia do de ``pipeline_observer.py``
    (`ava-tobe-orchestrator` 2.1.0 × 2.3.0) e de 52 agentes reais.
    """
    try:
        if str(SCRIPT_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPT_DIR))
        import agent_registry
        return agent_registry.catalog_or(_STATIC_AGENT_CATALOG)
    except Exception:
        return _STATIC_AGENT_CATALOG


#: Catálogo efetivo — derivado do disco, com fallback estático.
AGENT_CATALOG = _load_agent_catalog()


def generate_baseline(project_name: str, output_path: str | None = None):
    """Generate a baseline Excel with all pipeline agents (status=pending)."""
    from agent_observability import _save_state, _export_xlsx, _get_data_dir
    import uuid

    run_id = str(uuid.uuid4())[:8].upper()
    state = {
        "run_id": run_id,
        "project_name": project_name,
        "run_type": "full-pipeline",
        "model": "Claude Opus 4.6",
        "start_time": "",
        "end_time": "",
        "status": "pending",
        "agents": {},
    }

    for entry in AGENT_CATALOG:
        state["agents"][entry["agent"]] = {
            "phase": entry["phase"],
            "version": entry["version"],
            "start_time": "",
            "end_time": "",
            "duration_ms": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_total": 0,
            "cost_usd": 0.0,
            "status": "pending",
            "model": "Claude Opus 4.6",
            "run_type": "full-pipeline",
        }

    _save_state(project_name, state)

    if not output_path:
        output_path = str(
            PROJECT_ROOT / "docs" / "optimization"
            / f"agent-observability-{project_name}-{run_id}.xlsx"
        )

    _export_xlsx(project_name, state, output_path)
    return output_path


def export_existing(project_name: str, output_path: str | None = None):
    """Export existing run data to Excel."""
    from agent_observability import _load_state, _export_xlsx

    state = _load_state(project_name)
    if not state:
        print(f"ERROR: No run data found for project '{project_name}'", file=sys.stderr)
        sys.exit(1)

    _export_xlsx(project_name, state, output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate Agent Observability Report")
    parser.add_argument("--project", "-p", required=True, help="Project name")
    parser.add_argument("--mode", choices=["export", "baseline"], default="export")
    parser.add_argument("--output", "-o", default=None, help="Custom output path")
    args = parser.parse_args()

    if args.mode == "baseline":
        path = generate_baseline(args.project, args.output)
        print(f"✅ Baseline report generated: {path}")
    else:
        export_existing(args.project, args.output)


if __name__ == "__main__":
    # Add parent dir to path for importing agent_observability
    sys.path.insert(0, str(SCRIPT_DIR))
    main()
