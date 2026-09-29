#!/usr/bin/env python3
"""
AVA Fabric - Fallback Artifact Generator
Gera metrics.json e risk-register.json a partir dos relatórios Markdown existentes
quando os agents ava-asis-inventory ou ava-asis-gaps-risks não os produziram.

Uso:
    python generate_fallback_artifacts.py --type metrics --project database-comparer-examples
    python generate_fallback_artifacts.py --type risks --project Meu-ERP
    python generate_fallback_artifacts.py --type all --project database-comparer-examples
"""
import argparse
import json
import re
import yaml
from pathlib import Path
from datetime import datetime


def load_project_config(project_name: str) -> dict:
    """Carrega configuração do projeto"""
    config_path = Path(f"projects/{project_name}/context/project-config.yaml")
    if not config_path.exists():
        return {"project_name": project_name, "trace_id": "unknown"}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_metrics_json(project_name: str) -> Path:
    """
    Gera metrics.json a partir de master-report.md e inventory-report.md
    
    Extrai métricas via regex e glob quando JSONs estruturados não existem
    """
    print(f"\n🔧 Gerando metrics.json para {project_name}...")
    
    base_path = Path(f"projects/{project_name}/outputs/asis")
    master_report = base_path / "master-report.md"
    inventory_report = base_path / "inventory-report.md"
    config = load_project_config(project_name)
    
    # Ler relatórios
    master_text = master_report.read_text(encoding='utf-8') if master_report.exists() else ""
    inventory_text = inventory_report.read_text(encoding='utf-8') if inventory_report.exists() else ""
    combined = master_text + "\n" + inventory_text
    
    # Função auxiliar para extrair métricas
    def extract(pattern: str, default="N/D"):
        match = re.search(pattern, combined, re.IGNORECASE | re.MULTILINE)
        if match:
            try:
                return int(match.group(1))
            except:
                return match.group(1)
        return default
    
    # Extrair métricas
    metrics = {
        "trace_id": config.get("trace_id", "unknown"),
        "project": project_name,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "generated_by": "fallback_generator",
        "source": "master-report.md + inventory-report.md",
        "totals": {
            "loc_total": extract(r"(?:total.*loc|analyzed_loc)[:\s]+(\d+)"),
            "loc_pas": extract(r"pas.*loc[:\s]+(\d+)", 0),
            "loc_dfm": extract(r"dfm.*loc[:\s]+(\d+)", 0),
            "loc_dpr": extract(r"dpr.*loc[:\s]+(\d+)", 0),
            "loc_sql": extract(r"sql.*loc[:\s]+(\d+)", 0),
            "files_total": extract(r"files.*total[:\s]+(\d+)"),
            "files_pas": extract(r"(?:pas files|\.pas)[:\s]+(\d+)", 0),
            "files_dfm": extract(r"(?:dfm files|\.dfm)[:\s]+(\d+)", 0),
            "files_dpr": extract(r"(?:dpr files|\.dpr)[:\s]+(\d+)", 0),
            "files_sql": extract(r"(?:sql files|\.sql)[:\s]+(\d+)", 0),
            "classes_form": extract(r"forms[:\s]+(\d+)"),
            "classes_datamodule": extract(r"datamodules?[:\s]+(\d+)", 0),
            "methods_total": extract(r"(?:methods|procedures|functions)[:\s]+(\d+)"),
            "modules": extract(r"modules[:\s]+(\d+)", 1),
            "layers": extract(r"layers[:\s]+(\d+)", 1)
        }
    }
    
    # Salvar
    output_path = base_path / "metrics.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ {output_path}")
    print(f"   📊 LOC Total: {metrics['totals']['loc_total']}")
    print(f"   📊 Files: {metrics['totals']['files_total']}")
    return output_path


def generate_risk_register_json(project_name: str) -> Path:
    """
    Gera risk-register.json a partir de gaps-risks-report.md e master-report.md
    
    Extrai tabela de riscos via regex
    """
    print(f"\n🔧 Gerando risk-register.json para {project_name}...")
    
    base_path = Path(f"projects/{project_name}/outputs/asis")
    gaps_report = base_path / "gaps-risks-report.md"
    master_report = base_path / "master-report.md"
    security_report = base_path / "security-map.md"
    config = load_project_config(project_name)
    
    # Ler relatórios
    gaps_text = gaps_report.read_text(encoding='utf-8') if gaps_report.exists() else ""
    master_text = master_report.read_text(encoding='utf-8') if master_report.exists() else ""
    security_text = security_report.read_text(encoding='utf-8') if security_report.exists() else ""
    combined = gaps_text + "\n" + master_text + "\n" + security_text
    
    risks = []
    
    # Tentar extrair tabela estruturada de riscos
    # Formato: | R-001 | Categoria | Descrição | Prob | Imp | Score | Mitigação |
    table_pattern = r"\|\s*(R-\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*(\d+)\s*\|\s*([^|]+)\s*\|"
    
    prob_map = {"alta": 5, "high": 5, "média": 3, "medium": 3, "baixa": 1, "low": 1, "5": 5, "4": 4, "3": 3, "2": 2, "1": 1}
    
    for match in re.finditer(table_pattern, combined, re.IGNORECASE):
        risk_id, categoria, descricao, prob_text, imp_text, score_text, mitigacao = match.groups()
        
        prob = prob_map.get(prob_text.strip().lower(), 3)
        impacto = prob_map.get(imp_text.strip().lower(), 3)
        score = int(score_text.strip())
        
        # Classificar nível
        if score >= 20:
            nivel = "P0"
        elif score >= 12:
            nivel = "P1"
        elif score >= 6:
            nivel = "P2"
        else:
            nivel = "P3"
        
        risks.append({
            "id": risk_id.strip(),
            "categoria": categoria.strip(),
            "descricao": descricao.strip(),
            "probabilidade": prob,
            "impacto": impacto,
            "score": score,
            "nivel": nivel,
            "mitigacao": mitigacao.strip()
        })
    
    # Fallback: extrair de seções de risco no master-report
    if len(risks) == 0:
        print("   ⚠️ Tabela de riscos não encontrada — extraindo do texto...")
        
        # Procurar seções de risco
        risk_sections = re.findall(
            r"(?:Risk|Risco|RISK)[:\s]+([^\n]{10,200})",
            combined,
            re.IGNORECASE
        )
        
        for i, risk_desc in enumerate(risk_sections[:15], 1):
            if len(risk_desc.strip()) > 10:  # Evitar matches vazios
                risks.append({
                    "id": f"R-{i:03d}",
                    "categoria": "Geral",
                    "descricao": risk_desc.strip(),
                    "probabilidade": 3,
                    "impacto": 3,
                    "score": 9,
                    "nivel": "P2",
                    "mitigacao": "A definir"
                })
    
    # Build JSON
    risk_register = {
        "trace_id": config.get("trace_id", "unknown"),
        "project": project_name,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "generated_by": "fallback_generator",
        "source": "gaps-risks-report.md + master-report.md + security-map.md",
        "risks": risks
    }
    
    # Salvar
    output_path = base_path / "risk-register.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(risk_register, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ {output_path}")
    print(f"   🔴 Riscos extraídos: {len(risks)}")
    if risks:
        p0_count = sum(1 for r in risks if r['nivel'] == 'P0')
        print(f"   🔴 Críticos (P0): {p0_count}")
    
    return output_path

def generate_gap_register_json(project_name: str) -> Path:
    """
    Gera gap-register.json a partir de gap-list-report.md e gap-analysis-summary.md.

    Tenta extrair linhas da tabela de GAPs; em caso de falha gera array vazio válido.
    Schema: [{id, category, title, artifact, description, impact, complexity, score}]
    """
    print(f"\n🔧 Gerando gap-register.json para {project_name}...")

    base_path = Path(f"projects/{project_name}/outputs/asis")
    gap_report  = base_path / "gap-list-report.md"
    gap_summary = base_path / "gap-analysis-summary.md"

    gap_text    = gap_report.read_text(encoding='utf-8')  if gap_report.exists()  else ""
    summary_text= gap_summary.read_text(encoding='utf-8') if gap_summary.exists() else ""
    combined    = gap_text + "\n" + summary_text

    gaps = []

    # Formato esperado: | GAP-001 | EXT | CRITICAL | 5 | Título | artefato.md | Impacto |
    table_pattern = (
        r"\|\s*(GAP-\d+)\s*\|\s*([A-Z\-]+)\s*\|\s*(CRITICAL|HIGH|MEDIUM|LOW|TRIVIAL)\s*\|"
        r"\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|"
    )

    CATEGORY_LABELS = {
        "EXT": "Extensão 3rd-party", "COM": "COM/ActiveX", "DAT": "Acesso a dados",
        "ORM": "ORM/LINQ", "DB": "Banco de dados", "FWK": "Framework",
        "EVT": "Eventos/Mensageria", "THR": "Threading", "STR": "Streaming",
        "SEC": "Segurança", "RPT": "Relatórios", "MSG": "Mensageria",
        "INT": "Integração", "CFG": "Configuração", "TXN": "Transações",
        "STT": "Estado/Session", "ARC": "Arquitetura", "DEP": "Dependências",
        "PLT": "Plataforma", "LIC": "Licenciamento", "TST": "Testes",
        "DOC": "Documentação", "DAT-MIG": "Migração de dados",
    }

    SCORE_MAP = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "TRIVIAL": 1}

    for match in re.finditer(table_pattern, combined, re.IGNORECASE):
        gap_id, category, complexity, score_raw, title, artifact, impact = match.groups()
        complexity = complexity.strip().upper()
        category   = category.strip().upper()
        score = int(score_raw.strip()) if score_raw.strip().isdigit() else SCORE_MAP.get(complexity, 3)
        gaps.append({
            "id":            gap_id.strip(),
            "category":      category,
            "categoryLabel": CATEGORY_LABELS.get(category, category),
            "complexity":    complexity,
            "score":         score,
            "title":         title.strip(),
            "artifact":      artifact.strip(),
            "impact":        impact.strip(),
            "description":   "",
        })

    mrs = sum(g["score"] for g in gaps)
    gap_register = {
        "generated_at": "",
        "project":      project_name,
        "agent":        "ava-asis-gap-migration-analyzer",
        "mrs":          mrs,
        "gap_count":    len(gaps),
        "items":        gaps,
    }

    output_path = base_path / "gap-register.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(gap_register, f, indent=2, ensure_ascii=False)

    print(f"   ✅ {output_path}")
    print(f"   🔵 GAPs extraídos: {len(gaps)}  |  MRS: {mrs}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Gera artefatos de fallback para summary HTML")
    parser.add_argument("--type", choices=["metrics", "risks", "all"], required=True,
                        help="Tipo de artefato a gerar")
    parser.add_argument("--project", required=True,
                        help="Nome do projeto (ex: database-comparer-examples)")
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"  AVA Fabric Fallback Generator")
    print(f"  Project: {args.project}")
    print(f"  Type: {args.type}")
    print(f"{'='*60}")
    
    if args.type in ["metrics", "all"]:
        generate_metrics_json(args.project)
    
    if args.type in ["risks", "all"]:
        generate_risk_register_json(args.project)

    if args.type in ["gaps", "all"]:
        generate_gap_register_json(args.project)
        
    print(f"\n{'='*60}")
    print(f"  ✅ Fallback generation completed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
