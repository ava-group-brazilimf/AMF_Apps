#!/usr/bin/env python3
"""
f4_loop.py — Laço externo (Ralph Wiggum) da F4, dirigido pelo razão.

O laço externo faz UMA coisa por iteração: recarrega o razão do disco, recalcula
as tasks prontas, escolhe a próxima e a executa até um estado terminal. Não
existe lista estática de tasks: a conclusão de uma task libera dependentes, e
essas dependentes só aparecem porque a fila é recalculada **depois** de cada
iteração.

Por que não é o `expand_foreach`
--------------------------------
A expansão declarativa monta N passos uma única vez, no início da fase. Se a
task 7 desbloqueia a 41, a 41 já tinha sido classificada como "não pronta" e
saía do run — voltava só num `--resume`. Além disso, todo passo expandido
carregava o manifesto global da fase, o que fazia N despachos com o MESMO
contexto e o MESMO prompt.

Composição
----------
O laço não sabe falar com modelo nem rodar build. Ele recebe dois callables:

    dispatch(ctx)  -> dict   # implementa a task (etapas A–C do laço interno)
    verify(ctx)    -> dict   # build real + remediação + commit + razão (D–G)

É o que permite testá-lo inteiro sem SDK, sem rede e sem toolchain instalada.

Invariantes
-----------
* razão inválido, ausente ou com checksum divergente → a fase **não roda**;
* gate F4S reprovado → nenhum agente é despachado;
* roteamento sem agente especializado → erro registrado, nunca agente genérico;
* `verified` só existe se `verify` devolveu `exit_code == 0`;
* fila vazia com tasks não terminais → diagnóstico + BLOCKED/FAILED, nunca
  "concluído".
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import f4_gate  # noqa: E402
import f4_routing  # noqa: E402
import f4_task_context  # noqa: E402
import task_ledger  # noqa: E402

#: Teto de iterações do laço externo. É proteção contra giro em falso, não
#: orçamento: o normal é o laço parar por fila vazia, muito antes disto.
MAX_ITERATIONS = 1000

#: Nível máximo de redução de contexto por task (ver `f4_task_context`).
MAX_CONTEXT_LEVEL = 2

EXECUTION_LOG = "f4-execution-log.json"


class LoopError(Exception):
    """Condição que impede a F4 de rodar. Sempre antes de qualquer inferência."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class TaskOutcome:
    """Uma linha de observabilidade por task executada."""

    task_id: str
    status: str
    agent: str = ""
    routing_reason: str = ""
    component_type: str = ""
    target_stack: str = ""
    canonical_source_dir: str = ""
    feature: str = ""
    spec_id: str = ""
    attempt: int = 0
    started_at: str = ""
    ended_at: str = ""
    duration_s: float = 0.0
    exit_code: int | None = None
    command: str = ""
    files_written: list[str] = field(default_factory=list)
    commit_hash: str = ""
    previous_status: str = ""
    error: str = ""
    recovery_reason: str = ""
    context_chars: int = 0
    agent_contract: dict[str, Any] = field(default_factory=dict)
    #: Isolamento e rastreabilidade por task (branch, merge, artefatos).
    branch: str = ""
    base_branch: str = ""
    merged: bool = False
    merge_status: str = ""
    review_reason: str = ""
    excluded_from_commit: list[dict[str, str]] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    alternative_paths: list[dict[str, str]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    baseline: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {chave: valor for chave, valor in self.__dict__.items()}


@dataclass
class LoopResult:
    project: str
    run_id: str
    status: str = task_ledger.COMPLETION_FAILED
    reason: str = ""
    iterations: int = 0
    outcomes: list[TaskOutcome] = field(default_factory=list)
    recovered: list[dict[str, Any]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    execution_counts: dict[str, int] = field(default_factory=dict)
    diagnosis: dict[str, Any] = field(default_factory=dict)
    gate: dict[str, Any] = field(default_factory=dict)
    blocked_reason: str = ""
    #: Completude de execução ≠ sucesso funcional. O completeness gate lê os dois.
    execution_complete: bool = False
    functional_success: bool = False
    summary: dict[str, Any] = field(default_factory=dict)
    finalized: list[dict[str, Any]] = field(default_factory=list)
    toolchain_missing: dict[str, str] = field(default_factory=dict)
    #: Telemetria — nunca condição de parada.
    consecutive_skips: int = 0

    @property
    def ok(self) -> bool:
        """Encerramento CONTROLADO — não é o mesmo que sucesso funcional.

        A F4 termina bem quando processou tudo e registrou tudo. Task em
        revisão é resultado, não falha da fase: reprovar a fase inteira por
        causa de uma task foi o que deixou 162 tasks sem tentativa.
        """
        return self.status in {task_ledger.COMPLETION_SUCCESS,
                               task_ledger.COMPLETION_PARTIAL,
                               task_ledger.COMPLETION_WITH_REVIEW}

    @property
    def verified(self) -> int:
        return sum(1 for item in self.outcomes
                   if item.status in {task_ledger.EXEC_COMPLETED,
                                      task_ledger.EXEC_COMPLETED_WARN,
                                      "verified"})

    @property
    def artifacts(self) -> list[str]:
        vistos: list[str] = []
        for item in self.outcomes:
            for arquivo in item.files_written:
                if arquivo not in vistos:
                    vistos.append(arquivo)
        return vistos

    def as_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "run_id": self.run_id,
            "status": self.status,
            "reason": self.reason,
            "iterations": self.iterations,
            "verified": self.verified,
            "counts": dict(self.counts),
            "recovered": list(self.recovered),
            "diagnosis": dict(self.diagnosis),
            "gate": dict(self.gate),
            "execution_counts": dict(self.execution_counts),
            "execution_complete": self.execution_complete,
            "functional_success": self.functional_success,
            "summary": dict(self.summary),
            "toolchain_missing": dict(self.toolchain_missing),
            "consecutive_skips": self.consecutive_skips,
            "tasks": [item.as_dict() for item in self.outcomes],
        }


# ─── Pré-condições ───────────────────────────────────────────────────────────

def preflight(project: str, repo_root: Path | None = None, *,
              check_gate: bool = True,
              require_checksum: bool = True) -> dict[str, Any]:
    """Tudo que precisa ser verdade antes do primeiro despacho.

    Levanta `LoopError` — nunca degrada para despacho único, nunca segue com
    aviso. As duas condições que este bloco existe para impedir são o razão
    ausente (que virava um prompt monolítico) e o scaffold não aprovado (que
    virava feature gerada sobre um baseline que não compila).
    """
    root = repo_root or REPO_ROOT
    try:
        task_ledger.ensure_enriched(project, root)
        ledger_info = task_ledger.validate(project, root,
                                           require_checksum=require_checksum)
    except task_ledger.LedgerError as exc:
        raise LoopError(str(exc)) from exc

    gate_info: dict[str, Any] = {}
    if check_gate:
        resultado = f4_gate.check(project, root)
        gate_info = resultado.as_dict()
        if not resultado.ok:
            raise LoopError(resultado.message())

    problemas = f4_routing.validate_routing_table(root)
    if problemas:
        raise LoopError(
            "tabela de roteamento incoerente com o agent_registry:\n  - "
            + "\n  - ".join(problemas))

    return {"ledger": ledger_info, "gate": gate_info}


# ─── Observabilidade ─────────────────────────────────────────────────────────

def execution_log_path(project: str, repo_root: Path | None = None) -> Path:
    return ((repo_root or REPO_ROOT) / "projects" / project / "outputs" / "tobe"
            / "speckit" / EXECUTION_LOG)


def append_execution_log(project: str, entry: dict[str, Any],
                         repo_root: Path | None = None) -> None:
    """Append idempotente ao log de execução da F4. Nunca derruba o laço."""
    caminho = execution_log_path(project, repo_root)
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        dados: dict[str, Any] = {"schema_version": "1.0.0", "project": project,
                                 "entries": []}
        if caminho.is_file():
            try:
                carregado = json.loads(caminho.read_text(encoding="utf-8"))
                if isinstance(carregado, dict) and isinstance(carregado.get("entries"), list):
                    dados = carregado
            except (OSError, json.JSONDecodeError):
                pass
        dados["entries"].append(entry)
        dados["updated_at"] = _now()
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    except OSError:
        return


# ─── Laço ────────────────────────────────────────────────────────────────────

def _select(project: str, repo_root: Path,
            ja_tentadas: set[str] | None = None
            ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Próxima task pronta. Toda task pronta é tentada — sem exceção de stack.

    `ja_tentadas` guarda os ids já despachados neste run e nunca-verificados:
    sem isso, uma task que volta a `failed` seria escolhida de novo antes das
    outras (o razão a mantém pronta), e o laço giraria numa task só até o teto
    de tentativas — deixando as demais para o fim.
    """
    vistas = ja_tentadas or set()
    tasks = task_ledger.load(project, repo_root).get("tasks", [])
    prontas = task_ledger.ready_tasks(project, repo_root=repo_root)
    frescas = [t for t in prontas if t["task_id"] not in vistas]
    # Sem task nova, volta às já tentadas — é a retentativa do laço interno.
    fila = frescas or prontas
    return (fila[0] if fila else None), tasks


def _finalize(project: str, root: Path,
              on_event: Callable[[str, dict[str, Any]], None] | None = None
              ) -> list[dict[str, Any]]:
    """Fecha o razão: nenhuma task pode terminar a fase em `pending`.

    Duas classes de sobra, e cada uma tem um nome próprio:

    * dependência explícita em estado terminal ruim → `blocked_by_dependency`;
    * sem dependência que explique (ciclo, grafo quebrado, task órfã) →
      `review`, com o diagnóstico do razão como motivo.

    Nunca `skipped`, e nunca deixar `pending`: "não sei o que aconteceu" é
    exatamente o estado que o completeness gate existe para não aceitar.
    """
    fechadas = task_ledger.classify_pending_dependencies(project, root)

    ledger = task_ledger.load(project, root)
    conhecidas = {t["task_id"] for t in ledger.get("tasks", [])}
    diagnostico = task_ledger.diagnose(project, root)
    for task in ledger.get("tasks", []):
        if task_ledger.execution_status_of(task) in task_ledger.EXECUTION_TERMINAL:
            continue
        deps = [d for d in (list(task.get("depends_on") or [])
                            + list(task.get("backend_dependencies") or []))
                if d in conhecidas]
        # `completed_with_warnings` É conclusão: a task entregou os artefatos e
        # só a validação externa reclamou. Tratá-la como pendência bloquearia em
        # cascata tudo que depende de uma task de infraestrutura.
        concluidos = {task_ledger.EXEC_COMPLETED, task_ledger.EXEC_COMPLETED_WARN}
        pendentes = [d for d in deps
                     if task_ledger.execution_status_of(
                         next(t for t in ledger["tasks"] if t["task_id"] == d))
                     not in concluidos]
        if pendentes:
            task_ledger.mark_execution(
                project, task["task_id"],
                task_ledger.EXEC_BLOCKED_BY_DEPENDENCY,
                review_reason=("dependencia(s) nunca concluida(s): "
                               + ", ".join(pendentes)),
                blocked_by=pendentes, repo_root=root)
        else:
            task_ledger.mark_execution(
                project, task["task_id"], task_ledger.EXEC_REVIEW,
                review_reason=(f"task nao alcancada pelo laco "
                               f"(diagnostico do razao: {diagnostico.get('status')})"),
                repo_root=root)
        fechadas.append({"task_id": task["task_id"], "blockedByTaskIds": pendentes})

    if fechadas and on_event:
        on_event("finalized", {"tasks": fechadas})
    return fechadas


def run(project: str, *,
        dispatch: Callable[[dict[str, Any]], dict[str, Any]],
        verify: Callable[[dict[str, Any]], dict[str, Any]],
        run_id: str,
        repo_root: Path | None = None,
        max_iterations: int = MAX_ITERATIONS,
        check_gate: bool = True,
        require_checksum: bool = True,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
        max_tasks: int | None = None) -> LoopResult:
    """Executa a F4 inteira, uma task por vez, até uma condição terminal."""
    root = repo_root or REPO_ROOT
    resultado = LoopResult(project=project, run_id=run_id)

    def evento(nome: str, dados: dict[str, Any]) -> None:
        if on_event:
            try:
                on_event(nome, dados)
            except Exception:  # noqa: BLE001 — observabilidade nunca derruba o laço
                pass

    precondicoes = preflight(project, root, check_gate=check_gate,
                             require_checksum=require_checksum)
    resultado.gate = precondicoes.get("gate", {})
    evento("preflight", precondicoes)

    # Retomada: tasks presas em `in_progress` de um run morto voltam para a fila
    # ANTES de a fila ser lida pela primeira vez.
    resultado.recovered = task_ledger.recover_stale(project, run_id, root)
    if resultado.recovered:
        evento("recovered", {"tasks": resultado.recovered})

    executadas = 0
    stacks_sem_toolchain: dict[str, str] = {}
    tentadas: set[str] = set()
    baselines: dict[str, dict[str, Any]] = {}
    while resultado.iterations < max_iterations:
        if max_tasks is not None and executadas >= max_tasks:
            resultado.reason = f"limite de {max_tasks} task(s) desta execucao atingido"
            break

        # (1) o razão é relido do disco a cada volta: ele é a fonte, não a
        #     memória do processo, e outra ferramenta pode tê-lo movido.
        task, todas = _select(project, root, tentadas)
        if task is None:
            break

        resultado.iterations += 1
        task_id = str(task["task_id"])
        status_anterior = str(task.get("status") or "")
        inicio = time.time()

        registro = TaskOutcome(
            task_id=task_id,
            status="dispatch_failed",
            feature=str(task.get("feature") or ""),
            spec_id=str(task.get("spec_id") or ""),
            previous_status=status_anterior,
            recovery_reason=str(task.get("recovery_reason") or ""),
            started_at=_now(),
            attempt=int(task.get("attempts", 0) or 0) + 1,
        )

        # (2) roteamento ANTES de marcar in_progress: uma task sem agente
        #     especializado não pode consumir tentativa de implementação.
        try:
            route = f4_routing.resolve_route(task, project, root)
        except f4_routing.RoutingError as exc:
            registro.status = "routing_failed"
            registro.error = f"{exc.code}: {exc}"
            registro.ended_at = _now()
            registro.duration_s = round(time.time() - inicio, 2)
            estado = task_ledger.record_result(
                project, task_id,
                command=f"<routing:{exc.code}>", exit_code=78,
                log_path=None, files_written=None,
                recorded_by="pipeline_runner",
                summary_text=str(exc), repo_root=root,
                routing={"error": exc.as_dict()})
            registro.status = estado["status"]
            resultado.outcomes.append(registro)
            append_execution_log(project, registro.as_dict(), root)
            evento("routing_failed", registro.as_dict())
            continue

        registro.agent = route.agent
        registro.routing_reason = route.reason
        registro.component_type = route.component_type
        registro.target_stack = route.target_stack
        registro.canonical_source_dir = route.canonical_source_rel

        # (3) marca in_progress e PERSISTE antes de gastar inferência: se o
        #     processo morrer no despacho, a retomada sabe onde estava.
        try:
            task = task_ledger.start(project, task_id, run_id, root)
        except task_ledger.LedgerError as exc:
            registro.status = "not_ready"
            registro.error = str(exc)
            resultado.outcomes.append(registro)
            evento("not_ready", registro.as_dict())
            continue

        tentadas.add(task_id)

        # (3b) baseline do scaffold — uma vez por componente, antes da primeira
        #      task dele. É o que separa "a task quebrou o build" de "o scaffold
        #      já estava vermelho", e o que prova que o scaffold foi REUSADO.
        contexto_branch = _prepare_workspace(project, task, route, root, baselines)
        if contexto_branch.get("scaffold_missing"):
            task_ledger.mark_execution(
                project, task_id, task_ledger.EXEC_REVIEW,
                review_reason=(f"erro estrutural: scaffold de "
                               f"{route.component_type} nao localizado em "
                               f"{contexto_branch.get('scaffold_path')} — a F4 "
                               f"nao recria scaffold"),
                fields={"scaffoldPath": contexto_branch.get("scaffold_path"),
                        "scaffoldReused": False, "scaffoldRecreated": False,
                        "finishedAt": _now()},
                repo_root=root)
            registro.status = task_ledger.EXEC_REVIEW
            registro.error = "scaffold ausente"
            registro.ended_at = _now()
            resultado.outcomes.append(registro)
            append_execution_log(project, registro.as_dict(), root)
            evento("scaffold_missing", registro.as_dict())
            continue

        contexto = {
            "project": project,
            "run_id": run_id,
            "task": task,
            "task_id": task_id,
            "route": route,
            "attempt": registro.attempt,
            "ledger_tasks": todas,
            "repo_root": root,
            "branch_context": contexto_branch,
            "context_level": min(MAX_CONTEXT_LEVEL,
                                 max(0, int(task.get("context_level") or 0))),
        }
        evento("task_start", {"task_id": task_id, "agent": route.agent,
                              "attempt": registro.attempt,
                              "routing_reason": route.reason})

        # (4) implementação (laço interno A–C dentro do agente).
        try:
            despacho = dispatch(contexto) or {}
        except Exception as exc:  # noqa: BLE001 — falha de despacho não derruba a fase
            despacho = {"error": f"{type(exc).__name__}: {exc}"}
        registro.context_chars = int(despacho.get("context_chars", 0) or 0)
        registro.agent_contract = dict(despacho.get("agent_result") or {})

        if despacho.get("error"):
            registro.error = str(despacho["error"])
            estado = task_ledger.record_result(
                project, task_id,
                command=f"<dispatch:{route.agent}>", exit_code=70,
                log_path=despacho.get("log"), files_written=None,
                recorded_by="pipeline_runner", routing=route.as_dict(),
                summary_text=registro.error,
                agent_result=registro.agent_contract or None, repo_root=root)
            registro.status = estado["status"]
            registro.ended_at = _now()
            registro.duration_s = round(time.time() - inicio, 2)
            resultado.outcomes.append(registro)
            append_execution_log(project, registro.as_dict(), root)
            evento("task_end", registro.as_dict())
            executadas += 1
            continue

        # (5) verificação determinística (D–G) — a ÚNICA porta para `verified`.
        contexto["dispatch"] = despacho
        verificacao = verify(contexto) or {}
        registro.status = str(verificacao.get("execution_status")
                              or verificacao.get("status") or "failed")
        registro.exit_code = verificacao.get("exit_code")
        registro.command = str(verificacao.get("command") or "")
        registro.files_written = list(verificacao.get("files_written") or [])
        registro.commit_hash = str(verificacao.get("commit_hash") or "")
        registro.branch = str(verificacao.get("branch") or "")
        registro.base_branch = str(contexto_branch.get("base") or "")
        registro.merged = bool(verificacao.get("merged"))
        registro.merge_status = str(verificacao.get("merge_status") or "")
        registro.review_reason = str(verificacao.get("review_reason") or "")
        registro.excluded_from_commit = list(
            verificacao.get("excluded_from_commit") or [])
        registro.missing_artifacts = list(verificacao.get("missing_artifacts") or [])
        registro.alternative_paths = list(verificacao.get("alternative_paths") or [])
        registro.validation = dict(verificacao.get("validation") or {})
        registro.baseline = dict(contexto_branch.get("baseline") or {})
        registro.ended_at = _now()
        registro.duration_s = round(time.time() - inicio, 2)
        if verificacao.get("error"):
            registro.error = str(verificacao["error"])

        resultado.outcomes.append(registro)
        append_execution_log(project, registro.as_dict(), root)
        evento("task_end", registro.as_dict())
        executadas += 1

        # Toolchain ausente vira telemetria e `review` na task (limitação
        # externa comprovada) — não motivo para pular as demais tasks da stack.
        # Toda task planejada recebe tentativa real; nenhuma fica `pending`.
        faltando = str(verificacao.get("toolchain_missing") or "")
        if faltando:
            stack = str(route.target_stack or "").lower()
            if stack not in stacks_sem_toolchain:
                evento("toolchain_missing", {"stack": stack,
                                             "executable": faltando,
                                             "task_id": task_id})
            stacks_sem_toolchain[stack] = faltando

        # `abort_needed` do harness é TELEMETRIA. Ele não interrompe mais a
        # fase: três specs seguidas falhando é sinal para o relatório, não
        # motivo para abandonar as 160 tasks restantes.
        if verificacao.get("abort_needed"):
            resultado.consecutive_skips += 1
            evento("consecutive_skips",
                   {"count": resultado.consecutive_skips, "task_id": task_id})

    # ── Fechamento: nenhuma task pode sobrar em `pending` ───────────────────
    if max_tasks is None:
        resultado.finalized = _finalize(project, root, evento)

    veredito = task_ledger.completion_status(project, root)
    resultado.counts = veredito.get("counts", {})
    resultado.execution_counts = veredito.get("execution_counts", {})
    resultado.execution_complete = bool(veredito.get("execution_complete"))
    resultado.functional_success = bool(veredito.get("functional_success"))
    resultado.status = veredito["status"]
    resultado.reason = resultado.reason or veredito["reason"]
    resultado.toolchain_missing = dict(stacks_sem_toolchain)

    if not resultado.functional_success:
        # Fila vazia com pendência é diagnóstico, nunca conclusão silenciosa.
        resultado.diagnosis = task_ledger.diagnose(project, root)
    if stacks_sem_toolchain:
        resultado.diagnosis = dict(resultado.diagnosis or {})
        resultado.diagnosis["toolchain_missing"] = dict(stacks_sem_toolchain)
    if resultado.iterations >= max_iterations:
        resultado.status = task_ledger.COMPLETION_FAILED
        resultado.reason = (f"teto de {max_iterations} iteracoes atingido — "
                            f"o laco foi interrompido para nao girar em falso")

    resultado.summary = build_summary(project, resultado, root)
    evento("loop_end", resultado.as_dict())
    return resultado


def build_summary(project: str, resultado: "LoopResult",
                  repo_root: Path | None = None) -> dict[str, Any]:
    """Relatório final da F4 — o que foi entregue, o que precisa de gente."""
    root = repo_root or REPO_ROOT
    tasks = task_ledger.load(project, root).get("tasks", [])
    por_estado: dict[str, list[str]] = {}
    for task in tasks:
        por_estado.setdefault(task_ledger.execution_status_of(task), []).append(
            task["task_id"])

    integrados = [o.task_id for o in resultado.outcomes if o.merged]
    preservados = [o.task_id for o in resultado.outcomes
                   if o.branch and not o.merged]
    excluidos = [item for o in resultado.outcomes for item in o.excluded_from_commit]
    alternativos = [item for o in resultado.outcomes for item in o.alternative_paths]
    ausentes = [item for o in resultado.outcomes for item in o.missing_artifacts]

    return {
        "planned": len(tasks),
        "executed": len(resultado.outcomes),
        "completed": len(por_estado.get(task_ledger.EXEC_COMPLETED, [])),
        "completed_with_warnings": len(
            por_estado.get(task_ledger.EXEC_COMPLETED_WARN, [])),
        "review": len(por_estado.get(task_ledger.EXEC_REVIEW, [])),
        "failed_after_remediation": len(
            por_estado.get(task_ledger.EXEC_FAILED_AFTER_REMEDIATION, [])),
        "blocked_by_dependency": len(
            por_estado.get(task_ledger.EXEC_BLOCKED_BY_DEPENDENCY, [])),
        "still_pending": len(por_estado.get(task_ledger.EXEC_PENDING, []))
        + len(por_estado.get(task_ledger.EXEC_RUNNING, [])),
        "branches_merged": integrados,
        "branches_preserved_for_review": preservados,
        "artifacts_expected_and_found": sum(
            len(o.files_written) for o in resultado.outcomes),
        "artifacts_missing": ausentes,
        "artifacts_in_alternative_paths": alternativos,
        "files_excluded_from_commit": excluidos,
        "toolchain_missing": dict(resultado.toolchain_missing),
        "consecutive_skips_observed": resultado.consecutive_skips,
        "execution_complete": resultado.execution_complete,
        "functional_success": resultado.functional_success,
        "by_execution_status": por_estado,
    }


def _prepare_workspace(project: str, task: dict[str, Any], route: Any,
                       root: Path, baselines: dict[str, dict[str, Any]]
                       ) -> dict[str, Any]:
    """Baseline do componente + branch local exclusivo da task.

    O branch é criado **antes** do despacho, para que tudo que o agente escrever
    já nasça isolado: é isso que permite preservar a tentativa de uma task que
    não compilou sem contaminar o branch principal nem a task seguinte.
    """
    import f4_baseline  # noqa: PLC0415
    import f4s_git_helper as git  # noqa: PLC0415

    componente = route.component_type
    repo = route.repo_dir
    work_dir = route.canonical_source_dir
    contexto: dict[str, Any] = {"component_type": componente,
                                "scaffold_path": work_dir.as_posix()}

    if componente not in baselines:
        baselines[componente] = f4_baseline.ensure(
            repo, work_dir, componente, route.target_stack)
    baseline = baselines[componente]
    contexto["baseline"] = baseline

    # Infra não tem scaffold da F4S: o diretório é criado por demanda.
    if componente == "infra":
        work_dir.mkdir(parents=True, exist_ok=True)
    elif baseline.get("status") == "scaffold_missing":
        contexto["scaffold_missing"] = True
        return contexto

    try:
        base = git.current_branch(repo)
        if base.startswith("task/"):
            # Um run anterior morreu dentro de um branch de task; a base é o
            # branch principal, não o branch da task que ficou aberta.
            base = "main" if git.branch_exists(repo, "main") else base
            git.checkout_branch(repo, base)
        branch = git.task_branch_name(str(task.get("task_id")),
                                      str(task.get("title") or ""))
        # Branch de execução anterior é EVIDÊNCIA: não se reaproveita nem se
        # apaga. Reusá-lo colocava o trabalho novo sobre um `main` antigo, e o
        # merge de volta conflitava — foi o que deixou `T-W0-SCF-007` em
        # `review` com `mergeStatus: conflict`.
        if git.branch_exists(repo, branch) and not git.is_ancestor(repo, base, branch):
            sufixo = 2
            while git.branch_exists(repo, f"{branch}--r{sufixo}"):
                sufixo += 1
            contexto["previous_branch"] = branch
            branch = f"{branch}--r{sufixo}"
        git.checkout_branch(repo, branch, create=True, base=base)
        contexto.update({"branch": branch, "base": base})
    except Exception as exc:  # noqa: BLE001 — sem git a task ainda roda
        contexto.update({"branch": "", "base": "",
                         "branch_error": f"{type(exc).__name__}: {exc}"})
    return contexto


def build_task_context(ctx: dict[str, Any], *, failure_context: str = "") -> str:
    """Atalho: contexto mínimo da task do `ctx` corrente."""
    return f4_task_context.build(
        ctx["project"], ctx["task"], ctx["route"],
        ledger_tasks=ctx.get("ledger_tasks"),
        attempt=int(ctx.get("attempt", 1)),
        level=int(ctx.get("context_level", 0)),
        failure_context=failure_context,
        repo_root=ctx.get("repo_root"))
