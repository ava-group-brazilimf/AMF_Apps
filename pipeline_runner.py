#!/usr/bin/env python3
"""
AVA Fabric Pipeline Runner — DEPRECADO
=======================================
Substituído por ``src/shared/tools/ava_pipeline.py``, que faz o mesmo com CLI,
``--dry-run``, rota via proxy Headroom e configuração centralizada em
``src/shared/data/ava-pipeline.yaml``.

Este arquivo virou um shim para não quebrar quem tem o comando na memória
muscular ou em atalho. Sem argumentos, cai no menu interativo do subcomando
``run``, que preserva o fluxo antigo.

Equivalências
-------------
=================================  ==========================================
``python pipeline_runner.py``      ``ava-pipeline run -p <PROJ>``
menu "Full Pipeline"               ``--all``
menu "Por Fase"                    ``--phase F2`` (grupo) ou ``--phase F2b``
menu "Automático"                  ``--yes``
=================================  ==========================================

O que mudou de verdade
----------------------
- ``WORKSPACE`` apontava para outro checkout; agora o repo é resolvido de
  ``__file__``, então o script roda onde está.
- A spec de cada agente vem do ``agent_registry`` pelo caminho exato, no lugar
  da heurística de substring que podia carregar o agente errado.
- Modelo, endpoint e a ordem da esteira saíram do código para o YAML.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS))

import ava_pipeline  # noqa: E402

SUBCOMMANDS = ("run", "list", "config", "doctor")


def _pick_project() -> str:
    """Seletor de projeto do runner antigo — `run` exige --project.

    Fica no shim, não no CLI: lá `--project` é obrigatório de propósito, para
    que o comando seja scriptável sem prompt escondido.
    """
    projects = ava_pipeline.list_projects()
    print("\n\033[1mProjetos disponíveis:\033[0m")
    for i, name in enumerate(projects, 1):
        print(f"  {i}. {name}")
    print(f"  {len(projects) + 1}. Digitar nome manualmente")

    raw = input("\n\033[1mSelecione o projeto [número ou nome]: \033[0m").strip()
    if raw.isdigit():
        idx = int(raw) - 1
        if idx == len(projects):
            raw = input("  Nome do projeto: ").strip()
        elif 0 <= idx < len(projects):
            raw = projects[idx]
        else:
            raise SystemExit("Seleção inválida.")
    if not raw:
        raise SystemExit("Nome do projeto não pode ser vazio.")
    return raw


if __name__ == "__main__":
    print(
        "\033[93m"
        "AVISO: pipeline_runner.py está deprecado.\n"
        "       Use: python src/shared/tools/ava_pipeline.py run -p <PROJETO>\n"
        "       ou:  ava-pipeline.bat run -p <PROJETO> --all\n"
        "\033[0m",
        file=sys.stderr,
    )

    argv = list(sys.argv[1:])
    if not argv or argv[0] not in (*SUBCOMMANDS, "-h", "--help"):
        argv = ["run", *argv]
    if argv[0] == "run" and not {"-p", "--project"} & set(argv):
        argv += ["-p", _pick_project()]

    sys.exit(ava_pipeline.main(argv))
