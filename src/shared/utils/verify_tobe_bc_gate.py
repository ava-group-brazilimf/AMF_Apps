#!/usr/bin/env python3
"""
verify_tobe_bc_gate.py — Gate executável entre trigger CB e trigger TD
do agente architecture-design-tobe.md.

Verifica em disco que o trigger BC produziu seus artefatos obrigatórios
antes de permitir que o trigger TD seja invocado.

Uso:
    python src/shared/utils/verify_tobe_bc_gate.py --project Meu-ERP

Exit codes:
    0 = PASS — bounded-context-map.md e context-map.mmd existem e têm size > 0
    1 = FAIL — um ou mais artefatos BC ausentes ou vazios
"""

import argparse
import sys
from pathlib import Path

# Força UTF-8 no Windows. Sem isto, o console cp1252 estourava
# `UnicodeEncodeError` ao imprimir `⛔` — exatamente no caminho de FALHA, o único
# em que a mensagem importa. O operador via um traceback no lugar da razão.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ancorado no arquivo, não no cwd: um path relativo resolve contra o diretório
# corrente e, num segundo checkout do repo sem aquele projeto, reporta ausente
# um artefato que existe. Foi essa classe de falso negativo que derrubou a F2
# em MeuERP-002 (ver tobe-architecture/utils/artifact_gate_tobe.py).
_REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate executável: verifica artefatos do trigger BC antes de TD."
    )
    parser.add_argument("--project", required=True, help="Nome do projeto (ex: Meu-ERP)")
    args = parser.parse_args()

    project_name = args.project
    base = _REPO_ROOT / "projects" / project_name / "outputs" / "tobe"

    # Artefatos obrigatórios do trigger BC
    required = [
        base / "docs" / "bounded-context-map.md",
        base / "diagrams" / "context-map.mmd",
    ]

    failures: list[str] = []

    for artifact in required:
        if not artifact.exists():
            failures.append(f"  AUSENTE : {artifact}")
        elif artifact.stat().st_size == 0:
            failures.append(f"  VAZIO   : {artifact}")
        else:
            size_kb = artifact.stat().st_size / 1024
            print(f"  OK      : {artifact.name} ({size_kb:.1f} KB)")

    if failures:
        print()
        print("⛔ [BC-GATE FAILED] Trigger BC não gerou todos os artefatos obrigatórios:")
        for f in failures:
            print(f)
        print()
        print("AÇÃO OBRIGATÓRIA:")
        print("  1. Re-invocar architecture-design-tobe.md com trigger 'BC' (max 1 retry)")
        print("  2. Re-executar este script para confirmar")
        print("  3. NÃO invocar trigger TD enquanto este gate não passar")
        print()
        print(
            f"BLOQUEIO: {len(failures)} artefato(s) ausente(s) — "
            "trigger TD PROIBIDO até resolução."
        )
        return 1

    print()
    print("✅ [BC-GATE PASSED] Trigger BC validado — trigger TD pode ser invocado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
