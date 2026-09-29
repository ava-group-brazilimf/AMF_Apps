#!/usr/bin/env python3
"""
f4s_build_runner.py — Executa o build de verificação por stack na F4S.

Mapeia `target_stack` para o comando padrão de build e permite override via
configuração do projeto. Devolve exit_code, stdout, stderr e o comando executado.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Verificadores determinísticos que SUBSTITUEM o comando de build da stack.
#:
#: Os harnesses sao a autoridade de build das stacks que possuem um. Angular cobre
#: install -> build -> boot -> health; .NET cobre structure -> restore -> build -> test.
#: O caminho evita que a F4S marque uma feature como compilada sem validar o projeto.
#:
#: Spec 042: para Angular o build não é `npm run build`, e sim o harness completo
#: (install -> build -> boot -> health). Ele é a autoridade sobre "compila e roda":
#:  - escolhe `npm install` ou `npm ci` conforme a presença do lockfile — `npm ci`
#:    incondicional falhava num scaffold recém-gerado, que ainda não tem lockfile;
#:  - a fase health captura defeitos que passam no `ng build` e só quebram no
#:    browser, como a ausência de `polyfills: ["zone.js"]` (NG0908).
STACK_VERIFIERS: dict[str, Path] = {
    "angular": REPO_ROOT / "src" / "shared" / "utils" / "verify_angular_app.py",
    "dotnet": REPO_ROOT / "src" / "shared" / "utils" / "verify_dotnet_solution.py",
}


#: Aliases de linguagem convivem com os de framework porque o `target_stack` do
#: SpecKit usa as duas grafias (`spring-boot` e `java`, `fastapi` e `python`,
#: `gin` e `go`, `nestjs` e `node`) — e `f4_routing.STACK_AGENTS` aceita ambas.
#: Uma stack roteável sem comando de build aqui viraria erro de rota na F4.
DEFAULT_COMMANDS: dict[str, list[str]] = {
    "fastapi": ["python", "-m", "pytest"],
    "python": ["python", "-m", "pytest"],
    "spring-boot": ["mvn", "-B", "verify"],
    "java": ["mvn", "-B", "verify"],
    "gin": ["go", "build", "./..."],
    "go": ["go", "build", "./..."],
    "nestjs": ["npm", "run", "build"],
    "node": ["npm", "run", "build"],
    "react": ["npm", "install", "&&", "npm", "run", "build"],
    "vue": ["npm", "install", "&&", "npm", "run", "build"],
    "blazor": ["dotnet", "build"],
}


class BuildRunnerError(Exception):
    """Erro de configuração do build runner."""


def resolve_command(stack: str, override: str | None = None) -> list[str]:
    """Resolve o comando de build da stack.

    **Precedência: o verificador da stack vence o override da task.** Isto é o
    que o docstring do módulo sempre disse ("os harnesses são a autoridade de
    build das stacks que possuem um") e o que o código não fazia — o `override`
    era testado primeiro e desligava o verificador.

    O custo real disso está medido em `cadastro-funcionario-03`: o
    `verify_command` da task era `ng build --configuration=production
    --project=cadastro-funcionario-app`, escrito em prosa pelo SpecKit.
    `ng` não existe no PATH (é `node_modules/.bin/ng.cmd`, e o `npm install`
    ainda não tinha rodado) → `FileNotFoundError` → exit 127 em três tentativas,
    seis remediações de LLM e 251s gastos num erro que nenhum agente consegue
    corrigir escrevendo código. O `verify_angular_app.py`, que faz
    install → build → boot → health, estava desligado justamente pela task.

    Override continua valendo para stacks **sem** verificador determinístico.
    """
    stack = str(stack or "").lower()

    verifier = STACK_VERIFIERS.get(stack)
    if verifier is not None:
        if not verifier.is_file():
            raise BuildRunnerError(
                f"verificador da stack '{stack}' ausente: {verifier}"
            )
        # `--root .` porque run_build executa com cwd=repo_root.
        return [sys.executable, str(verifier), "--root", ".", "--json"]

    if override:
        # Suporta tanto string quanto lista YAML já carregada.
        if isinstance(override, list):
            return [str(x) for x in override]
        return shlex.split(str(override))

    if stack not in DEFAULT_COMMANDS:
        raise BuildRunnerError(f"stack '{stack}' sem comando de build padrão")
    return list(DEFAULT_COMMANDS[stack])


def overrides_stack_verifier(stack: str) -> bool:
    """True quando a stack tem verificador determinístico próprio."""
    return str(stack or "").lower() in STACK_VERIFIERS


def executable_missing(cmd: list[str]) -> str:
    """Nome do executável ausente no PATH, ou `""` quando tudo resolve.

    Um comando que não existe é falha de **ambiente**, não de código: distinguir
    isso antes de rodar é o que impede o pipeline de pedir a um agente que
    conserte a ausência do `ng`.
    """
    for parte in _split_shell_and(cmd):
        if not parte:
            continue
        alvo = str(parte[0])
        if Path(alvo).is_file():
            continue
        if shutil.which(alvo) is None:
            return alvo
    return ""


def _split_shell_and(cmd: list[str]) -> list[list[str]]:
    """Separa uma lista de args quando há '&&' em modo shell-like."""
    parts: list[list[str]] = []
    current: list[str] = []
    for token in cmd:
        if token == "&&":
            parts.append(current)
            current = []
        else:
            current.append(token)
    if current:
        parts.append(current)
    return parts


def run_build(repo_root: Path, stack: str,
              command_override: str | list[str] | None = None,
              timeout: int = 600) -> dict[str, Any]:
    """
    Executa o build no repo_root.

    Retorna dict: command, exit_code, stdout, stderr, timed_out.
    """
    if not repo_root.is_dir():
        raise BuildRunnerError(f"repo_root não existe: {repo_root}")

    cmd = resolve_command(stack, command_override)
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    exit_code = 0
    timed_out = False

    # Executável ausente é falha de AMBIENTE. Devolver isso classificado — em vez
    # de deixar estourar como um exit code qualquer — é o que permite ao harness
    # não gastar remediação de LLM com `ng: command not found`.
    faltando = executable_missing(cmd)
    if faltando:
        return {
            "command": " ".join(str(t) for t in cmd),
            "exit_code": 127,
            "stdout": "",
            "stderr": (f"executavel ausente no PATH: {faltando!r}. "
                       f"Isto e falha de ambiente (toolchain nao instalada ou "
                       f"binario local nao resolvido), nao de codigo gerado."),
            "timed_out": False,
            "toolchain_missing": faltando,
        }

    # Para stacks node, frequentemente precisamos de `npm ci && npm run build`.
    # Em Windows é mais seguro rodar via shell quando há '&&'.
    parts = _split_shell_and(cmd)
    use_shell = len(parts) > 1

    try:
        if use_shell:
            shell_cmd = " ".join(shlex.quote(str(t)) for t in cmd)
            result = subprocess.run(
                shell_cmd,
                cwd=str(repo_root),
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            stdout_parts.append(result.stdout)
            stderr_parts.append(result.stderr)
            exit_code = result.returncode
        else:
            for part in parts:
                result = subprocess.run(
                    part,
                    cwd=str(repo_root),
                    shell=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    check=False,
                )
                stdout_parts.append(result.stdout)
                stderr_parts.append(result.stderr)
                exit_code = result.returncode
                if exit_code != 0:
                    break
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = -1
    except FileNotFoundError as exc:
        stderr_parts.append(str(exc))
        exit_code = 127

    resultado = {
        "command": " ".join(str(c) for c in cmd),
        "exit_code": exit_code,
        "stdout": "\n".join(stdout_parts),
        "stderr": "\n".join(stderr_parts),
        "timed_out": timed_out,
    }
    if exit_code == 127:
        # `which` passou mas o exec falhou mesmo assim (shim quebrado, .cmd sem
        # interpretador). Continua sendo ambiente, não código.
        resultado["toolchain_missing"] = str(cmd[0]) if cmd else "?"
    return resultado
