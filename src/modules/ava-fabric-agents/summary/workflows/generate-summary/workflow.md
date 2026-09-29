---
name: generate-summary
display_name: "Gerar AVA Fabric Summary"
description: |
  Workflow completo de geração do relatório HTML consolidado da AVA Fabric.
  Descobre artefatos, extrai dados, constrói o HTML e valida o resultado.
version: "1.0.0"
agent: ava-summary
standalone: true
triggers:
  - "GS" # generate-summary: todos os outputs disponíveis
  - "SAS" # summary AS-IS apenas
  - "STO" # summary TO-BE apenas
  - "SI" # independente, custom path
---

# Workflow — Generate Summary

## Visão Geral

```
[Inputs disponíveis em projects/{project_name}/outputs/]
          ↓
     Step 01 — Contexto & Descoberta
          ↓
     Step 02 — Extração de Dados
          ↓
     Step 03 — Construção do HTML
          ↓
     Step 04 — Validação & Saída
          ↓
[projects/{project_name}/outputs/summary/AVA-FABRIC-SUMMARY-{PROJECT}-{DATE}.html]
```

## Entradas do Workflow

| Campo               | Obrigatório | Default                            |
| ------------------- | ----------- | ---------------------------------- |
| `outputs_base_path` | Não         | `projects/{project_name}/outputs/` |
| `project_name`      | Não         | lido de `project-config.yaml`      |
| `language`          | Não         | `en`                               |
| `include_diagrams`  | Não         | `true`                             |
| `phases_to_include` | Não         | todas disponíveis                  |

## Saídas do Workflow

| Arquivo                                                             | Conteúdo                       |
| ------------------------------------------------------------------- | ------------------------------ |
| `projects/{project_name}/outputs/summary/AVA-FABRIC-SUMMARY-*.html` | Relatório HTML interativo      |
| `projects/{project_name}/outputs/summary/index.md`                  | Índice com link e estatísticas |
| `projects/{project_name}/outputs/summary/summary-data.json`         | Dados extraídos em JSON        |

## Steps

Seguir os steps em ordem:

1. `workflows/generate-summary/steps/step-01-discover.md`
2. `workflows/generate-summary/steps/step-02-extract.md`
3. `workflows/generate-summary/steps/step-03-build-html.md`
4. `workflows/generate-summary/steps/step-04-validate-deliver.md`

## Pre-Step: Garantir Artefatos Críticos (para trigger GS)

**Quando**: Sempre que `trigger == "GS"` (generate-summary completo)

**Objetivo**: Garantir que `metrics.json` e `risk-register.json` existem antes de extrair dados

**Ações**:

```python
# Verificar artefatos críticos
critical_artifacts = [
    f"projects/{project_name}/outputs/asis/metrics.json",
    f"projects/{project_name}/outputs/asis/risk-register.json"
]

missing = []
for artifact_path in critical_artifacts:
    if not Path(artifact_path).exists():
        missing.append(artifact_path)

# Gerar fallbacks se necessário
if missing:
    print(f"⚠️ {len(missing)} artefatos críticos ausentes — gerando fallbacks...")

    # Chamar script de fallback
    import subprocess

    if "metrics.json" in str(missing):
        subprocess.run([
            "python",
            "src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_fallback_artifacts.py",
            "--type", "metrics",
            "--project", project_name
        ])

    if "risk-register.json" in str(missing):
        subprocess.run([
            "python",
            "src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_fallback_artifacts.py",
            "--type", "risks",
            "--project", project_name
        ])

    print(f"✅ Fallbacks gerados — prosseguindo para Step 01...")
```
