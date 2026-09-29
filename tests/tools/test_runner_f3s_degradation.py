"""Regression tests for non-blocking F3S DAG expansion failures."""
from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PY = REPO_ROOT / "ava-pipeline-runner-cli.py"
_FUNCTIONS = (
    "_mark_executed", "_record_degradation", "_print_degradation",
    "_degrade_phase", "_degrade_unexpandable_f3s",
    # A degradação consulta o predicado para decidir se a fase entra na
    # contabilidade de reprovação — a F3S é non-blocking e não entra.
    "_is_speckit_nonblocking", "_speckit_nonblocking_step",
)
_CONSTANTS = ("_DEGRADATIONS", "SPECKIT_PHASE_PREFIX", "SPECKIT_AGENT_PREFIXES")


def _compile_helpers() -> object:
    tree = ast.parse(RUNNER_PY.read_text(encoding="utf-8"))
    body = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in _FUNCTIONS
        or isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        and node.target.id in _CONSTANTS
        or isinstance(node, ast.Assign) and any(
            isinstance(alvo, ast.Name) and alvo.id in _CONSTANTS
            for alvo in node.targets)
    ]
    found = {node.name for node in body if isinstance(node, ast.FunctionDef)}
    assert found == set(_FUNCTIONS), sorted(set(_FUNCTIONS) - found)
    return compile(ast.Module(body=body, type_ignores=[]), "<runner>", "exec")


def test_unexpandable_f3s_is_degraded_without_becoming_aborted(capsys):
    # `CYAN`: a degradação informativa (fase non-blocking) usa outra cor que a
    # degradação comum, para o texto não sugerir reprovação onde não há.
    namespace = {"YELLOW": "", "CYAN": "", "RESET": ""}
    exec(_compile_helpers(), namespace)

    executed: list[str] = []
    skipped: list[str] = []
    aborted: list[str] = []
    val_failed: list[str] = []
    metrics: dict = {}
    step = {"phase": "F3S", "agent": "ava-speckit-orchestrator"}

    namespace["_degrade_unexpandable_f3s"](
        step, RuntimeError("wave-model.json inválido"), executed, skipped, aborted,
        metrics, val_failed,
    )

    assert executed == ["F3S"]
    assert aborted == []
    # Antes: `val_failed == ["F3S"]`. A camada SpecKit passou a ser
    # non-blocking enquanto está em evolução — o achado continua registrado em
    # `_DEGRADATIONS` e em `metrics`, mas a fase NÃO entra na contabilidade de
    # reprovação do run nem aparece como "❌ Val-Fail" no dashboard.
    # Ver `_is_speckit_nonblocking` no runner.
    assert val_failed == []
    assert metrics["F3S"]["degraded"] is True
    assert metrics["F3S"]["non_blocking"] is True
    assert "wave-model.json inválido" in metrics["F3S"]["detail"]
    assert namespace["_DEGRADATIONS"][0]["phase"] == "F3S"
    assert namespace["_DEGRADATIONS"][0]["severity"] == "info"