"""Gate com prazo: 60s para decidir, depois aprova sozinho.

Política definida pelo usuário, invertendo o desenho original (que bloqueava
por ausência de resposta). O que estes testes travam:

  - o prazo existe e é respeitado (não espera para sempre);
  - esgotado, APROVA e libera os coders;
  - a decisão automática é distinguível da humana em `tasks-progress.json`;
  - resposta humana dentro do prazo manda, inclusive rejeição;
  - o automatismo NUNCA rejeita sozinho;
  - `timeout_s=0` restaura o modo estrito.

Os prazos usados aqui são de milissegundos: o que se verifica é o mecanismo,
não a constante de 60s (essa é conferida separadamente).
"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))

import scaffold_approval as ap  # noqa: E402
import scaffold_state as st  # noqa: E402


@pytest.fixture()
def projeto(tmp_path: Path) -> Path:
    d = tmp_path / "projects" / "P"
    (d / "outputs" / "tobe").mkdir(parents=True)
    return d


def _resumo() -> dict:
    return {
        "components": {
            "frontend": {"stack": "angular", "status": "completed",
                         "output_path": "source-code/frontend",
                         "build_status": "succeeded", "warning_count": 0},
            "backend": {"stack": "dotnet", "status": "completed",
                        "output_path": "source-code/backend",
                        "restore_status": "succeeded",
                        "build_status": "succeeded", "warning_count": 0},
        },
        "commit_sha": "abc1234567890", "log_path": None,
    }


def _pedir(projeto: Path, estado: dict, **kw):
    return ap.request_approval(projeto, estado, summary=_resumo(), **kw)


# ── O prazo padrão ─────────────────────────────────────────────────────────

def test_prazo_padrao_e_de_60_segundos():
    """O número que o usuário pediu, no lugar onde ele é lido."""
    assert ap.DEFAULT_APPROVAL_TIMEOUT_S == 60
    assert ap._timeout_configurado(None) == 60


def test_prazo_pode_ser_ajustado_por_ambiente(monkeypatch):
    monkeypatch.setenv("AVA_SCAFFOLD_APPROVAL_TIMEOUT", "5")
    assert ap._timeout_configurado(None) == 5


def test_argumento_explicito_vence_o_ambiente(monkeypatch):
    monkeypatch.setenv("AVA_SCAFFOLD_APPROVAL_TIMEOUT", "5")
    assert ap._timeout_configurado(12) == 12


def test_valor_invalido_no_ambiente_cai_no_padrao(monkeypatch):
    monkeypatch.setenv("AVA_SCAFFOLD_APPROVAL_TIMEOUT", "depois")
    assert ap._timeout_configurado(None) == 60


# ── Mecanismo de leitura com prazo ─────────────────────────────────────────

def test_leitura_com_prazo_devolve_none_quando_esgota(monkeypatch):
    """Sem resposta, retorna — não trava o processo."""
    monkeypatch.setattr("builtins.input", lambda *_: time.sleep(30) or "A")

    inicio = time.monotonic()
    resultado = ap._input_com_timeout("? ", 1)
    decorrido = time.monotonic() - inicio

    assert resultado is None
    assert decorrido < 5, f"não respeitou o prazo: {decorrido:.1f}s"


def test_leitura_com_prazo_devolve_a_resposta_quando_chega(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "A")
    assert ap._input_com_timeout("? ", 5) == "A"


# ── Comportamento do gate ──────────────────────────────────────────────────

def test_prazo_esgotado_aprova_e_libera_os_coders(projeto: Path, monkeypatch):
    monkeypatch.setattr(ap, "_input_com_timeout", lambda *_a, **_k: None)
    estado = st.load_state(projeto, "P")

    registro = _pedir(projeto, estado, interactive=True, timeout_s=1)

    assert registro["status"] == st.APPROVED
    assert st.is_approved(st.load_state(projeto, "P"))


def test_aprovacao_por_prazo_fica_marcada_como_automatica(projeto: Path, monkeypatch):
    """A diferença que a auditoria precisa enxergar."""
    monkeypatch.setattr(ap, "_input_com_timeout", lambda *_a, **_k: None)
    estado = st.load_state(projeto, "P")

    registro = _pedir(projeto, estado, interactive=True, timeout_s=1, user="ana")

    assert registro["decided_by"] == "timeout"
    assert registro["auto_approved"] is True
    assert registro["user"] is None, "prazo vencido não é decisão de ninguém"
    assert "60" in str(registro.get("timeout_s")) or registro["timeout_s"] == 1

    persistido = st.load_state(projeto, "P")["approval"]
    assert persistido["decided_by"] == "timeout"


def test_resposta_humana_dentro_do_prazo_manda(projeto: Path, monkeypatch):
    monkeypatch.setattr(ap, "_input_com_timeout", lambda *_a, **_k: "A")
    estado = st.load_state(projeto, "P")

    registro = _pedir(projeto, estado, interactive=True, timeout_s=30, user="ana")

    assert registro["status"] == st.APPROVED
    assert registro["decided_by"] == "user"
    assert registro["auto_approved"] is False
    assert registro["user"] == "ana"


def test_rejeicao_dentro_do_prazo_bloqueia(projeto: Path, monkeypatch):
    monkeypatch.setattr(ap, "_input_com_timeout", lambda *_a, **_k: "R")
    estado = st.load_state(projeto, "P")

    registro = _pedir(projeto, estado, interactive=True, timeout_s=30, user="ana")

    assert registro["status"] == st.REJECTED
    assert not st.is_approved(st.load_state(projeto, "P"))


def test_automatismo_nunca_rejeita_sozinho(projeto: Path, monkeypatch):
    """O prazo só pode APROVAR. Rejeitar exige alguém."""
    monkeypatch.setattr(ap, "_input_com_timeout", lambda *_a, **_k: None)
    estado = st.load_state(projeto, "P")

    registro = _pedir(projeto, estado, interactive=True, timeout_s=1)
    assert registro["status"] != st.REJECTED


def test_resposta_ilegivel_nao_vira_aprovacao(projeto: Path, monkeypatch):
    """Quem digitou algo estava presente. Typo não pode virar 'aprovado'."""
    monkeypatch.setattr(ap, "_input_com_timeout", lambda *_a, **_k: "talvez")
    estado = st.load_state(projeto, "P")

    registro = _pedir(projeto, estado, interactive=True, timeout_s=30)

    assert registro["status"] == st.AWAITING_USER_APPROVAL
    assert not st.is_approved(st.load_state(projeto, "P"))


def test_sem_terminal_aprova_automaticamente(projeto: Path):
    """Esteira automática despacha os coders — o pedido explícito do usuário."""
    estado = st.load_state(projeto, "P")

    registro = _pedir(projeto, estado, interactive=False, timeout_s=60)

    assert registro["status"] == st.APPROVED
    assert registro["decided_by"] == "non-interactive"
    assert registro["auto_approved"] is True


# ── Modo estrito ───────────────────────────────────────────────────────────

def test_modo_estrito_sem_terminal_fica_em_espera(projeto: Path):
    estado = st.load_state(projeto, "P")

    registro = _pedir(projeto, estado, interactive=False, timeout_s=0)

    assert registro["status"] == st.AWAITING_USER_APPROVAL
    assert not st.is_approved(st.load_state(projeto, "P"))


def test_modo_estrito_com_terminal_usa_input_sem_prazo(projeto: Path, monkeypatch):
    chamadas: list[str] = []
    monkeypatch.setattr("builtins.input", lambda p="": chamadas.append("input") or "A")
    monkeypatch.setattr(ap, "_input_com_timeout",
                        lambda *_a, **_k: pytest.fail("não deveria usar prazo"))
    estado = st.load_state(projeto, "P")

    registro = _pedir(projeto, estado, interactive=True, timeout_s=0)

    assert chamadas == ["input"]
    assert registro["status"] == st.APPROVED
    assert registro["decided_by"] == "user"


# ── Mensagem ao operador ───────────────────────────────────────────────────

def test_mensagem_avisa_que_a_omissao_aprova():
    """O operador precisa saber que ficar calado libera os coders."""
    texto = ap.render_summary(_resumo())
    assert "APROVADO automaticamente" in texto
    assert "[A]" in texto and "[R]" in texto


def test_decisao_explicita_por_flag_conta_como_humana(projeto: Path):
    estado = st.load_state(projeto, "P")
    registro = _pedir(projeto, estado, decision="approve", user="ana")
    assert registro["decided_by"] == "user"
    assert registro["auto_approved"] is False
