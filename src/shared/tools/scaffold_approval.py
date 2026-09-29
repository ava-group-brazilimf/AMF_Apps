#!/usr/bin/env python3
"""Gate humano entre o baseline compilável e os agentes coder.

Política vigente: o operador tem **60 segundos** para decidir. Esgotado o
prazo — ou não havendo terminal — o baseline é **aprovado automaticamente** e os
agentes coder são despachados.

Isso inverte o desenho original, em que ausência de resposta bloqueava. O
trade-off é real e vale enunciar: um baseline que COMPILA mas está errado (BC
faltando, versão de framework trocada, blueprint desatualizado) passa sozinho
quando ninguém está olhando, e os coders geram features inteiras sobre ele. O
gate deixa de ser barreira e vira janela de veto.

Por isso a decisão automática é gravada como tal (`decided_by`: `user` |
`timeout` | `non-interactive`, mais `auto_approved`): quem auditar depois
consegue separar "alguém revisou e aprovou" de "o prazo venceu".

Rejeição continua exigindo ato explícito — nada aqui rejeita sozinho. E o modo
estrito antigo permanece disponível: `timeout_s=0` (ou
`AVA_SCAFFOLD_APPROVAL_TIMEOUT=0`) restaura o bloqueio por ausência de resposta.

Nada aqui espera indefinidamente: o prazo é finito e sem terminal a função
retorna na hora. Loop de espera ativa num passo de pipeline é como se perde uma
noite de CI.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from scaffold_state import (
    APPROVED,
    AWAITING_USER_APPROVAL,
    REJECTED,
    _now,
    save_state,
    set_approval,
)

# Cores: o runner de produção usa os mesmos códigos ANSI.
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"

_STACK_LABELS = {
    "dotnet": ".NET", "angular": "Angular", "react": "React", "vue": "Vue",
    "blazor": "Blazor", "spring-boot": "Spring Boot", "fastapi": "FastAPI",
    "gin": "Gin", "nestjs": "NestJS",
}


def _label(stack: Any) -> str:
    valor = str(stack or "—")
    return _STACK_LABELS.get(valor.lower(), valor)


def _linha_status(status: Any) -> str:
    mapa = {
        "succeeded": f"{GREEN}concluída com sucesso{RESET}",
        "failed": f"{RED}falhou{RESET}",
        "skipped": f"{DIM}pulada{RESET}",
        "toolchain_unavailable": f"{YELLOW}toolchain indisponível{RESET}",
        None: f"{DIM}—{RESET}",
    }
    return mapa.get(status, str(status))


def build_summary(state: dict[str, Any], *, commit_sha: str | None = None,
                  log_path: str | None = None) -> dict[str, Any]:
    """Resumo estruturado do que será aprovado — a base da mensagem e do estado."""
    from scaffold_state import TASK_IDS

    componentes: dict[str, Any] = {}
    for component_type, task_id in TASK_IDS.items():
        registro = state.get("tasks", {}).get(task_id) or {}
        componentes[component_type] = {
            "task_id": task_id,
            "stack": registro.get("stack"),
            "status": registro.get("status"),
            "output_path": registro.get("output_path"),
            "restore_status": registro.get("restore_status"),
            "build_status": registro.get("build_status"),
            "verification_status": registro.get("verification_status"),
            "error_count": len(registro.get("error_summary") or []) if isinstance(
                registro.get("error_summary"), list) else (1 if registro.get("error_summary") else 0),
            "warning_count": registro.get("warning_count"),
            "attempts": registro.get("attempts"),
        }
    return {
        "components": componentes,
        "commit_sha": commit_sha,
        "log_path": log_path,
    }


def render_summary(summary: dict[str, Any]) -> str:
    """Mensagem exibida ao operador. Stack é informação; diretório é contrato."""
    frente = summary["components"].get("frontend", {})
    fundo = summary["components"].get("backend", {})
    linhas = [
        "",
        f"{CYAN}{'═' * 72}{RESET}",
        f"{CYAN}{BOLD}  APROVAÇÃO NECESSÁRIA — BASELINE DE SCAFFOLD{RESET}",
        f"{CYAN}{'═' * 72}{RESET}",
        "",
        "  Os scaffolds foram gerados e validados com sucesso.",
        "",
        f"  {BOLD}Frontend:{RESET}",
        f"    - Stack: {_label(frente.get('stack'))}",
        f"    - Diretório: {frente.get('output_path') or '—'}/",
        f"    - Compilação: {_linha_status(frente.get('build_status'))}",
    ]
    if frente.get("warning_count") is not None:
        linhas.append(f"    - Warnings: {frente['warning_count']}")
    linhas += [
        "",
        f"  {BOLD}Backend:{RESET}",
        f"    - Stack: {_label(fundo.get('stack'))}",
        f"    - Diretório: {fundo.get('output_path') or '—'}/",
        f"    - Restore: {_linha_status(fundo.get('restore_status'))}",
        f"    - Compilação: {_linha_status(fundo.get('build_status'))}",
    ]
    if fundo.get("warning_count") is not None:
        linhas.append(f"    - Warnings: {fundo['warning_count']}")
    linhas.append("")
    if summary.get("commit_sha"):
        linhas.append(f"  O baseline compilável foi registrado no repositório "
                      f"({summary['commit_sha'][:12]}).")
    else:
        linhas.append(f"  {YELLOW}Nenhum commit de baseline foi criado.{RESET}")
    if summary.get("log_path"):
        linhas.append(f"  Log: {summary['log_path']}")
    linhas += [
        "",
        "  Deseja continuar com a geração das funcionalidades pelos agentes coder?",
        "",
        f"    {GREEN}[A]{RESET} Aprovar e continuar",
        f"    {RED}[R]{RESET} Rejeitar e interromper",
        "",
        f"  {YELLOW}Sem resposta, o baseline é APROVADO automaticamente "
        f"e os coders são despachados.{RESET}",
        f"{CYAN}{'═' * 72}{RESET}",
        "",
    ]
    return "\n".join(linhas)


#: Janela de resposta do operador, em segundos. Esgotada, o gate APROVA
#: automaticamente e os agentes coder são despachados.
#:
#: Isto é uma inversão consciente do desenho original, que tratava ausência de
#: resposta como bloqueio. O trade-off aceito: um baseline que COMPILA mas está
#: errado (BC faltando, versão trocada, blueprint desatualizado) passa sozinho
#: quando ninguém está olhando, e os coders geram features inteiras sobre ele.
#: Por isso a aprovação automática é registrada como tal em `tasks-progress.json`
#: (`decided_by`), e não se confunde com decisão humana em auditoria.
#:
#: `0` desliga a automação e restaura o comportamento estrito: sem resposta, o
#: estado fica `awaiting_user_approval` e nada avança.
DEFAULT_APPROVAL_TIMEOUT_S = 60


def _timeout_configurado(explicito: int | None) -> int:
    if explicito is not None:
        return max(0, int(explicito))
    bruto = os.environ.get("AVA_SCAFFOLD_APPROVAL_TIMEOUT", "").strip()
    if bruto.isdigit():
        return int(bruto)
    return DEFAULT_APPROVAL_TIMEOUT_S


def _pode_perguntar() -> bool:
    """Só pergunta quando existe alguém para responder."""
    if os.environ.get("AVA_NON_INTERACTIVE") == "1":
        return False
    try:
        return bool(sys.stdin) and sys.stdin.isatty()
    except (ValueError, AttributeError):
        return False


def _input_com_timeout(prompt: str, segundos: int) -> str | None:
    """Lê uma linha do stdin com prazo. `None` quando o prazo esgota.

    A leitura vai para uma thread daemon: `input()` não é interrompível e não
    existe API portável de stdin com timeout. Esgotado o prazo, a thread é
    abandonada — daemon, então não segura o encerramento do processo.

    Efeito colateral conhecido: a thread abandonada continua bloqueada no
    stdin. Se algo adiante no mesmo processo voltar a ler stdin, uma tecla
    digitada tarde pode ser consumida por ela. Na esteira isso não acontece
    porque o gate é o último ponto interativo antes do despacho dos coders.
    """
    import threading

    resultado: list[str] = []

    def ler() -> None:
        try:
            resultado.append(input())
        except (EOFError, KeyboardInterrupt, OSError):
            pass

    print(prompt, end="", flush=True)
    thread = threading.Thread(target=ler, daemon=True)
    thread.start()
    thread.join(timeout=segundos)
    if thread.is_alive() or not resultado:
        return None
    return resultado[0]


#: Resultados do gate de falha de componente.
OVERRIDE_CONTINUED = "continued"
OVERRIDE_ABORTED = "aborted"


def request_failure_override(project_dir, state: dict[str, Any], *,
                             component_type: str,
                             resultado: dict[str, Any],
                             decision: str | None = None,
                             interactive: bool | None = None,
                             timeout_s: int | None = None) -> dict[str, Any]:
    """Falha de componente vira decisão do operador, não beco sem saída.

    Antes, componente reprovado encerrava o passo na hora (RF-011: não há valor
    em compilar metade do sistema). A regra continua certa como DEFAULT, mas
    executá-la em silêncio tirava do operador uma escolha que é dele: às vezes
    a falha é periférica — um projeto de teste que não gerou — e ele prefere
    seguir para as fases seguintes sabendo do risco.

    Aqui a política é o INVERSO do gate de aprovação do baseline: **falha
    silenciosa fecha**. Sem terminal, com prazo esgotado ou em CI, o resultado
    é `aborted`. Aprovar por ausência faria a esteira seguir sobre um scaffold
    quebrado sem que ninguém tivesse visto o erro — que é exatamente o que
    torna o defeito caro três fases adiante.

    A decisão fica gravada em `state["failure_overrides"]` com quem decidiu,
    para que a auditoria separe "alguém viu e aceitou o risco" de "passou".
    """
    registro: dict[str, Any] = {
        "component_type": component_type,
        "stack": resultado.get("stack"),
        "error": str(resultado.get("error") or "falhou")[:2000],
        "at": _now(),
    }

    def _decidir(status: str, por: str) -> dict[str, Any]:
        registro.update({"status": status, "decided_by": por})
        historico = state.setdefault("failure_overrides", [])
        historico.append(registro)
        save_state(project_dir, state)
        return registro

    if decision:
        escolha = str(decision).strip().casefold()
        if escolha in {"continue", "continuar", "c", OVERRIDE_CONTINUED}:
            return _decidir(OVERRIDE_CONTINUED, "flag")
        return _decidir(OVERRIDE_ABORTED, "flag")

    pode = _pode_perguntar() if interactive is None else bool(interactive)
    if not pode:
        return _decidir(OVERRIDE_ABORTED, "non-interactive")

    prazo = _timeout_configurado(timeout_s)
    print(f"\n{YELLOW}{BOLD}  Falha em {component_type} — decisão do operador"
          f"{RESET}")
    print(f"  {DIM}Prosseguir mantém o scaffold parcial em disco e libera as "
          f"fases seguintes,{RESET}")
    print(f"  {DIM}mas os agentes coder permanecem bloqueados: eles exigem "
          f"baseline compilável.{RESET}")
    resposta = _input_com_timeout(
        f"  {BOLD}[C]ontinuar mesmo assim ou [A]bortar? "
        f"(Enter = abortar, {prazo}s): {RESET}", prazo)

    if resposta is None:
        print(f"  {RED}prazo esgotado — abortado.{RESET}")
        return _decidir(OVERRIDE_ABORTED, "timeout")
    if resposta.strip().casefold() in {"c", "continuar", "continue"}:
        print(f"  {YELLOW}risco aceito pelo operador — seguindo.{RESET}")
        return _decidir(OVERRIDE_CONTINUED, "user")
    print(f"  {RED}abortado pelo operador.{RESET}")
    return _decidir(OVERRIDE_ABORTED, "user")


def request_approval(project_dir, state: dict[str, Any], *,
                     summary: dict[str, Any],
                     run_id: str | None = None,
                     decision: str | None = None,
                     user: str | None = None,
                     note: str | None = None,
                     interactive: bool | None = None,
                     timeout_s: int | None = None) -> dict[str, Any]:
    """Apresenta o gate, espera `timeout_s` e decide.

    Caminhos possíveis:
      - `decision` explícito ("approve"/"reject") → honrado, `decided_by=user`;
      - terminal interativo → pergunta com prazo; resposta manda;
      - prazo esgotado → APROVA, `decided_by=timeout`;
      - sem terminal (esteira automática) → APROVA, `decided_by=non-interactive`;
      - `timeout_s=0` → modo estrito: sem resposta, fica em espera e nada avança.

    Rejeição continua exigindo ato explícito: nada aqui rejeita sozinho.
    """
    identidade = user or os.environ.get("AVA_APPROVAL_USER") or os.environ.get("USERNAME") or None
    prazo = _timeout_configurado(timeout_s)

    def _decidir(status: str, *, por: str, observacao: str | None = None) -> dict[str, Any]:
        # A máquina de estados não aceita saltar direto para approved/rejected:
        # o gate precisa constar como ALCANÇADO antes de ser decidido, senão um
        # `set_approval(APPROVED)` solto em qualquer ponto do código passaria a
        # valer como aprovação. Chegar aqui É alcançar o gate.
        if not (state.get("approval") or {}).get("status"):
            set_approval(project_dir, state, status=AWAITING_USER_APPROVAL,
                         run_id=run_id,
                         user=identidade if por == "user" else None,
                         summary=summary)
        registro = set_approval(project_dir, state, status=status, run_id=run_id,
                                user=identidade if por == "user" else None,
                                note=observacao or note, summary=summary)
        # `set_approval` só sobrescreve `user` quando recebe valor — para não
        # apagar o autor numa transição posterior. Aqui a intenção é o oposto:
        # decisão automática NÃO pode sair com nome de gente. Limpamos explícito.
        if por != "user":
            registro["user"] = None
        # `decided_by` separa decisão humana de automática. Sem isso, uma
        # auditoria não distingue "alguém revisou e aprovou" de "ninguém estava
        # olhando e o prazo venceu" — que é exatamente a diferença que importa.
        registro["decided_by"] = por
        registro["auto_approved"] = (status == APPROVED and por != "user")
        registro["timeout_s"] = prazo
        state["approval"] = registro
        save_state(project_dir, state)
        return registro

    if decision in {"approve", "approved", "reject", "rejected"}:
        alvo = APPROVED if decision in {"approve", "approved"} else REJECTED
        return _decidir(alvo, por="user")

    print(render_summary(summary))

    permitido = _pode_perguntar() if interactive is None else interactive

    if not permitido:
        if prazo == 0:
            print(f"  {YELLOW}Sem terminal interativo e modo estrito ativo — "
                  f"nenhuma decisão foi tomada.{RESET}")
            print(f"  {DIM}Retome com --approve ou --reject.{RESET}\n")
            return set_approval(project_dir, state, status=AWAITING_USER_APPROVAL,
                                run_id=run_id, user=identidade, summary=summary)
        print(f"  {YELLOW}Sem terminal interativo — APROVAÇÃO AUTOMÁTICA.{RESET}")
        print(f"  {DIM}Registrado como decisão automática, não humana "
              f"(decided_by=non-interactive).{RESET}\n")
        return _decidir(APPROVED, por="non-interactive",
                        observacao="aprovado automaticamente: execução sem terminal")

    if prazo == 0:
        rotulo = "  Aprovar? [A]provar / [R]ejeitar: "
        try:
            bruto = input(rotulo)
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {YELLOW}Interrompido sem decisão — mantido em espera.{RESET}\n")
            return set_approval(project_dir, state, status=AWAITING_USER_APPROVAL,
                                run_id=run_id, user=identidade, summary=summary)
    else:
        print(f"  {DIM}Sem resposta em {prazo}s, o baseline é aprovado "
              f"automaticamente e os coders são despachados.{RESET}")
        bruto = _input_com_timeout(
            f"  Aprovar? [A]provar / [R]ejeitar  ({prazo}s): ", prazo)
        if bruto is None:
            print(f"\n  {YELLOW}Prazo de {prazo}s esgotado — APROVAÇÃO "
                  f"AUTOMÁTICA.{RESET}")
            print(f"  {DIM}Registrado como decisão automática, não humana "
                  f"(decided_by=timeout).{RESET}\n")
            return _decidir(APPROVED, por="timeout",
                            observacao=f"aprovado automaticamente após {prazo}s sem resposta")

    resposta = (bruto or "").strip().upper()

    if resposta in {"A", "APROVAR", "S", "SIM", "Y", "YES"}:
        registro = _decidir(APPROVED, por="user")
        print(f"  {GREEN}Aprovado. Os agentes coder estão liberados.{RESET}\n")
        return registro
    if resposta in {"R", "REJEITAR", "N", "NAO", "NÃO", "NO"}:
        registro = _decidir(REJECTED, por="user")
        print(f"  {RED}Rejeitado. Nenhum agente coder será executado.{RESET}")
        print(f"  {DIM}Os scaffolds gerados foram preservados.{RESET}\n")
        return registro

    # Resposta ilegível NÃO vira aprovação automática: quem digitou algo estava
    # presente e quis decidir. Tratar um typo como "aprovado" seria pior que o
    # silêncio, porque o operador acredita ter respondido.
    print(f"  {YELLOW}Resposta não reconhecida ({resposta!r}) — "
          f"nenhuma decisão registrada.{RESET}")
    print(f"  {DIM}O gate volta na próxima execução.{RESET}\n")
    return set_approval(project_dir, state, status=AWAITING_USER_APPROVAL,
                        run_id=run_id, user=identidade, summary=summary)
