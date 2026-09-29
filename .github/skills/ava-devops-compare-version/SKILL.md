---
name: ava-devops-compare-version
description: "Compara AS-IS × TO-BE para aprovação de wave — execução simultânea com golden dataset, score de paridade por bounded context, métricas, checklist go/no-go e sign-offs."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/devops-agents/agents/compare-version-agent.md`

Utilize os seguintes templates e schemas:
- Template de relatório: `src/shared/templates/reports/wave-comparison-report-template.md`
- Checklist Go/No-Go: `src/shared/checklists/wave-gonogo-checklist.md`
- Schema de validação: `src/shared/schemas/wave-comparison.schema.json`
- Schema wave-approval: `src/shared/schemas/wave-approval.schema.json`

Leia os thresholds configurados em:
`projects/{PROJECT_NAME}/context/project-config.yaml` → bloco `wave_approval.thresholds`

Golden dataset (fonte primária de payloads para execução simultânea):
`projects/{PROJECT_NAME}/outputs/qa/golden-dataset.json`

Ativa com: "comparar versões", "equivalência funcional", "compare legacy vs migrated",
"parity test", "version comparison", "wave approval", "go/no-go",
"comparação AS-IS TO-BE", "golden dataset", "parity score", "score por bounded context",
"parity-test-report"
