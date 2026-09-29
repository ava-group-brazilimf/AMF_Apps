#!/usr/bin/env python3
"""Execução de subprocesso com streaming ao vivo, teto total e kill de árvore.

Por que um módulo próprio
-------------------------
Até aqui cada camada da F4S rolava o seu ``subprocess.run(..., capture_output=
True)``. Somadas, elas formam uma cadeia CEGA:

    pipeline_runner → scaffold_runner → f4s_*_scaffold → dotnet

A saída do ``dotnet`` só aparecia — quando aparecia — depois que o processo
inteiro terminava. Num scaffold de 79 projetos isso é ~15 minutos de tela
parada; e quando o teto do passo estourava, o processo morria antes de emitir
qualquer coisa e TODA a evidência ia junto. Foi exatamente o que aconteceu em
`nopcommerce-02`: 280 invocações de ``dotnet``, 835s de trabalho real, morte no
último suspiro, zero log.

Este módulo é a única infraestrutura de execução de processo da esteira. Três
garantias, que é o que os chamadores precisam:

* **streaming** — os pipes são lidos em modo binário e SEM buffer, por uma
  thread cada, e repassados assim que o SO os entrega. Ler por BLOCO (e não por
  linha) é deliberado: preserva o prompt sem ``\\n`` do gate de aprovação, que a
  leitura por linha esconderia até o timeout.
* **teto total** — o prazo vale para a execução inteira, conta do spawn e nunca
  é reiniciado por linha nova. NÃO é timeout de inatividade.
* **árvore** — ``Popen.kill()`` deixa ``dotnet``/``node`` órfãos no Windows,
  segurando lock de arquivo e CPU (R10). O encerramento passa por
  ``taskkill /T`` (ou ``killpg``), com força só se o normal não bastar.

Uma thread por pipe, e nunca ``communicate()`` depois de ler: é o que elimina o
deadlock clássico de encher o buffer de um pipe enquanto se lê o outro.
"""
from __future__ import annotations

import codecs
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, BinaryIO, Iterable, TextIO

#: Leitura por bloco: grande o bastante para não picotar log de build, pequena
#: o bastante para um prompt aparecer na hora.
_CHUNK = 65536

#: Prazo para o processo morrer depois do sinal, antes do encerramento forçado.
GRACE_S = 10.0


def kill_process_tree(pid: int) -> None:
    """Encerra o processo E todos os seus descendentes.

    ``Popen.terminate()`` mata só o pai. No Windows o ``dotnet`` (ou o ``node``)
    que ele lançou continua vivo, segurando lock de arquivo — daí ``/T``.
    """
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True, check=False)
        return
    import signal  # noqa: PLC0415 — só há caminho POSIX aqui
    for sinal in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(pid), sinal)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                os.kill(pid, sinal)
            except (ProcessLookupError, PermissionError, OSError):
                return
        if sinal is signal.SIGTERM:
            time.sleep(0.5)
            if _morreu(pid):
                return


def _morreu(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return True
    return False


def tail(texto: str, linhas: int = 25) -> str:
    """Últimas `linhas` não-vazias — o que cabe numa mensagem de erro."""
    uteis = [linha for linha in (texto or "").splitlines() if linha.strip()]
    return "\n".join(uteis[-linhas:])


class _Pump(threading.Thread):
    """Lê um pipe até EOF, repassando ao console e/ou acumulando.

    O prefixo é aplicado só no início de cada linha: o conteúdo original chega
    ao operador byte a byte, que é o que serve para diagnóstico.
    """

    def __init__(self, pipe: BinaryIO, *, echo: TextIO | None, prefix: str,
                 lock: threading.Lock, capture: bool) -> None:
        super().__init__(daemon=True)
        self.pipe, self.echo, self.prefix, self.lock = pipe, echo, prefix, lock
        self.capture = capture
        self.chunks: list[str] = []
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._inicio_de_linha = True

    def run(self) -> None:  # pragma: no cover - exercitado pelos testes de ponta
        try:
            while True:
                bruto = self.pipe.read(_CHUNK)
                if not bruto:
                    break
                self._emitir(self._decoder.decode(bruto))
            self._emitir(self._decoder.decode(b"", final=True))
        except (OSError, ValueError):
            # Pipe fechado embaixo da thread — acontece no kill e não é erro.
            pass
        finally:
            try:
                self.pipe.close()
            except Exception:  # noqa: BLE001
                pass

    def _emitir(self, texto: str) -> None:
        if not texto:
            return
        if self.capture:
            self.chunks.append(texto)
        if self.echo is None:
            return
        with self.lock:
            if not self.prefix:
                self.echo.write(texto)
            else:
                # Split manual em "\n": `splitlines()` quebra também em \v, \f e
                # U+2028, que aparecem no meio de sequência ANSI e picotariam a
                # cor do log filho.
                resto = texto
                while resto:
                    corte = resto.find("\n")
                    if corte < 0:
                        pedaco, resto = resto, ""
                    else:
                        pedaco, resto = resto[:corte + 1], resto[corte + 1:]
                    if self._inicio_de_linha and pedaco:
                        self.echo.write(self.prefix)
                    self.echo.write(pedaco)
                    self._inicio_de_linha = pedaco.endswith("\n")
            try:
                self.echo.flush()
            except Exception:  # noqa: BLE001 — console fechado não derruba o passo
                pass

    @property
    def texto(self) -> str:
        return "".join(self.chunks)


def _env_sem_buffer(env: dict[str, str] | None) -> dict[str, str]:
    """Filho Python bufferiza stdout quando não é tty — e some da tela.

    `PYTHONUNBUFFERED` resolve para os nossos scripts; `PYTHONIOENCODING` evita
    que o console cp1252 do Windows estoure em UnicodeEncodeError no meio de um
    log com acento ou box-drawing.
    """
    base = dict(os.environ if env is None else env)
    base.setdefault("PYTHONUNBUFFERED", "1")
    base.setdefault("PYTHONIOENCODING", "utf-8")
    return base


def run(command: Iterable[str], cwd: Path | str | None = None, *,
        timeout_s: float | None, prefix: str = "",
        stream: TextIO | None = None,
        echo_stdout: bool = True, echo_stderr: bool = True,
        capture_stdout: bool = True, capture_stderr: bool = True,
        merge_stderr: bool = False, shell: bool = False,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Executa `command` transmitindo a saída ao vivo, sob um teto TOTAL.

    `timeout_s` cobre a execução inteira, começa no spawn e não é reiniciado por
    saída nova. Estourou: a ÁRVORE é encerrada e sobe `subprocess.TimeoutExpired`
    já com o que o processo tinha produzido (`.output`/`.stderr`) e o tempo real
    decorrido (`.elapsed_s`) — sem isso o operador recebe um timeout sem nenhuma
    pista de onde o processo estava.

    `merge_stderr` junta os dois fluxos num pipe só, preservando a ordem real de
    emissão; separado, cada um vai para a sua thread (nunca há leitura serial de
    um pipe enquanto o outro enche — é assim que o deadlock é evitado).

    `shell` existe por um único motivo já assumido pelo repo: `npm`/`ng` são
    `.cmd` no Windows e estouram WinError 193 sem ele. O default é False e
    nenhum caminho novo o liga; `taskkill /T` continua levando o `cmd.exe`
    intermediário e seus filhos.
    """
    argv = [str(parte) for parte in command]
    if timeout_s is not None and (isinstance(timeout_s, bool)
                                  or not isinstance(timeout_s, (int, float))
                                  or timeout_s <= 0):
        raise ValueError(f"timeout_s inválido: {timeout_s!r}")

    destino = sys.stderr if stream is None else stream
    kwargs: dict[str, Any] = {
        "cwd": str(cwd) if cwd is not None else None,
        "shell": shell,
        "bufsize": 0,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT if merge_stderr else subprocess.PIPE,
        "env": _env_sem_buffer(env),
    }
    if os.name != "nt":
        # Grupo próprio: é o que torna `killpg` capaz de levar os netos junto.
        kwargs["start_new_session"] = True

    inicio = time.monotonic()
    proc = subprocess.Popen(argv, **kwargs)

    lock = threading.Lock()
    bombas = [_Pump(proc.stdout, echo=destino if echo_stdout else None,
                    prefix=prefix, lock=lock, capture=capture_stdout)]
    if not merge_stderr and proc.stderr is not None:
        bombas.append(_Pump(proc.stderr, echo=destino if echo_stderr else None,
                            prefix=prefix, lock=lock, capture=capture_stderr))
    for bomba in bombas:
        bomba.start()

    estourou = False
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        estourou = True
        kill_process_tree(proc.pid)
        try:
            proc.wait(timeout=GRACE_S)
        except subprocess.TimeoutExpired:  # pragma: no cover - último recurso
            proc.kill()
            proc.wait()
    finally:
        # As bombas terminam sozinhas no EOF que o kill provoca. O join tem teto
        # para que um pipe herdado por um neto sobrevivente não trave o runner.
        for bomba in bombas:
            bomba.join(timeout=GRACE_S)

    decorrido = time.monotonic() - inicio
    saida = bombas[0].texto
    erro = bombas[1].texto if len(bombas) > 1 else ""

    if estourou:
        exc = subprocess.TimeoutExpired(argv, timeout_s, output=saida, stderr=erro)
        exc.elapsed_s = decorrido  # type: ignore[attr-defined]
        raise exc

    resultado = subprocess.CompletedProcess(argv, proc.returncode, saida, erro)
    resultado.elapsed_s = decorrido  # type: ignore[attr-defined]
    return resultado
