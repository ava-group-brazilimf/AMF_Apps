#!/usr/bin/env python3
"""Caminho curto para uma pasta funda, no Windows, sem admin e sem renomear nada.

O problema
----------
A F4S gera solutions .NET cujo caminho mais fundo passa de MAX_PATH (260). Medido
em 2026-08-26, projeto `cadastro-funcionarios`:

    ...\\backend\\tests\\EmployeeManagement\\
       CadastroFuncionarios.EmployeeManagement.Application.Tests\\
       CadastroFuncionarios.EmployeeManagement.Application.Tests.csproj      267 chars

Acima do limite o Windows clássico mente em vez de falhar: `Path.is_file()`
devolve `False` para arquivo existente. O gerador conclui "não existe", manda
`dotnet new` recriar, e o `dotnet new` — que enxerga o arquivo — recusa
sobrescrever com exit 73 (DestructiveChangesDetected). O sintoma não menciona
comprimento de caminho em momento algum.

Por que `subst` e não junction
------------------------------
Medido nas duas, nesta máquina:

  - `mklink /J` (junction): **não resolve**. O motor de templates do
    `dotnet new` canonicaliza o reparse point de volta para o alvo longo e
    falha com "The filename, directory name, or volume label syntax is
    incorrect".
  - `subst` (mapeamento DosDevice para letra de unidade): **resolve**.
    `GetFullPath` não desfaz o mapeamento, então o processo filho opera em
    `X:\\tests\\...` — curto. Verificado ponta a ponta: `dotnet new` cria e
    `dotnet build` compila (exit 0), com os arquivos e o `obj/bin` nascendo no
    caminho real e longo.

Nem `subst` nem junction exigem administrador.

O que este contorno NÃO muda
----------------------------
Nada do artefato. Os arquivos nascem com o nome e no lugar de sempre — a letra
de unidade só existe durante a chamada. Isso é o ponto: a saída é idêntica com
ou sem contorno, então habilitar `LongPathsEnabled` depois não muda um byte do
que já foi gerado. Um contorno que alterasse nomes de projeto tornaria a saída
dependente do ambiente, e aí a esteira deixaria de ser determinística.

⚠️ `.resolve()` DESFAZ o contorno
---------------------------------
`Path("Z:/").resolve()` devolve o caminho longo de verdade — o Windows resolve o
mapeamento DosDevice. Um `root = root.resolve()` defensivo no meio do caminho
apaga o contorno **sem erro nenhum**, e o sintoma volta a ser o `FileNotFoundError`
num arquivo que existe. Dentro do bloco `short_root`, trate a raiz curta como
absoluta e não a normalize. Foi assim que o verifier continuou falhando depois de
o generator já estar corrigido.

Limites conhecidos
------------------
  - Só Windows. Em Linux/macOS o context manager é no-op.
  - Precisa de uma letra livre; sem nenhuma, devolve o caminho original e quem
    chama reprova com a mensagem de sempre.
  - O mapeamento é da sessão de logon: processo elevado não enxerga um `subst`
    criado por processo não elevado. Não afeta a esteira, que roda inteira na
    mesma sessão.
"""
from __future__ import annotations

import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

WINDOWS_MAX_PATH = 260

#: Letras candidatas, do fim para o começo: `Z:` e vizinhas raramente estão em
#: uso, e começar por `E:` colidiria com pendrive, unidade de rede montada e
#: partição secundária.
_CANDIDATAS = "ZYXWVUT"

#: Caminho absoluto do `subst.exe`. Resolver pelo `SystemRoot` evita depender do
#: PATH, que num shell da esteira pode vir enxuto.
_SUBST_EXE = str(Path(os.environ.get("SystemRoot", r"C:\Windows"))
                 / "System32" / "subst.exe")


def long_paths_enabled() -> bool:
    """O Windows desta máquina aceita caminho acima de MAX_PATH?

    Duas travas independentes: a chave de registro `LongPathsEnabled` E um
    manifesto `longPathAware` no executável (o `python.exe` do CPython traz o
    dele desde a 3.6). Fora do Windows não existe a limitação.
    """
    if sys.platform != "win32":
        return True
    try:
        import winreg  # noqa: PLC0415 — só existe no Windows
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\FileSystem") as chave:
            return bool(winreg.QueryValueEx(chave, "LongPathsEnabled")[0])
    except OSError:
        return False


def path_exists(path: Path) -> bool:
    """`is_file()` que não mente quando o caminho passa de MAX_PATH.

    O prefixo `\\\\?\\` desliga a normalização do Win32 e alcança o arquivo que
    a API clássica não enxerga. Sem isto o chamador conclui "não existe" para um
    arquivo que existe — e manda recriá-lo.
    """
    if path.exists():
        return True
    if sys.platform != "win32":
        return False
    bruto = str(path)
    if bruto.startswith("\\\\?\\") or not Path(bruto).is_absolute():
        return False
    return Path(f"\\\\?\\{bruto}").exists()


def _letra_livre() -> str | None:
    """Primeira candidata sem unidade montada. `None` se todas estiverem em uso."""
    return next((letra for letra in _CANDIDATAS
                 if not Path(f"{letra}:\\").exists()), None)


def _subst(letra: str, alvo: Path) -> bool:
    # `subst.exe` existe em System32 — nada de `shell=True`, que exporia a
    # linha a interpretação do cmd por um caminho com espaço ou `&`.
    proc = subprocess.run([_SUBST_EXE, f"{letra}:", str(alvo)],
                          capture_output=True, text=True, check=False)
    return proc.returncode == 0 and Path(f"{letra}:\\").exists()


def _dessubst(letra: str) -> None:
    subprocess.run([_SUBST_EXE, f"{letra}:", "/D"],
                   capture_output=True, text=True, check=False)


def budget_exceeded(paths: Iterator[Path] | list[Path], *, headroom: int = 0) -> Path | None:
    """O pior caminho da lista, se algum estourar MAX_PATH; `None` se todos cabem.

    `headroom` reserva espaço para o que uma ferramenta a jusante acrescenta por
    baixo — no caso do MSBuild, `obj/Debug/netX.0/ref/<assembly>.dll` e afins.
    """
    if long_paths_enabled():
        return None
    pior = max(paths, key=lambda caminho: len(str(caminho)), default=None)
    if pior is None or len(str(pior)) + headroom <= WINDOWS_MAX_PATH:
        return None
    return pior


@contextmanager
def short_root(root: Path, *, needed: bool) -> Iterator[tuple[Path, str | None]]:
    """Cede um caminho curto equivalente a `root` enquanto durar o bloco.

    Devolve `(raiz_de_trabalho, letra)`. Quando o contorno não é necessário ou
    não é possível, `raiz_de_trabalho is root` e `letra is None` — quem chama
    segue com o caminho original e decide se reprova.

    A remoção do mapeamento vai em `finally`: deixar uma letra pendurada
    depois de uma falha entulha a máquina do operador com unidades fantasma.
    """
    if not needed or sys.platform != "win32":
        yield root, None
        return

    root.mkdir(parents=True, exist_ok=True)
    letra = _letra_livre()
    if letra is None or not _subst(letra, root):
        yield root, None
        return
    try:
        yield Path(f"{letra}:\\"), letra
    finally:
        _dessubst(letra)


def to_real(caminho: Path, curta: Path, real: Path) -> Path:
    """Traduz um caminho sob a raiz curta de volta para a raiz real.

    Existe porque o artefato e o relatório precisam nomear o lugar de verdade:
    um JSON que diz `X:\\tests\\...` descreve uma unidade que já não existe
    quando alguém for ler.
    """
    try:
        return real / caminho.relative_to(curta)
    except ValueError:
        return caminho
