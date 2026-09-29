---
name: ava-qa-scenario-generator
description: "DEPRECATED (2026-08-05) — geração de cenários BDD Gherkin absorvida pelo
  ava-qa-bridge-fastqa-tobe (Momento 1). Use @ava-qa-bridge-fastqa-tobe.
"
---

> ⛔ **DEPRECATED**: este agente não é mais invocado pela esteira. Use `@ava-qa-bridge-fastqa-tobe`
> (trigger `TS` no `ava-qa-orchestrator`) para geração de cenários BDD Gherkin.

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/qa-agents/agents/bridge-fastqa-tobe.md`

> Referência histórica (não executar): `src/modules/ava-fabric-agents/qa-agents/agents/scenario-generator-agent.md`
