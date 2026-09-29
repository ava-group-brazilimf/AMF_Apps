---
name: ava-tobe-spec
description: "Gera a especificação OpenAPI 3.1 completa por bounded context ANTES do codegen, definindo contratos de API (paths, schemas, operationIds, bearerAuth, servidores) que serão respeitados pelo coder-dotnet e validados por contract tests. Derivação 100% rastreável a partir de bounded-context-map.md — nunca inventa. Ativa com: 'gerar openapi spec por BC', 'OA-BC', 'contrato de API', 'design-first spec', 'api contract por bounded context'."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/tobe-architecture/agents/openapi-spec-tobe.md`
