---
name: ava-tobe-architecture-technical
description: "Stack técnica TO-BE: NuGet packages, solution structure, quality gates."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia os ADRs gerados na Fase 0 (decisões vinculantes para seleção de pacotes):
`docs/decisions/ADR-001-greenfield-rewrite.md`
`docs/decisions/ADR-002-database.md`
`docs/decisions/ADR-003-security.md`
`docs/decisions/ADR-004-backend.md`
`docs/decisions/ADR-005-frontend.md`
`docs/decisions/ADR-006-integration.md`
`docs/decisions/ADR-007-observability.md`
`docs/decisions/ADR-008-audit-log.md`

Leia as seções de referência técnica de:
`projects/{PROJECT_NAME}/context/project-config.yaml`
→ Seções obrigatórias: `tobe_stack`, `architecture_patterns`, `solution_layers`, `persistence`, `auth`, `observability`, `infrastructure`, `quality_gates`, `tobe_resilience`, `tobe_messaging`, `tobe_api`, `tobe_compliance`
Esses parâmetros guiam a seleção de packages, estrutura de solução e quality gates — o agente NÃO deve usar thresholds fixos internos.

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/tobe-architecture/agents/architecture-technical-tobe.md`
