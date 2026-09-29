#!/usr/bin/env python3
"""
verify_tobe_prereqs_gate.py — Gate executável de pré-requisitos TO-BE para agentes downstream.

Verifica em disco que os artefatos obrigatórios da fase F2 (TO-BE) existem e têm
tamanho > 0 antes que agentes downstream (stack-orchestrator, coder-dotnet, etc.) sejam
invocados.

Segue o mesmo padrão de verify_tobe_bc_gate.py (gate inter-trigger BC→TD da Fase 1).

Artefatos verificados:
  - outputs/tobe/docs/architecture-blueprint.md   (sempre obrigatório)
  - outputs/tobe/docs/security-architecture.md    (sempre obrigatório)
  - outputs/tobe/docs/spec/{BC}-spec.md           (apenas se cqrs == true, para cada BC)

Detecção automática de CQRS:
  Lida de projects/{project}/context/project-config.yaml com a seguinte ordem de prioridade:
    1. overrides.architecture_patterns.cqrs
    2. tobe_stack.architecture_patterns.cqrs  (ou architecture_patterns.cqrs)
  Retorna False se o arquivo estiver ausente ou nenhuma chave cqrs for encontrada.

Detecção automática de BCs:
  Lida de projects/{project}/outputs/tobe/docs/bounded-context-map.md
  Reconhece cabeçalhos no padrão produzido por architecture-design-tobe:
    ### BC-01 — CustomerSupplier
    ### BC-1 — AccountsPayable
    ## BC-02: BillingPayment

Uso:
    # Execução padrão — auto-detecta CQRS e BCs a partir dos artefatos do projeto
    python src/shared/utils/verify_tobe_prereqs_gate.py --project Meu-ERP

    # Forçar verificação de spec files (sobrepõe project-config.yaml)
    python src/shared/utils/verify_tobe_prereqs_gate.py --project Meu-ERP --cqrs

    # Desabilitar verificação de spec files (sobrepõe project-config.yaml)
    python src/shared/utils/verify_tobe_prereqs_gate.py --project Meu-ERP --no-cqrs

    # Informar BCs manualmente (bypassa auto-detecção de bounded-context-map.md)
    python src/shared/utils/verify_tobe_prereqs_gate.py --project Meu-ERP --bcs bc01-customer-supplier,bc02-accounts-payable

Exit codes:
    0 = PASS — todos os artefatos obrigatórios presentes e com tamanho > 0
    1 = FAIL — um ou mais artefatos ausentes ou vazios
"""

import argparse
import re
import sys
from pathlib import Path

# Força UTF-8 no Windows — ver comentário equivalente em verify_tobe_bc_gate.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ancorado no arquivo, não no cwd: um path relativo resolve contra o diretório
# corrente e, num segundo checkout do repo sem aquele projeto, reporta ausente
# um artefato que existe. Foi essa classe de falso negativo que derrubou a F2
# em MeuERP-002 (ver tobe-architecture/utils/artifact_gate_tobe.py).
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _camel_to_kebab(name: str) -> str:
    """Convert CamelCase or PascalCase to kebab-case.

    Examples:
        CustomerSupplier  → customer-supplier
        AccountsPayable   → accounts-payable
        APIGateway        → api-gateway
    """
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", s)
    return s.lower()


def _read_bool_flag(config_path: Path, flag_name: str) -> bool | None:
    """Read a boolean flag from project-config.yaml.

    Resolution order (highest priority first):
      1. overrides.{flag_name}
      2. any occurrence of {flag_name}: true/false in the file
    Returns None if the file is absent or the flag is not found.
    """
    if not config_path.exists():
        return None
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Priority 1 — overrides block
    override_match = re.search(
        r"^overrides\s*:\s*\n((?:[ \t]+.*\n)*)",
        text,
        re.MULTILINE,
    )
    if override_match:
        flag_in_override = re.search(
            rf"{re.escape(flag_name)}\s*:\s*(true|false)",
            override_match.group(1),
        )
        if flag_in_override:
            return flag_in_override.group(1).lower() == "true"

    # Priority 2 — any occurrence in the file (last occurrence = most specific block)
    all_matches = re.findall(rf"{re.escape(flag_name)}\s*:\s*(true|false)", text)
    if all_matches:
        return all_matches[-1].lower() == "true"

    return None


def _read_cqrs_flag(config_path: Path) -> bool:
    """Read the effective CQRS flag from project-config.yaml.

    Resolution order (highest priority first):
      1. overrides.architecture_patterns.cqrs
      2. any cqrs key in the file (tobe_stack.architecture_patterns.cqrs or
         architecture_patterns.cqrs)
    Returns False if the file is absent or no cqrs key is found.
    """
    return _read_bool_flag(config_path, "cqrs") or False


def _extract_bc_slugs(bc_map_path: Path) -> list[str]:
    """Extract BC slugs from bounded-context-map.md TO-BE.

    Recognises heading patterns produced by architecture-design-tobe:
      ### BC-01 — CustomerSupplier
      ### BC-1 — AccountsPayable
      ## BC-02: BillingPayment

    Returns slugs in the form ``bc01-customer-supplier``.
    """
    if not bc_map_path.exists():
        return []
    try:
        text = bc_map_path.read_text(encoding="utf-8")
    except OSError:
        return []

    bcs: list[str] = []
    seen: set[str] = set()

    pattern = re.compile(
        r"#{1,4}\s+BC[-_]?(\d+)\s*[—:\-]\s*([A-Za-z][A-Za-z0-9]*)",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        num = m.group(1).zfill(2)
        name = m.group(2)
        slug = f"bc{num}-{_camel_to_kebab(name)}"
        if slug not in seen:
            seen.add(slug)
            bcs.append(slug)

    return bcs


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gate executável: verifica pré-requisitos TO-BE (F2) antes de agentes downstream."
        )
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Nome do projeto (ex: Meu-ERP)",
    )

    cqrs_group = parser.add_mutually_exclusive_group()
    cqrs_group.add_argument(
        "--cqrs",
        action="store_true",
        default=False,
        help=(
            "Forçar verificação de spec/{BC}-spec.md para todos os BCs "
            "(sobrepõe project-config.yaml)."
        ),
    )
    cqrs_group.add_argument(
        "--no-cqrs",
        dest="no_cqrs",
        action="store_true",
        default=False,
        help=(
            "Desabilitar verificação de spec/{BC}-spec.md "
            "(sobrepõe project-config.yaml)."
        ),
    )

    parser.add_argument(
        "--bcs",
        default=None,
        help=(
            "Lista de BCs separada por vírgulas para verificação de spec files "
            "(ex: bc01-customer-supplier,bc02-accounts-payable). "
            "Omitir para auto-detectar de bounded-context-map.md."
        ),
    )
    args = parser.parse_args()

    project_name = args.project
    project_root = _REPO_ROOT / "projects" / project_name
    tobe = project_root / "outputs" / "tobe"
    config_path = project_root / "context" / "project-config.yaml"
    bc_map_path = tobe / "docs" / "bounded-context-map.md"

    failures: list[str] = []

    print(f"[PREREQS-GATE] Verificando pré-requisitos TO-BE — projeto: {project_name}")
    print()

    # ── Artefatos fixos ───────────────────────────────────────────────────────
    fixed_artifacts = [
        (
            tobe / "docs" / "architecture-blueprint.md",
            "ava-tobe-architecture-design (trigger CB)",
        ),
        (
            tobe / "docs" / "security-architecture.md",
            "security-design-tobe (Fase 1.6)",
        ),
    ]

    security_enabled_tobe = _read_bool_flag(config_path, "security_enabled_tobe")
    if security_enabled_tobe is None:
        security_enabled_tobe = True  # default when flag is missing

    for artifact, producer in fixed_artifacts:
        if artifact.name == "security-architecture.md" and not security_enabled_tobe:
            if artifact.exists() and artifact.stat().st_size > 0:
                print(
                    f"  SKIP    : {artifact.name} — security_enabled_tobe=false; "
                    f"placeholder presente"
                )
            else:
                print(
                    f"  SKIP    : {artifact.name} — security_enabled_tobe=false; "
                    f"nenhum placeholder gerado (pipeline continua)"
                )
            continue

        if not artifact.exists():
            failures.append(
                f"  AUSENTE : {artifact}\n"
                f"            Produzido por: {producer}"
            )
        elif artifact.stat().st_size == 0:
            failures.append(
                f"  VAZIO   : {artifact}\n"
                f"            Produzido por: {producer}"
            )
        else:
            size_kb = artifact.stat().st_size / 1024
            print(f"  OK      : {artifact.name} ({size_kb:.1f} KB)")

    # ── Spec files por BC (apenas se CQRS habilitado) ─────────────────────────
    if args.no_cqrs:
        check_cqrs = False
    elif args.cqrs:
        check_cqrs = True
    else:
        check_cqrs = _read_cqrs_flag(config_path)

    if not check_cqrs:
        print(
            f"  SKIP    : spec files por BC "
            f"(cqrs não habilitado para projeto '{project_name}')"
        )
    else:
        # Resolve BC list
        if args.bcs:
            bcs = [bc.strip() for bc in args.bcs.split(",") if bc.strip()]
        else:
            bcs = _extract_bc_slugs(bc_map_path)

        if not bcs:
            failures.append(
                f"  AVISO   : CQRS habilitado mas nenhum BC detectado para verificar spec files.\n"
                f"            Certifique-se de que '{bc_map_path}' existe e contém cabeçalhos\n"
                f"            no padrão '### BC-NN — NomeDoBoundedContext', "
                f"ou passe --bcs manualmente."
            )
        else:
            for bc in bcs:
                spec = tobe / "docs" / "spec" / f"{bc}-spec.md"
                if not spec.exists():
                    failures.append(
                        f"  AUSENTE : {spec}\n"
                        f"            Produzido por: ava-tobe-user-journeys (CQRS ativo)"
                    )
                elif spec.stat().st_size == 0:
                    failures.append(
                        f"  VAZIO   : {spec}\n"
                        f"            Produzido por: ava-tobe-user-journeys (CQRS ativo)"
                    )
                else:
                    size_kb = spec.stat().st_size / 1024
                    print(f"  OK      : {spec.name} ({size_kb:.1f} KB)")

    # ── Resultado final ────────────────────────────────────────────────────────
    if failures:
        print()
        print("⛔ [PREREQS-GATE FAILED] Artefatos F2 TO-BE ausentes ou inválidos:")
        print()
        for f in failures:
            print(f)
        print()
        print("AÇÃO OBRIGATÓRIA:")
        print("  1. Identificar o agente responsável pelo artefato ausente (ver acima)")
        print("  2. Re-executar o agente responsável:")
        print("       architecture-blueprint.md  → @ava-tobe-architecture-design (trigger CB)")
        print("       security-architecture.md   → @security-design-tobe (Fase 1.6)")
        print("       spec/{BC}-spec.md           → @ava-tobe-user-journeys (CQRS ativo)")
        print("  3. Re-executar este script para confirmar resolução")
        print()
        print(
            f"BLOQUEIO: {len(failures)} verificação(ões) com falha — "
            "agentes downstream PROIBIDOS até resolução."
        )
        return 1

    print()
    print("✅ [PREREQS-GATE PASSED] Todos os pré-requisitos F2 TO-BE validados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
