---
name: ava-master-orchestrator
description: "Orquestra a esteira completa AVA Fabric end-to-end: F1 AS-IS → F2 TO-BE → F3 Stack → F5 QA → F7 DevOps → F6 Deliverables. Coordena 24 agentes em 6 fases sequenciais, com Summary HTML gerado após cada fase. Triggers: FP (full pipeline), SR (status report), RS (resume from phase), HG (human gate). Ativa com: 'executar pipeline completo', 'iniciar esteira completa', 'full pipeline', 'run full avafabric pipeline', 'master orchestrator'."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md`

> ⛔ INVARIANTE CRÍTICA — geração de Summary HTML:
> Todo Summary HTML neste pipeline é gerado EXCLUSIVAMENTE via Bash:
> `python src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py --project {PROJECT_NAME}`
> NUNCA gerar HTML inline ou sintetizar o Summary a partir do contexto da conversa.
> O script carrega o template Avanade oficial — qualquer desvio produz UI incorreto.
