#!/usr/bin/env python3
"""
AVA Fabric — CLI de orquestração da esteira
============================================
Executa a esteira completa de agentes, uma etapa por vez, em contexto isolado.
Sucessor do ``pipeline_runner.py`` interativo da raiz do repo.

Fontes de verdade (nenhuma duplicada aqui)
------------------------------------------
=============================  ==============================================
Modelo · endpoint · proxy      ``src/shared/data/ava-pipeline.yaml``
Ordem da esteira               ``ava-pipeline.yaml`` → ``pipeline.steps``
Caminho da spec de cada agente ``agent_registry.py`` (~107 agentes)
URL do proxy Headroom          ``headroom_config.py --proxy-url``
=============================  ==============================================

Motores
-------
``--engine sdk``      chama o Foundry pelo SDK Anthropic; o modelo devolve os
                      artefatos em blocos ``<!-- FILE: ... -->`` (default)
``--engine copilot``  delega para ``agent_runner.py``: processo isolado por
                      agente, com gate de artefato e telemetria

Uso
---
    ava_pipeline.py run -p MeuERP-002 --all
    ava_pipeline.py run -p MeuERP-002 --phase F2 --dry-run
    ava_pipeline.py run -p MeuERP-002 --phase F2b --model sonnet --yes
    ava_pipeline.py run -p MeuERP-002 --agent ava-asis-inventory
    ava_pipeline.py list --phases
    ava_pipeline.py doctor -p MeuERP-002

Exit codes
----------
    0 — todas as etapas executadas ou puladas
    1 — ao menos uma etapa falhou
    2 — erro de configuração (projeto inexistente, chave ausente, plano inválido,
        --via-proxy com o proxy fora do ar)
  130 — abortado pelo usuário
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import agent_registry  # noqa: E402
import f4s_deterministic_harness as f4s_harness  # noqa: E402
import pipeline_config  # noqa: E402
import pipeline_plan  # noqa: E402
import proc_stream  # noqa: E402
import sdk_engine  # noqa: E402
from pipeline_plan import PlanError, Step  # noqa: E402
from sdk_engine import BOLD, CYAN, DIM, GREEN, MAGENTA, RED, RESET, YELLOW, Route  # noqa: E402

EXIT_OK, EXIT_FAILED, EXIT_CONFIG, EXIT_ABORTED = 0, 1, 2, 130
_SHELL_OPERATORS = frozenset({"&&", "||", "|", ";", "&", ">", ">>", "<", "2>"})

#: agent_runner.py só tem DAG para F1 — src/shared/data/pipeline-dag/ tem um
#: único arquivo. Nas demais etapas o motor copilot despacha apenas o
#: orquestrador, e o CLI diz isso em voz alta em vez de fingir cobertura.
DAG_DIR = REPO_ROOT / "src" / "shared" / "data" / "pipeline-dag"


def banner(text: str, color: str = CYAN) -> None:
    line = "─" * 68
    print(f"\n{color}{BOLD}{line}{RESET}")
    print(f"{color}{BOLD}  {text}{RESET}")
    print(f"{color}{BOLD}{line}{RESET}")


# ─── Rota (proxy Headroom) ───────────────────────────────────────────────────

def resolve_route(cfg: dict[str, Any], mode: str) -> Route:
    """Decide entre proxy e rota direta.

    ``auto``    usa o proxy se estiver no ar; senão degrada COM AVISO ALTO
    ``require`` aborta se o proxy não responder (nunca roda sem compressão)
    ``off``     sempre direto
    """
    endpoint = cfg.get("foundry", {}).get("endpoint", "")

    if mode == "off":
        return Route(base_url=endpoint, via_proxy=False)

    url = pipeline_config.proxy_url(cfg)
    alive = bool(url) and pipeline_config.proxy_alive(cfg)

    if alive:
        return Route(base_url=url, via_proxy=True)

    if mode == "require":
        raise SystemExit(
            f"ERRO: --via-proxy pedido mas o proxy Headroom não respondeu"
            f"{f' em {url}' if url else ''}.\n"
            "      Suba com: .\\src\\shared\\tools\\headroom\\run_standalone.ps1\n"
            "      Ou rode sem --via-proxy (rota direta, sem compressão)."
        )

    print(f"\n{YELLOW}{BOLD}  ⚠️  Headroom proxy não respondeu"
          f"{f' em {url}' if url else ''}.{RESET}")
    print(f"{YELLOW}      Degradando para o endpoint direto — SEM compressão de contexto.{RESET}")
    print(f"{YELLOW}      Para ativar: .\\src\\shared\\tools\\headroom\\run_standalone.ps1{RESET}")
    return Route(base_url=endpoint, via_proxy=False)


# ─── Interação ───────────────────────────────────────────────────────────────

def status_bar(steps: list[Step], idx: int, executed: list[str], skipped: list[str]) -> str:
    parts = []
    for i, s in enumerate(steps):
        if s.phase in executed:
            parts.append(f"{GREEN}✅{s.phase}{RESET}")
        elif s.phase in skipped:
            parts.append(f"{YELLOW}⏭{s.phase}{RESET}")
        elif i == idx:
            parts.append(f"{CYAN}{BOLD}▶{s.phase}{RESET}")
        else:
            parts.append(f"{DIM}○{s.phase}{RESET}")
    return "  " + "  ".join(parts)


def ask_permission(step: Step, idx: int, steps: list[Step], auto: bool,
                   executed: list[str], skipped: list[str]) -> str:
    """Retorna 'S' (sim), 'P' (pular), 'V' (ver skill) ou 'A' (abortar)."""
    print(f"\n{YELLOW}{'═' * 68}{RESET}")
    print(f"{YELLOW}{BOLD}  Passo {idx + 1}/{len(steps)} — {step.phase}{RESET}")
    print(f"{YELLOW}  {step.label}{RESET}")
    kind = "Tool" if step.kind == "tool" else "Agente"
    prefix = "" if step.kind == "tool" else "@"
    print(f"{DIM}  {kind:<7}: {prefix}{step.agent}"
          f"{f' (v{step.version})' if step.version else ''}{RESET}")
    if step.trigger:
        print(f"{DIM}  Trigger: {step.trigger}{RESET}")
    print(f"{YELLOW}{'═' * 68}{RESET}")
    print(status_bar(steps, idx, executed, skipped))

    if auto:
        print(f"  {DIM}[AUTO] Executando automaticamente...{RESET}")
        return "S"

    while True:
        resp = input(f"\n  {BOLD}Executar? [S]im / [P]ular / [V]er skill / [A]bortar: {RESET}")
        resp = resp.strip().upper()
        if resp in ("S", ""):
            return "S"
        if resp in ("P", "N"):
            return "P"
        if resp in ("V", "A"):
            return resp
        print(f"  {RED}Digite S, P, V ou A.{RESET}")


def select_phases_interactive(steps: list[Step]) -> list[str]:
    """Menu de grupos, para quem chamou `run` sem --phase e sem --all."""
    groups: list[str] = []
    for s in steps:
        if s.group not in groups:
            groups.append(s.group)

    print(f"\n{BOLD}Etapas disponíveis:{RESET}")
    for i, g in enumerate(groups, 1):
        members = [s for s in steps if s.group == g]
        agentes = ", ".join(f"@{m.agent.replace('ava-', '')}" for m in members)
        print(f"  {CYAN}{i}.{RESET} {g}  ({len(members)} passo(s))")
        print(f"     {DIM}{agentes}{RESET}")
    print(f"  {CYAN}{len(groups) + 1}.{RESET} Todas ({len(steps)} passos)")

    raw = input(f"\n{BOLD}Números das etapas (ex: 1 2 3) ou vazio para todas: {RESET}").strip()
    if not raw:
        return []
    selected: list[str] = []
    for tok in raw.replace(",", " ").split():
        if not tok.isdigit():
            continue
        idx = int(tok) - 1
        if idx == len(groups):
            return []
        if 0 <= idx < len(groups):
            selected.append(groups[idx])
    if not selected:
        raise SystemExit("ERRO: nenhuma etapa válida selecionada.")
    return selected


# ─── Motores ─────────────────────────────────────────────────────────────────

def copilot_dag(step: Step) -> Path:
    """DAG que o agent_runner consumiria para esta etapa.

    Usa a fase do MÓDULO (registry), não a etapa da esteira: os arquivos em
    pipeline-dag/ são nomeados pelo módulo. Para a etapa F5 (DevOps Execute) o
    DAG procurado é F6.yaml, porque devops-agents é o módulo F6.
    """
    return DAG_DIR / f"{step.registry_phase or step.phase}.yaml"


def copilot_argv(step: Step, project: str, route: Route) -> list[str]:
    """argv do agent_runner para esta etapa.

    Quando o agente da etapa é o **orquestrador da fase**, roda o DAG inteiro
    (sem ``--agent``): a etapa "F1 = @ava-asis-orchestrator | FP" significa
    "execute a fase F1 completa". Passar ``--agent ava-asis-orchestrator``
    filtraria zero nós — o orquestrador não é nó do DAG, é quem despacha.
    """
    phase = step.registry_phase or step.phase
    argv = [sys.executable, str(SCRIPT_DIR / "agent_runner.py"),
            "--project", project, "--phase", phase]
    if step.agent != agent_registry.orchestrator_of(phase):
        argv += ["--agent", step.agent]
    if step.feature:
        argv += ["--feature", step.feature]
    if route.via_proxy:
        argv.append("--via-proxy")
    return argv


def run_via_copilot(step: Step, project: str, route: Route, timeout_s: int) -> dict[str, Any]:
    """Delega ao agent_runner.py — processo isolado, gate de artefato, telemetria."""
    dag = copilot_dag(step)
    if not dag.is_file():
        print(f"{YELLOW}  ⚠️  Sem DAG para {dag.stem} — o agent_runner só cobre as fases "
              f"com arquivo em src/shared/data/pipeline-dag/.{RESET}")
        print(f"{YELLOW}      Etapa {step.phase} NÃO executada pelo motor copilot. "
              f"Use --engine sdk para esta etapa.{RESET}")
        return {"phase": step.phase, "agent": step.agent, "status": "skipped",
                "detail": f"sem DAG {dag.name}"}

    if step.trigger:
        # O agent_runner monta o próprio envelope a partir do DAG e não conhece
        # triggers. Duas etapas do mesmo orquestrador (F2b=DP e F5=DE) colapsam
        # no MESMO comando — o modo de operação se perde. Dizer isso alto é o
        # mínimo; distinguir de verdade exige um DAG por etapa.
        print(f"{YELLOW}  ⚠️  trigger {step.trigger!r} NÃO é propagado pelo motor copilot "
              f"— o agent_runner monta o envelope pelo DAG.{RESET}")
        print(f"{YELLOW}      Para honrar o trigger, use --engine sdk nesta etapa.{RESET}")

    argv = copilot_argv(step, project, route)
    print(f"{DIM}  $ {' '.join(argv[1:])}{RESET}\n")
    proc = subprocess.run(argv, cwd=str(REPO_ROOT), timeout=timeout_s, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"agent_runner.py saiu com código {proc.returncode}")
    return {"phase": step.phase, "agent": step.agent, "status": "completed"}


def resolve_tool_command(step: Step, project: str) -> list[str]:
    """Resolve placeholders without invoking a shell."""
    if step.kind != "tool" or not step.command:
        raise ValueError(f"{step.phase}: passo não é uma tool executável")
    resolved = []
    for part in step.command:
        if part == "{python}":
            resolved.append(sys.executable)
        else:
            resolved.append(part.replace("{project}", project))
    return resolved


def run_tool_step(step: Step, project: str,
                  timeout_s: int | None = None) -> dict[str, Any]:
    """Run one deterministic DAG node and propagate its real exit code.

    O teto sai do PRÓPRIO passo (``timeout_s`` do nó no DAG); o parâmetro
    homônimo é só o fallback dos chamadores legados, e o default global fecha
    a conta. Nada disso deriva de bounded contexts, de projetos ou de
    comandos — ver `pipeline_plan.DEFAULT_TOOL_TIMEOUT_S`.

    A saída da tool é transmitida AO VIVO, rotulada com a fase. Antes o
    processo herdava o console e, quando o teto estourava, morria levando
    junto todo o log; hoje o que já saiu está na tela e o rabo da saída
    viaja na exceção, para a mensagem de timeout poder mostrar onde parou.
    """
    command = resolve_tool_command(step, project)
    efetivo = pipeline_plan.resolve_tool_timeout_s(
        getattr(step, "timeout_s", None), fallback=timeout_s, label=step.phase)
    print(f"\n{DIM}  $ {' '.join(command)}{RESET}")
    print(f"{DIM}  teto: {efetivo}s — timeout_s do nó {step.phase} no DAG{RESET}\n")

    try:
        proc = proc_stream.run(command, cwd=REPO_ROOT, timeout_s=efetivo,
                               prefix=f"{DIM}[{step.phase}]{RESET} ",
                               stream=sys.stdout, merge_stderr=True)
    except subprocess.TimeoutExpired as exc:
        # Reetiqueta com o teto EFETIVO e o tempo real. Sem isso o operador
        # lê "899.9999895 seconds" e não tem como ligar o número a
        # configuração nenhuma — foi assim que a recomendação "aumente
        # timeout_s no DAG" apontou para uma propriedade que não existia.
        exc.phase = step.phase                             # type: ignore[attr-defined]
        exc.timeout_s = efetivo                            # type: ignore[attr-defined]
        exc.tail = proc_stream.tail(exc.output or "")      # type: ignore[attr-defined]
        raise
    if proc.returncode != 0:
        on_fail = str(getattr(step, "on_fail", "") or "")
        if on_fail == "warn":
            print(f"{YELLOW}  Tool {step.phase} reprovou (exit {proc.returncode}), "
                  f"mas on_fail=warn: registrando aviso e continuando.{RESET}")
            return {
                "phase": step.phase,
                "agent": step.agent,
                "kind": "tool",
                "status": "warning",
                "command": command,
                "exit_code": proc.returncode,
                "on_fail": "warn",
                "timeout_s": efetivo,
                "elapsed_s": round(getattr(proc, "elapsed_s", 0.0), 1),
            }
        erro =  RuntimeError(
            f"tool {step.agent} saiu com código {proc.returncode}: {' '.join(command)}"
        )
        # O código exato importa para quem decide o que fazer com a falha: o
        # runner só oferece aceite de risco no código reservado a lacunas de
        # qualidade (3). Ler isso da mensagem seria frágil.
        erro.returncode = proc.returncode  # type: ignore[attr-defined]
        raise erro
    return {
        "phase": step.phase,
        "agent": step.agent,
        "kind": "tool",
        "status": "completed",
        "command": command,
        "exit_code": proc.returncode,
        "timeout_s": efetivo,
        "elapsed_s": round(getattr(proc, "elapsed_s", 0.0), 1),
    }


def verification_argv(command: str) -> list[str]:
    """Parse one executable command and reject shell composition."""
    argv = shlex.split(command, posix=os.name != "nt")
    if os.name == "nt":
        argv = [
            token[1:-1] if len(token) >= 2 and token[0] == token[-1]
            and token[0] in {'"', "'"} else token
            for token in argv
        ]
    operators = [token for token in argv if token in _SHELL_OPERATORS]
    if operators:
        raise ValueError(
            f"verify_command contém operador de shell {operators[0]!r}; "
            "use um script verify.ps1/.sh como comando único"
        )
    if not argv:
        raise ValueError("verify_command vazio")
    return argv


def verify_task_step(step: Step, project: str, generation: dict[str, Any],
                     output_dir: Path, timeout_s: int,
                     client: Any = None, model: str = "",
                     cfg: dict[str, Any] | None = None,
                     route: Any = None,
                     agent_result: dict[str, Any] | None = None,
                     remediate: Callable[[int, dict[str, Any]], bool] | None = None,
                     branch_context: dict[str, Any] | None = None,
                     repo_root: Path | None = None) -> dict[str, Any]:
    """Run the task proof and persist its real exit code."""
    import task_ledger  # noqa: PLC0415

    root = repo_root or REPO_ROOT
    task = task_ledger.get(project, step.task_id, root)
    command = str(task.get("verify_command") or "").strip()
    output_dir.mkdir(parents=True, exist_ok=True)

    # F4 steps use the git-backed harness: build, remediate, commit/fail.
    if step.phase.startswith("F4"):
        return _verify_f4_task(step, project, generation, task, command,
                               output_dir, timeout_s, repo_root=root,
                               client=client, model=model, cfg=cfg,
                               route=route, agent_result=agent_result,
                               remediate=remediate, branch_context=branch_context)

    source_dir = (
        REPO_ROOT / "projects" / project / "outputs" / "tobe" / "source-code"
    )
    log_path = output_dir / f"verify_{step.task_id}.log"
    exit_code = 2
    output = ""

    if not command:
        output = "verify_command ausente no razão"
    elif not source_dir.is_dir():
        output = f"diretório de código ausente: {source_dir}"
    else:
        try:
            argv = verification_argv(command)
            proc = subprocess.run(
                argv, cwd=source_dir, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout_s, check=False,
            )
            exit_code = proc.returncode
            output = (proc.stdout or "") + (proc.stderr or "")
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            output = f"falha ao executar {command!r}: {exc}"

    log_path.write_text(output, encoding="utf-8")
    relative_log = str(log_path.relative_to(REPO_ROOT))
    state = task_ledger.record_result(
        project, step.task_id, command=command or "<missing verify_command>",
        exit_code=exit_code, log_path=relative_log,
        files_written=list(generation.get("artifacts") or []),
        recorded_by="ava_pipeline",
    )
    return {
        "task_id": step.task_id,
        "command": command,
        "exit_code": exit_code,
        "status": state["status"],
        "log": relative_log,
    }


def _build_failure_context(build_result: dict[str, Any], attempt: int,
                           feature: str, stack: str) -> str:
    """Build the remediation prompt appended to the coder agent invocation."""
    lines = [
        f"The previous implementation attempt for `{feature}` (stack `{stack}`) failed to build.",
        f"Remediation attempt: {attempt} of {f4s_harness.MAX_BUILD_ATTEMPTS - 1}.",
        "",
        "Build command:",
        f"  {build_result.get('command', 'unknown')}",
        "",
        "Build exit code:",
        f"  {build_result.get('exit_code', 'unknown')}",
        "",
        "Build output (stdout + stderr):",
        "```text",
        (build_result.get("stdout", "") + build_result.get("stderr", "")).strip(),
        "```",
        "",
        "Instructions:",
        "1. Read the current source tree and the failing build output above.",
        "2. Apply the minimal surgical changes required to make the build pass.",
        "3. Do NOT regenerate the entire scaffold; preserve existing working files.",
        "4. After writing changes, the pipeline will re-run the build automatically.",
    ]
    return "\n".join(lines)


def _make_remediation_callback(
    step: Step,
    project: str,
    stack: str,
    feature: str,
    output_dir: Path,
    client: Any,
    model: str,
    cfg: dict[str, Any],
    route: Any = None,
) -> Callable[[int, dict[str, Any]], bool] | None:
    """Return a callback that re-dispatches the SPECIALIZED coder on build failure.

    Etapas E (REFLECT) e F (CORRECT) do laço interno: quem recebe o erro é o
    mesmo agente que escreveu o código — nunca um agente genérico — e ele recebe
    a saída real do build, não um resumo.
    """
    if client is None or not model:
        return None

    agente = getattr(route, "agent", "") or step.agent
    spec_path = None
    if route is not None and getattr(route, "spec_path", ""):
        spec_path = REPO_ROOT / route.spec_path

    def remediate(attempt: int, build_result: dict[str, Any]) -> bool:
        context = _build_failure_context(build_result, attempt, feature, stack)
        rem_step = Step(
            phase=step.phase,
            group=step.group,
            agent=agente,
            spec_path=spec_path or step.spec_path,
            trigger=step.trigger,
            label=f"{step.label} · remediation attempt {attempt}",
            inputs=dict(step.inputs),
            feature=step.feature,
            target_stack=step.target_stack,
            task_id=step.task_id,
            task_group=step.task_group,
            remediation_context=context,
        )
        try:
            metrics = sdk_engine.run_step(
                client, rem_step, project, model, cfg, output_dir
            )
        except Exception as exc:  # noqa: BLE001 — remediation failure is not fatal
            print(f"  {YELLOW}⚠️  Remediation dispatch failed for {feature}: {exc}{RESET}")
            return False
        # If the agent produced no artifacts we assume it could not fix anything.
        altered = bool(metrics.get("artifacts"))
        if altered:
            print(f"  {GREEN}✅ Remediation for {feature} wrote {len(metrics['artifacts'])} file(s){RESET}")
        return altered

    return remediate


def _verify_f4_task(step: Step, project: str, generation: dict[str, Any],
                    task: dict[str, Any], command: str,
                    output_dir: Path, timeout_s: int,
                    repo_root: Path | None = None,
                    client: Any = None, model: str = "",
                    cfg: dict[str, Any] | None = None,
                    route: Any = None,
                    agent_result: dict[str, Any] | None = None,
                    remediate: Callable[[int, dict[str, Any]], bool] | None = None,
                    branch_context: dict[str, Any] | None = None,
                    ) -> dict[str, Any]:
    """Verificação determinística de UMA task da F4.

    Ordem: rota canônica → snapshot → build real (com até 2 remediações pelo
    agente especializado) → diff real → commit restrito ao componente → razão.
    O `status` sai daqui com exit code de comando real; nada do que o agente
    disse entra nessa decisão.
    """
    import task_ledger  # noqa: PLC0415
    import f4_routing  # noqa: PLC0415
    import f4s_git_helper as _git  # noqa: PLC0415

    root = repo_root or REPO_ROOT
    if route is None:
        # Fail-closed: sem rota não há diretório canônico nem agente — e um
        # caminho "padrão" aqui é como o código voltaria a `source-code/{stack}`.
        route = f4_routing.resolve_route(task, project, root)

    import f4_baseline  # noqa: PLC0415
    import f4_scope  # noqa: PLC0415

    stack = route.target_stack
    componente = route.component_type
    feature = task.get("feature") or step.feature or step.task_id
    rotulo = f"{step.task_id}·{feature}"
    command_override = command or None
    infra = not f4_scope.is_blocking(componente)

    repo = f4s_harness.ensure_repo(project, stack, repo_root=root,
                                   component_type=componente)
    work_dir = f4s_harness.component_source_dir(project, componente, root)
    f4s_harness.snapshot_before(repo, rotulo)

    branch = str((branch_context or {}).get("branch") or "")
    base_branch = str((branch_context or {}).get("base") or "")
    baseline = dict((branch_context or {}).get("baseline") or {})

    # ── 1. O que a task realmente mexeu, no repo inteiro ────────────────────
    # Sem pathspec de propósito: uma task de infraestrutura escreve em `infra/`,
    # e olhar só o diretório do componente foi o que fez os `.tf` sumirem.
    def _mudancas_da_task() -> list[str]:
        pendentes = _git.git_changed_files(repo)
        # Somado ao que a task já commitou no branch dela: da 2ª tentativa em
        # diante o arquivo da 1ª está commitado e sumiria do `git status`,
        # aparecendo como artefato ausente.
        commitados = _git.git_branch_changed_files(repo, base_branch) if branch else []
        vistos: list[str] = []
        for item in (*pendentes, *commitados):
            if item not in vistos:
                vistos.append(item)
        return vistos

    changed_all = _mudancas_da_task()
    reconciliacao = f4_scope.reconcile(
        task, changed=changed_all,
        agent_declared=list(generation.get("artifacts") or []),
        kind=componente)

    # ── 2. Verificação ──────────────────────────────────────────────────────
    if infra:
        # Infra não é dependência de compilação: a prova determinística da task
        # é ter produzido os artefatos no escopo. `terraform validate` entra
        # como validação **advisória** — falha dele não reprova o `.tf` gerado.
        validacao = _run_advisory_validation(route, work_dir, repo, timeout_s)
        exit_code = 0 if reconciliacao.has_output else 2
        final_command = validacao.get("command") or " ".join(route.build_command)
        result = {"success": exit_code == 0, "attempts": [], "abort_needed": False,
                  "toolchain_missing": validacao.get("toolchain_missing", "")}
        comparacao: dict[str, Any] = {}
    else:
        if remediate is None:
            remediate = _make_remediation_callback(
                step, project, stack, feature, output_dir, client, model,
                cfg or {}, route=route)
        result = f4s_harness.run_build_with_remediation(
            repo, stack, rotulo,
            command_override=command_override,
            remediate=remediate,
            timeout=timeout_s,
            work_dir=work_dir,
        )
        final_command = (result["attempts"][-1]["command"] if result["attempts"]
                         else command)
        ultimo = result["attempts"][-1] if result["attempts"] else {}
        comparacao = f4_baseline.compare(baseline, ultimo)
        validacao = {"command": final_command,
                     "exit_code": result["final_exit_code"],
                     "errors": comparacao.get("errorsAfter", 0),
                     "warnings": comparacao.get("warningsAfter", 0)}
        exit_code = result["final_exit_code"]
        # O exit code registrado é SEMPRE o real. Antes, "não introduziu erro
        # novo" forçava `exit_code = 0` e a task virava `verified` — 18 tasks de
        # `cadastro-funcionario-03` foram integradas como sucesso sem que um
        # único build tivesse passado. Falha preexistente permite **integrar**
        # (o trabalho não se perde), nunca **verificar**.
        result["integrable_sem_verificacao"] = bool(
            exit_code and comparacao.get("integrable"))

        # Reconciliação refeita: a remediação escreve arquivos depois do 1º diff.
        changed_all = _mudancas_da_task()
        reconciliacao = f4_scope.reconcile(
            task, changed=changed_all,
            agent_declared=list(generation.get("artifacts") or []),
            kind=componente)

    # ── 3. Commit no branch da task, restrito ao escopo reconciliado ────────
    # Commit quando a verificação passou; ou, se ela reprovou, apenas dentro do
    # branch da task — é o "commit de diagnóstico" que preserva a tentativa sem
    # levar código quebrado para o branch principal.
    commit_hash = ""
    pendentes_no_disco = set(_git.git_changed_files(repo))
    a_commitar = [item for item in reconciliacao.to_commit
                  if item in pendentes_no_disco]
    pode_commitar = bool(a_commitar) and (result["success"] or bool(branch))
    if pode_commitar:
        _git.git_add_paths(repo, a_commitar)
        commit_hash = _git.git_commit(
            repo,
            f"feat({componente}/{stack}): implement {step.task_id} {feature}",
            stage_all=False)
    if result["success"]:
        f4s_harness.snapshot_after(repo, rotulo)
        f4s_harness.reset_consecutive_skips_counter(repo)

    # ── 4. Integração ao branch principal ──────────────────────────────────
    integravel = bool(commit_hash) and (
        result["success"] or result.get("integrable_sem_verificacao", False))
    merge = {"status": "not_attempted"}
    if branch and base_branch and integravel:
        merge = _git.merge_branch(
            repo, branch, into=base_branch,
            message=f"merge {branch} ({step.task_id}) into {base_branch}")
        if merge.get("status") == "conflict":
            integravel = False
    elif branch and base_branch:
        # Branch preservado de propósito: é a evidência do que a task tentou.
        merge = {"status": "preserved_for_review", "branch": branch}

    # ── 5. Estado de execução ──────────────────────────────────────────────
    execution_status, review_reason = _f4_execution_status(
        infra=infra, success=result["success"], reconciliacao=reconciliacao,
        comparacao=comparacao, merge=merge, validacao=validacao,
        toolchain=result.get("toolchain_missing", ""),
        attempts=int(task.get("attempts", 0)) + 1)

    campos = {
        "taskName": task.get("title") or step.label,
        "taskType": componente,
        "branchName": branch,
        "baseBranch": base_branch,
        "mergedToMain": merge.get("status") == "merged",
        "mergeStatus": merge.get("status"),
        "scaffoldPath": baseline.get("scaffoldPath") or work_dir.as_posix(),
        "scaffoldReused": bool(baseline.get("scaffoldReused", not infra)),
        "scaffoldRecreated": False,
        "baselineBuild": baseline or None,
        "buildAttempts": len(result.get("attempts") or []),
        "remediationAttempts": max(0, len(result.get("attempts") or []) - 1),
        "validationResults": validacao,
        "generatedArtifacts": list(reconciliacao.to_commit),
        "modifiedFiles": list(changed_all),
        "missingArtifacts": list(reconciliacao.missing),
        "alternativeArtifactPaths": list(reconciliacao.alternative_paths),
        "excludedFromCommit": list(reconciliacao.excluded),
        "artifactReconciliation": reconciliacao.as_dict()["artifacts"],
        "finishedAt": _utc_now(),
        "finalSummary": review_reason or "task concluida e integrada",
    }
    if comparacao:
        campos["buildComparison"] = comparacao

    state = task_ledger.record_result(
        project, step.task_id,
        command=final_command or f"<build:{stack}>",
        exit_code=exit_code,
        log_path=str((repo / "GENERATION_LOG.md").relative_to(root)),
        files_written=list(reconciliacao.to_commit)
        or list(generation.get("artifacts") or []),
        recorded_by="ava_pipeline",
        routing=route.as_dict(),
        commit_hash=commit_hash or None,
        summary_text=review_reason or "build verificado e commitado",
        agent_result=agent_result,
        execution_status=execution_status or None,
        review_reason=review_reason,
        fields=campos,
        repo_root=root,
    )

    return {
        "task_id": step.task_id,
        "feature": feature,
        "stack": stack,
        "agent": route.agent,
        "component_type": componente,
        "canonical_source_dir": route.canonical_source_rel,
        "routing_reason": route.reason,
        "command": final_command,
        "exit_code": exit_code,
        "status": state["status"],
        "execution_status": execution_status,
        "review_reason": review_reason,
        "files_written": list(reconciliacao.to_commit),
        "excluded_from_commit": list(reconciliacao.excluded),
        "missing_artifacts": list(reconciliacao.missing),
        "alternative_paths": list(reconciliacao.alternative_paths),
        "commit_hash": commit_hash,
        "branch": branch,
        "merged": merge.get("status") == "merged",
        "merge_status": merge.get("status"),
        "attempts": len(result.get("attempts") or []),
        "ledger_attempts": state.get("attempts"),
        # `abort_needed` continua sendo devolvido para telemetria; o laço NÃO
        # para por causa dele — uma task falhando não é motivo para abandonar
        # as outras 162.
        "abort_needed": result.get("abort_needed", False),
        "toolchain_missing": result.get("toolchain_missing") or "",
        "validation": validacao,
        "log": str((repo / "GENERATION_LOG.md").relative_to(root)),
    }


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _run_advisory_validation(route: Any, work_dir: Path, repo: Path,
                             timeout_s: int) -> dict[str, Any]:
    """Validação de infraestrutura — informativa, nunca bloqueante.

    `terraform validate` sem `terraform init`, sem credencial e sem provider
    baixado falha por motivos que nada dizem sobre o `.tf` gerado. O resultado
    entra em `validationResults`; quem decide o status é a reconciliação de
    artefatos.
    """
    comando = list(route.build_command or [])
    if not comando:
        return {"command": "", "exit_code": None, "skipped": "sem comando"}
    faltando = ""
    try:
        import f4s_build_runner  # noqa: PLC0415
        faltando = f4s_build_runner.executable_missing(comando)
    except Exception:  # noqa: BLE001
        faltando = ""
    if faltando:
        return {"command": " ".join(comando), "exit_code": 127,
                "toolchain_missing": faltando,
                "errors": [f"ferramenta ausente no PATH: {faltando}"],
                "warnings": ["validacao de infraestrutura nao executada"]}
    try:
        proc = subprocess.run(comando, cwd=str(work_dir), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=timeout_s, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"command": " ".join(comando), "exit_code": 1,
                "errors": [f"{type(exc).__name__}: {exc}"], "warnings": []}
    saida = (proc.stdout or "") + (proc.stderr or "")
    return {"command": " ".join(comando), "exit_code": proc.returncode,
            "errors": ([saida.strip()[:2000]] if proc.returncode else []),
            "warnings": ([] if proc.returncode == 0
                         else ["validacao externa reprovou; artefatos preservados"])}


def _f4_execution_status(*, infra: bool, success: bool, reconciliacao: Any,
                         comparacao: dict[str, Any], merge: dict[str, Any],
                         validacao: dict[str, Any], toolchain: str,
                         attempts: int) -> tuple[str, str]:
    """Traduz o resultado real da task no vocabulário de execução.

    Nenhum caminho aqui devolve "pendente": toda task que chegou até este ponto
    termina com um estado terminal e um motivo legível.
    """
    import task_ledger  # noqa: PLC0415

    if infra:
        if not reconciliacao.has_output:
            return (task_ledger.EXEC_REVIEW,
                    "task de infraestrutura nao produziu artefato algum no escopo")
        if validacao.get("exit_code") not in (0, None):
            detalhe = (f"toolchain ausente: {toolchain}" if toolchain
                       else f"validacao externa exit {validacao.get('exit_code')}")
            return (task_ledger.EXEC_COMPLETED_WARN,
                    f"artefatos gerados e commitados; {detalhe} "
                    f"(nao bloqueante para a esteira)")
        return task_ledger.EXEC_COMPLETED, ""

    if toolchain:
        return (task_ledger.EXEC_REVIEW,
                f"limitacao externa comprovada: toolchain `{toolchain}` ausente; "
                f"o codigo foi gerado mas nao pode ser compilado aqui")
    if merge.get("status") == "conflict":
        return (task_ledger.EXEC_REVIEW,
                f"conflito ao integrar {merge.get('branch')} em "
                f"{merge.get('into')}; branch preservado")
    if success:
        # Build REALMENTE passou (exit 0). Só aqui existe `completed`.
        if comparacao.get("warningsAfter"):
            return (task_ledger.EXEC_COMPLETED_WARN,
                    f"build verde com {comparacao['warningsAfter']} aviso(s)")
        return task_ledger.EXEC_COMPLETED, ""

    # Build reprovado. Enquanto houver tentativa, a task continua RETENTÁVEL —
    # o limite de remediação é por task e precisa ser gasto antes de qualquer
    # estado terminal.
    if attempts < task_ledger.MAX_ATTEMPTS:
        return "", "build reprovado nesta tentativa; branch preservado"

    if comparacao.get("samePreexistingFailure"):
        # Mesma falha do baseline: a task não é culpada e o trabalho é
        # integrado — mas o componente NÃO compila, e isso não pode ser
        # registrado como conclusão. Quem conserta o baseline é gente.
        return (task_ledger.EXEC_REVIEW,
                f"integrada sem piorar o quadro, mas o componente NAO compila "
                f"desde o baseline (falha {comparacao.get('failureSignature')} "
                f"identica a do scaffold); a task nao pode ser verificada")
    return (task_ledger.EXEC_FAILED_AFTER_REMEDIATION,
            f"build reprovado apos {attempts} tentativa(s) e as remediacoes do "
            f"limite (falha {comparacao.get('failureSignature') or 'sem assinatura'}"
            f", baseline {comparacao.get('baselineStatus')}); branch preservado")


# ─── Subcomando: run ─────────────────────────────────────────────────────────

def preflight_inputs(steps: list, project: str, cfg: dict, verbose: bool = False) -> bool:
    """Confere os insumos declarados de cada passo **antes** de qualquer inferência.

    Devolve ``True`` quando ao menos um passo está bloqueado por insumo
    obrigatório ausente. Passo sem `inputs:` declarado é ignorado — usa o
    caminho legado e não tem contrato a conferir.

    Existe por causa do defeito da spec 039 §2 P-1: a esteira rodou 105 minutos e
    gerou 140 arquivos sem que um único artefato TO-BE tivesse chegado ao
    gerador. Falhar em 2 segundos é estritamente melhor.
    """
    declarados = [s for s in steps if getattr(s, "inputs", None)]
    if not declarados:
        return False

    bloqueados = False
    for step in declarados:
        res = sdk_engine.resolve_context(project, step, cfg)
        if res.blocked:
            bloqueados = True
            msg = sdk_engine.context_manifest.format_missing(
                res, step.phase, step.agent, project)
            print(f"\n{RED}{msg}{RESET}", file=sys.stderr)
        elif verbose:
            obrig = sum(1 for i in res.included if i.tier == "mandatory")
            compl = len(res.included) - obrig
            print(f"  {DIM}{step.phase:<4} insumos: {obrig} obrigatórios, "
                  f"{compl} complementares{RESET}")
            for item in res.included:
                marca = "*" if item.tier == "mandatory" else " "
                print(f"    {DIM}{marca} {item.rel} ({len(item.body):,} chars){RESET}")
            for m in res.missing_advisory:
                print(f"    {YELLOW}~ ausente (complementar): {m.pattern}{RESET}")
    return bloqueados


def cmd_run(args: argparse.Namespace) -> int:
    cfg = pipeline_config.load_config(args.project)

    proj_dir = pipeline_config.project_dir(args.project)
    if not proj_dir.is_dir():
        print(f"ERRO: projeto não encontrado: projects/{args.project}", file=sys.stderr)
        print(f"      Disponíveis: {', '.join(list_projects()) or '(nenhum)'}", file=sys.stderr)
        return EXIT_CONFIG

    phases = [p for raw in (args.phase or []) for p in raw.split(",") if p.strip()]
    if not phases and not args.all and not args.agent:
        phases = select_phases_interactive(pipeline_plan.declared_steps(cfg))

    try:
        steps = pipeline_plan.build_plan(cfg, phases or None, args.agent, args.start_at)
    except PlanError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    # Fan-out: um passo por grupo de tasks, cada um com a sua fatia e o agente
    # coder real da stack. Sem razão de progresso em disco, degrada com aviso.
    steps = pipeline_plan.expand_foreach(steps, args.project)

    problems = pipeline_plan.validate_plan(steps)
    if problems:
        print("ERRO: plano incoerente com o agent_registry:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return EXIT_CONFIG

    engine = args.engine or cfg.get("execution", {}).get("engine", "sdk")
    model = pipeline_config.resolve_model(cfg, args.model)
    mode = args.proxy_mode or cfg.get("proxy", {}).get("mode", "auto")
    auto = args.yes or cfg.get("execution", {}).get("confirm") == "auto"
    timeout_s = int(cfg.get("execution", {}).get("timeout_s", 900))
    output_dir = proj_dir / cfg.get("execution", {}).get("output_subdir", "outputs/pipeline_runner")

    try:
        route = resolve_route(cfg, mode)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG

    print(f"\n{MAGENTA}{'═' * 68}{RESET}")
    print(f"{MAGENTA}{BOLD}  AVA Fabric — Pipeline Runner{RESET}")
    print(f"{MAGENTA}{'═' * 68}{RESET}")
    print(f"  {BOLD}Projeto  :{RESET} {args.project}")
    print(f"  {BOLD}Rota     :{RESET} {route.label} → {route.base_url}")
    print(f"  {BOLD}Modelo   :{RESET} {model}")
    print(f"  {BOLD}Motor    :{RESET} {engine}")
    print(f"  {BOLD}Passos   :{RESET} {len(steps)}")
    print(f"  {BOLD}Outputs  :{RESET} projects/{args.project}/"
          f"{cfg.get('execution', {}).get('output_subdir')}")
    print()
    print(pipeline_plan.format_table(steps))

    # As entradas internas da F3S são causais: a tool do manifesto precisa rodar
    # antes que specification possa exigi-lo. Elas recebem preflight passo a
    # passo no loop de execução; conferir todas aqui bloquearia o produtor pela
    # ausência do próprio output.
    initial_preflight = [step for step in steps if not step.phase.startswith("F3S:")]
    blocked = preflight_inputs(initial_preflight, args.project, cfg, verbose=args.dry_run)
    if blocked and not args.dry_run:
        return EXIT_CONFIG

    if args.dry_run:
        banner("DRY RUN — nenhuma inferência executada", CYAN)
        for s in steps:
            if s.kind == "tool":
                print(f"  {s.phase:<24} tool  {' '.join(resolve_tool_command(s, args.project))}")
            elif engine == "sdk":
                chars = sdk_engine.estimate_prompt_chars(s, args.project, cfg)
                print(f"  {s.phase:<4} prompt ≈ {chars:>9,} chars (~{chars // 4:,} tokens)  "
                      f"| {s.build_prompt(args.project)}")
            else:
                dag = copilot_dag(s)
                mark = "✅        " if dag.is_file() else f"⚠️  sem {dag.name}"
                cmd = " ".join(copilot_argv(s, args.project, route)[2:])
                print(f"  {s.phase:<4} {mark}  agent_runner.py {cmd}")
        return EXIT_CONFIG if blocked else EXIT_OK

    if engine == "sdk":
        if sdk_engine.apply_dns_overrides(cfg):
            print(f"  {DIM}[dns] overrides aplicados{RESET}")
        try:
            api_key = pipeline_config.api_key(cfg)
        except SystemExit as exc:
            print(str(exc), file=sys.stderr)
            return EXIT_CONFIG
        client = sdk_engine.make_client(cfg, route, api_key)
        print(f"\n{BOLD}[Auth]{RESET} Testando conectividade...")
        try:
            sdk_engine.ping(client, model)
            print(f"{GREEN}  ✅ Conectado — {model} pronto ({route.label}).{RESET}")
        except Exception as exc:  # noqa: BLE001
            print(f"{RED}  ❌ Falha na conexão: {exc}{RESET}", file=sys.stderr)
            return EXIT_CONFIG
    else:
        client = None

    run_id = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    executed: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []
    aborted = False
    results: list[dict[str, Any]] = []

    idx = 0
    while idx < len(steps):
        step = steps[idx]
        if str(step.foreach.get("source")) == "dag":
            try:
                expanded = pipeline_plan.expand_runtime_dag(step, args.project)
            except PlanError as exc:
                print(f"ERRO: {exc}", file=sys.stderr)
                failed.append(step.phase)
                results.append({"phase": step.phase, "agent": step.agent,
                                "status": "failed", "detail": str(exc)})
                break
            problems = pipeline_plan.validate_plan(expanded)
            if problems:
                failed.append(step.phase)
                results.append({"phase": step.phase, "agent": step.agent,
                                "status": "failed", "detail": "; ".join(problems)})
                break
            steps[idx:idx + 1] = expanded
            continue
        if step.phase.startswith("F3S:") and preflight_inputs(
                [step], args.project, cfg, verbose=False):
            failed.append(step.phase)
            results.append({"phase": step.phase, "agent": step.agent,
                            "status": "failed", "detail": "insumo obrigatório ausente"})
            break
        if step.task_id:
            import task_ledger  # noqa: PLC0415
            ready_ids = {task["task_id"] for task in task_ledger.ready_tasks(args.project)}
            if step.task_id not in ready_ids:
                diagnosis = task_ledger.diagnose(args.project)
                detail = f"task não pronta: {diagnosis['status']}"
                results.append({"phase": step.phase, "agent": step.agent,
                                "task_id": step.task_id, "status": "blocked",
                                "detail": detail, "diagnosis": diagnosis})
                failed.append(step.phase)
                print(f"\n{RED}  ❌ {step.task_id} não executada — {detail}{RESET}")
                continue
        while True:
            try:
                decision = ask_permission(step, idx, steps, auto, executed, skipped)
            except (EOFError, KeyboardInterrupt):
                aborted = True
                decision = "A"

            if decision == "V":
                if step.kind == "tool":
                    print(f"\n{DIM}{' '.join(resolve_tool_command(step, args.project))}{RESET}")
                    continue
                skill = sdk_engine.load_skill(step, cfg)
                print(f"\n{DIM}{textwrap.fill(skill[:2000], width=88)}{RESET}")
                if len(skill) > 2000:
                    print(f"{DIM}  [...] (skill truncado — {len(skill):,} chars total){RESET}")
                continue

            if decision == "A":
                aborted = True
                banner("Pipeline abortado pelo usuário", RED)
                break

            if decision == "P":
                if step.task_id:
                    import task_ledger  # noqa: PLC0415
                    task_ledger.skip(args.project, step.task_id, "pulada pelo operador")
                skipped.append(step.phase)
                print(f"  {YELLOW}⏭  Passo {step.phase} pulado.{RESET}")
                break

            try:
                if step.task_id:
                    import task_ledger  # noqa: PLC0415
                    task_ledger.start(args.project, step.task_id, run_id=run_id)
                if step.kind == "tool":
                    result = run_tool_step(step, args.project, timeout_s)
                elif engine == "sdk":
                    result = sdk_engine.run_step(client, step, args.project, model, cfg, output_dir)
                else:
                    result = run_via_copilot(step, args.project, route, timeout_s)
                if step.task_id:
                    if result.get("status") == "skipped":
                        import task_ledger  # noqa: PLC0415
                        state = task_ledger.record_result(
                            args.project, step.task_id, command="agent dispatch",
                            exit_code=1, recorded_by="ava_pipeline")
                        result["status"] = state["status"]
                    else:
                        result["verification"] = verify_task_step(
                            step, args.project, result, output_dir, timeout_s)
                        result["status"] = (
                            "completed" if result["verification"]["status"] == "verified"
                            else "failed"
                        )
                        if result["verification"].get("abort_needed"):
                            aborted = True
                            banner(
                                f"F4 abortado: {result['verification'].get('abort_reason', '')}",
                                RED,
                            )
                            break
                results.append(result)
                if result.get("status") == "warning":
                    skipped.append(step.phase)
                elif result.get("status") in {"failed", "blocked"}:
                    failed.append(step.phase)
                elif result.get("status") == "skipped":
                    skipped.append(step.phase)
                else:
                    executed.append(step.phase)
            except KeyboardInterrupt:
                aborted = True
                banner("Interrompido pelo usuário", RED)
                break
            except Exception as exc:  # noqa: BLE001 — falha de um passo não derruba a esteira
                if step.task_id:
                    try:
                        import task_ledger  # noqa: PLC0415
                        current = task_ledger.get(args.project, step.task_id)
                        if current.get("status") == "in_progress":
                            task_ledger.record_result(
                                args.project, step.task_id, command="agent execution",
                                exit_code=1, recorded_by="ava_pipeline")
                    except Exception:
                        pass
                print(f"\n{RED}  ❌ Erro no passo {step.phase}: {exc}{RESET}", file=sys.stderr)
                results.append({"phase": step.phase, "agent": step.agent,
                                "status": "failed", "detail": str(exc)[:500]})
                if not auto:
                    try:
                        if input("  Tentar novamente? [S/N]: ").strip().upper() == "S":
                            continue
                    except (EOFError, KeyboardInterrupt):
                        pass
                failed.append(step.phase)
            break

        if aborted:
            break
        idx += 1

    _write_run_state(proj_dir, run_id, args.project, route, model, engine,
                     steps, executed, skipped, failed, aborted, results)

    banner("Execução concluída", RED if failed or aborted else GREEN)
    print(f"\n  {GREEN}✅ Executados ({len(executed)}): {', '.join(executed) or '—'}{RESET}")
    print(f"  {YELLOW}⏭  Pulados   ({len(skipped)}): {', '.join(skipped) or '—'}{RESET}")
    if failed:
        print(f"  {RED}❌ Falharam  ({len(failed)}): {', '.join(failed)}{RESET}")
    if aborted:
        print(f"  {RED}🛑 Abortado pelo usuário{RESET}")
    print(f"\n  {DIM}Estado do run: projects/{args.project}/outputs/.runs/{run_id}/run.json{RESET}\n")

    if args.json:
        print(json.dumps({"project": args.project, "run_id": run_id, "route": route.label,
                          "model": model, "engine": engine, "results": results},
                         ensure_ascii=False, indent=2))

    if aborted:
        return EXIT_ABORTED
    return EXIT_FAILED if failed else EXIT_OK


def _write_run_state(proj_dir: Path, run_id: str, project: str, route: Route, model: str,
                     engine: str, steps: list[Step], executed: list[str], skipped: list[str],
                     failed: list[str], aborted: bool, results: list[dict[str, Any]]) -> None:
    run_dir = proj_dir / "outputs" / ".runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps({
        "run_id": run_id, "project": project, "model": model, "engine": engine,
        "route": route.label, "base_url": route.base_url,
        "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "plan": [s.as_dict() for s in steps],
        "executed": executed, "skipped": skipped, "failed": failed, "aborted": aborted,
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── Subcomando: list ────────────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace) -> int:
    cfg = pipeline_config.load_config(args.project)

    if args.agents:
        entries = [e for e in agent_registry.catalog()
                   if not args.phase or e["phase"] in args.phase]
        for e in entries:
            print(f"  {e['phase']:<3}  {e['agent']:<40}  v{e['version']}")
        print(f"\n  {DIM}{len(entries)} agente(s) — fonte: agent_registry.py{RESET}")
        return EXIT_OK

    try:
        steps = pipeline_plan.build_plan(cfg)
    except PlanError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    print(f"\n{BOLD}Ordem da esteira{RESET} {DIM}(src/shared/data/ava-pipeline.yaml "
          f"→ pipeline.steps){RESET}\n")
    print(pipeline_plan.format_table(steps))
    print(f"\n  {DIM}--phase aceita a etapa (F2b) ou o grupo (F2). "
          f"Grupos: {', '.join(dict.fromkeys(s.group for s in steps))}{RESET}")
    print(f"  {DIM}As etapas são a ORDEM DA ESTEIRA, não os módulos do agent_registry: "
          f"aqui F5=DevOps e F6=QA.{RESET}\n")

    problems = pipeline_plan.validate_plan(steps)
    for p in problems:
        print(f"  ⚠️  {p}", file=sys.stderr)
    return EXIT_CONFIG if problems else EXIT_OK


# ─── Subcomando: config ──────────────────────────────────────────────────────

def cmd_config(args: argparse.Namespace) -> int:
    cfg = pipeline_config.load_config(args.project)
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
    return EXIT_OK


# ─── Subcomando: doctor ──────────────────────────────────────────────────────

def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = pipeline_config.load_config(args.project)
    checks: list[tuple[bool, str, str]] = []

    checks.append((pipeline_config.TOOL_CONFIG.is_file(), "config",
                   str(pipeline_config.TOOL_CONFIG.relative_to(REPO_ROOT))))

    key_path = pipeline_config.api_key_path(cfg)
    has_key = key_path.is_file() and bool(key_path.read_text(encoding="utf-8").strip())
    checks.append((has_key, "API key", str(key_path.name) if has_key else f"ausente: {key_path}"))

    try:
        import anthropic
        checks.append((True, "SDK anthropic", anthropic.__version__))
    except ImportError:
        checks.append((False, "SDK anthropic",
                       "ausente — pip install -r src/shared/tools/requirements-pipeline.txt"))

    url = pipeline_config.proxy_url(cfg)
    alive = bool(url) and pipeline_config.proxy_alive(cfg)
    checks.append((alive, "proxy Headroom",
                   f"{url} no ar" if alive else f"fora do ar ({url or 'URL não resolvida'})"))

    try:
        steps = pipeline_plan.build_plan(cfg)
        problems = pipeline_plan.validate_plan(steps)
        checks.append((not problems, "plano da esteira",
                       f"{len(steps)} passos" if not problems else "; ".join(problems[:3])))
    except PlanError as exc:
        checks.append((False, "plano da esteira", str(exc)[:120]))

    if args.project:
        proj = pipeline_config.project_dir(args.project)
        checks.append((proj.is_dir(), "projeto", str(args.project) if proj.is_dir()
                       else f"não encontrado: projects/{args.project}"))
        cfg_path = pipeline_config.project_config_path(args.project)
        checks.append((cfg_path.is_file(), "project-config.yaml",
                       "ok" if cfg_path.is_file() else f"ausente: {cfg_path}"))

    print()
    for ok, name, detail in checks:
        icon = f"{GREEN}✅" if ok else f"{RED}❌"
        print(f"  {icon} {name:<22}{RESET} {detail}")
    print(f"\n  {DIM}modelo={pipeline_config.resolve_model(cfg)} · "
          f"endpoint={cfg.get('foundry', {}).get('endpoint')}{RESET}\n")

    # O proxy fora do ar é degradação prevista (mode=auto), não erro de config.
    hard = [c for c in checks if not c[0] and c[1] != "proxy Headroom"]
    return EXIT_CONFIG if hard else EXIT_OK


# ─── Utilidades ──────────────────────────────────────────────────────────────

def list_projects() -> list[str]:
    root = REPO_ROOT / "projects"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_"))


# ─── Entrypoint ──────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="ava-pipeline",
        description="Orquestra a esteira de agentes AVA Fabric",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Exemplos:
              ava-pipeline run -p MeuERP-002 --all
              ava-pipeline run -p MeuERP-002 --phase F2 --dry-run
              ava-pipeline run -p MeuERP-002 --phase F2b --model sonnet --yes
              ava-pipeline run -p MeuERP-002 --agent ava-asis-inventory
              ava-pipeline run -p MeuERP-002 --all --from F4 --via-proxy
              ava-pipeline list --phases
              ava-pipeline doctor -p MeuERP-002

            Exit codes: 0 ok · 1 etapa falhou · 2 erro de configuração · 130 abortado
        """),
    )
    sub = ap.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Executa a esteira (ou parte dela)")
    run.add_argument("-p", "--project", required=True, help="Nome do projeto em projects/")
    sel = run.add_mutually_exclusive_group()
    sel.add_argument("--phase", action="append", metavar="ID",
                     help="Etapa (F2b) ou grupo (F2). Repetível; aceita F1,F2")
    sel.add_argument("--all", action="store_true", help="Todas as etapas da esteira, em ordem")
    run.add_argument("--agent", metavar="ID",
                     help="Roda só este agente (da esteira ou avulso do agent_registry)")
    run.add_argument("--model", help="Wire model ou alias (ex: sonnet)")
    run.add_argument("--engine", choices=pipeline_config.ENGINES,
                     help="sdk (SDK Anthropic) | copilot (agent_runner.py)")
    run.add_argument("--from", dest="start_at", metavar="ID",
                     help="Começa nesta etapa, cortando o prefixo")
    proxy = run.add_mutually_exclusive_group()
    proxy.add_argument("--via-proxy", dest="proxy_mode", action="store_const", const="require",
                       help="Exige o proxy Headroom; aborta se estiver fora do ar")
    proxy.add_argument("--no-proxy", dest="proxy_mode", action="store_const", const="off",
                       help="Força a rota direta, sem compressão")
    run.add_argument("--yes", "-y", action="store_true", help="Não pergunta a cada passo")
    run.add_argument("--dry-run", action="store_true",
                     help="Mostra o plano e a rota sem gastar inferência")
    run.add_argument("--json", action="store_true", help="Emite o resultado em JSON no final")
    run.set_defaults(func=cmd_run, proxy_mode=None)

    lst = sub.add_parser("list", help="Lista a ordem da esteira ou o catálogo de agentes")
    lst.add_argument("-p", "--project")
    lst.add_argument("--phases", action="store_true", help="Ordem da esteira (default)")
    lst.add_argument("--agents", action="store_true", help="Catálogo do agent_registry")
    lst.add_argument("--phase", action="append", help="Filtra --agents por fase do módulo")
    lst.set_defaults(func=cmd_list)

    cfgp = sub.add_parser("config", help="Mostra a configuração efetiva")
    cfgp.add_argument("-p", "--project")
    cfgp.add_argument("--json", action="store_true", help="(saída já é JSON)")
    cfgp.set_defaults(func=cmd_config)

    doc = sub.add_parser("doctor", help="Diagnostica config, chave, SDK, proxy e plano")
    doc.add_argument("-p", "--project")
    doc.set_defaults(func=cmd_doctor)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print(f"\n{RED}Interrompido.{RESET}", file=sys.stderr)
        return EXIT_ABORTED
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        print(str(exc.code), file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
