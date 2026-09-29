---
name: ava-deliverable-strategy-align
description: "Gera os materiais de preparação e o template de registro para a sessão de Strategy Align entre o PM e o Requestor, consolidando priorização de bounded contexts, alinhamento de integrações, dependências de infraestrutura, decisão de PILOT/POC e aprovação formal do pacote de migração."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/deliverables/agents/strategy-align-agent.md`
