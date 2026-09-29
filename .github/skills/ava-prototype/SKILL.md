---
name: ava-prototype
description: "Gera protótipo HTML navegável do sistema TO-BE com UX heurísticas Nielsen-Norman, validação de formulários e demo script."
---

Determine o PROJECT_NAME antes de executar:

1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Opcionalmente, se disponível, leia também:
`projects/{PROJECT_NAME}/outputs/asis/docs/functional-requirements.md`
(usado para enriquecer labels e validações com terminologia do negócio)

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md`
