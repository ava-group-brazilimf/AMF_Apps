---
name: ava-tobe-adr
description: "Materializa os 8 ADRs obrigatórios do projeto em formato Michael Nygard (Context / Decision / Consequences / Alternatives / Status). Fontes: shared-context.md + outputs/asis/docs/ + project-config.yaml."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`
`projects/{PROJECT_NAME}/context/project-config.yaml`

Leia também os artefatos AS-IS gerados pelo diagnóstico F1:
`projects/{PROJECT_NAME}/outputs/asis/docs/business-rules.md`
`projects/{PROJECT_NAME}/outputs/asis/docs/functional-requirements.md`
`projects/{PROJECT_NAME}/outputs/asis/docs/screen-navigation-map.md`
`projects/{PROJECT_NAME}/outputs/asis/docs/screen-rules.md`
`projects/{PROJECT_NAME}/outputs/asis/docs/value-chain.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/tobe-architecture/agents/adr-tobe.md`
