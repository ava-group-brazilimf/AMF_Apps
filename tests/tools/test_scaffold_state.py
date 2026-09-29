"""Máquina de estados e escrita atômica do `tasks-progress.json`.

O invariante central: **ausência de decisão nunca é aprovação**. Todo o resto
existe para que esse fato sobreviva a interrupção, retomada e corrupção.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))

import scaffold_state as st  # noqa: E402


@pytest.fixture()
def projeto(tmp_path: Path) -> Path:
    d = tmp_path / "projects" / "P"
    (d / "outputs" / "tobe").mkdir(parents=True)
    return d


# ── Escrita atômica ────────────────────────────────────────────────────────

def test_estado_ausente_devolve_estado_vazio(projeto: Path):
    estado = st.load_state(projeto, "P")
    assert estado["tasks"] == {}
    assert estado["approval"] is None
    assert not st.is_approved(estado)


def test_json_corrompido_nao_trava_a_esteira(projeto: Path):
    st.state_path(projeto).write_text("{ isso nao e json", encoding="utf-8")
    estado = st.load_state(projeto, "P")
    assert estado["tasks"] == {}
    assert not st.is_approved(estado)


def test_escrita_e_atomica_sem_deixar_temporario(projeto: Path):
    estado = st.load_state(projeto, "P")
    st.save_state(projeto, estado)
    diretorio = st.state_path(projeto).parent
    restos = [p.name for p in diretorio.iterdir() if p.name.endswith(".tmp")]
    assert restos == []
    assert json.loads(st.state_path(projeto).read_text(encoding="utf-8"))["project"] == "P"


def test_falha_no_meio_da_escrita_preserva_o_arquivo_anterior(projeto: Path,
                                                              monkeypatch):
    estado = st.load_state(projeto, "P")
    estado["marcador"] = "original"
    st.save_state(projeto, estado)

    def explodir(*_a, **_k):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", explodir)
    estado["marcador"] = "novo"
    with pytest.raises(OSError):
        st.save_state(projeto, estado)

    em_disco = json.loads(st.state_path(projeto).read_text(encoding="utf-8"))
    assert em_disco["marcador"] == "original"
    restos = [p.name for p in st.state_path(projeto).parent.iterdir()
              if p.name.endswith(".tmp")]
    assert restos == [], "temporário vazado após falha"


# ── Transições ─────────────────────────────────────────────────────────────

def test_transicoes_validas_do_ciclo_feliz():
    st.assert_transition(None, st.RUNNING)
    st.assert_transition(st.RUNNING, st.GENERATED)
    st.assert_transition(st.GENERATED, st.VERIFYING)
    st.assert_transition(st.VERIFYING, st.COMPLETED)


@pytest.mark.parametrize("de,para", [
    (st.RUNNING, st.COMPLETED),      # não se conclui sem verificar
    (st.GENERATED, st.COMPLETED),    # idem
    (st.COMPLETED, st.FAILED),
    (st.APPROVED, st.REJECTED),      # aprovado não volta atrás sozinho
    (None, st.COMPLETED),
])
def test_transicoes_invalidas_sao_bloqueadas(de, para):
    with pytest.raises(st.StateError, match="transição inválida|inicial inválido"):
        st.assert_transition(de, para)


def test_status_desconhecido_e_rejeitado():
    with pytest.raises(st.StateError, match="desconhecido"):
        st.assert_transition(st.RUNNING, "quase_pronto")


# ── Tasks de scaffold ──────────────────────────────────────────────────────

def test_task_registra_component_type_stack_e_caminho_canonico(projeto: Path):
    estado = st.load_state(projeto, "P")
    st.update_scaffold_task(projeto, estado, component_type="frontend",
                            status=st.RUNNING, stack="angular")
    st.update_scaffold_task(projeto, estado, component_type="frontend",
                            status=st.GENERATED)
    st.update_scaffold_task(projeto, estado, component_type="frontend",
                            status=st.VERIFYING)
    registro = st.update_scaffold_task(projeto, estado, component_type="frontend",
                                       status=st.COMPLETED, build_status="succeeded")

    assert registro["task_id"] == "T-SCAFFOLD-FRONTEND-001"
    assert registro["component_type"] == "frontend"
    assert registro["stack"] == "angular"
    assert registro["output_path"] == "source-code/frontend"   # CA-023
    assert registro["started_at"] and registro["completed_at"]
    assert estado["artifacts"]["artifact:scaffold:frontend"]["stack"] == "angular"


def test_backend_registra_o_caminho_canonico_de_backend(projeto: Path):
    """CA-024 — e o id da task é por responsabilidade, não por tecnologia."""
    estado = st.load_state(projeto, "P")
    st.update_scaffold_task(projeto, estado, component_type="backend",
                            status=st.RUNNING, stack="dotnet")
    registro = st.scaffold_task(estado, "backend")
    assert registro["task_id"] == "T-SCAFFOLD-BACKEND-001"
    assert registro["output_path"] == "source-code/backend"
    assert "dotnet" not in registro["task_id"].lower()


def test_output_path_nao_pode_ser_injetado_de_fora(projeto: Path):
    """Nem passando explicitamente o caminho errado ele é aceito."""
    estado = st.load_state(projeto, "P")
    registro = st.update_scaffold_task(
        projeto, estado, component_type="frontend", status=st.RUNNING,
        stack="angular", output_path="source-code/angular")
    assert registro["output_path"] == "source-code/frontend"


# ── Gate de aprovação ──────────────────────────────────────────────────────

def test_sem_registro_nao_ha_aprovacao(projeto: Path):
    """CA-009 — a esteira não pode inferir aprovação."""
    assert not st.is_approved(st.load_state(projeto, "P"))


def test_espera_nao_libera_e_nao_cria_artifact(projeto: Path):
    estado = st.load_state(projeto, "P")
    st.set_approval(projeto, estado, status=st.AWAITING_USER_APPROVAL)
    assert not st.is_approved(estado)
    assert st.APPROVAL_ARTIFACT not in estado["artifacts"]


def test_rejeicao_nao_libera_e_remove_artifact(projeto: Path):
    estado = st.load_state(projeto, "P")
    st.set_approval(projeto, estado, status=st.AWAITING_USER_APPROVAL)
    st.set_approval(projeto, estado, status=st.REJECTED, user="ana")
    assert not st.is_approved(estado)
    assert st.APPROVAL_ARTIFACT not in estado["artifacts"]
    assert estado["approval"]["decided_at"]
    assert estado["approval"]["user"] == "ana"


def test_aprovacao_explicita_libera_e_registra_autor(projeto: Path):
    estado = st.load_state(projeto, "P")
    st.set_approval(projeto, estado, status=st.AWAITING_USER_APPROVAL)
    st.set_approval(projeto, estado, status=st.APPROVED, user="ana",
                    run_id="run-1", note="revisado")
    assert st.is_approved(estado)
    assert estado["artifacts"][st.APPROVAL_ARTIFACT]["status"] == st.APPROVED
    assert estado["approval"]["run_id"] == "run-1"


def test_rejeicao_aceita_nova_decisao_explicita(projeto: Path):
    """Rejeitar por engano não pode inutilizar o projeto."""
    estado = st.load_state(projeto, "P")
    st.set_approval(projeto, estado, status=st.AWAITING_USER_APPROVAL)
    st.set_approval(projeto, estado, status=st.REJECTED)
    st.set_approval(projeto, estado, status=st.APPROVED, user="ana")
    assert st.is_approved(estado)


def test_estado_persistido_sobrevive_a_recarga(projeto: Path):
    estado = st.load_state(projeto, "P")
    st.set_approval(projeto, estado, status=st.AWAITING_USER_APPROVAL)
    recarregado = st.load_state(projeto, "P")
    assert st.approval_status(recarregado) == st.AWAITING_USER_APPROVAL
    assert not st.is_approved(recarregado)


# ── Idempotência / retomada ────────────────────────────────────────────────

def test_task_concluida_com_artefato_em_disco_e_reaproveitavel(projeto: Path):
    tobe = projeto / "outputs" / "tobe"
    destino = tobe / "source-code" / "frontend"
    destino.mkdir(parents=True)
    (destino / "package.json").write_text("{}", encoding="utf-8")

    estado = st.load_state(projeto, "P")
    for status in (st.RUNNING, st.GENERATED, st.VERIFYING, st.COMPLETED):
        st.update_scaffold_task(projeto, estado, component_type="frontend",
                                status=status, stack="angular")
    assert st.task_is_reusable(estado, "frontend", tobe)


def test_estado_completed_com_diretorio_apagado_nao_e_reaproveitavel(projeto: Path):
    """RF-012 — não confiar só no estado persistido."""
    tobe = projeto / "outputs" / "tobe"
    estado = st.load_state(projeto, "P")
    for status in (st.RUNNING, st.GENERATED, st.VERIFYING, st.COMPLETED):
        st.update_scaffold_task(projeto, estado, component_type="frontend",
                                status=status, stack="angular")
    assert not st.task_is_reusable(estado, "frontend", tobe)


def test_diretorio_vazio_nao_conta_como_scaffold_valido(projeto: Path):
    tobe = projeto / "outputs" / "tobe"
    (tobe / "source-code" / "frontend").mkdir(parents=True)
    estado = st.load_state(projeto, "P")
    for status in (st.RUNNING, st.GENERATED, st.VERIFYING, st.COMPLETED):
        st.update_scaffold_task(projeto, estado, component_type="frontend",
                                status=status, stack="angular")
    assert not st.task_is_reusable(estado, "frontend", tobe)


def test_scaffold_completed_exige_os_dois_componentes(projeto: Path):
    estado = st.load_state(projeto, "P")
    for status in (st.RUNNING, st.GENERATED, st.VERIFYING, st.COMPLETED):
        st.update_scaffold_task(projeto, estado, component_type="frontend",
                                status=status, stack="angular")
    assert not st.scaffold_completed(estado)
    for status in (st.RUNNING, st.GENERATED, st.VERIFYING, st.COMPLETED):
        st.update_scaffold_task(projeto, estado, component_type="backend",
                                status=status, stack="dotnet")
    assert st.scaffold_completed(estado)
