#!/usr/bin/env python3
"""
f4s_git_helper.py — Operações git determinísticas para a fase F4S.

Toda a história de geração de código fica no repo
`projects/{project}/outputs/tobe/source-code/{stack}/`. Este módulo NÃO escreve
código — só inicializa o repo, adiciona arquivos, commita e consulta status.
"""
from __future__ import annotations

import subprocess
import unicodedata
from pathlib import Path


class GitHelperError(Exception):
    """Erro de configuração ou execução do git."""


def _run(repo_root: Path, args: list[str], check: bool = True,
         timeout: int = 60, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Executa git em repo_root com codificação UTF-8."""
    if not repo_root.is_dir():
        raise GitHelperError(f"diretório não existe: {repo_root}")
    try:
        return subprocess.run(
            # `core.longpaths` por invocação, nunca no config do usuário: o
            # scaffold .NET gera caminhos acima de MAX_PATH (o nome do projeto
            # entra duas vezes — pasta + arquivo) e sem isto o `git add --all`
            # do baseline morre com "Filename too long", depois de generator e
            # verifier já terem passado. `-c` mantém a mudança no escopo desta
            # chamada; mexer no config global do operador seria efeito colateral
            # de uma tool de pipeline.
            ["git", "-c", "core.longpaths=true", *args],
            cwd=str(repo_root),
            capture_output=capture,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        raise GitHelperError(
            f"git falhou em {repo_root}: {' '.join(args)}\n"
            f"stdout: {exc.stdout.strip()}\nstderr: {exc.stderr.strip()}"
        ) from exc
    except FileNotFoundError as exc:
        raise GitHelperError("git não encontrado no PATH") from exc


def git_init(repo_root: Path, default_branch: str = "main") -> None:
    """Inicializa repo em repo_root, forçando o branch padrão."""
    repo_root.mkdir(parents=True, exist_ok=True)
    if (repo_root / ".git").is_dir():
        return
    _run(repo_root, ["init", "--quiet", f"--initial-branch={default_branch}"])
    _run(repo_root, ["config", "user.email", "ava-fabric@example.com"])
    _run(repo_root, ["config", "user.name", "AVA Fabric F4S"])


def git_add_all(repo_root: Path) -> None:
    """Stage de todos os arquivos do repo."""
    _run(repo_root, ["add", "--all"])


def git_commit(repo_root: Path, message: str, *, stage_all: bool = True) -> str:
    """Commita staged changes e devolve o hash curto.

    `stage_all=False` para o commit por task da F4, onde o stage já foi feito
    com pathspec restrito ao diretório canônico do componente: um `add --all`
    ali arrastaria para o commit da task qualquer coisa deixada por outra.
    """
    if stage_all:
        git_add_all(repo_root)
    if git_status_is_clean(repo_root, cached=True):
        return ""
    _run(repo_root, ["commit", "--quiet", "-m", message])
    result = _run(repo_root, ["rev-parse", "--short", "HEAD"])
    return result.stdout.strip()


#: Comprimento máximo do nome de branch — nomes de task + slug de título passam
#: fácil de 200 chars, e o Windows tem limite de caminho para o ref em disco.
BRANCH_NAME_MAX = 80


def sanitize_branch_name(*partes: str) -> str:
    """Nome de branch determinístico e válido a partir de id + título da task.

    Git recusa `~ ^ : ? * [ \\`, espaço, `..`, `@{`, ponto final e barra dupla.
    Um nome derivado do id da task precisa ser previsível: a mesma task gera
    sempre o mesmo branch, o que torna a retomada idempotente.
    """
    import re  # noqa: PLC0415

    bruto = "-".join(str(p or "").strip() for p in partes if str(p or "").strip())
    limpo = unicodedata.normalize("NFKD", bruto).encode("ascii", "ignore").decode()
    # `/` sai do slug: um título como "criar infra/terraform/main.tf" viraria
    # `task/...-infra/terraform/main.tf`, um ref aninhado que colide com
    # `task/...-infra` e é impossível de criar depois dele.
    limpo = re.sub(r"[^A-Za-z0-9._-]+", "-", limpo).strip("-.")
    limpo = re.sub(r"-{2,}", "-", limpo)
    limpo = re.sub(r"\.{2,}", ".", limpo).replace("@{", "-")
    return (limpo[:BRANCH_NAME_MAX].rstrip("-.") or "task").lower()


def task_branch_name(task_id: str, title: str = "") -> str:
    """`task/<task-id>-<slug-do-titulo>`."""
    return "task/" + sanitize_branch_name(task_id, title)


def current_branch(repo_root: Path) -> str:
    resultado = _run(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"], check=False)
    return resultado.stdout.strip() or "HEAD"


def branch_exists(repo_root: Path, branch: str) -> bool:
    resultado = _run(repo_root, ["rev-parse", "--verify", "--quiet", branch],
                     check=False)
    return resultado.returncode == 0


def is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    """`ancestor` está contido em `descendant`? Base do teste de branch obsoleto.

    Um branch de task criado num run anterior tem como base um `main` antigo;
    escrever nele agora e integrar depois produz conflito com tudo que entrou no
    `main` desde então.
    """
    if not ancestor or not descendant:
        return False
    resultado = _run(repo_root, ["merge-base", "--is-ancestor", ancestor, descendant],
                     check=False)
    return resultado.returncode == 0


def has_commits(repo_root: Path) -> bool:
    return _run(repo_root, ["rev-parse", "--verify", "--quiet", "HEAD"],
                check=False).returncode == 0


def checkout_branch(repo_root: Path, branch: str, *, create: bool = False,
                    base: str | None = None) -> str:
    """Troca (ou cria) o branch. Devolve o branch efetivo.

    `create=True` num branch que já existe apenas faz checkout — retomada de
    uma task interrompida volta para o branch dela, não cria um segundo.
    """
    if create and not branch_exists(repo_root, branch):
        args = ["checkout", "-b", branch]
        if base:
            args.append(base)
        _run(repo_root, args)
    else:
        _run(repo_root, ["checkout", branch])
    return current_branch(repo_root)


def merge_branch(repo_root: Path, branch: str, *, into: str,
                 message: str | None = None) -> dict[str, str]:
    """Integra `branch` em `into` com `--no-ff`. Nunca faz push, nunca força.

    Conflito não é resolvido às escondidas: o merge é abortado, o branch da task
    é preservado e o resultado volta como `conflict` para virar `review`.
    """
    _run(repo_root, ["checkout", into])
    resultado = _run(
        repo_root,
        ["merge", "--no-ff", branch, "-m", message or f"merge {branch} into {into}"],
        check=False)
    if resultado.returncode != 0:
        _run(repo_root, ["merge", "--abort"], check=False)
        return {"status": "conflict", "branch": branch, "into": into,
                "detail": (resultado.stdout + resultado.stderr).strip()[:2000]}
    commit = _run(repo_root, ["rev-parse", "--short", "HEAD"], check=False)
    return {"status": "merged", "branch": branch, "into": into,
            "commit": commit.stdout.strip()}


def git_changed_files(repo_root: Path, pathspec: str | None = None) -> list[str]:
    """Arquivos realmente alterados na árvore, por `git status --porcelain`.

    É a fonte de `files_written` da F4. O que o agente *declara* ter escrito é
    diagnóstico; o que o disco mostra é evidência — e o razão só guarda
    evidência. `pathspec` restringe ao diretório canônico do componente.
    """
    args = ["status", "--porcelain", "--untracked-files=all"]
    if pathspec:
        args += ["--", pathspec]
    resultado = _run(repo_root, args, check=False)
    arquivos: list[str] = []
    for linha in resultado.stdout.splitlines():
        if len(linha) < 4:
            continue
        caminho = linha[3:].strip().strip('"')
        # Rename vem como "origem -> destino"; o que interessa é o destino.
        if " -> " in caminho:
            caminho = caminho.split(" -> ", 1)[1]
        if caminho:
            arquivos.append(caminho)
    return arquivos


def git_branch_changed_files(repo_root: Path, base: str) -> list[str]:
    """Tudo que o branch atual mudou em relação a `base`, já commitado.

    A partir da 2ª tentativa de uma task, o que ela escreveu na 1ª já está
    commitado no branch dela e some do `git status` — e o alvo declarado
    aparecia como `expected_but_missing`. O diff contra a base é o que dá a
    visão completa do que a TASK produziu, não só do que está pendente.
    """
    if not base:
        return []
    resultado = _run(repo_root, ["diff", "--name-only", f"{base}...HEAD"],
                     check=False)
    if resultado.returncode != 0:
        return []
    return [linha.strip() for linha in resultado.stdout.splitlines() if linha.strip()]


def git_add_paths(repo_root: Path, pathspecs: list[str]) -> None:
    """Stage restrito. Sem pathspec não faz nada — nunca cai em `add --all`."""
    caminhos = [p for p in pathspecs if p]
    if not caminhos:
        return
    _run(repo_root, ["add", "--", *caminhos])


def git_status_is_clean(repo_root: Path, cached: bool = False) -> bool:
    """True se não há alterações pendentes (cached=True considera staged)."""
    args = ["diff", "--quiet"]
    if cached:
        args = ["diff", "--cached", "--quiet"]
    result = _run(repo_root, args, check=False)
    return result.returncode == 0


def git_get_log(repo_root: Path, max_count: int = 20,
                format_: str = "%h %s") -> list[str]:
    """Devolve lista de linhas do git log --oneline."""
    result = _run(
        repo_root,
        ["log", f"--max-count={max_count}", f"--pretty=format:{format_}"],
    )
    return [line for line in result.stdout.splitlines() if line.strip()]
