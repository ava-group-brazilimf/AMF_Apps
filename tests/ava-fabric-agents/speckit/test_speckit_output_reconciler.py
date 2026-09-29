from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL = REPO_ROOT / "src" / "shared" / "tools" / "speckit_output_reconciler.py"


def _load():
    spec = importlib.util.spec_from_file_location("speckit_output_reconciler_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


reconciler = _load()


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    root.mkdir(parents=True)
    (root / "wave-spec-manifest.json").write_text(json.dumps({
        "trace_id": "trace-1",
        "features": [
            {"feature": "001-w0-foundation", "codegen": True},
            {"feature": "002-w1-domain", "codegen": True},
            {"feature": "003-w2-cutover", "codegen": False},
        ],
    }), encoding="utf-8")
    return root


def test_materializa_todos_os_contratos_sem_liberar_f4(tmp_path: Path):
    root = _project(tmp_path)

    planning = reconciler.reconcile("P", "planning", tmp_path)
    final = reconciler.reconcile("P", "final", tmp_path)

    assert planning["status"] == "INCOMPLETE"
    assert final["status"] == "INCOMPLETE"
    for feature in ("001-w0-foundation", "002-w1-domain"):
        directory = root / "specs" / feature
        assert all((directory / name).is_file() for name in (
            "spec.md", "plan.md", "plan-graph.json", "task-fragment.json", "tasks.md",
        ))
    assert (root / "specs" / "003-w2-cutover" / "spec.md").is_file()
    assert not (root / "specs" / "003-w2-cutover" / "plan.md").exists()
    assert json.loads((root / "compliance-status.json").read_text(encoding="utf-8"))[
        "verdict"] == "BLOCKED"
    assert (root / "ava-agents-progress.txt").is_file()


def test_nao_sobrescreve_output_real_e_e_idempotente(tmp_path: Path):
    root = _project(tmp_path)
    constitution = root / "constitution.md"
    constitution.write_text("# real\n", encoding="utf-8")

    first = reconciler.reconcile("P", "planning", tmp_path)
    second = reconciler.reconcile("P", "planning", tmp_path)

    assert constitution.read_text(encoding="utf-8") == "# real\n"
    assert first["materialized"]
    assert second["materialized"] == []
    assert second["status"] == "INCOMPLETE"


def test_json_existente_sem_campos_obrigatorios_continua_incomplete(tmp_path: Path):
    root = _project(tmp_path)
    (root / "traceability.json").write_text("{}", encoding="utf-8")

    result = reconciler.reconcile("P", "planning", tmp_path)

    assert result["status"] == "INCOMPLETE"
    assert "traceability.json" in result["placeholders"]