---
name: ava-qa-bridge-fastqa-tobe
description: "Bridge entre TO-BE e FastQA. Único gerador de cenários BDD Gherkin da esteira (Momento 1 — absorveu o extinto ava-qa-scenario-generator) e orquestrador de testes de API black-box, exploratórios live (POISED/VADER) e automação Playwright/TS (Momento 2) a partir dos Test Cases TO-BE consolidados.
"
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/qa-agents/agents/bridge-fastqa-tobe.md`
