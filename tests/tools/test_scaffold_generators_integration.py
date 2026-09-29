"""Integração real: generators produzem árvore que os SDKs de fato compilam.

Diferente de `test_scaffold_runner.py`, aqui NÃO há stub. Se o SDK estiver
disponível, o teste roda `dotnet restore` + `dotnet build` de verdade. Sem SDK,
o teste é pulado com a razão explícita — nunca finge que passou.

Windows: a árvore .NET é profunda (`src/<BC>/<Prefix>.<BC>.Infrastructure/...`)
e estoura MAX_PATH sob caminhos longos. Por isso o workspace vai para um
diretório curto em vez do tmp_path do pytest, que já começa com ~120 caracteres.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "shared" / "tools"
UTILS = REPO_ROOT / "src" / "shared" / "utils"
sys.path.insert(0, str(TOOLS))

import f4s_dotnet_scaffold as gen_dotnet  # noqa: E402
import scaffold_paths as sp  # noqa: E402

CONFIG = """\
project_name: "AcmeErp"
client_name: "Avanade"
tobe_stack:
  frontend_framework: "angular"
  frontend_version: "17"
  backend_framework: "dotnet"
  backend_version: "8.0"
"""

BLUEPRINT = """\
| BC | Nome | Entidades |
|---|---|---|
| BC-01 | AcmeErp.Customers | Customer |
| BC-02 | AcmeErp.Billing | Invoice |
"""


def _dotnet_sdk_disponivel(major: str = "8.0") -> bool:
    if shutil.which("dotnet") is None:
        return False
    try:
        result = subprocess.run(["dotnet", "--list-sdks"], capture_output=True,
                                text=True, check=False)
    except OSError:
        return False
    return any(line.startswith(major + ".") for line in result.stdout.splitlines())


def _fake_dotnet(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    if command[-1] == "--help":
        return subprocess.CompletedProcess(command, 0, "--format --no-openapi", "")
    if command[:3] == ["dotnet", "new", "sln"]:
        name = command[command.index("--name") + 1]
        (cwd / f"{name}.sln").write_text("Solution\n", encoding="utf-8")
    elif command[:2] == ["dotnet", "new"]:
        template = command[2]
        output = cwd / command[command.index("--output") + 1]
        name = command[command.index("--name") + 1]
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
            f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>'
            f'net8.0</TargetFramework></PropertyGroup>{packages}</Project>', encoding="utf-8")
        if template == "webapi":
            (output / "Program.cs").write_text("var app = WebApplication.Create();\n", encoding="utf-8")
    elif command[:2] == ["dotnet", "sln"] and "add" in command:
        solution = Path(command[2])
        solution.write_text(solution.read_text(encoding="utf-8") + command[4] + "\n", encoding="utf-8")
    return subprocess.CompletedProcess(command, 0, "", "")


#: Pacotes de teste da matriz do major usado pelas fixtures (8.0). Lidos em
#: runtime para que o teste acompanhe versions.yaml em vez de duplicá-lo.
_PACOTES_TESTE = {
    nome: versao
    for nome, versao in gen_dotnet.load_versions()["majors"]["8.0"]["packages"].items()
    if nome in ("Microsoft.NET.Test.Sdk", "xunit")
}


@pytest.fixture()
def workspace_curto():
    """Workspace num caminho curto — MAX_PATH do Windows é real aqui."""
    base = Path(tempfile.mkdtemp(prefix="avasc-", dir=Path(tempfile.gettempdir())))
    projeto = base / "projects" / "P"
    (projeto / "context").mkdir(parents=True)
    (projeto / "outputs" / "tobe" / "docs").mkdir(parents=True)
    (projeto / "context" / "project-config.yaml").write_text(CONFIG, encoding="utf-8")
    (projeto / "outputs" / "tobe" / "docs" / "architecture-blueprint.md").write_text(
        BLUEPRINT, encoding="utf-8")
    try:
        yield base
    finally:
        shutil.rmtree(base, ignore_errors=True)


# ── Geração determinística (sem SDK) ───────────────────────────────────────

def test_generator_dotnet_escreve_em_backend_e_nunca_em_dotnet(workspace_curto: Path):
    """CA-019 — o destino é a responsabilidade, não a tecnologia."""
    resultado = gen_dotnet.scaffold("P", workspace_curto, executor=_fake_dotnet)

    assert resultado["component_type"] == "backend"
    source = workspace_curto / "projects/P/outputs/tobe/source-code"
    assert (source / "backend").is_dir()
    assert not (source / "dotnet").exists()
    assert resultado["output_path"].endswith("source-code/backend")


def test_generator_dotnet_recusa_destino_derivado_da_tecnologia(workspace_curto: Path):
    """CA-027 — nem com --output-path explícito ele escreve fora do canônico."""
    tobe = workspace_curto / "projects/P/outputs/tobe"
    with pytest.raises(sp.ScaffoldPathError, match="tecnologia|não corresponde"):
        gen_dotnet.scaffold("P", workspace_curto,
                            output_path=tobe / "source-code" / "dotnet")
    assert not (tobe / "source-code" / "dotnet").exists()


def test_geracao_e_reproduzivel_byte_a_byte(workspace_curto: Path):
    """Sem uuid4: o mesmo projeto gera sempre a mesma solution."""
    primeira = gen_dotnet.scaffold("P", workspace_curto, executor=_fake_dotnet)
    sln = Path(primeira["output_path"]) / f"{primeira['solution_prefix']}.sln"
    antes = sln.read_bytes()

    sln.unlink()
    gen_dotnet.scaffold("P", workspace_curto, executor=_fake_dotnet)

    assert sln.read_bytes() == antes


def test_reexecucao_preserva_arquivo_customizado(workspace_curto: Path):
    """Idempotência: sem --force, nada que já existe é sobrescrito."""
    primeira = gen_dotnet.scaffold("P", workspace_curto, executor=_fake_dotnet)
    programa = (Path(primeira["output_path"]) / "src" / "Customers" /
                "AcmeErp.Customers.Api" / "Program.cs")
    programa.write_text("// editado a mão\n", encoding="utf-8")

    segunda = gen_dotnet.scaffold("P", workspace_curto, executor=_fake_dotnet)

    assert programa.read_text(encoding="utf-8") == "// editado a mão\n"
    assert "src/Customers/AcmeErp.Customers.Api/AcmeErp.Customers.Api.csproj" in segunda["files_skipped"]


def test_major_nao_suportado_reprova_sem_adivinhar(workspace_curto: Path):
    config = workspace_curto / "projects/P/context/project-config.yaml"
    config.write_text(CONFIG.replace('backend_version: "8.0"',
                                     'backend_version: "5.0"'), encoding="utf-8")
    with pytest.raises(gen_dotnet.ScaffoldError, match="nao e suportado"):
        gen_dotnet.scaffold("P", workspace_curto)


def test_bc_do_blueprint_nao_repete_o_prefixo_da_solution(workspace_curto: Path):
    """`AcmeErp.Customers` vira `Customers`, não `AcmeErpCustomers`."""
    resultado = gen_dotnet.scaffold("P", workspace_curto, executor=_fake_dotnet)
    assert resultado["bcs"] == ["Customers", "Billing"]
    assert "AcmeErp.Customers.Domain" in " ".join(resultado["files_written"])


def test_scaffold_nao_declara_pacote_com_cve_conhecida(workspace_curto: Path):
    """Regressão: Microsoft.AspNetCore.OpenApi arrastava NU1903 (GHSA-v5pm)."""
    resultado = gen_dotnet.scaffold("P", workspace_curto, executor=_fake_dotnet)
    props = (Path(resultado["output_path"]) / "Directory.Packages.props").read_text(
        encoding="utf-8")
    assert "Microsoft.AspNetCore.OpenApi" not in props
    assert "Microsoft.OpenApi" not in props


# ── Build real (exige SDK) ─────────────────────────────────────────────────

@pytest.mark.skipif(not _dotnet_sdk_disponivel(), reason="SDK .NET 8 ausente no PATH")
def test_verifier_dotnet_compila_o_scaffold_de_verdade(workspace_curto: Path):
    """CA-003 — restore e build com exit code zero."""
    resultado = gen_dotnet.scaffold("P", workspace_curto)

    proc = subprocess.run(
        [sys.executable, str(UTILS / "verify_dotnet_solution.py"),
         "--root", resultado["output_path"], "--json"],
        capture_output=True, text=True, timeout=900, check=False)
    payload = json.loads(proc.stdout)

    assert payload["status"] == "PASS", payload.get("error")
    assert proc.returncode == 0
    assert [phase["name"] for phase in payload["phases"]] == [
        "prereq", "structure", "restore", "build", "test"]


@pytest.mark.skipif(not _dotnet_sdk_disponivel(), reason="SDK .NET 8 ausente no PATH")
def test_verifier_reprova_scaffold_quebrado(workspace_curto: Path):
    """Presença de arquivo não é evidência de compilação."""
    resultado = gen_dotnet.scaffold("P", workspace_curto)
    raiz = Path(resultado["output_path"])
    (raiz / "src" / "Customers" / "AcmeErp.Customers.Api" / "Program.cs").write_text(
        "this is not valid C#;", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(UTILS / "verify_dotnet_solution.py"),
         "--root", str(raiz), "--json"],
        capture_output=True, text=True, timeout=900, check=False)
    payload = json.loads(proc.stdout)

    assert proc.returncode != 0
    assert payload["status"] == "FAIL"
    assert payload["phases"][-1]["name"] == "build"


@pytest.mark.skipif(not _dotnet_sdk_disponivel(), reason="SDK .NET 8 ausente no PATH")
def test_duas_solutions_sao_ambiguidade_e_nao_escolha(workspace_curto: Path):
    """Sintoma clássico de scaffold novo convivendo com legado."""
    resultado = gen_dotnet.scaffold("P", workspace_curto)
    raiz = Path(resultado["output_path"])
    (raiz / "Legado.sln").write_text("x", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(UTILS / "verify_dotnet_solution.py"),
         "--root", str(raiz), "--json"],
        capture_output=True, text=True, timeout=300, check=False)
    payload = json.loads(proc.stdout)

    assert proc.returncode != 0
    assert "esperada exatamente uma solution" in (payload["error"] or "")


def test_verifier_sem_sdk_reprova_em_vez_de_aprovar(workspace_curto: Path, monkeypatch):
    """Toolchain ausente é limitação, nunca aprovação implícita."""
    sys.path.insert(0, str(UTILS))
    import verify_dotnet_solution as verifier

    gen_dotnet.scaffold("P", workspace_curto, executor=_fake_dotnet)
    raiz = (workspace_curto / "projects/P/outputs/tobe/source-code/backend")
    monkeypatch.setattr(verifier.shutil, "which", lambda _: None)

    resultado = verifier.verify(raiz, quiet=True)

    assert resultado["status"] == "FAIL"
    assert resultado["phases"][-1]["name"] == "prereq"


def test_sanitizador_remove_credenciais_do_log():
    sys.path.insert(0, str(UTILS))
    import verify_dotnet_app as vda

    bruto = ("Server=db;Password=Sup3rS3cret;User=sa "
             "ApiKey: abc123def456 Authorization: Bearer eyJhbGciOiJIUzI1NiJ9")
    limpo = vda.sanitize(bruto)

    assert "Sup3rS3cret" not in limpo
    assert "abc123def456" not in limpo
    assert "eyJhbGciOiJIUzI1NiJ9" not in limpo
    assert "***" in limpo
