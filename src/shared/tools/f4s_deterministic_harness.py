#!/usr/bin/env python3
"""
f4s_deterministic_harness.py — orquestração determinística da fase F4 (Tech Stack).

Cada task do razão vira um commit (ou skip documentado) dentro do repo git de
`outputs/tobe/source-code/{target_stack}/`. O harness:

  1. inicializa o repo git na primeira task de cada stack;
  2. captura snapshot da árvore antes/depois;
  3. executa o build de verificação;
  4. aplica até 2 rodadas de remediação quando o build falha;
  5. commita no git quando o build passa;
  6. gera um Compilation Failure Report embutido em GENERATION_LOG.md quando
     a task é pulada;
  7. aborta a geração após 3 specs consecutivas puladas por falha de build.

Este módulo não gera código — ele envolve a geração (delegada ao agente/codegen)
com git, build e registro estruturado.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import f4s_build_runner as build_runner
import f4s_generation_log as gen_log
import f4s_git_helper as git
import f4s_tree_snapshot as tree_snapshot
import scaffold_paths


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HarnessError(Exception):
    """Erro de configuração ou execução do harness F4S."""


MAX_BUILD_ATTEMPTS = 3  # build inicial + 2 remediações
MAX_CONSECUTIVE_SKIPS = 3


def _tobe_root(project: str, repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    return root / "projects" / project / "outputs" / "tobe"


def repo_dir(project: str, repo_root: Path | None = None) -> Path:
    """Repositório git do código gerado — `source-code/`, o mesmo do baseline F4S.

    Um repo por stack (`source-code/dotnet/.git`) criava um repositório aninhado
    dentro do baseline que a F4S commita em `source-code/`, e nenhum commit
    representava "o sistema", só "esta metade". A F4 commita no MESMO repo que a
    F4S inaugurou.
    """
    return _tobe_root(project, repo_root) / scaffold_paths.SOURCE_CODE_ROOT


#: Escopo de infraestrutura da F4. Não passa por `scaffold_paths` porque aquele
#: módulo é a autoridade dos DOIS componentes que a F4S gera — e mudá-lo
#: alteraria o comportamento da F4S, que está fora do escopo desta correção.
INFRA_COMPONENT = "infra"


def component_source_dir(project: str, component_type: str,
                         repo_root: Path | None = None) -> Path:
    """`source-code/{frontend|backend|infra}`."""
    if str(component_type).strip().lower() == INFRA_COMPONENT:
        return repo_dir(project, repo_root) / INFRA_COMPONENT
    return scaffold_paths.resolve_output_dir(
        _tobe_root(project, repo_root), component_type)


def stack_source_dir(project: str, stack: str, repo_root: Path | None = None) -> Path:
    """Diretório canônico do componente ao qual a stack pertence.

    O nome permanece por compatibilidade de chamada, mas o comportamento mudou:
    ele nunca mais devolve `source-code/{stack}`. A stack apenas **classifica**
    (`angular` → frontend, `dotnet` → backend); o caminho vem da
    responsabilidade, exatamente como na F4S.
    """
    return component_source_dir(
        project, scaffold_paths.component_type_for_stack(stack), repo_root)


def _gitignore_lines(stack: str) -> list[str]:
    """Conteúdo padrão de .gitignore para repos de source-code."""
    ignores = [
        "# Build artifacts",
        "bin/",
        "obj/",
        "*.dll",
        "*.exe",
        "*.pdb",
        "node_modules/",
        "dist/",
        "__pycache__/",
        ".venv/",
        "venv/",
        "target/",
        "*.class",
        "*.jar",
        "",
        "# IDE / cache",
        ".vs/",
        ".idea/",
        ".vscode/",
        "",
        "# AVA Fabric internal state",
        "f4s-state.json",
        ".f4s/",
    ]
    if stack in {"dotnet", "blazor"}:
        ignores.extend(["", "# .NET", "*.user", "*.suo"])
    if stack in {"angular", "react", "vue", "nestjs"}:
        ignores.extend(["", "# Node", ".angular/", ".next/"])
    return ignores


def ensure_repo(project: str, stack: str, repo_root: Path | None = None, *,
                component_type: str | None = None) -> Path:
    """Garante o repo git de `source-code/` e o diretório canônico do componente.

    Idempotente sobre o baseline da F4S: `git_init` não faz nada quando o repo
    já existe, e o `.gitignore` do baseline é preservado.
    """
    repo = repo_dir(project, repo_root)
    repo.mkdir(parents=True, exist_ok=True)
    git.git_init(repo)

    componente = component_type or scaffold_paths.component_type_for_stack(stack)
    if componente == INFRA_COMPONENT:
        destino = component_source_dir(project, componente, repo_root)
        destino.mkdir(parents=True, exist_ok=True)
        gen_log.init_log(repo)
        return repo
    destino = component_source_dir(project, componente, repo_root)
    destino.mkdir(parents=True, exist_ok=True)

    gitignore = repo / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("\n".join(_gitignore_lines(stack)) + "\n", encoding="utf-8")
        # Só o `.gitignore`: um `add --all` aqui varreria para o commit de
        # inicialização o código que a task acabou de escrever, e a task
        # terminaria "sem nada a commitar".
        git.git_add_paths(repo, [".gitignore"])
        git.git_commit(repo, "chore: initialize F4S repo with .gitignore",
                       stage_all=False)
    gen_log.init_log(repo)
    return repo


def _load_state(repo: Path) -> dict[str, Any]:
    return gen_log.load_state(repo)


def _consecutive_skips(state: dict[str, Any]) -> int:
    """Quantas specs **distintas** foram puladas em sequência.

    O sinal que este contador existe para dar é "a geração inteira está
    quebrada" — três *specs diferentes* seguidas falhando. Contar rodadas
    repetidas da MESMA spec transforma "uma task esgotou suas 3 tentativas" em
    "aborte a fase": medido em `cadastro-funcionario-03`, `T-W0-FE-001` sozinha
    produziu três entradas `skipped` e derrubou a F4 com 162 tasks nunca
    tentadas. Uma task que falha é `blocked` no razão; ela não é motivo para
    parar as outras.
    """
    vistas: list[str] = []
    for spec in reversed(state.get("specs", [])):
        status = spec.get("status")
        if status == "skipped":
            nome = str(spec.get("spec") or "")
            if nome not in vistas:
                vistas.append(nome)
            continue
        if status in {"verified", "completed"}:
            break
        # Estados intermediários não quebram nem incrementam a contagem.
    return len(vistas)


def _record_attempt(repo: Path, feature: str, attempt: int,
                    build_result: dict[str, Any], commit: str = "-",
                    notes: str = "", *, status: str | None = None) -> None:
    """Registra uma tentativa de build no log e no estado."""
    gen_log.append_log(
        repo, feature, attempt,
        build_result["command"], build_result["exit_code"],
        commit, notes,
    )
    state = gen_log.load_state(repo)
    entry: dict[str, Any] = {
        "spec": feature,
        "attempt": attempt,
        "exit_code": build_result["exit_code"],
        "commit": commit or None,
        "timestamp": _now_iso(),
        "notes": notes,
        "status": status,
    }
    state["specs"].append(entry)
    state["last_commit"] = commit or state.get("last_commit")
    gen_log.save_state(repo, state)


def _last_spec_status(state: dict[str, Any]) -> str | None:
    """Devolve o status da última spec registrada, se houver."""
    specs = state.get("specs") or []
    if not specs:
        return None
    return specs[-1].get("status")


def _embed_failure_report(repo: Path, feature: str,
                          attempts: list[dict[str, Any]]) -> None:
    """Insere uma seção de Compilation Failure Report no GENERATION_LOG.md."""
    log_path = repo / "GENERATION_LOG.md"
    lines: list[str] = [
        "",
        f"## Compilation Failure Report — {feature}",
        "",
        f"**Status:** skipped after {len(attempts)} build attempt(s)",
        "",
        "### Remediation applied",
        "",
    ]
    for idx, attempt in enumerate(attempts, start=1):
        lines.extend([
            f"- Attempt {idx}: exit code {attempt['exit_code']}",
            f"  - Command: `{attempt['command']}`",
            f"  - Hypothesis: {attempt.get('hypothesis', 'No automatic remediation available; build errors persisted.')}",
        ])
    lines.extend([
        "",
        "### Why it is hypothesised not to work",
        "",
        "The automatic remediation did not resolve the build failures. "
        "Common causes include missing dependencies, unresolved symbols, "
        "or generated code that contradicts the project structure. "
        "Human review of the build output and source tree is required.",
        "",
        "### Build output (last attempt)",
        "",
        "```text",
        attempts[-1].get("stderr", "") + attempts[-1].get("stdout", ""),
        "```",
        "",
    ])
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def run_build_with_remediation(
    repo: Path,
    stack: str,
    feature: str,
    *,
    command_override: str | list[str] | None = None,
    remediate: Callable[[int, dict[str, Any]], bool] | None = None,
    timeout: int = 600,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Executa o build inicialmente e aplica até 2 remediações.

    `remediate(attempt, build_result)` deve tentar corrigir o código e
    devolver True se alterou algo (o build será reexecutado), ou False se
    nada pôde ser feito. Quando `remediate` é None, o harness ainda executa
    as 3 tentativas para manter o registro consistente com a política.

    `work_dir` é onde o build roda — o diretório canônico do componente. `repo`
    continua sendo a raiz git (`source-code/`), que é onde o log, o estado e o
    commit vivem. Separar os dois é o que permite commitar frontend e backend no
    mesmo repositório do baseline e ainda assim rodar `dotnet build` no lugar
    certo.

    Retorna dict com: success, attempts (lista), final_exit_code,
    skipped, abort_needed, status.
    """
    alvo_build = Path(work_dir) if work_dir else repo
    attempts: list[dict[str, Any]] = []
    success = False
    skipped = False
    for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
        build_result = build_runner.run_build(
            alvo_build, stack, command_override=command_override, timeout=timeout
        )
        attempts.append(build_result)

        # Falha de AMBIENTE não é remediável por agente: pedir ao coder que
        # conserte `ng: command not found` gasta inferência e não muda nada.
        # Medido: 6 despachos e 251s em `cadastro-funcionario-03`.
        if build_result.get("toolchain_missing"):
            _record_attempt(
                repo, feature, attempt, build_result,
                notes=(f"toolchain ausente: {build_result['toolchain_missing']} — "
                       f"remediacao nao aplicavel"),
                status="skipped",
            )
            break

        if build_result["exit_code"] == 0:
            success = True
            _record_attempt(
                repo, feature, attempt, build_result,
                notes="build passed",
                status="verified",
            )
            break
        # Build falhou — tentar remediação, exceto na última tentativa.
        if attempt < MAX_BUILD_ATTEMPTS:
            altered = False
            if remediate:
                altered = remediate(attempt, build_result)
            _record_attempt(
                repo, feature, attempt, build_result,
                notes=("remediation triggered" if altered
                       else "remediation did not change files"),
                status="remediating",
            )
            if remediate and not altered:
                # Sem alteração, não há sentido em reexecutar.
                break
        else:
            _record_attempt(
                repo, feature, attempt, build_result,
                notes="final attempt failed; spec will be skipped",
                status="skipped",
            )

    final_exit_code = attempts[-1]["exit_code"] if attempts else 2
    if not success:
        skipped = True
        _embed_failure_report(repo, feature, attempts)

    state = gen_log.load_state(repo)
    consecutive = _consecutive_skips(state)
    abort_needed = consecutive >= MAX_CONSECUTIVE_SKIPS

    toolchain = next((a.get("toolchain_missing") for a in reversed(attempts)
                      if a.get("toolchain_missing")), "")

    return {
        "success": success,
        "skipped": skipped,
        "attempts": attempts,
        "final_exit_code": final_exit_code,
        "abort_needed": abort_needed,
        "consecutive_skips": consecutive,
        "toolchain_missing": toolchain,
        "status": "verified" if success else "skipped",
    }


def snapshot_before(repo: Path, feature: str) -> Path:
    """Gera snapshot da árvore antes de um spec e devolve o path do markdown."""
    output = repo / ".f4s" / "snapshots"
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{feature}-before.md"
    tree_snapshot.snapshot(repo, output_md=path)
    return path


def snapshot_after(repo: Path, feature: str) -> Path:
    """Gera snapshot da árvore depois de um spec e devolve o path do markdown."""
    output = repo / ".f4s" / "snapshots"
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{feature}-after.md"
    tree_snapshot.snapshot(repo, output_md=path)
    return path


def run_task(
    project: str,
    stack: str,
    feature: str,
    *,
    command_override: str | list[str] | None = None,
    remediate: Callable[[int, dict[str, Any]], bool] | None = None,
    timeout: int = 600,
    repo_root: Path | None = None,
    component_type: str | None = None,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """
    Executa o ciclo completo de uma task F4: repo → snapshot → build → commit.

    A geração de código em si deve ser feita pelo caller ANTES de chamar
    `run_task`; esta função assume que o source-code já foi modificado para
    a `feature` e apenas orquestra verificação, remediação e commit.

    Retorna dict com success, status, commit_hash, abort_needed, attempts.
    """
    componente = component_type or scaffold_paths.component_type_for_stack(stack)
    repo = ensure_repo(project, stack, repo_root, component_type=componente)
    work_dir = component_source_dir(project, componente, repo_root)
    snapshot_before(repo, feature)

    result = run_build_with_remediation(
        repo, stack, feature,
        command_override=command_override,
        remediate=remediate,
        timeout=timeout,
        work_dir=work_dir,
    )

    commit_hash = ""
    if result["success"]:
        snapshot_after(repo, feature)
        git.git_add_all(repo)
        commit_hash = git.git_commit(
            repo, commit_message or f"feat({componente}/{stack}): implement {feature}")
        _record_attempt(
            repo, feature, len(result["attempts"]),
            {"command": result["attempts"][-1]["command"],
             "exit_code": result["attempts"][-1]["exit_code"]},
            commit=commit_hash,
            notes="build verified and committed",
            status="verified",
        )
    else:
        _record_attempt(
            repo, feature, len(result["attempts"]),
            {"command": result["attempts"][-1]["command"],
             "exit_code": result["attempts"][-1]["exit_code"]},
            commit="-",
            notes="spec skipped — see Compilation Failure Report",
            status="skipped",
        )

    return {
        "success": result["success"],
        "status": result["status"],
        "commit_hash": commit_hash,
        "abort_needed": result["abort_needed"],
        "attempts": result["attempts"],
        "repo": str(repo),
        "feature": feature,
        "stack": stack,
    }


def reset_consecutive_skips_counter(repo: Path) -> None:
    """Marca uma task bem-sucedida no estado para quebrar sequência de skips."""
    state = gen_log.load_state(repo)
    state["last_success_at"] = _now_iso()
    gen_log.save_state(repo, state)
