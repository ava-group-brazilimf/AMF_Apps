#!/usr/bin/env python3
"""
AVA Fabric - Delphi AST Extraction Tool (Legacy Compatibility Shim)
====================================================================
Este módulo existe apenas para compatibilidade com scripts e documentação que
ainda invocam ``run_delphi_ast_analysis.py``. Todo o trabalho real agora é
feito pelo roteador ``run_ast_analysis.py``.

Uso:
    python run_delphi_ast_analysis.py --project Meu-ERP \
        --ava-analyzer-path "C:\\path\\to\\ava-fabric-delphi-analyzer"

    # ou configurando uma vez por ambiente:
    set AVA_DELPHI_ANALYZER_HOME=C:\\path\\to\\ava-fabric-delphi-analyzer
    python run_delphi_ast_analysis.py --project Meu-ERP
"""
import argparse
import os
import sys
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _load_config(project_name: str) -> dict:
    config_path = Path(f"projects/{project_name}/context/project-config.yaml")
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_analyzer_path(cli_arg: str | None) -> Path | None:
    raw = cli_arg or os.environ.get("AVA_DELPHI_ANALYZER_HOME")
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_absolute() else p.resolve()


def run_delphi_ast_analysis(
    project_name: str,
    analyzer_path: Path,
    *,
    skip_module_partitioner: bool = False,
    skip_sql_ir_generator: bool = False,
    skip_business_rules_catalog: bool = False,
) -> int:
    """Executa a extração Delphi via ``run_ast_analysis.py`` e gera catálogo de regras.

    Os parâmetros ``skip_module_partitioner`` e ``skip_sql_ir_generator`` são
    mantidos na assinatura apenas por compatibilidade: o roteador executa esses
    passos automaticamente. O parâmetro ``skip_business_rules_catalog`` continua
    funcional.
    """
    config = _load_config(project_name)
    legacy_technology = config.get("legacy_technology", "")
    if legacy_technology and legacy_technology != "delphi":
        print(f"   ⏭️  legacy_technology='{legacy_technology}' (não é 'delphi') — pulando.")
        return 0

    if skip_module_partitioner:
        print("   ⏭️  --skip-module-partitioner ativo — mantido apenas para compatibilidade.")
    if skip_sql_ir_generator:
        print("   ⏭️  --skip-sql-ir-generator ativo — mantido apenas para compatibilidade.")

    os.environ["AVA_DELPHI_ANALYZER_HOME"] = str(analyzer_path)

    from run_ast_analysis import run_ast_analysis

    rc = run_ast_analysis(
        project_name=project_name,
        cli_language="delphi",
        mirror_legacy_delphi=True,
    )
    if rc != 0:
        return rc

    if not skip_business_rules_catalog:
        try:
            from business_rules_catalog_generator import BusinessRulesCatalogGenerator
            gen = BusinessRulesCatalogGenerator(project_name)
            ret = gen.run()
            if ret != 0:
                print(f"   ⚠️  BusinessRulesCatalog retornou {ret} — verificar paridade de regras.")
        except Exception as exc:
            print(f"   ⚠️  BusinessRulesCatalog falhou: {exc} — prosseguindo sem catálogo.")
    else:
        print("   ⏭️  --skip-business-rules-catalog ativo — pulando catálogo de regras.")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="(Compatibilidade) Delega para run_ast_analysis.py --language delphi"
    )
    ap.add_argument("--project", required=True, help="Nome do projeto (ex: Meu-ERP)")
    ap.add_argument("--ava-analyzer-path", default=None,
                    help="Caminho do ava-fabric-delphi-analyzer (ou setar "
                         "AVA_DELPHI_ANALYZER_HOME)")
    ap.add_argument("--skip-module-partitioner", action="store_true",
                    help="Ignorado — mantido apenas para compatibilidade")
    ap.add_argument("--skip-sql-ir-generator", action="store_true",
                    help="Ignorado — mantido apenas para compatibilidade")
    ap.add_argument("--skip-business-rules-catalog", action="store_true",
                    help="Pula a geração do business-rules-catalog.json (bypass de emergência)")
    a = ap.parse_args()

    config = _load_config(a.project)
    legacy_technology = config.get("legacy_technology", "")
    if legacy_technology and legacy_technology != "delphi":
        print(f"   ⏭️  legacy_technology='{legacy_technology}' (não é 'delphi') — pulando.")
        return 0

    analyzer_path = _resolve_analyzer_path(a.ava_analyzer_path)
    if analyzer_path is None:
        print("❌ Caminho do ava-fabric-delphi-analyzer não configurado. Use "
              "--ava-analyzer-path ou defina a variável de ambiente "
              "AVA_DELPHI_ANALYZER_HOME.", file=sys.stderr)
        return 1
    if not analyzer_path.exists():
        print(f"❌ Caminho não existe: {analyzer_path}", file=sys.stderr)
        return 1

    return run_delphi_ast_analysis(
        a.project, analyzer_path,
        skip_module_partitioner=a.skip_module_partitioner,
        skip_sql_ir_generator=a.skip_sql_ir_generator,
        skip_business_rules_catalog=a.skip_business_rules_catalog,
    )


if __name__ == "__main__":
    sys.exit(main())
