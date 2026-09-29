#!/usr/bin/env python3
"""Verificador real do scaffold .NET — restore e build, não presença de arquivo.

`verify_scaffold.py --manifest dotnet` confere que os arquivos existem. Isso
nunca provou que a solution compila: uma `<ProjectReference>` apontando para um
csproj inexistente passa no manifesto e explode no primeiro build, já com o
commit de baseline feito e os agentes coder liberados.

Este verificador roda `dotnet restore` e `dotnet build` de verdade e separa
warnings de errors. Exit != 0 quando o build falha — é o que impede o commit.

Uso:
    python src/shared/utils/verify_dotnet_app.py --root <.../source-code/backend> --json
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_TIMEOUT = 900

#: Arquivos sem os quais nem faz sentido chamar o SDK.
REQUIRED_FILES: tuple[str, ...] = ("Directory.Packages.props",)
REQUIRED_DIRS: tuple[str, ...] = ("src",)

#: `MSB1234: mensagem` / `CS0246: ...` — o código é o que interessa para
#: classificar; a linha inteira vira evidência.
_DIAG = re.compile(
    r"^(?P<file>.*?)(?:\((?P<line>\d+),(?P<col>\d+)\))?\s*:\s*"
    r"(?P<sev>error|warning)\s+(?P<code>[A-Z]+\d+)\s*:\s*(?P<msg>.*)$",
    re.IGNORECASE,
)

#: Nunca ecoar segredo em log. Cobre o que aparece em appsettings/env de build.
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(password|pwd)\s*=\s*[^;\"'\s]+"), r"\1=***"),
    (re.compile(r"(?i)(accountkey|sharedaccesskey)\s*=\s*[^;\"'\s]+"), r"\1=***"),
    (re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*[^;,\"'\s]+"), r"\1=***"),
    (re.compile(r"(?i)(bearer)\s+[A-Za-z0-9._\-]{12,}"), r"\1 ***"),
)


def sanitize(text: str) -> str:
    """Remove credenciais antes de qualquer coisa ir para log ou task-state."""
    for padrao, troca in _SECRET_PATTERNS:
        text = padrao.sub(troca, text)
    return text


def _tail(text: str, linhas: int = 60) -> str:
    partes = sanitize(text).splitlines()
    return "\n".join(partes[-linhas:])


def parse_diagnostics(saida: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separa errors de warnings, sem duplicar a mesma ocorrência."""
    erros: dict[str, dict[str, Any]] = {}
    avisos: dict[str, dict[str, Any]] = {}
    for linha in saida.splitlines():
        match = _DIAG.match(linha.strip())
        if not match:
            continue
        registro = {
            "code": match.group("code").upper(),
            "message": sanitize(match.group("msg").strip()),
            "file": sanitize((match.group("file") or "").strip()) or None,
            "line": int(match.group("line")) if match.group("line") else None,
        }
        chave = f"{registro['code']}|{registro['file']}|{registro['line']}|{registro['message']}"
        destino = erros if match.group("sev").lower() == "error" else avisos
        destino.setdefault(chave, registro)
    return list(erros.values()), list(avisos.values())


def _dotnet_disponivel() -> str | None:
    return shutil.which("dotnet")


def _run(comando: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    inicio = time.monotonic()
    try:
        proc = subprocess.run(comando, cwd=str(cwd), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, check=False)
        saida, erro, codigo, expirou = proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        saida = exc.stdout if isinstance(exc.stdout, str) else ""
        erro = exc.stderr if isinstance(exc.stderr, str) else ""
        codigo, expirou = 124, True
    duracao = round(time.monotonic() - inicio, 2)
    combinado = f"{saida}\n{erro}"
    erros, avisos = parse_diagnostics(combinado)
    return {
        "command": comando,
        "cwd": cwd.as_posix(),
        "exit_code": codigo,
        "duration_s": duracao,
        "timed_out": expirou,
        "errors": erros,
        "warnings": avisos,
        "stdout_tail": _tail(saida),
        "stderr_tail": _tail(erro),
    }


def find_solution(root: Path) -> Path | None:
    """Solution na raiz do backend. Mais de uma é ambiguidade, não escolha.

    Duas `.sln` no mesmo diretório fazem `dotnet build` sem argumento falhar com
    MSB1011 — e é o sintoma clássico de scaffold novo convivendo com legado.
    """
    solutions = sorted(root.glob("*.sln")) + sorted(root.glob("*.slnx"))
    if len(solutions) == 1:
        return solutions[0]
    if len(solutions) > 1:
        raise RuntimeError(
            "mais de uma solution em " + root.as_posix() + ": "
            + ", ".join(s.name for s in solutions)
            + ". Resolva o conflito (provavelmente scaffold legado) antes de compilar.")
    projetos = sorted(root.rglob("*.csproj"))
    return projetos[0] if len(projetos) == 1 else None


def verify(root: Path, *, timeout: int = DEFAULT_TIMEOUT,
           skip_build: bool = False,
           configuration: str = "Release") -> dict[str, Any]:
    """Valida estrutura, restaura e compila. Resultado estruturado sempre."""
    resultado: dict[str, Any] = {
        "success": False,
        "status": "FAIL",
        "stack": "dotnet",
        "component_type": "backend",
        "phase": "verification",
        "output_path": root.as_posix(),
        "solution": None,
        "command": [],
        "exit_code": 1,
        "restore_status": None,
        "build_status": None,
        "errors": [],
        "warnings": [],
        "artifacts": [],
        "evidence": [],
        "attempt": 1,
        "error": None,
    }

    if not root.is_dir():
        resultado["error"] = f"diretório do backend não existe: {root}"
        resultado["errors"] = [{"code": "SCAFFOLD000", "message": resultado["error"]}]
        return resultado

    faltando = [item for item in REQUIRED_FILES if not (root / item).is_file()]
    faltando += [item for item in REQUIRED_DIRS if not (root / item).is_dir()]
    if faltando:
        resultado["error"] = f"estrutura incompleta: {', '.join(faltando)}"
        resultado["errors"] = [{"code": "SCAFFOLD001", "message": resultado["error"]}]
        return resultado

    try:
        alvo = find_solution(root)
    except RuntimeError as exc:
        resultado["error"] = str(exc)
        resultado["errors"] = [{"code": "SCAFFOLD002", "message": str(exc)}]
        return resultado
    if alvo is None:
        resultado["error"] = (
            "nenhuma solution (.sln) nem projeto único (.csproj) encontrado em "
            + root.as_posix())
        resultado["errors"] = [{"code": "SCAFFOLD003", "message": resultado["error"]}]
        return resultado
    resultado["solution"] = alvo.relative_to(root).as_posix()
    resultado["artifacts"] = [alvo.as_posix()]

    if _dotnet_disponivel() is None:
        # Toolchain ausente é limitação de ambiente, não aprovação: o status
        # continua FAIL e nenhum commit de baseline acontece.
        resultado["error"] = (
            "dotnet SDK não encontrado no PATH — impossível provar que o "
            "scaffold compila.")
        resultado["errors"] = [{"code": "TOOLCHAIN001", "message": resultado["error"]}]
        resultado["restore_status"] = "toolchain_unavailable"
        resultado["build_status"] = "toolchain_unavailable"
        return resultado

    if skip_build:
        resultado.update({"success": True, "status": "PASS", "exit_code": 0,
                          "restore_status": "skipped", "build_status": "skipped"})
        return resultado

    restore = _run(["dotnet", "restore", alvo.name], root, timeout)
    resultado["evidence"].append({"step": "restore", **restore})
    resultado["command"] = restore["command"]
    if restore["exit_code"] != 0:
        resultado["restore_status"] = "failed"
        resultado["exit_code"] = restore["exit_code"]
        resultado["errors"] = restore["errors"] or [{
            "code": "RESTORE001",
            "message": restore["stderr_tail"] or "dotnet restore falhou sem diagnóstico",
        }]
        resultado["warnings"] = restore["warnings"]
        resultado["error"] = f"dotnet restore falhou (exit {restore['exit_code']})"
        return resultado
    resultado["restore_status"] = "succeeded"
    resultado["warnings"].extend(restore["warnings"])

    build = _run(
        ["dotnet", "build", alvo.name, "--configuration", configuration, "--no-restore"],
        root, timeout)
    resultado["evidence"].append({"step": "build", **build})
    resultado["command"] = build["command"]
    resultado["warnings"].extend(build["warnings"])
    if build["exit_code"] != 0:
        resultado["build_status"] = "failed"
        resultado["exit_code"] = build["exit_code"]
        resultado["errors"] = build["errors"] or [{
            "code": "BUILD001",
            "message": build["stderr_tail"] or "dotnet build falhou sem diagnóstico",
        }]
        resultado["error"] = f"dotnet build falhou (exit {build['exit_code']})"
        return resultado

    resultado.update({
        "success": True, "status": "PASS", "exit_code": 0,
        "build_status": "succeeded", "errors": [],
    })
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Valida o scaffold .NET executando restore e build reais.")
    parser.add_argument("--root", required=True,
                        help="raiz do backend (source-code/backend)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--configuration", default="Release")
    parser.add_argument("--skip-build", action="store_true",
                        help="só valida estrutura — não prova compilação")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    resultado = verify(Path(args.root).resolve(), timeout=args.timeout,
                       skip_build=args.skip_build,
                       configuration=args.configuration)
    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    elif not args.quiet:
        print(f"[verify-dotnet] {resultado['status']} — "
              f"restore={resultado['restore_status']} "
              f"build={resultado['build_status']} "
              f"errors={len(resultado['errors'])} "
              f"warnings={len(resultado['warnings'])}")
        if resultado["error"]:
            print(f"  {resultado['error']}", file=sys.stderr)
    return 0 if resultado["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
