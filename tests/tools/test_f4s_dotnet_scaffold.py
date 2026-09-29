"""Testes do gerador deterministico de scaffold .NET (spec 044)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
import f4s_dotnet_scaffold as scaffold  # noqa: E402


BLUEPRINT = """\
# Architecture Blueprint
## 3. Bounded Context Map - TO-BE
| # | AS-IS Context | TO-BE Module | Changes |
|---|---------------|--------------|---------|
| 1 | Sales | **Vendas** | API |
| 2 | Stock | **Estoque** | API |
"""


#: Pacotes de teste da matriz do major usado pelas fixtures (10.0). Lidos em
#: runtime para que o teste acompanhe versions.yaml em vez de duplicá-lo.
_PACOTES_TESTE = {
    nome: versao
    for nome, versao in scaffold.load_versions()["majors"]["10.0"]["packages"].items()
    if nome in ("Microsoft.NET.Test.Sdk", "xunit")
}


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    project = tmp_path / "projects" / "demo"
    (project / "context").mkdir(parents=True)
    (project / "outputs" / "tobe" / "docs").mkdir(parents=True)
    (project / "context" / "project-config.yaml").write_text(
        "project_name: Demo ERP\ntobe_stack:\n  backend_version: '10.0'\n  dotnet_sdk_version: '10.0.100'\n",
        encoding="utf-8",
    )
    (project / "outputs" / "tobe" / "docs" / "architecture-blueprint.md").write_text(BLUEPRINT, encoding="utf-8")
    return tmp_path


def _option(command: list[str], name: str) -> str:
    return command[command.index(name) + 1]


def _fake_dotnet(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    if command[:3] == ["dotnet", "new", "sln"] and "--name" in command:
        (cwd / f"{_option(command, '--name')}.sln").write_text("Solution\n", encoding="utf-8")
    elif command[:2] == ["dotnet", "new"] and "--output" in command:
        template, output, name = command[2], cwd / _option(command, "--output"), _option(command, "--name")
        output.mkdir(parents=True, exist_ok=True)
        packages = ""
        if template == "xunit":
            # Versoes vindas da MATRIZ, nunca hardcoded: o template real do
            # `dotnet new` emite o que o SDK instalado define, e o gerador
            # aborta em divergencia. Fixar aqui fazia o teste reprovar a cada
            # atualizacao legitima de versions.yaml.
            packages = ("<ItemGroup>"
                        + "".join(f'<PackageReference Include="{nome}" Version="{v}" />'
                                  for nome, v in _PACOTES_TESTE.items())
                        + "</ItemGroup>")
        (output / f"{name}.csproj").write_text(
            f"<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup>{packages}</Project>", encoding="utf-8")
    elif command[:2] == ["dotnet", "sln"] and "add" in command:
        solution = Path(command[2])
        solution.write_text(solution.read_text(encoding="utf-8") + command[4] + "\n", encoding="utf-8")
    return subprocess.CompletedProcess(command, 0, "--format" if command[-1] == "--help" else "", "")


def test_normaliza_nome_e_contextos():
    assert scaffold.to_pascal("Gestao-de Pedidos") == "GestaoDePedidos"
    assert scaffold.extract_bcs(BLUEPRINT) == ["Vendas", "Estoque"]


def test_extract_bcs_pela_coluna_name():
    blueprint = """\
## Bounded Contexts TO-BE
| BC | Name | Domain Type |
|----|------|-------------|
| BC-01 | Catalog | Core Domain |
| BC-02 | Orders | Core Domain |
"""
    assert scaffold.extract_bcs(blueprint) == ["Catalog", "Orders"]


def test_tfm_desconhecido_reprova_sem_escrever(workspace: Path):
    config = workspace / "projects" / "demo" / "context" / "project-config.yaml"
    config.write_text("project_name: Demo\ntobe_stack:\n  backend_version: '42.0'\n", encoding="utf-8")
    with pytest.raises(scaffold.ScaffoldError, match="TFM net42.0 nao e suportado"):
        scaffold.scaffold("demo", workspace, app_root=workspace / "out", executor=_fake_dotnet)
    assert not (workspace / "out").exists()


def test_gera_solution_cpm_e_referencias(workspace: Path):
    result = scaffold.scaffold("demo", workspace, executor=_fake_dotnet)
    root = Path(result["app_root"])
    assert result["status"] == "PASS"
    assert result["solution"] == "DemoErp.sln"
    assert result["bcs"] == ["Vendas", "Estoque"]
    assert (root / "src/Vendas/DemoErp.Vendas.Domain/DemoErp.Vendas.Domain.csproj").is_file()
    assert (root / "tests/Estoque/DemoErp.Estoque.Application.Tests/DemoErp.Estoque.Application.Tests.csproj").is_file()
    packages = (root / "Directory.Packages.props").read_text(encoding="utf-8")
    test_project = (root / "tests/Vendas/DemoErp.Vendas.Domain.Tests/DemoErp.Vendas.Domain.Tests.csproj").read_text(encoding="utf-8")
    esperado = _PACOTES_TESTE["Microsoft.NET.Test.Sdk"]
    assert f'PackageVersion Include="Microsoft.NET.Test.Sdk" Version="{esperado}"' in packages
    assert 'PackageReference Include="Microsoft.NET.Test.Sdk" Version=' not in test_project
    assert any(record["argv"][:3] == ["dotnet", "add", str(root / "src/Vendas/DemoErp.Vendas.Domain/DemoErp.Vendas.Domain.csproj")] for record in result["commands"])


def test_segunda_execucao_preserva_projeto(workspace: Path):
    first = scaffold.scaffold("demo", workspace, executor=_fake_dotnet)
    root = Path(first["app_root"])
    domain = root / "src/Vendas/DemoErp.Vendas.Domain/DemoErp.Vendas.Domain.csproj"
    domain.write_text("<Project />", encoding="utf-8")
    second = scaffold.scaffold("demo", workspace, executor=_fake_dotnet)
    assert domain.read_text(encoding="utf-8") == "<Project />"
    assert "src/Vendas/DemoErp.Vendas.Domain/DemoErp.Vendas.Domain.csproj" in second["files_skipped"]
    assert second["files_written"] == []


def test_cli_erro_json(workspace: Path, capsys):
    code = scaffold.main(["--project", "ausente", "--workspace", str(workspace), "--json"])
    assert code == 2
    assert json.loads(capsys.readouterr().out)["status"] == "ERROR"
