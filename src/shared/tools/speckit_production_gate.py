#!/usr/bin/env python3
"""
AVA Fabric — Gate de PRODUÇÃO dos artefatos da F3S
===================================================
Confere que a consolidação da wave5b **produziu de fato** o que promete, em vez
de confiar no exit code do passo anterior.

Por que existe
--------------
Medido em ``cadastro-funcionarios-04``: `speckit_task_compiler.py compile
--warn` saía com **0** e não gravava artefato nenhum. `--warn` trocava o exit
code; o abort interno continuava lá. O passo ficava verde, `traceability.json`
seguia placeholder, e o defeito só aparecia 11 checks adiante, descrito como 11
sintomas diferentes.

A lição: **exit code não é prova de produção.** Este gate olha o disco.

O que confere
-------------
* ``traceability.json`` existe, é JSON válido e ``recovery_placeholder`` é false;
* o ``status`` não é ``INCOMPLETE`` (warnings são aceitáveis);
* ``tasks-progress.json`` existe e também não é placeholder;
* a contagem de tasks bate entre os dois artefatos;
* ``compile-warnings.json``, quando existe, declara ``artifacts_written: true``.

Política de saída
-----------------
Non-blocking por padrão, como o resto da camada SpecKit: reporta e sai 0. Com
``--strict``, sai 1 quando a produção não aconteceu — para quem quiser usar o
gate em CI. O relatório vai sempre para
``outputs/tobe/speckit/production-gate-status.json``.

Uso
---
    python src/shared/tools/speckit_production_gate.py -p <projeto> [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPORT_NAME = "production-gate-status.json"


def _speckit(project: str, root: Path) -> Path:
    return root / "projects" / project / "outputs" / "tobe" / "speckit"


def _ler(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.is_file():
        return None, "ausente"
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"ilegível ({type(exc).__name__})"
    if not isinstance(dados, dict):
        return None, "raiz não é objeto JSON"
    return dados, ""


def check_production(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Veredito de produção. Nunca levanta: um gate que quebra não é um gate."""
    root = repo_root or REPO_ROOT
    speckit = _speckit(project, root)
    problemas: list[str] = []
    detalhes: dict[str, Any] = {}

    trace, erro = _ler(speckit / "traceability.json")
    if trace is None:
        problemas.append(f"traceability.json {erro}")
        entries = 0
    else:
        entries = len(trace.get("entries") or [])
        detalhes["traceability_status"] = trace.get("status")
        detalhes["traceability_entries"] = entries
        if trace.get("recovery_placeholder"):
            problemas.append("traceability.json é placeholder de recuperação — "
                             "o consolidador não produziu o artefato")
        if str(trace.get("status") or "") == "INCOMPLETE":
            problemas.append("traceability.json com status INCOMPLETE")

    progresso, erro = _ler(speckit / "tasks-progress.json")
    if progresso is None:
        problemas.append(f"tasks-progress.json {erro}")
        tasks = 0
    else:
        tasks = len(progresso.get("tasks") or [])
        detalhes["progress_tasks"] = tasks
        if progresso.get("recovery_placeholder"):
            problemas.append("tasks-progress.json é placeholder de recuperação")

    if trace is not None and progresso is not None and entries != tasks:
        problemas.append(
            f"contagem incompatível: traceability={entries} entries, "
            f"tasks-progress={tasks} tasks")

    avisos, _ = _ler(speckit / "compile-warnings.json")
    if avisos is not None:
        detalhes["artifacts_written"] = avisos.get("artifacts_written")
        detalhes["warning_count"] = avisos.get("warning_count", avisos.get("total_warnings"))
        detalhes["ownership_conflicts"] = len(avisos.get("conflicts") or [])
        if avisos.get("artifacts_written") is False:
            problemas.append("compile-warnings.json declara artifacts_written: false")

    return {
        "project": project,
        "generated_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "produced": not problemas,
        "problems": problemas,
        **detalhes,
    }


def _persistir(project: str, veredito: dict[str, Any], root: Path) -> Path | None:
    alvo = _speckit(project, root) / REPORT_NAME
    try:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(veredito, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        return alvo
    except OSError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python src/shared/tools/speckit_production_gate.py",
        description="Confere que a F3S produziu traceability e progresso de verdade.")
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 quando a produção não aconteceu (padrão: 0)")
    args = parser.parse_args(argv)

    if not (REPO_ROOT / "projects" / args.project).is_dir():
        print(f"ERRO: projeto não encontrado: projects/{args.project}", file=sys.stderr)
        return 2

    veredito = check_production(args.project)
    destino = _persistir(args.project, veredito, REPO_ROOT)

    if args.json:
        print(json.dumps(veredito, ensure_ascii=False, indent=2))
    elif veredito["produced"]:
        print(f"\n  ✅ F3S produziu os artefatos — "
              f"{veredito.get('traceability_entries', 0)} entry(ies), "
              f"{veredito.get('progress_tasks', 0)} task(s) em progresso")
        if veredito.get("ownership_conflicts"):
            print(f"     {veredito['ownership_conflicts']} conflito(s) de ownership "
                  f"registrado(s) — ver compile-warnings.json")
    else:
        print(f"\n  ⚠️  F3S NÃO produziu os artefatos esperados — {args.project}")
        for problema in veredito["problems"]:
            print(f"     · {problema}")
        print("     Rode: python src/shared/tools/speckit_task_compiler.py "
              f"compile -p {args.project}")
    if destino:
        print(f"  📄 {destino.relative_to(REPO_ROOT).as_posix()}")

    return 0 if (veredito["produced"] or not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
