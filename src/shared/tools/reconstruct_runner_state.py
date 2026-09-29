#!/usr/bin/env python3
"""Reconstruct runner-state.json from existing execution artifacts.

This is a recovery/debug tool. It scans the outputs of a project and rebuilds a
valid ``runner-state.json`` that ``ava-pipeline-runner-cli.py`` can resume from.

It is especially useful for F3S because that phase is dynamically expanded from
``src/shared/data/pipeline-dag/F3S.yaml`` + ``wave-spec-manifest.json``.  If the
runner was killed before it could persist state, this script lets you retomar
from the last successfully executed step.

Usage:
    python src/shared/tools/reconstruct_runner_state.py --project <name> [--dry-run]

The script does NOT run any agent. It only writes
``projects/{project}/outputs/pipeline_runner/runner-state.json``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

# Regex for per-step execution reports produced by the runner.
# Examples:
#   F0_ast-extractor_20260811_154133.md
#   F3S-constitution_ava-speckit-constitution_20260818_110924.md
#   F3S-specification-002-w1-core-read_ava-speckit-specification_20260818_111742.md
#   F3S_ava-speckit-orchestrator_20260813_110522.md
REPORT_RE = re.compile(
    r"^(?P<phase>F3S(?:-[a-z]+)?(?:-[a-z0-9-]+)?|[A-Za-z0-9]+)"
    r"_(?P<agent>[a-z0-9-]+)"
    r"_(?P<ts>\d{8}_\d{6})\.md$"
)

# Maps legacy numeric feature suffixes (from older runner versions) to the
# current manifest feature names. Only needed when reconstructing old reports.
LEGACY_FEATURE_MAP: dict[str, str | None] = {
    "001-business-rules": "001-w0-foundation",
    "002-api": "002-w1-core-read",
    "003-api-map": "003-w2-core-write",
    "004-backlog": "004-w3-transactional-core",
    "005-waves": "005-w4-cutover",
    "006-test-cases": None,
    "007-prototype": None,
}


def _fail(message: str) -> None:
    print(f"[reconstruct_runner_state] ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _project_dir(project: str) -> Path:
    return REPO_ROOT / "projects" / project


def _runner_state_path(project: str) -> Path:
    return _project_dir(project) / "outputs" / "pipeline_runner" / "runner-state.json"


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        _fail("pyyaml não está instalado")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise _fail(f"arquivo ausente: {path}") from exc
    except Exception as exc:  # noqa: BLE001
        raise _fail(f"falha ao ler {path}: {exc}") from exc
    return data if isinstance(data, dict) else {}


def _read_project_config(project: str) -> dict[str, Any]:
    path = _project_dir(project) / "context" / "project-config.yaml"
    return _load_yaml(path)


def _read_manifest(project: str) -> dict[str, Any] | None:
    path = _project_dir(project) / "outputs" / "tobe" / "speckit" / "wave-spec-manifest.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _expand_f3s_phases(project: str) -> list[dict[str, Any]]:
    """Return the exact F3S step list that ava-pipeline-runner-cli.py would expand.

    This reuses ``pipeline_plan.dag_steps`` so the phase keys are identical to
    the runner's ``_phase_identity(step)`` values.
    """
    try:
        sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
        import pipeline_plan  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        _fail(f"não foi possível importar pipeline_plan: {exc}")

    steps = pipeline_plan.dag_steps("F3S", REPO_ROOT, project=project)
    if not steps:
        _fail(
            "F3S não pôde ser expandido. Verifique se "
            "src/shared/data/pipeline-dag/F3S.yaml e o wave-spec-manifest.json existem."
        )
    return steps


def _normalize_report_phase(
    raw_phase: str, agent: str, manifest_features: list[str]
) -> str | None:
    """Convert a report filename phase to the current DAG phase key.

    Returns ``None`` when the report cannot be mapped to a current step.
    """
    # Already the orchestrator placeholder — not a real expanded step.
    if raw_phase == "F3S" and agent == "ava-speckit-orchestrator":
        return None

    # Modern format: F3S-<role>-<feature>
    if raw_phase.startswith("F3S-"):
        # Remove the F3S- prefix and split into role + feature.
        rest = raw_phase[4:]
        for role in ("specification", "planning", "tasks", "constitution"):
            if rest.startswith(f"{role}-"):
                feature = rest[len(role) + 1 :]
                mapped = LEGACY_FEATURE_MAP.get(feature, feature)
                if mapped is None:
                    return None
                return f"F3S:{role}:{mapped}"
        # constitution has no feature suffix.
        if rest == "constitution":
            return "F3S:constitution"
        # Unknown role — cannot map.
        return None

    # Old format: F3S-001-business-rules with agent indicating role.
    if raw_phase.startswith("F3S-"):
        feature = raw_phase[4:]
        mapped = LEGACY_FEATURE_MAP.get(feature, feature)
        if mapped is None:
            return None
        if agent == "ava-speckit-specification":
            return f"F3S:specification:{mapped}"
        if agent == "ava-speckit-prototype-spec":
            return None
        if agent == "ava-speckit-planning":
            return f"F3S:planning:{mapped}"
        if agent == "ava-speckit-tasks":
            return f"F3S:tasks:{mapped}"
        return None

    # Non-F3S phases are returned as-is.
    return raw_phase


def _scan_report_files(project: str, manifest_features: list[str]) -> dict[str, str]:
    """Map phase key -> latest timestamp from execution report files."""
    runner_dir = _project_dir(project) / "outputs" / "pipeline_runner"
    if not runner_dir.is_dir():
        return {}

    latest: dict[str, str] = {}
    for path in runner_dir.iterdir():
        if not path.is_file() or path.suffix != ".md":
            continue
        m = REPORT_RE.match(path.name)
        if not m:
            continue
        raw_phase = m.group("phase")
        agent = m.group("agent")
        ts = m.group("ts")
        phase_key = _normalize_report_phase(raw_phase, agent, manifest_features)
        if phase_key is None:
            continue
        # Ignore reports whose feature is not part of the current DAG expansion.
        # The DAG uses codegen_only filters (e.g. planning skips foundation/cutover),
        # so we also drop reports for features that are absent from active_phases.
        if phase_key.startswith("F3S:") and ":" in phase_key[4:]:
            parts = phase_key.split(":", 2)
            if len(parts) == 3:
                feature = parts[2]
                if feature and manifest_features and feature not in manifest_features:
                    continue
        if phase_key not in latest or latest[phase_key] < ts:
            latest[phase_key] = ts
    return latest


def _infer_tool_steps_from_artifacts(
    project: str, executed: set[str]
) -> set[str]:
    """Add deterministic F3S tool steps when their output artifacts exist.

    Tools do not produce execution reports (or produce no useful report), so we
    infer success from the artifacts they are known to generate.
    """
    speckit = _project_dir(project) / "outputs" / "tobe" / "speckit"
    inferred: set[str] = set()

    # speckit-wave-manifest -> wave-spec-manifest.json
    if (speckit / "wave-spec-manifest.json").is_file():
        inferred.add("F3S:tool:speckit-wave-manifest")

    # f4s-scaffold-inject -> grupo/task de scaffold DENTRO da feature W0.
    #
    # Antes esta checagem era `glob("000-scaffold-*")`, sobre diretórios que o
    # injetor nunca criou: ele enriquece a feature W0 (`001-w0-*`) em vez de
    # gerar uma feature por stack. A condição era sempre falsa, então o passo
    # nunca constava como executado e a retomada o refazia todo run. Hoje a
    # detecção olha o artefato que o injetor realmente produz.
    if any(
        "T-SCAFFOLD-" in fragmento.read_text(encoding="utf-8", errors="replace")
        for fragmento in (speckit / "specs").glob("*/task-fragment.json")
    ):
        inferred.add("F3S:tool:f4s-scaffold-inject")

    # speckit-task-compile -> traceability.json (produced by compiler) AND
    # consolidated tasks.md in each codegen feature directory.
    if (speckit / "traceability.json").is_file() and any(
        (speckit / "specs" / feature / "tasks.md").is_file()
        for feature in _codegen_features(project)
    ):
        inferred.add("F3S:tool:speckit-task-compile")

    # speckit-ledger-init -> task ledger files under readiness-gate/
    if any((_project_dir(project) / "outputs" / "readiness-gate").glob("*.json")):
        inferred.add("F3S:tool:speckit-ledger-init")

    # speckit-dependency-checks -> no stable output; do not infer.

    # speckit-entry-gate -> success is implied if later F3S phases ran.
    # We mark it executed only if at least one other F3S step is executed.
    if any(p.startswith("F3S:") for p in executed if p != "F3S:tool:speckit-entry-gate"):
        inferred.add("F3S:tool:speckit-entry-gate")

    return inferred


def _codegen_features(project: str) -> list[str]:
    """Return feature ids flagged as codegen=True from the wave manifest."""
    manifest = _read_manifest(project)
    if not manifest:
        return []
    return [str(f["feature"]) for f in manifest.get("features", []) if f.get("codegen")]


def _build_active_phases(pipeline: list[dict[str, Any]]) -> list[str]:
    """Return phase identity list for the full pipeline (before F3S expansion).

    The saved ``active_phases`` in runner-state.json is actually the expanded
    list. To keep reconstruction simple we expand F3S here.
    """
    active: list[dict[str, Any]] = []
    for step in pipeline:
        active.append(step)
    return [s["phase"] for s in active]


def _expand_full_pipeline(project: str) -> list[dict[str, Any]]:
    """Build the expanded step list matching ava-pipeline-runner-cli.py logic."""
    sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
    import pipeline_plan  # noqa: PLC0415

    pipeline: list[dict[str, Any]] = [
        {
            "phase": "F0",
            "agent": "_ast_extractor",
            "trigger": None,
            "label": "AST Extraction — Deterministic (run_ast_analysis.py)",
        },
        {"phase": "F1", "agent": "ava-asis-orchestrator", "trigger": "FP"},
        {"phase": "F1a", "agent": "ava-asis-inventory", "trigger": None},
        {"phase": "F1b", "agent": "ava-asis-solution-delphi", "trigger": None},
        {"phase": "F1c", "agent": "ava-asis-db-analyzer", "trigger": None},
        {"phase": "F1d", "agent": "ava-asis-documentation", "trigger": None},
        {"phase": "F1e", "agent": "ava-asis-security-review", "trigger": None},
        {"phase": "F1f", "agent": "ava-asis-gaps-risks", "trigger": None},
        {"phase": "F2a", "agent": "ava-tobe-orchestrator", "trigger": "SD"},
        {"phase": "F2b", "agent": "ava-devops-orchestrator", "trigger": "DP"},
        {"phase": "F2c", "agent": "ava-qa-orchestrator", "trigger": "TPT"},
        {"phase": "F3", "agent": "ava-prototype", "trigger": None},
        {"phase": "F3S", "agent": "ava-speckit-orchestrator", "trigger": "SK"},
        {"phase": "F4", "agent": "ava-stack-orchestrator", "trigger": "SG"},
        {"phase": "F5", "agent": "ava-devops-orchestrator", "trigger": "DE"},
        {"phase": "F6", "agent": "ava-qa-orchestrator", "trigger": "TPT"},
        {"phase": "S1", "agent": "ava-summary", "trigger": "SAS"},
        {"phase": "S2", "agent": "ava-summary-remediation", "trigger": None},
        {"phase": "S3", "agent": "ava-summary-validate", "trigger": None},
        {"phase": "S4", "agent": "ava-summary", "trigger": "SAS"},
        {"phase": "FC", "agent": "ava-devops-containerize", "trigger": None},
        {"phase": "FP", "agent": "ava-devops-podman-run", "trigger": None},
    ]

    # Expand F3S in-place.
    f3s_steps = pipeline_plan.dag_steps("F3S", REPO_ROOT, project=project)
    if f3s_steps:
        idx = next((i for i, s in enumerate(pipeline) if s["phase"] == "F3S"), -1)
        if idx >= 0:
            pipeline[idx : idx + 1] = [
                {
                    "phase": s["phase"],
                    "agent": s["agent"],
                    "trigger": s.get("trigger"),
                    "label": s.get("label", ""),
                    "feature": s.get("feature", ""),
                    "task_id": s.get("task_id", ""),
                    "kind": s.get("kind", "agent"),
                }
                for s in f3s_steps
            ]

    # Expand F4 from task ledger.
    try:
        import pipeline_config as _pipeline_config  # noqa: PLC0415
        planned = pipeline_plan.build_plan(_pipeline_config.load_config(project), phases=["F4"])
        expanded_f4 = pipeline_plan.expand_foreach(planned, project)
        if len(expanded_f4) > 1 or expanded_f4[0].task_id:
            idx = next((i for i, s in enumerate(pipeline) if s["phase"] == "F4"), -1)
            if idx >= 0:
                pipeline[idx : idx + 1] = [
                    {
                        "phase": step.phase,
                        "agent": step.agent,
                        "trigger": step.trigger,
                        "label": step.label,
                        "feature": step.feature or "",
                        "task_id": step.task_id or "",
                        "task_group": step.task_group or "",
                        "target_stack": step.target_stack or "",
                        "kind": step.kind,
                    }
                    for step in expanded_f4
                ]
    except Exception:  # noqa: BLE001
        pass

    return pipeline


def _compute_metrics_skeleton(
    active_phases: list[str], executed: set[str]
) -> dict[str, dict[str, Any]]:
    """Build a minimal exec_metrics dict for reconstructed state."""
    metrics: dict[str, dict[str, Any]] = {}
    for phase in active_phases:
        metrics[phase] = {
            "phase": phase,
            "agent": "",
            "skill_kb": 0,
            "inp_tokens": 0,
            "out_max": 0,
            "resp_tokens": 0,
            "ctx_pct": 0,
            "elapsed_s": 0,
            "artifacts": 0,
            "val_ok": phase in executed,
            "detail": "reconstructed from execution report",
        }
    return metrics


def reconstruct(project: str) -> dict[str, Any]:
    """Build a runner-state.json dict from existing artifacts."""
    manifest = _read_manifest(project)
    manifest_features = [f["feature"] for f in manifest.get("features", [])] if manifest else []

    # Scan per-step reports.
    latest_reports = _scan_report_files(project, manifest_features)

    # Build expanded pipeline to know active_phases and determine ordering.
    active_steps = _expand_full_pipeline(project)
    active_phases = [s["phase"] for s in active_steps]

    # Reports are evidence of execution.
    executed: set[str] = {p for p in latest_reports if p in active_phases}

    # Infer deterministic tool steps from artifacts.
    executed.update(_infer_tool_steps_from_artifacts(project, executed))

    # Restrict inferred steps to the current active phase list.
    executed &= set(active_phases)

    # Build metrics skeleton.
    exec_metrics = _compute_metrics_skeleton(active_phases, executed)

    # Determine last_index: position right after the last contiguous executed step.
    last_index = 0
    for idx, phase in enumerate(active_phases):
        if phase in executed:
            last_index = idx + 1
        else:
            break

    # skipped/aborted: we cannot reconstruct them reliably from reports alone.
    skipped: list[str] = []
    aborted: list[str] = []

    state = {
        "project": project,
        "run_id": f"reconstructed-{int(time.time())}",
        "active_phases": active_phases,
        "executed": sorted(executed),
        "skipped": skipped,
        "aborted": aborted,
        "exec_metrics": exec_metrics,
        "last_index": last_index,
        "reconstructed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "reconstructed_from": "execution reports + artifacts",
    }
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reconstruct ava-pipeline-runner-cli runner-state.json from artifacts."
    )
    parser.add_argument("--project", required=True, help="Nome do projeto")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime o JSON gerado sem escrever no disco",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescreve runner-state.json existente",
    )
    args = parser.parse_args(argv)

    project = args.project
    if not _project_dir(project).is_dir():
        _fail(f"projeto não encontrado: {project}")

    state_path = _runner_state_path(project)
    if state_path.exists() and not args.dry_run and not args.force:
        _fail(
            f"{state_path} já existe. Use --force para sobrescrever "
            f"ou --dry-run para visualizar."
        )

    state = reconstruct(project)

    # Validate JSON serialization.
    try:
        json.dumps(state)
    except Exception as exc:  # noqa: BLE001
        _fail(f"estado gerado não é serializável em JSON: {exc}")

    if args.dry_run:
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[reconstruct_runner_state] estado salvo em: {state_path}")
    print(f"  fases ativas: {len(state['active_phases'])}")
    print(f"  executadas: {len(state['executed'])}")
    print(f"  last_index: {state['last_index']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
