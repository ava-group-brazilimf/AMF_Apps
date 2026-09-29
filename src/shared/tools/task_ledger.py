#!/usr/bin/env python3
"""
AVA Fabric — Razão de progresso da geração de código
=====================================================
Mantém ``projects/{p}/outputs/tobe/speckit/tasks-progress.json``: uma linha por task de
implementação, com o status movido **exclusivamente por exit code real**.

Por que existe
--------------
Quando a F4 deixa de ser um despacho único e vira N chamadas (spec 039, Fase 3),
cada chamada começa com janela de contexto nova e precisa saber o que já foi
construído. O padrão de harness para agentes de execução longa resolve isso com
dois artefatos duráveis: uma lista de features com status e um log de progresso.

**Um desvio deliberado em relação a esse padrão.** No padrão original, o próprio
agente vira o `passes` da feature depois de testar. Aqui ele não pode. A auditoria
de ``nopcommerce-02-cli-ava`` encontrou:

* relatórios declarando ``Build Status: ✅ PASS (Simulated — toolchain validation
  pending)`` enquanto ``dotnet build`` falhava com 1 + 35 + 8 erros (RC-02);
* uma matriz de rastreabilidade marcando 15/15 linhas ✅ para classes que não
  existiam no código gerado (RC-03).

Um agente que se auto-declara concluído é precisamente a falha que este projeto já
tem. Portanto: **agentes nunca escrevem aqui**. Quem escreve é esta ferramenta,
chamada pelo wrapper de passo depois de rodar ``verify.ps1`` e as suítes de check.
``record_result`` recusa qualquer ``recorded_by`` que pareça um agente.

Dois arquivos, duas vidas
-------------------------
``traceability.json`` é a espinha **imutável** — proveniência de cada task, fixada
ao fim da F3S e conferida por checksum. ``tasks-progress.json`` é o razão **mutável**.
Não são fundidos de propósito: se estado e proveniência morassem no mesmo arquivo,
uma escrita de progresso poderia corromper a rastreabilidade.

JSON, e não Markdown, pela mesma razão que o padrão de harness recomenda: o modelo
tem muito menos probabilidade de reescrever ou reformatar um arquivo JSON.

Uso
---
    python task_ledger.py -p Meu-ERP --init
    python task_ledger.py -p Meu-ERP --summary
    python task_ledger.py -p Meu-ERP --next [--group G-CART] [--stack dotnet]
    python task_ledger.py -p Meu-ERP --groups --json

Exit codes
----------
    0 — ok      1 — nada pendente / razão inconsistente      2 — erro de configuração
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import dependency_graph  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "3.0.0"

#: Teto de tentativas por task. Acima disso a task é **exposta**, não retentada
#: para sempre: um loop de reparo silencioso esconde o defeito real.
MAX_ATTEMPTS = 3

#: Quem pode gravar evidência. Agente nunca — ver docstring do módulo.
_TOOL_WRITERS = frozenset({"task_ledger", "ava_pipeline", "pipeline_runner", "verify"})
_AGENT_NAME = re.compile(r"^ava-[a-z0-9-]+$")

_TERMINAL = frozenset({"verified", "skipped", "blocked"})

# ─── Vocabulário de execução (`executionStatus`) ─────────────────────────────
#
# `status` continua com o vocabulário legado — gates, suites de check e
# dashboards leem esse campo, e mudá-lo quebraria todos de uma vez. `execution_
# status` é o vocabulário novo, aditivo, que a F4 usa para distinguir o que o
# legado não distinguia: "falhou e precisa de gente" não é a mesma coisa que
# "não pôde rodar porque a dependência falhou", e "gerou tudo mas a validação
# externa reclamou" não é a mesma coisa que "não entregou".
EXEC_PENDING = "pending"
EXEC_RUNNING = "running"
EXEC_REMEDIATION = "remediation"
EXEC_COMPLETED = "completed"
EXEC_COMPLETED_WARN = "completed_with_warnings"
EXEC_REVIEW = "review"
EXEC_FAILED_AFTER_REMEDIATION = "failed_after_remediation"
EXEC_BLOCKED_BY_DEPENDENCY = "blocked_by_dependency"

EXECUTION_STATUSES: frozenset[str] = frozenset({
    EXEC_PENDING, EXEC_RUNNING, EXEC_REMEDIATION, EXEC_COMPLETED,
    EXEC_COMPLETED_WARN, EXEC_REVIEW, EXEC_FAILED_AFTER_REMEDIATION,
    EXEC_BLOCKED_BY_DEPENDENCY,
})

#: Estados de execução terminais — a task foi processada e não volta para a fila.
EXECUTION_TERMINAL: frozenset[str] = frozenset({
    EXEC_COMPLETED, EXEC_COMPLETED_WARN, EXEC_REVIEW,
    EXEC_FAILED_AFTER_REMEDIATION, EXEC_BLOCKED_BY_DEPENDENCY,
})

#: Tradução para o campo legado. `completed_with_warnings` só mapeia para
#: `verified` porque, nesse caminho, a prova determinística que subiu o status é
#: a reconciliação de artefatos com exit 0 — a validação externa que reclamou
#: fica registrada em `validationResults`, separada. O invariante continua:
#: `verified` exige exit code 0 de uma verificação real.
_LEGACY_STATUS: dict[str, str] = {
    EXEC_PENDING: "pending",
    EXEC_RUNNING: "in_progress",
    EXEC_REMEDIATION: "in_progress",
    EXEC_COMPLETED: "verified",
    EXEC_COMPLETED_WARN: "verified",
    EXEC_REVIEW: "blocked",
    EXEC_FAILED_AFTER_REMEDIATION: "blocked",
    EXEC_BLOCKED_BY_DEPENDENCY: "blocked",
}


def legacy_status_for(execution_status: str) -> str:
    """Campo `status` correspondente a um `executionStatus`."""
    valor = str(execution_status or "").strip().lower()
    if valor not in EXECUTION_STATUSES:
        raise LedgerError(
            f"executionStatus desconhecido: {execution_status!r} "
            f"(aceitos: {', '.join(sorted(EXECUTION_STATUSES))})")
    return _LEGACY_STATUS[valor]


def execution_status_of(task: dict[str, Any]) -> str:
    """`executionStatus` da task, derivado do legado quando ausente.

    Razões criados antes deste vocabulário continuam legíveis: `verified` vira
    `completed`, `blocked` vira `review`, e assim por diante.
    """
    valor = str(task.get("executionStatus") or "").strip().lower()
    if valor in EXECUTION_STATUSES:
        return valor
    legado = str(task.get("status") or "pending")
    return {
        "pending": EXEC_PENDING,
        "in_progress": EXEC_RUNNING,
        "verified": EXEC_COMPLETED,
        "failed": EXEC_RUNNING,
        "blocked": EXEC_REVIEW,
        "skipped": EXEC_REVIEW,
    }.get(legado, EXEC_PENDING)


class LedgerError(Exception):
    """Erro de uso do razão. O CLI converte em exit 2."""


# ─── Caminhos ────────────────────────────────────────────────────────────────

def _speckit_dir(project: str, repo_root: Path) -> Path:
    return repo_root / "projects" / project / "outputs" / "tobe" / "speckit"


def ledger_path(project: str, repo_root: Path | None = None) -> Path:
    return _speckit_dir(project, repo_root or REPO_ROOT) / "tasks-progress.json"


#: Nome anterior do razão, antes da padronização de schema. Projetos gerados
#: com a esteira antiga têm este arquivo e nenhum `tasks-progress.json` — a F4
#: não pode usá-lo às escondidas nem ignorá-lo em silêncio. Ver `migrate_legacy`.
LEGACY_LEDGER_FILENAME = "tasks-state.json"


def legacy_ledger_path(project: str, repo_root: Path | None = None) -> Path:
    return _speckit_dir(project, repo_root or REPO_ROOT) / LEGACY_LEDGER_FILENAME


def traceability_path(project: str, repo_root: Path | None = None) -> Path:
    return _speckit_dir(project, repo_root or REPO_ROOT) / "traceability.json"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# ─── Leitura / escrita ───────────────────────────────────────────────────────

def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LedgerError(f"arquivo ausente: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LedgerError(f"JSON inválido em {path}: {exc}") from exc


def load(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    path = ledger_path(project, repo_root)
    if not path.is_file():
        raise LedgerError(
            f"razão de progresso ausente: {path}\n"
            f"      Rode: python src/shared/tools/task_ledger.py -p {project} --init")
    return _read_json(path)


def save(project: str, ledger: dict[str, Any], repo_root: Path | None = None) -> None:
    """Escrita atômica: arquivo temporário + ``os.replace``.

    O razão é reescrito a cada transição de task, e uma interrupção no meio de
    um `write_text` deixaria JSON pela metade — isto é, a esteira perderia o
    progresso justamente no cenário em que o razão existe para salvá-lo.
    """
    path = ledger_path(project, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = _now()
    payload = json.dumps(ledger, ensure_ascii=False, indent=2) + "\n"
    fd, temporario = tempfile.mkstemp(dir=str(path.parent),
                                      prefix=".tasks-progress.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_com_retry(temporario, path)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise


#: Windows devolve `PermissionError` transitório em `os.replace` quando o
#: destino está momentaneamente aberto (antivírus, indexador, um leitor
#: concorrente do razão). Não é corrupção — é o SO pedindo milissegundos.
_REPLACE_TENTATIVAS = 5
_REPLACE_ESPERA_S = 0.05


def _replace_com_retry(origem: str, destino: Path) -> None:
    for tentativa in range(1, _REPLACE_TENTATIVAS + 1):
        try:
            os.replace(origem, destino)
            return
        except PermissionError:
            if tentativa == _REPLACE_TENTATIVAS:
                raise
            time.sleep(_REPLACE_ESPERA_S * tentativa)


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checksum_matches(project: str, repo_root: Path | None = None) -> bool:
    """A espinha é imutável depois da F3S. Divergência invalida o razão."""
    ledger = load(project, repo_root)
    trace = traceability_path(project, repo_root)
    if not trace.is_file():
        return False
    return ledger.get("traceability_checksum") == _checksum(trace)


def validate(project: str, repo_root: Path | None = None, *,
             require_checksum: bool = True) -> dict[str, Any]:
    """Confere o razão antes de a F4 gastar um token. Levanta `LedgerError`.

    Fail-closed de propósito: razão ausente, schema desconhecido ou espinha
    alterada depois do `--init` são condições em que a F4 **não roda**. O
    comportamento antigo — degradar para despacho único — reintroduzia
    exatamente o defeito que o razão existe para fechar (140 arquivos numa
    resposta só).
    """
    root = repo_root or REPO_ROOT
    caminho = ledger_path(project, root)
    if not caminho.is_file():
        legado = legacy_ledger_path(project, root)
        extra = (f"\n      Existe `{LEGACY_LEDGER_FILENAME}` neste projeto: rode "
                 f"`task_ledger.py -p {project} --migrate-legacy` para converte-lo."
                 if legado.is_file() else "")
        raise LedgerError(
            f"razão de progresso ausente: {caminho}{extra}\n"
            f"      Sem ele a F4 não roda: a alternativa seria um despacho "
            f"monolítico, que é o defeito original.")

    ledger = load(project, root)
    versao = str(ledger.get("schema_version") or "")
    if versao != SCHEMA_VERSION:
        raise LedgerError(
            f"razão com schema_version={versao!r}; esperado {SCHEMA_VERSION!r} "
            f"({caminho})\n      Reexecute `task_ledger.py -p {project} --init`.")

    tasks = ledger.get("tasks")
    if not isinstance(tasks, list):
        raise LedgerError(f"razão sem lista `tasks` legível: {caminho}")

    trace = traceability_path(project, root)
    checksum_ok = trace.is_file() and (
        ledger.get("traceability_checksum") == _checksum(trace))
    if require_checksum and not checksum_ok:
        raise LedgerError(
            f"traceability.json diverge do checksum registrado no razão.\n"
            f"      A espinha é imutável depois da F3S; se ela mudou, o razão "
            f"não descreve mais o mesmo grafo.\n"
            f"      Reconcilie a F3S e rode `task_ledger.py -p {project} --init` "
            f"(o progresso verificado é preservado).")

    return {
        "path": str(caminho),
        "schema_version": versao,
        "tasks": len(tasks),
        "checksum_ok": checksum_ok,
        "counts": summary(project, root),
    }


#: Campos que a F4 precisa por task para montar contexto mínimo. Razões criados
#: antes desta versão não os têm — e sem `feature` todo despacho volta a receber
#: as specs de todas as features.
_ENRICHED_FIELDS = ("feature", "title", "target_files")


def ensure_enriched(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Reidrata um razão antigo a partir da espinha, preservando o progresso.

    `init()` é idempotente e mantém `status`, `attempts`, `evidence` e
    `files_written` de cada task; a única coisa que ele refaz são os campos
    derivados do `traceability.json`. Por isso é seguro chamar aqui quando o
    razão em disco é anterior aos campos de contexto por task.
    """
    root = repo_root or REPO_ROOT
    ledger = load(project, root)
    tasks = ledger.get("tasks") or []
    if not tasks:
        return {"status": "skipped", "reason": "razão sem tasks"}
    faltando = [campo for campo in _ENRICHED_FIELDS
                if any(campo not in task for task in tasks)]
    if not faltando:
        return {"status": "current", "reason": "razão já tem os campos de contexto"}
    if not traceability_path(project, root).is_file():
        return {"status": "skipped",
                "reason": "traceability.json ausente; nada a reidratar",
                "missing_fields": faltando}
    novo = init(project, root)
    return {"status": "enriched", "missing_fields": faltando,
            "tasks": len(novo.get("tasks") or [])}


def migrate_legacy(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Converte `tasks-state.json` (nome antigo) em `tasks-progress.json`.

    Idempotente e conservadora: com o razão atual já em disco, não faz nada —
    progresso válido nunca é sobrescrito. Schema incompatível **não** é migrado
    às escondidas: levanta erro acionável, porque usar um arquivo com outro
    contrato calado é como a F4 herdaria estado errado sem ninguém notar.
    """
    root = repo_root or REPO_ROOT
    atual = ledger_path(project, root)
    legado = legacy_ledger_path(project, root)

    if atual.is_file():
        return {"status": "skipped", "reason": "razão atual já existe",
                "path": str(atual)}
    if not legado.is_file():
        raise LedgerError(
            f"nada a migrar: nem {atual.name} nem {LEGACY_LEDGER_FILENAME} "
            f"existem em {atual.parent}")

    dados = _read_json(legado)
    versao = str(dados.get("schema_version") or "")
    if versao != SCHEMA_VERSION or not isinstance(dados.get("tasks"), list):
        raise LedgerError(
            f"{LEGACY_LEDGER_FILENAME} tem schema_version={versao!r} e não pode "
            f"ser migrado com segurança para o razão v{SCHEMA_VERSION}.\n"
            f"      Rode a F3S (speckit_task_compiler.py + task_ledger.py --init) "
            f"para regenerar o razão a partir da espinha.")

    save(project, dados, root)
    return {"status": "migrated", "tasks": len(dados["tasks"]),
            "from": str(legado), "path": str(atual)}


# ─── Inicialização ───────────────────────────────────────────────────────────

def init(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Cria o razão a partir do ``traceability.json``, tudo em ``pending``.

    Idempotente: reinvocar preserva o progresso real das tasks que já existiam.
    Zerar progresso porque a fase foi reexecutada faria a esteira regerar código
    já verificado — o oposto de retomar.
    """
    root = repo_root or REPO_ROOT
    trace_file = traceability_path(project, root)
    if not trace_file.is_file():
        raise LedgerError(
            f"traceability.json ausente em {trace_file}\n"
            f"      A F3S precisa rodar antes: o razão deriva da espinha, não a cria.")

    data = _read_json(trace_file)
    if data.get("schema_version") != "4.0.0":
        raise LedgerError(
            f"traceability.json v4 obrigatório para inicializar o razão v3: {trace_file}\n"
            "      Recompile a F3S com speckit_task_compiler.py antes da F4."
        )
    avisos: list[str] = []
    entries_brutas = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries_brutas, list):
        raise LedgerError(f"traceability.json com `entries` ilegível: {trace_file}")

    # Entry sem `task_id` é estruturalmente ilegível: some do razão, mas é
    # contada. Descartar a lista inteira por causa de uma entry quebrada é o
    # padrão de falha que esta camada existe para não repetir.
    entries = [e for e in entries_brutas if isinstance(e, dict) and e.get("task_id")]
    if len(entries) != len(entries_brutas):
        avisos.append(f"{len(entries_brutas) - len(entries)} entry(ies) sem task_id "
                      f"ignorada(s) — estruturalmente ilegíveis")

    # `status` do traceability: warning de planejamento NÃO impede o razão.
    # `INCOMPLETE` é reservado a falha técnica, e mesmo aí o que existir é
    # aproveitado — nunca trocado por vazio.
    status_trace = str(data.get("status") or "")
    if status_trace and status_trace not in ("COMPLETE", "COMPLETE_WITH_WARNINGS"):
        avisos.append(f"traceability.json com status={status_trace!r}")

    try:
        graph = dependency_graph.analyze(entries) if entries else None
    except dependency_graph.DependencyGraphError as exc:
        # Grafo inválido é defeito do plano, não do razão. A ordem topológica
        # cai para 0 e o problema vira aviso — o razão continua existindo, que é
        # o que a F4 precisa para retomar.
        avisos.append(f"grafo de dependências inválido ({len(exc.issues)} achado(s)); "
                      f"topological_rank degradado para 0")
        graph = None

    def _rank(task_id: str) -> int:
        return int(graph.ranks[task_id]) if graph and task_id in graph.ranks else 0

    anterior: dict[str, dict[str, Any]] = {}
    path = ledger_path(project, root)
    if path.is_file():
        try:
            anterior = {t["task_id"]: t for t in _read_json(path).get("tasks", [])}
        except LedgerError:
            anterior = {}

    tasks: list[dict[str, Any]] = []
    for e in entries:
        tid = e.get("task_id")
        if not tid:
            continue
        prev = anterior.get(tid)
        tasks.append({
            "task_id": tid,
            # `feature`, `title` e os alvos vêm da espinha e são o que permite
            # despachar UMA task com o contexto DELA. Sem eles, todo despacho do
            # fan-out recebia o mesmo prompt e as specs de todas as features.
            "feature": e.get("feature", "") or e.get("source_feature", ""),
            "title": e.get("title", ""),
            "spec_id": e.get("spec_id", ""),
            "plan_id": e.get("plan_id", ""),
            "group": e.get("group", ""),
            "migration_wave_id": e.get("migration_wave_id", ""),
            "migration_wave_order": e.get("migration_wave_order", 0),
            "task_type": e.get("task_type", ""),
            "target_stack": e.get("target_stack", ""),
            "priority": e.get("priority", "P2"),
            "depends_on": list(e.get("depends_on") or []),
            "backend_dependencies": list(e.get("backend_dependencies") or []),
            "topological_rank": _rank(tid),
            "execution_wave": _rank(tid),
            "verify_command": e.get("verify_command"),
            "status": prev.get("status", "pending") if prev else "pending",
            "executionStatus": (execution_status_of(prev) if prev else EXEC_PENDING),
            "reviewRequired": bool(prev.get("reviewRequired")) if prev else False,
            "reviewReason": (prev.get("reviewReason") or "") if prev else "",
            "blockedByTaskIds": list(prev.get("blockedByTaskIds") or []) if prev else [],
            "acceptance": list(e.get("acceptance") or []),
            "target_files": list(e.get("target_files") or (
                [e["target_file"]] if e.get("target_file") else [])),
            "source_refs": list(e.get("source_refs") or []),
            "rule_ids": list(e.get("rule_ids") or []),
            "api_ops": list(e.get("api_ops") or []),
            "test_ids": list(e.get("test_ids") or []),
            "screen_id": e.get("screen_id"),
            "attempts": int(prev.get("attempts", 0)) if prev else 0,
            "run_id": prev.get("run_id") if prev else None,
            "started_at": prev.get("started_at") if prev else None,
            "updated_at": prev.get("updated_at") if prev else None,
            "files_written": list(prev.get("files_written") or []) if prev else [],
            "evidence": prev.get("evidence") if prev else None,
            "attempt_history": list(prev.get("attempt_history") or []) if prev else [],
            "recovery_reason": prev.get("recovery_reason") if prev else None,
            "routing": prev.get("routing") if prev else None,
            "blocked_reason": prev.get("blocked_reason") if prev else None,
        })

    ledger = {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "trace_id": str(data.get("trace_id", "")) if isinstance(data, dict) else "",
        "traceability_checksum": _checksum(trace_file),
        "initialized_at": _now(),
        "updated_at": None,
        # Lista legitimamente vazia NAO e placeholder de recuperacao. A
        # distincao existe porque o reconciler decidia por este campo, e um
        # razao valido com zero tasks era tratado como artefato perdido.
        "recovery_placeholder": False,
        "status": "COMPLETE_WITH_WARNINGS" if avisos else "COMPLETE",
        "reason": ("nenhuma task consolidada em traceability.json"
                   if not tasks else ""),
        "warnings": avisos,
        "tasks": tasks,
    }
    save(project, ledger, root)
    return ledger


# ─── Consulta ────────────────────────────────────────────────────────────────

def get(project: str, task_id: str, repo_root: Path | None = None) -> dict[str, Any]:
    for t in load(project, repo_root).get("tasks", []):
        if t["task_id"] == task_id:
            return t
    raise LedgerError(f"task desconhecida no razão: {task_id}")


#: Peso de prioridade. P1 antes de P2 antes de P3, sempre.
_PRIORIDADE = {"P1": 0, "P2": 1, "P3": 2}


def order_key(task: dict[str, Any]) -> tuple[Any, ...]:
    """Ordem determinística de execução da F4.

    Rank topológico primeiro (dependência manda), depois a onda de migração,
    depois prioridade, grupo e id. Duas execuções do mesmo razão escolhem a
    mesma próxima task — é o que faz a retomada ser previsível.
    """
    return (
        int(task.get("topological_rank", 0) or 0),
        int(task.get("migration_wave_order", 0) or 0),
        _PRIORIDADE.get(str(task.get("priority") or "P2"), 1),
        str(task.get("group") or ""),
        str(task.get("task_id") or ""),
    )


def ready_tasks(project: str, group: str | None = None, target_stack: str | None = None,
                repo_root: Path | None = None) -> list[dict[str, Any]]:
    """Tasks prontas para execução, em ordem de dependência.

    ``in_progress`` volta para a fila de propósito: um run morto no meio deixa a
    task nesse estado, e ela não pode desaparecer da esteira por isso.

    ``backend_dependencies`` conta junto com ``depends_on``: uma tela que
    consome um endpoint não fica pronta antes do endpoint existir.
    """
    tasks = load(project, repo_root).get("tasks", [])
    concluidas = {t["task_id"] for t in tasks if t["status"] == "verified"}
    conhecidas = {t["task_id"] for t in tasks}

    def _dependencias(t: dict[str, Any]) -> list[str]:
        # Dependência que não existe no razão não pode travar a task para
        # sempre: ela vira achado do `diagnose`, não bloqueio silencioso.
        return [d for d in (list(t.get("depends_on") or [])
                            + list(t.get("backend_dependencies") or []))
                if d in conhecidas]

    prontas = [
        t for t in tasks
        if t["status"] in {"pending", "in_progress", "failed"}
        and all(d in concluidas for d in _dependencias(t))
        and (group is None or t.get("group") == group)
        and (target_stack is None or t.get("target_stack") == target_stack)
    ]
    prontas.sort(key=order_key)
    return prontas


def next_tasks(project: str, group: str | None = None, target_stack: str | None = None,
               repo_root: Path | None = None) -> list[dict[str, Any]]:
    """Compatibility alias for callers created before the dependency scheduler."""
    return ready_tasks(project, group, target_stack, repo_root)


def execution_order(project: str, repo_root: Path | None = None) -> list[dict[str, Any]]:
    """All ledger tasks in their stable topological order."""
    return sorted(load(project, repo_root).get("tasks", []), key=order_key)


def diagnose(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Classify why the ledger can or cannot make progress."""
    tasks = load(project, repo_root).get("tasks", [])
    try:
        graph = dependency_graph.analyze(tasks)
    except dependency_graph.DependencyGraphError as exc:
        codes = {issue.code for issue in exc.issues}
        status = "cycle" if codes == {"cycle"} else "dangling_dependency"
        return {
            "status": status,
            "ready": [],
            "issues": [issue.as_dict() for issue in exc.issues],
            "blocked": [],
        }

    by_id = {task["task_id"]: task for task in tasks}
    ready = ready_tasks(project, repo_root=repo_root)
    if ready:
        return {
            "status": "ready",
            "ready": [task["task_id"] for task in ready],
            "issues": [],
            "blocked": [],
        }

    if tasks and all(task.get("status") == "verified" for task in tasks):
        return {"status": "complete", "ready": [], "issues": [], "blocked": []}

    blocked: list[dict[str, Any]] = []
    terminal_blockers = {"blocked", "skipped"}
    for task_id in graph.order:
        task = by_id[task_id]
        if task.get("status") == "verified":
            continue
        blockers = [
            dependency_id
            for dependency_id in graph.predecessors[task_id]
            if by_id[dependency_id].get("status") in terminal_blockers
        ]
        if blockers:
            blocked.append({
                "task_id": task_id,
                "blocked_by": blockers,
                "blocker_status": {
                    dependency_id: by_id[dependency_id].get("status")
                    for dependency_id in blockers
                },
            })

    status = "blocked_by_terminal" if blocked else "waiting"
    return {
        "status": status,
        "ready": [],
        "issues": [],
        "blocked": blocked,
    }


def recover_stale(project: str, active_run_id: str | None = None,
                  repo_root: Path | None = None) -> list[dict[str, Any]]:
    """Devolve à fila as tasks presas em `in_progress` de um run que morreu.

    O critério **não** é tempo. Uma task só é recuperada quando o `run_id` dela
    não é o do run atual — ou seja, quando quem a marcou não é quem está
    executando agora. Tempo decorrido sozinho recuperaria uma task que está
    rodando neste instante em outro terminal.

    O que é preservado: `attempts`, `evidence`, `files_written`. O que muda:
    `status` volta para `failed` (havia evidência de falha) ou `pending` (não
    houve nem despacho conferível), e `recovery_reason` registra o porquê.
    Task que já estourou o teto de tentativas vai para `blocked`, não para a
    fila — recuperar em loop esconderia o defeito real.
    """
    root = repo_root or REPO_ROOT
    ledger = load(project, root)
    recuperadas: list[dict[str, Any]] = []
    mudou = False

    for task in ledger.get("tasks", []):
        if task.get("status") != "in_progress":
            continue
        if active_run_id and task.get("run_id") == active_run_id:
            continue  # é o run atual: a task está viva, não abandonada.

        evidencia = task.get("evidence") or {}
        tinha_falha = bool(evidencia) and int(evidencia.get("exit_code", 1) or 1) != 0
        anterior = task.get("run_id")
        if int(task.get("attempts", 0) or 0) >= MAX_ATTEMPTS:
            task["status"] = "blocked"
            task["blocked_reason"] = (
                f"run {anterior!r} interrompido com {task.get('attempts')} "
                f"tentativas já registradas; exposta em vez de retentada.")
            motivo = "abandonada com teto de tentativas atingido"
        else:
            task["status"] = "failed" if tinha_falha else "pending"
            motivo = ("run anterior interrompido após uma verificação reprovada"
                      if tinha_falha else
                      "run anterior interrompido antes de qualquer verificação")
        task["recovery_reason"] = (
            f"{motivo} (run_id anterior={anterior!r}, "
            f"run atual={active_run_id!r}) — recuperada em {_now()}")
        task["run_id"] = None
        task["executionStatus"] = EXEC_PENDING
        task["updated_at"] = _now()
        recuperadas.append({
            "task_id": task["task_id"],
            "status": task["status"],
            "previous_run_id": anterior,
            "attempts": task.get("attempts", 0),
            "recovery_reason": task["recovery_reason"],
        })
        mudou = True

    if mudou:
        save(project, ledger, root)
    return recuperadas


#: Classificação final da fase. `skipped` só existe como decisão explícita de
#: operador — nunca como resultado de build reprovado (isso é `failed`/`blocked`).
COMPLETION_SUCCESS = "SUCCESS"
COMPLETION_PARTIAL = "PARTIAL"
COMPLETION_BLOCKED = "BLOCKED"
COMPLETION_FAILED = "FAILED"


#: Encerramento controlado: a fase foi processada inteira, mas parte do
#: resultado precisa de gente. Não é sucesso funcional e não é bloqueio.
COMPLETION_WITH_REVIEW = "COMPLETED_WITH_REVIEW"


def execution_counts(project: str, repo_root: Path | None = None) -> dict[str, int]:
    """Contagem por `executionStatus` — o vocabulário do relatório da F4."""
    tasks = load(project, repo_root).get("tasks", [])
    contagem = {chave: 0 for chave in sorted(EXECUTION_STATUSES)}
    contagem["total"] = len(tasks)
    for task in tasks:
        contagem[execution_status_of(task)] += 1
    return contagem


def completion_status(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Veredito da F4. Separa **completude de execução** de **sucesso funcional**.

    A regra antiga tratava qualquer task não `verified` como fracasso da fase —
    e uma única task falhando devolvia `F4 BLOCKED` com 162 tasks intactas. A
    pergunta certa do completeness gate não é "deu tudo certo?", é "tudo foi
    processado e está registrado?".
    """
    tasks = load(project, repo_root).get("tasks", [])
    contagem = summary(project, repo_root)
    execucao = execution_counts(project, repo_root)
    if not tasks:
        return {"status": COMPLETION_FAILED, "counts": contagem,
                "execution_counts": execucao,
                "execution_complete": False, "functional_success": False,
                "reason": "razão sem nenhuma task — nada foi planejado para a F4"}

    nao_terminais = [t["task_id"] for t in tasks
                     if execution_status_of(t) not in EXECUTION_TERMINAL]
    revisao = [t["task_id"] for t in tasks
               if execution_status_of(t) in {EXEC_REVIEW,
                                             EXEC_FAILED_AFTER_REMEDIATION}]
    dependencias = [t["task_id"] for t in tasks
                    if execution_status_of(t) == EXEC_BLOCKED_BY_DEPENDENCY]
    avisos = [t["task_id"] for t in tasks
              if execution_status_of(t) == EXEC_COMPLETED_WARN]

    base = {
        "counts": contagem,
        "execution_counts": execucao,
        "execution_complete": not nao_terminais,
        "functional_success": not (nao_terminais or revisao or dependencias),
        "review_required": revisao,
        "dependency_blocks": dependencias,
        "infrastructure_warnings": avisos,
        "pending": nao_terminais,
    }

    if nao_terminais:
        return {**base, "status": COMPLETION_FAILED,
                "reason": f"{len(nao_terminais)} task(s) sem estado terminal: "
                          + ", ".join(nao_terminais[:10])}
    if revisao or dependencias:
        return {**base, "status": COMPLETION_WITH_REVIEW,
                "reason": (f"todas as {len(tasks)} tasks foram processadas; "
                           f"{len(revisao)} exigem revisão e "
                           f"{len(dependencias)} ficaram bloqueadas por "
                           f"dependência")}
    if avisos:
        return {**base, "status": COMPLETION_PARTIAL,
                "reason": f"{len(avisos)} task(s) concluída(s) com avisos "
                          f"(validação externa não bloqueante)"}
    return {**base, "status": COMPLETION_SUCCESS,
            "reason": f"todas as {len(tasks)} tasks verificadas com exit code 0"}


def groups(project: str, repo_root: Path | None = None) -> list[dict[str, Any]]:
    """Grupos de tasks — a unidade de fan-out da F4, com a stack que os roteia."""
    tasks = load(project, repo_root).get("tasks", [])
    agrupado: dict[str, dict[str, Any]] = {}
    for t in tasks:
        g = agrupado.setdefault(t.get("group", ""), {
            "group": t.get("group", ""), "target_stack": t.get("target_stack", ""),
            "total": 0, "pending": 0, "verified": 0, "failed": 0, "blocked": 0,
        })
        g["total"] += 1
        if t["status"] in {"pending", "in_progress"}:
            g["pending"] += 1
        elif t["status"] in g:
            g[t["status"]] += 1
    return sorted(agrupado.values(), key=lambda g: g["group"])


def summary(project: str, repo_root: Path | None = None) -> dict[str, int]:
    tasks = load(project, repo_root).get("tasks", [])
    contagem = {"total": len(tasks), "pending": 0, "in_progress": 0,
                "verified": 0, "failed": 0, "blocked": 0, "skipped": 0}
    for t in tasks:
        if t["status"] in contagem:
            contagem[t["status"]] += 1
    return contagem


# ─── Transições ──────────────────────────────────────────────────────────────

def _mutate(project: str, task_id: str, repo_root: Path | None,
            fn) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    ledger = load(project, root)
    for t in ledger.get("tasks", []):
        if t["task_id"] == task_id:
            fn(t)
            t["updated_at"] = _now()
            save(project, ledger, root)
            return t
    raise LedgerError(
        f"task desconhecida no razão: {task_id}\n"
        f"      O razão deriva de traceability.json; task fora da espinha não existe.")


def start(project: str, task_id: str, run_id: str,
          repo_root: Path | None = None) -> dict[str, Any]:
    ready_ids = {task["task_id"] for task in ready_tasks(project, repo_root=repo_root)}
    if task_id not in ready_ids:
        state = get(project, task_id, repo_root)
        raise LedgerError(
            f"task {task_id} não está pronta (status={state.get('status')}, "
            f"depends_on={state.get('depends_on') or []})"
        )

    def _apply(t: dict[str, Any]) -> None:
        t["status"] = "in_progress"
        t["executionStatus"] = EXEC_RUNNING
        t["run_id"] = run_id
        t["started_at"] = _now()
        t["finishedAt"] = None
    return _mutate(project, task_id, repo_root, _apply)


def record_result(project: str, task_id: str, *, command: str, exit_code: int,
                  log_path: str | None = None, checks: dict[str, str] | None = None,
                  files_written: list[str] | None = None,
                  recorded_by: str = "task_ledger",
                  routing: dict[str, Any] | None = None,
                  commit_hash: str | None = None,
                  summary_text: str = "",
                  agent_result: dict[str, Any] | None = None,
                  execution_status: str | None = None,
                  review_reason: str = "",
                  fields: dict[str, Any] | None = None,
                  repo_root: Path | None = None) -> dict[str, Any]:
    """Grava o resultado real de uma task. **Única porta para `verified`.**

    ``command`` e ``exit_code`` são obrigatórios e nomeados: não existe caminho de
    código que marque uma task como concluída sem prova. ``recorded_by`` vindo de
    um agente é recusado — ver a docstring do módulo.
    """
    if _AGENT_NAME.match(recorded_by) or recorded_by not in _TOOL_WRITERS:
        raise LedgerError(
            f"gravação recusada: `recorded_by={recorded_by!r}` parece um agente.\n"
            f"      O razão é escrito por ferramenta, a partir de exit code real.\n"
            f"      Auto-relato de conclusão é a RC-02 desta esteira "
            f"(`Build Status: PASS (Simulated)` com o build real falhando).")

    def _apply(t: dict[str, Any]) -> None:
        t["attempts"] = int(t.get("attempts", 0)) + 1
        t["evidence"] = {
            "command": command,
            "exit_code": int(exit_code),
            "log_path": log_path,
            "checks": dict(checks or {}),
            "recorded_at": _now(),
            "recorded_by": recorded_by,
            "commit_hash": commit_hash,
            # O que o AGENTE declarou fica aqui, ao lado — e não no lugar — da
            # prova real. É diagnóstico, nunca autoridade de status.
            "agent_result": dict(agent_result or {}) or None,
        }
        if routing:
            t["routing"] = dict(routing)
        if files_written:
            t["files_written"] = list(files_written)
        # Histórico: uma linha por tentativa, nunca sobrescrita. É o que permite
        # responder "quantas tentativas e por que cada uma falhou" depois.
        historico = list(t.get("attempt_history") or [])
        historico.append({
            "attempt": t["attempts"],
            "command": command,
            "exit_code": int(exit_code),
            "log_path": log_path,
            "commit_hash": commit_hash,
            "agent": (routing or {}).get("agent"),
            "summary": summary_text,
            "recorded_at": _now(),
            "recorded_by": recorded_by,
        })
        t["attempt_history"] = historico

        # Campos de observabilidade da F4 (branch, baseline, validação,
        # artefatos, exclusões). Aditivos: consumidor antigo ignora o que não
        # conhece, e nenhum campo existente é removido.
        for chave, valor in (fields or {}).items():
            t[chave] = valor

        # 1. Status legado derivado do exit code real — o invariante de sempre.
        if int(exit_code) == 0:
            t["status"] = "verified"
            t["blocked_reason"] = None
        elif t["attempts"] >= MAX_ATTEMPTS:
            t["status"] = "blocked"
            t["blocked_reason"] = (
                f"{t['attempts']} tentativas, última com exit {exit_code}. "
                f"Exposta em vez de retentada: reparo em loop esconde o defeito real.")
        else:
            t["status"] = "failed"

        # 2. `executionStatus`: rótulo explícito quando a F4 sabe mais que o
        #    exit code (validação externa que reclamou, limitação de ambiente);
        #    derivado do legado quando não sabe.
        if execution_status:
            t["executionStatus"] = execution_status
            t["status"] = legacy_status_for(execution_status)
            if execution_status in {EXEC_REVIEW, EXEC_FAILED_AFTER_REMEDIATION,
                                    EXEC_BLOCKED_BY_DEPENDENCY}:
                t["reviewRequired"] = True
                t["reviewReason"] = review_reason or summary_text
                t["blocked_reason"] = review_reason or summary_text
            else:
                t["reviewRequired"] = bool(review_reason)
                t["reviewReason"] = review_reason
                if t["status"] == "verified":
                    t["blocked_reason"] = None
        else:
            t["executionStatus"] = {
                "verified": EXEC_COMPLETED,
                "failed": EXEC_RUNNING,
                "blocked": EXEC_FAILED_AFTER_REMEDIATION,
            }.get(t["status"], EXEC_RUNNING)
            if t["status"] == "blocked":
                t["reviewRequired"] = True
                t["reviewReason"] = t.get("blocked_reason") or summary_text

    return _mutate(project, task_id, repo_root, _apply)


def progress_path(project: str, repo_root: Path | None = None) -> Path:
    return _speckit_dir(project, repo_root or REPO_ROOT) / "ava-agents-progress.txt"


def iteration_preamble(project: str, group: str | None = None,
                       task_id: str | None = None, repo_root: Path | None = None,
                       progress_lines: int = 40) -> list[str]:
    """Bloco de estado prefixado a cada chamada do fan-out.

    O padrão de harness para agentes de execução longa pede que cada sessão comece
    lendo as notas de progresso e escolhendo a próxima feature. Aqui a rotina é
    **imposta pelo harness**, não confiada à memória do agente — e a escolha da
    task não é dele: vem da expansão determinística do razão.

    Contém, nesta ordem: o que já está verificado no grupo, a task que ele possui,
    o que ela depende, e as últimas entradas do log narrativo.
    """
    root = repo_root or REPO_ROOT
    blocos: list[str] = []

    try:
        ledger = load(project, root)
    except LedgerError:
        return blocos

    tasks = [t for t in ledger.get("tasks", [])
             if group is None or t.get("group") == group]
    if not tasks:
        return blocos

    feitas = [t for t in tasks if t["status"] == "verified"]
    prontas = ready_tasks(project, group=group, repo_root=root)
    bloqueadas = [t for t in tasks if t["status"] == "blocked"]

    linhas = [f"### Razão de progresso — grupo {group or 'todos'}", ""]
    linhas.append(f"- Verificadas: {len(feitas)} de {len(tasks)}")
    if feitas:
        linhas.append("  - " + ", ".join(t["task_id"] for t in feitas[:20]))
    if bloqueadas:
        linhas.append(f"- Bloqueadas (não retentar): "
                      + ", ".join(t["task_id"] for t in bloqueadas[:10]))
    alvo = None
    if task_id:
        alvo = next((task for task in tasks if task["task_id"] == task_id), None)
    elif prontas:
        alvo = prontas[0]
    if alvo:
        linhas += [
            "",
            f"**Sua task nesta execução: {alvo['task_id']}**",
            f"- Critério de aceite: {'; '.join(alvo.get('acceptance') or ['—'])}",
            f"- Depende de: {', '.join(alvo.get('depends_on') or ['—'])}",
            f"- Tentativas anteriores: {alvo.get('attempts', 0)}",
            f"- Onda topológica: {alvo.get('execution_wave', 0)}",
            f"- Verificação: `{alvo.get('verify_command') or 'AUSENTE'}`",
        ]
        if alvo.get("evidence"):
            ev = alvo["evidence"]
            linhas.append(f"- Última verificação: `{ev.get('command')}` "
                          f"→ exit {ev.get('exit_code')}")
    linhas += [
        "",
        "> Você não escolhe a task e não declara conclusão. O status é gravado por",
        "> ferramenta, a partir do exit code real da verificação.",
    ]
    blocos.append("\n".join(linhas))

    prog = progress_path(project, root)
    if prog.is_file():
        texto = prog.read_text(encoding="utf-8", errors="replace").splitlines()
        recentes = texto[-progress_lines:]
        if recentes:
            blocos.append("### Notas de progresso (ava-agents-progress.txt, mais recentes)\n\n"
                          + "\n".join(recentes))
    return blocos


def append_progress(project: str, entry: str, repo_root: Path | None = None) -> None:
    """Acrescenta uma nota narrativa. Nunca carrega afirmação de status."""
    path = progress_path(project, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{_now()}] {entry.strip()}\n")


def mark_execution(project: str, task_id: str, execution_status: str, *,
                   review_reason: str = "", blocked_by: list[str] | None = None,
                   fields: dict[str, Any] | None = None,
                   repo_root: Path | None = None) -> dict[str, Any]:
    """Grava um `executionStatus` terminal sem passar por `record_result`.

    Usado nos dois casos em que não existe exit code de build para registrar:
    dependência bloqueada e limitação externa comprovada (toolchain ausente,
    scaffold não localizado). O `status` legado sai da tradução, nunca de
    palpite — e `review` **exige** motivo: uma task em revisão sem justificativa
    é indistinguível de uma task esquecida.
    """
    legado = legacy_status_for(execution_status)
    if execution_status in {EXEC_REVIEW, EXEC_FAILED_AFTER_REMEDIATION,
                            EXEC_BLOCKED_BY_DEPENDENCY} and not review_reason:
        raise LedgerError(
            f"`{execution_status}` exige `review_reason` — task {task_id}")

    def _apply(t: dict[str, Any]) -> None:
        t["executionStatus"] = execution_status
        t["status"] = legado
        if execution_status in {EXEC_REVIEW, EXEC_FAILED_AFTER_REMEDIATION,
                                EXEC_BLOCKED_BY_DEPENDENCY}:
            t["reviewRequired"] = True
            t["reviewReason"] = review_reason
            t["blocked_reason"] = review_reason
        if blocked_by is not None:
            t["blockedByTaskIds"] = list(blocked_by)
            t["dependencyReason"] = review_reason
            t["dependencyType"] = "explicit"
            t["evaluatedAt"] = _now()
        for chave, valor in (fields or {}).items():
            t[chave] = valor

    return _mutate(project, task_id, repo_root, _apply)


def classify_pending_dependencies(project: str,
                                  repo_root: Path | None = None) -> list[dict[str, Any]]:
    """Fecha o razão: task que nunca pôde rodar vira `blocked_by_dependency`.

    Só é `blocked_by_dependency` quem tem dependência **explícita** que terminou
    mal. Falha de uma task nunca é bloqueio implícito das demais — e uma task
    sem dependência falha alguma que continuou `pending` é achado de defeito do
    laço, reportado como tal, não escondido.
    """
    root = repo_root or REPO_ROOT
    ledger = load(project, root)
    por_id = {t["task_id"]: t for t in ledger.get("tasks", [])}
    ruins = {tid for tid, t in por_id.items()
             if execution_status_of(t) in {EXEC_REVIEW,
                                           EXEC_FAILED_AFTER_REMEDIATION,
                                           EXEC_BLOCKED_BY_DEPENDENCY}}
    fechadas: list[dict[str, Any]] = []
    mudou = False

    for task in ledger.get("tasks", []):
        if execution_status_of(task) in EXECUTION_TERMINAL:
            continue
        deps = [d for d in (list(task.get("depends_on") or [])
                            + list(task.get("backend_dependencies") or []))
                if d in por_id]
        impedidas = [d for d in deps if d in ruins]
        if not impedidas:
            continue
        motivo = ("dependencia(s) em estado terminal nao concluido: "
                  + ", ".join(impedidas))
        task["executionStatus"] = EXEC_BLOCKED_BY_DEPENDENCY
        task["status"] = _LEGACY_STATUS[EXEC_BLOCKED_BY_DEPENDENCY]
        task["reviewRequired"] = True
        task["reviewReason"] = motivo
        task["blocked_reason"] = motivo
        task["blockedByTaskIds"] = impedidas
        task["dependencyReason"] = motivo
        task["dependencyType"] = "explicit"
        task["evaluatedAt"] = _now()
        task["updated_at"] = _now()
        fechadas.append({"task_id": task["task_id"], "blockedByTaskIds": impedidas})
        mudou = True

    if mudou:
        save(project, ledger, root)
    return fechadas


def reset(project: str, task_id: str, reason: str,
          repo_root: Path | None = None) -> dict[str, Any]:
    """Devolve uma task `blocked`/`failed` à fila, por decisão explícita.

    Existe porque nem toda tarefa bloqueada é defeito de código: em
    `cadastro-funcionario-03`, `T-W0-FE-001` foi bloqueada por `exit 127` — o
    `ng` não estava no PATH. Depois de instalar a toolchain, exigir uma
    recompilação da F3S para reexecutar uma task seria desproporcional.

    O que muda: `status` volta a `pending` e `attempts` zera (senão a task
    re-bloqueia na primeira tentativa). O que **não** muda: `attempt_history` e
    `evidence` continuam lá — o histórico de por que ela falhou é preservado, e
    o motivo do reset fica registrado em `recovery_reason`.
    """
    def _apply(t: dict[str, Any]) -> None:
        anterior = t.get("status")
        t["status"] = "pending"
        t["executionStatus"] = EXEC_PENDING
        t["reviewRequired"] = False
        t["attempts"] = 0
        t["run_id"] = None
        t["blocked_reason"] = None
        t["recovery_reason"] = (
            f"reset explicito de `{anterior}` para `pending` em {_now()}: {reason}")
    return _mutate(project, task_id, repo_root, _apply)


def skip(project: str, task_id: str, reason: str,
         repo_root: Path | None = None) -> dict[str, Any]:
    def _apply(t: dict[str, Any]) -> None:
        t["status"] = "skipped"
        # `skipped` é decisão explícita de operador, e decisão explícita precisa
        # de dono: no vocabulário novo isso é `review`, com o motivo registrado.
        t["executionStatus"] = EXEC_REVIEW
        t["reviewRequired"] = True
        t["reviewReason"] = reason
        t["blocked_reason"] = reason
    return _mutate(project, task_id, repo_root, _apply)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python src/shared/tools/task_ledger.py",
        description="Razão de progresso da F4 — status só sobe com exit code real.")
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--init", action="store_true",
                        help="cria o razão a partir do traceability.json")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--next", action="store_true", help="tasks prontas para execução")
    parser.add_argument("--order", action="store_true", help="ordem topológica completa")
    parser.add_argument("--diagnose", action="store_true", help="diagnóstico de progresso")
    parser.add_argument("--validate", action="store_true",
                        help="confere schema e checksum antes da F4 (fail-closed)")
    parser.add_argument("--migrate-legacy", action="store_true",
                        help=f"converte {LEGACY_LEDGER_FILENAME} em tasks-progress.json")
    parser.add_argument("--recover", action="store_true",
                        help="devolve à fila tasks in_progress de runs mortos")
    parser.add_argument("--completion", action="store_true",
                        help="veredito da fase: SUCCESS|PARTIAL|BLOCKED|FAILED")
    parser.add_argument("--run-id", default=None,
                        help="run atual, usado por --recover para não mexer no run vivo")
    parser.add_argument("--reset", metavar="TASK_ID", default=None,
                        help="devolve uma task blocked/failed à fila (decisão do operador)")
    parser.add_argument("--reason", default="",
                        help="motivo do --reset, gravado em recovery_reason")
    parser.add_argument("--groups", action="store_true", help="grupos de fan-out")
    parser.add_argument("--group", help="filtra por grupo")
    parser.add_argument("--stack", help="filtra por stack alvo")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn", action="store_true",
                        help="converte erros de validação em avisos e retorna exit 0")
    args = parser.parse_args(argv)

    try:
        if args.init:
            ledger = init(args.project)
            if args.json:
                print(json.dumps({
                    "status": "initialized",
                    "tasks": len(ledger["tasks"]),
                    "path": str(ledger_path(args.project)),
                }, ensure_ascii=False, indent=2))
            else:
                print(f"  ✅ razão criado com {len(ledger['tasks'])} task(s), todas em `pending`")
                print(f"     {ledger_path(args.project)}")
            return 0

        if args.migrate_legacy:
            resultado = migrate_legacy(args.project)
            print(json.dumps(resultado, ensure_ascii=False, indent=2) if args.json
                  else f"  {resultado['status']}: {resultado.get('path')}")
            return 0

        if args.validate:
            dados = validate(args.project)
            print(json.dumps(dados, ensure_ascii=False, indent=2) if args.json
                  else f"  razão válido: {dados['tasks']} task(s), "
                       f"checksum {'ok' if dados['checksum_ok'] else 'DIVERGENTE'}")
            return 0

        if args.recover:
            recuperadas = recover_stale(args.project, args.run_id)
            if args.json:
                print(json.dumps(recuperadas, ensure_ascii=False, indent=2))
            else:
                for item in recuperadas:
                    print(f"  {item['task_id']} → {item['status']} "
                          f"({item['recovery_reason']})")
                if not recuperadas:
                    print("  nenhuma task presa em in_progress")
            return 0

        if args.reset:
            if not args.reason:
                print("ERRO: --reset exige --reason (o motivo vai para o razão)",
                      file=sys.stderr)
                return 2
            task = reset(args.project, args.reset, args.reason)
            print(json.dumps(task, ensure_ascii=False, indent=2) if args.json
                  else f"  {task['task_id']} -> {task['status']} "
                       f"({task['recovery_reason']})")
            return 0

        if args.completion:
            dados = completion_status(args.project)
            print(json.dumps(dados, ensure_ascii=False, indent=2) if args.json
                  else f"  {dados['status']}: {dados['reason']}")
            return 0 if dados["status"] == COMPLETION_SUCCESS else 1

        if args.groups:
            dados = groups(args.project)
            print(json.dumps(dados, ensure_ascii=False, indent=2) if args.json else "")
            if not args.json:
                for g in dados:
                    print(f"  {g['group']:<20} {g['target_stack']:<10} "
                          f"total={g['total']:<4} pendentes={g['pending']:<4} "
                          f"verificadas={g['verified']:<4} bloqueadas={g['blocked']}")
            return 0

        if args.next:
            dados = next_tasks(args.project, args.group, args.stack)
            if args.json:
                print(json.dumps(dados, ensure_ascii=False, indent=2))
            else:
                for t in dados:
                    print(f"  {t['task_id']:<16} {t['group']:<18} {t['target_stack']:<10} "
                          f"{t['status']:<12} tentativas={t['attempts']}")
            return 0 if dados else 1

        if args.order:
            dados = execution_order(args.project)
            if args.json:
                print(json.dumps(dados, ensure_ascii=False, indent=2))
            else:
                for task in dados:
                    print(f"  wave={task.get('execution_wave', 0):<3} "
                          f"{task['task_id']:<16} {task['status']}")
            return 0

        if args.diagnose:
            dados = diagnose(args.project)
            print(json.dumps(dados, ensure_ascii=False, indent=2) if args.json
                  else f"  {dados['status']}: "
                       f"{', '.join(dados['ready']) or 'nenhuma task pronta'}")
            return 0 if dados["status"] in {"ready", "complete"} else 1

        s = summary(args.project)
        if args.json:
            print(json.dumps(s, ensure_ascii=False, indent=2))
        else:
            print(f"\n  Razão de progresso — {args.project}")
            for k in ("total", "pending", "in_progress", "verified",
                      "failed", "blocked", "skipped"):
                print(f"    {k:<12} {s[k]}")
            if not checksum_matches(args.project):
                print("\n    ⚠️  traceability.json mudou depois do --init — "
                      "a espinha deveria ser imutável. Reveja a F3S.")
        return 0

    except LedgerError as exc:
        if args.warn:
            warning = {
                "status": "warning",
                "message": str(exc),
                "command": "task_ledger",
                "project": args.project,
            }
            print(json.dumps(warning, ensure_ascii=False, indent=2) if args.json
                  else f"AVISO: {exc}\n  (continuando porque --warn foi solicitado)")
            return 0
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        if args.warn:
            warning = {
                "status": "warning",
                "message": f"{type(exc).__name__}: {exc}",
                "command": "task_ledger",
                "project": args.project,
            }
            print(json.dumps(warning, ensure_ascii=False, indent=2) if args.json
                  else f"AVISO: {type(exc).__name__}: {exc}\n  (continuando porque --warn foi solicitado)")
            return 0
        raise


if __name__ == "__main__":
    raise SystemExit(_main())
