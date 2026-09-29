---
name: ava-devops-podman-run
description: |
  Executa a solução containerizada localmente no Podman/Windows — verifica dependências
  (WSL2, virtualização, winget, Podman), instrui como resolver o que faltar, provisiona a
  Podman Machine, resolve o .env e sobe os contêineres validando a saúde de cada serviço.
  Ativa com: "rodar no podman", "subir os containers", "executar a aplicação localmente",
  "iniciar a solução no windows", "verificar dependências do podman".
---

Determine o PROJECT_NAME antes de executar:
1. Faça Glob em `projects/*/context/project-config.yaml` e leia o campo `project_name`
   (ignore `projects/_template/` e `projects/test-determinism/`)
2. Se houver exatamente um projeto, use-o **sem perguntar**
3. Se houver vários, liste-os e pergunte: "Qual projeto você quer executar no Podman?"
4. Se não houver nenhum, pergunte: "Qual é o nome do projeto? (ex: Meu-ERP)"
5. Use esse PROJECT_NAME para resolver todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia o contexto do projeto (se existirem):
`projects/{PROJECT_NAME}/context/project-config.yaml`
`projects/{PROJECT_NAME}/context/shared-context.md`

Guia de referência (fonte da verdade dos comandos e diagnósticos):
`docs/podman-windows-guide.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/devops-agents/agents/podman-run-agent.md`

Triggers aceitos (padrão `PR` quando o usuário não indicar nenhum):
`PR` run completo | `PC` só checar dependências | `PM` machine | `PE` .env |
`PU` subir | `PS` status | `PL` logs | `PD` parar | `PT` diagnosticar
