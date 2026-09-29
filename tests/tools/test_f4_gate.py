"""Gate estrutural F4S → F4 — `src/shared/tools/f4_gate.py`.

A precondição "só despache coders com o scaffold aprovado" era prosa no Step 0.0
do `orchestrator-stack.md`, conferida pelo próprio agente que ela governa. Estes
testes existem para que ela seja conferida por código, e para que a ausência de
evidência reprove — nunca aprove por omissão.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import f4_gate


def _estado(**overrides) -> dict:
    task = {"status": "completed", "build_status": "succeeded",
            "verification_status": "succeeded", "commit_sha": "abc1234"}
    base = {
        "schema_version": "1.0.0", "project": "P",
        "tasks": {"T-SCAFFOLD-FRONTEND-001": dict(task),
                  "T-SCAFFOLD-BACKEND-001": dict(task)},
        "approval": {"status": "approved"},
        "artifacts": {},
    }
    base.update(overrides)
    return base


def _projeto(tmp_path: Path, estado: dict | None = None, *,
             com_dirs: bool = True, com_git: bool = True) -> Path:
    tobe = tmp_path / "projects" / "P" / "outputs" / "tobe"
    tobe.mkdir(parents=True, exist_ok=True)
    if com_dirs:
        for componente, arquivo in (("frontend", "package.json"),
                                    ("backend", "App.csproj")):
            destino = tobe / "source-code" / componente
            destino.mkdir(parents=True, exist_ok=True)
            (destino / arquivo).write_text("{}", encoding="utf-8")
    if com_git:
        (tobe / "source-code" / ".git").mkdir(parents=True, exist_ok=True)
    if estado is not None:
        (tobe / "tasks-progress.json").write_text(json.dumps(estado), encoding="utf-8")
    return tmp_path


def test_gate_valido_libera_os_coders(tmp_path: Path) -> None:
    _projeto(tmp_path, _estado())
    resultado = f4_gate.check("P", tmp_path)
    assert resultado.ok is True
    assert resultado.coders_released is True
    assert resultado.reasons == []


def test_coders_released_false_impede_a_f4(tmp_path: Path) -> None:
    _projeto(tmp_path, _estado(approval={"status": "awaiting_user_approval"}))
    resultado = f4_gate.check("P", tmp_path)
    assert resultado.ok is False
    assert any("coders_released=false" in motivo for motivo in resultado.reasons)


def test_aprovacao_ausente_impede_a_f4(tmp_path: Path) -> None:
    """Ausência de decisão nunca é aprovação."""
    _projeto(tmp_path, _estado(approval=None))
    assert f4_gate.check("P", tmp_path).ok is False


def test_estado_da_f4s_ausente_impede_a_f4(tmp_path: Path) -> None:
    _projeto(tmp_path, None)
    resultado = f4_gate.check("P", tmp_path)
    assert resultado.ok is False
    assert "F4S" in resultado.reasons[0]


def test_scaffold_incompleto_impede_a_f4(tmp_path: Path) -> None:
    estado = _estado()
    estado["tasks"]["T-SCAFFOLD-FRONTEND-001"]["status"] = "failed"
    _projeto(tmp_path, estado)
    resultado = f4_gate.check("P", tmp_path)
    assert resultado.ok is False
    assert any("frontend" in motivo for motivo in resultado.reasons)


def test_build_inicial_reprovado_impede_a_f4(tmp_path: Path) -> None:
    estado = _estado()
    estado["tasks"]["T-SCAFFOLD-BACKEND-001"]["build_status"] = "failed"
    _projeto(tmp_path, estado)
    resultado = f4_gate.check("P", tmp_path)
    assert resultado.ok is False
    assert any("build inicial de backend" in motivo for motivo in resultado.reasons)


def test_baseline_ausente_impede_a_f4(tmp_path: Path) -> None:
    _projeto(tmp_path, _estado(), com_git=False)
    resultado = f4_gate.check("P", tmp_path)
    assert resultado.ok is False
    assert any("baseline git" in motivo for motivo in resultado.reasons)


def test_diretorio_canonico_vazio_impede_a_f4(tmp_path: Path) -> None:
    _projeto(tmp_path, _estado(), com_dirs=False)
    resultado = f4_gate.check("P", tmp_path)
    assert resultado.ok is False
    assert any("canonico" in motivo for motivo in resultado.reasons)


def test_downstream_bloqueado_pela_f4s_impede_a_f4(tmp_path: Path) -> None:
    estado = _estado()
    estado["downstream"] = {"status": "blocked", "reason": "componente reprovado"}
    _projeto(tmp_path, estado)
    assert f4_gate.check("P", tmp_path).ok is False
