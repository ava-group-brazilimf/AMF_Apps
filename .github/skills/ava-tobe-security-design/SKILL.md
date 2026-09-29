---
name: ava-tobe-security-design
description: "Fase 1.6 — Security Architecture TO-BE. Gera security-architecture.md (15 seções), mapeamento V-01..V-13, diagrama Mermaid flowchart TB e Draw.io. Implementa protocolo Z-curve de remediação controlado por skip_z-curve-remediation. Requer ADR-003 da Fase 0."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/project-config.yaml`
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia o ADR vinculante de segurança (Gate obrigatório — Fase 0):
`projects/{PROJECT_NAME}/outputs/tobe/docs/decisions/ADR-003-security.md`
→ Se ausente → interromper: "Gate: ADR-003 ausente. Execute a Fase 0 primeiro."

Leia os ADRs contextuais:
`projects/{PROJECT_NAME}/outputs/tobe/docs/decisions/ADR-004-backend.md`
`projects/{PROJECT_NAME}/outputs/tobe/docs/decisions/ADR-008-audit-log.md`

Leia os artefatos AS-IS de segurança:
`projects/{PROJECT_NAME}/outputs/asis/security-map.md`
`projects/{PROJECT_NAME}/outputs/asis/vulnerabilities.md`
`projects/{PROJECT_NAME}/outputs/asis/compliance-gaps.md`
`projects/{PROJECT_NAME}/outputs/asis/gap-register.json`

Leia o blueprint de arquitetura TO-BE (contexto):
`projects/{PROJECT_NAME}/outputs/tobe/docs/architecture-blueprint.md`

Leia as guardrails de Mermaid:
`src/modules/ava-fabric-agents/shared/mermaid-guardrails.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/tobe-architecture/agents/security-design-tobe.md`
