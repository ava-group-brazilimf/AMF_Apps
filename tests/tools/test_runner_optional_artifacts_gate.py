"""
Gate de artefatos OPCIONAIS ausentes (`ava-pipeline-runner-cli.py`).

Este gate existe por uma falha medida: na F3 do `nopcommerce-02`, o
`ava-prototype` encontrou `design-system.md` e `user-journeys.md` ausentes,
imprimiu "Continuar mesmo sem os artefatos opcionais? [sim/não]" e encerrou a
resposta. A chamada é single-shot — ninguém podia responder —, então a fase
terminou em 12,5 s com 0 artefatos e ainda assim contabilizada como executada.

A decisão passou a ser tomada no runner, antes do despacho. O que estes testes
travam é a regra que impede a repetição daquilo:

* O SILÊNCIO APROVA. Prazo estourado, ou console inexistente, gera protótipo —
  nunca cancela. Cancelar exige um "não" digitado por alguém.
* A aprovação viaja no prompt. Sem a diretriz, o agente reexecuta o pre-flight
  do próprio corpo e volta a perguntar — o bug de novo, com outra roupa.
* O prazo é de 60s, e é o que vai para `safe_input_timeout`.

Roda com o Python do repo:
    python -m pytest tests/tools/test_runner_optional_artifacts_gate.py -q
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PY = REPO_ROOT / "ava-pipeline-runner-cli.py"

_FUNCOES = ("_opcionais_ausentes", "_painel_opcionais",
            "confirmar_opcionais_ausentes")
_CONSTANTES = ("_OPCIONAIS_TIMEOUT_S", "_ARTEFATOS_OPCIONAIS",
               "_DIRETRIZ_OPCIONAIS")

#: Os três opcionais do `ava-prototype` que o pre-flight do agente confere.
#: `api-map.md` entra na lista do runner mas não neste fixture: ele tem
#: fallback próprio para `openapi/*.yaml` e não muda a decisão.
_OPCIONAIS_PROTOTYPE = ("outputs/tobe/docs/bounded-context-map.md",
                        "outputs/tobe/docs/design-system.md",
                        "outputs/tobe/docs/user-journeys.md",
                        "outputs/tobe/docs/api-map.md")


def _compilar() -> object:
    """Compila só o gate. O runner importa `msvcrt` no topo e monta estado
    global ao carregar; importá-lo inteiro num teste não é viável."""
    arvore = ast.parse(RUNNER_PY.read_text(encoding="utf-8"))
    corpo = []
    for no in arvore.body:
        if isinstance(no, ast.FunctionDef) and no.name in _FUNCOES:
            corpo.append(no)
        elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name) \
                and no.target.id in _CONSTANTES:
            corpo.append(no)
        elif isinstance(no, ast.Assign) and any(
                isinstance(alvo, ast.Name) and alvo.id in _CONSTANTES
                for alvo in no.targets):
            corpo.append(no)
    encontradas = {no.name for no in corpo if isinstance(no, ast.FunctionDef)}
    assert encontradas == set(_FUNCOES), sorted(set(_FUNCOES) - encontradas)
    return compile(ast.Module(body=corpo, type_ignores=[]), "<runner>", "exec")


_CODIGO = _compilar()


@pytest.fixture
def ns(tmp_path: Path):
    """Namespace novo por teste, com WORKSPACE apontando para um projeto vazio.

    Reexecutar o código compilado a cada teste é o que garante isolamento: as
    funções compartilham UM dict de globals, que é o próprio namespace.
    """
    (tmp_path / "projects" / "acme" / "outputs" / "tobe" / "docs").mkdir(parents=True)
    local: dict = {
        "sys": sys, "Path": Path, "WORKSPACE": tmp_path,
        "BOLD": "", "DIM": "", "RESET": "", "RED": "", "YELLOW": "",
        "GREEN": "", "CYAN": "",
    }
    exec(_CODIGO, local)
    local["_tmp"] = tmp_path
    return local


def _criar(ns: dict, *relativos: str, conteudo: str = "conteudo") -> None:
    raiz = ns["_tmp"] / "projects" / "acme"
    for rel in relativos:
        alvo = raiz / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")


def _teclado(ns: dict, resposta, *, prazos: list | None = None):
    """Dubla o prompt com prazo. `None` = ninguém respondeu a tempo.

    Uma exceção como `resposta` é levantada — é assim que se testa o console
    ausente (`EOFError`) e o Ctrl+C (`KeyboardInterrupt`).
    """
    registrados = prazos if prazos is not None else []

    def _safe_input_timeout(prompt: str, timeout_s: int):
        registrados.append(timeout_s)
        if isinstance(resposta, type) and issubclass(resposta, BaseException):
            raise resposta()
        return resposta

    ns["safe_input_timeout"] = _safe_input_timeout
    return registrados


# ── Detecção ─────────────────────────────────────────────────────────────────

def test_todos_presentes_nao_pergunta_nada(ns):
    _criar(ns, *_OPCIONAIS_PROTOTYPE)

    def _nunca(prompt, timeout_s):
        raise AssertionError("não deveria perguntar com todos os opcionais presentes")

    ns["safe_input_timeout"] = _nunca

    prosseguir, diretriz = ns["confirmar_opcionais_ausentes"](
        "ava-prototype", "acme", "F3")

    assert prosseguir is True
    assert diretriz == ""


def test_arquivo_vazio_conta_como_ausente(ns):
    _criar(ns, *_OPCIONAIS_PROTOTYPE)
    _criar(ns, "outputs/tobe/docs/design-system.md", conteudo="")

    ausentes = ns["_opcionais_ausentes"]("ava-prototype", "acme")

    assert [rel for rel, _ in ausentes] == ["outputs/tobe/docs/design-system.md"]


def test_agente_sem_opcionais_declarados_passa_direto(ns):
    prosseguir, diretriz = ns["confirmar_opcionais_ausentes"](
        "ava-asis-documentation", "acme", "F1d")

    assert (prosseguir, diretriz) == (True, "")


# ── O silêncio aprova ────────────────────────────────────────────────────────

def test_prazo_estourado_aprova_e_gera(ns):
    """O caso do nopcommerce-02: ninguém responde e a esteira SEGUE gerando."""
    prazos = _teclado(ns, None)

    prosseguir, diretriz = ns["confirmar_opcionais_ausentes"](
        "ava-prototype", "acme", "F3")

    assert prosseguir is True
    assert "decurso de prazo" in diretriz
    assert prazos == [60], "o prazo do prompt tem de ser o de 60s"


def test_prazo_e_o_declarado_na_constante(ns):
    prazos = _teclado(ns, None)
    ns["confirmar_opcionais_ausentes"]("ava-prototype", "acme", "F3")

    assert ns["_OPCIONAIS_TIMEOUT_S"] == 60
    assert prazos == [ns["_OPCIONAIS_TIMEOUT_S"]]


def test_sem_console_aprova_em_vez_de_travar(ns):
    _teclado(ns, EOFError)

    prosseguir, diretriz = ns["confirmar_opcionais_ausentes"](
        "ava-prototype", "acme", "F3")

    assert prosseguir is True
    assert diretriz


def test_enter_vazio_aprova(ns):
    """`""` é alguém apertando Enter — a ação default é seguir, não cancelar."""
    _teclado(ns, "")

    prosseguir, _ = ns["confirmar_opcionais_ausentes"](
        "ava-prototype", "acme", "F3")

    assert prosseguir is True


# ── Recusa explícita ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("resposta", ["n", "N", "nao", "não", " NÃO "])
def test_nao_digitado_cancela_a_fase(ns, resposta):
    _teclado(ns, resposta)

    prosseguir, diretriz = ns["confirmar_opcionais_ausentes"](
        "ava-prototype", "acme", "F3")

    assert prosseguir is False
    assert diretriz == ""


def test_ctrl_c_cancela(ns):
    _teclado(ns, KeyboardInterrupt)

    prosseguir, diretriz = ns["confirmar_opcionais_ausentes"](
        "ava-prototype", "acme", "F3")

    assert (prosseguir, diretriz) == (False, "")


@pytest.mark.parametrize("resposta", ["s", "S", "sim", "SIM"])
def test_sim_digitado_aprova_com_autoria(ns, resposta):
    _teclado(ns, resposta)

    prosseguir, diretriz = ns["confirmar_opcionais_ausentes"](
        "ava-prototype", "acme", "F3")

    assert prosseguir is True
    assert "operador" in diretriz


# ── A diretriz que vai no prompt ─────────────────────────────────────────────

def test_diretriz_lista_apenas_os_ausentes(ns):
    _criar(ns, "outputs/tobe/docs/bounded-context-map.md",
           "outputs/tobe/docs/api-map.md")
    _teclado(ns, None)

    _, diretriz = ns["confirmar_opcionais_ausentes"]("ava-prototype", "acme", "F3")

    assert "design-system.md" in diretriz
    assert "user-journeys.md" in diretriz
    assert "bounded-context-map.md" not in diretriz
    assert "api-map.md" not in diretriz


def test_diretriz_proibe_a_pergunta_que_travou_a_f3(ns):
    _teclado(ns, None)

    _, diretriz = ns["confirmar_opcionais_ausentes"]("ava-prototype", "acme", "F3")

    assert "PRE-FLIGHT JÁ RESOLVIDO PELO RUNNER" in diretriz
    assert "NÃO exiba a pergunta" in diretriz
    assert "PROSSEGUIR COM AVISOS" in diretriz


# ── Ligação com o despacho ───────────────────────────────────────────────────

def _corpo_de(nome: str) -> ast.FunctionDef:
    arvore = ast.parse(RUNNER_PY.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == nome:
            return no
    raise AssertionError(f"função {nome} não encontrada no runner")


def test_run_step_consulta_o_gate_antes_de_despachar():
    """Gate desligado do despacho é gate que não protege nada."""
    corpo = _corpo_de("run_step")
    chamadas = [no.func.id for no in ast.walk(corpo)
                if isinstance(no, ast.Call) and isinstance(no.func, ast.Name)]

    assert "confirmar_opcionais_ausentes" in chamadas
    assert chamadas.index("confirmar_opcionais_ausentes") < chamadas.index("_dispatch_model")


def test_system_prompt_proibe_perguntar():
    """A regra geral: nenhum agente pode encerrar aguardando resposta."""
    fonte = ast.get_source_segment(
        RUNNER_PY.read_text(encoding="utf-8"), _corpo_de("build_system_prompt"))

    assert "MODO NÃO-INTERATIVO" in fonte
    assert "NÃO faça perguntas" in fonte
