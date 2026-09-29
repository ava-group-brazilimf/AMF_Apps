#!/usr/bin/env python3
"""
verify_wave_plan.py — Gate externo de integridade do wave-plan.md

Valida que o artefato outputs/tobe/docs/wave-plan.md foi gerado corretamente
pelo agente ava-tobe-migration-plan na Fase 4 do orquestrador TO-BE.

Uso:
  python src/shared/utils/verify_wave_plan.py --project <project_name>

Exit codes:
  0 = PASS — wave-plan.md existe e atende aos critérios obrigatórios.
  1 = FAIL — wave-plan.md ausente, vazio ou viola critérios de integridade.
"""

import argparse
import json
import re
import sys
from pathlib import Path

WAVE_PLAN_SECTIONS = (
    "Resumo Executivo",
    "Composição de Bounded Contexts",
    "T-Shirt Sizing por Wave",
    "Esforço Estimado",
    "Squad e Responsável",
    "Dependências",
    "Critérios de Aceite Quantitativos",
    "Go/No-Go Checklist",
    "Rollback Strategy",
    "Escopo de User Stories",
)

EXPECTED_WAVE_TYPES = {"W0", "W1", "W2", "W3", "W4"}

# Força UTF-8 no Windows — ver comentário equivalente em verify_tobe_bc_gate.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ancorado no arquivo, não no cwd: um path relativo resolve contra o diretório
# corrente e, num segundo checkout do repo sem aquele projeto, reporta ausente
# um artefato que existe. Foi essa classe de falso negativo que derrubou a F2
# em MeuERP-002 (ver tobe-architecture/utils/artifact_gate_tobe.py).
_REPO_ROOT = Path(__file__).resolve().parents[3]


def fail(message: str, details: list[str] | None = None) -> int:
    print(f"[FAIL] {message}")
    if details:
        for line in details:
            print(f"       - {line}")
    return 1


def pass_ok(message: str) -> None:
    print(f"[PASS] {message}")


def get_outputs_root(project_name: str) -> Path:
    # Ancorado no arquivo, não no cwd — ver comentário em `_REPO_ROOT`.
    return _REPO_ROOT / "projects" / project_name / "outputs" / "tobe"


def validate_wave_plan(project_name: str) -> int:
    outputs_root = get_outputs_root(project_name)
    wave_plan_path = outputs_root / "docs/wave-plan.md"
    wave_model_path = outputs_root / "migration/wave-model.json"

    if not wave_plan_path.exists():
        return fail(
            f"wave-plan.md ausente: {wave_plan_path}",
            ["Execute a Fase 4 do orquestrador TO-BE (ava-tobe-migration-plan sem trigger)."],
        )

    if wave_plan_path.stat().st_size == 0:
        return fail(f"wave-plan.md existe mas está vazio: {wave_plan_path}")

    content = wave_plan_path.read_text(encoding="utf-8")

    issues: list[str] = []

    # 1. Verificar presença de exatamente 5 waves W0..W4
    wave_headers = re.findall(r"^##\s+(W\d)\s*[\-–—]\s*", content, re.MULTILINE)
    waves_found = sorted(set([h for h in wave_headers if h in EXPECTED_WAVE_TYPES]))
    if waves_found != sorted(EXPECTED_WAVE_TYPES):
        issues.append(f"Esperava headers W0..W4, encontrados: {waves_found}")

    # 2. Verificar seções obrigatórias (ao menos 8 das 10, sendo Resumo Executivo e Go/No-Go obrigatórias)
    missing_sections = [sec for sec in WAVE_PLAN_SECTIONS if sec not in content]
    hard_sections = ("Resumo Executivo", "Go/No-Go Checklist")
    missing_hard = [sec for sec in hard_sections if sec not in content]
    if missing_hard:
        issues.append(f"Seções obrigatórias ausentes: {missing_hard}")
    elif missing_sections:
        issues.append(f"Seções recomendadas ausentes: {missing_sections}")

    # 3. Verificar bloco Mermaid Gantt na seção Cronograma Estimado
    gantt_blocks = re.findall(r"```mermaid\s*\n\s*gantt", content, re.IGNORECASE)
    if len(gantt_blocks) == 0:
        issues.append("Bloco 'gantt' Mermaid não encontrado em 'Cronograma Estimado'")

    # 4. Verificar diagrama de dependências entre waves
    if "Mapa de Dependências entre Waves" not in content:
        issues.append("Seção 'Mapa de Dependências entre Waves' ausente")
    flowchart_blocks = re.findall(r"```mermaid\s*\n\s*flowchart", content, re.IGNORECASE)
    if len(flowchart_blocks) == 0:
        issues.append("Bloco 'flowchart' Mermaid não encontrado no mapa de dependências")

    # 5. Consistência com wave-model.json (SSoT)
    if wave_model_path.exists():
        try:
            wave_model = json.loads(wave_model_path.read_text(encoding="utf-8"))
            model_waves = wave_model.get("waves", [])
            model_wave_names = {f"W{w.get('wave_number', '')}" for w in model_waves}
            if model_wave_names != EXPECTED_WAVE_TYPES:
                issues.append(f"wave-model.json não contém exatamente 5 waves W0..W4: {model_wave_names}")
            else:
                for w in model_waves:
                    w_name = f"W{w.get('wave_number', '')}"
                    # aceita nomes com hífen, em-dash, en-dash e variações de espaço
                    pattern = rf"^##\s+{re.escape(w_name)}\s*[\-–—]\s*{re.escape(w.get('wave_name', '').replace(w_name + ' — ', '').replace(w_name + ' - ', ''))}"
                    if w.get("wave_name") and not re.search(pattern, content, re.MULTILINE):
                        # fallback: apenas verificar se nome da wave aparece após header W{N}
                        section = re.search(
                            rf"^##\s+{re.escape(w_name)}\b.*$",
                            content,
                            re.MULTILINE,
                        )
                        if not section:
                            issues.append(f"Header da wave {w_name} não encontrado")
        except json.JSONDecodeError as exc:
            issues.append(f"wave-model.json não é JSON válido: {exc}")
    else:
        issues.append(f"wave-model.json ausente: {wave_model_path}")

    # 6. Verificar presença de tabela no Resumo Executivo
    if "Resumo Executivo" in content:
        summary_section_match = re.search(
            r"##\s+Resumo Executivo.*?(?=^##\s|\Z)",
            content,
            re.DOTALL | re.MULTILINE,
        )
        if summary_section_match:
            summary_section = summary_section_match.group(0)
            if "|---|" not in summary_section:
                issues.append("Resumo Executivo não contém tabela markdown")
        else:
            issues.append("Não foi possível extrair seção 'Resumo Executivo'")

    # 7. Verificar Go/No-Go checklist por wave
    for w in EXPECTED_WAVE_TYPES:
        pattern = rf"{re.escape(w)}.*Go/No-Go|Go/No-Go.*{re.escape(w)}"
        if not re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Checklist Go/No-Go não encontrado para {w}")
            break

    if issues:
        return fail("wave-plan.md falhou na validação de integridade", issues)

    pass_ok(f"wave-plan.md validado com sucesso para o projeto '{project_name}'")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida integridade do wave-plan.md")
    parser.add_argument("--project", required=True, help="Nome do projeto em projects/{name}")
    args = parser.parse_args()
    return validate_wave_plan(args.project)


if __name__ == "__main__":
    sys.exit(main())
