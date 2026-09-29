---
name: ava-speckit-constitution
description: "Destila a arquitetura TO-BE aprovada no documento governante do projeto: princípios, padrões, NFRs, restrições e decisões obrigatórias rastreadas aos ADRs."
---

Determine o PROJECT_NAME antes de executar:

1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia as seções de referência arquitetural de:
`projects/{PROJECT_NAME}/context/project-config.yaml`
→ Seções relevantes: `tobe_stack`, `architecture_patterns`, `auth`, `tobe_compliance`, `overrides`
Versões de pacote e runtime saem de `src/shared/data/reference-architecture.yaml` — nunca de memória.

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/speckit/agents/constitution-agent.md`
