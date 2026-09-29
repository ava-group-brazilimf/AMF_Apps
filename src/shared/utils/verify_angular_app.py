#!/usr/bin/env python3
"""
verify_angular_app.py — gate determinístico de aplicação Angular (spec 042).

Fases: PREREQ → INSTALL → BUILD → BOOT → HEALTH → veredito.

Prova que o app **compila e responde**, não apenas que compila: a ausência de
`polyfills: ["zone.js"]` em `angular.json`, por exemplo, passa no `ng build` e só
quebra no browser (NG0908). A fase HEALTH captura essa classe de defeito.

Porte do `verify-angular.sh` para Python, com três divergências deliberadas — todas
por portabilidade Windows ou determinismo:

  - `npm install` quando não há lockfile, `npm ci` quando há. O `.sh` usava `npm ci`
    incondicionalmente, o que falha num scaffold recém-gerado.
  - servidor estático via `http.server` da stdlib, com bind na porta 0. Elimina a
    dependência de `npx http-server` e toda a classe de falha "porta em uso"
    (o `.sh` usava `lsof`, que não existe no Windows).
  - shutdown por `try/finally` + `atexit` no lugar de `trap`.

Uso:
    python src/shared/utils/verify_angular_app.py --root <app_root> --json
    python src/shared/utils/verify_angular_app.py --root <app_root> --skip-serve
    python src/shared/utils/verify_angular_app.py --root <app_root> --expect "<app-root"

Saída (JSON em stdout):
    {
      "status": "PASS" | "FAIL" | "ERROR",
      "app_root": "/abs/path",
      "dist_dir": "/abs/path/dist/app/browser",
      "phases": [{"name": "install", "status": "PASS", "detail": "npm install"}, ...],
      "log_path": "/abs/path/.artifacts/verify-angular.log",
      "elapsed_seconds": 91.4,
      "error": null
    }

Exit codes:
    0  — PASS
    10 — pré-requisitos
    20 — install
    30 — build
    40 — boot
    50 — health
    60 — uso incorreto
"""
from __future__ import annotations

import argparse
import atexit
import functools
import http.server
import json
import os
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# O executor comum da esteira vive em src/shared/tools; este arquivo está em
# src/shared/utils e não é importável como pacote.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import proc_stream  # noqa: E402

EXIT_PASS = 0
EXIT_PREREQ = 10
EXIT_INSTALL = 20
EXIT_BUILD = 30
EXIT_BOOT = 40
EXIT_HEALTH = 50
EXIT_USAGE = 60

#: Profundidade máxima na busca pelo `angular.json`. Cobre o layout canônico
#: (na raiz) e árvores legadas como `frontend/<app>-spa/`.
APP_ROOT_MAX_DEPTH = 2

DEFAULT_TIMEOUT = 60


class VerifyError(Exception):
    """Falha de fase; carrega o exit code correspondente."""

    def __init__(self, code: int, phase: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.phase = phase
        self.message = message


# ─── logging ────────────────────────────────────────────────────────────────────


class Logger:
    """Log estruturado simultâneo em arquivo e stderr."""

    def __init__(self, log_path: Path, quiet: bool = False) -> None:
        self.path = log_path
        self.quiet = quiet
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")

    def __call__(self, level: str, message: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{stamp}] [{level}] {message}"
        with self.path.open("a", encoding="utf-8", errors="replace") as fh:
            fh.write(line + "\n")
        if not self.quiet:
            print(line, file=sys.stderr)


# ─── resolução do app_root ──────────────────────────────────────────────────────


def resolve_app_root(root: Path) -> Path:
    """Localiza o diretório que contém `angular.json`.

    O scaffold determinístico o coloca na raiz do repo da stack. Árvores geradas
    antes da spec 042 o enterravam sob `frontend/<app>-spa/`, então procuramos
    também alguns níveis abaixo em vez de reprovar.
    """
    if (root / "angular.json").is_file():
        return root

    for depth in range(1, APP_ROOT_MAX_DEPTH + 1):
        pattern = "/".join(["*"] * depth) + "/angular.json"
        matches = sorted(
            p for p in root.glob(pattern) if "node_modules" not in p.parts
        )
        if len(matches) == 1:
            return matches[0].parent
        if len(matches) > 1:
            found = ", ".join(str(m.parent) for m in matches)
            raise VerifyError(
                EXIT_PREREQ, "prereq",
                f"mais de um angular.json sob {root}: {found}. "
                "Use --root para apontar o app explicitamente.",
            )
    return root


# ─── execução de subprocessos ───────────────────────────────────────────────────


def run_logged(log: Logger, phase: str, cmd: list[str], cwd: Path,
               timeout: int) -> subprocess.CompletedProcess[str]:
    log("INFO", f"{phase}: $ {' '.join(cmd)}")
    print(f"  [verify:{phase}] $ {' '.join(cmd)}", file=sys.stderr, flush=True)
    try:
        # `npm install` e `ng build` são as etapas longas da perna frontend.
        # Transmitir ao vivo (pelo stderr, para não sujar o JSON do stdout) é o
        # que permite ver o progresso; a captura segue inteira para o arquivo.
        proc = proc_stream.run(
            cmd, cwd=cwd, timeout_s=timeout, prefix=f"  [{phase}] ",
            stream=sys.stderr,
            # npm/ng no Windows são .cmd; shell=True evita WinError 193.
            shell=(os.name == "nt"),
        )
    except FileNotFoundError as exc:
        raise VerifyError(EXIT_PREREQ, phase, f"comando não encontrado: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VerifyError(EXIT_PREREQ, phase,
                          f"timeout de {timeout}s excedido em {' '.join(cmd)}") from exc

    for stream in (proc.stdout, proc.stderr):
        if stream:
            with log.path.open("a", encoding="utf-8", errors="replace") as fh:
                fh.write(stream if stream.endswith("\n") else stream + "\n")
    return proc


def _tail(text: str, lines: int = 15) -> str:
    kept = [ln for ln in (text or "").splitlines() if ln.strip()][-lines:]
    return "\n".join(kept)


# ─── fases ──────────────────────────────────────────────────────────────────────


def phase_prereq(log: Logger, app_root: Path) -> str:
    for tool in ("node", "npm"):
        if shutil.which(tool) is None:
            raise VerifyError(EXIT_PREREQ, "prereq", f"{tool} não encontrado no PATH")
    if not (app_root / "package.json").is_file():
        raise VerifyError(EXIT_PREREQ, "prereq",
                          f"package.json não encontrado em {app_root}")
    if not (app_root / "angular.json").is_file():
        raise VerifyError(EXIT_PREREQ, "prereq",
                          f"angular.json não encontrado em {app_root}")
    log("PASS", f"prereq: node e npm disponíveis; projeto em {app_root}")
    return str(app_root)


def choose_install_command(app_root: Path) -> list[str]:
    """`npm ci` exige lockfile; um scaffold recém-gerado ainda não tem um.

    Primeira execução usa `npm install` e produz o lockfile, que entra no commit
    inicial. Da segunda em diante o install volta a ser reprodutível com `npm ci`.
    """
    base = ["npm", "ci"] if (app_root / "package-lock.json").is_file() else ["npm", "install"]
    return [*base, "--no-audit", "--no-fund"]


def phase_install(log: Logger, app_root: Path, timeout: int) -> str:
    cmd = choose_install_command(app_root)
    log("INFO", f"fase 1/4: instalando dependências ({' '.join(cmd[:2])})")
    proc = run_logged(log, "install", cmd, app_root, timeout)
    if proc.returncode != 0:
        raise VerifyError(EXIT_INSTALL, "install",
                          f"{' '.join(cmd[:2])} falhou (exit {proc.returncode}):\n"
                          f"{_tail(proc.stderr or proc.stdout)}")
    log("PASS", f"install: dependências instaladas via {' '.join(cmd[:2])}")
    return " ".join(cmd[:2])


def find_dist_dir(app_root: Path) -> Path | None:
    """Localiza o diretório servível do build.

    Angular 17+ emite `dist/<app>/browser/index.html`; versões anteriores emitiam
    `dist/<app>/index.html`. Procuramos o `index.html` e usamos o diretório dele,
    o que cobre os dois layouts sem condicional por versão.
    """
    dist = app_root / "dist"
    if not dist.is_dir():
        return None
    matches = sorted(dist.rglob("index.html"), key=lambda p: len(p.parts))
    for match in matches:
        if "node_modules" not in match.parts:
            return match.parent
    return None


def phase_build(log: Logger, app_root: Path, timeout: int) -> Path:
    log("INFO", "fase 2/4: compilando (ng build --configuration production)")
    cmd = ["npx", "ng", "build", "--configuration", "production"]
    proc = run_logged(log, "build", cmd, app_root, timeout)
    if proc.returncode != 0:
        raise VerifyError(EXIT_BUILD, "build",
                          f"ng build falhou (exit {proc.returncode}):\n"
                          f"{_tail(proc.stdout or proc.stderr, 25)}")

    dist_dir = find_dist_dir(app_root)
    if dist_dir is None:
        raise VerifyError(EXIT_BUILD, "build",
                          f"index.html não encontrado sob {app_root / 'dist'} após o build")
    log("PASS", f"build: artefatos em {dist_dir}")
    return dist_dir


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler sem poluir stderr a cada requisição."""

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        return


def start_static_server(
    directory: Path,
) -> tuple[socketserver.TCPServer, int, threading.Thread]:
    """Sobe um servidor estático numa porta efêmera.

    Bind na porta 0 faz o SO escolher uma porta livre — eliminando a classe de falha
    "porta já em uso" que o script original tratava com `lsof`.
    """
    handler = functools.partial(_QuietHandler, directory=str(directory))

    class _Server(socketserver.TCPServer):
        allow_reuse_address = True
        address_family = socket.AF_INET

    server = _Server(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port, thread


def phase_health(log: Logger, port: int, path: str, expect: str,
                 timeout: int, server_thread: threading.Thread) -> str:
    url = f"http://127.0.0.1:{port}{path}"
    log("INFO", f"fase 4/4: health-check em {url} (até {timeout}s)")

    deadline = time.monotonic() + timeout
    last_status = "sem resposta"
    body = ""

    while time.monotonic() < deadline:
        # A thread do servidor morrer é falha de boot; reportá-la de imediato evita
        # esperar o timeout inteiro por algo que nunca vai responder.
        if not server_thread.is_alive():
            raise VerifyError(EXIT_BOOT, "boot",
                              "a thread do servidor estático terminou antes do "
                              "primeiro health-check")
        try:
            with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310
                last_status = str(response.status)
                if response.status == 200:
                    body = response.read().decode("utf-8", errors="replace")
                    break
        except urllib.error.HTTPError as exc:
            last_status = str(exc.code)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_status = f"sem conexão ({exc})"
        time.sleep(0.25)

    if not body:
        raise VerifyError(EXIT_HEALTH, "health",
                          f"sem HTTP 200 em {timeout}s (último status: {last_status})")
    if expect not in body:
        raise VerifyError(EXIT_HEALTH, "health",
                          f"HTTP 200 recebido, mas o conteúdo esperado está ausente: "
                          f"{expect!r}")
    log("PASS", f"health: HTTP 200 e conteúdo {expect!r} presente")
    return url


# ─── orquestração ───────────────────────────────────────────────────────────────


def verify(root: Path, timeout: int = DEFAULT_TIMEOUT, health_path: str = "/",
           expect: str = "<app-root", skip_serve: bool = False,
           quiet: bool = False, install_timeout: int = 900,
           build_timeout: int = 900) -> dict[str, Any]:
    started = time.monotonic()
    app_root = resolve_app_root(root.resolve())
    log = Logger(app_root / ".artifacts" / "verify-angular.log", quiet=quiet)
    log("INFO", f"── verify-angular @ {app_root} ──")

    phases: list[dict[str, str]] = []
    result: dict[str, Any] = {
        "status": "PASS",
        "app_root": str(app_root),
        "dist_dir": None,
        "phases": phases,
        "log_path": str(log.path),
        "elapsed_seconds": 0.0,
        "error": None,
    }
    server: socketserver.TCPServer | None = None

    def shutdown() -> None:
        if server is not None:
            try:
                server.shutdown()
                server.server_close()
            except Exception:  # noqa: BLE001 — cleanup nunca deve mascarar o veredito
                pass

    atexit.register(shutdown)
    try:
        phases.append({"name": "prereq", "status": "PASS",
                       "detail": phase_prereq(log, app_root)})
        phases.append({"name": "install", "status": "PASS",
                       "detail": phase_install(log, app_root, install_timeout)})

        dist_dir = phase_build(log, app_root, build_timeout)
        result["dist_dir"] = str(dist_dir)
        phases.append({"name": "build", "status": "PASS", "detail": str(dist_dir)})

        if skip_serve:
            log("INFO", "boot/health pulados (--skip-serve)")
            phases.append({"name": "boot", "status": "SKIPPED", "detail": "--skip-serve"})
            phases.append({"name": "health", "status": "SKIPPED", "detail": "--skip-serve"})
        else:
            log("INFO", "fase 3/4: subindo servidor estático em porta efêmera")
            try:
                server, port, server_thread = start_static_server(dist_dir)
            except OSError as exc:
                raise VerifyError(EXIT_BOOT, "boot",
                                  f"falha ao subir o servidor estático: {exc}") from exc
            log("PASS", f"boot: servindo {dist_dir} em http://127.0.0.1:{port}")
            phases.append({"name": "boot", "status": "PASS",
                           "detail": f"127.0.0.1:{port}"})
            phases.append({"name": "health", "status": "PASS",
                           "detail": phase_health(log, port, health_path, expect,
                                                  timeout, server_thread)})
    except VerifyError as exc:
        phases.append({"name": exc.phase, "status": "FAIL", "detail": exc.message})
        result["status"] = "FAIL"
        result["error"] = f"{exc.phase}: {exc.message}"
        result["exit_code"] = exc.code
        log("FAIL", f"{exc.phase}: {exc.message}")
    finally:
        shutdown()
        server = None

    result["elapsed_seconds"] = round(time.monotonic() - started, 1)
    if result["status"] == "PASS":
        log("PASS", f"veredito: OK — install, build, boot e health "
                    f"({result['elapsed_seconds']}s)")
    else:
        log("FAIL", f"veredito: NOK — log completo em {log.path}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate determinístico de aplicação Angular: "
                    "install, build, boot e health."
    )
    parser.add_argument("--root", required=True,
                        help="diretório do app (ou ancestral que o contenha)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"timeout do health-check em segundos "
                             f"(default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--install-timeout", type=int, default=900)
    parser.add_argument("--build-timeout", type=int, default=900)
    parser.add_argument("--path", default="/", help="caminho do health-check")
    parser.add_argument("--expect", default="<app-root",
                        help="trecho que deve estar presente na resposta")
    parser.add_argument("--skip-serve", action="store_true",
                        help="executa apenas prereq, install e build")
    parser.add_argument("--json", action="store_true", help="saída JSON em stdout")
    parser.add_argument("--quiet", action="store_true",
                        help="não espelha o log em stderr")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        payload = {"status": "ERROR", "error": f"diretório inexistente: {root}",
                   "phases": []}
        print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json
              else f"[verify-angular] ERROR: diretório inexistente: {root}",
              file=sys.stdout if args.json else sys.stderr)
        return EXIT_USAGE

    result = verify(
        root=root,
        timeout=args.timeout,
        health_path=args.path,
        expect=args.expect,
        skip_serve=args.skip_serve,
        quiet=args.quiet or args.json,
        install_timeout=args.install_timeout,
        build_timeout=args.build_timeout,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for phase in result["phases"]:
            print(f"  {phase['status']:<7} {phase['name']:<8} {phase['detail']}")
        print(f"[verify-angular] {result['status']} "
              f"({result['elapsed_seconds']}s) — log: {result['log_path']}")

    return EXIT_PASS if result["status"] == "PASS" else int(result.get("exit_code", 1))


if __name__ == "__main__":
    sys.exit(main())
