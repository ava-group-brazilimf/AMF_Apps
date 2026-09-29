"""Isolamento dos agentes coder e limpeza das premissas sobre `000-scaffold-*`.

Estes testes existem porque as duas garantias vivem em lugares diferentes do
código e são fáceis de quebrar sem perceber: o bloqueio dos coders está no
`f4s_phase_runner.main`, e a detecção de scaffold executado está no
`reconstruct_runner_state`, que por muito tempo procurou um diretório que
ninguém criava — uma condição SEMPRE falsa.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS))

import scaffold_state as st  # noqa: E402

PHASE_RUNNER = TOOLS / "f4s_phase_runner.py"


def _projeto(tmp_path: Path) -> Path:
    d = tmp_path / "projects" / "P"
    (d / "outputs" / "tobe" / "speckit" / "specs").mkdir(parents=True)
    (d / "context").mkdir(parents=True)
    return d


# ── CA-004 / RF-001: coder não roda sem aprovação ──────────────────────────

def _rodar_phase_runner(projeto_raiz: Path, monkeypatch) -> subprocess.CompletedProcess:
    """Executa o runner de codegen apontando OUTPUTS_ROOT para a bancada."""
    script = (
        "import sys\n"
        f"sys.path.insert(0, r'{TOOLS}')\n"
        "from pathlib import Path\n"
        "import f4s_phase_runner as fpr\n"
        f"fpr.OUTPUTS_ROOT = Path(r'{projeto_raiz}')\n"
        "raise SystemExit(fpr.main(['--project-name','P','--target-stack','dotnet']))\n"
    )
    return subprocess.run([sys.executable, "-c", script],
                          capture_output=True, text=True, check=False, timeout=120)


def test_coder_nao_roda_sem_estado_de_aprovacao(tmp_path: Path, monkeypatch):
    """CA-009 — estado inexistente NÃO é aprovação."""
    projeto = _projeto(tmp_path)
    proc = _rodar_phase_runner(projeto.parent, monkeypatch)

    assert proc.returncode == 3
    assert "BLOQUEADO" in proc.stderr
    assert "Nenhum agente coder" in proc.stderr


def test_coder_nao_roda_com_gate_em_espera(tmp_path: Path, monkeypatch):
    projeto = _projeto(tmp_path)
    estado = st.load_state(projeto, "P")
    st.set_approval(projeto, estado, status=st.AWAITING_USER_APPROVAL)

    proc = _rodar_phase_runner(projeto.parent, monkeypatch)

    assert proc.returncode == 3
    assert "awaiting_user_approval" in proc.stderr


def test_coder_nao_roda_com_gate_rejeitado(tmp_path: Path, monkeypatch):
    """CA-008 — rejeição interrompe a esteira."""
    projeto = _projeto(tmp_path)
    estado = st.load_state(projeto, "P")
    st.set_approval(projeto, estado, status=st.AWAITING_USER_APPROVAL)
    st.set_approval(projeto, estado, status=st.REJECTED)

    proc = _rodar_phase_runner(projeto.parent, monkeypatch)

    assert proc.returncode == 3
    assert "rejected" in proc.stderr


def test_gate_aprovado_libera_o_bloqueio(tmp_path: Path):
    """CA-007 — a mesma condição que barra em espera/rejeição deixa passar.

    Não roda o runner inteiro de propósito: adiante ele despacha agente e faz
    git, que são limites externos. O que importa aqui é a guarda.
    """
    projeto = _projeto(tmp_path)
    estado = st.load_state(projeto, "P")
    st.set_approval(projeto, estado, status=st.AWAITING_USER_APPROVAL)
    assert not st.is_approved(st.load_state(projeto, "P"))

    st.set_approval(projeto, estado, status=st.APPROVED, user="ana")
    assert st.is_approved(st.load_state(projeto, "P"))


def test_a_guarda_do_runner_de_codegen_existe_e_usa_is_approved():
    """Trava o ponto exato: o bloqueio é código, não instrução de prompt."""
    fonte = PHASE_RUNNER.read_text(encoding="utf-8")
    assert "if not is_approved(estado):" in fonte
    assert "return 3" in fonte
    assert "Nenhum agente coder será executado" in fonte


# ── CA-016: reconstrução de estado não depende de `000-scaffold-*` ─────────

def test_reconstrucao_nao_procura_diretorio_que_ninguem_cria():
    """A condição antiga (`glob('000-scaffold-*')`) era sempre falsa.

    A checagem ignora comentários de propósito: o comentário que EXPLICA a
    remoção cita o padrão antigo, e apagá-lo junto perderia o porquê.
    """
    fonte = (TOOLS / "reconstruct_runner_state.py").read_text(encoding="utf-8")
    codigo = [linha for linha in fonte.splitlines()
              if not linha.lstrip().startswith("#")]
    assert not [linha for linha in codigo if 'glob("000-scaffold-*")' in linha]
    assert "T-SCAFFOLD-" in fonte, (
        "a detecção precisa olhar o artefato que o injetor realmente produz")


def test_reconstrucao_detecta_scaffold_pela_task_no_fragment(tmp_path: Path,
                                                             monkeypatch):
    import reconstruct_runner_state as rrs

    projeto = _projeto(tmp_path)
    specs = projeto / "outputs" / "tobe" / "speckit" / "specs" / "001-w0-foundation"
    specs.mkdir(parents=True)
    monkeypatch.setattr(rrs, "_project_dir", lambda _p: projeto)

    (specs / "task-fragment.json").write_text(json.dumps({
        "entries": [{"task_id": "T-D-001"}]}), encoding="utf-8")
    assert "F3S:tool:f4s-scaffold-inject" not in rrs._infer_tool_steps_from_artifacts("P", set())

    (specs / "task-fragment.json").write_text(json.dumps({
        "entries": [{"task_id": "T-SCAFFOLD-BACKEND-001"}]}), encoding="utf-8")
    assert "F3S:tool:f4s-scaffold-inject" in rrs._infer_tool_steps_from_artifacts("P", set())


def test_gate_speckit_nao_exige_artefato_de_pasta_inexistente():
    fonte = (REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "speckit"
             / "utils" / "artifact_gate_speckit.py").read_text(encoding="utf-8")
    # A isenção permanece por compatibilidade, mas sem exigir spec.md /
    # plan-graph.json dentro de um diretório que o injetor não cria mais.
    trecho = fonte.split("scaffolds = {name for name in actual")[1][:600]
    assert "plan-graph.json" not in trecho


# ── O injetor não duplica mais a receita (RF-013) ──────────────────────────

def test_injetor_referencia_a_receita_em_vez_de_copia_la():
    fonte = (TOOLS / "f4s_scaffold_injector.py").read_text(encoding="utf-8")
    assert "scaffold_md.read_text(encoding=\"utf-8\").strip()" not in fonte, (
        "a receita voltou a ser copiada para dentro do spec.md")
    assert "Conteúdo derivado" in fonte
    assert "hashlib.sha256" in fonte


def test_injetor_nomeia_task_e_artifact_por_responsabilidade():
    fonte = (TOOLS / "f4s_scaffold_injector.py").read_text(encoding="utf-8")
    assert "_component_type(stack).upper()" in fonte
    assert 'f"artifact:scaffold:{stack}"' not in fonte
