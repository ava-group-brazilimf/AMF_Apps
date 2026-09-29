#!/usr/bin/env python3
"""Gate deterministico da solution .NET: estrutura, restore, build e test."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import proc_stream  # noqa: E402
import short_path_root as spr  # noqa: E402
from verify_cpm_consistency import verify_cpm_consistency
from verify_nuget_packages import verify_nuget_packages
from verify_scaffold import verify_scaffold


EXIT_PASS = 0
EXIT_PREREQ = 10
EXIT_STRUCTURE = 20
EXIT_RESTORE = 30
EXIT_BUILD = 40
EXIT_TEST = 50
EXIT_USAGE = 60

#: Teto por COMANDO do verifier (`restore`, `build`, `test`), em segundos.
#: Fica deliberadamente abaixo do teto do passo F4S (ver
#: `pipeline_plan.DEFAULT_TOOL_TIMEOUT_S`): assim quem estoura primeiro é o
#: comando, que sabe dizer QUAL fase travou, e não o pai, que só sabe dizer que
#: o tempo acabou. Os 900s anteriores eram o teto mais apertado de toda a
#: cadeia e o menos visível — um `dotnet build` de 79 projetos passa deles.
#: Nao deriva de bounded context nem de contagem de projeto: e limite de
#: seguranca.
DEFAULT_COMMAND_TIMEOUT_S = 1800


class VerifyError(Exception):
    def __init__(self, code: int, phase: str, message: str) -> None:
        super().__init__(message)
        self.code, self.phase, self.message = code, phase, message


class Logger:
    def __init__(self, path: Path, quiet: bool) -> None:
        self.path, self.quiet = path, quiet
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def write(self, level: str, message: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{stamp}] [{level}] {message}"
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        if not self.quiet:
            print(line, file=sys.stderr)


def _tail(output: str, lines: int = 20) -> str:
    return "\n".join(line for line in output.splitlines()[-lines:] if line.strip())


def _run(log: Logger, phase: str, command: list[str], root: Path,
         timeout: int, stream: bool = True) -> None:
    log.write("INFO", f"{phase}: $ {' '.join(command)}")
    print(f"  [verify:{phase}] $ {' '.join(command)}", file=sys.stderr, flush=True)
    try:
        # `restore`, `build` e `test` sao as tres etapas longas da F4S. Capturar
        # em silencio e despejar no fim deixava o operador sem saber se o build
        # progredia; o log completo continua indo para o arquivo, intacto.
        result = proc_stream.run(command, cwd=root, timeout_s=timeout,
                                 prefix=f"  [{phase}] ",
                                 echo_stdout=stream, echo_stderr=stream,
                                 stream=sys.stderr)
    except FileNotFoundError as exc:
        raise VerifyError(EXIT_PREREQ, phase, f"comando nao encontrado: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VerifyError(EXIT_PREREQ, phase, f"timeout de {timeout}s em {' '.join(command)}") from exc
    if result.stdout or result.stderr:
        with log.path.open("a", encoding="utf-8") as stream:
            for output in (result.stdout, result.stderr):
                if output:
                    stream.write(output if output.endswith("\n") else output + "\n")
    if result.returncode:
        codes = {"restore": EXIT_RESTORE, "build": EXIT_BUILD, "test": EXIT_TEST}
        raise VerifyError(codes[phase], phase,
                          f"{' '.join(command)} falhou (exit {result.returncode}):\n"
                          f"{_tail(result.stderr or result.stdout)}")


def _solution(root: Path) -> Path:
    solutions = sorted(root.glob("*.sln"))
    if len(solutions) != 1:
        found = ", ".join(path.name for path in solutions) or "nenhuma"
        raise VerifyError(EXIT_PREREQ, "prereq",
                          f"esperada exatamente uma solution .sln em {root}; encontrada: {found}")
    return solutions[0]


def phase_prereq(log: Logger, root: Path) -> Path:
    if shutil.which("dotnet") is None:
        raise VerifyError(EXIT_PREREQ, "prereq", "dotnet nao encontrado no PATH")
    solution = _solution(root)
    log.write("PASS", f"prereq: dotnet disponivel; solution {solution.name}")
    return solution


def phase_structure(log: Logger, root: Path) -> None:
    scaffold = verify_scaffold("dotnet", str(root))
    if scaffold["status"] != "PASS":
        missing = ", ".join(item["path"] for item in scaffold["missing"] if item["blocking"])
        raise VerifyError(EXIT_STRUCTURE, "structure", f"manifest .NET reprovado: {missing}")
    cpm = verify_cpm_consistency(root)
    if cpm["status"] != "PASS":
        raise VerifyError(EXIT_STRUCTURE, "structure", f"CPM invalido: {cpm}")
    nuget = verify_nuget_packages(str(root))
    if nuget["status"] != "PASS":
        raise VerifyError(EXIT_STRUCTURE, "structure", f"PackageReference duplicado: {nuget}")
    log.write("PASS", "structure: manifest, CPM e PackageReference validos")


def verify(root: Path, *, timeout: int = DEFAULT_COMMAND_TIMEOUT_S,
           quiet: bool = False,
           stream: bool = True) -> dict[str, Any]:
    started = time.monotonic()
    # `.resolve()` DESFAZ o mapeamento `subst`: `Path("Z:/").resolve()` devolve o
    # caminho longo de verdade, e o contorno de MAX_PATH some sem aviso. Caminho
    # já absoluto passa intacto; só o relativo é resolvido.
    root = root if root.is_absolute() else root.resolve()
    log = Logger(root / ".artifacts" / "verify-dotnet.log", quiet)
    phases: list[dict[str, str]] = []
    result: dict[str, Any] = {"status": "PASS", "root": str(root), "solution": None,
                              "phases": phases, "log_path": str(log.path), "error": None}
    try:
        solution = phase_prereq(log, root)
        result["solution"] = solution.name
        phases.append({"name": "prereq", "status": "PASS", "detail": solution.name})
        phase_structure(log, root)
        phases.append({"name": "structure", "status": "PASS", "detail": "manifest + CPM"})
        _run(log, "restore", ["dotnet", "restore", str(solution)], root, timeout, stream)
        phases.append({"name": "restore", "status": "PASS", "detail": solution.name})
        _run(log, "build", ["dotnet", "build", str(solution), "--no-restore",
                              "--configuration", "Release"], root, timeout, stream)
        phases.append({"name": "build", "status": "PASS", "detail": "Release"})
        _run(log, "test", ["dotnet", "test", str(solution), "--no-build", "--no-restore",
                             "--configuration", "Release"], root, timeout, stream)
        phases.append({"name": "test", "status": "PASS", "detail": "Release"})
    except VerifyError as exc:
        phases.append({"name": exc.phase, "status": "FAIL", "detail": exc.message})
        result.update(status="FAIL", error=f"{exc.phase}: {exc.message}", exit_code=exc.code)
        log.write("FAIL", result["error"])
    result["elapsed_seconds"] = round(time.monotonic() - started, 1)
    if result["status"] == "PASS":
        log.write("PASS", f"veredito: structure, restore, build e test ({result['elapsed_seconds']}s)")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida uma solution .NET gerada pela F4S")
    parser.add_argument("--root", required=True)
    parser.add_argument("--timeout", type=int, default=DEFAULT_COMMAND_TIMEOUT_S)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        payload = {"status": "ERROR", "error": f"diretorio inexistente: {root}", "phases": []}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload["error"],
              file=sys.stdout if args.json else sys.stderr)
        return EXIT_USAGE
    # Mesmo contorno de MAX_PATH do generator, pelo mesmo motivo: sem ele o
    # verifier tropeça antes de compilar, com `FileNotFoundError` num .csproj
    # que existe — a API clássica do Windows não enxerga acima de 260 chars.
    # No Windows sem `LongPathsEnabled` sempre tentamos a raiz curta: o custo é
    # um `subst`, e enumerar os caminhos para decidir esbarraria na mesma
    # cegueira que estamos contornando.
    precisa = not spr.long_paths_enabled()
    with spr.short_root(root.resolve(), needed=precisa) as (trabalho, letra):
        # `quiet` silencia o Logger para nao poluir o stdout do `--json`; o log
        # do `dotnet` sai pelo stderr e por isso NAO precisa ser silenciado
        # junto — era esse acoplamento que deixava a F4S muda em modo JSON.
        result = verify(trabalho, timeout=args.timeout,
                        quiet=args.quiet or args.json, stream=not args.quiet)
        if letra is not None:
            # O relatório nomeia o lugar de verdade: `Z:\...` descreve uma
            # unidade que já não existe quando alguém for ler o JSON.
            real = root.resolve()
            result["root"] = str(real)
            result["log_path"] = str(spr.to_real(Path(result["log_path"]), trabalho, real))
            result["path_workaround"] = (
                f"verificado atraves da raiz curta {letra}: (subst) — caminhos "
                f"acima de MAX_PATH neste Windows. Correcao definitiva: "
                f"LongPathsEnabled=1.")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for phase in result["phases"]:
            print(f"  {phase['status']:<7} {phase['name']:<10} {phase['detail']}")
        print(f"[verify-dotnet] {result['status']} - {result['log_path']}")
    return EXIT_PASS if result["status"] == "PASS" else int(result.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
