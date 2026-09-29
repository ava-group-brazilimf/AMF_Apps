---
name: ava-tobe-security-review
description: "Fase 4.8 — Security Review pós-geração de código. Verifica que as vulnerabilidades identificadas no diagnóstico AS-IS (V-01..V-N) foram remediadas no código gerado. Emite security-review-report.md e security-gate-decision.json (APPROVED | CONDITIONAL | BLOCKED). Executa após Build Gate 5.5 (PASS obrigatório)."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, confirme que a Fase 5.5 (Build & Security Validation Gate) concluiu com PASS:
`projects/{PROJECT_NAME}/outputs/tobe/build-gate-result.json`
→ Se ausente ou status != "PASS" → interromper com mensagem de gate bloqueado.

Leia o contexto do projeto:
`projects/{PROJECT_NAME}/context/project-config.yaml`
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia os achados de segurança AS-IS (Gate obrigatório — F1):
`projects/{PROJECT_NAME}/outputs/asis/security/security-findings.json`
→ Se ausente → interromper: "Gate: security-findings.json ausente. Execute o diagnóstico AS-IS (F1) primeiro."

Leia a arquitetura de segurança TO-BE — Seção 12 (Gate obrigatório — Fase 1.6):
`projects/{PROJECT_NAME}/outputs/tobe/docs/security-architecture.md`
→ Se ausente → interromper: "Gate: security-architecture.md ausente. Execute a Fase 1.6 (ava-tobe-security-design) primeiro."

Leia os artefatos AS-IS complementares (não-bloqueantes):
`projects/{PROJECT_NAME}/outputs/asis/security/security-map.md`
`projects/{PROJECT_NAME}/outputs/asis/vulnerabilities.md`
`projects/{PROJECT_NAME}/outputs/asis/security/threat-model-stride.md`
`projects/{PROJECT_NAME}/outputs/asis/security/owasp-coverage-matrix.md`
`projects/{PROJECT_NAME}/outputs/asis/security/remediation-backlog.md`

Inspecione o código gerado na Fase 4.7:
`projects/{PROJECT_NAME}/outputs/tobe/src/`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/tobe-architecture/agents/security-review-tobe.md`
