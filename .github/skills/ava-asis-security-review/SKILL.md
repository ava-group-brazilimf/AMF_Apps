---
name: ava-asis-security-review
description: "Redireciona para o ava-asis-security-orchestrator. O security-review-asis.md opera como sub-agent interno do orquestrador de segurança. Use `ava-asis-security-orchestrator` para invocar o orquestrador completo (7 sub-agents + loop)."
---

> ⚠️ Este skill foi substituído por `ava-asis-security-orchestrator`.
> O `security-review-asis.md` continua disponível como sub-agent interno do orquestrador.

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/asis-diagnostic/agents/security/security-orchestrator-asis.md`
