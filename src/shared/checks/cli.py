"""
cli.py — entry-point for the unified check runner.

Usage:
    python -m src.shared.checks --project Meu-ERP
    python -m src.shared.checks --project Meu-ERP --suite html
    python -m src.shared.checks --project Meu-ERP --suite mmd --verbose
    python -m src.shared.checks --project Meu-ERP --suite all
"""
import argparse
import sys

# Força UTF-8 no Windows — mesma guarda dos demais tools do repo.
# Sem ela, o console cp1252 estoura com UnicodeEncodeError em qualquer detalhe
# de check que contenha acento ou seta, e o runner morre no meio da suíte em vez
# de reportar o resultado.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m src.shared.checks",
        description="AVA Fabric — unified HTML + Mermaid output checker",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Project name (must match a folder under projects/)",
    )
    parser.add_argument(
        "--suite",
        default="all",
        choices=["all", "artifact_size", "html", "mmd", "mermaid_runtime", "nav", "gherkin", "tobe_db_policy", "tobe_db_type_target", "phase_status", "pipeline_consistency", "ftm_traceability", "evidence_capture", "speckit_traceability", "prototype_coverage", "speckit_frontend_integration"],
        help="Suite to run (default: all)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detail for passing checks too",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path to persist results as structured JSON "
             "(consumed by downstream agents/gates, not just the console)",
    )
    parser.add_argument(
        "--warn",
        action="store_true",
        help="reprovação vira aviso e o exit code continua 0 — a fase do "
             "pipeline não é bloqueada, mas o relatório sai igual",
    )
    args = parser.parse_args()

    from src.shared.checks import run_checks_detailed

    reporter = run_checks_detailed(args.project, suite=args.suite,
                                   verbose=args.verbose, json_out=args.json_out)
    # 0 = tudo passou · 3 = só lacunas de cobertura · 1 = falha estrutural.
    # O runner só oferece aceite de risco no código 3.
    #
    # `ok` não existia neste escopo: a linha era `if not ok and args.warn:` e
    # levantava `NameError` ANTES do `sys.exit(0)` — ou seja, `--warn` nunca
    # funcionou desde que foi escrito. O processo morria com exit 1 (código de
    # exceção não tratada), que é exatamente o que a flag existia para evitar.
    # Medido em `cadastro-funcionarios-04`: `speckit-dependency-checks` saía com
    # 1 apesar de `--warn` no DAG, e o dashboard mostrava "exit 1" numa etapa
    # que a fase declarava como aviso. O relatório de `--json-out` sobrevivia
    # porque é gravado antes desta linha — o que mascarou o defeito.
    ok = reporter.exit_code == 0
    if not ok and args.warn:
        # Exit 1 fazia o runner levantar RuntimeError e rotular a fase como
        # "⏭ pulado" — rótulo que mente sobre o que aconteceu: a suíte rodou e
        # reprovou. Com --warn a fase fica como executada e o achado vive no
        # relatório, que é onde ele é acionável.
        report = args.json_out or "(nenhum: passe --json-out para persistir)"
        print("\n" + "─" * 72)
        print(f"⚠️  CHECKS REPROVARAM — suíte '{args.suite}' em {args.project}")
        print("   A fase NÃO foi bloqueada (--warn). Os achados acima são")
        print("   lacunas de qualidade a corrigir antes de confiar na F4.")
        print(f"   Relatório estruturado: {report}")
        print("─" * 72)
        sys.exit(0)
    sys.exit(reporter.exit_code)


if __name__ == "__main__":
    main()
