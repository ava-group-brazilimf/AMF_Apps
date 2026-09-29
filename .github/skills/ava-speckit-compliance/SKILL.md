---
name: ava-speckit-compliance
description: "Audita specs, planos e tasks contra a constituição do projeto e emite veredito por princípio, com evidência. Roda depois dos checks determinísticos, nunca no lugar deles."
---

Determine o PROJECT_NAME antes de executar:

1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

O que já é verificado por código NÃO é escopo deste agente. Rode antes, e não repita:
`python -m src.shared.checks --project {PROJECT_NAME} --suite speckit_traceability`
`python -m src.shared.checks --project {PROJECT_NAME} --suite prototype_coverage`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/speckit/agents/compliance-agent.md`
