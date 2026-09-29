---
name: ava-tobe-architecture-design
description: "Define arquitetura TO-BE: C4 blueprints, bounded contexts, APIs e DDD."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia as seções de referência arquitetural de:
`projects/{PROJECT_NAME}/context/project-config.yaml`
→ Seções obrigatórias: `tobe_stack`, `architecture_patterns`, `architecture_principles`, `solution_layers`, `persistence`, `auth`, `observability`, `infrastructure`, `quality_gates`, `tobe_api`, `tobe_resilience`, `tobe_messaging`, `tobe_migration`, `tobe_compliance`
Esses parâmetros são a fonte-de-verdade para TODO o design TO-BE — o agente NÃO deve usar valores hardcoded.

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/tobe-architecture/agents/architecture-design-tobe.md`
