---
name: ava-tobe-azure-infra-estimator
description: "Estima infraestrutura Azure TO-BE por ambiente (dev, staging, prod) com preços reais da Azure Retail Prices API. Gera SKU matrix, cost tables, TCO summary, concurrency report (CSV) e azure-provisioning-planV1.md sem valores monetários. Triggers: FR (full report) | RG | MS | SK | CC | AA | CA | TA | AP | UP"
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/tobe-architecture/agents/azure-infra-estimator-tobe.md`
