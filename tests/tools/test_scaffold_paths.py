"""Resolução de caminho do scaffold: responsabilidade decide, tecnologia não.

O defeito que estes testes travam: o repo tinha duas convenções vivas —
`source-code/{stack}/` no `f4s_phase_runner.py` e `source-code/backend|frontend/`
no `ava-stack-orchestrator`. O mesmo projeto podia terminar com código nos dois
lugares, e nenhum verificador olhava os dois.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))

import scaffold_paths as sp  # noqa: E402


# ── Positivos: stack não muda o diretório ──────────────────────────────────

@pytest.mark.parametrize("stack", ["angular", "react", "vue", "svelte", "blazor"])
def test_toda_stack_de_frontend_resolve_para_frontend(stack: str):
    assert sp.component_type_for_stack(stack) == "frontend"
    assert sp.resolve_source_code_path(
        sp.component_type_for_stack(stack)) == "source-code/frontend"


@pytest.mark.parametrize("stack", ["dotnet", "java", "spring-boot", "node",
                                   "nestjs", "python", "fastapi", "go", "gin"])
def test_toda_stack_de_backend_resolve_para_backend(stack: str):
    assert sp.component_type_for_stack(stack) == "backend"
    assert sp.resolve_source_code_path(
        sp.component_type_for_stack(stack)) == "source-code/backend"


def test_trocar_de_stack_nao_muda_o_diretorio_raiz():
    """CA-021 — migrar Angular→React ou .NET→Java preserva o caminho."""
    for antes, depois in (("angular", "react"), ("dotnet", "java")):
        assert (sp.resolve_source_code_path(sp.component_type_for_stack(antes))
                == sp.resolve_source_code_path(sp.component_type_for_stack(depois)))


def test_component_type_invalido_falha_antes_de_gerar():
    for valor in ("", None, "fullstack", "angular", "dotnet", "shared"):
        with pytest.raises(sp.ScaffoldPathError):
            sp.resolve_source_code_path(valor)


def test_stack_desconhecida_falha_em_vez_de_adivinhar():
    with pytest.raises(sp.ScaffoldPathError, match="component_type"):
        sp.component_type_for_stack("cobol-web")


# ── Negativos: destinos proibidos ──────────────────────────────────────────

@pytest.fixture()
def tobe(tmp_path: Path) -> Path:
    raiz = tmp_path / "projects" / "P" / "outputs" / "tobe"
    (raiz / "source-code").mkdir(parents=True)
    return raiz


@pytest.mark.parametrize("proibido", [
    "source-code/angular", "source-code/dotnet", "source-code/java",
    "source-code/react", "source-code/vue", "source-code/node",
    "source-code/python", "source-code/go", "source-code/stacks",
])
def test_diretorio_derivado_da_tecnologia_e_rejeitado(tobe: Path, proibido: str):
    """CA-022 — nome de linguagem/framework nunca é raiz de componente."""
    componente = "frontend" if proibido.split("/")[-1] in {
        "angular", "react", "vue"} else "backend"
    with pytest.raises(sp.ScaffoldPathError, match="tecnologia|não corresponde"):
        sp.validate_output_dir(tobe / proibido, componente, tobe)


def test_caminho_absoluto_fora_do_projeto_e_rejeitado(tobe: Path, tmp_path: Path):
    with pytest.raises(sp.ScaffoldPathError, match="fora de source-code"):
        sp.validate_output_dir(tmp_path / "outro" / "frontend", "frontend", tobe)


@pytest.mark.parametrize("traversal", [
    "../source-code/frontend",
    "source-code/frontend/../../out",
    "source-code/../../frontend",
])
def test_path_traversal_e_rejeitado(tobe: Path, traversal: str):
    with pytest.raises(sp.ScaffoldPathError):
        sp.validate_output_dir(tobe / traversal, "frontend", tobe)


def test_subdiretorio_nao_e_raiz_de_componente(tobe: Path):
    with pytest.raises(sp.ScaffoldPathError, match="raiz de um componente"):
        sp.validate_output_dir(tobe / "source-code/frontend/angular", "frontend", tobe)


def test_backend_nao_pode_apontar_para_frontend(tobe: Path):
    with pytest.raises(sp.ScaffoldPathError, match="não corresponde"):
        sp.validate_output_dir(tobe / "source-code/frontend", "backend", tobe)


@pytest.mark.skipif(sys.platform == "win32",
                    reason="symlink exige privilégio elevado no Windows")
def test_symlink_para_fora_do_projeto_e_rejeitado(tobe: Path, tmp_path: Path):
    externo = tmp_path / "externo"
    externo.mkdir()
    (tobe / "source-code" / "frontend").symlink_to(externo, target_is_directory=True)
    with pytest.raises(sp.ScaffoldPathError, match="symlink"):
        sp.validate_output_dir(tobe / "source-code/frontend", "frontend", tobe)


# ── output_path declarado (compatibilidade) ────────────────────────────────

def test_output_path_declarado_precisa_bater_com_component_type():
    assert sp.assert_declared_output_path("source-code/frontend", "frontend")
    assert sp.assert_declared_output_path("source-code/backend", "backend")


@pytest.mark.parametrize("declarado,componente", [
    ("source-code/angular", "frontend"),
    ("source-code/dotnet", "backend"),
    ("source-code/frontend", "backend"),
    ("src/frontend", "frontend"),
])
def test_output_path_divergente_e_erro_de_configuracao(declarado, componente):
    """CA-026 — front-matter não sobrescreve a convenção."""
    with pytest.raises(sp.ScaffoldPathError):
        sp.assert_declared_output_path(declarado, componente)


# ── Detecção de legado ─────────────────────────────────────────────────────

def test_diretorio_legado_e_detectado_mas_nao_movido(tobe: Path):
    legado = tobe / "source-code" / "angular"
    (legado / "src").mkdir(parents=True)
    (legado / "src" / "main.ts").write_text("//", encoding="utf-8")

    achados = sp.detect_legacy_output_dirs(tobe)

    assert [a["name"] for a in achados] == ["angular"]
    assert achados[0]["canonical"] == "source-code/frontend"
    assert achados[0]["has_files"] is True
    # A migração é rotina explícita: detectar não move nada.
    assert legado.is_dir() and (legado / "src" / "main.ts").is_file()


def test_git_e_infra_nao_sao_confundidos_com_legado(tobe: Path):
    """O repo do baseline vive em `source-code/` — não é output de stack."""
    (tobe / "source-code" / ".git").mkdir()
    (tobe / "source-code" / "frontend").mkdir()
    assert sp.detect_legacy_output_dirs(tobe) == []
    assert sp.files_outside_canonical(tobe) == []


def test_legado_com_conteudo_bloqueia_o_baseline(tobe: Path):
    legado = tobe / "source-code" / "dotnet"
    legado.mkdir(parents=True)
    (legado / "a.sln").write_text("x", encoding="utf-8")
    assert sp.files_outside_canonical(tobe)


# ── Regressão de código-fonte ──────────────────────────────────────────────

def test_detector_de_antipadrao_reconhece_caminho_por_stack():
    exemplos = [
        'root = tobe / f"source-code/{stack}"',
        'root = Path("source-code") / stack',
        'os.path.join("source-code", target_stack)',
    ]
    for trecho in exemplos:
        assert sp.find_stack_path_antipatterns(trecho), trecho
    assert not sp.find_stack_path_antipatterns(
        'root = tobe / resolve_source_code_path(component_type)')


def test_nenhuma_tool_de_scaffold_monta_caminho_por_stack():
    """Varre o código operacional em busca de `source-code/{stack}`."""
    alvos = [
        REPO_ROOT / "src" / "shared" / "tools" / "scaffold_runner.py",
        REPO_ROOT / "src" / "shared" / "tools" / "scaffold_paths.py",
        REPO_ROOT / "src" / "shared" / "tools" / "f4s_angular_scaffold.py",
        REPO_ROOT / "src" / "shared" / "tools" / "f4s_dotnet_scaffold.py",
        REPO_ROOT / "src" / "shared" / "tools" / "f4s_phase_runner.py",
        REPO_ROOT / "src" / "shared" / "utils" / "verify_dotnet_app.py",
    ]
    ofensores: list[str] = []
    for alvo in alvos:
        if not alvo.is_file():
            continue
        texto = alvo.read_text(encoding="utf-8")
        if alvo.name == "scaffold_paths.py":
            # Este arquivo DECLARA os antipadrões para poder detectá-los.
            continue
        achados = sp.find_stack_path_antipatterns(texto)
        if achados:
            ofensores.append(f"{alvo.name}: {achados}")
    assert not ofensores, (
        "caminho derivado da stack reintroduzido: " + "; ".join(ofensores))
