"""
Testes do gate de artefatos AS-IS (F1) — `asis-diagnostic/utils/artifact_gate.py`.

Este gate sustenta o `agent_runner` em produção (guard pré e pós-dispatch) e não
tinha cobertura. Os testes aqui congelam dois invariantes que já custaram
incidentes:

* `db/db-analysis-report.md` mora em `asis/db/`, não na raiz (ISSUE-002 §RC-2 —
  o guard nunca confirmava o db-analyzer e o re-despachava em loop);
* `_resolve_base` continua resolvendo `base="asis"` para o mesmo diretório após
  a generalização feita para a F2 reusar `check_item`.

Roda com o Python do repo:
    python -m pytest tests/tools/test_artifact_gate.py -q
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_PY = (
    REPO_ROOT / "src" / "modules" / "ava-fabric-agents"
    / "asis-diagnostic" / "utils" / "artifact_gate.py"
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load(GATE_PY, "artifact_gate_asis_under_test")


# ─── Ancoragem ───────────────────────────────────────────────────────────────

def test_repo_root_e_ancorado_no_arquivo_e_nao_no_cwd():
    assert gate.REPO_ROOT == REPO_ROOT
    assert (gate.REPO_ROOT / "projects").is_dir()


def test_resolve_base_asis_nao_mudou_com_a_generalizacao():
    """A F2 acrescentou `tobe`/`context` a `_PROJECT_BASES`; `asis` tem de ficar igual."""
    assert gate._resolve_base("X", "asis") == REPO_ROOT / "projects" / "X" / "outputs" / "asis"


def test_resolve_base_conhece_as_bases_da_f2():
    assert gate._resolve_base("X", "tobe") == REPO_ROOT / "projects" / "X" / "outputs" / "tobe"
    assert gate._resolve_base("X", "context") == REPO_ROOT / "projects" / "X" / "context"


def test_resolve_base_workspace_e_fastqa_continuam_intactos():
    assert gate._resolve_base("X", "workspace") == REPO_ROOT
    assert gate._resolve_base("X", "fastqa") == REPO_ROOT / "fastqa/manual_test"


# ─── Contrato do db-analyzer (ISSUE-002 §RC-2 / ISSUE-003 §6.1) ──────────────

def test_db_analysis_report_esta_sob_db_no_contrato_do_agente():
    paths = {item["path"] for item in gate.ARTIFACT_CONTRACTS["ava-asis-db-analyzer"]}
    assert "db/db-analysis-report.md" in paths
    assert "db-analysis-report.md" not in paths


def test_db_analysis_report_esta_sob_db_no_contrato_da_fase():
    assert "db/db-analysis-report.md" in gate.F1_OUTPUT_CONTRACT
    assert "db-analysis-report.md" not in gate.F1_OUTPUT_CONTRACT


# ─── Semântica de dispatch ───────────────────────────────────────────────────

def test_agente_sem_contrato_nunca_bloqueia_dispatch():
    res = gate.check_agent("MeuERP-002", "agente-que-nao-existe")
    assert res["status"] == "no_contract"
    assert res["should_dispatch"] is True


def test_arquivo_vazio_conta_como_ausente(tmp_path, monkeypatch):
    """`min_size` default é 1 byte — placeholder vazio não pode aprovar o gate."""
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    alvo = tmp_path / "projects/P/outputs/asis/master-report.md"
    alvo.parent.mkdir(parents=True)
    alvo.write_text("", encoding="utf-8")
    res = gate.check_agent("P", "ava-asis-orchestrator")
    assert res["complete"] is False
