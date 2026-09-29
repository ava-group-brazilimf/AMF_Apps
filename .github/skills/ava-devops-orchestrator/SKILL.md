---
name: ava-devops-orchestrator
description: "Orquestra a fase DevOps em dois momentos: DP (DevOps Plan, após F2 TO-BE) define a estratégia de IaC, CI/CD e observabilidade e gera o esqueleto wave-1; DE (DevOps Execute, após F4 Stack) despacha os agentes DevOps para containerização, deploy e comparação de versão. Ativa com: 'iniciar devops', 'orquestrar devops', 'planejar devops', 'executar devops', 'trigger DP', 'trigger DE'."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/project-config.yaml`
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/devops-agents/agents/orchestrator-devops.md`
