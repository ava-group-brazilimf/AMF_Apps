---
name: ava-asis-business-rules-generator-agent
description: "Gera business-rules.md a partir de 10_business_rule_cases.json com curadoria semântica, bounded contexts, requisitos funcionais opcionais e processamento em lotes."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/asis-diagnostic/agents/business-rules-generator-agent.md`
