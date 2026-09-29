---
name: ava-qa-behavior-mapping
description: "Analisa código-fonte legado Delphi (.pas, .dfm, SPs, views, triggers) correlacionando com documentação funcional AS-IS para catalogar todos os comportamentos de negócio por bounded context que devem ser preservados no TO-BE. Produz behavior-catalog.json e behavior-mapping-report.md. Ativa com: 'mapear comportamentos', 'behavior mapping', 'comportamentos AS-IS', 'catalogar regras de negócio legado', 'BM' (via qa-orchestrator)."
---

## Resolução do PROJECT_NAME

Determine o PROJECT_NAME antes de executar qualquer instrução:

1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se o arquivo não existir ou `project_name` estiver vazio, pergunte ao usuário:
   `"Qual é o nome do projeto? (ex: Meu-ERP)"`
3. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

## Leitura de Contexto do Projeto

Antes de executar o agente, leia os seguintes arquivos de contexto:

- `projects/{PROJECT_NAME}/context/project-config.yaml`
- `projects/{PROJECT_NAME}/context/shared-context.md`

## Execução do Agente

Leia e siga as instruções completas do agente em:

`src/modules/ava-fabric-agents/qa-agents/agents/behavior-mapping-agent.md`

> ⚠️ O agente possui um algoritmo de execução em 6 passos obrigatórios.
> Não pule nenhum passo e siga a ordem definida no agente.
