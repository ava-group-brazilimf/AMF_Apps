"""
Testes do gate de aprovação humana no lado do runner (`ava-pipeline-runner-cli.py`).

O runner é um script de ~5000 linhas que importa `msvcrt` no topo e monta estado
global ao carregar — importá-lo num teste não é viável. As funções sob teste são
extraídas por AST e executadas contra um namespace com o teclado e o subprocesso
substituídos. É o mesmo recorte usado para verificar `_degrade_phase`.

O que estes testes protegem é a assimetria entre os modos, que é a decisão de
desenho mais fácil de quebrar sem perceber:

* MANUAL   — há uma pessoa a quem perguntar; a decisão dela vale, inclusive para
             parar a esteira. Assinatura anônima não passa.
* AUTOMÁTICO — não há; perguntar é cortesia com prazo, e o silêncio vira
             `auto_acknowledged`. NUNCA trava.

Roda com o Python do repo:
    python -m pytest tests/tools/test_runner_approval_gate.py -q
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PY = REPO_ROOT / "ava-pipeline-runner-cli.py"

_FUNCOES = (
    "_ler_gate_aprovacao", "_registrar_decisao", "_painel_aprovacao",
    "_coletar_identidade", "_solicitar_aprovacao",
    "_consumir_linha", "safe_input_timeout",
)
_CONSTANTES = ("_APROVACAO_TIMEOUT_S",)


def _compilar() -> object:
    """Compila só as funções do gate, uma vez, para reexecutar por teste."""
    arvore = ast.parse(RUNNER_PY.read_text(encoding="utf-8"))
    corpo = [
        no for no in arvore.body
        if (isinstance(no, ast.FunctionDef) and no.name in _FUNCOES)
        or (isinstance(no, ast.Assign) and any(
            isinstance(alvo, ast.Name) and alvo.id in _CONSTANTES
            for alvo in no.targets))
    ]
    encontradas = {no.name for no in corpo if isinstance(no, ast.FunctionDef)}
    assert encontradas == set(_FUNCOES), sorted(set(_FUNCOES) - encontradas)
    return compile(ast.Module(body=corpo, type_ignores=[]), "<runner>", "exec")


_CODIGO = _compilar()


@pytest.fixture
def ns():
    """Namespace novo por teste.

    Reexecutar o código compilado a cada teste é o que garante isolamento: as
    funções compartilham UM dict de globals, e ele é o próprio namespace. Um
    `dict(...)` compartilhado entre testes deixava o dublê de teclado de um
    teste visível para o seguinte.

    Como `fn.__globals__ is ns`, trocar uma chave do dict já redireciona todas
    as chamadas — não é preciso mexer nos call sites.
    """
    local: dict = {
        "json": json, "sys": sys, "subprocess": subprocess, "Path": Path,
        "WORKSPACE": REPO_ROOT,
        "BOLD": "", "DIM": "", "RESET": "", "RED": "", "YELLOW": "",
        "GREEN": "", "CYAN": "",
    }
    exec(_CODIGO, local)
    local["_decisoes"] = []

    def _registrar(project, decisao, *, nome="", papel="", modo="manual",
                   fingerprint=""):
        local["_decisoes"].append({"decisao": decisao, "nome": nome,
                                   "papel": papel, "modo": modo,
                                   "fingerprint": fingerprint})
        return local.get("_registro_falha") is not True

    local["_registrar_decisao"] = _registrar
    return local


def _teclado(ns: dict, respostas: list, *, timeout: list | None = None) -> None:
    """Enfileira o que o operador digita. `None` = estourou o prazo."""
    fila = list(respostas)
    fila_timeout = list(timeout if timeout is not None else respostas)

    def _safe_input(prompt: str) -> str:
        assert fila, f"prompt inesperado sem resposta enfileirada: {prompt!r}"
        return fila.pop(0)

    def _safe_input_timeout(prompt: str, timeout_s: int):
        assert fila_timeout, f"prompt inesperado: {prompt!r}"
        return fila_timeout.pop(0)

    ns["safe_input"] = _safe_input
    ns["safe_input_timeout"] = _safe_input_timeout


_GATE = {
    "project": "acme",
    "verdict": "APPROVED_WITH_FINDINGS",
    "fingerprint": "sha256:abc",
    "triggers": [{"code": "HIGH_SEVERITY_FINDINGS", "detail": "2 achados"}],
    "blockers": [
        {"id": "NORM-001", "severity": "critical", "summary": "CMK não definido",
         "evidence": "spec.md § 9", "remediation": "Tech Lead"},
    ],
}


# ── Modo manual ──────────────────────────────────────────────────────────────

def test_manual_aprovado_registra_nome_e_papel(ns, capsys):
    _teclado(ns, ["S", "Rafael Almeida", "Tech Lead"])

    assert ns["_solicitar_aprovacao"]("acme", _GATE, False) is True

    assert ns["_decisoes"] == [{"decisao": "approve", "nome": "Rafael Almeida",
                                "papel": "Tech Lead", "modo": "manual",
                                "fingerprint": "sha256:abc"}]


def test_manual_recusado_para_a_esteira(ns):
    _teclado(ns, ["N", "Ana Souza", "QA Lead"])

    assert ns["_solicitar_aprovacao"]("acme", _GATE, False) is False

    assert ns["_decisoes"][0]["decisao"] == "reject"
    assert ns["_decisoes"][0]["nome"] == "Ana Souza"


def test_manual_insiste_ate_nome_valido(ns):
    """Assinatura anônima não registra responsabilidade — o prompt reinsiste."""
    _teclado(ns, ["S", "", "R", "Rafael", "Tech Lead"])

    assert ns["_solicitar_aprovacao"]("acme", _GATE, False) is True

    assert ns["_decisoes"][0]["nome"] == "Rafael"


def test_manual_resposta_invalida_repergunta(ns):
    _teclado(ns, ["talvez", "x", "S", "Rafael", "TL"])

    assert ns["_solicitar_aprovacao"]("acme", _GATE, False) is True


def test_manual_falha_de_registro_nao_libera_a_f4(ns):
    """Se a decisão não pôde ser gravada, não há assinatura — logo, não libera."""
    _teclado(ns, ["S", "Rafael", "TL"])
    ns["_registro_falha"] = True

    assert ns["_solicitar_aprovacao"]("acme", _GATE, False) is False


def test_manual_interrupcao_nao_aprova(ns):
    def _boom(prompt):
        raise KeyboardInterrupt

    ns["safe_input"] = _boom

    assert ns["_solicitar_aprovacao"]("acme", _GATE, False) is False
    assert ns["_decisoes"] == []


# ── Modo automático ──────────────────────────────────────────────────────────

def test_auto_sem_ninguem_no_teclado_segue_sem_travar(ns):
    """O requisito central do modo automático: nunca pendura, nunca bloqueia."""
    _teclado(ns, [], timeout=[None])

    assert ns["_solicitar_aprovacao"]("acme", _GATE, True) is True

    assert ns["_decisoes"] == [{"decisao": "acknowledge", "nome": "", "papel": "",
                                "modo": "auto", "fingerprint": "sha256:abc"}]


def test_auto_com_dados_no_prazo_assina_nominalmente(ns):
    _teclado(ns, [], timeout=["Rafael Almeida", "Tech Lead"])

    assert ns["_solicitar_aprovacao"]("acme", _GATE, True) is True

    assert ns["_decisoes"][0]["decisao"] == "approve"
    assert ns["_decisoes"][0]["modo"] == "auto"
    assert ns["_decisoes"][0]["nome"] == "Rafael Almeida"


def test_auto_com_nome_e_papel_em_branco_reconhece(ns):
    """Enter vazio não é assinatura — cai no reconhecimento automático."""
    _teclado(ns, [], timeout=["Rafael", None])

    assert ns["_solicitar_aprovacao"]("acme", _GATE, True) is True

    assert ns["_decisoes"] == [{"decisao": "acknowledge", "nome": "", "papel": "",
                                "modo": "auto", "fingerprint": "sha256:abc"}]


def test_auto_com_falha_de_registro_nominal_cai_no_reconhecimento(ns):
    """Nem uma falha de gravação pode travar a esteira em modo automático."""
    _teclado(ns, [], timeout=["Rafael", "TL"])
    ns["_registro_falha"] = True

    assert ns["_solicitar_aprovacao"]("acme", _GATE, True) is True

    assert [d["decisao"] for d in ns["_decisoes"]] == ["approve", "acknowledge"]


# ── Painel ───────────────────────────────────────────────────────────────────

def test_painel_mostra_os_achados_nos_dois_modos(ns, capsys):
    """Dar ciência é o ponto; o modo só muda o que acontece depois."""
    _teclado(ns, [], timeout=[None])
    ns["_solicitar_aprovacao"]("acme", _GATE, True)
    auto = capsys.readouterr().out

    _teclado(ns, ["N", "Ana", "QA"])
    ns["_solicitar_aprovacao"]("acme", _GATE, False)
    manual = capsys.readouterr().out

    for saida in (auto, manual):
        assert "NORM-001" in saida
        assert "CMK não definido" in saida
        assert "HIGH_SEVERITY_FINDINGS" in saida


# ── Leitura do relatório da tool ─────────────────────────────────────────────

def test_ler_gate_devolve_none_quando_o_relatorio_nao_existe(ns, tmp_path,
                                                             monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert ns["_ler_gate_aprovacao"]("inexistente") is None


def test_ler_gate_devolve_none_quando_o_json_esta_corrompido(ns, tmp_path,
                                                             monkeypatch):
    monkeypatch.chdir(tmp_path)
    destino = tmp_path / "projects" / "acme" / "outputs" / "tobe" / "speckit"
    destino.mkdir(parents=True)
    (destino / "compliance-gate.json").write_text("{ nao json", encoding="utf-8")

    assert ns["_ler_gate_aprovacao"]("acme") is None


def test_ler_gate_le_o_relatorio_da_wave6c(ns, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    destino = tmp_path / "projects" / "acme" / "outputs" / "tobe" / "speckit"
    destino.mkdir(parents=True)
    (destino / "compliance-gate.json").write_text(
        json.dumps({"decision_pending": True, "fingerprint": "sha256:x"}),
        encoding="utf-8")

    assert ns["_ler_gate_aprovacao"]("acme")["decision_pending"] is True


# ── safe_input_timeout ───────────────────────────────────────────────────────
# O prazo vale só até a PRIMEIRA tecla. Quem começou a digitar não pode ter o
# nome cortado no meio por um cronômetro — sem isso, um sobrenome longo vira
# assinatura truncada, que é pior que assinatura nenhuma.

class _TecladoFalso:
    """Substitui `msvcrt`: entrega teclas depois de N sondagens sem tecla."""

    def __init__(self, teclas: str, atraso: int = 0) -> None:
        self._teclas = list(teclas)
        self._atraso = atraso
        self.sondagens = 0

    def kbhit(self) -> bool:
        self.sondagens += 1
        return self.sondagens > self._atraso and bool(self._teclas)

    def getwch(self) -> str:
        return self._teclas.pop(0)


class _RelogioFalso:
    """`time.monotonic` que avança 1s por chamada; `sleep` não dorme."""

    def __init__(self) -> None:
        self.agora = 0.0

    def monotonic(self) -> float:
        self.agora += 1.0
        return self.agora

    def sleep(self, _segundos: float) -> None:
        return None


def _com_teclado(ns: dict, teclado) -> dict:
    """Injeta o teclado e o relógio falsos no namespace do teste."""
    ns["msvcrt"] = teclado
    ns["time"] = _RelogioFalso()
    return ns


def test_timeout_sem_ninguem_digitando_devolve_none(ns, capsys):
    local = _com_teclado(ns, _TecladoFalso("", atraso=999))

    assert local["safe_input_timeout"]("Nome: ", 3) is None


def test_linha_completa_quando_alguem_digita(ns, capsys):
    local = _com_teclado(ns, _TecladoFalso("Rafael Almeida\r"))

    assert local["safe_input_timeout"]("Nome: ", 30) == "Rafael Almeida"


def test_prazo_nao_corta_quem_ja_comecou_a_digitar(ns, capsys):
    """A primeira tecla chega quase no fim do prazo; o resto vem sem pressa.

    O relógio falso avança 1s por sondagem, então um prazo de 3s estouraria em
    3 sondagens. A tecla chega na terceira e a linha inteira ainda é lida.
    """
    local = _com_teclado(ns, _TecladoFalso("Almeida Junior\r", atraso=2))

    assert local["safe_input_timeout"]("Nome: ", 3) == "Almeida Junior"


def test_enter_vazio_e_resposta_e_nao_estouro(ns, capsys):
    """`""` (apertou Enter) precisa ser distinguível de `None` (não respondeu)."""
    local = _com_teclado(ns, _TecladoFalso("\r"))

    assert local["safe_input_timeout"]("Nome: ", 30) == ""


def test_backspace_apaga_caractere(ns, capsys):
    local = _com_teclado(ns, _TecladoFalso("Rafaek\x08l\r"))

    assert local["safe_input_timeout"]("Nome: ", 30) == "Rafael"


def test_tecla_especial_de_dois_bytes_e_descartada(ns, capsys):
    """Seta/F-key emite 2 chars; consumir só o primeiro sujaria o nome."""
    local = _com_teclado(ns, _TecladoFalso("Ra\xe0Hfael\r"))

    assert local["safe_input_timeout"]("Nome: ", 30) == "Rafael"


def test_ctrl_c_interrompe(ns, capsys):
    local = _com_teclado(ns, _TecladoFalso("Raf\x03"))

    with pytest.raises(KeyboardInterrupt):
        local["safe_input_timeout"]("Nome: ", 30)


def test_sem_console_devolve_none_em_vez_de_estourar(ns, capsys):
    """Serviço/pipe puro: não há a quem perguntar, e não pode quebrar."""
    class _SemConsole:
        def kbhit(self):
            raise OSError("sem console")

    local = _com_teclado(ns, _SemConsole())

    assert local["safe_input_timeout"]("Nome: ", 30) is None
