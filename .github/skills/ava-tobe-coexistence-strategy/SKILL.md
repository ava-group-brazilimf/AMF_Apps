---
name: ava-tobe-coexistence-strategy
description: "Estratégia de coexistência AS-IS ↔ TO-BE com classificação de BCs em zonas de migração (Z1/Z2/Z3), catálogo de feature flags, diretivas de data sync, protocolo de graduação (0%→100%) e protocolo de decommission por BC."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/tobe-architecture/agents/coexistence-strategy-tobe.md`
