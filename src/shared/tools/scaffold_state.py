#!/usr/bin/env python3
"""`tasks-progress.json` — estado da fase de scaffold, com escrita atômica.

Por que um arquivo novo em vez de reaproveitar `f4s-state.json`: aquele vive
DENTRO do repo de código gerado (`source-code/<componente>/f4s-state.json`) e
descreve o progresso de features de um repo só. O gate de aprovação e a ordem
frontend→backend são fatos do PROJETO, acima de qualquer repo de stack, e
precisam sobreviver a um `git init` que ainda não aconteceu. `f4s-state.json` e
`GENERATION_LOG.md` continuam existindo e sendo escritos como antes.

Escrita atômica: `write_text` num arquivo de estado é o modo clássico de perder
tudo — um Ctrl-C no meio deixa JSON truncado, e a retomada não consegue nem ler
o que já tinha sido feito. Aqui grava-se em temporário no mesmo diretório e
troca-se com `os.replace`, que é atômico no NTFS e no ext4.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from scaffold_paths import COMPONENT_TYPES, resolve_source_code_path

SCHEMA_VERSION = "1.0.0"
STATE_FILENAME = "tasks-progress.json"

# ── Estados ────────────────────────────────────────────────────────────────
PENDING = "pending"
RUNNING = "running"
GENERATED = "generated"
VERIFYING = "verifying"
COMPLETED = "completed"
FAILED = "failed"
BLOCKED = "blocked"
AWAITING_USER_APPROVAL = "awaiting_user_approval"
APPROVED = "approved"
REJECTED = "rejected"
CANCELLED = "cancelled"

VALID_STATUSES: frozenset[str] = frozenset({
    PENDING, RUNNING, GENERATED, VERIFYING, COMPLETED, FAILED, BLOCKED,
    AWAITING_USER_APPROVAL, APPROVED, REJECTED, CANCELLED,
})

#: Transições permitidas. Um estado terminal só sai dele por reexecução
#: explícita (retry → running), nunca por deriva.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    PENDING: frozenset({RUNNING, BLOCKED, CANCELLED, PENDING}),
    RUNNING: frozenset({GENERATED, FAILED, CANCELLED, RUNNING}),
    GENERATED: frozenset({VERIFYING, FAILED, CANCELLED}),
    VERIFYING: frozenset({COMPLETED, FAILED, CANCELLED}),
    COMPLETED: frozenset({RUNNING, COMPLETED}),
    FAILED: frozenset({RUNNING, BLOCKED, CANCELLED, FAILED}),
    BLOCKED: frozenset({PENDING, RUNNING, CANCELLED}),
    AWAITING_USER_APPROVAL: frozenset({
        APPROVED, REJECTED, CANCELLED, AWAITING_USER_APPROVAL}),
    # Aprovado não volta atrás sozinho: o que já foi liberado, foi.
    APPROVED: frozenset({APPROVED}),
    # Rejeitado aceita nova decisão explícita — rejeitar por engano não pode
    # inutilizar o projeto. O invariante que importa não é "rejeição é
    # definitiva", é "nada avança sem aprovação explícita e registrada": a
    # segunda decisão é tão explícita quanto a primeira, e fica com seu próprio
    # timestamp e autor.
    REJECTED: frozenset({AWAITING_USER_APPROVAL, APPROVED, REJECTED}),
    CANCELLED: frozenset({PENDING, RUNNING}),
}

#: Ids de task por responsabilidade — nunca por tecnologia. A stack fica como
#: atributo, para que trocar Angular por React não renomeie a task.
TASK_IDS: dict[str, str] = {
    "frontend": "T-SCAFFOLD-FRONTEND-001",
    "backend": "T-SCAFFOLD-BACKEND-001",
}
APPROVAL_TASK_ID = "T-APPROVAL-CODEGEN-001"

#: Artifacts do grafo, também por responsabilidade.
ARTIFACT_IDS: dict[str, str] = {
    "frontend": "artifact:scaffold:frontend",
    "backend": "artifact:scaffold:backend",
}
APPROVAL_ARTIFACT = "artifact:approval:code-generation"


class StateError(RuntimeError):
    """Transição inválida ou estado corrompido."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_path(project_dir: Path) -> Path:
    return Path(project_dir) / "outputs" / "tobe" / STATE_FILENAME


def _empty_state(project: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "created_at": _now(),
        "updated_at": _now(),
        "run_id": None,
        "tasks": {},
        "approval": None,
        "artifacts": {},
    }


def load_state(project_dir: Path, project: str = "") -> dict[str, Any]:
    """Lê o estado; devolve estado vazio se ausente ou ilegível.

    JSON corrompido não pode travar a esteira: o pior caso vira "refazer o
    scaffold", que é idempotente, e não "impossível continuar".
    """
    caminho = state_path(project_dir)
    if not caminho.is_file():
        return _empty_state(project)
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state(project)
    if not isinstance(dados, dict) or "tasks" not in dados:
        return _empty_state(project)
    dados.setdefault("artifacts", {})
    dados.setdefault("approval", None)
    dados.setdefault("project", project)
    return dados


def save_state(project_dir: Path, state: dict[str, Any]) -> Path:
    """Persiste com troca atômica — nunca deixa arquivo pela metade."""
    caminho = state_path(project_dir)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    fd, temporario = tempfile.mkstemp(
        dir=str(caminho.parent), prefix=f".{STATE_FILENAME}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_com_retry(temporario, caminho)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise
    return caminho


#: Tentativas de troca atômica antes de desistir. No Windows `os.replace` falha
#: com PermissionError transitório quando o destino está momentaneamente aberto
#: por outro processo (antivírus, indexador, um leitor concorrente do estado).
#: Não é corrupção nem disputa lógica — é o SO pedindo alguns milissegundos.
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


def assert_transition(atual: str | None, novo: str) -> None:
    if novo not in VALID_STATUSES:
        raise StateError(f"status desconhecido: {novo!r}")
    if atual is None:
        if novo not in {PENDING, RUNNING, BLOCKED, AWAITING_USER_APPROVAL, CANCELLED}:
            raise StateError(f"estado inicial inválido: {novo!r}")
        return
    permitidos = ALLOWED_TRANSITIONS.get(atual, frozenset())
    if novo not in permitidos:
        raise StateError(
            f"transição inválida: {atual} → {novo} "
            f"(permitidas: {', '.join(sorted(permitidos)) or 'nenhuma'})")


def scaffold_task(state: dict[str, Any], component_type: str) -> dict[str, Any] | None:
    return state.get("tasks", {}).get(TASK_IDS[component_type])


def update_scaffold_task(project_dir: Path, state: dict[str, Any], *,
                         component_type: str, status: str,
                         **campos: Any) -> dict[str, Any]:
    """Aplica uma transição na task de scaffold e persiste atomicamente."""
    if component_type not in TASK_IDS:
        raise StateError(f"component_type inválido: {component_type!r}")
    task_id = TASK_IDS[component_type]
    atual = state.setdefault("tasks", {}).get(task_id)
    assert_transition((atual or {}).get("status"), status)

    registro: dict[str, Any] = dict(atual or {
        "task_id": task_id,
        "type": "scaffold",
        "component_type": component_type,
        "stack": None,
        "status": None,
        "started_at": None,
        "completed_at": None,
        "generator": None,
        "verifier": None,
        "source_path": None,
        "output_path": resolve_source_code_path(component_type),
        "restore_status": None,
        "build_status": None,
        "verification_status": None,
        "attempts": 0,
        "commit_sha": None,
        "error_summary": None,
        "evidence": [],
    })
    registro.update({k: v for k, v in campos.items() if v is not None})
    registro["status"] = status
    # output_path é derivado, jamais aceito de fora.
    registro["output_path"] = resolve_source_code_path(component_type)
    if status == RUNNING and not registro.get("started_at"):
        registro["started_at"] = _now()
    if status in {COMPLETED, FAILED, CANCELLED}:
        registro["completed_at"] = _now()
    registro["updated_at"] = _now()

    state["tasks"][task_id] = registro
    if status == COMPLETED:
        state.setdefault("artifacts", {})[ARTIFACT_IDS[component_type]] = {
            "artifact_id": ARTIFACT_IDS[component_type],
            "component_type": component_type,
            "stack": registro.get("stack"),
            "path": registro["output_path"],
            "status": COMPLETED,
            "updated_at": _now(),
        }
    save_state(project_dir, state)
    return registro


def set_approval(project_dir: Path, state: dict[str, Any], *, status: str,
                 run_id: str | None = None, user: str | None = None,
                 note: str | None = None,
                 summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Registra o gate humano. Ausência de decisão NUNCA vira aprovação."""
    atual = (state.get("approval") or {}).get("status")
    assert_transition(atual, status)
    registro = dict(state.get("approval") or {
        "task_id": APPROVAL_TASK_ID,
        "type": "approval-gate",
        "artifact_id": APPROVAL_ARTIFACT,
        "decided_at": None,
        "user": None,
        "note": None,
        "run_id": None,
        "summary": None,
    })
    registro["status"] = status
    registro["run_id"] = run_id or registro.get("run_id")
    if user:
        registro["user"] = user
    if note:
        registro["note"] = note
    if summary is not None:
        registro["summary"] = summary
    if status in {APPROVED, REJECTED}:
        registro["decided_at"] = _now()
    registro["updated_at"] = _now()

    state["approval"] = registro
    artifacts = state.setdefault("artifacts", {})
    if status == APPROVED:
        artifacts[APPROVAL_ARTIFACT] = {
            "artifact_id": APPROVAL_ARTIFACT,
            "status": APPROVED,
            "decided_at": registro["decided_at"],
            "user": registro.get("user"),
        }
    else:
        # Rejeição/espera não deixam artifact de aprovação para trás: qualquer
        # consumidor que só cheque presença precisa ver ausência.
        artifacts.pop(APPROVAL_ARTIFACT, None)
    save_state(project_dir, state)
    return registro


def is_approved(state: dict[str, Any]) -> bool:
    """Única porta de entrada dos coders. Sem registro explícito → False."""
    return (state.get("approval") or {}).get("status") == APPROVED


def approval_status(state: dict[str, Any]) -> str | None:
    return (state.get("approval") or {}).get("status")


def scaffold_completed(state: dict[str, Any],
                       component_types: Iterable[str] = COMPONENT_TYPES) -> bool:
    return all(
        (scaffold_task(state, item) or {}).get("status") == COMPLETED
        for item in component_types
    )


def task_is_reusable(state: dict[str, Any], component_type: str,
                     tobe_root: Path) -> bool:
    """A task consta como concluída E o artefato ainda existe em disco.

    Estado persistido sozinho não basta (RF-012): alguém pode ter apagado
    `source-code/frontend/` entre duas execuções. Aqui a evidência mínima é o
    diretório canônico existir e não estar vazio.
    """
    registro = scaffold_task(state, component_type)
    if not registro or registro.get("status") != COMPLETED:
        return False
    destino = Path(tobe_root) / resolve_source_code_path(component_type)
    if not destino.is_dir():
        return False
    return any(destino.iterdir())


def blocked_by_gate(project_dir: Path, state: dict[str, Any],
                    motivo: str) -> dict[str, Any]:
    """Marca as etapas dependentes como bloqueadas após rejeição."""
    state.setdefault("downstream", {})
    state["downstream"] = {
        "status": BLOCKED,
        "reason": motivo,
        "updated_at": _now(),
    }
    save_state(project_dir, state)
    return state["downstream"]
