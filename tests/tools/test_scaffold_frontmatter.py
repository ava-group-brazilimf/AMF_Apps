"""Front-matter como configuração executável — e a allowlist que o torna seguro.

Tornar o front-matter a fonte de `generator`/`verifier` significa executar um
caminho declarado em arquivo de conteúdo. Estes testes travam a allowlist: fora
dela, a execução falha ANTES de qualquer comando rodar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))

import scaffold_frontmatter as fm  # noqa: E402

SCAFFOLDS_DIR = (REPO_ROOT / "src" / "modules" / "ava-fabric-agents"
                 / "tech-stack" / "scaffolds")


# ── Definições reais do repo ───────────────────────────────────────────────

def test_angular_declara_frontend_com_generator_e_verifier():
    d = fm.scaffold_definition_for_stack("angular", SCAFFOLDS_DIR)
    assert d.component_type == "frontend"
    assert d.stack == "angular"
    assert d.generator.name == "f4s_angular_scaffold.py"
    assert d.verifier.name == "verify_angular_app.py"
    assert d.output_path == "source-code/frontend"


def test_dotnet_declara_backend_com_generator_e_verifier():
    d = fm.scaffold_definition_for_stack("dotnet", SCAFFOLDS_DIR)
    assert d.component_type == "backend"
    assert d.generator.name == "f4s_dotnet_scaffold.py"
    assert d.verifier.name == "verify_dotnet_solution.py"
    assert d.output_path == "source-code/backend"


def test_output_path_e_derivado_nunca_declarado():
    """CA-014 — o destino sai do component_type, não de dict nem do Markdown."""
    for stack in ("angular", "dotnet"):
        d = fm.scaffold_definition_for_stack(stack, SCAFFOLDS_DIR)
        assert "output_path" not in d.raw, (
            f"{stack}-scaffold.md declara output_path; ele é calculado")


def test_stack_sem_scaffold_falha_alto():
    """Sem fallback genérico: stack sem receita determinística bloqueia."""
    with pytest.raises(fm.FrontMatterError, match="sem scaffold determinístico"):
        fm.scaffold_definition_for_stack("cobol", SCAFFOLDS_DIR)


# ── Parsing e schema ───────────────────────────────────────────────────────

def _escrever(tmp_path: Path, front: str, nome: str = "x-scaffold.md") -> Path:
    alvo = tmp_path / nome
    alvo.write_text(f"---\n{front}\n---\n\n# corpo\n", encoding="utf-8")
    return alvo


BASE = """component_type: frontend
stack: angular
generator: src/shared/tools/f4s_angular_scaffold.py
verifier: src/shared/utils/verify_angular_app.py
template_path: src/shared/templates/angular-scaffold"""


def test_front_matter_ausente_falha(tmp_path: Path):
    alvo = tmp_path / "a-scaffold.md"
    alvo.write_text("# sem front-matter\n", encoding="utf-8")
    with pytest.raises(fm.FrontMatterError, match="front-matter YAML ausente"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_front_matter_nao_fechado_falha(tmp_path: Path):
    alvo = tmp_path / "a-scaffold.md"
    alvo.write_text("---\nstack: angular\n", encoding="utf-8")
    with pytest.raises(fm.FrontMatterError, match="não fechado"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_campo_obrigatorio_ausente_falha(tmp_path: Path):
    alvo = _escrever(tmp_path, "component_type: frontend\nstack: angular")
    with pytest.raises(fm.FrontMatterError, match="obrigatórios ausentes"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_campo_desconhecido_falha(tmp_path: Path):
    """Typo em configuração executável não pode passar em silêncio."""
    alvo = _escrever(tmp_path, BASE + "\ngenrator: outro.py")
    with pytest.raises(fm.FrontMatterError, match="não reconhecidos"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_stack_incoerente_com_component_type_falha(tmp_path: Path):
    """`stack: angular` + `component_type: backend` geraria front dentro de back."""
    alvo = _escrever(tmp_path, BASE.replace("component_type: frontend",
                                            "component_type: backend"))
    with pytest.raises(fm.FrontMatterError, match="é frontend"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_output_path_divergente_falha(tmp_path: Path):
    """CA-026 — output_path declarado só é aceito se for o canônico."""
    alvo = _escrever(tmp_path, BASE + "\noutput_path: source-code/angular")
    with pytest.raises(Exception, match="output_path|canônico"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_output_path_canonico_e_tolerado(tmp_path: Path):
    alvo = _escrever(tmp_path, BASE + "\noutput_path: source-code/frontend")
    d = fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)
    assert d.output_path == "source-code/frontend"


# ── Allowlist / segurança ──────────────────────────────────────────────────

@pytest.mark.parametrize("caminho", [
    "../../../etc/passwd",
    "src/shared/tools/../../../evil.py",
])
def test_generator_com_traversal_e_rejeitado(tmp_path: Path, caminho: str):
    """CA-015 — falha ANTES de executar qualquer comando."""
    alvo = _escrever(tmp_path, BASE.replace(
        "generator: src/shared/tools/f4s_angular_scaffold.py",
        f"generator: {caminho}"))
    with pytest.raises(fm.FrontMatterError, match="traversal|fora do"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


@pytest.mark.parametrize("caminho", [
    "/usr/bin/python", "C:/Windows/System32/cmd.exe",
])
def test_generator_absoluto_e_rejeitado(tmp_path: Path, caminho: str):
    alvo = _escrever(tmp_path, BASE.replace(
        "generator: src/shared/tools/f4s_angular_scaffold.py",
        f"generator: {caminho}"))
    with pytest.raises(fm.FrontMatterError, match="relativo"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_generator_fora_dos_diretorios_autorizados_e_rejeitado(tmp_path: Path):
    alvo = _escrever(tmp_path, BASE.replace(
        "generator: src/shared/tools/f4s_angular_scaffold.py",
        "generator: ava-pipeline-runner-cli.py"))
    with pytest.raises(fm.FrontMatterError, match="fora dos diretórios autorizados"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_generator_nao_python_e_rejeitado(tmp_path: Path):
    """Front-matter não é vetor para .sh/.ps1/.bat/.exe."""
    script = REPO_ROOT / "src" / "shared" / "tools" / "_probe_scaffold.sh"
    script.write_text("#!/bin/sh\necho x\n", encoding="utf-8")
    try:
        alvo = _escrever(tmp_path, BASE.replace(
            "generator: src/shared/tools/f4s_angular_scaffold.py",
            "generator: src/shared/tools/_probe_scaffold.sh"))
        with pytest.raises(fm.FrontMatterError, match="extensão não autorizada"):
            fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)
    finally:
        script.unlink(missing_ok=True)


def test_generator_inexistente_e_rejeitado(tmp_path: Path):
    alvo = _escrever(tmp_path, BASE.replace(
        "generator: src/shared/tools/f4s_angular_scaffold.py",
        "generator: src/shared/tools/nao_existe.py"))
    with pytest.raises(fm.FrontMatterError, match="não existe"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_template_path_fora_da_allowlist_e_rejeitado(tmp_path: Path):
    alvo = _escrever(tmp_path, BASE.replace(
        "template_path: src/shared/templates/angular-scaffold",
        "template_path: src/shared/tools"))
    with pytest.raises(fm.FrontMatterError, match="fora dos diretórios autorizados"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)


def test_version_source_precisa_ser_nome_de_arquivo(tmp_path: Path):
    alvo = _escrever(tmp_path, BASE + "\nversion_source: ../../etc/passwd")
    with pytest.raises(fm.FrontMatterError, match="nome de arquivo"):
        fm.load_scaffold_definition(alvo, repo_root=REPO_ROOT)
