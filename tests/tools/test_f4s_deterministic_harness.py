"""Tests for f4s_deterministic_harness."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import f4s_build_runner
import f4s_deterministic_harness as harness


def test_ensure_repo_initializes_git_and_log(tmp_path: Path) -> None:
    repo = harness.ensure_repo("P", "dotnet", repo_root=tmp_path)
    assert (repo / ".git").is_dir()
    assert (repo / "GENERATION_LOG.md").exists()
    assert (repo / ".gitignore").exists()


def test_run_build_with_remediation_succeeds_first_try(tmp_path: Path) -> None:
    repo = harness.ensure_repo("P", "dotnet", repo_root=tmp_path)
    # dotnet build needs a real project; mock the runner instead.
    original = f4s_build_runner.run_build

    def fake_run_build(repo_root: Path, stack: str, **kwargs: object) -> dict:
        return {
            "command": "dotnet build", "exit_code": 0,
            "stdout": "ok", "stderr": "", "timed_out": False,
        }

    f4s_build_runner.run_build = fake_run_build
    try:
        result = harness.run_build_with_remediation(repo, "dotnet", "001-domain")
        assert result["success"] is True
        assert result["skipped"] is False
        assert result["status"] == "verified"
        assert len(result["attempts"]) == 1
        assert result["abort_needed"] is False
    finally:
        f4s_build_runner.run_build = original


def test_run_build_with_remediation_retries_then_skips(tmp_path: Path) -> None:
    repo = harness.ensure_repo("P", "dotnet", repo_root=tmp_path)
    original = f4s_build_runner.run_build
    calls = {"count": 0}

    def fake_run_build(repo_root: Path, stack: str, **kwargs: object) -> dict:
        calls["count"] += 1
        return {
            "command": "dotnet build", "exit_code": 1,
            "stdout": "", "stderr": "error", "timed_out": False,
        }

    f4s_build_runner.run_build = fake_run_build
    try:
        result = harness.run_build_with_remediation(repo, "dotnet", "001-domain")
        assert result["success"] is False
        assert result["skipped"] is True
        assert result["status"] == "skipped"
        assert calls["count"] == harness.MAX_BUILD_ATTEMPTS
        assert result["abort_needed"] is False
        log = (repo / "GENERATION_LOG.md").read_text(encoding="utf-8")
        assert "Compilation Failure Report" in log
    finally:
        f4s_build_runner.run_build = original


def test_run_build_with_remediation_aborts_after_three_skips(tmp_path: Path) -> None:
    repo = harness.ensure_repo("P", "dotnet", repo_root=tmp_path)
    original = f4s_build_runner.run_build

    def fake_run_build(repo_root: Path, stack: str, **kwargs: object) -> dict:
        return {
            "command": "dotnet build", "exit_code": 1,
            "stdout": "", "stderr": "error", "timed_out": False,
        }

    f4s_build_runner.run_build = fake_run_build
    try:
        for i in range(3):
            result = harness.run_build_with_remediation(
                repo, "dotnet", f"00{i}-domain"
            )
        assert result["abort_needed"] is True
        assert result["consecutive_skips"] == 3
    finally:
        f4s_build_runner.run_build = original


def test_run_task_commits_on_success(tmp_path: Path) -> None:
    repo = harness.ensure_repo("P", "dotnet", repo_root=tmp_path)
    original = f4s_build_runner.run_build

    def fake_run_build(repo_root: Path, stack: str, **kwargs: object) -> dict:
        return {
            "command": "dotnet build", "exit_code": 0,
            "stdout": "ok", "stderr": "", "timed_out": False,
        }

    f4s_build_runner.run_build = fake_run_build
    try:
        result = harness.run_task("P", "dotnet", "001-domain", repo_root=tmp_path)
        assert result["success"] is True
        assert result["status"] == "verified"
        assert result["commit_hash"] != ""
        assert (repo / ".f4s" / "snapshots" / "001-domain-before.md").exists()
        assert (repo / ".f4s" / "snapshots" / "001-domain-after.md").exists()
    finally:
        f4s_build_runner.run_build = original


def test_run_task_skips_without_commit_on_failure(tmp_path: Path) -> None:
    repo = harness.ensure_repo("P", "dotnet", repo_root=tmp_path)
    original = f4s_build_runner.run_build

    def fake_run_build(repo_root: Path, stack: str, **kwargs: object) -> dict:
        return {
            "command": "dotnet build", "exit_code": 1,
            "stdout": "", "stderr": "error", "timed_out": False,
        }

    f4s_build_runner.run_build = fake_run_build
    try:
        result = harness.run_task("P", "dotnet", "001-domain", repo_root=tmp_path)
        assert result["success"] is False
        assert result["status"] == "skipped"
        assert result["commit_hash"] == ""
    finally:
        f4s_build_runner.run_build = original


# ─── Regressões de causa raiz (cadastro-funcionario-03) ──────────────────────
#
# T-W0-FE-001 falhou com exit 127 em 3 tentativas, disparou 6 remediações de LLM
# (251s) e derrubou a fase inteira com 162 tasks nunca tentadas. Três defeitos
# encadeados, um teste para cada.

def test_verificador_da_stack_vence_o_verify_command_da_task() -> None:
    """`ng build ...` escrito em prosa não pode desligar o verify_angular_app."""
    comando = f4s_build_runner.resolve_command(
        "angular", "ng build --configuration=production --project=app")
    assert "verify_angular_app.py" in " ".join(comando)
    assert "ng" not in comando[:1]

    comando_dotnet = f4s_build_runner.resolve_command("dotnet", "dotnet build")
    assert "verify_dotnet_solution.py" in " ".join(comando_dotnet)


def test_override_continua_valendo_para_stack_sem_verificador() -> None:
    assert f4s_build_runner.resolve_command("fastapi", "pytest -q") == ["pytest", "-q"]


def test_executavel_ausente_e_classificado_sem_executar(tmp_path: Path) -> None:
    resultado = f4s_build_runner.run_build(
        tmp_path, "fastapi", command_override="ng build --prod")
    assert resultado["exit_code"] == 127
    assert resultado["toolchain_missing"] == "ng"
    assert "ambiente" in resultado["stderr"]


def test_toolchain_ausente_nao_gasta_remediacao(tmp_path: Path) -> None:
    """Nenhum agente conserta `ng: command not found` escrevendo código."""
    repo = harness.ensure_repo("P", "dotnet", repo_root=tmp_path)
    original = f4s_build_runner.run_build
    chamadas = {"build": 0, "remediacao": 0}

    def fake_run_build(repo_root, stack, **kwargs):
        chamadas["build"] += 1
        return {"command": "ng build", "exit_code": 127, "stdout": "",
                "stderr": "executavel ausente", "timed_out": False,
                "toolchain_missing": "ng"}

    def remediar(attempt, build_result):
        chamadas["remediacao"] += 1
        return True

    f4s_build_runner.run_build = fake_run_build
    try:
        resultado = harness.run_build_with_remediation(
            repo, "dotnet", "T-001", remediate=remediar)
        assert chamadas["build"] == 1, "não insiste num comando que não existe"
        assert chamadas["remediacao"] == 0, "não pede correção de código ao agente"
        assert resultado["toolchain_missing"] == "ng"
        assert resultado["success"] is False
    finally:
        f4s_build_runner.run_build = original


def test_uma_task_falhando_3x_nao_aborta_a_fase(tmp_path: Path) -> None:
    """O contador é de specs DISTINTAS; retentativa da mesma não conta 3 vezes."""
    repo = harness.ensure_repo("P", "dotnet", repo_root=tmp_path)
    original = f4s_build_runner.run_build
    f4s_build_runner.run_build = lambda repo_root, stack, **kwargs: {
        "command": "dotnet build", "exit_code": 1,
        "stdout": "", "stderr": "CS0246", "timed_out": False,
    }
    try:
        for _ in range(3):   # as 3 tentativas de ledger da MESMA task
            resultado = harness.run_build_with_remediation(repo, "dotnet", "T-001")
        assert resultado["consecutive_skips"] == 1
        assert resultado["abort_needed"] is False
    finally:
        f4s_build_runner.run_build = original


def test_tres_specs_distintas_puladas_ainda_abortam(tmp_path: Path) -> None:
    """O sinal legítimo continua existindo: a geração inteira está quebrada."""
    repo = harness.ensure_repo("P", "dotnet", repo_root=tmp_path)
    original = f4s_build_runner.run_build
    f4s_build_runner.run_build = lambda repo_root, stack, **kwargs: {
        "command": "dotnet build", "exit_code": 1,
        "stdout": "", "stderr": "CS0246", "timed_out": False,
    }
    try:
        for task_id in ("T-001", "T-002", "T-003"):
            resultado = harness.run_build_with_remediation(repo, "dotnet", task_id)
        assert resultado["consecutive_skips"] == 3
        assert resultado["abort_needed"] is True
    finally:
        f4s_build_runner.run_build = original
