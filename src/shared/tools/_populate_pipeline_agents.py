"""
Populate observability state with all pipeline agents for report generation.
Run: python src/shared/tools/_populate_pipeline_agents.py --project Meu-ERP-001
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from agent_observability import _load_state, _save_state
from generate_observability_report import AGENT_CATALOG


def populate(project_name: str):
    state = _load_state(project_name)
    if not state:
        print("ERROR: No active run. Initialize first.", file=sys.stderr)
        sys.exit(1)

    # Add all agents not yet tracked
    for entry in AGENT_CATALOG:
        agent = entry["agent"]
        if agent not in state["agents"]:
            # F1 agents are blocked because repo not found
            if entry["phase"] == "F1":
                status = "failed"
                reason = "blocked: legacy repository not found at C:\\_git\\Examples\\Meu-ERP"
            else:
                status = "skipped"
                reason = "skipped: F1 blocked — prerequisites not met"

            state["agents"][agent] = {
                "phase": entry["phase"],
                "version": entry["version"],
                "start_time": state.get("start_time", ""),
                "end_time": state.get("start_time", ""),
                "duration_ms": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "tokens_total": 0,
                "cost_usd": 0.0,
                "status": status,
                "model": state.get("model", "Claude Opus 4.6"),
                "run_type": state.get("run_type", "full-pipeline"),
                "error_detail": reason,
            }

    _save_state(project_name, state)
    print(f"✅ Populated {len(AGENT_CATALOG)} agents in pipeline state")
    print(f"   F1: {sum(1 for a in AGENT_CATALOG if a['phase'] == 'F1')} agents (blocked)")
    print(f"   F2-F6: {sum(1 for a in AGENT_CATALOG if a['phase'] != 'F1')} agents (skipped)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", "-p", required=True)
    args = parser.parse_args()
    populate(args.project)
