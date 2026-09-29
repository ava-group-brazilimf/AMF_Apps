"""Testes do gate deterministico da solution .NET (spec 044)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "utils"))
import verify_dotnet_solution as verifier  # noqa: E402


def _write(path: Path, text: str = '<Project Sdk="Microsoft.NET.Sdk" />') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def solution_root(tmp_path: Path) -> Path:
    _write(tmp_path / "Demo.sln", "Solution")
    _write(tmp_path / "global.json", '{"sdk":{"version":"10.0.100"}}')
    _write(tmp_path / "Directory.Build.props")
    _write(tmp_path / "Directory.Packages.props", "<Project><PropertyGroup><ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally></PropertyGroup></Project>")
    _write(tmp_path / ".gitignore", "bin/\nobj/\n")
    _write(tmp_path / "src/SharedKernel/Demo.SharedKernel/Demo.SharedKernel.csproj")
    for layer in ("Domain", "Application", "Infrastructure", "Api"):
        _write(tmp_path / f"src/Vendas/Demo.Vendas.{layer}/Demo.Vendas.{layer}.csproj")
    for layer in ("Domain.Tests", "Application.Tests"):
        _write(tmp_path / f"tests/Vendas/Demo.Vendas.{layer}/Demo.Vendas.{layer}.csproj")
    return tmp_path


def _successful_run(calls: list[list[str]]):
    def runner(command, *args, **kwargs):
        calls.append(list(command))
        return subprocess.CompletedProcess(command, 0, "ok", "")
    return runner


#: O verifier executa por `proc_stream.run` — que transmite `restore`/`build`/
#: `test` ao vivo e encerra a árvore no timeout — e não mais por
#: `subprocess.run`. Interceptar aqui é interceptar o executor de verdade.
_SEAM = (verifier.proc_stream, "run")


def test_verificacao_completa_passa(solution_root: Path, monkeypatch):
    calls: list[list[str]] = []
    monkeypatch.setattr(verifier.shutil, "which", lambda _: "dotnet")
    monkeypatch.setattr(*_SEAM, _successful_run(calls))
    result = verifier.verify(solution_root, quiet=True)
    assert result["status"] == "PASS"
    assert [phase["name"] for phase in result["phases"]] == ["prereq", "structure", "restore", "build", "test"]
    assert [command[1] for command in calls] == ["restore", "build", "test"]


def test_estrutura_incompleta_para_antes_do_restore(solution_root: Path, monkeypatch):
    api = solution_root / "src/Vendas/Demo.Vendas.Api/Demo.Vendas.Api.csproj"
    api.unlink()
    monkeypatch.setattr(verifier.shutil, "which", lambda _: "dotnet")
    result = verifier.verify(solution_root, quiet=True)
    assert result["status"] == "FAIL"
    assert result["exit_code"] == verifier.EXIT_STRUCTURE
    assert [phase["name"] for phase in result["phases"]] == ["prereq", "structure"]


def test_build_falhando_retorna_exit_40(solution_root: Path, monkeypatch):
    monkeypatch.setattr(verifier.shutil, "which", lambda _: "dotnet")
    def runner(command, *args, **kwargs):
        return subprocess.CompletedProcess(command, 1 if command[1] == "build" else 0, "CS0246", "")
    monkeypatch.setattr(*_SEAM, runner)
    result = verifier.verify(solution_root, quiet=True)
    assert result["status"] == "FAIL"
    assert result["exit_code"] == verifier.EXIT_BUILD
    assert result["phases"][-1]["name"] == "build"


def test_cli_reprova_diretorio_inexistente(tmp_path: Path, capsys):
    code = verifier.main(["--root", str(tmp_path / "ausente"), "--json"])
    assert code == verifier.EXIT_USAGE
