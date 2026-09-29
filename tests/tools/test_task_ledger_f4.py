"""Razão de progresso — o que a F4 passou a exigir dele.

Complementa `test_task_ledger.py` (que continua valendo, e que protege o
invariante central: agente não escreve status). Aqui: validação fail-closed,
ordenação determinística completa, migração do nome legado, recuperação de
`in_progress` e política de conclusão da fase.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import task_ledger as tl


def _entry(task_id: str, **campos) -> dict:
    base = {
        "task_id": task_id,
        "title": f"Task {task_id}",
        "feature": "001-domain",
        "spec_id": "SPEC-001",
        "group": "G-A",
        "task_type": "backend",
        "target_stack": "dotnet",
        "migration_wave_id": "W1",
        "migration_wave_order": 1,
        "priority": "P2",
        "depends_on": [],
        "backend_dependencies": [],
        "verify_command": "dotnet build",
        "acceptance": ["compila"],
        "target_files": [f"backend/{task_id}.cs"],
        "topological_rank": 0,
    }
    base.update(campos)
    return base


def _razao(tmp_path: Path, entries: list[dict]) -> Path:
    tl.REPO_ROOT = tmp_path
    speckit = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    speckit.mkdir(parents=True, exist_ok=True)
    (speckit / "traceability.json").write_text(json.dumps({
        "schema_version": "4.0.0", "project": "P", "trace_id": "t",
        "entries": entries}), encoding="utf-8")
    tl.init("P", repo_root=tmp_path)
    return tmp_path


# ─── Campos de contexto ──────────────────────────────────────────────────────

def test_razao_carrega_feature_titulo_e_alvos(tmp_path: Path) -> None:
    """Sem `feature` no razão, todo despacho volta a receber todas as specs."""
    _razao(tmp_path, [_entry("T-001")])
    task = tl.get("P", "T-001", tmp_path)
    assert task["feature"] == "001-domain"
    assert task["title"] == "Task T-001"
    assert task["target_files"] == ["backend/T-001.cs"]


def test_ensure_enriched_reidrata_razao_antigo_preservando_progresso(tmp_path: Path) -> None:
    _razao(tmp_path, [_entry("T-001")])
    ledger = tl.load("P", tmp_path)
    ledger["tasks"][0]["status"] = "verified"
    ledger["tasks"][0]["attempts"] = 2
    for campo in ("feature", "title", "target_files"):
        ledger["tasks"][0].pop(campo)
    tl.save("P", ledger, tmp_path)

    resultado = tl.ensure_enriched("P", tmp_path)
    task = tl.get("P", "T-001", tmp_path)
    assert resultado["status"] == "enriched"
    assert task["feature"] == "001-domain"
    assert task["status"] == "verified", "progresso verificado nunca é zerado"
    assert task["attempts"] == 2


# ─── Ordenação ───────────────────────────────────────────────────────────────

def test_ordem_topologica_wave_prioridade_grupo_id() -> None:
    """A chave de ordenação inteira, na ordem que a F4 promete respeitar."""
    tasks = [
        {"task_id": "T-D", "topological_rank": 1, "migration_wave_order": 0,
         "priority": "P1", "group": "G-A"},
        {"task_id": "T-A", "topological_rank": 0, "migration_wave_order": 0,
         "priority": "P1", "group": "G-A"},
        {"task_id": "T-C", "topological_rank": 0, "migration_wave_order": 1,
         "priority": "P1", "group": "G-A"},
        {"task_id": "T-B", "topological_rank": 0, "migration_wave_order": 0,
         "priority": "P3", "group": "G-A"},
    ]
    ordenadas = [t["task_id"] for t in sorted(tasks, key=tl.order_key)]
    assert ordenadas == ["T-A", "T-B", "T-C", "T-D"]


def test_dependencia_define_o_rank_e_a_ordem_real(tmp_path: Path) -> None:
    """No razão o rank é recalculado da espinha — não é campo de entrada."""
    _razao(tmp_path, [
        _entry("T-002", depends_on=["T-001"]),
        _entry("T-001"),
    ])
    assert [t["task_id"] for t in tl.execution_order("P", tmp_path)] == [
        "T-001", "T-002"]
    assert [t["task_id"] for t in tl.ready_tasks("P", repo_root=tmp_path)] == [
        "T-001"]


def test_prioridade_p1_precede_p2_e_p3(tmp_path: Path) -> None:
    _razao(tmp_path, [
        _entry("T-X", priority="P3"),
        _entry("T-Y", priority="P1"),
        _entry("T-Z", priority="P2"),
    ])
    assert [t["task_id"] for t in tl.ready_tasks("P", repo_root=tmp_path)] == [
        "T-Y", "T-Z", "T-X"]


def test_backend_dependencies_seguram_a_task(tmp_path: Path) -> None:
    _razao(tmp_path, [
        _entry("T-API"),
        _entry("T-TELA", task_type="frontend", target_stack="angular",
               backend_dependencies=["T-API"]),
    ])
    prontas = {t["task_id"] for t in tl.ready_tasks("P", repo_root=tmp_path)}
    assert prontas == {"T-API"}


# ─── Validação fail-closed ───────────────────────────────────────────────────

def test_razao_ausente_levanta(tmp_path: Path) -> None:
    tl.REPO_ROOT = tmp_path
    (tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit").mkdir(parents=True)
    with pytest.raises(tl.LedgerError):
        tl.validate("P", tmp_path)


def test_checksum_divergente_levanta(tmp_path: Path) -> None:
    _razao(tmp_path, [_entry("T-001")])
    trace = (tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
             / "traceability.json")
    trace.write_text(trace.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(tl.LedgerError) as exc:
        tl.validate("P", tmp_path)
    assert "checksum" in str(exc.value)


def test_schema_desconhecido_levanta(tmp_path: Path) -> None:
    _razao(tmp_path, [_entry("T-001")])
    ledger = tl.load("P", tmp_path)
    ledger["schema_version"] = "2.0.0"
    tl.save("P", ledger, tmp_path)
    with pytest.raises(tl.LedgerError):
        tl.validate("P", tmp_path)


# ─── Migração do nome legado ─────────────────────────────────────────────────

def test_tasks_state_legado_nao_e_usado_em_silencio(tmp_path: Path) -> None:
    tl.REPO_ROOT = tmp_path
    speckit = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    speckit.mkdir(parents=True)
    (speckit / tl.LEGACY_LEDGER_FILENAME).write_text(
        json.dumps({"schema_version": "3.0.0", "tasks": [_entry("T-001")]}),
        encoding="utf-8")
    with pytest.raises(tl.LedgerError) as exc:
        tl.validate("P", tmp_path)
    assert "--migrate-legacy" in str(exc.value)


def test_migracao_do_legado_e_idempotente(tmp_path: Path) -> None:
    tl.REPO_ROOT = tmp_path
    speckit = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    speckit.mkdir(parents=True)
    legado = {"schema_version": "3.0.0", "project": "P", "tasks": [_entry("T-001")]}
    (speckit / tl.LEGACY_LEDGER_FILENAME).write_text(json.dumps(legado),
                                                     encoding="utf-8")
    primeira = tl.migrate_legacy("P", tmp_path)
    assert primeira["status"] == "migrated"

    ledger = tl.load("P", tmp_path)
    ledger["tasks"][0]["status"] = "verified"
    tl.save("P", ledger, tmp_path)
    segunda = tl.migrate_legacy("P", tmp_path)
    assert segunda["status"] == "skipped"
    assert tl.get("P", "T-001", tmp_path)["status"] == "verified"


def test_schema_incompativel_nao_e_migrado(tmp_path: Path) -> None:
    tl.REPO_ROOT = tmp_path
    speckit = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    speckit.mkdir(parents=True)
    (speckit / tl.LEGACY_LEDGER_FILENAME).write_text(
        json.dumps({"schema_version": "1.0.0", "tasks": []}), encoding="utf-8")
    with pytest.raises(tl.LedgerError):
        tl.migrate_legacy("P", tmp_path)


# ─── Recuperação ─────────────────────────────────────────────────────────────

def test_in_progress_abandonado_volta_para_pending(tmp_path: Path) -> None:
    _razao(tmp_path, [_entry("T-001")])
    tl.start("P", "T-001", "run-morto", tmp_path)
    recuperadas = tl.recover_stale("P", "run-novo", tmp_path)
    task = tl.get("P", "T-001", tmp_path)
    assert recuperadas[0]["task_id"] == "T-001"
    assert task["status"] == "pending"
    assert task["recovery_reason"]
    assert task["run_id"] is None


def test_in_progress_com_falha_anterior_volta_para_failed(tmp_path: Path) -> None:
    _razao(tmp_path, [_entry("T-001")])
    tl.start("P", "T-001", "run-morto", tmp_path)
    tl.record_result("P", "T-001", command="dotnet build", exit_code=1,
                     recorded_by="pipeline_runner", repo_root=tmp_path)
    ledger = tl.load("P", tmp_path)
    ledger["tasks"][0]["status"] = "in_progress"
    ledger["tasks"][0]["run_id"] = "run-morto"
    tl.save("P", ledger, tmp_path)

    tl.recover_stale("P", "run-novo", tmp_path)
    task = tl.get("P", "T-001", tmp_path)
    assert task["status"] == "failed"
    assert task["attempts"] == 1, "tentativas anteriores são preservadas"
    assert task["evidence"]["exit_code"] == 1


def test_recuperacao_respeita_o_teto_de_tentativas(tmp_path: Path) -> None:
    _razao(tmp_path, [_entry("T-001")])
    ledger = tl.load("P", tmp_path)
    ledger["tasks"][0].update({"status": "in_progress", "run_id": "run-morto",
                               "attempts": tl.MAX_ATTEMPTS})
    tl.save("P", ledger, tmp_path)
    tl.recover_stale("P", "run-novo", tmp_path)
    assert tl.get("P", "T-001", tmp_path)["status"] == "blocked"


# ─── Conclusão da fase ───────────────────────────────────────────────────────

def test_conclusao_exige_todas_verified(tmp_path: Path) -> None:
    _razao(tmp_path, [_entry("T-001"), _entry("T-002")])
    assert tl.completion_status("P", tmp_path)["status"] == tl.COMPLETION_FAILED

    for task_id in ("T-001", "T-002"):
        tl.start("P", task_id, "r", tmp_path)
        tl.record_result("P", task_id, command="dotnet build", exit_code=0,
                         recorded_by="pipeline_runner", repo_root=tmp_path)
    assert tl.completion_status("P", tmp_path)["status"] == tl.COMPLETION_SUCCESS


def test_task_bloqueada_nao_vira_sucesso_funcional(tmp_path: Path) -> None:
    """A fase encerra (tudo processado), mas sem sucesso funcional."""
    _razao(tmp_path, [_entry("T-001")])
    ledger = tl.load("P", tmp_path)
    ledger["tasks"][0]["status"] = "blocked"
    ledger["tasks"][0]["executionStatus"] = tl.EXEC_FAILED_AFTER_REMEDIATION
    tl.save("P", ledger, tmp_path)
    veredito = tl.completion_status("P", tmp_path)
    assert veredito["status"] == tl.COMPLETION_WITH_REVIEW
    assert veredito["execution_complete"] is True
    assert veredito["functional_success"] is False
    assert veredito["review_required"] == ["T-001"]


def test_skipped_exige_revisao_e_nunca_e_sucesso(tmp_path: Path) -> None:
    """`skipped` é decisão de operador: entra como `review`, com dono e motivo."""
    _razao(tmp_path, [_entry("T-001")])
    tl.skip("P", "T-001", "decisão explícita do operador", tmp_path)
    task = tl.get("P", "T-001", tmp_path)
    assert task["executionStatus"] == tl.EXEC_REVIEW
    assert task["reviewRequired"] is True
    veredito = tl.completion_status("P", tmp_path)
    assert veredito["status"] == tl.COMPLETION_WITH_REVIEW
    assert veredito["execution_complete"] is True
    assert veredito["functional_success"] is False


# ─── Histórico e autoridade ──────────────────────────────────────────────────

def test_historico_de_tentativas_e_acumulado(tmp_path: Path) -> None:
    _razao(tmp_path, [_entry("T-001")])
    tl.start("P", "T-001", "r", tmp_path)
    tl.record_result("P", "T-001", command="dotnet build", exit_code=1,
                     recorded_by="pipeline_runner", repo_root=tmp_path,
                     summary_text="erro CS0246")
    tl.record_result("P", "T-001", command="dotnet build", exit_code=0,
                     recorded_by="pipeline_runner", repo_root=tmp_path,
                     commit_hash="c0ffee", summary_text="corrigido")
    task = tl.get("P", "T-001", tmp_path)
    assert [h["exit_code"] for h in task["attempt_history"]] == [1, 0]
    assert task["attempt_history"][0]["summary"] == "erro CS0246"
    assert task["evidence"]["commit_hash"] == "c0ffee"


def test_agente_nao_grava_nem_com_os_campos_novos(tmp_path: Path) -> None:
    _razao(tmp_path, [_entry("T-001")])
    with pytest.raises(tl.LedgerError):
        tl.record_result("P", "T-001", command="dotnet build", exit_code=0,
                         recorded_by="ava-stack-dotnet-backend",
                         routing={"agent": "ava-stack-dotnet-backend"},
                         repo_root=tmp_path)
