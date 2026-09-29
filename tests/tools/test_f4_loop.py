"""Laço externo da F4 (Ralph Wiggum) — `src/shared/tools/f4_loop.py`.

O que precisa ser verdade, e por quê:

* **a fila não é estática** — concluir a task 1 tem de fazer a 2 aparecer *no
  mesmo run*. Era o defeito do `expand_foreach`: a lista era montada uma vez, e
  a dependente só voltava num `--resume`;
* **fail-closed** — razão ausente, checksum divergente ou gate F4S reprovado
  impedem a fase; nenhum agente é despachado;
* **`verified` só com exit code 0** — declaração do agente não conta;
* **fila vazia com pendência não é sucesso** — vira BLOCKED/FAILED com
  diagnóstico;
* **retomada** — task presa em `in_progress` de um run morto volta para a fila
  preservando `attempts` e evidência.

O laço recebe `dispatch` e `verify` por parâmetro, então tudo aqui roda sem SDK,
sem rede e sem toolchain.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import f4_loop
import task_ledger


# ─── Fixture de projeto ──────────────────────────────────────────────────────

def _entry(task_id: str, *, depends_on: list[str] | None = None,
           stack: str = "dotnet", task_type: str = "backend",
           priority: str = "P2", rank: int = 0, wave: int = 0) -> dict:
    return {
        "task_id": task_id,
        "title": f"Task {task_id}",
        "feature": "001-domain",
        "spec_id": "SPEC-001",
        "group": "G-A",
        "task_type": task_type,
        "target_stack": stack,
        "migration_wave_id": f"W{wave}",
        "migration_wave_order": wave,
        "priority": priority,
        "depends_on": list(depends_on or []),
        "backend_dependencies": [],
        "verify_command": "dotnet build",
        "acceptance": ["compila"],
        "target_files": [f"backend/{task_id}.cs"],
        "topological_rank": rank,
    }


def _projeto(tmp_path: Path, entries: list[dict], *, aprovado: bool = True) -> Path:
    """Cria razão + estado de F4S aprovado, como a esteira real deixaria."""
    task_ledger.REPO_ROOT = tmp_path
    tobe = tmp_path / "projects" / "P" / "outputs" / "tobe"
    speckit = tobe / "speckit"
    speckit.mkdir(parents=True, exist_ok=True)
    trace = {"schema_version": "4.0.0", "project": "P", "trace_id": "t",
             "total_tasks": len(entries), "entries": entries}
    (speckit / "traceability.json").write_text(json.dumps(trace), encoding="utf-8")
    task_ledger.init("P", repo_root=tmp_path)

    # Scaffold "real" da F4S: a F4 reusa o que existe e nunca recria.
    for componente, arquivo in (("frontend", "package.json"),
                                ("backend", "App.csproj")):
        destino = tobe / "source-code" / componente
        destino.mkdir(parents=True, exist_ok=True)
        (destino / arquivo).write_text("{}", encoding="utf-8")
    (tobe / "source-code" / ".git").mkdir(parents=True, exist_ok=True)

    estado = {
        "schema_version": "1.0.0", "project": "P",
        "tasks": {
            "T-SCAFFOLD-FRONTEND-001": {"status": "completed",
                                        "build_status": "succeeded",
                                        "verification_status": "succeeded",
                                        "commit_sha": "abc1234"},
            "T-SCAFFOLD-BACKEND-001": {"status": "completed",
                                       "build_status": "succeeded",
                                       "verification_status": "succeeded",
                                       "commit_sha": "abc1234"},
        },
        "approval": {"status": "approved" if aprovado else "awaiting_user_approval",
                     "decided_at": "2026-08-30T00:00:00+00:00"},
        "artifacts": {},
    }
    (tobe / "tasks-progress.json").write_text(json.dumps(estado), encoding="utf-8")
    return tmp_path


def _fakes(*, falha_em: set[str] | None = None):
    """`dispatch`/`verify` que gravam no razão como o harness real gravaria."""
    falha_em = falha_em or set()
    chamadas: list[dict] = []

    def dispatch(ctx: dict) -> dict:
        chamadas.append({"task_id": ctx["task_id"], "agent": ctx["route"].agent,
                         "attempt": ctx["attempt"],
                         "component_type": ctx["route"].component_type})
        return {"artifacts": [f"{ctx['task_id']}.cs"],
                "agent_result": {"implementation_status": "completed"}}

    def verify(ctx: dict) -> dict:
        task_id = ctx["task_id"]
        exit_code = 1 if task_id in falha_em else 0
        estado = task_ledger.record_result(
            ctx["project"], task_id, command="dotnet build", exit_code=exit_code,
            log_path="GENERATION_LOG.md", files_written=[f"backend/{task_id}.cs"],
            recorded_by="pipeline_runner", routing=ctx["route"].as_dict(),
            repo_root=ctx["repo_root"])
        return {"status": estado["status"], "exit_code": exit_code,
                "command": "dotnet build",
                "files_written": [f"backend/{task_id}.cs"],
                "commit_hash": "c0ffee" if exit_code == 0 else ""}

    return dispatch, verify, chamadas


# ─── D. Ralph loop ───────────────────────────────────────────────────────────

def test_conclusao_de_uma_task_libera_a_dependente_no_mesmo_run(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001"), _entry("T-002", depends_on=["T-001"], rank=1)])
    dispatch, verify, chamadas = _fakes()

    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)

    assert [c["task_id"] for c in chamadas] == ["T-001", "T-002"]
    assert resultado.status == task_ledger.COMPLETION_SUCCESS
    assert resultado.iterations == 2


def test_a_lista_de_tasks_nao_e_estatica(tmp_path: Path) -> None:
    """A dependente não estava pronta quando o laço começou — e ainda assim rodou."""
    _projeto(tmp_path, [_entry("T-001"), _entry("T-002", depends_on=["T-001"], rank=1)])
    prontas_no_inicio = [t["task_id"] for t in task_ledger.ready_tasks("P", repo_root=tmp_path)]
    assert prontas_no_inicio == ["T-001"]

    dispatch, verify, chamadas = _fakes()
    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1", repo_root=tmp_path)
    assert "T-002" in [c["task_id"] for c in chamadas]


def test_ordem_respeita_rank_wave_e_prioridade(tmp_path: Path) -> None:
    _projeto(tmp_path, [
        _entry("T-C", priority="P3", rank=0, wave=0),
        _entry("T-A", priority="P1", rank=0, wave=0),
        _entry("T-B", priority="P2", rank=0, wave=0),
        _entry("T-D", priority="P1", rank=0, wave=1),
    ])
    dispatch, verify, chamadas = _fakes()
    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1", repo_root=tmp_path)
    assert [c["task_id"] for c in chamadas] == ["T-A", "T-B", "T-C", "T-D"]


def test_falha_recuperavel_gera_nova_tentativa_e_depois_bloqueia(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")])
    dispatch, verify, chamadas = _fakes(falha_em={"T-001"})

    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)

    assert len(chamadas) == task_ledger.MAX_ATTEMPTS, (
        "a task falhada volta para a fila até o teto de tentativas")
    task = task_ledger.get("P", "T-001", tmp_path)
    assert task["status"] == "blocked"
    assert task["executionStatus"] == task_ledger.EXEC_FAILED_AFTER_REMEDIATION
    assert task["reviewRequired"] is True
    # A FASE encerra de forma controlada: tudo foi processado, e o que falhou
    # está registrado para revisão. Uma task falhada não reprova a fase.
    assert resultado.status == task_ledger.COMPLETION_WITH_REVIEW
    assert resultado.execution_complete is True
    assert resultado.functional_success is False


def test_task_verified_nao_e_reexecutada(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001"), _entry("T-002", rank=1)])
    dispatch, verify, _ = _fakes()
    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1", repo_root=tmp_path)

    dispatch2, verify2, chamadas2 = _fakes()
    resultado = f4_loop.run("P", dispatch=dispatch2, verify=verify2, run_id="r2",
                            repo_root=tmp_path)
    assert chamadas2 == [], "nada a refazer: todas as tasks já estão verified"
    assert resultado.status == task_ledger.COMPLETION_SUCCESS


def test_interrupcao_permite_retomada_do_ponto_certo(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001"), _entry("T-002", depends_on=["T-001"], rank=1)])
    dispatch, verify, _ = _fakes()
    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1", repo_root=tmp_path,
                max_tasks=1)
    assert task_ledger.get("P", "T-001", tmp_path)["status"] == "verified"
    assert task_ledger.get("P", "T-002", tmp_path)["status"] == "pending"

    dispatch2, verify2, chamadas2 = _fakes()
    f4_loop.run("P", dispatch=dispatch2, verify=verify2, run_id="r2", repo_root=tmp_path)
    assert [c["task_id"] for c in chamadas2] == ["T-002"]


def test_task_in_progress_de_run_morto_volta_para_a_fila(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")])
    task_ledger.start("P", "T-001", "run-morto", tmp_path)
    assert task_ledger.get("P", "T-001", tmp_path)["status"] == "in_progress"

    dispatch, verify, chamadas = _fakes()
    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="run-novo",
                            repo_root=tmp_path)

    assert resultado.recovered and resultado.recovered[0]["task_id"] == "T-001"
    assert "recuperada" in resultado.recovered[0]["recovery_reason"]
    assert [c["task_id"] for c in chamadas] == ["T-001"]


def test_run_vivo_nao_e_recuperado(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")])
    task_ledger.start("P", "T-001", "run-vivo", tmp_path)
    recuperadas = task_ledger.recover_stale("P", "run-vivo", tmp_path)
    assert recuperadas == []


def test_declaracao_do_agente_nao_marca_verified(tmp_path: Path) -> None:
    """O agente jura que terminou; o build falha; a task NÃO fica verified."""
    _projeto(tmp_path, [_entry("T-001")])
    dispatch, verify, _ = _fakes(falha_em={"T-001"})

    def dispatch_otimista(ctx: dict) -> dict:
        saida = dispatch(ctx)
        saida["agent_result"] = {"implementation_status": "completed",
                                 "acceptance_results": [{"status": "passed"}]}
        return saida

    f4_loop.run("P", dispatch=dispatch_otimista, verify=verify, run_id="r1",
                repo_root=tmp_path)
    assert task_ledger.get("P", "T-001", tmp_path)["status"] != "verified"


def test_erro_de_roteamento_nao_cai_em_agente_generico(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001", stack="cobol")])
    # `task_type` vazio força a decisão pela stack, que é desconhecida.
    ledger = task_ledger.load("P", tmp_path)
    ledger["tasks"][0]["task_type"] = ""
    task_ledger.save("P", ledger, tmp_path)

    dispatch, verify, chamadas = _fakes()
    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)

    assert chamadas == [], "nenhum agente pode ser despachado sem rota"
    assert resultado.outcomes[0].error.startswith("ROUTE")
    assert resultado.functional_success is False
    assert task_ledger.get("P", "T-001", tmp_path)["executionStatus"] in {
        task_ledger.EXEC_FAILED_AFTER_REMEDIATION, task_ledger.EXEC_REVIEW}


def test_fila_vazia_com_pendencia_nao_vira_sucesso(tmp_path: Path) -> None:
    """T-002 depende de uma task bloqueada: fila vazia, mas nada concluído."""
    _projeto(tmp_path, [_entry("T-001"), _entry("T-002", depends_on=["T-001"], rank=1)])
    dispatch, verify, _ = _fakes(falha_em={"T-001"})
    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)
    assert resultado.status != task_ledger.COMPLETION_SUCCESS
    assert resultado.diagnosis["status"] in {"blocked_by_terminal", "waiting"}


# ─── Pré-condições (fail-closed) ─────────────────────────────────────────────

def test_razao_ausente_impede_a_f4(tmp_path: Path) -> None:
    task_ledger.REPO_ROOT = tmp_path
    (tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit").mkdir(parents=True)
    dispatch, verify, chamadas = _fakes()
    with pytest.raises(f4_loop.LoopError) as exc:
        f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                    repo_root=tmp_path)
    assert "despacho" in str(exc.value) or "razão" in str(exc.value)
    assert chamadas == []


def test_checksum_divergente_impede_a_f4(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")])
    trace = (tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
             / "traceability.json")
    trace.write_text(trace.read_text(encoding="utf-8") + " ", encoding="utf-8")
    dispatch, verify, chamadas = _fakes()
    with pytest.raises(f4_loop.LoopError):
        f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                    repo_root=tmp_path)
    assert chamadas == []


def test_gate_f4s_reprovado_impede_a_f4(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")], aprovado=False)
    dispatch, verify, chamadas = _fakes()
    with pytest.raises(f4_loop.LoopError) as exc:
        f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                    repo_root=tmp_path)
    assert "coders_released=false" in str(exc.value)
    assert chamadas == []
    assert task_ledger.get("P", "T-001", tmp_path)["status"] == "pending", (
        "nenhuma task pode ir para in_progress com o gate reprovado")


def test_log_de_execucao_registra_agente_e_rota(tmp_path: Path) -> None:
    _projeto(tmp_path, [_entry("T-001")])
    dispatch, verify, _ = _fakes()
    f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1", repo_root=tmp_path)

    log = json.loads(f4_loop.execution_log_path("P", tmp_path).read_text(encoding="utf-8"))
    entrada = log["entries"][0]
    assert entrada["task_id"] == "T-001"
    assert entrada["agent"] == "ava-stack-dotnet-backend"
    assert entrada["canonical_source_dir"] == "source-code/backend"
    assert entrada["routing_reason"]
    assert entrada["exit_code"] == 0


# ─── Toolchain ausente (regressão de cadastro-funcionario-03) ────────────────

def test_toolchain_ausente_nao_impede_as_demais_tasks(tmp_path: Path) -> None:
    """Faltou `ng`: TODAS as tasks são tentadas; as de frontend vão a `review`.

    A versão anterior parava de despachar a stack sem toolchain — e deixava
    tasks em `pending` ao fim da fase. O requisito é o oposto: toda task
    planejada recebe tentativa real e termina em estado terminal; limitação
    externa comprovada vira `review`, com o motivo registrado.
    """
    _projeto(tmp_path, [
        _entry("T-BE-001", stack="dotnet", task_type="backend"),
        _entry("T-FE-001", stack="angular", task_type="frontend", rank=1),
        _entry("T-FE-002", stack="angular", task_type="frontend", rank=2),
        _entry("T-BE-002", stack="dotnet", task_type="backend", rank=3),
    ])
    despachadas: list[str] = []

    def dispatch(ctx: dict) -> dict:
        despachadas.append(ctx["task_id"])
        return {"artifacts": [], "agent_result": {}}

    def verify(ctx: dict) -> dict:
        angular = ctx["route"].target_stack == "angular"
        exit_code = 127 if angular else 0
        estado = task_ledger.record_result(
            ctx["project"], ctx["task_id"], command="build", exit_code=exit_code,
            recorded_by="pipeline_runner", routing=ctx["route"].as_dict(),
            repo_root=ctx["repo_root"])
        if angular:
            estado = task_ledger.mark_execution(
                ctx["project"], ctx["task_id"], task_ledger.EXEC_REVIEW,
                review_reason="limitacao externa: toolchain `ng` ausente",
                repo_root=ctx["repo_root"])
        return {"status": estado["status"],
                "execution_status": task_ledger.execution_status_of(estado),
                "exit_code": exit_code,
                "command": "build", "files_written": [], "commit_hash": "",
                "toolchain_missing": "ng" if angular else ""}

    resultado = f4_loop.run("P", dispatch=dispatch, verify=verify, run_id="r1",
                            repo_root=tmp_path)

    assert {"T-BE-001", "T-BE-002", "T-FE-001", "T-FE-002"} <= set(despachadas), (
        "toda task planejada recebe tentativa real")
    assert task_ledger.get("P", "T-BE-002", tmp_path)["status"] == "verified"
    frontend = task_ledger.get("P", "T-FE-001", tmp_path)
    assert frontend["executionStatus"] == task_ledger.EXEC_REVIEW
    assert "toolchain" in frontend["reviewReason"]
    assert resultado.toolchain_missing == {"angular": "ng"}
    assert resultado.execution_complete is True, "nenhuma task fica pendente"
    assert resultado.summary["still_pending"] == 0
