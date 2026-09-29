---
name: ava-deliverable-security-compliance
description: "F7 — Gera Security Compliance Report (13 seções) para aprovação CISO/DPO. Consolida evidências AS-IS + TO-BE + SAST/DAST. Emite compliance_gate: APPROVED, CONDITIONAL, BLOCKED ou PARTIAL."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/project-config.yaml`
`projects/{PROJECT_NAME}/context/shared-context.md`

Verifique o gate obrigatório (PRIMARY INPUT):
`projects/{PROJECT_NAME}/outputs/tobe/docs/security-architecture.md`
→ Se ausente → interromper: "Gate: security-architecture.md ausente. Execute a Fase 1.6 (ava-tobe-security-design) primeiro."

Leia os artefatos AS-IS de segurança:
`projects/{PROJECT_NAME}/outputs/asis/security-map.md`
`projects/{PROJECT_NAME}/outputs/asis/vulnerabilities.md`
`projects/{PROJECT_NAME}/outputs/asis/compliance-gaps.md`
`projects/{PROJECT_NAME}/outputs/asis/security/security-findings.json`
`projects/{PROJECT_NAME}/outputs/asis/security/threat-model-stride.md`
`projects/{PROJECT_NAME}/outputs/asis/security/remediation-backlog.md`
`projects/{PROJECT_NAME}/outputs/asis/security/owasp-coverage-matrix.md`

Leia os ADRs TO-BE:
`projects/{PROJECT_NAME}/outputs/tobe/docs/decisions/ADR-003-security.md`
`projects/{PROJECT_NAME}/outputs/tobe/docs/decisions/ADR-008-audit-log.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/deliverables/agents/security-compliance-agent.md`
