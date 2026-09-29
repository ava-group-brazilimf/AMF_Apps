#!/usr/bin/env python3
"""
verify_agent_observability.py — Gate de consistência do auto-reporte dos agentes.

A versão e a fase de cada agente vivem em **três** lugares que podem divergir
independentemente:

    1. frontmatter `version:` do próprio `.md`          ← FONTE DE VERDADE
    2. literal `--version` / `--phase` do bloco de observabilidade
    3. `AGENT_CATALOG` (hoje derivado de `agent_registry.py`)

Como o bloco é escrito à mão em ~100 arquivos e não existe gerador, o drift é
inevitável sem um gate. Na varredura que originou specs/032 havia 7 `--phase`
errados, 3 agentes reportando o `--agent` de outro (copiar-colar) e 18 versões
divergentes — ou seja, economia de contexto creditada ao agente ou à fase errada.

Verificações
------------
    E1  `--agent` do bloco ≠ frontmatter `name`
    E2  `--phase` do bloco ≠ fase do módulo (Constituição v1.4.0)
    E3  `--version` do bloco ≠ frontmatter `version`
    E4  agente despachável sem bloco `track`
    E5  frontmatter sem `version:`
    E6  o mesmo `name` declarado por mais de um arquivo

Uso
---
    python src/shared/utils/verify_agent_observability.py
    python src/shared/utils/verify_agent_observability.py --json
    python src/shared/utils/verify_agent_observability.py --agent ava-qa-exploratory
    python src/shared/utils/verify_agent_observability.py --ignore E5

Exit codes
----------
    0 — nenhuma violação
    1 — violações encontradas
    2 — erro de execução (registro vazio/ilegível)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
_REGISTRY_PATH = PROJECT_ROOT / "src" / "shared" / "tools" / "agent_registry.py"

CHECK_LABELS = {
    "E1": "--agent diverge do frontmatter name",
    "E2": "--phase diverge da fase do módulo",
    "E3": "--version diverge do frontmatter version",
    "E4": "agente despachável sem bloco track",
    "E5": "frontmatter sem version",
    "E6": "id declarado por mais de um arquivo",
}


def _load_registry():
    """Importa ``agent_registry.py`` por path — ``src/shared/tools`` não é pacote."""
    spec = importlib.util.spec_from_file_location("ava_agent_registry", _REGISTRY_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect_violations(registry, ignore: set[str]) -> list[dict[str, Any]]:
    """Aplica E1–E6 sobre todos os registros e devolve as violações."""
    violations: list[dict[str, Any]] = []

    def add(code: str, record: dict[str, Any], detail: str) -> None:
        if code in ignore:
            return
        violations.append({
            "check": code,
            "label": CHECK_LABELS[code],
            "agent": record["agent"],
            "path": record["path"],
            "detail": detail,
        })

    for record in registry.load():
        # Sub-skills não têm identidade de execução própria.
        if not record["dispatchable"]:
            continue

        if not record["has_track"]:
            add("E4", record, "nenhum bloco `pipeline_observer.py … track` encontrado")
            # Sem bloco não há o que comparar em E1–E3.
            if not record["version"]:
                add("E5", record, "frontmatter sem `version:`")
            continue

        if record["track_agent"] and record["track_agent"] != record["agent"]:
            add("E1", record,
                f"bloco reporta `{record['track_agent']}`, frontmatter é `{record['agent']}`")

        expected_phase = record["phase"]
        if record["track_phase"] is not None and record["track_phase"] != expected_phase:
            add("E2", record,
                f"bloco reporta `{record['track_phase'] or '(vazio)'}`, "
                f"módulo `{record['module']}` é `{expected_phase or '(transversal)'}`")

        if not record["version"]:
            add("E5", record, "frontmatter sem `version:`")
        elif record["track_version"] and record["track_version"] != record["version"]:
            add("E3", record,
                f"bloco reporta `{record['track_version']}`, frontmatter é `{record['version']}`")

    for agent, paths in registry.duplicates().items():
        add("E6", {"agent": agent, "path": paths[0]}, " · ".join(paths))

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="verify_agent_observability.py",
        description="Verifica a consistência do auto-reporte de observabilidade dos agentes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Verificações:\n"
            + "".join(f"  {code}  {label}\n" for code, label in CHECK_LABELS.items())
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emite as violações em JSON")
    parser.add_argument("--agent", help="Restringe a um agent_id")
    parser.add_argument("--ignore", action="append", default=[], metavar="Ex",
                        help="Ignora uma verificação (repetível), ex: --ignore E5")
    args = parser.parse_args()

    registry = _load_registry()
    if registry is None or not registry.load():
        print(f"❌ não foi possível carregar o registro em {_REGISTRY_PATH}", file=sys.stderr)
        sys.exit(2)

    ignore = {code.upper() for code in args.ignore}
    violations = collect_violations(registry, ignore)
    if args.agent:
        violations = [v for v in violations if v["agent"] == args.agent]

    total_agents = len([r for r in registry.load() if r["dispatchable"]])

    if args.json:
        print(json.dumps({
            "agents_checked": total_agents,
            "violations": len(violations),
            "ignored_checks": sorted(ignore),
            "items": violations,
        }, indent=2, ensure_ascii=False))
        sys.exit(1 if violations else 0)

    print(f"🔎 Consistência de observabilidade :: {total_agents} agentes despacháveis")
    if not violations:
        print("   ✅ nenhuma violação")
        sys.exit(0)

    by_check: dict[str, list[dict[str, Any]]] = {}
    for violation in violations:
        by_check.setdefault(violation["check"], []).append(violation)

    for code in sorted(by_check):
        items = by_check[code]
        print(f"\n   ❌ {code} — {CHECK_LABELS[code]} ({len(items)})")
        for item in items:
            print(f"      {item['agent']:<40} {item['detail']}")
            print(f"      {'':<40} {item['path']}")

    print(f"\n   total: {len(violations)} violações")
    sys.exit(1)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
