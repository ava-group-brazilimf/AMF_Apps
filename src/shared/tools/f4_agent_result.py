#!/usr/bin/env python3
"""
f4_agent_result.py — Contrato estruturado da resposta dos coders da F4.

O que o agente devolve é **evidência de execução**, nunca autoridade de status.
Este módulo faz três coisas, nessa ordem de importância:

1. extrai o bloco de resultado da resposta do modelo;
2. valida o contrato (campos obrigatórios, tipos, coerência com a task/rota);
3. classifica os arquivos escritos: dentro ou fora do diretório canônico.

O que ele **não** faz: decidir se a task passou. `implementation_status:
completed` no JSON do agente é uma afirmação do modelo — o `verified` só sai de
`task_ledger.record_result` com `exit_code == 0` de um build real. Um contrato
válido com `local_checks[].exit_code: 0` continua valendo zero como prova; ele
serve para diagnóstico e para o relatório de observabilidade.

Formato aceito na resposta do agente
------------------------------------
    <!-- F4_RESULT -->
    { ... json ... }
    <!-- /F4_RESULT -->

ou, como tolerância, uma cerca ```json contendo `task_id` e `schema_version`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "1.0.0"

_SENTINEL_BLOCK = re.compile(
    r"<!--\s*F4_RESULT\s*-->\s*(?:```(?:json)?\s*)?(.*?)(?:```\s*)?<!--\s*/F4_RESULT\s*-->",
    re.DOTALL | re.IGNORECASE,
)
_JSON_FENCE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)

IMPLEMENTATION_STATUSES = frozenset({"completed", "failed", "blocked"})


class ContractError(Exception):
    """Resposta do agente fora do contrato. Nunca vira sucesso silencioso."""

    def __init__(self, message: str, *, code: str = "CONTRACT000") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class AgentResult:
    """Resultado declarado pelo agente, já validado estruturalmente."""

    task_id: str
    agent: str
    implementation_status: str
    attempt: int = 1
    task_type: str = ""
    target_stack: str = ""
    canonical_source_dir: str = ""
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    commands_executed: list[str] = field(default_factory=list)
    local_checks: list[dict[str, Any]] = field(default_factory=list)
    acceptance_results: list[dict[str, Any]] = field(default_factory=list)
    sentinel_path: str = ""
    error: str | None = None
    blocker: str | None = None
    #: Preenchido pelo validador, não pelo agente.
    files_outside_canonical: list[str] = field(default_factory=list)
    parse_error: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def declared_files(self) -> list[str]:
        vistos: list[str] = []
        for item in (*self.files_created, *self.files_modified):
            if item not in vistos:
                vistos.append(item)
        return vistos

    @property
    def claims_success(self) -> bool:
        """O agente DIZ que terminou. Não confunda com `verified`."""
        return self.implementation_status == "completed"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "task_id": self.task_id,
            "agent": self.agent,
            "attempt": self.attempt,
            "task_type": self.task_type,
            "target_stack": self.target_stack,
            "canonical_source_dir": self.canonical_source_dir,
            "implementation_status": self.implementation_status,
            "files_created": list(self.files_created),
            "files_modified": list(self.files_modified),
            "files_deleted": list(self.files_deleted),
            "commands_executed": list(self.commands_executed),
            "local_checks": list(self.local_checks),
            "acceptance_results": list(self.acceptance_results),
            "sentinel_path": self.sentinel_path,
            "error": self.error,
            "blocker": self.blocker,
            "files_outside_canonical": list(self.files_outside_canonical),
            "parse_error": self.parse_error,
        }


def extract(response: str) -> dict[str, Any]:
    """Extrai o objeto de resultado da resposta bruta do modelo."""
    if not response:
        raise ContractError("resposta vazia do agente", code="CONTRACT001")

    bruto = ""
    achado = _SENTINEL_BLOCK.search(response)
    if achado:
        bruto = achado.group(1).strip()
    else:
        for candidato in _JSON_FENCE.finditer(response):
            texto = candidato.group(1)
            if '"task_id"' in texto:
                bruto = texto.strip()
                break
    if not bruto:
        raise ContractError(
            "bloco <!-- F4_RESULT --> ausente na resposta do agente",
            code="CONTRACT002")
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError as exc:
        raise ContractError(f"resultado do agente nao e JSON valido: {exc}",
                            code="CONTRACT003") from exc
    if not isinstance(dados, dict):
        raise ContractError("resultado do agente nao e um objeto JSON",
                            code="CONTRACT004")
    return dados


def _string_list(dados: dict[str, Any], chave: str) -> list[str]:
    valor = dados.get(chave) or []
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, list):
        raise ContractError(f"`{chave}` precisa ser lista de strings",
                            code="CONTRACT005")
    return [str(item).replace("\\", "/").strip() for item in valor if str(item).strip()]


def _normalize_rel(caminho: str, project: str) -> str:
    """Normaliza para o espaço de caminhos de `source-code/`.

    O agente declara caminhos das duas formas: absoluto-do-repositório
    (`projects/P/outputs/tobe/source-code/backend/x.cs`) e relativo ao repo de
    código (`backend/x.cs`, que é como o SpecKit escreve `target_files` e como o
    `git status` responde). Tratar a segunda forma como "fora do canônico"
    produzia um aviso falso em toda task — `backend/Directory.Packages.props`
    era anunciado como recusado enquanto era commitado normalmente.
    """
    import f4_scope  # noqa: PLC0415

    return f4_scope.normalize(caminho)


def validate(dados: dict[str, Any], *, task: dict[str, Any], route: Any,
             project: str, attempt: int = 1) -> AgentResult:
    """Valida o contrato contra a task e a rota. Levanta `ContractError`."""
    task_id = str(task.get("task_id") or "")
    declarado = str(dados.get("task_id") or "").strip()
    if not declarado:
        raise ContractError("`task_id` ausente no resultado do agente",
                            code="CONTRACT006")
    if declarado != task_id:
        raise ContractError(
            f"resultado do agente e de outra task: {declarado!r} != {task_id!r} "
            f"— o despacho e de uma task por vez",
            code="CONTRACT007")

    status = str(dados.get("implementation_status") or "").strip().lower()
    if status not in IMPLEMENTATION_STATUSES:
        raise ContractError(
            f"implementation_status invalido: {status!r} "
            f"(aceitos: {', '.join(sorted(IMPLEMENTATION_STATUSES))})",
            code="CONTRACT008")

    import f4_scope  # noqa: PLC0415

    canonico_rel = getattr(route, "canonical_source_rel", "")
    componente = getattr(route, "component_type", "") or (
        canonico_rel.rsplit("/", 1)[-1] if canonico_rel else "")

    criados = _string_list(dados, "files_created")
    modificados = _string_list(dados, "files_modified")
    # A pergunta é "pertence ao escopo desta task?", e quem responde é a MESMA
    # política que decide o commit (`f4_scope`). Duas respostas diferentes para
    # a mesma pergunta era o que fazia o aviso contradizer o commit.
    fora = [item for item in (*criados, *modificados)
            if componente and not f4_scope.is_allowed(item, componente, task)]

    checks = dados.get("local_checks") or []
    if not isinstance(checks, list):
        raise ContractError("`local_checks` precisa ser lista", code="CONTRACT009")
    aceites = dados.get("acceptance_results") or []
    if not isinstance(aceites, list):
        raise ContractError("`acceptance_results` precisa ser lista",
                            code="CONTRACT010")

    return AgentResult(
        task_id=task_id,
        agent=str(dados.get("agent") or getattr(route, "agent", "")),
        implementation_status=status,
        attempt=int(dados.get("attempt") or attempt),
        task_type=str(dados.get("task_type") or getattr(route, "component_type", "")),
        target_stack=str(dados.get("target_stack") or getattr(route, "target_stack", "")),
        canonical_source_dir=str(dados.get("canonical_source_dir") or canonico_rel),
        files_created=criados,
        files_modified=modificados,
        files_deleted=_string_list(dados, "files_deleted"),
        commands_executed=_string_list(dados, "commands_executed"),
        local_checks=[item for item in checks if isinstance(item, dict)],
        acceptance_results=[item for item in aceites if isinstance(item, dict)],
        sentinel_path=str(dados.get("sentinel_path") or ""),
        error=(str(dados["error"]) if dados.get("error") else None),
        blocker=(str(dados["blocker"]) if dados.get("blocker") else None),
        files_outside_canonical=fora,
        raw=dict(dados),
    )


def parse(response: str, *, task: dict[str, Any], route: Any, project: str,
          attempt: int = 1, strict: bool = False) -> AgentResult:
    """Extrai + valida. Com `strict=False`, contrato ausente vira diagnóstico.

    Por que não é estrito por padrão: o contrato é **evidência**, e a prova de
    verdade é o build. Recusar a task porque o agente esqueceu o bloco JSON
    trocaria uma falha de forma por uma falha de resultado — o build ainda vai
    rodar e ainda vai decidir. O `parse_error` fica registrado no ledger e no
    log, e `strict=True` existe para quem quiser o contrário.
    """
    try:
        dados = extract(response)
        return validate(dados, task=task, route=route, project=project,
                        attempt=attempt)
    except ContractError as exc:
        if strict:
            raise
        return AgentResult(
            task_id=str(task.get("task_id") or ""),
            agent=str(getattr(route, "agent", "")),
            implementation_status="failed",
            attempt=attempt,
            task_type=str(getattr(route, "component_type", "")),
            target_stack=str(getattr(route, "target_stack", "")),
            canonical_source_dir=str(getattr(route, "canonical_source_rel", "")),
            error=str(exc),
            parse_error=f"{exc.code}: {exc}",
        )


def contract_template(project: str, task: dict[str, Any], route: Any,
                      attempt: int = 1) -> str:
    """O bloco que o agente precisa devolver — usado no prompt da task."""
    modelo = {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "run_id": "{run_id}",
        "task_id": task.get("task_id"),
        "task_type": getattr(route, "component_type", ""),
        "target_stack": getattr(route, "target_stack", ""),
        "agent": getattr(route, "agent", ""),
        "canonical_source_dir": getattr(route, "canonical_source_rel", ""),
        "attempt": attempt,
        "implementation_status": "completed|failed|blocked",
        "files_created": [],
        "files_modified": [],
        "files_deleted": [],
        "commands_executed": [],
        "local_checks": [
            {"command": "", "exit_code": 0, "stdout_summary": "",
             "stderr_summary": ""}
        ],
        "acceptance_results": [
            {"criterion": "", "status": "passed|failed", "evidence": ""}
        ],
        "sentinel_path": "",
        "error": None,
        "blocker": None,
    }
    return json.dumps(modelo, ensure_ascii=False, indent=2)
