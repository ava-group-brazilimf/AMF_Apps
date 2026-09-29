---
name: ava-asis-gaps-risks
description: ">"
  Consolida findings em risk register priorizado (P0–P3) com score de risco.
  Também gera o risk-register-residual.json TO-BE com riscos aceitos pós-mitigação.
  Ativa com: "listar riscos", "gaps analysis", "risk assessment", "consolidar riscos",
  "risk register", "riscos residuais", "residual risk register",
  "risk-register-residual", "gerar risk-register-residual.json".
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/asis-diagnostic/agents/gaps-risks-asis.md`
