"""Verificação determinística de uma task da F4 — `ava_pipeline._verify_f4_task`.

O que estes testes protegem, em ordem de importância:

1. `verified` só existe com exit code 0 de um build real;
2. o código verificado vive em `source-code/{frontend|backend}` — nunca em
   `source-code/{stack}` — e o commit acontece no repo do baseline da F4S;
3. `files_written` vem do diff do git, não da declaração do agente;
4. build reprovado vira `failed`/`blocked` no razão, nunca `skipped` (que
   significaria "pulado por decisão", não "não compilou").
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import f4_routing
import f4s_build_runner
import f4s_deterministic_harness
import task_ledger
from ava_pipeline import Step, _verify_f4_task


def _setup_ledger(tmp_path: Path) -> None:
    task_ledger.REPO_ROOT = tmp_path
    speckit = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    speckit.mkdir(parents=True, exist_ok=True)
    trace = {
        "schema_version": "4.0.0",
        "project": "P",
        "trace_id": "trace-test",
        "total_tasks": 1,
        "entries": [{
            "task_id": "T-001",
            "title": "Implementa Cart",
            "feature": "001-domain",
            "spec_id": "SPEC-001",
            "group": "G-D",
            "task_type": "backend",
            "target_stack": "dotnet",
            "migration_wave_id": "W1",
            "migration_wave_order": 1,
            "verify_command": "dotnet build",
            "action": "create",
            "target_file": "backend/Domain/Cart.cs",
            "depends_on": [],
            "backend_dependencies": [],
            "acceptance": ["ok"],
            "priority": "P2",
        }],
    }
    (speckit / "traceability.json").write_text(json.dumps(trace), encoding="utf-8")
    task_ledger.init("P", repo_root=tmp_path)


def _step() -> Step:
    return Step(
        phase="F4:T-001", group="F4", agent="ava-stack-dotnet-backend",
        trigger="SG", label="F4 — T-001", inputs={},
        task_group="G-D", target_stack="dotnet",
        feature="001-domain", task_id="T-001",
    )


@pytest.fixture()
def build_ok(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(f4s_build_runner, "run_build",
                        lambda repo_root, stack, **kwargs: {
                            "command": "dotnet build", "exit_code": 0,
                            "stdout": "ok", "stderr": "", "timed_out": False})


@pytest.fixture()
def build_fail(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(f4s_build_runner, "run_build",
                        lambda repo_root, stack, **kwargs: {
                            "command": "dotnet build", "exit_code": 1,
                            "stdout": "", "stderr": "error", "timed_out": False})


def test_verify_f4_task_verifies_and_commits(tmp_path: Path, build_ok) -> None:
    _setup_ledger(tmp_path)
    backend = (tmp_path / "projects" / "P" / "outputs" / "tobe"
               / "source-code" / "backend")
    backend.mkdir(parents=True, exist_ok=True)
    (backend / "Cart.cs").write_text("class Cart {}", encoding="utf-8")

    result = _verify_f4_task(
        _step(), "P", {"artifacts": []}, task_ledger.get("P", "T-001", tmp_path),
        "dotnet build", tmp_path / "logs", 60, repo_root=tmp_path,
    )

    assert result["status"] == "verified"
    assert result["exit_code"] == 0
    assert result["commit_hash"] != ""
    assert result["component_type"] == "backend"
    assert result["canonical_source_dir"] == "source-code/backend"
    # files_written vem do diff real, e o arquivo escrito aparece nele.
    assert any("Cart.cs" in item for item in result["files_written"])

    repo = tmp_path / "projects" / "P" / "outputs" / "tobe" / "source-code"
    assert (repo / "GENERATION_LOG.md").exists()
    assert (repo / ".git").is_dir()
    assert not (repo / "dotnet").exists(), "nenhum diretorio por stack"

    estado = task_ledger.get("P", "T-001", tmp_path)
    assert estado["status"] == "verified"
    assert estado["routing"]["agent"] == "ava-stack-dotnet-backend"
    assert estado["evidence"]["commit_hash"] == result["commit_hash"]
    assert len(estado["attempt_history"]) == 1


def test_verify_f4_task_failed_build_never_verifies(tmp_path: Path, build_fail) -> None:
    _setup_ledger(tmp_path)
    result = _verify_f4_task(
        _step(), "P", {"artifacts": []}, task_ledger.get("P", "T-001", tmp_path),
        "dotnet build", tmp_path / "logs", 60, repo_root=tmp_path,
    )

    assert result["exit_code"] == 1
    assert result["status"] == "failed", "build reprovado nao pode virar `skipped`"
    assert result["commit_hash"] == "", "task reprovada nao gera commit"
    assert result["attempts"] == f4s_deterministic_harness.MAX_BUILD_ATTEMPTS
    assert task_ledger.get("P", "T-001", tmp_path)["status"] == "failed"


def test_verify_f4_task_blocks_after_max_attempts(tmp_path: Path, build_fail) -> None:
    _setup_ledger(tmp_path)
    for _ in range(task_ledger.MAX_ATTEMPTS):
        _verify_f4_task(
            _step(), "P", {"artifacts": []},
            task_ledger.get("P", "T-001", tmp_path),
            "dotnet build", tmp_path / "logs", 60, repo_root=tmp_path)
    estado = task_ledger.get("P", "T-001", tmp_path)
    assert estado["status"] == "blocked"
    assert len(estado["attempt_history"]) == task_ledger.MAX_ATTEMPTS


def test_verify_f4_task_routes_to_specialized_agent(tmp_path: Path, build_ok) -> None:
    """A rota é resolvida aqui dentro quando o chamador não a passa."""
    _setup_ledger(tmp_path)
    result = _verify_f4_task(
        _step(), "P", {"artifacts": []}, task_ledger.get("P", "T-001", tmp_path),
        "dotnet build", tmp_path / "logs", 60, repo_root=tmp_path,
    )
    assert result["agent"] == "ava-stack-dotnet-backend"
    assert "ava-f4s-codegen-agent" not in result["agent"]


def test_verify_f4_task_fails_closed_on_unknown_stack(tmp_path: Path, build_ok) -> None:
    _setup_ledger(tmp_path)
    task = dict(task_ledger.get("P", "T-001", tmp_path))
    task["target_stack"] = "cobol"
    task["task_type"] = ""
    with pytest.raises(f4_routing.RoutingError):
        _verify_f4_task(_step(), "P", {"artifacts": []}, task,
                        "dotnet build", tmp_path / "logs", 60, repo_root=tmp_path)
