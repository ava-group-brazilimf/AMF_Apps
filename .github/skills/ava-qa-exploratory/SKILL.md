---
name: ava-qa-exploratory
version: "2.0.0"
date: "2026-06-16"
description: "Conduz sessões estruturadas de Exploratory Testing no sistema legado AS-IS para descobrir comportamentos implícitos, regras de negócio não documentadas, dependências ocultas, fluxos alternativos, caminhos de exceção e edge cases. Complementa o Golden Dataset e o catálogo de testes AS-IS. Ativa com: 'exploratory testing', 'testes exploratórios', 'descobrir comportamentos implícitos', 'edge cases legado', 'regras ocultas', 'dependências ocultas', 'fluxos alternativos', 'exceções', 'ET'."
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir ou estiver vazio, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto em:
- `projects/{PROJECT_NAME}/context/project-config.yaml`
- `projects/{PROJECT_NAME}/context/shared-context.md`

Artefatos AS-IS que serão consultados (quando disponíveis):
- `projects/{PROJECT_NAME}/outputs/asis/master-report.md` ← OBRIGATÓRIO
- `projects/{PROJECT_NAME}/outputs/asis/docs/functional-requirements.md` ← OBRIGATÓRIO
- `projects/{PROJECT_NAME}/outputs/asis/docs/business-rules.md`
- `projects/{PROJECT_NAME}/outputs/asis/architecture-blueprint.md`
- `projects/{PROJECT_NAME}/outputs/asis/pattern-classifications.json`
- `projects/{PROJECT_NAME}/outputs/asis/bounded-context-map.md`
- `projects/{PROJECT_NAME}/outputs/asis/docs/screen-navigation-map.md`
- `projects/{PROJECT_NAME}/outputs/asis/events-pubsub-inventory.md`
- `projects/{PROJECT_NAME}/outputs/asis/gap-list-report.md`
- `projects/{PROJECT_NAME}/outputs/asis/qa/test-coverage-asis.md`
- `projects/{PROJECT_NAME}/outputs/qa/golden-dataset.json`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/qa-agents/agents/exploratory-agent.md`
