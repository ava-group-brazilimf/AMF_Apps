#!/usr/bin/env python3
"""Regenera pipeline-status.html usando a função corrigida de ava-pipeline-runner-cli.py.

Como a execução original não registrou executed/skipped/exec_metrics corretamente
(devido ao bug no loop principal), este script reconstrói o estado a partir dos
logs de fase existentes em projects/{project}/outputs/pipeline_runner/.
"""
import datetime
import re
import sys
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))

# Carrega a função _write_status_html do runner (nome com espaço requer import via spec)
import importlib.util

runner_path = WORKSPACE / "ava-pipeline-runner-cli.py"
spec = importlib.util.spec_from_file_location("pipeline_runner_19", runner_path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
write_status_html = runner._write_status_html
PIPELINE = runner.PIPELINE

PROJECT = "nopcommerce-04-cli-ava"
LOG_DIR = WORKSPACE / "projects" / PROJECT / "outputs" / "pipeline_runner"


def parse_phase_log(log_path: Path) -> dict:
    """Extrai métricas básicas do cabeçalho markdown do log da fase."""
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    metrics = {
        "agent": "",
        "elapsed_s": 0.0,
        "artifacts": 0,
        "inp_tokens": 0,
        "val_ok": True,
        "out_max": 0,
        "resp_tokens": 0,
    }

    # Agente
    m = re.search(r"\*\*Agente:\*\*\s*@?(\S+)", text)
    if m:
        metrics["agent"] = m.group(1)

    # Artefatos gerados
    m = re.search(r"\*\*Artefatos gerados:\*\*\s*(\d+)", text)
    if m:
        metrics["artifacts"] = int(m.group(1))

    # Linha de tempo: **Tempo:** 123.4s
    m = re.search(r"\*\*Tempo:\*\*\s*([\d.]+)s", text)
    if m:
        metrics["elapsed_s"] = float(m.group(1))

    # Input tokens aproximado do prompt
    inp = len(text) // 4
    metrics["inp_tokens"] = inp

    return metrics


def main():
    # 1) Reconstruir active_steps a partir do PIPELINE + expansão F3S real dos logs
    active_steps = list(PIPELINE)

    # Fases presentes nos logs (excluindo execution-report, headroom, S* e F3S subfases)
    log_phases = {}
    for p in LOG_DIR.glob("*.md"):
        name = p.name
        if name.startswith("execution-report_") or name.startswith("headroom-optimization_"):
            continue
        # formato: FASE_AGENTE_YYYYMMDD_HHMMSS.md ou F3S-SUBFASE_AGENTE_...
        m = re.match(r"(F3S-[^_]+|F[0-6]|S[1-4]|FC|FP)_", name)
        if m:
            ph = m.group(1)
            # manter apenas o log mais recente por fase
            if ph not in log_phases or p.stat().st_mtime > log_phases[ph].stat().st_mtime:
                log_phases[ph] = p

    # Expande o PIPELINE para incluir fases F3S reais encontradas nos logs
    f3s_steps = []
    for ph, log in sorted(log_phases.items()):
        if ph.startswith("F3S-"):
            # Agent a partir do nome do arquivo
            parts = log.stem.split("_")
            agent = parts[1] if len(parts) > 1 else "speckit-orchestrator"
            f3s_steps.append({"phase": ph, "agent": agent, "label": ph})

    if f3s_steps:
        # Substitui o step F3S genérico pelos passos reais
        active_steps = [s for s in active_steps if s["phase"] != "F3S"]
        idx = next((i for i, s in enumerate(active_steps) if s["phase"] == "F3"), len(active_steps) - 1) + 1
        active_steps[idx:idx] = f3s_steps

    # 2) Reconstruir executed/skipped/aborted/exec_metrics
    executed, skipped, aborted = [], [], []
    exec_metrics = {}

    # Fase abortada conforme relatório
    aborted.append("F3S:tool:speckit-task-compile")
    exec_metrics["F3S:tool:speckit-task-compile"] = {
        "phase": "F3S:tool:speckit-task-compile",
        "agent": "speckit-task-compile",
        "elapsed_s": 0,
        "artifacts": 0,
        "inp_tokens": 0,
        "val_ok": False,
    }

    # Demais fases com logs são consideradas executadas
    for ph, log in log_phases.items():
        if ph in aborted:
            continue
        metrics = parse_phase_log(log)
        metrics["phase"] = ph
        metrics.setdefault("agent", active_steps[[s["phase"] for s in active_steps].index(ph)]["agent"] if ph in [s["phase"] for s in active_steps] else "")
        executed.append(ph)
        exec_metrics[ph] = metrics

    # 3) Tempo total estimado a partir do primeiro e último log
    mtimes = [p.stat().st_mtime for p in LOG_DIR.glob("*.md")]
    start_ts = min(mtimes) if mtimes else time.time()

    # 4) Gerar HTML
    html_path = write_status_html(
        PROJECT,
        active_steps,
        executed,
        skipped,
        aborted,
        start_ts=start_ts,
        exec_metrics=exec_metrics,
        done=True,
    )
    print(f"HTML regenerado: {html_path}")
    print(f"  - Fases: {len(active_steps)}")
    print(f"  - Executadas: {len(executed)}")
    print(f"  - Puladas: {len(skipped)}")
    print(f"  - Abortadas: {len(aborted)}")


if __name__ == "__main__":
    main()
