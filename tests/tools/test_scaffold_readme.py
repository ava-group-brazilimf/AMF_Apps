"""
`outputs/tobe/source-code/README.md` — folha de rosto da árvore gerada pela F4S.

Contrato: depois de frontend E backend nascerem, a fase escreve o README no
`source-code/`, ANTES do baseline — a ordem importa, porque `create_baseline`
faz `git add -A` ali e é assim que o arquivo entra no commit que representa
"o sistema compila".

Roda com o Python do repo:
    python -m pytest tests/tools/test_scaffold_readme.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import scaffold_readme  # noqa: E402
import scaffold_runner  # noqa: E402


def _state(**overrides):
    base = {
        "project": "demo",
        "run_id": "scaffold-abc123",
        "tasks": {
            "T-SCAFFOLD-FRONTEND-001": {
                "component_type": "frontend", "stack": "angular",
                "status": "completed", "attempts": 1,
                "build_status": "succeeded", "verification_status": "succeeded",
            },
            "T-SCAFFOLD-BACKEND-001": {
                "component_type": "backend", "stack": "dotnet",
                "status": "completed", "attempts": 2,
                "build_status": "succeeded", "verification_status": "succeeded",
            },
        },
    }
    base.update(overrides)
    return base


def _components():
    return {
        "frontend": {
            "success": True, "stack": "angular",
            "generation": {"app_name": "demo-spa", "angular_major": 20,
                           "files_written": ["a", "b", "c"], "files_skipped": []},
            "verification": {"warnings": []}, "warnings": [],
        },
        "backend": {
            "success": True, "stack": "dotnet",
            "generation": {"solution": "Demo.sln", "solution_prefix": "Demo",
                           "tfm": "net10.0", "sdk": "10.0.100",
                           "files_written": ["x"] * 79, "files_skipped": []},
            "verification": {"warnings": ["CS0168"]}, "warnings": ["CS0168"],
        },
    }


# ── O arquivo nasce no lugar certo, com o nome certo ────────────────────────

def test_readme_e_escrito_em_source_code(tmp_path):
    destino = scaffold_readme.write_readme(
        tmp_path, "demo", _state(), _components(), bcs=["BC-01", "BC-02"])

    assert destino == tmp_path / "outputs" / "tobe" / "source-code" / "README.md"
    assert destino.is_file()
    assert destino.stat().st_size > 0


def test_diretorio_inexistente_e_criado(tmp_path):
    """A fase pode escrever o README antes de qualquer outra coisa existir ali."""
    destino = scaffold_readme.write_readme(tmp_path, "demo", _state(), {})
    assert destino.is_file()


# ── Conteúdo: descreve os DOIS componentes com o que a fase registrou ──────

def test_readme_descreve_frontend_e_backend(tmp_path):
    texto = scaffold_readme.write_readme(
        tmp_path, "demo", _state(), _components(),
        bcs=["BC-01", "BC-02"]).read_text(encoding="utf-8")

    assert "source-code/frontend" in texto and "angular" in texto
    assert "source-code/backend" in texto and "dotnet" in texto
    # Dados que só o generator conhece — provam que o README lê o resultado
    # real, e não um template fixo.
    assert "Demo.sln" in texto and "net10.0" in texto and "10.0.100" in texto
    assert "demo-spa" in texto
    assert "BC-01" in texto and "BC-02" in texto
    assert "scaffold-abc123" in texto
    assert "79" in texto, "contagem de arquivos gerados do backend"


def test_readme_traz_o_comando_de_build_de_cada_stack(tmp_path):
    texto = scaffold_readme.write_readme(
        tmp_path, "demo", _state(), _components()).read_text(encoding="utf-8")

    assert "dotnet build" in texto
    assert "ng build" in texto


def test_build_command_do_front_matter_vence_o_padrao(tmp_path):
    class _Def:
        build_command = "dotnet build -c Release --nologo"

    texto = scaffold_readme.write_readme(
        tmp_path, "demo", _state(), _components(),
        definitions={"backend": _Def()}).read_text(encoding="utf-8")

    assert "dotnet build -c Release --nologo" in texto


def test_componente_reprovado_aparece_em_destaque(tmp_path):
    estado = _state()
    estado["tasks"]["T-SCAFFOLD-BACKEND-001"].update(
        status="failed", build_status="failed", verification_status="failed",
        error_summary="build: CS0246 tipo nao encontrado")
    componentes = _components()
    componentes["backend"]["success"] = False
    componentes["backend"]["error"] = "build: CS0246 tipo nao encontrado"

    texto = scaffold_readme.write_readme(
        tmp_path, "demo", estado, componentes).read_text(encoding="utf-8")

    assert "Reprovado" in texto and "CS0246" in texto
    assert "❌" in texto, "silêncio num componente reprovado seria lido como ok"


def test_campo_ausente_nao_e_inventado(tmp_path):
    """Stack nova sem `tfm`/`app_name` não pode fazer o README inventar.

    Campo opcional que a stack não tem some da tabela; `Status`, não — tabela
    sem status é lida como "deu certo".
    """
    estado = _state()
    estado["tasks"]["T-SCAFFOLD-BACKEND-001"] = {
        "component_type": "backend", "stack": "fastapi",
    }
    texto = scaffold_readme.write_readme(
        tmp_path, "demo", estado,
        {"backend": {"success": True, "stack": "fastapi", "generation": {}}}
    ).read_text(encoding="utf-8")

    assert "net10.0" not in texto and "Target framework" not in texto
    assert "Restore" not in texto, "campo que a stack não tem some da tabela"
    assert "não registrado" in texto, "status ausente precisa ser dito"


def test_baseline_sem_sha_explica_em_vez_de_dizer_que_nao_existe(tmp_path):
    """O SHA do commit que INCLUI o arquivo não cabe dentro dele."""
    texto = scaffold_readme.write_readme(
        tmp_path, "demo", _state(), _components()).read_text(encoding="utf-8")

    assert "git -C source-code log -1" in texto
    assert "não criado" not in texto


def test_baseline_bloqueado_diz_o_motivo(tmp_path):
    texto = scaffold_readme.write_readme(
        tmp_path, "demo", _state(), _components(),
        baseline={"error": "componente reprovado com risco aceito"},
    ).read_text(encoding="utf-8")

    assert "não** criado" in texto
    assert "componente reprovado com risco aceito" in texto
    assert "coder" in texto, "precisa dizer que os coders seguem bloqueados"


def test_baseline_com_sha_mostra_o_commit(tmp_path):
    texto = scaffold_readme.write_readme(
        tmp_path, "demo", _state(), _components(),
        baseline={"commit_sha": "0123456789abcdef0123"},
    ).read_text(encoding="utf-8")

    assert "0123456789ab" in texto


# ── Idempotência: é projeção de estado, não documento acumulativo ──────────

def test_reescrita_e_idempotente_e_nao_acumula(tmp_path):
    primeiro = scaffold_readme.write_readme(tmp_path, "demo", _state(), _components())
    conteudo_1 = primeiro.read_text(encoding="utf-8")
    segundo = scaffold_readme.write_readme(tmp_path, "demo", _state(), _components())
    conteudo_2 = segundo.read_text(encoding="utf-8")

    assert primeiro == segundo
    # Só o carimbo de tempo pode divergir entre duas execuções.
    sem_data_1 = [l for l in conteudo_1.splitlines() if "Gerado em" not in l]
    sem_data_2 = [l for l in conteudo_2.splitlines() if "Gerado em" not in l]
    assert sem_data_1 == sem_data_2
    assert conteudo_2.count("# demo — código-fonte gerado") == 1


def test_readme_de_outro_autor_e_preservado(tmp_path):
    """`nopcommerce-01` tem 248 linhas escritas por agente de fase posterior.

    Re-executar a F4S é a primeira coisa que se recomenda quando o passo
    estoura — e não pode custar aquela documentação.
    """
    destino = tmp_path / "outputs" / "tobe" / "source-code" / "README.md"
    destino.parent.mkdir(parents=True)
    destino.write_text("# escrito à mão\n\ndocker-compose, pipeline, auth",
                       encoding="utf-8")

    scaffold_readme.write_readme(tmp_path, "demo", _state(), _components())

    assert destino.read_text(encoding="utf-8").startswith("# escrito à mão")


def test_force_substitui_readme_de_outro_autor(tmp_path):
    destino = tmp_path / "outputs" / "tobe" / "source-code" / "README.md"
    destino.parent.mkdir(parents=True)
    destino.write_text("# escrito à mão", encoding="utf-8")

    scaffold_readme.write_readme(tmp_path, "demo", _state(), _components(),
                                 force=True)

    texto = destino.read_text(encoding="utf-8")
    assert "escrito à mão" not in texto
    assert scaffold_readme.SENTINELA in texto


def test_o_proprio_readme_e_regenerado_sem_force(tmp_path):
    """O que é nosso é projeção de estado: reescreve sempre."""
    primeiro = scaffold_readme.write_readme(tmp_path, "demo", _state(), _components())
    primeiro.write_text(primeiro.read_text(encoding="utf-8") + "\nsujeira",
                        encoding="utf-8")

    scaffold_readme.write_readme(tmp_path, "demo", _state(), _components())

    texto = primeiro.read_text(encoding="utf-8")
    assert "sujeira" not in texto
    assert "é reescrito por inteiro" in texto, "o arquivo tem de avisar isso"


def test_sentinela_e_invisivel_no_markdown(tmp_path):
    destino = scaffold_readme.write_readme(tmp_path, "demo", _state(), _components())
    texto = destino.read_text(encoding="utf-8")

    assert texto.startswith(scaffold_readme.SENTINELA)
    assert scaffold_readme.SENTINELA.startswith("<!--"), "comentário HTML não renderiza"
    assert scaffold_readme.foi_gerado_por_nos(destino)


def test_quebra_de_linha_e_lf(tmp_path):
    destino = scaffold_readme.write_readme(tmp_path, "demo", _state(), _components())
    assert b"\r\n" not in destino.read_bytes()


# ── A fase chama o gerador entre os componentes e o baseline ──────────────

def test_fase_escreve_o_readme_antes_do_baseline():
    fonte = (TOOLS_DIR / "scaffold_runner.py").read_text(encoding="utf-8")
    corpo = fonte[fonte.index("def run_scaffold_phase"):]

    chamada = corpo.index("scaffold_readme.write_readme")
    baseline = corpo.index("create_baseline(project_dir, state)")
    loop = corpo.index("for component_type in COMPONENT_TYPES:")

    assert loop < chamada < baseline, (
        "o README tem de ser escrito DEPOIS dos dois componentes e ANTES do "
        "baseline — `create_baseline` faz `git add -A` em source-code/")


def test_falha_ao_escrever_readme_nao_derruba_a_fase(monkeypatch, tmp_path):
    """Documentação não é artefato de contrato: disco cheio não mata a F4S."""
    fonte = (TOOLS_DIR / "scaffold_runner.py").read_text(encoding="utf-8")
    trecho = fonte[fonte.index("scaffold_readme.write_readme") - 400:
                   fonte.index("scaffold_readme.write_readme") + 900]

    assert "try:" in trecho and "except OSError" in trecho


def test_runner_expoe_o_caminho_do_readme_no_resultado():
    fonte = (TOOLS_DIR / "scaffold_runner.py").read_text(encoding="utf-8")
    assert 'saida["readme"]' in fonte
