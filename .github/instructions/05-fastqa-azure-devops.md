---
description: FastQA — Fase 5: Integração com Azure DevOps.
applyTo: '**'
tools: ['azureDevOps', 'memory', 'sequential-thinking']
---

# FastQA — Fase 5: Integração Azure DevOps

> **Arquivo:** `05-fastqa-azure-devops.instructions.md`
> **Escopo:** Integração completa com Azure DevOps — Work Items, Test Plans, Test Runs, Repositórios Git e Pipelines CI/CD
> **Índice geral:** Consulte `00-fastqa-index.instructions.md`

---

## 🔀 Prefixos de Comando

Todos os comandos neste arquivo suportam **dois prefixos**:

| Prefixo | Comportamento |
|---------|--------------|
| `@fastqa:` | Execução direta do workflow |
| `@fastqa_code:` | Ativa o modo **TEA** (Test Architect & Quality Advisor) em `code_qa/_bmad/bmm/agents/tea.md` **antes** de executar o workflow |

> Quando o comando for chamado com `@fastqa_code:`, **sempre ativar o TEA primeiro**, depois seguir o workflow normalmente.

---

## 🎯 Objetivo

Este arquivo contém instruções para integração do FastQA com Azure DevOps utilizando **TypeScript nativo** com Node.js fetch API. Todas as operações — criação de work items, upload de evidências, gerenciamento de test plans — são realizadas via **Azure DevOps REST API v7.1** através de scripts TypeScript sem dependências externas de HTTP clients.

> **⚠️ REGRA OBRIGATÓRIA CRÍTICA:**
> - ✅ **SEMPRE** utilizar scripts **TypeScript (.ts)** localizados em `fastqa/scripts/azure-devops/`
> - ❌ **NUNCA** utilizar scripts PowerShell (.ps1) para integração com Azure DevOps
> - ❌ **NUNCA** utilizar comandos diretos via terminal (exceto `npx tsx`)
> - ✅ Toda integração **DEVE** ser feita via scripts TypeScript nativos
> - ✅ Executar sempre com: `npx tsx fastqa/scripts/azure-devops/commands/<script>.command.ts`

> **🤖 AGENT DISPONÍVEL:** Todos os comandos Azure DevOps documentados neste arquivo estão implementados no agent: `fastqa/agents/core/fastqa_5.1_azure_devops.md`. Você pode usar os comandos `@fastqa:azdo_*` diretamente ou referenciar o agent para utilizá-lo como template de execução.

---

## 🏗️ Arquitetura da Integração

```
┌──────────────────────────┐
│     FastQA Agents        │
│  (Comandos @fastqa:azdo) │
└───────────┬──────────────┘
            │ invoca
            ▼
┌──────────────────────────────────────────────────────┐
│  📌 @fastqa:azdo_get_work_item_by_id_or_title        │
│  → MCP Azure DevOps DIRETO (.vscode/mcp.json)       │
│  → NÃO usa scripts TypeScript                       │
├──────────────────────────────────────────────────────┤
│  📌 @fastqa:azdo_list_work_items_by_sprint           │
│  → MCP Azure DevOps DIRETO (.vscode/mcp.json)       │
│  → NÃO usa scripts TypeScript                       │
├──────────────────────────────────────────────────────┤
│  📦 Demais comandos @fastqa:azdo_*                   │
│  → TypeScript Scripts (Native fetch + request)       │
│  → scripts/azure-devops/                             │
└───────────┬──────────────────────────────────────────┘
            │ REST API v7.1 (Basic Auth via PAT)
            ▼
┌──────────────────────────┐
│     Azure DevOps         │
│  Work Items · Test Plans │
│  Test Runs · Attachments │
└──────────────────────────┘
```

> **📌 EXCEÇÃO IMPORTANTE:** Os comandos `@fastqa:azdo_get_work_item_by_id_or_title`, `@fastqa:azdo_list_work_items_by_sprint` e `@fastqa:azdo_create_work_item` **SEMPRE** utilizam **exclusivamente** o **MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`). Eles **NÃO** utilizam scripts TypeScript nem Playwright MCP. Todos os demais comandos continuam usando os scripts TypeScript.

**Stack tecnológica:**
- **TypeScript nativo** — `fetch()` para chamadas REST sem dependências externas (**OBRIGATÓRIO** - não usar PowerShell)
- **Node.js** — Runtime JavaScript nativo
- **Azure DevOps REST API v7.1** — Endpoints oficiais Microsoft
- **dotenv** — Gerenciamento seguro de credenciais
- **tsx** — Execução direta de TypeScript via `npx tsx`

> **⚠️ TECNOLOGIA MANDATÓRIA:** Todos os scripts de integração Azure DevOps **DEVEM** ser escritos em **TypeScript** e executados com `npx tsx`. PowerShell (.ps1) **NÃO** deve ser utilizado.

---

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

Criar/editar arquivo `.env` na raiz de `fastqa/` com as variáveis:

> **⚠️ IMPORTANTE:** Use as **MESMAS credenciais** no `fastqa/.env`. O MCP server é iniciado via wrapper (`mcp-azdo-wrapper.js`) que carrega o `.env` automaticamente.

---

## 🔧 Troubleshooting: MCP Azure DevOps

| Sintoma | Causa | Solução |
|---|---|---|
| Health check OK mas ferramentas MCP não disponíveis | MCP server `azureDevOps` não foi iniciado no VS Code | `Ctrl+Shift+P` → `MCP: List Servers` → `azureDevOps` → **Start Server** |
| MCP "conectado" mas retorna 401 | `mcp.json` usa `${env:...}` legado (credenciais do SO divergem do `.env`) | Execute `@fastqa_ /update` para migrar para o wrapper |
| Health check REST OK, MCP falha com 401 | PAT expirado ou MCP usando credenciais antigas | Verifique PAT no `.env`, reinicie MCP server |
| PAT expirado | Token fora da validade | Crie novo PAT em `dev.azure.com/{org}/_usersSettings/tokens`, atualize `fastqa/.env`, reinicie MCP |
| Check 7 falha (wrapper não existe) | Template antigo ou `mcp-azdo-wrapper.js` deletado | Execute `@fastqa_ /update` para regenerar |
| Check 8 falha (usa ${env:} legado) | `mcp.json` não foi migrado | Execute `@fastqa_ /update` |
| 401 com PAT válido no .env | `AZURE_DEVOPS_PAT` do SO (stale) conflita com `.env` | Execute `@fastqa_ /update` (fix na prioridade), ou remova a var do SO e reinicie VS Code |
| MCP não inicia após setup | `chat.mcp.autostart` não habilitado ou Trust dialog pendente | Verifique settings do workspace; aceite o diálogo de Trust do VS Code |

> **🔌 Auto-start MCP:** Após `/start` ou `/update`, a setting `chat.mcp.autostart` é habilitada no workspace. Na primeira vez, o VS Code exibe um diálogo de Trust — clique em "Allow". A partir da próxima sessão, servidores MCP iniciam automaticamente.
>
> **⚠️ Fallback manual:** Se o auto-start não estiver habilitado, o usuário deve iniciar via `Ctrl+Shift+P` → `MCP: List Servers` → `azureDevOps` → **Start Server**.

```env
# === Azure DevOps ===
# ⚠️ Use os mesmos valores do arquivo .vscode/mcp.json (servidor azureDevOps)
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/sua-organizacao
AZURE_DEVOPS_PAT=seu-personal-access-token
AZURE_DEVOPS_PROJECT=seu-projeto
AZURE_DEVOPS_API_VERSION=7.1
```

**Exemplo de configuração:**
```json
// .vscode/mcp.json
"azureDevOps": {
  "command": "node",
  "args": ["fastqa/scripts/mcp-azdo-wrapper.js"]
}
```

> O wrapper `mcp-azdo-wrapper.js` carrega credenciais diretamente do `fastqa/.env`, eliminando a necessidade de configurar variáveis de ambiente no SO.

```env
# fastqa/.env
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/leandroifarias-hubqa
AZURE_DEVOPS_PAT=seu-token-aqui
AZURE_DEVOPS_DEFAULT_PROJECT=hub-qa-playwright-agents
AZURE_DEVOPS_API_VERSION=7.1
```

### Pré-requisitos

- Node.js v22+
- TypeScript instalado (`npm install typescript`)
- Dependências: `npm install dotenv tsx`
- Variáveis de ambiente configuradas no `.env`

### Permissões Necessárias do PAT

| Escopo | Permissão | Uso |
|--------|-----------|-----|
| **Work Items** | Read & Write | CRUD de work items e attachments |
| **Test Management** | Read & Write | Test Plans, Suites, Runs, Results |
| **Code** | Read & Write | Git repositories, branches, pushes |
| **Build** | Read & Write | Pipelines, builds, logs, definições |
| **Project and Team** | Read | Informações do projeto |
| **Variable Groups** | Read, create, & manage | Criar/atualizar Variable Groups (Cmd 23) |

### Como Criar o PAT

1. Acesse: `https://dev.azure.com/{sua-org}/_usersSettings/tokens`
2. Clique em **New Token**
3. Configure:
   - **Name:** `FastQA-Playwright`
   - **Expiration:** conforme política da organização
   - **Scopes:** Work Items (R&W), Test Management (R&W), Project (R)
4. Copie o token para o `.env`

---

## 📂 Estrutura de Scripts

```
fastqa/scripts/azure-devops/
├── README.md                                # Documentação dos scripts
├── azure-devops.config.ts                   # 🔧 Configuração e constantes
├── azure-devops.client.ts                   # 🔑 Client principal (fetch nativo)
│
├── types/
│   └── azure-devops.types.ts                # Interfaces e tipos TypeScript
│
├── utils/
│   ├── base64.util.ts                       # Encoding de arquivos para upload
│   ├── logger.util.ts                       # Logger estruturado (console + arquivo)
│   └── report-generator.util.ts             # Gerador de relatórios Markdown
│
├── commands/                                # Scripts executáveis (25 scripts)
│   ├── get-work-item.command.ts                 # 🔍 Buscar work item (TS fallback)
│   ├── list-work-items-by-sprint.command.ts     # 📋 Listar work items por sprint (TS fallback)
│   ├── create-work-item.command.ts              # ➕ Criar work item (TS fallback)
│   ├── create-test-case.command.ts              # 📝 Criar test case (TS fallback)
│   ├── link-work-items.command.ts               # 🔗 Vincular work items (TS fallback)
│   ├── list-test-plans.command.ts               # 📋 Listar test plans (TS fallback)
│   ├── add-testcase-to-suite.command.ts         # 📌 Adicionar TC à suite (TS fallback)
│   ├── associate-bug-to-test-result.command.ts  # 🔗 Associar bug a test result
│   ├── create-bug.command.ts                    # 🐛 Criar bug com campos QA
│   ├── create-repo.command.ts                   # 🆕 Criar repositório + push inicial
│   ├── generate-pipeline-yaml.command.ts        # ⚙️ Gerar pipeline YAML CI/CD
│   ├── generate-report.command.ts               # 📊 Gerar relatório (TS fallback)
│   ├── push-automation.command.ts               # 📤 Push de automação para repo
│   ├── sync-pipeline-results.command.ts         # 🔄 Sincronizar resultados pipeline
│   ├── update-work-item.command.ts              # ✏️ Atualizar work item
│   ├── upload-batch-test-execution.command.ts   # 📦 Upload de múltiplas execuções em lote
│   ├── upload-evidence.command.ts               # 📎 Upload de evidência individual
│   ├── upload-folder-evidence.command.ts        # 📁 Upload de pasta de evidências
│   ├── upload-folder-test-result.command.ts     # 📂 Upload de pasta para Test Result
│   ├── upload-test-execution.command.ts         # 🚀 Fluxo completo de execução
│   ├── verify-test-result-bug-link.command.ts   # ✅ Verificar vínculo bug ↔ test result
│   ├── create-test-plan.command.ts              # 📋 Criar Test Plan (Cmd 19)
│   ├── update-test-plan.command.ts              # 📝 Atualizar Test Plan (Cmd 20)
│   ├── create-pipeline.command.ts               # 🚀 Criar Pipeline (Cmd 21)
│   ├── run-pipeline.command.ts                  # ▶️ Executar Pipeline (Cmd 22)
│   ├── set-pipeline-variable.command.ts         # 🔑 Variáveis de Pipeline (Cmd 23)
│   └── verify-pipeline-results.command.ts       # 🔍 Verificar Resultados (Cmd 24)
│
├── examples/                                # Exemplos de arquivos de entrada
│   ├── batch-executions-example.csv         # Exemplo CSV para upload em lote
│   ├── batch-executions-example.json        # Exemplo JSON para upload em lote
│   └── README.md                            # Documentação dos exemplos
│
└── logs/                                    # Logs de execução automáticos
    └── .gitkeep
```

### Execução dos Scripts

```bash
# Formato padrão
npx tsx fastqa/scripts/azure-devops/commands/<command>.command.ts [--args]

# Exemplos
npx tsx fastqa/scripts/azure-devops/commands/create-bug.command.ts --title "Erro no login" --severity "2 - High"
npx tsx fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts --test-plan-id 110 --test-suite-id 112 --test-case-id 45 --evidence-path "manual_test/evidence/TS-001/video.webm" --result Passed
npx tsx fastqa/scripts/azure-devops/commands/create-repo.command.ts --repo "meu-repo" --automation-dir web --project "meu-projeto"
```

---

## 📋 Comandos FastQA Azure DevOps

### Índice de Comandos

| # | Comando | Descrição | Tipo | Tecnologia |
|---|---------|-----------|------|------------|
| 1 | `@fastqa:azdo_get_work_item_by_id_or_title` | **⚡ Via MCP Azure DevOps DIRETO** — Obter informações de work item por ID ou título (aceita nome completo ou parte do nome) com filtro opcional por tipo (NÃO usa scripts TS) | 🔍 Consulta | MCP Azure DevOps |
| 2 | `@fastqa:azdo_list_work_items_by_sprint` | **⚡ Via MCP Azure DevOps DIRETO** — Listar work items de uma sprint/iteração (NÃO usa scripts TS) | 🔍 Consulta | MCP Azure DevOps |
| 3 | `@fastqa:azdo_create_work_item` | **⚡ Via MCP Azure DevOps DIRETO** — Criar work item com tipo selecionável (NÃO usa scripts TS) | ➕ Criação | MCP Azure DevOps |
| 4 | `@fastqa:azdo_create_bug` | **🔧 Via MCP + TypeScript** — Criar bug (MCP) + vincular (MCP) + evidências (TS) | 🐛 Criação | **MCP + TypeScript** |
| 5 | `@fastqa:azdo_create_test_case` | **🔧 Via MCP + TypeScript** — Criar test case com steps estruturados (MCP primário, TS fallback/batch) | 📝 Criação | **MCP + TypeScript** |
| 6 | `@fastqa:azdo_update_work_item` | **⚡ Via MCP Azure DevOps** — Atualizar campos de um work item existente + upload opcional de evidências via TS | ✏️ Edição | **MCP Azure DevOps** |
| 7 | `@fastqa:azdo_link_work_items` | **⚡ Via MCP Azure DevOps DIRETO** — Vincular work items (NÃO usa scripts TS) | 🔗 Relacionamento | **MCP Azure DevOps** |
| 8 | `@fastqa:azdo_upload_evidence` | **🔧 Via TypeScript** — Upload de evidência individual para Work Item | 📎 Upload | **TypeScript** |
| 9 | `@fastqa:azdo_upload_folder_evidence` | **🔧 Via TypeScript** — Upload de todos arquivos de uma pasta para Work Item | 📁 Upload | **TypeScript** |
| 10 | `@fastqa:azdo_upload_test_execution` | **🔧 Via TypeScript** — Fluxo completo: Run + Upload + Status + (Bug) | 🚀 Execução | **TypeScript** |
| 11 | `@fastqa:azdo_list_test_plans` | **⚡ Via MCP Azure DevOps** — Listar Test Plans, Suites e Test Cases (NÃO usa scripts TS) | 📋 Consulta | **MCP Azure DevOps** |
| 12 | `@fastqa:azdo_add_testcase_to_suite` | **⚡ Via MCP Azure DevOps** — Adicionar Test Cases a uma Test Suite (NÃO usa scripts TS) | 📌 Associação | **MCP Azure DevOps** |
| 13 | `@fastqa:azdo_upload_batch_test_execution` | **🔧 Via TypeScript** — Upload de múltiplas execuções em lote | 📦 Lote | **TypeScript** |
| 14 | `@fastqa:azdo_generate_report` | **⚡ Via MCP Azure DevOps** — Gerar relatório consolidado de execução (NÃO usa scripts TS) | 📊 Relatório | **MCP Azure DevOps** |
| 15 | `@fastqa:azdo_push_automation` | **🔧 Via MCP + TypeScript** — Push de código de automação para repositório Azure DevOps (MCP para listar repos/branches + TS para push Git) | 📤 Git Push | **MCP + TypeScript** |
| 16 | `@fastqa:azdo_generate_pipeline` | **🔧 Via TypeScript** — Gerar YAML de pipeline CI/CD + opcional push para repositório | ⚙️ Pipeline | **TypeScript** |
| 17 | `@fastqa:azdo_sync_pipeline_results` | **🔧 Via TypeScript** — Sincronizar resultados de build/pipeline com Test Plan (Test Runs + Bugs automáticos) | 🔄 Sincronização | **TypeScript** |
| 18 | `@fastqa:azdo_create_repo` | **🔧 Via TypeScript** — Criar repositório no Azure DevOps com push inicial de código de automação (suporte cross-project) | 🆕 Criação Repo | **TypeScript** |
| 19 | `@fastqa:azdo_create_test_plan` | **🔧 Via TypeScript** — Criar Test Plan com suites opcionais | 📋 Criação | **TypeScript** |
| 20 | `@fastqa:azdo_update_test_plan` | **🔧 Via TypeScript** — Atualizar Test Plan (nome, datas, estado) | ✏️ Atualização | **TypeScript** |
| 21 | `@fastqa:azdo_create_pipeline` | **🔧 Via TypeScript** — Criar definição de pipeline no AzDO | 🚀 Criação Pipeline | **TypeScript** |
| 22 | `@fastqa:azdo_run_pipeline` | **🔧 Via TypeScript** — Executar pipeline com polling opcional | ▶️ Execução | **TypeScript** |
| 23 | `@fastqa:azdo_set_pipeline_variable` | **🔧 Via TypeScript** — Criar/atualizar Variable Group + autorizar pipeline | 🔑 Variáveis | **TypeScript** |
| 24 | `@fastqa:azdo_verify_pipeline_results` | **🔧 Via TypeScript** — Verificar resultados + diagnóstico para auto-healing | 🔍 Verificação | **TypeScript** |

> **📌 IMPORTANTE:** Comandos 1-3, 5-7, 11-12, 14 usam **MCP Azure DevOps direto** (sem scripts) com **fallback TypeScript** quando MCP não está ativo. Comando 4 usa **MCP (criação+link) + TypeScript (evidências)**. Comandos 8-10, 13, 15-24 usam **scripts TypeScript** (`npx tsx`) e/ou **MCP + TypeScript** combinados. Novos comandos 19-24 (Test Plans, Pipeline CRUD, Variables, Verificação) são **100% TypeScript**.

---

### 🔍 1. `@fastqa:azdo_get_work_item_by_id_or_title` — Obter Informações de Work Item (Azure DevOps MCP)

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 1

Recupera e exibe informações detalhadas de um work item do Azure DevOps por **ID** ou **Título** (aceita nome completo ou parte do nome), **utilizando EXCLUSIVAMENTE o MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`).

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **APENAS** o **MCP Azure DevOps** (`azureDevOps` conforme `.vscode/mcp.json`).
> - ❌ **NÃO** utilizar scripts TypeScript (`get-work-item.command.ts` ou qualquer outro)
> - ❌ **NÃO** utilizar Playwright MCP para navegar ao Azure DevOps
> - ❌ **NÃO** utilizar `npx tsx` ou qualquer comando de terminal
> - ✅ **SEMPRE** usar o MCP Azure DevOps (`azureDevOps`) para acessar a API REST diretamente

**Tecnologia:** MCP Azure DevOps — servidor `azureDevOps` configurado em `.vscode/mcp.json`

**Workflow:**
1. **Perguntar o modo de busca** e **AGUARDAR** resposta do usuário:
   - **Opção 1:** Buscar por **ID** (número do work item)
   - **Opção 2:** Buscar por **Título** (nome completo ou parte do nome)

2. **[OPCIONAL] Perguntar o tipo de work item** para filtrar a busca e **AGUARDAR** resposta (pode pular):
   - Epic
   - Feature
   - Product Backlog Item
   - User Story
   - Task
   - Bug
   - Test Case
   - Issue
   - (Deixar vazio para buscar em todos os tipos)

3. **Executar busca conforme modo selecionado:**
   
   **Se Opção 1 (ID):**
   - Solicitar o **ID do Work Item**
   - Buscar diretamente usando `mcp_microsoft_azu_wit_get_work_item`
   
   **Se Opção 2 (Título):**
   - Solicitar o **Título** (pode ser o nome completo ou apenas parte dele)
   - Construir query usando `mcp_microsoft_azu_search_workitem`:
     - A busca usa `CONTAINS`, então funciona tanto para nome completo quanto parcial
     - Exemplo: "login" encontrará "Tela de Login", "Login com erro", "Validação de login", etc.
   - Se houver **múltiplos resultados**, exibir lista numerada e solicitar escolha:
     ```
     Encontrados X work items:
     1. #123 - [Bug] Erro no login (Estado: Active)
     2. #456 - [Task] Corrigir login (Estado: Closed)
     3. #789 - [User Story] Implementar tela de login (Estado: New)
     ...
     Qual deseja visualizar? (Digite o número)
     ```
   - **AGUARDAR** seleção do usuário
   - Buscar o work item selecionado por ID usando `mcp_microsoft_azu_wit_get_work_item`

4. **Obter informações detalhadas** usando **MCP Azure DevOps** (`azureDevOps` conforme `.vscode/mcp.json`):
   a. Obter dados completos do work item:
      - **Tipo**, **Título**, **Estado**, **Área**, **Iteração**
      - **Descrição** e **Critérios de Aceite** (campos HTML)
      - **Atribuído a**, **Criado por**, **Datas de criação e modificação**
      - **Prioridade**, **Severidade** (se aplicável)
      - **Tags**, **Comentários**, **Histórico de revisões**
   b. Obter work items vinculados (relations)
   c. Obter anexos (attachments)

5. **Formatar e exibir** informações completas no chat:
   - Cabeçalho com ID, tipo, título e estado
   - Seção de informações básicas (área, iteração, responsável)
   - Descrição e critérios de aceite formatados
   - Lista de work items vinculados com tipos de relação
   - Lista de anexos com tamanhos
   - Histórico de alterações recentes

6. Gerar **URL direta** para visualização no Azure DevOps:
   - Formato: `{AZURE_DEVOPS_ORG_URL}/{PROJECT}/_workitems/edit/{id}`

7. **Perguntar se deseja salvar o work item como arquivo markdown** e **AGUARDAR** resposta:
   - Se **Sim**: 
     a. Mapear tipo do work item para sigla:
        - `Epic` → `EPIC`
        - `Feature` → `FEAT`
        - `Product Backlog Item` → `PBI`
        - `User Story` → `US`
        - `Task` → `TASK`
        - `Bug` → `BUG`
        - `Test Case` → `TC`
        - `Issue` → `ISSUE`
     b. Criar arquivo markdown em: `C:\projetos\avanade-code-qa\fastqa\manual_test\US\{TIPO}-{ID}.md`
        - Exemplo: `PBI-2.md`, `US-15.md`, `BUG-45.md`
     c. Conteúdo do arquivo deve seguir o formato:
        ```markdown
        # {Tipo} #{ID}: {Título}
        
        **Estado:** {Estado}  
        **Prioridade:** {Prioridade}  
        **Iteração:** {Iteração}  
        **Criado em:** {Data de Criação}  
        **Criado por:** {Criador}  
        
        ## 📝 Descrição
        
        {Descrição formatada em markdown}
        
        ## ✅ Critérios de Aceite
        
        {Critérios de aceite formatados em markdown}
        
        ## 🔗 Links
        
        - [Ver no Azure DevOps]({URL do work item})
        
        ## 📎 Work Items Vinculados
        
        {Lista de work items relacionados}
        
        ---
        *Extraído em: {Data/Hora}*
        ```
     d. Confirmar salvamento com caminho completo do arquivo criado
   - Se **Não**: prosseguir para próximo passo

8. Perguntar se deseja executar alguma ação adicional com os dados obtidos

**Parâmetros:**
- `Modo de Busca` (obrigatório) — ID | Título (aceita nome completo ou parte do nome)
- `Valor de Busca` (obrigatório) — ID numérico ou texto do título
- `Tipo de Work Item` (opcional) — Para filtrar resultados da busca

**Configuração MCP utilizada (`.vscode/mcp.json`):**
```json
"azureDevOps": {
  "command": "npx",
  "args": ["-y", "@tiberriver256/mcp-server-azure-devops"],
  "env": {
    "AZURE_DEVOPS_ORG_URL": "...",
    "AZURE_DEVOPS_AUTH_METHOD": "pat",
    "AZURE_DEVOPS_PAT": "...",
    "AZURE_DEVOPS_DEFAULT_PROJECT": "..."
  }
}
```

**Pré-requisitos:**
- MCP Azure DevOps configurado e **habilitado** em `.vscode/mcp.json` (servidor `azureDevOps`)
- PAT token válido nas variáveis de ambiente do MCP
- Variáveis `AZURE_DEVOPS_ORG_URL` e `AZURE_DEVOPS_DEFAULT_PROJECT` configuradas
- Servidor MCP Azure DevOps **ativo** (verificar no painel MCP do VS Code)

---

### 🔍 2. `@fastqa:azdo_list_work_items_by_sprint` — Listar Work Items por Sprint (Azure DevOps MCP)

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 2

Lista todos os work items de uma sprint/iteração específica do Azure DevOps **utilizando EXCLUSIVAMENTE o MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`).

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **APENAS** o **MCP Azure DevOps** (`azureDevOps` conforme `.vscode/mcp.json`).
> - ❌ **NÃO** utilizar scripts TypeScript
> - ❌ **NÃO** utilizar Playwright MCP
> - ❌ **NÃO** utilizar `npx tsx` ou qualquer comando de terminal
> - ✅ **SEMPRE** usar o MCP Azure DevOps (`azureDevOps`) para acessar a API REST diretamente

**Tecnologia:** MCP Azure DevOps — servidor `azureDevOps` configurado em `.vscode/mcp.json`

**Workflow:**
1. Solicitar o **Nome do Projeto Azure DevOps** e **AGUARDAR** resposta do usuário
2. Usar **MCP Azure DevOps** (`mcp_microsoft_azu_work_list_iterations`) para listar todas as iterações/sprints do projeto:
   - Exibir tabela com: Número, Nome, Período (se disponível), Path
   - Exemplo: Sprint 1, Sprint 2, etc.
3. Perguntar qual iteração deseja consultar e **AGUARDAR** resposta:
   - Opções: Sprint específica ou Todas as sprints
4. Usar **MCP Azure DevOps** para obter work items:
   a. Executar `mcp_microsoft_azu_wit_list_backlog_work_items` para obter IDs dos work items do backlog
   b. Executar `mcp_microsoft_azu_wit_get_work_items_batch_by_ids` para obter detalhes completos em lote
   c. Filtrar work items pela iteração selecionada verificando o campo `System.IterationPath`
5. Para cada work item encontrado na sprint, coletar:
   - **ID**, **Tipo** (System.WorkItemType), **Título** (System.Title), **Estado** (System.State)
   - **Atribuído a** (System.AssignedTo), **Prioridade** (Microsoft.VSTS.Common.Priority)
   - **Tags** (System.Tags), **Iteração** (System.IterationPath)
6. Formatar e exibir lista completa no chat:
   - Cabeçalho com nome da sprint e período (se disponível)
   - Tabela organizada por tipo de work item:
     - Épicos
     - Features
     - Product Backlog Items / User Stories
     - Tasks
     - Bugs
     - Test Cases
   - Resumo de distribuição (quantidade por tipo e por estado)
4. Gerar URLs diretas para visualização no Azure DevOps
5. **Perguntar se deseja salvar os work items como arquivos markdown** e **AGUARDAR** resposta:
   - Se **Sim**:
     a. Para cada work item listado, perguntar individualmente ou em lote:
        - **Opção 1:** Salvar todos os work items da lista
        - **Opção 2:** Selecionar work items específicos por ID (separados por vírgula)
     b. Mapear tipo do work item para sigla:
        - `Epic` → `EPIC`
        - `Feature` → `FEAT`
        - `Product Backlog Item` → `PBI`
        - `User Story` → `US`
        - `Task` → `TASK`
        - `Bug` → `BUG`
        - `Test Case` → `TC`
     c. Para cada work item selecionado, buscar detalhes completos via MCP
     d. Criar arquivo markdown em: `C:\projetos\avanade-code-qa\fastqa\manual_test\US\{TIPO}-{ID}.md`
        - Exemplo: `PBI-2.md`, `US-15.md`, `BUG-45.md`
     e. Conteúdo do arquivo deve seguir o formato:
        ```markdown
        # {Tipo} #{ID}: {Título}
        
        **Estado:** {Estado}  
        **Prioridade:** {Prioridade}  
        **Iteração:** {Iteração}  
        **Criado em:** {Data de Criação}  
        **Criado por:** {Criador}  
        
        ## 📝 Descrição
        
        {Descrição formatada em markdown}
        
        ## ✅ Critérios de Aceite
        
        {Critérios de aceite formatados em markdown}
        
        ## 🔗 Links
        
        - [Ver no Azure DevOps]({URL do work item})
        
        ## 📎 Work Items Vinculados
        
        {Lista de work items relacionados}
        
        ---
        *Extraído em: {Data/Hora} | Sprint: {Nome da Sprint}*
        ```
     f. Exibir resumo: quantidade de arquivos salvos e lista de arquivos criados
   - Se **Não**: prosseguir para próximo passo
6. Perguntar se deseja executar alguma ação adicional (ex: detalhar um work item, criar test cases, etc.)

**Parâmetros:**
- `Nome da Sprint/Iteração` (opcional) — Nome completo da iteração (ex: "Sprint 15", "hub-qa-playwright-agents\Sprint 1")
- `Tipos de Work Item` (opcional) — Filtrar por tipos específicos (ex: "Bug,Task")
- `Estados` (opcional) — Filtrar por estados (ex: "Active,Resolved")

**Configuração MCP utilizada (`.vscode/mcp.json`):**
```json
"azureDevOps": {
  "command": "npx",
  "args": ["-y", "@tiberriver256/mcp-server-azure-devops"],
  "env": {
    "AZURE_DEVOPS_ORG_URL": "...",
    "AZURE_DEVOPS_AUTH_METHOD": "pat",
    "AZURE_DEVOPS_PAT": "...",
    "AZURE_DEVOPS_DEFAULT_PROJECT": "..."
  }
}
```

**Exemplo de saída:**

```markdown
## 📋 Work Items da Sprint: "Sprint 15"
**Período:** 01/02/2026 - 15/02/2026
**Projeto:** hub-qa-playwright-agents

### 📊 Resumo
- Total: 25 work items
- ✅ Concluídos: 15 (60%)
- 🔄 Em Progresso: 8 (32%)
- ⏳ Novos: 2 (8%)

### 🎯 Épicos (2)
| ID | Título | Estado | Responsável |
|----|--------|--------|-------------|
| 1 | Teste QA | To Do | Leandro Farias |
| 5 | Módulo de Login | Active | — |

### 📋 User Stories (8)
...

### 🐛 Bugs (3)
...
```

**Pré-requisitos:**
- MCP Azure DevOps configurado e **habilitado** em `.vscode/mcp.json` (servidor `azureDevOps`)
- PAT token válido nas variáveis de ambiente do MCP
- Variáveis `AZURE_DEVOPS_ORG_URL` e `AZURE_DEVOPS_DEFAULT_PROJECT` configuradas
- Servidor MCP Azure DevOps **ativo** (verificar no painel MCP do VS Code)

---

### ➕ 3. `@fastqa:azdo_create_work_item` — Criar Work Item (Azure DevOps MCP)

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 3

Cria um novo work item no Azure DevOps **utilizando EXCLUSIVAMENTE o MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`), com suporte opcional para upload automático de evidências.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **APENAS** o **MCP Azure DevOps** (`azureDevOps` conforme `.vscode/mcp.json`).
> - ❌ **NÃO** utilizar scripts TypeScript (`create-work-item.command.ts` ou qualquer outro)
> - ❌ **NÃO** utilizar Playwright MCP
> - ❌ **NÃO** utilizar `npx tsx` ou qualquer comando de terminal
> - ✅ **SEMPRE** usar o MCP Azure DevOps (`azureDevOps`) e a ferramenta `mcp_microsoft_azu_wit_create_work_item`

**Tecnologia:** MCP Azure DevOps — servidor `azureDevOps` configurado em `.vscode/mcp.json`

**Workflow:**
1. Solicitar o **Nome do Projeto Azure DevOps** e **AGUARDAR** resposta do usuário

2. Apresentar menu de tipos de work item e **AGUARDAR** seleção do usuário:
   - 🐛 **Bug** — Defeito encontrado durante testes
   - 📋 **Product Backlog Item** — Requisito ou funcionalidade
   - ✅ **Task** — Tarefa de trabalho
   - 📝 **Test Case** — Caso de teste
   - 🎯 **Feature** — Feature de alto nível
   - 📌 **User Story** — História de usuário
   - 🚧 **Issue** — Problema ou impedimento

3. Solicitar campos conforme tipo selecionado e **AGUARDAR** dados do usuário:
   
   **Campos obrigatórios para TODOS os tipos:**
   - **Título** (System.Title) — Descrição resumida
   - **Descrição** (System.Description) — Descrição detalhada (aceita HTML)
   
   **Campos opcionais gerais:**
   - **Área Path** (System.AreaPath) — Área do projeto (usar padrão se omitido)
   - **Atribuído a** (System.AssignedTo) — Email do responsável
   - **Prioridade** (Microsoft.VSTS.Common.Priority) — 1 (Alta) a 4 (Baixa)
   - **Tags** (System.Tags) — Tags separadas por vírgula
   - **Evidências** (opcional) — Caminho de screenshots/vídeos para anexar (será processado no passo 6)

3.1. **Perguntar sobre Sprint/Iteration** e **AGUARDAR** resposta:
   - "Deseja associar este work item a uma Sprint/Iteração específica?"
   - **Se Sim:** Solicitar o nome completo da Sprint/Iteration (ex: "Sprint 15", "hub-qa-playwright-agents\Sprint 1")
   - **Se Não:** Usar iteração padrão do projeto ou deixar sem associação específica
   - **Campo:** **Iteration Path** (System.IterationPath) — Sprint/Iteração
   
   **Campos específicos por tipo:**
   
   **Se Bug:**
   - **Severity** (Microsoft.VSTS.Common.Severity) — `1 - Critical` | `2 - High` | `3 - Medium` | `4 - Low`
   - **Repro Steps** (Microsoft.VSTS.TCM.ReproSteps) — Passos de reprodução (HTML)
   - **System Info** (Microsoft.VSTS.TCM.SystemInfo) — Ambiente de execução
   
   **Se Test Case:**
   - **Steps** (Microsoft.VSTS.TCM.Steps) — XML com steps literais do `.feature` (linha completa, sem reescrita)
   - Se houver `Background` no `.feature`, incluir seus steps como primeiros no Test Case
   - **Preconditions** (Microsoft.VSTS.Common.Preconditions) — Pré-condições
   
   **Se Task:**
   - **Remaining Work** (Microsoft.VSTS.Scheduling.RemainingWork) — Horas restantes
   - **Activity** (Microsoft.VSTS.Common.Activity) — Tipo de atividade (Development, Testing, etc.)
   
   **Se Product Backlog Item ou User Story:**
   - **Acceptance Criteria** (Microsoft.VSTS.Common.AcceptanceCriteria) — Critérios de aceite
   - **Story Points** (Microsoft.VSTS.Scheduling.StoryPoints) — Pontuação
   - **Business Value** (Microsoft.VSTS.Common.BusinessValue) — Valor de negócio

4. Construir objeto de campos para o MCP:
   ```json
   {
     "System.Title": "[valor do título]",
     "System.Description": "[valor da descrição]",
     "System.AreaPath": "[projeto]\\[área]",
     "System.IterationPath": "[projeto]\\[sprint]", // Conforme resposta do passo 3.1
     "System.AssignedTo": "[email]",
     "Microsoft.VSTS.Common.Priority": "[1-4]",
     "System.Tags": "[tag1; tag2; tag3]",
     // Campos específicos conforme tipo
   }
   ```

5. Executar criação usando **MCP Azure DevOps**:
   - Usar ferramenta: `mcp_microsoft_azu_wit_create_work_item`
   - Parâmetros obrigatórios:
     - `project` (string): Nome do projeto
     - `work_item_type` (string): Tipo do work item ("Bug", "Task", "Product Backlog Item", "User Story", "Feature", "Test Case", "Issue")
     - `title` (string): Título do work item
   - Parâmetros opcionais:
     - `description` (string): Descrição
     - `assigned_to` (string): Email do responsável
     - `area_path` (string): Caminho da área
     - `iteration_path` (string): Caminho da iteração
     - `priority` (number): 1-4
     - `tags` (string): Tags separadas por vírgula
     - Campos específicos do tipo conforme mapeamento acima

6. Capturar o **Work Item ID** retornado pelo MCP

7. **[OBRIGATÓRIO]** Se evidências foram informadas:
   a. **SEMPRE** executar script TypeScript de upload:
      ```bash
      npx tsx fastqa/scripts/azure-devops/commands/upload-evidence.command.ts \
        --work-item-id {Work Item ID capturado no passo 6} \
        --evidence-path "{caminho informado no passo 3}"
      ```
   b. O script fará:
      - Upload de todos os arquivos de evidência (screenshots, vídeos, logs)
      - Anexação automática ao Work Item criado
      - Exibição do resumo de arquivos anexados

8. Capturar resposta do MCP com:
   - **ID** do work item criado
   - **URL** direto para visualização no Azure DevOps
   - **Campos** preenchidos

9. Formatar e exibir resultado no chat:
   ```markdown
   ✅ Work Item criado com sucesso!
   
   **ID:** #[ID]
   **Tipo:** [Tipo]
   **Título:** [Título]
   **Estado:** New
   **Prioridade:** [Prioridade]
   **Sprint:** [Sprint informada ou "Padrão"]
   **Atribuído a:** [Responsável]
   **Evidências:** [Quantidade] anexadas (se aplicável)
   
   🔗 [Ver no Azure DevOps]([URL])
   ```

10. Perguntar se deseja executar alguma ação adicional:
   - Vincular a outro work item (`@fastqa:azdo_link_work_items`)
   - Adicionar anexos ou evidências adicionais
   - Criar work items relacionados

**Parâmetros MCP:**
- `project` (obrigatório) — Nome do projeto Azure DevOps
- `work_item_type` (obrigatório) — Tipo: `Bug` | `Task` | `Product Backlog Item` | `User Story` | `Feature` | `Test Case` | `Issue`
- `title` (obrigatório) — Título do work item
- `description` (opcional) — Descrição detalhada (aceita HTML)
- `assigned_to` (opcional) — Email do responsável
- `area_path` (opcional) — Caminho da área
- `iteration_path` (opcional) — Caminho da iteração/sprint (conforme resposta do passo 3.1)
- `priority` (opcional) — 1 (Alta) a 4 (Baixa)
- `tags` (opcional) — Tags separadas por vírgula
- `evidence_path` (opcional) — Caminho de arquivo ou pasta com evidências para anexar
- Campos específicos do tipo (ver workflow passo 3)

**Configuração MCP utilizada (`.vscode/mcp.json`):**
```json
"azureDevOps": {
  "command": "npx",
  "args": ["-y", "@tiberriver256/mcp-server-azure-devops"],
  "env": {
    "AZURE_DEVOPS_ORG_URL": "...",
    "AZURE_DEVOPS_AUTH_METHOD": "pat",
    "AZURE_DEVOPS_PAT": "...",
    "AZURE_DEVOPS_DEFAULT_PROJECT": "..."
  }
}
```

**Pré-requisitos:**
- MCP Azure DevOps configurado e **habilitado** em `.vscode/mcp.json` (servidor `azureDevOps`)
- PAT token válido nas variáveis de ambiente do MCP
- Variáveis `AZURE_DEVOPS_ORG_URL` e `AZURE_DEVOPS_DEFAULT_PROJECT` configuradas
- Servidor MCP Azure DevOps **ativo** (verificar no painel MCP do VS Code)

---

### 🐛 4. `@fastqa:azdo_create_bug` — Criar Bug (QA Especializado)

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 4

Cria um bug com campos especializados para o time de QA, incluindo passos de reprodução estruturados, severidade e anexos de evidência automaticamente.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando utiliza **MCP Azure DevOps** para criação do bug e **TypeScript** apenas para upload de evidências:
> - ✅ **SEMPRE** usar **MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`) para criar o bug via `mcp_microsoft_azu_wit_create_work_item`
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/upload-evidence.command.ts` para anexar evidências (se informadas)
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ❌ **NUNCA** utilizar script `create-bug.command.ts` - criar via MCP
> - ⚠️ **IMPORTANTE:** Upload de evidências é feito separadamente via script TypeScript após criação do bug

**Tecnologia:** MCP Azure DevOps (criação) + TypeScript (upload de evidências)

**Workflow:**
1. Solicitar informações do bug e **AGUARDAR** resposta do usuário:
   - **Título** (obrigatório) — Descrição resumida e objetiva do bug
   - **Passos de Reprodução** (obrigatório) — Steps numerados detalhados
   - **Resultado Esperado** (obrigatório) — O que deveria acontecer
   - **Resultado Obtido** (obrigatório) — O que aconteceu de fato
   - **Severidade** (obrigatório) — `1 - Critical` | `2 - High` | `3 - Medium` | `4 - Low`
   - **Prioridade** (opcional) — `1` | `2` | `3` | `4` (padrão: mesma da severidade)
   - **Ambiente** (opcional) — Browser, OS, dispositivo, URL
   - **Evidências** (opcional) — Caminho de screenshots/vídeos para anexar (será processado no passo 5)
   - **US/PBI relacionada** (opcional) — ID do work item pai
   - **Tags** (opcional) — Ex: `regression`, `login`, `sprint-15`

2. Formatar corpo do bug com template QA padrão em HTML:
   ```html
   <div style="font-family: Segoe UI, Tahoma, Geneva, Verdana, sans-serif;">
     <h3 style="color: #0078d4;">🔄 Passos de Reprodução</h3>
     <ol style="line-height: 1.6;">
       <li>Acessar a URL https://...</li>
       <li>Preencher campo "Email" com valor inválido</li>
       <li>Clicar no botão "Entrar"</li>
     </ol>
     <h3 style="color: #107c10; margin-top: 20px;">✅ Resultado Esperado</h3>
     <p style="padding: 10px; background-color: #f0f9f0; border-left: 4px solid #107c10;">
       Exibir mensagem de erro "Email inválido" abaixo do campo.
     </p>
     <h3 style="color: #d13438; margin-top: 20px;">❌ Resultado Obtido</h3>
     <p style="padding: 10px; background-color: #fff4f4; border-left: 4px solid #d13438;">
       Sistema aceita o email e exibe página em branco (erro 500).
     </p>
     <h3 style="color: #505050; margin-top: 20px;">🖥️ Ambiente</h3>
     <p style="padding: 10px; background-color: #f5f5f5; border-left: 4px solid #505050;">
       Chrome 120 · Windows 11 · Resolução 1920x1080
     </p>
   </div>
   ```

3. Criar o bug usando **MCP Azure DevOps** (`mcp_microsoft_azu_wit_create_work_item`):
   - **project:** Nome do projeto
   - **work_item_type:** "Bug"
   - **title:** Título informado
   - **description:** HTML formatado do passo 2 (campo `Microsoft.VSTS.TCM.ReproSteps`)
   - **priority:** Prioridade informada (ou derivada da severidade)
   - **tags:** Tags informadas
   - **Campos adicionais via `fields` parameter:**
     - `Microsoft.VSTS.Common.Severity`: Severidade selecionada
     - `Microsoft.VSTS.TCM.SystemInfo`: Informações do ambiente

4. Capturar o **Bug ID** retornado pelo MCP

5. **[OBRIGATÓRIO]** Se evidências foram informadas:
   a. **SEMPRE** executar script TypeScript de upload:
      ```bash
      npx tsx fastqa/scripts/azure-devops/commands/upload-evidence.command.ts \
        --work-item-id {Bug ID capturado no passo 4} \
        --evidence-path "{caminho informado no passo 1}"
      ```
   b. O script fará:
      - Upload de todos os arquivos de evidência (screenshots, vídeos, logs)
      - Anexação automática ao Bug criado
      - Exibição do resumo de arquivos anexados

6. **[OBRIGATÓRIO]** Se US/PBI relacionada foi informada:
   a. **SEMPRE** usar **MCP Azure DevOps** para vincular: `mcp_azuredevops_manage_work_item_link`
   b. Parâmetros corretos:
      - `workitemid`: ID do Bug (source)
      - `linktoworkitemid`: ID do work item relacionado (target)  
      - `linktype`: Tipo de link Azure DevOps (usar strings completas como "Microsoft.VSTS.Common.TestedBy-Forward" ou "System.LinkTypes.Hierarchy-Forward")
      - `comment`: Comentário do vínculo (ex: "Bug relacionado à User Story/PBI - vinculado via FastQA")
   c. **IMPORTANTE:** Para "related" usar "System.LinkTypes.Related", para hierarquia usar "System.LinkTypes.Hierarchy-Forward"
   d. Exemplo de chamada:
      ```typescript
      mcp_azuredevops_manage_work_item_link({
        workitemid: 11,
        linktoworkitemid: 5,
        linktype: "System.LinkTypes.Related",
        comment: "Bug relacionado à User Story/PBI - vinculado via FastQA"
      })
      ```
   ❌ **NUNCA** usar scripts TypeScript para vincular work items
   ❌ **NUNCA** executar `link-work-items.command.ts` (não deve existir)

7. Exibir resumo completo:
   - Bug ID e URL
   - Severidade e Prioridade
   - Quantidade de evidências anexadas
   - Vínculo com US/PBI (se aplicável) - tipo de link usado e comentário

8. Perguntar se deseja executar alguma ação adicional

**Parâmetros MCP (`mcp_microsoft_azu_wit_create_work_item`):**
- `project` (obrigatório) — Nome do projeto Azure DevOps
- `work_item_type` (obrigatório) — "Bug"
- `title` (obrigatório) — Título do bug
- `description` (opcional) — HTML formatado com passos, resultado esperado/obtido, ambiente
- `priority` (opcional) — 1 a 4 (padrão: derivado da severidade)
- `tags` (opcional) — Tags separadas por vírgula
- `assigned_to` (opcional) — Email do responsável
- `area_path` (opcional) — Área do projeto
- `iteration_path` (opcional) — Iteração/Sprint
- **Campos customizados via parameter `fields`:**
  - `Microsoft.VSTS.TCM.ReproSteps`: HTML com passos + resultados + ambiente
  - `Microsoft.VSTS.Common.Severity`: "1 - Critical" | "2 - High" | "3 - Medium" | "4 - Low"
  - `Microsoft.VSTS.TCM.SystemInfo`: Informações do ambiente (Browser, OS, etc.)

**Parâmetros Script TypeScript (apenas para upload):**
- `--work-item-id` (obrigatório) — ID do bug criado
- `--evidence-path` (obrigatório) — Caminho de arquivo ou pasta com evidências

**Ferramentas utilizadas:**
1. **Criação do Bug:** MCP Azure DevOps (`mcp_microsoft_azu_wit_create_work_item`)
2. **Vínculo com US/PBI:** MCP Azure DevOps (`mcp_azuredevops_manage_work_item_link`) — **SEMPRE via MCP**
3. **Upload de Evidências:** Script TypeScript `fastqa/scripts/azure-devops/commands/upload-evidence.command.ts`

**API Endpoints (via MCP e Script):**
1. MCP: `POST /_apis/wit/workitems/$Bug?api-version=7.1` — Criar bug
2. MCP: `PATCH /_apis/wit/workitems/{sourceId}?api-version=7.1` — Vincular work items (SEMPRE via MCP)
3. Script TS: `POST /_apis/wit/attachments?api-version=7.1` — Upload de evidências
4. Script TS: `PATCH /_apis/wit/workitems/{bugId}?api-version=7.1` — Anexar evidências ao bug

**⚠️ IMPORTANTE - Tipos de Link:**
- Use `"related"` (mais flexível) quando o bug se relaciona ao work item
- Use `"child"` apenas se o bug deve ser filho direto (pode gerar erro se work item já tem pai)
- Use `"parent"` se o work item deve ser pai do bug

---

### 📝 5. `@fastqa:azdo_create_test_case` — Criar Test Case com Steps (Azure DevOps MCP + TypeScript)

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 5

Cria um test case no Azure DevOps com steps estruturados. Suporta criação manual ou conversão automática de cenários Gherkin.

> **⚠️ REGRAS DE TECNOLOGIA:**
> - ✅ **PRIMÁRIO:** Usar **MCP Azure DevOps** (`azureDevOps` conforme `.vscode/mcp.json`) para criação individual
> - ✅ **FALLBACK:** Se MCP falhar (auth, timeout, etc.), usar script TypeScript: `npx tsx fastqa/scripts/azure-devops/commands/create-test-case.command.ts`
> - ✅ **BATCH (Journey):** Para criação em lote (múltiplos cenários de um `.feature`), usar: `npx tsx fastqa/scripts/azure-devops/commands/batch-create-test-cases.command.ts`
> - ❌ **NÃO** utilizar Playwright MCP
>
> **📋 Modo Journey/Batch:** Quando executado dentro da jornada Full Automation Cycle (Step 14), SEMPRE usar o script de batch para criar todos os TCs de uma vez, vinculando ao PBI e adicionando às suites corretas numa única execução.

#### 🔄 Modo Batch (Journey — Step 14)

Quando executado na jornada, usar o script de batch que:
1. Parseia o `.feature` separando cada `Scenario` individualmente
2. Cria 1 TC por `Scenario` com título numerado: `{n} - {nome do cenário}`
3. Vincula cada TC como **child** do PBI (parent)
4. Adiciona cada TC à suite correspondente via `--suite-map`

**Comando:**
```bash
npx tsx fastqa/scripts/azure-devops/commands/batch-create-test-cases.command.ts \
  --feature-file fastqa/manual_test/test_cases/{pasta}/{PBI}.feature \
  --parent-id {PBI_ID} \
  --plan-id {PLAN_ID} \
  --suite-map '{"1-2": SUITE_SMOKE, "3-4": SUITE_AUTH, ...}' \
  [--area-path "Project\\Area"] \
  [--iteration "Project\\Sprint"] \
  [--tags "pbi-{ID}; fastqa"]
```

**Parâmetros do script batch:**
- `--feature-file` (obrigatório) — Caminho do arquivo `.feature`
- `--parent-id` — ID do PBI para vincular TCs como children
- `--plan-id` — ID do Test Plan
- `--suite-id` — Suite única para todos os TCs
- `--suite-map` — JSON mapeando ranges de cenários para suite IDs (ex: `{"1-2":49,"3-4":50}`)
- `--area-path` — Area Path do projeto
- `--iteration` — Iteration Path
- `--tags` — Tags separadas por ponto e vírgula

**Tecnologia:** MCP Azure DevOps — servidor `azureDevOps` configurado em `.vscode/mcp.json`

**Workflow:**
1. Solicitar o **Nome do Projeto Azure DevOps** e **AGUARDAR** resposta do usuário

2. Solicitar uma das opções e **AGUARDAR** resposta:
   - **Opção 1:** Criar manualmente — informar título e steps (ação + resultado esperado)
   - **Opção 2:** Gerar a partir de um arquivo `.feature` — Gherkin → Test Case Steps
   - **Opção 3:** Gerar a partir de cenário Gherkin colado no chat

3. **Se Opção 1 (Manual):**
   - Solicitar: **Título**, **Pré-condições**, e **Steps** no formato:
     | # | Ação | Resultado Esperado |
     |---|------|-------------------|
     | 1 | Acessar /login | Página de login exibida |
     | 2 | Preencher credenciais | Campos preenchidos |
     | 3 | Clicar "Entrar" | Redirect para dashboard |

4. **Se Opção 2 (Arquivo .feature):**
   - Solicitar caminho do arquivo `.feature` e **AGUARDAR**
   - Ler arquivo e parsear cenários Gherkin
   - **[OPCIONAL]** Se existir `Background` no arquivo, perguntar se deseja incluí-lo no campo Description e **AGUARDAR** resposta:
     - **Se Sim:** Incluir Background no campo **Description** do Test Case com formato: **Background (Contexto):** [texto do background]
     - **Se Não:** Usar apenas título do cenário na descrição
   - Para cada `Scenario`, montar os steps preservando o texto **literal** de cada linha Gherkin:
     - Incluir APENAS os steps do cenário (`Given`, `When`, `Then`, `And`, `But`) **sem reescrita**
     - **Background NUNCA é incluído nos steps XML**
     - Não resumir, não traduzir e não quebrar steps
   - **NUMERAÇÃO OBRIGATÓRIA:** Cada `Scenario` vira um Test Case separado com título numerado: "1 ", "2 ", "3 ", etc.
   - Formato do título: `{número} - {nome original do cenário}`

5. **Se Opção 3 (Gherkin no chat):**
   - Receber texto Gherkin no chat e parsear
   - **[OPCIONAL]** Se existir `Background` no texto Gherkin, perguntar se deseja incluí-lo no campo Description e **AGUARDAR** resposta:
     - **Se Sim:** Incluir Background no campo **Description** do Test Case com formato: **Background (Contexto):** [texto do background]
     - **Se Não:** Usar apenas título do cenário na descrição
   - **NUMERAÇÃO OBRIGATÓRIA:** Aplicar mesma conversão da Opção 2 com títulos numerados: "1 ", "2 ", "3 ", etc.
   - Formato do título: `{número} - {nome original do cenário}`

6. **Perguntar sobre Sprint/Iteration** e **AGUARDAR** resposta:
   - "Deseja associar este Test Case a uma Sprint/Iteração específica?"
   - **Se Sim:** Solicitar o nome completo da Sprint/Iteration usando o formato do projeto (ex: "IA - Projetos Assistenciais\2026\1TRI2026\Sprint 2")
   - **Se Não:** Usar iteração padrão do projeto ou deixar sem associação específica
   - **Campo:** **Iteration Path** (System.IterationPath) — Sprint/Iteração

7. **Converter steps para formato XML do Azure DevOps (preservando linha literal):**
   ```xml
    <steps id="0" last="4">
     <step id="1" type="ActionStep">
          <parameterizedString isformatted="true">Given que o usuário acessa "https://www.avanade.com/pt-br"</parameterizedString>
          <parameterizedString isformatted="true">Página da Avanade deve ser carregada</parameterizedString>
     </step>
     <step id="2" type="ActionStep">
          <parameterizedString isformatted="true">When a página inicial termina de carregar</parameterizedString>
          <parameterizedString isformatted="true">Página deve estar completamente carregada</parameterizedString>
     </step>
     <step id="3" type="ActionStep">
          <parameterizedString isformatted="true">Then a logo da Avanade deve estar visível no cabeçalho</parameterizedString>
          <parameterizedString isformatted="true">Logo da Avanade deve ser exibida no cabeçalho</parameterizedString>
       </step>
       <step id="4" type="ActionStep">
          <parameterizedString isformatted="true">And a logo deve estar sem distorções visuais</parameterizedString>
          <parameterizedString isformatted="true">Logo deve ser exibida sem distorções</parameterizedString>
     </step>
   </steps>
   ```

    > **⚠️ Regra obrigatória:** no XML do campo `Microsoft.VSTS.TCM.Steps`, cada step deve conter exatamente a linha completa do `.feature` referente APENAS aos steps do Scenario. **Background NUNCA é incluído nos steps XML** - Background vai apenas no campo Description (se o usuário escolher essa opção).
    > 
    > **📝 Estrutura do XML:** Cada `<step>` tem dois `<parameterizedString>`:
    > - **Primeiro:** Ação literal do Gherkin (Given/When/Then/And/But + texto)
    > - **Segundo:** Resultado esperado derivado da ação (sem repetir o texto da ação)

7.1. **Preparar campo Description (se Background incluído):**
   - Se Background foi incluído na resposta do passo 4/5, formatar o campo `description` com:
   ```
   **Background (Contexto):** [Texto completo linha por linha do Background do .feature]
   ```
   
   **Exemplo:**
   ```
   **Background (Contexto):**                     Given que sou um gestor Administrativo Operacional                                     And que estou autenticado no sistema

   **Cenário:** Sistema disponibilizar tela administrativa para parametrização
   ```
   
   - Se Background NÃO foi incluído, usar descrição padrão do cenário

8. **Criar o test case usando MCP Azure DevOps** (`mcp_microsoft_azu_wit_create_work_item`):
   - **project:** Nome do projeto
   - **workItemType:** "Test Case"
   - **fields:** Array de objetos com name/value:
     - `{"name": "System.Title", "value": "Título informado"}`
     - `{"name": "System.Description", "value": "Campo preparado no passo 7.1"}`
     - `{"name": "Microsoft.VSTS.TCM.Steps", "value": "XML com steps literais APENAS do Scenario"}`
     - `{"name": "Microsoft.VSTS.Common.Priority", "value": "Prioridade (1 a 4)"}`
     - `{"name": "System.AreaPath", "value": "Área do projeto (se informado)"}`
     - `{"name": "System.IterationPath", "value": "Iteração/Sprint"}`
     - `{"name": "System.Tags", "value": "Tags separadas por ponto e vírgula"}`
     - `{"name": "Microsoft.VSTS.TCM.AutomatedTestName", "value": "Nome do teste automatizado"}`
     - `{"name": "Microsoft.VSTS.TCM.AutomationStatus", "value": "Not Automated"}`

9. Capturar o **Test Case ID** retornado pelo MCP

10. Exibir resumo formatado:
   ```markdown
   ✅ Test Case criado com sucesso!
   
   **ID:** #[ID]
   **Tipo:** Test Case
   **Título:** [Título]
   **Estado:** Design
   **Steps:** [Quantidade] steps criados
   **Prioridade:** [Prioridade]
   
   🔗 [Ver no Azure DevOps]([URL])
   ```

10. Perguntar se deseja executar alguma ação adicional:
    - Adicionar a uma Test Suite (`@fastqa:azdo_add_testcase_to_suite`)
    - Vincular a uma User Story (`@fastqa:azdo_link_work_items`)
    - Criar test cases adicionais do mesmo arquivo .feature

**Parâmetros MCP (`mcp_microsoft_azu_wit_create_work_item`):**
- `project` (obrigatório) — Nome do projeto Azure DevOps
- `workItemType` (obrigatório) — "Test Case"
- `fields` (obrigatório) — Array de objetos com campos name/value:
   - `{"name": "System.Title", "value": "Título do test case"}`
   - `{"name": "System.Description", "value": "Descrição com contexto do Background"}`
   - `{"name": "Microsoft.VSTS.TCM.Steps", "value": "XML com steps literais APENAS do Scenario"}`
   - `{"name": "Microsoft.VSTS.Common.Priority", "value": "1-4"}`
   - `{"name": "System.AreaPath", "value": "Área do projeto"}`
   - `{"name": "System.IterationPath", "value": "IA - Projetos Assistenciais\\2026\\1TRI2026\\Sprint 2"}`
   - `{"name": "System.Tags", "value": "Tags separadas por ponto e vírgula"}`
   - `{"name": "Microsoft.VSTS.TCM.AutomationStatus", "value": "Not Automated"}`
   - `{"name": "System.AssignedTo", "value": "Email do responsável"}`

**Configuração MCP utilizada (`.vscode/mcp.json`):**
```json
"azureDevOps": {
  "command": "npx",
  "args": ["-y", "@tiberriver256/mcp-server-azure-devops"],
  "env": {
    "AZURE_DEVOPS_ORG_URL": "...",
    "AZURE_DEVOPS_AUTH_METHOD": "pat",
    "AZURE_DEVOPS_PAT": "...",
    "AZURE_DEVOPS_DEFAULT_PROJECT": "..."
  }
}
```

**Ferramenta MCP:** `mcp_microsoft_azu_wit_create_work_item`

**API Endpoint (via MCP):** `POST /_apis/wit/workitems/$Test%20Case?api-version=7.1`

**Pré-requisitos:**
- MCP Azure DevOps configurado e **habilitado** em `.vscode/mcp.json` (servidor `azureDevOps`)
- PAT token válido nas variáveis de ambiente do MCP
- Variáveis `AZURE_DEVOPS_ORG_URL` e `AZURE_DEVOPS_DEFAULT_PROJECT` configuradas
- Servidor MCP Azure DevOps **ativo** (verificar no painel MCP do VS Code)

---

### ✏️ 6. `@fastqa:azdo_update_work_item` — Atualizar Work Item

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 6

Atualiza campos de um work item existente no Azure DevOps, com suporte opcional para upload de evidências.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando utiliza **MCP Azure DevOps** para atualizações e **TypeScript** apenas para upload de evidências:
> - ✅ **SEMPRE** usar **MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`) para atualizar work item via `mcp_microsoft_azu_wit_update_work_item`
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/upload-evidence.command.ts` para anexar evidências (se informadas)
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ❌ **NUNCA** utilizar script `update-work-item.command.ts` - atualizar via MCP

**Tecnologia:** MCP Azure DevOps (atualização) + TypeScript (upload de evidências)

**Workflow:**
1. Solicitar **ID do Work Item** e **AGUARDAR** resposta
2. Buscar dados atuais usando **MCP Azure DevOps** (`mcp_microsoft_azu_wit_get_work_item`)
3. Exibir campos atuais e perguntar quais deseja atualizar:
   - Título, Descrição, Estado, Atribuído a, Severidade, Prioridade, Tags, Área, Iteração, etc.
4. **AGUARDAR** novos valores do usuário
5. Solicitar **Evidências** (opcional) — Caminho de screenshots/vídeos para anexar
6. Executar atualização usando **MCP Azure DevOps** (`mcp_microsoft_azu_wit_update_work_item`)
7. Capturar o **Work Item ID** retornado
8. **[OBRIGATÓRIO]** Se evidências foram informadas:
   a. **SEMPRE** executar script TypeScript de upload:
      ```bash
      npx tsx fastqa/scripts/azure-devops/commands/upload-evidence.command.ts \
        --work-item-id {Work Item ID} \
        --evidence-path "{caminho informado no passo 5}"
      ```
   b. O script fará upload e anexação automática das evidências
9. Exibir diff dos campos atualizados (antes → depois) e quantidade de evidências anexadas

**Parâmetros MCP (`mcp_microsoft_azu_wit_update_work_item`):**
- `project` (obrigatório) — Nome do projeto Azure DevOps
- `work_item_id` (obrigatório) — ID do work item a ser atualizado
- `fields` (obrigatório) — Objeto JSON com campos a atualizar:
  ```json
  {
    "System.State": "Active",
    "System.AssignedTo": "user@email.com",
    "System.Tags": "regression; sprint-15"
  }
  ```
- `evidence_path` (opcional) — Caminho de arquivo ou pasta com evidências para anexar
- `comment` (opcional) — Comentário na atualização (histórico)

**Ferramenta MCP:** `mcp_microsoft_azu_wit_update_work_item`

**API Endpoint (via MCP):** `PATCH /_apis/wit/workitems/{id}?api-version=7.1`

---

### 🔗 7. `@fastqa:azdo_link_work_items` — Vincular Work Items

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 7

Cria vínculo entre dois work items no Azure DevOps.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **MCP Azure DevOps**:
> - ✅ **SEMPRE** usar: `mcp_azuredevops_manage_work_item_link` (MCP Azure DevOps)
> - ❌ **NUNCA** utilizar script TypeScript `link-work-items.command.ts`
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ❌ **NUNCA** executar `npx tsx` para vincular work items

**Tecnologia:** MCP Azure DevOps (servidor `azureDevOps` em `.vscode/mcp.json`)

**Workflow:**
1. Solicitar informações e **AGUARDAR** resposta:
   - **Source ID** — ID do work item de origem
   - **Target ID** — ID do work item de destino
   - **Tipo de Link** — Apresentar opções:
     - `related` — Relacionado a (mais flexível, recomendado)
     - `parent` — É pai de
     - `child` — É filho de
     - `duplicate` — Duplicata de
     - `affects` — Afeta (usado para bugs)
     - `tested by` — É testado por (Test Case testa Work Item)
     - `tests` — Testa (Work Item é testado por Test Case)
   - **Comentário** (opcional) — Descrição do vínculo

2. **Executar usando MCP Azure DevOps:**
   ```typescript
   mcp_azuredevops_manage_work_item_link({
     workitemid: sourceId,
     linktoworkitemid: targetId,
     linktype: "System.LinkTypes.Related", // ou outro tipo Azure DevOps
     comment: "Comentário do vínculo" // opcional
   })
   ```

3. **Tratamento de erros:**
   - Se erro "work item can have only one Parent link" ao usar tipo hierarquia:
     - Automaticamente tentar novamente com tipo "System.LinkTypes.Related"
     - Informar ao usuário que foi usado tipo relacionado por limitação do Azure DevOps
   
4. Confirmar vínculo criado com:
   - IDs dos work items vinculados
   - Tipo de link utilizado
   - Comentário (se fornecido)
   - Iteração atualizada (se aplicável) — indicar se o work item de destino teve a iteração alterada
   - URLs diretos para ambos os work items no Azure DevOps

**Mapeamento de link types (Azure DevOps REST API):**
| Tipo MCP | Tipo Azure DevOps | Uso Recomendado | Observações |
|----------|------------------|-----------------|-------------|
| `related` | `System.LinkTypes.Related` | Relacionamento geral | ✅ **Mais flexível** - use quando não há hierarquia clara |
| `parent` | `System.LinkTypes.Hierarchy-Reverse` | Work item é pai | ⚠️ Cuidado: work item pode ter apenas 1 pai |
| `child` | `System.LinkTypes.Hierarchy-Forward` | Work item é filho | ⚠️ Pode falhar se já existe pai - use `related` como fallback |
| `duplicate` | `System.LinkTypes.Duplicate-Forward` | Duplicatas | Para marcar work items duplicados |
| `affects` | `Microsoft.VSTS.Common.Affects-Forward` | Bug afeta work item | Usado principalmente para bugs |
| `Tested by` | `Microsoft.VSTS.Common.TestedBy-Forward` | Test Case testa Work Item | 📝 **FUNCIONA DE PRIMEIRA** - Para vincular Test Cases com User Stories/PBIs |
| `tests` | `Microsoft.VSTS.Common.TestedBy-Reverse` | Work Item é testado por Test Case | 📝 Para vincular User Stories/PBIs com Test Cases |

**Parâmetros MCP (`mcp_azuredevops_manage_work_item_link`):**
- `workitemid` (obrigatório) — ID do work item de origem
- `linktoworkitemid` (obrigatório) — ID do work item de destino  
- `linktype` (obrigatório) — Tipo do vínculo Azure DevOps (usar valores da tabela acima)
- `comment` (opcional) — Comentário descritivo do vínculo

**Ferramenta MCP:** `mcp_azuredevops_manage_work_item_link`

**API Endpoint (via MCP):** `PATCH /_apis/wit/workitems/{sourceId}?api-version=7.1`

---

### 📎 8. `@fastqa:azdo_upload_evidence` — Upload de Evidência Individual

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 8

Faz upload de **um arquivo** de evidência para um Work Item no Azure DevOps.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/upload-evidence.command.ts`
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ✅ Script inclui normalização automática de paths Windows (converte \\ para /)

**Tecnologia:** TypeScript nativo com Node.js fetch API

**Workflow:**
1. Solicitar informações e **AGUARDAR** resposta do usuário:
   - **Work Item ID** (obrigatório)
   - **Caminho da Evidência** — Arquivo (.mp4, .webm, .png, .jpg, .pdf, .html, etc.)
   - **Comentário** (opcional)
2. Validar:
   - ✅ Arquivo existe e não excede 130 MB
   - ✅ Work Item informado existe
   - ✅ Credenciais configuradas no `.env`
3. Executar script: `fastqa/scripts/azure-devops/commands/upload-evidence.command.ts`
4. O script executa a sequência:
   a. Converte arquivo para Base64
   b. Faz upload do attachment (POST wit/attachments)
   c. Anexa ao Work Item informado (PATCH wit/workitems/{id})
   d. Registra comentário (se informado)
5. Exibir: Work Item ID e URL do anexo no Azure DevOps
6. Salvar IDs em: `fastqa/scripts/azure-devops/logs/`

**Parâmetros:**
- `--work-item-id` (obrigatório)
- `--evidence-path` (obrigatório) — Caminho completo do arquivo
- `--comment` (opcional) — Comentário sobre a execução

**Script:** `fastqa/scripts/azure-devops/commands/upload-evidence.command.ts`

**API Endpoints (sequência):**
1. `POST /_apis/wit/attachments?api-version=7.1`
2. `PATCH /_apis/wit/workitems/{workItemId}?api-version=7.1`

**Payload de Upload (campo `stream` em Base64):**
```json
{
  "stream": "<base64-encoded-file>",
  "fileName": "evidencia.mp4",
  "comment": "Evidência de teste TS-001",
  "attachmentType": "GeneralAttachment"
}
```

---

### 📁 9. `@fastqa:azdo_upload_folder_evidence` — Upload de Pasta de Evidências

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 9

Faz upload de **todos os arquivos** de uma pasta de evidências para um Work Item.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/upload-folder-evidence.command.ts`
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ✅ Script inclui normalização automática de paths Windows

**Tecnologia:** TypeScript nativo com Node.js fetch API

**Workflow:**
1. Solicitar informações e **AGUARDAR** resposta:
   - **Work Item ID** (obrigatório)
   - **Caminho da Pasta** — Ex: `fastqa/manual_test/evidence/TS-001/`
   - **Comentário** (opcional)
2. Validar:
   - ✅ Pasta existe e contém arquivos
   - ✅ Work Item informado existe
   - ✅ Extensões suportadas: `.mp4`, `.webm`, `.avi`, `.png`, `.jpg`, `.gif`, `.pdf`, `.html`, `.txt`, `.md`, `.json`, `.xlsx`, `.docx`
   - ✅ Nenhum arquivo excede 130 MB
3. Executar script: `fastqa/scripts/azure-devops/commands/upload-folder-evidence.command.ts`
4. O script executa:
   a. Lista todos os arquivos da pasta (recursivo por padrão)
   b. Para cada arquivo: converte para Base64 e faz upload como attachment
   c. Anexa todos os attachments ao Work Item informado
   d. Registra comentário (se informado)
5. Exibir relatório de upload:
   - Quantidade de arquivos enviados
   - Tamanho total transferido
   - Status individual de cada arquivo (✅ sucesso / ❌ falha)
   - URLs dos anexos no Azure DevOps

**Parâmetros:**
- `--work-item-id` (obrigatório)
- `--folder-path` (obrigatório) — Caminho da pasta com evidências
- `--comment` (opcional)
- `--recursive` (opcional) — Buscar em subpastas (padrão: `true`)
- `--extensions` (opcional) — Filtrar por extensões: `".png,.mp4,.pdf"`

**Script:** `fastqa/scripts/azure-devops/commands/upload-folder-evidence.command.ts`

**Exemplo de execução:**
```bash
npx tsx fastqa/scripts/azure-devops/commands/upload-folder-evidence.command.ts \
   --work-item-id 5 \
   --folder-path "fastqa/manual_test/evidence/TS-001" \
   --comment "teste upload"
```

> **📌 Nota de escopo:** `upload-folder-evidence.command.ts` é exclusivo para anexos em **Work Item**. Fluxos de **Test Run/Test Result** continuam nos comandos específicos de execução (`upload-test-execution.command.ts` e `upload-batch-test-execution.command.ts`).

---

### 🚀 10. `@fastqa:azdo_upload_test_execution` — Execução Completa de Teste

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 10

Executa o fluxo completo de teste em uma única operação: cria Test Run, faz upload de evidências, atualiza status, finaliza e opcionalmente cria bug.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts`
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ✅ Script inclui criação automática de bug se resultado = Failed

**Tecnologia:** TypeScript nativo com Node.js fetch API

**Workflow:**
1. Solicitar informações e **AGUARDAR** resposta:
   - **Test Plan ID**
   - **Test Suite ID**
   - **Test Case ID**
   - **Caminho da Evidência** — Arquivo individual ou pasta
   - **Resultado** — `Passed` | `Failed` | `Blocked` | `NotApplicable`
   - **Comentário** (opcional)
   - **Anexar ao Work Item?** (Sim/Não — padrão: Não)
   - **Criar Bug automaticamente?** (Sim/Não — apenas se resultado = `Failed`)
2. Executar script: `fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts`
3. O script executa em sequência:
   a. Verifica associação Test Case → Suite
   b. Adiciona Test Case à Suite se necessário (auto-fix)
   c. Obtém Test Point ID
   d. Cria Test Run
   e. Obtém Test Result ID
   f. Detecta se `evidence-path` é arquivo ou pasta:
      - **Arquivo:** upload individual
      - **Pasta:** upload de todos os arquivos
   g. Atualiza outcome do Test Result com comentário
   h. Finaliza Test Run com status `Completed`
   i. **(Se `--auto-bug` e resultado = `Failed`)** Cria Bug automaticamente:
      - Título: `[AUTO-BUG] Falha no TC-{id}: {título do test case}`
      - Repro Steps: Steps do Test Case + comentário
      - Severity: conforme `--bug-severity` (padrão: `3 - Medium`)
      - Vincula Bug ao Test Case (link type: `Tests`)
      - Anexa mesmas evidências ao Bug
   j. (Opcional) Anexa evidências ao Work Item
4. Exibir relatório completo:
   - ✅ Test Run ID + URL direta
   - ✅ Test Result ID + Outcome
   - ✅ Evidências anexadas (quantidade + tamanho total)
   - ✅ Bug ID + URL (se criado)
   - ✅ Links diretos no Azure DevOps
5. Salvar IDs em: `fastqa/scripts/azure-devops/logs/execution-{timestamp}.json`

**Parâmetros:**
- `--test-plan-id` (obrigatório)
- `--test-suite-id` (obrigatório)
- `--test-case-id` (obrigatório)
- `--evidence-path` (obrigatório) — Arquivo ou pasta
- `--result` (obrigatório) — `Passed` | `Failed` | `Blocked` | `NotApplicable`
- `--comment` (opcional) — Comentário sobre a execução
- `--attach-to-work-item` (opcional) — `true` | `false`
- `--auto-bug` (opcional) — Criar bug se Failed (padrão: `false`)
- `--bug-severity` (opcional) — Severidade do bug auto-criado (padrão: `3 - Medium`)

**Script:** `fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts`

---

### 📋 11. `@fastqa:azdo_list_test_plans` — Listar Test Plans e Suites

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 11

Lista Test Plans disponíveis no projeto com suas Test Suites e Test Cases.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **MCP Azure DevOps**:
> - ✅ **SEMPRE** usar **MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`) para listar test plans e suites
> - ✅ Usar ferramentas: `mcp_microsoft_azu_testplan_list`, `mcp_microsoft_azu_testplan_get_suites`, `mcp_microsoft_azu_testplan_get_test_cases`
> - ❌ **NUNCA** utilizar script `list-test-plans.command.ts` - listar via MCP
> - ❌ **NUNCA** utilizar PowerShell (.ps1)

**Tecnologia:** MCP Azure DevOps — servidor `azureDevOps` configurado em `.vscode/mcp.json`

**Workflow:**
1. Solicitar o **Nome do Projeto Azure DevOps** e **AGUARDAR** resposta do usuário
2. Opcionalmente perguntar por **Plan ID específico** ou **Suite ID específica** para filtrar
3. Executar listagem usando **MCP Azure DevOps**:
   a. Usar `mcp_microsoft_azu_testplan_list` para obter todos os test plans do projeto
   b. Para cada plan (ou plan específico), usar `mcp_microsoft_azu_testplan_get_suites` para obter suites
   c. Para cada suite, usar `mcp_microsoft_azu_testplan_get_test_cases` para obter test cases
4. Exibir hierarquia formatada:
   ```
   📋 Test Plan: "Sprint 15 - Testes" (ID: 110)
   ├── 📁 Suite: "Login" (ID: 112)
   │   ├── TC-45: Login com credenciais válidas         [✅ Passed]
   │   ├── TC-46: Login com senha incorreta             [❌ Failed]
   │   └── TC-47: Login com autenticação 2FA            [⏳ Not Run]
   ├── 📁 Suite: "Cadastro" (ID: 113)
   │   ├── TC-48: Cadastro de novo usuário              [✅ Passed]
   │   └── TC-49: Validação de campos obrigatórios      [✅ Passed]
   └── 📁 Suite: "API" (ID: 114)
       └── TC-50: GET /api/v1/users                     [⏳ Not Run]
   ```
5. Perguntar se deseja executar alguma ação com os IDs listados

**Parâmetros MCP:**
- `project` (obrigatório) — Nome do projeto Azure DevOps
- `plan_id` (opcional) — Filtrar suites de um plan específico
- `suite_id` (opcional) — Filtrar test cases de uma suite específica
- `show_results` (opcional) — Exibir último resultado de cada test case (padrão: `true`)

**Ferramentas MCP:**
- `mcp_microsoft_azu_testplan_list`
- `mcp_microsoft_azu_testplan_get_suites`
- `mcp_microsoft_azu_testplan_get_test_cases`

**API Endpoints (via MCP):**
- `GET /_apis/testplan/plans?api-version=7.1`
- `GET /_apis/testplan/Plans/{planId}/suites?api-version=7.1`
- `GET /_apis/testplan/Plans/{planId}/Suites/{suiteId}/TestCase?api-version=7.1`

---

### 📌 12. `@fastqa:azdo_add_testcase_to_suite` — Adicionar Test Case à Suite

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 12

Adiciona um ou mais Test Cases a uma Test Suite no Azure DevOps.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **MCP Azure DevOps**:
> - ✅ **SEMPRE** usar **MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`) para adicionar test cases à suite
> - ✅ Usar ferramenta: `mcp_microsoft_azu_testplan_add_test_case_to_suite`
> - ❌ **NUNCA** utilizar script `add-testcase-to-suite.command.ts` - adicionar via MCP
> - ❌ **NUNCA** utilizar PowerShell (.ps1)

**Tecnologia:** MCP Azure DevOps — servidor `azureDevOps` configurado em `.vscode/mcp.json`

**Workflow:**
1. Solicitar o **Nome do Projeto Azure DevOps** e **AGUARDAR** resposta do usuário
2. Solicitar informações e **AGUARDAR** resposta:
   - **Test Plan ID**
   - **Test Suite ID**
   - **Test Case IDs** — Um ou mais IDs separados por vírgula
3. Executar adição usando **MCP Azure DevOps**:
   - Usar ferramenta: `mcp_microsoft_azu_testplan_add_test_case_to_suite`
   - Para cada Test Case ID informado:
     - Verificar se já existe na Suite (evitar duplicatas)
     - Adicionar se não existir
     - Confirmar associação
4. Exibir resultado: IDs adicionados, IDs já existentes (ignorados)

**Parâmetros MCP (`mcp_microsoft_azu_testplan_add_test_case_to_suite`):**
- `project` (obrigatório) — Nome do projeto Azure DevOps
- `test_plan_id` (obrigatório) — ID do test plan
- `test_suite_id` (obrigatório) — ID da test suite
- `test_case_ids` (obrigatório) — Array de IDs dos test cases: `[45, 46, 47]`

**Ferramenta MCP:** `mcp_microsoft_azu_testplan_add_test_case_to_suite`

**API Endpoint (via MCP):** `POST /_apis/testplan/Plans/{planId}/Suites/{suiteId}/TestCase?api-version=7.1`

---

### � 13. `@fastqa:azdo_upload_batch_test_execution` — Upload de Múltiplas Execuções (Lote)

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 13

Processa múltiplas execuções de teste de uma vez no Azure DevOps, suportando entrada via arquivo JSON, CSV ou parâmetros inline.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/upload-batch-test-execution.command.ts`
> - ❌ **NUNCA** utilizar PowerShell (.ps1)

**Tecnologia:** TypeScript nativo com Node.js fetch API

**Workflow:**
1. Solicitar formato de entrada e **AGUARDAR** resposta do usuário:
   - **Opção 1:** Arquivo JSON (estruturado)
   - **Opção 2:** Arquivo CSV (planilha)  
   - **Opção 3:** Parâmetros inline (comando único)

2. **Se Opção 1 (JSON):**
   - Solicitar caminho do arquivo JSON e **AGUARDAR**
   - Se o arquivo não existir, perguntar se deseja criá-lo com template base e **AGUARDAR** resposta:
     - Se **Sim**: Criar arquivo no caminho informado com estrutura base
     - Se **Não**: Solicitar caminho de arquivo existente
   - Validar estrutura: `testPlanId`, `executions[]` 
   - **[NOVO]** Exibir conteúdo do arquivo carregado formatado no chat
   - **[NOVO]** Perguntar: "Confirma as informações do arquivo acima para prosseguir com a execução?" e **AGUARDAR** resposta:
     - Se **Sim**: Prosseguir para execução
     - Se **Não**: Permitir edição manual do arquivo e aguardar nova confirmação
     - Se **Editar**: Abrir arquivo para edição e aguardar confirmação posterior
   - Executar: `npx tsx upload-batch-test-execution.command.ts --json-file "caminho/arquivo.json"`

3. **Se Opção 2 (CSV):**
   - Solicitar Test Plan ID e caminho do arquivo CSV e **AGUARDAR**
   - Se o arquivo não existir, perguntar se deseja criá-lo com template base e **AGUARDAR** resposta:
     - Se **Sim**: Criar arquivo CSV no caminho informado com cabeçalho e linha exemplo
     - Se **Não**: Solicitar caminho de arquivo existente
   - Validar cabeçalho: `testSuiteId,testCaseId,result,evidencePath,comment,attachToWorkItem,autoBug,bugSeverity`
   - **[NOVO]** Exibir conteúdo do arquivo CSV formatado em tabela no chat
   - **[NOVO]** Perguntar: "Confirma as informações do arquivo CSV acima para prosseguir com a execução?" e **AGUARDAR** resposta:
     - Se **Sim**: Prosseguir para execução
     - Se **Não**: Permitir edição manual do arquivo e aguardar nova confirmação
     - Se **Editar**: Abrir arquivo para edição e aguardar confirmação posterior
   - Executar: `npx tsx upload-batch-test-execution.command.ts --csv-file "arquivo.csv" --test-plan-id 29`

4. **Se Opção 3 (Inline):**
   - Solicitar Test Plan ID e string de execuções e **AGUARDAR**
   - Formato: `suiteId:caseId:result:evidencePath:comment` separado por `|`
   - **[NOVO]** Exibir dados parseados em tabela formatada no chat
   - **[NOVO]** Perguntar: "Confirma os dados das execuções acima para prosseguir?" e **AGUARDAR** resposta:
     - Se **Sim**: Prosseguir para execução
     - Se **Não**: Permitir reentrada dos dados
   - Executar: `npx tsx upload-batch-test-execution.command.ts --test-plan-id 29 --executions "38:14:Passed:C:/evidence/TC-14:Teste 1|38:15:Failed:C:/evidence/TC-15:Teste 2"`

5. **[CONFIRMAÇÃO OBRIGATÓRIA]** Após confirmar os dados do arquivo/inline:
   - Exibir resumo final: Total de execuções, Test Plan ID, quantidade por resultado (Passed/Failed/etc.)
   - Perguntar: "Deseja prosseguir com a execução de {X} test cases no Azure DevOps?" e **AGUARDAR**
   - Se **Não**: Cancelar operação e voltar ao menu

6. **O script executa para cada execução sequencialmente:**
   a. Coleta arquivos de evidência do caminho especificado
   b. Obtém Test Point (Plan → Suite → Test Case)
   c. Cria Test Run individual no Azure DevOps
   d. Upload de evidências específicas ao Test Result
   e. Atualiza outcome (Passed/Failed/Blocked/NotApplicable)
   f. Finaliza Test Run com status "Completed"
   g. [Opcional] Cria Bug se `autoBug=true` e resultado = `Failed`
   h. [Opcional] Anexa evidências ao Work Item se `attachToWorkItem=true`
   i. Pausa de 1s entre execuções (evitar throttling da API)

7. **Exibir relatório consolidado:**
   - Total de execuções processadas
   - Taxa de sucesso/falha (% e números absolutos)
   - Test Runs criados
   - Evidências anexadas (total)
   - Bugs criados automaticamente (se aplicável)
   - Duração total do batch
   - Detalhamento individual por Test Case

8. **Salvar log detalhado em JSON:** `fastqa/scripts/azure-devops/logs/batch-execution-{timestamp}.json`

**Formatos de entrada suportados:**

**JSON (Estruturado - Recomendado):**
```json
{
  "testPlanId": 29,
  "executions": [
    {
      "testSuiteId": 38,
      "testCaseId": 14,
      "result": "Passed",
      "evidencePath": "C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-14",
      "comment": "Execução automatizada - Teste de logo no cabeçalho",
      "attachToWorkItem": true,
      "autoBug": false,
      "bugSeverity": "3 - Medium"
    },
    {
      "testSuiteId": 38,
      "testCaseId": 15,
      "result": "Failed",
      "evidencePath": "C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-15",
      "comment": "Falha na validação do formulário de login",
      "attachToWorkItem": false,
      "autoBug": true,
      "bugSeverity": "2 - High"
    }
  ]
}
```

**CSV (Planilha):**
```csv
testSuiteId,testCaseId,result,evidencePath,comment,attachToWorkItem,autoBug,bugSeverity
38,14,Passed,C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-14,Execução automatizada,true,false,3 - Medium
38,15,Failed,C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-15,Falha na validação,false,true,2 - High
39,16,Blocked,C:/projetos/avanade-code-qa/fastqa/manual_test/evidence/TC-16,Dependência externa,true,false,4 - Low
```

**Inline (Comando único):**
```bash
# Formato: suiteId:caseId:result:evidencePath:comment separado por |
--executions "38:14:Passed:C:/evidence/TC-14:Teste 1|38:15:Failed:C:/evidence/TC-15:Teste 2"
```

**Parâmetros:**
- `--json-file <caminho>` (opção 1) — Caminho para arquivo JSON estruturado com testPlanId e executions
- `--csv-file <caminho> --test-plan-id <id>` (opção 2) — Caminho para CSV + Test Plan ID separado
- `--executions <string> --test-plan-id <id>` (opção 3) — Execuções inline + Test Plan ID

**Campos obrigatórios para cada execução:**
| Campo | Tipo | Descrição | Valores Aceitos |
|-------|------|-----------|-----------------|
| `testSuiteId` | number | ID da Test Suite no Azure DevOps | Número inteiro |
| `testCaseId` | number | ID do Test Case no Azure DevOps | Número inteiro |
| `result` | string | Resultado da execução | `Passed`, `Failed`, `Blocked`, `NotApplicable` |
| `evidencePath` | string | Caminho para arquivo/pasta de evidências | Caminho absoluto ou relativo |

**Campos opcionais:**
| Campo | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `comment` | string | — | Comentário sobre a execução |
| `attachToWorkItem` | boolean | `false` | Anexar evidências ao Work Item também |
| `autoBug` | boolean | `false` | Criar bug automaticamente se resultado = Failed |
| `bugSeverity` | string | `3 - Medium` | Severidade do bug auto-criado |

**Validações automáticas:**
- ✅ **Arquivos de evidência** — Verifica se existem nos caminhos especificados
- ✅ **Associação Test Case → Suite** — Valida se TC está na Suite informada
- ✅ **Formatos de arquivo** — JSON/CSV estruturalmente corretos
- ✅ **Campos obrigatórios** — testSuiteId, testCaseId, result, evidencePath preenchidos
- ✅ **Valores de resultado** — Passed | Failed | Blocked | NotApplicable
- ✅ **Valores de severidade** — 1 - Critical | 2 - High | 3 - Medium | 4 - Low
- ✅ **Credenciais Azure DevOps** — PAT token válido configurado no .env

**Exemplo de saída do relatório:**
```
📊 RESUMO DO BATCH EXECUTION
═══════════════════════════════════════

   Test Plan:       #29
   Total Execuções: 4
   ✅ Sucessos:     3 (75.0%)
   ❌ Falhas:       1
   Test Runs:       4 criados  
   Evidências:      15 anexadas
   Bugs:            1 criados
   Duração Total:   45.3s

📋 DETALHAMENTO POR EXECUÇÃO:
   ✅ TC-14: 8.2s | Evidências: 5
   ❌ TC-15: 12.1s | Evidências: 0
      Erro: Test Point não encontrado para TC-15 na Suite 38
   ✅ TC-16: 15.7s | Evidências: 3
   ✅ TC-17: 9.3s | Evidências: 7

   📝 Log detalhado salvo em: C:/projetos/.../logs/batch-execution-1771623456789.json
```

**Script:** `fastqa/scripts/azure-devops/commands/upload-batch-test-execution.command.ts`

**Arquivos de exemplo:** 
- `fastqa/scripts/azure-devops/examples/batch-executions-example.json`
- `fastqa/scripts/azure-devops/examples/batch-executions-example.csv`

**API Endpoints (para cada execução):**
- `GET /_apis/testplan/Plans/{planId}/Suites/{suiteId}/TestPoint?testCaseId={caseId}&api-version=7.1`
- `POST /_apis/test/runs?api-version=7.1`
- `GET /_apis/test/runs/{runId}/results?api-version=7.1`
- `POST /_apis/test/runs/{runId}/results/{resultId}/attachments?api-version=7.1`
- `PATCH /_apis/test/runs/{runId}/results?api-version=7.1`
- `PATCH /_apis/test/runs/{runId}?api-version=7.1`

---

### 📊 14. `@fastqa:azdo_generate_report` — Gerar Relatório de Execução

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 14

Gera relatório consolidado de execução de testes em formato Markdown.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **MCP Azure DevOps**:
> - ✅ **SEMPRE** usar **MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`) para obter dados dos test plans, runs e results
> - ✅ Usar ferramentas: `mcp_microsoft_azu_testplan_list`, `mcp_microsoft_azu_testplan_get_suites`, `mcp_microsoft_azu_testplan_get_test_cases`
> - ❌ **NUNCA** utilizar script `generate-report.command.ts` - gerar via MCP
> - ❌ **NUNCA** utilizar PowerShell (.ps1)

**Tecnologia:** MCP Azure DevOps — servidor `azureDevOps` configurado em `.vscode/mcp.json`

**Workflow:**
1. Solicitar uma das opções e **AGUARDAR** resposta:
   - **Opção 1:** Relatório por **Test Plan ID** — todas as suites e resultados
   - **Opção 2:** Relatório por **Test Run ID** — resultados de uma execução específica (não suportado via MCP)
   - **Opção 3:** Relatório por **Test Suite ID** — test cases e resultados da suite
2. **Se Opção 1 (Test Plan):**
   - Usar **MCP Azure DevOps** (`mcp_microsoft_azu_testplan_list`) para obter dados do test plan
   - Usar `mcp_microsoft_azu_testplan_get_suites` para obter todas as suites do plan
   - Para cada suite, usar `mcp_microsoft_azu_testplan_get_test_cases` para obter test cases
3. **Se Opção 3 (Test Suite):**
   - Usar **MCP Azure DevOps** (`mcp_microsoft_azu_testplan_get_test_cases`) para obter test cases da suite
   - Coletar informações de execução disponíveis
4. **Coletar dados para o relatório:**
   - Total de Test Cases na seleção
   - Distribuição de resultados por estado: Design, Active, Ready, Closed
   - Test Cases executados vs não executados
   - Evidências anexadas (através de work item attachments)
   - Bugs vinculados aos test cases
5. **Gerar relatório Markdown** formatado com:
   - Cabeçalho com dados do plano/suite
   - Dashboard de resumo com métricas
   - Tabela detalhada de resultados por test case
   - Seção de bugs vinculados (se houver)
   - Métricas de cobertura (% por estado, % com evidências)
6. **Salvar relatório** em: `fastqa/manual_test/evidence/reports/report-{id}-{timestamp}.md`
7. **Exibir resumo** com caminho do arquivo gerado e principais métricas

**Parâmetros MCP:**
- `project` (obrigatório) — Nome do projeto Azure DevOps
- `plan_id` (opcional) — ID do test plan para relatório completo
- `suite_id` (opcional) — ID da test suite para relatório específico
- `include_details` (opcional) — Incluir detalhes completos dos test cases (padrão: `true`)

**Ferramentas MCP:**
- `mcp_microsoft_azu_testplan_list` — Listar test plans
- `mcp_microsoft_azu_testplan_get_suites` — Obter suites de um plan
- `mcp_microsoft_azu_testplan_get_test_cases` — Obter test cases de uma suite
- `mcp_microsoft_azu_wit_get_work_item` — Obter detalhes de test cases individuais (se necessário)

**API Endpoints (via MCP):**
- `GET /_apis/testplan/plans?api-version=7.1`
- `GET /_apis/testplan/Plans/{planId}/suites?api-version=7.1`  
- `GET /_apis/testplan/Plans/{planId}/Suites/{suiteId}/TestCase?api-version=7.1`

**Configuração MCP utilizada (`.vscode/mcp.json`):**
```json
"azureDevOps": {
  "command": "npx",
  "args": ["-y", "@tiberriver256/mcp-server-azure-devops"],
  "env": {
    "AZURE_DEVOPS_ORG_URL": "...",
    "AZURE_DEVOPS_AUTH_METHOD": "pat",
    "AZURE_DEVOPS_PAT": "...",
    "AZURE_DEVOPS_DEFAULT_PROJECT": "..."
  }
}
```

**Exemplo de Relatório Gerado:**

```markdown
# 📊 Relatório de Execução de Testes

**Test Plan:** Sprint 15 — Testes de Regressão (ID: 110)
**Data:** 19/02/2026 14:30
**Executado por:** QA Team

---

## Resumo Executivo

| Métrica            | Valor     |
|--------------------|-----------|
| Total de Test Cases | 25       |
| ✅ Passed           | 20 (80%) |
| ❌ Failed           | 3 (12%)  |
| ⚠️ Blocked          | 1 (4%)   |
| ⏳ Not Run          | 1 (4%)   |
| 📎 Evidências       | 23       |
| 🐛 Bugs Criados     | 3        |

---

## Detalhamento por Test Case

| TC ID  | Título                      | Resultado   | Evidência       | Bug     |
|--------|-----------------------------|-------------|-----------------|---------|
| TC-45  | Login com credenciais válidas | ✅ Passed  | video.mp4       | —       |
| TC-46  | Login com senha incorreta     | ❌ Failed  | screenshot.png  | BUG-123 |
| TC-47  | Login com 2FA                 | ⚠️ Blocked | —               | —       |
```

**Pré-requisitos:**
- MCP Azure DevOps configurado e **habilitado** em `.vscode/mcp.json` (servidor `azureDevOps`)
- PAT token válido nas variáveis de ambiente do MCP
- Variáveis `AZURE_DEVOPS_ORG_URL` e `AZURE_DEVOPS_DEFAULT_PROJECT` configuradas
- Servidor MCP Azure DevOps **ativo** (verificar no painel MCP do VS Code)

---

### 📤 15. `@fastqa:azdo_push_automation` — Push de Código de Automação para Repositório

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 15

Coleta os arquivos de automação gerados localmente e faz push para um repositório Azure DevOps, com suporte a criação de branch e detecção automática de plataforma/framework.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando utiliza **MCP Azure DevOps** para listar repositórios/branches e **TypeScript** para o push Git:
> - ✅ **SEMPRE** usar **MCP Azure DevOps** para listar repositórios (`mcp_microsoft_azu_repo_list_repos_by_project`) e branches (`mcp_microsoft_azu_repo_list_branches_by_repo`)
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/push-automation.command.ts` para o push Git REST API
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ❌ **NUNCA** utilizar `git` CLI diretamente — usar REST API via script TypeScript

**Tecnologia:** MCP Azure DevOps (listagem) + TypeScript (push Git via REST API)

**Workflow:**
1. Solicitar informações e **AGUARDAR** resposta do usuário:
   - **Repositório** (obrigatório) — Nome do repositório Azure DevOps
   - **Branch** (opcional) — Nome da branch de destino (padrão: `main`)
   - **Plataforma** (opcional) — `web` | `api` | `mobile` (auto-detectado do `project_config.json`)
   - **Mensagem de commit** (opcional) — Mensagem descritiva do push
   - **Criar branch?** (opcional) — Se a branch não existir, criar a partir de `--source-branch`
   - **Incluir shared?** (opcional) — Incluir pasta `automated_test/shared/` além da plataforma

2. Se repositório ou branch não forem informados, usar **MCP Azure DevOps** para listar opções:
   - `mcp_microsoft_azu_repo_list_repos_by_project` — Listar repositórios disponíveis
   - `mcp_microsoft_azu_repo_list_branches_by_repo` — Listar branches do repositório selecionado

3. Executar script TypeScript:
   ```bash
   npx tsx fastqa/scripts/azure-devops/commands/push-automation.command.ts \
     --repo "meu-repo" \
     --branch "feature/automated-tests" \
     --platform web \
     --message "feat: adicionar testes automatizados de login" \
     --create-branch \
     --source-branch main \
     --include-shared \
     --target-path "tests/e2e"
   ```

4. **O script executa:**
   a. Detecta plataforma e framework do `project_config.json` (se não especificado)
   b. Coleta arquivos de `automated_test/{platform}/` (e `shared/` se `--include-shared`)
   c. Resolve repositório por nome via Git API (`GET /_apis/git/repositories/{repoName}`)
   d. Se `--create-branch`: obtém SHA da `--source-branch` e cria nova branch via refUpdate
   e. Converte cada arquivo para Base64 e monta payload de push
   f. Executa push via `POST /_apis/git/repositories/{repoId}/pushes`
   g. Exibe resumo: arquivos enviados, commit ID, URLs

5. **Modo dry-run** (`--dry-run`): Lista arquivos que seriam enviados sem executar o push

6. Exibir resultado:
   ```markdown
   ✅ Push realizado com sucesso!
   
   **Repositório:** meu-repo
   **Branch:** feature/automated-tests
   **Commit:** abc1234
   **Arquivos:** 15 enviados (42.5 KB)
   **Plataforma:** web (Playwright + TypeScript)
   
   🔗 [Ver commit no Azure DevOps]([URL])
   ```

**Parâmetros:**
- `--repo` (obrigatório) — Nome do repositório Azure DevOps
- `--branch` (opcional, padrão: `main`) — Branch de destino
- `--platform` (opcional) — `web` | `api` | `mobile` (auto-detectado)
- `--message` (opcional) — Mensagem de commit
- `--create-branch` (flag) — Criar branch se não existir
- `--source-branch` (opcional, padrão: `main`) — Branch base para criação
- `--target-path` (opcional) — Caminho de destino no repositório (padrão: raiz)
- `--include-shared` (flag) — Incluir pasta `automated_test/shared/`
- `--dry-run` (flag) — Listar arquivos sem enviar

**Script:** `fastqa/scripts/azure-devops/commands/push-automation.command.ts`

**API Endpoints:**
- `GET /_apis/git/repositories/{repoName}?api-version=7.1` — Resolver repositório
- `GET /_apis/git/repositories/{repoId}/refs?filter=heads/{branch}&api-version=7.1` — Verificar branch
- `POST /_apis/git/repositories/{repoId}/pushes?api-version=7.1` — Push de arquivos

**Pré-requisitos:**
- PAT com escopo **Code (Read & Write)**
- Arquivos de automação gerados em `automated_test/{platform}/`
- Repositório existente no Azure DevOps (ou permissão para criar branch)

---

### ⚙️ 16. `@fastqa:azdo_generate_pipeline` — Gerar Pipeline YAML de CI/CD

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 16

Gera um arquivo YAML de pipeline Azure DevOps otimizado para o framework/linguagem configurado no projeto, com suporte a 15+ combinações de framework/linguagem e publicação automática de resultados de teste.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/generate-pipeline-yaml.command.ts`
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ✅ Suporta push automático do YAML para o repositório via flag `--push`

**Tecnologia:** TypeScript nativo + opcional push via Git REST API

**Workflow:**
1. Solicitar informações e **AGUARDAR** resposta do usuário:
   - **Framework** (opcional) — Auto-detectado do `project_config.json`
   - **Linguagem** (opcional) — Auto-detectado do `project_config.json`
   - **Branch de trigger** (opcional, padrão: `main`)
   - **Nome do pipeline** (opcional)
   - **Enviar para repositório?** (Sim/Não) — Se sim, informar repo e branch

2. Executar script TypeScript:
   ```bash
   npx tsx fastqa/scripts/azure-devops/commands/generate-pipeline-yaml.command.ts \
     --framework playwright \
     --language typescript \
     --trigger-branch main \
     --pipeline-name "E2E Tests - Playwright" \
     --output-path "automated_test/web/config/azure-pipelines.yml" \
     --push \
     --repo "meu-repo" \
     --push-branch "feature/ci-pipeline" \
     --push-path "azure-pipelines.yml"
   ```

3. **O script gera pipeline YAML com:**
   - **Pool:** `ubuntu-latest` (Linux) ou `windows-latest` para .NET
   - **Trigger:** Branch configurada + paths de `automated_test/`
   - **Steps específicos por framework:**
     - **Playwright (TS):** Node.js setup → `npm ci` → `npx playwright install --with-deps` → `npx playwright test` → `PublishTestResults@2` (JUnit)
     - **Playwright (Python):** Python setup → `pip install` → `pytest --junitxml` → PublishTestResults
     - **Playwright (Java):** Java setup → Maven → `mvn test` → PublishTestResults
     - **Playwright (C#):** .NET setup → `dotnet test --logger trx` → PublishTestResults (VSTest)
     - **Cypress (TS/JS):** Node.js → `npx cypress run` → PublishTestResults (JUnit)
     - **Selenium (Python/Java/C#):** Setup + driver + test execution + PublishTestResults
     - **Robot Framework:** Python → Robot → `--outputdir results --xunit xunit.xml` → PublishTestResults
     - **API (Supertest/Requests/RestAssured/Karate):** Frameworks de API com publicação de resultados
   - **PublishTestResults@2:** Formato correto por framework (JUnit, VSTest, NUnit, xUnit)
   - **Artefatos:** `PublishBuildArtifacts@1` para relatórios e evidências

4. **Se `--push`:** Envia o YAML para o repositório via Git REST API (mesma lógica do push-automation)

5. Salvar arquivo localmente e exibir resumo:
   ```markdown
   ✅ Pipeline YAML gerado com sucesso!
   
   **Framework:** Playwright + TypeScript
   **Arquivo:** automated_test/web/config/azure-pipelines.yml
   **Trigger:** main
   **Test Format:** JUnit
   **Push:** ✅ Enviado para meu-repo/feature/ci-pipeline
   ```

**Parâmetros:**
- `--framework` (opcional) — `playwright` | `cypress` | `selenium` | `robot` | `webdriverio` | `supertest` | `requests` | `restassured` | `karate`
- `--language` (opcional) — `typescript` | `javascript` | `python` | `java` | `csharp`
- `--trigger-branch` (opcional, padrão: `main`) — Branch de trigger
- `--pipeline-name` (opcional) — Nome do pipeline
- `--output-path` (opcional) — Caminho local para salvar o YAML
- `--push` (flag) — Enviar YAML para repositório
- `--repo` (obrigatório se `--push`) — Nome do repositório
- `--push-branch` (opcional) — Branch de destino para push
- `--push-path` (opcional, padrão: `azure-pipelines.yml`) — Caminho no repositório

**Frameworks suportados (15+ combinações):**
| Framework | Linguagens | Formato de Resultado |
|-----------|-----------|---------------------|
| Playwright | TS, Python, Java, C# | JUnit / VSTest / NUnit |
| Cypress | TS, JS | JUnit (Mocha) |
| Selenium | Python, Java, C# | JUnit / NUnit |
| Robot | Python | xUnit |
| WebdriverIO | TS, JS | JUnit (Mocha) |
| Supertest | TS, JS | JUnit (Mocha) |
| Requests | Python | JUnit (pytest) |
| RestAssured | Java | JUnit |
| Karate | Java | JUnit (Cucumber) |
| WebdriverIO | TS, JS | JUnit (Mocha) |

**Script:** `fastqa/scripts/azure-devops/commands/generate-pipeline-yaml.command.ts`

**Pré-requisitos:**
- Framework e linguagem configurados em `project_config.json` (ou informados via parâmetros)
- [Opcional] Repositório Azure DevOps com permissão de escrita (para `--push`)

---

### 🔄 17. `@fastqa:azdo_sync_pipeline_results` — Sincronizar Resultados de Pipeline com Test Plan

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 17

Sincroniza os resultados de execução de uma pipeline/build do Azure DevOps com o Test Plan, atualizando automaticamente os Test Runs dos Test Cases e criando bugs para falhas.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/sync-pipeline-results.command.ts`
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ✅ Script inclui mapeamento inteligente de test cases via 4 estratégias

**Tecnologia:** TypeScript nativo com Node.js fetch API

**Workflow:**
1. Solicitar informações e **AGUARDAR** resposta do usuário:
   - **Build ID** (obrigatório) — ID da build/pipeline executada
   - **Test Plan ID** (obrigatório) — ID do Test Plan no Azure DevOps
   - **Test Suite ID** (obrigatório) — ID da Test Suite
   - **Mapear por nome?** (opcional) — Usar nome do teste para mapear ao Test Case (padrão: `true`)
   - **Criar bugs para falhas?** (Sim/Não) — Criar bugs automaticamente para testes falhados
   - **Comentário** (opcional) — Comentário adicional no Test Run

2. Executar script TypeScript:
   ```bash
   npx tsx fastqa/scripts/azure-devops/commands/sync-pipeline-results.command.ts \
     --build-id 150 \
     --test-plan-id 29 \
     --test-suite-id 38 \
     --map-by-name \
     --auto-bug \
     --bug-severity "2 - High" \
     --comment "Sync automático da pipeline CI/CD"
   ```

3. **O script executa em 7 etapas:**

   **Etapa 1 — Obter Build:**
   - `GET /_apis/build/builds/{buildId}` — Obter info da build (status, result, branch)
   - Validar que build está completa (`status === 'completed'`)

   **Etapa 2 — Obter Test Runs da Build:**
   - `GET /_apis/test/runs?buildUri=vstfs:///Build/Build/{buildId}` — Listar Test Runs da build
   - Coletar resultados individuais de cada Test Run: `GET /_apis/test/runs/{runId}/results`

   **Etapa 3 — Coletar Resultados Individuais:**
   - Para cada Test Run da pipeline, obter resultados detalhados
   - Mapear: `testName`, `outcome` (Passed/Failed/etc.), `errorMessage`, `durationInMs`

   **Etapa 4 — Obter Test Points da Suite:**
   - `GET /_apis/testplan/Plans/{planId}/Suites/{suiteId}/TestPoint` — Obter todos os Test Points
   - Cada Test Point tem: `testCaseReference.id`, `testCaseReference.name`

   **Etapa 5 — Mapear Resultados → Test Cases (4 estratégias):**
   1. **Extração de ID:** Regex no nome do teste (`TC-123`, `[123]`, `#123`, `TestCase_123`, etc.)
   2. **Nome exato:** Match case-insensitive do nome do teste com `testCaseReference.name`
   3. **Nome normalizado:** Remove caracteres especiais e compara (ex: `loginComSucesso` ↔ `Login com sucesso`)
   4. **Nome parcial:** Verifica se o nome do teste contém o nome do Test Case (ou vice-versa)
   
   **Etapa 6 — Criar/Atualizar Test Runs:**
   - Cria um novo Test Run com todos os Test Point IDs mapeados
   - Atualiza cada Test Result com o outcome correspondente da pipeline
   - Mapeia outcomes da pipeline: `success`→`Passed`, `failure`/`error`→`Failed`, `skipped`/`ignored`→`NotExecuted`
   - Finaliza o Test Run com status `Completed`

   **Etapa 7 — Criar Bugs (opcional):**
   - Para cada teste `Failed`, cria Bug com:
     - Título: `[PIPELINE-BUG] {testCaseName} falhou no Build #{buildNumber}`
     - Repro Steps: HTML formatado com error message e stack trace
     - Severity: conforme `--bug-severity`
     - Tags: `pipeline-bug; fastqa; automation; ci-cd`
     - Vínculo: Relacionado ao Test Case (`related` link type)

4. **Modo dry-run** (`--dry-run`): Exibe tabela de mapeamento sem criar/atualizar nada:
   ```
   📋 DRY-RUN — Mapeamento encontrado:
   ┌─────────────────────────┬──────────────┬─────────┬───────────────────┐
   │ Pipeline Test           │ Test Case ID │ Outcome │ Strategy          │
   ├─────────────────────────┼──────────────┼─────────┼───────────────────┤
   │ TC-14 Login válido      │ 14           │ Passed  │ ID extraction     │
   │ TC-15 Login inválido    │ 15           │ Failed  │ ID extraction     │
   │ Registro de usuário     │ 16           │ Passed  │ Partial name      │
   └─────────────────────────┴──────────────┴─────────┴───────────────────┘
   ```

5. Exibir relatório final:
   ```markdown
   ✅ Sincronização concluída!
   
   **Build:** #150 (Completed/PartiallySucceeded)
   **Total Testes Pipeline:** 25
   **Mapeados:** 22 (88%)
   **Não mapeados:** 3
   
   📊 Resultados:
   - ✅ Passed: 18
   - ❌ Failed: 3
   - ⏭️ Skipped: 1
   
   🔄 Test Runs: 1 criado (Run ID: 456)
   🐛 Bugs: 3 criados (#501, #502, #503)
   
   📝 Log: fastqa/scripts/azure-devops/logs/pipeline-sync-150-{timestamp}.json
   ```

6. **Exit codes:**
   - `0` — Sucesso, todos os testes passaram
   - `1` — Erro no script (configuração, rede, API)
   - `2` — Sucesso na sincronização, mas há testes falhados

**Parâmetros:**
- `--build-id` (obrigatório) — ID da build/pipeline no Azure DevOps
- `--test-plan-id` (obrigatório) — ID do Test Plan
- `--test-suite-id` (obrigatório) — ID da Test Suite
- `--map-by-name` (flag, padrão: true) — Usar nome do teste para mapeamento
- `--comment` (opcional) — Comentário adicional no Test Run
- `--auto-bug` (flag) — Criar bugs para testes falhados
- `--bug-severity` (opcional, padrão: `3 - Medium`) — Severidade dos bugs criados
- `--update-existing` (flag) — Atualizar Test Runs existentes da mesma build
- `--dry-run` (flag) — Exibir mapeamento sem executar alterações

**Script:** `fastqa/scripts/azure-devops/commands/sync-pipeline-results.command.ts`

**API Endpoints (sequência completa):**
1. `GET /_apis/build/builds/{buildId}?api-version=7.1` — Obter dados da build
2. `GET /_apis/test/runs?buildUri=vstfs:///Build/Build/{buildId}&api-version=7.1` — Test Runs da build
3. `GET /_apis/test/runs/{runId}/results?api-version=7.1` — Resultados detalhados
4. `GET /_apis/testplan/Plans/{planId}/Suites/{suiteId}/TestPoint?api-version=7.1` — Test Points
5. `POST /_apis/test/runs?api-version=7.1` — Criar novo Test Run
6. `PATCH /_apis/test/runs/{runId}/results?api-version=7.1` — Atualizar resultados
7. `PATCH /_apis/test/runs/{runId}?api-version=7.1` — Finalizar Test Run
8. `POST /_apis/wit/workitems/$Bug?api-version=7.1` — Criar bug (se `--auto-bug`)
9. `PATCH /_apis/wit/workitems/{bugId}?api-version=7.1` — Vincular bug ao Test Case

**Pré-requisitos:**
- PAT com escopo **Test Management (Read & Write)**, **Build (Read)**, **Work Items (Read & Write)**
- Build/pipeline já executada e com status `completed`
- Test Cases associados à Test Suite (`@fastqa:azdo_add_testcase_to_suite`)
- Nomes dos testes automatizados devem conter ID ou nome do Test Case para mapeamento correto

---

### 🆕 18. `@fastqa:azdo_create_repo` — Criar Repositório no Azure DevOps

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 18

Cria um novo repositório Git no Azure DevOps com push inicial de código de automação. Suporta criação em **projetos diferentes** (cross-project), seleção automática do diretório de automação por plataforma, geração de `.gitignore` e `README.md` específicos para o framework/linguagem configurado, e modo dry-run para verificação prévia.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/create-repo.command.ts`
> - ❌ **NUNCA** utilizar PowerShell (.ps1)
> - ❌ **NUNCA** utilizar `git` CLI diretamente — usar REST API via script TypeScript
> - ✅ Script inclui suporte cross-project, geração automática de .gitignore/README e modo dry-run

**Tecnologia:** TypeScript nativo com Node.js fetch API

**Workflow:**
1. Solicitar informações e **AGUARDAR** resposta do usuário:
   - **Nome do repositório** (obrigatório) — Nome do novo repositório a ser criado
   - **Diretório de automação** (opcional) — Diretório fonte dos arquivos para push inicial:
     - Se omitido, detecta automaticamente do `project_config.json` (plataforma → `web`, `api` ou `mobile`)
     - Aceita valores: `web`, `api`, `mobile` (resolve para `automated_test/{valor}/`)
     - Ou caminho absoluto/relativo para diretório customizado
   - **Projeto Azure DevOps** (opcional) — Nome do projeto destino:
     - Se omitido, usa o projeto padrão configurado em `.env` (`AZURE_DEVOPS_PROJECT`)
     - Permite criação **cross-project**: criar repositório em projeto diferente do padrão
   - **Descrição** (opcional) — Descrição do repositório (exibida no Azure DevOps)
   - **Branch padrão** (opcional, padrão: `main`) — Nome da branch inicial
   - **Target path** (opcional) — Caminho de destino no repositório para os arquivos
   - **Incluir shared?** (opcional) — Incluir pasta `automated_test/shared/` além da plataforma
   - **Gerar .gitignore?** (opcional, padrão: `true`) — Gerar `.gitignore` específico para o framework
   - **Dry-run?** (opcional) — Listar arquivos que seriam enviados sem criar o repositório

2. Executar script TypeScript:
   ```bash
   npx tsx fastqa/scripts/azure-devops/commands/create-repo.command.ts \
     --repo "meu-novo-repo" \
     --automation-dir web \
     --project "outro-projeto" \
     --description "Testes automatizados E2E com Playwright" \
     --branch main \
     --target-path "tests/e2e" \
     --include-shared \
     --generate-gitignore \
     --dry-run
   ```

3. **O script executa em sequência:**

   **Etapa 1 — Resolução do diretório fonte:**
   - Se `--automation-dir` é `web`, `api` ou `mobile`: resolve para `automated_test/{valor}/`
   - Se é caminho absoluto/relativo: usa diretamente
   - Se omitido: lê `project_config.json` e detecta plataforma automaticamente
   - Valida que o diretório existe e contém arquivos

   **Etapa 2 — Coleta de arquivos:**
   - Recursivamente coleta todos os arquivos do diretório fonte
   - Aplica filtros de ignore (node_modules, .git, __pycache__, .env, etc.)
   - Se `--include-shared`: inclui também `automated_test/shared/`
   - Classifica arquivos como texto ou binário (25+ extensões binárias suportadas)
   - Valida tamanho total < 100 MB

   **Etapa 3 — Geração de arquivos virtuais:**
   - Se `--generate-gitignore` (padrão: true):
     - Gera `.gitignore` específico para o framework/linguagem detectado do `project_config.json`
     - Suporta: Playwright, Cypress, Selenium, Robot, WebdriverIO (TypeScript, Python, Java, C#, JavaScript)
   - Sempre gera `README.md` automático com:
     - Nome do repositório, framework, linguagem
     - Tabela de informações do stack
     - Comandos de instalação e execução específicos do framework
     - Estrutura de pastas

   **Etapa 4 — Modo dry-run** (se `--dry-run`):
   - Exibe lista completa de arquivos que seriam enviados
   - Mostra tamanho total e quantidade de arquivos
   - **NÃO** cria repositório nem faz push
   - Encerra execução

   **Etapa 5 — Resolução do projeto:**
   - Se `--project` informado: verifica se projeto existe via `GET /_apis/projects/{projectName}`
   - Se omitido: usa projeto padrão configurado em `.env`
   - Suporta criação **cross-project**: repositório em projeto diferente do padrão

   **Etapa 6 — Criação do repositório:**
   - `POST /_apis/git/repositories?api-version=7.1` — Cria repositório vazio
   - Payload: `{ "name": "{repoName}", "project": { "id": "{projectId}" } }`
   - Captura `repositoryId` e `remoteUrl` do response

   **Etapa 7 — Push inicial:**
   - Monta payload de push com todos os arquivos coletados + virtuais
   - Arquivos texto: encoding Base64 UTF-8
   - Arquivos binários: encoding Base64 raw
   - `oldObjectId`: `0000000000000000000000000000000000000000` (40 zeros — push inicial em repo vazio)
   - Se cross-project: usa `POST /{project}/_apis/git/repositories/{repoId}/pushes`
   - Se mesmo projeto: usa endpoint padrão do client

   **Etapa 8 — Relatório e log:**
   - Exibe resumo com: nome do repo, projeto, branch, quantidade de arquivos, tamanho total, commit ID
   - Salva log JSON detalhado em `fastqa/scripts/azure-devops/logs/`

4. Exibir resultado:
   ```markdown
   ✅ Repositório criado com sucesso!
   
   **Repositório:** meu-novo-repo
   **Projeto:** outro-projeto
   **Branch:** main
   **Commit:** abc1234def5678
   **Arquivos:** 15 enviados (42.5 KB)
   **Plataforma:** web (Playwright + TypeScript)
   **Gerados:** .gitignore, README.md
   
   🔗 [Ver no Azure DevOps]({URL do repositório})
   ```

5. Perguntar se deseja executar ação adicional:
   - Gerar pipeline CI/CD para o novo repositório (`@fastqa:azdo_generate_pipeline`)
   - Enviar mais código com `@fastqa:azdo_push_automation`
   - Listar repositórios do projeto

**Parâmetros:**
- `--repo` (obrigatório) — Nome do novo repositório
- `--automation-dir` (opcional) — `web` | `api` | `mobile` ou caminho do diretório fonte (auto-detectado do `project_config.json`)
- `--project` (opcional) — Nome do projeto Azure DevOps destino (cross-project); padrão: projeto do `.env`
- `--description` (opcional) — Descrição do repositório
- `--branch` (opcional, padrão: `main`) — Nome da branch inicial
- `--target-path` (opcional) — Caminho de destino no repositório para os arquivos
- `--include-shared` (flag) — Incluir pasta `automated_test/shared/`
- `--generate-gitignore` (flag, padrão: `true`) — Gerar `.gitignore` específico do framework
- `--dry-run` (flag) — Listar arquivos sem criar repositório

**Script:** `fastqa/scripts/azure-devops/commands/create-repo.command.ts`

**API Endpoints:**
1. `GET /_apis/projects/{projectName}?api-version=7.1` — Verificar/obter projeto (Core API — suporte cross-project)
2. `POST /{project}/_apis/git/repositories?api-version=7.1` — Criar repositório Git
3. `POST /{project}/_apis/git/repositories/{repoId}/pushes?api-version=7.1` — Push inicial (cross-project)
4. `POST /_apis/git/repositories/{repoId}/pushes?api-version=7.1` — Push inicial (mesmo projeto)

**Geração automática de .gitignore:**

Suporta os seguintes frameworks/linguagens:
| Framework | Linguagens | Entradas Específicas |
|-----------|-----------|---------------------|
| Playwright | TS, Python, Java, C# | `test-results/`, `playwright-report/`, `blob-report/` |
| Cypress | TS, JS | `cypress/videos/`, `cypress/screenshots/`, `cypress/downloads/` |
| Selenium | Python, Java, C# | `geckodriver.log`, `chromedriver.log`, `target/` |
| Robot | Python | `output.xml`, `log.html`, `report.html`, `.robot/` |
| WebdriverIO | TS, JS | `allure-results/`, `wdio-logs/`, `*.apk`, `*.ipa` |

**Geração automática de README.md:**
- Título com nome do repositório
- Tabela com stack completo (framework, linguagem, plataforma)
- Comandos de instalação e execução específicos por framework
- Estrutura de pastas explicada

**Tratamento de erros:**
| Erro | Causa | Solução |
|------|-------|---------|
| `409 Conflict` | Repositório com mesmo nome já existe | Usar nome diferente ou `@fastqa:azdo_push_automation` para repo existente |
| `404 Not Found` (projeto) | Projeto cross-project não encontrado | Verificar nome do projeto no Azure DevOps |
| `Diretório fonte não encontrado` | Caminho do `--automation-dir` inválido | Verificar se diretório existe e contém arquivos |
| `Payload excede 100 MB` | Muitos arquivos ou arquivos muito grandes | Reduzir escopo ou usar `--dry-run` para verificar |

**Cross-project — Como funciona:**
- Por padrão, o repositório é criado no projeto configurado em `AZURE_DEVOPS_PROJECT` (`.env`)
- Com `--project "outro-projeto"`, o script:
  1. Verifica se o projeto existe via Core API (`/_apis/projects/{nome}`)
  2. Cria o repositório no projeto especificado (enviando `project.id` no payload)
  3. Faz o push inicial usando URL com escopo do projeto: `/{project}/_apis/git/repositories/{repoId}/pushes`
- O PAT precisa ter permissão **Code (Read & Write)** no projeto destino

**Pré-requisitos:**
- PAT com escopo **Code (Read & Write)** — no projeto destino se cross-project
- Arquivos de automação gerados em `automated_test/{platform}/`
- Node.js v22+ e dependências instaladas (`npm install`)
- Variáveis de ambiente configuradas no `.env`

---

### 📋 19. `@fastqa:azdo_create_test_plan` — Criar Test Plan

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 19

Cria um novo Test Plan no Azure DevOps com suites opcionais.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/create-test-plan.command.ts`

**Workflow:**
1. Solicitar informações e **AGUARDAR** resposta:
   - **Nome do Test Plan** (obrigatório)
   - **Area Path** (opcional)
   - **Iteration** (opcional)
   - **Data início e fim** (opcional)
   - **Nomes das Suites** (opcional — separados por vírgula)
2. Executar: `npx tsx fastqa/scripts/azure-devops/commands/create-test-plan.command.ts`
3. Script cria Test Plan via `POST /_apis/testplan/plans`
4. Se suites informadas, cria cada uma via `POST /_apis/testplan/Plans/{planId}/suites`
5. Exibir: Plan ID, Root Suite ID, Suites criadas com IDs

**Parâmetros:**
- `--name` (obrigatório) — Nome do test plan
- `--area-path` (opcional) — Area Path do projeto
- `--iteration` (opcional) — Iteration/Sprint
- `--start-date` (opcional) — Data de início (YYYY-MM-DD)
- `--end-date` (opcional) — Data de fim (YYYY-MM-DD)
- `--description` (opcional) — Descrição do plano
- `--suites` (opcional) — Nomes das suites separados por vírgula
- `--dry-run` (flag)

---

### 📝 20. `@fastqa:azdo_update_test_plan` — Atualizar Test Plan

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 20

Atualiza propriedades de um Test Plan existente (nome, datas, iteration, area path, estado).

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/update-test-plan.command.ts`

**Workflow:**
1. Solicitar: **Plan ID** (obrigatório) + campos a atualizar (pelo menos um)
2. Script obtém estado atual do plano e exibe diff antes/depois
3. Aplica atualização via `PATCH /_apis/testplan/plans/{planId}`

**Parâmetros:**
- `--plan-id` (obrigatório)
- `--name`, `--area-path`, `--iteration`, `--start-date`, `--end-date`, `--state`, `--description` (pelo menos um)

---

### 🚀 21. `@fastqa:azdo_create_pipeline` — Criar Pipeline no Azure DevOps

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 21

Cria uma definição de pipeline (build definition) no Azure DevOps apontando para um arquivo YAML.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/create-pipeline.command.ts`

**Workflow:**
1. Solicitar informações:
   - **Nome da Pipeline** (obrigatório)
   - **Nome do Repositório** (obrigatório)
   - **Caminho do YAML** (opcional, padrão: `azure-pipelines.yml`)
   - **Branch padrão** (opcional, padrão: `main`)
2. Script resolve repositório via `GET /_apis/git/repositories/{name}`
3. Cria build definition via `POST /_apis/build/definitions`
4. Exibir: Pipeline ID, nome, URL

**Parâmetros:**
- `--name` (obrigatório)
- `--repo` (obrigatório)
- `--yaml-path` (opcional, padrão: `azure-pipelines.yml`)
- `--branch` (opcional, padrão: `main`)
- `--folder` (opcional, padrão: `\`)
- `--dry-run` (flag)

**Pré-requisitos:** PAT com **Build (Read & Write)**, repositório já existente com YAML

---

### ▶️ 22. `@fastqa:azdo_run_pipeline` — Executar Pipeline

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 22

Dispara execução de uma pipeline e opcionalmente aguarda conclusão com polling automático.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/run-pipeline.command.ts`

**Workflow:**
1. Solicitar: **Pipeline ID** (obrigatório), Branch (opcional), Variáveis (opcional)
2. Script dispara via `POST /_apis/pipelines/{id}/runs`
3. Se `--wait`: polling a cada 15s até `status === 'completed'` (timeout: 10min)
4. Exibir: Run ID, Build ID, resultado, duração, URL

**Parâmetros:**
- `--pipeline-id` (obrigatório)
- `--branch` (opcional)
- `--variables` (opcional — `"KEY1=VALUE1,KEY2=VALUE2"`)
- `--wait` (flag)
- `--timeout` (opcional, padrão: 600000ms)
- `--poll-interval` (opcional, padrão: 15000ms)

**Pré-requisitos:** PAT com **Build (Read & Write)**, pipeline definition criada

---

### 🔑 23. `@fastqa:azdo_set_pipeline_variable` — Criar/Atualizar Variáveis de Pipeline

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 23

Cria ou atualiza um Variable Group e opcionalmente autoriza uma pipeline a utilizá-lo.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/set-pipeline-variable.command.ts`

**Workflow:**
1. Solicitar: **Nome do Variable Group**, **Variáveis** (KEY=VALUE), Secret vars (opcional), Pipeline ID (opcional)
2. Script verifica se grupo existe via `GET /_apis/distributedtask/variablegroups`
3. Cria ou atualiza conforme existência + flag `--update`
4. Se `--pipeline-id`: autoriza pipeline via `PATCH /_apis/pipelines/pipelinepermissions/variablegroup/{id}`

**Parâmetros:**
- `--group-name` (obrigatório)
- `--variables` (obrigatório — `"KEY1=VALUE1,KEY2=VALUE2"`)
- `--secret-vars` (opcional — `"KEY1,KEY2"`)
- `--pipeline-id` (opcional)
- `--description` (opcional)
- `--update` (flag)

**Pré-requisitos:** PAT com **Variable Groups (Read, create, & manage)**

---

### 🔍 24. `@fastqa:azdo_verify_pipeline_results` — Verificar Resultados + Auto-Healing

> **🤖 Agent:** `fastqa/agents/core/fastqa_5.1_azure_devops.md` — Comando 24

Verifica resultados de uma pipeline executada, extrai diagnóstico de falhas dos logs, e gera relatório estruturado para `@fastqa:verify_and_fix`.

> **⚠️ REGRA OBRIGATÓRIA:** Este comando **SEMPRE** utiliza **script TypeScript**:
> - ✅ **SEMPRE** executar: `npx tsx fastqa/scripts/azure-devops/commands/verify-pipeline-results.command.ts`

**Workflow:**
1. Solicitar: **Build ID**, **Test Plan ID**, **Test Suite ID**
2. Obter build + test runs + resultados detalhados
3. Para cada teste falhado: extrair error message + stack trace + logs da build
4. Gerar relatório de diagnóstico em `fastqa/manual_test/evidence/reports/`
5. Redirecionar QA para `@fastqa:verify_and_fix` com arquivos de teste falhados

**Parâmetros:**
- `--build-id` (obrigatório)
- `--test-plan-id` (obrigatório)
- `--test-suite-id` (obrigatório)
- `--auto-bug` (flag)
- `--wait` (flag) — Aguardar build se em andamento
- `--timeout` (opcional, padrão: 600000ms)

**Pré-requisitos:** PAT com **Build (Read)**, **Test Management (Read & Write)**, **Work Items (Read & Write)**

---

## 🔑 Client API Principal

O client centraliza as chamadas REST ao Azure DevOps via Node.js `fetch()` nativo para **uploads de evidências, batch processing, Git push, sincronização de pipeline, CRUD de Test Plans, Pipeline definitions, Variable Groups e execução/monitoramento de pipelines**.

> **📌 IMPORTANTE:** Operações CRUD de work items e test management usam **MCP Azure DevOps** quando ativo, com **fallback TypeScript** automático. Os comandos 19-24 (CI/CD completo) são **100% TypeScript**.

**Arquivo:** `fastqa/scripts/azure-devops/azure-devops.client.ts`

**Funcionalidades:**
- Autenticação via PAT (HTTP Basic Auth com Base64)
- Retry automático com backoff exponencial (3 tentativas)
- Logging estruturado em arquivo e console
- Tratamento de erros HTTP com mensagens descritivas
- Encoding UTF-8 para payloads JSON
- Upload de arquivos binários em Base64
- Timeout configurável por requisição (padrão: 30s)

**Métodos principais do client (apenas para uploads e batch):**

| Categoria | Método | Descrição | Status |
|-----------|--------|-----------|--------|
| **Work Items** | `getWorkItem(id)` | Obter work item por ID | ⚠️ **USAR MCP** `mcp_microsoft_azu_wit_get_work_item` |
| | `createWorkItem(type, fields)` | Criar work item | ⚠️ **USAR MCP** `mcp_microsoft_azu_wit_create_work_item` |
| | `updateWorkItem(id, operations)` | Atualizar campos | ⚠️ **USAR MCP** `mcp_microsoft_azu_wit_update_work_item` |
| | ~~`linkWorkItems(sourceId, targetId, linkType)`~~ | ⚠️ **DEPRECADO** — Usar MCP `mcp_azuredevops_manage_work_item_link` |
| **Attachments** | `uploadAttachment(filePath, fileName)` | Upload de arquivo | ✅ **USADO** para evidências |
| | `attachToWorkItem(workItemId, attachmentUrl)` | Vincular attachment | ✅ **USADO** para evidências |
| **Test Plans** | `getTestPlans()` | Listar test plans | ⚠️ **USAR MCP** `mcp_microsoft_azu_testplan_list` |
| | `getTestSuites(planId)` | Listar test suites | ⚠️ **USAR MCP** `mcp_microsoft_azu_testplan_get_suites` |
| | `getTestCases(planId, suiteId)` | Listar test cases | ⚠️ **USAR MCP** `mcp_microsoft_azu_testplan_get_test_cases` |
| | `addTestCaseToSuite(planId, suiteId, caseIds)` | Adicionar TC à suite | ⚠️ **USAR MCP** `mcp_microsoft_azu_testplan_add_test_case_to_suite` |
| **Test Runs** | `getTestPoints(planId, suiteId, caseId)` | Obter test points | ✅ **USADO** para batch execution |
| | `createTestRun(planId, pointIds, name)` | Criar test run | ✅ **USADO** para batch execution |
| | `getTestResults(runId)` | Obter results do run | ✅ **USADO** para batch execution |
| | `uploadResultAttachment(runId, resultId, filePath)` | Upload para result | ✅ **USADO** para evidências |
| | `updateTestResult(runId, resultId, outcome, comment)` | Atualizar outcome | ✅ **USADO** para batch execution |
| | `completeTestRun(runId)` | Finalizar run | ✅ **USADO** para batch execution |
| **Git** | `pushChanges(repoId, payload)` | Push de arquivos via REST | ✅ **USADO** para push-automation |
| | `createRepository(repoName, projectId, projectName?)` | Criar repositório Git | ✅ **USADO** para create-repo |
| | `createGitPushInProject(projectName, repoId, push)` | Push cross-project | ✅ **USADO** para create-repo (cross-project) |
| **Core** | `getProject(projectName)` | Obter informações do projeto | ✅ **USADO** para create-repo (cross-project) |
| **Build** | `getBuild(buildId)` | Obter dados da build | ✅ **USADO** para sync-pipeline |
| | `getBuilds(params?)` | Listar builds com filtros | ✅ **USADO** para sync-pipeline |
| | `getTestRunsByBuild(buildUri)` | Test Runs da build | ✅ **USADO** para sync-pipeline |

**Padrão de uso atual (MCP + TypeScript):**
```typescript
// ❌ NÃO USAR MAIS - Usar MCP Azure DevOps
// const workItem = await client.getWorkItem(123);

// ✅ USAR - MCP Azure DevOps para CRUD
mcp_microsoft_azu_wit_get_work_item({ project: "projeto", id: 123 });

// ❌ NÃO USAR MAIS - Usar MCP Azure DevOps  
// const bug = await client.createWorkItem('Bug', [...]);

// ✅ USAR - MCP Azure DevOps para criação
mcp_microsoft_azu_wit_create_work_item({
  project: "projeto",
  work_item_type: "Bug", 
  title: "Erro no login",
  description: "Descrição HTML..."
});

// ✅ AINDA USAR - Client TypeScript para uploads
import { AzureDevOpsClient } from '../azure-devops.client';
const client = new AzureDevOpsClient();
await client.uploadResultAttachment(runId, resultId, 'manual_test/evidence/TS-001/video.webm');

// ✅ USAR - Client TypeScript para Git push
await client.pushChanges(repoId, pushPayload);

// ✅ USAR - Client TypeScript para criar repositório
const project = await client.getProject('outro-projeto');
const repo = await client.createRepository('meu-repo', project.id, project.name);
await client.createGitPushInProject('outro-projeto', repo.id, pushPayload); // cross-project

// ✅ USAR - Client TypeScript para sync pipeline
const build = await client.getBuild(buildId);
const testRuns = await client.getTestRunsByBuild(`vstfs:///Build/Build/${buildId}`);
```

---

## 🔄 Fluxos de Trabalho

### Fluxo Principal: Execução Manual → Upload → Relatório (Com Integração Automática)

```
@fastqa:run_manual_test
        ↓
   [Evidências capturadas em fastqa/manual_test/evidence/]
        ↓
   [✨ NOVO: PROMPT - Deseja enviar resultado para Azure DevOps?]
        ├── Opção 1: Sim
        │   ↓
        │   @fastqa:azdo_upload_test_execution (executado automaticamente)
        │   ↓
        │   [Test Run criado + Evidências uploadadas + Status atualizado]
        │
        ├── Opção 2: Não
        │   ↓
        │   [Evidências salvas localmente]
        │
        └── Opção 3: Ver parâmetros
            ↓
            [Exibe comando manual para executar depois]
        ↓
@fastqa:azdo_generate_report
        ↓
   [Relatório consolidado gerado em manual_test/evidence/reports/]
```

### Fluxo: Bug Encontrado Durante Teste (Com Integração Automática)

```
@fastqa:run_manual_test (cenário falha)
        ↓
   [Evidências capturadas]
        ↓
   [✨ PROMPT: Deseja enviar resultado para Azure DevOps?]
        ↓
   [Usuário escolhe: Sim]
        ↓
   [Coleta parâmetros: Test Plan ID, Suite ID, Case ID, Result=Failed]
        ↓
@fastqa:azdo_upload_test_execution --result Failed --auto-bug (executado automaticamente)
        ↓
   [Test Run + Evidência + Bug criado automaticamente]
        ↓
@fastqa:azdo_link_work_items (Bug vinculado à User Story automaticamente)
```

### Fluxo: Preparação de Test Plan

```
@fastqa:test_case_with_fastqa (gerar .feature)
        ↓
@fastqa:azdo_create_test_case (converter .feature → Test Cases)
        ↓
@fastqa:azdo_add_testcase_to_suite
        ↓
@fastqa:azdo_list_test_plans (verificar hierarquia)
```

### Fluxo: Automação → Pipeline → Sincronização de Resultados

```
@fastqa:automate_test (gerar scripts automatizados)
        ↓
   [Scripts gerados em automated_test/{platform}/]
        ↓
   [Opcional: Criar novo repositório]
@fastqa:azdo_create_repo --repo "meu-repo" --automation-dir web --project "meu-projeto"
        ↓
   [Repositório criado + Push inicial com código de automação]
        ↓
   [Ou: Push para repositório existente]
@fastqa:azdo_push_automation --repo "meu-repo" --branch "feature/tests"
        ↓
   [Código pushado para repositório Azure DevOps]
        ↓
@fastqa:azdo_generate_pipeline --push --repo "meu-repo"
        ↓
   [Pipeline YAML gerado e pushado para o repositório]
        ↓
   [Execução manual ou automática da pipeline no Azure DevOps]
        ↓
   [Build completada com resultados de teste]
        ↓
@fastqa:azdo_sync_pipeline_results --build-id 150 --test-plan-id 29 --test-suite-id 38
        ↓
   [Test Runs atualizados + Bugs criados automaticamente (se --auto-bug)]
        ↓
@fastqa:azdo_generate_report
        ↓
   [Relatório consolidado com resultados da pipeline]
```

### Fluxo: Dry-Run de Push + Sync (Verificação sem alterações)

```
@fastqa:azdo_create_repo --repo "novo-repo" --automation-dir web --dry-run
        ↓
   [Lista de arquivos que seriam enviados — sem criar repositório]
        ↓
@fastqa:azdo_push_automation --repo "meu-repo" --dry-run
        ↓
   [Lista de arquivos que seriam enviados — sem executar push]
        ↓
@fastqa:azdo_sync_pipeline_results --build-id 150 --dry-run
        ↓
   [Tabela de mapeamento Test Cases → Resultados — sem criar Test Runs]
```

---

## 🔄 Integração com Outros Comandos FastQA

### Sequência Completa de QA

```
# Fase 0: Setup
@fastqa:azdo_list_test_plans               # Ver plans/suites disponíveis

# Fase 1: Análise de Requisitos
@fastqa:load_pbi                            # Carregar PBI do Azure DevOps
@fastqa:identify_gaps                       # Identificar gaps nos requisitos
@fastqa:analyze_requirements                # Estruturar requisitos

# Fase 2: Geração de Testes
@fastqa:test_case_with_fastqa               # Gerar cenários Gherkin (.feature)
@fastqa:validate_scenarios                  # Validar cenários

# Fase 2.5: Criar Test Cases no Azure DevOps
@fastqa:azdo_create_test_case               # .feature → Test Cases no AzDO
@fastqa:azdo_add_testcase_to_suite          # Adicionar TCs à Suite

# Fase 3: Execução
@fastqa:run_manual_test                     # Executar via Playwright MCP
                                            # ✨ NOVO: Prompt automático para upload ao Azure DevOps

# Fase 4: Integração Azure DevOps
@fastqa:azdo_upload_test_execution          # Upload + Status + Bug (se falhar)
                                            # Pode ser executado automaticamente se usuário escolher "Sim" no prompt
@fastqa:azdo_generate_report                # Relatório consolidado

# Fase 5: CI/CD & Repositório
@fastqa:azdo_create_repo                    # Criar novo repositório + push inicial
@fastqa:azdo_push_automation                # Push código de automação para repo existente
@fastqa:azdo_generate_pipeline              # Gerar pipeline YAML de CI/CD
@fastqa:azdo_sync_pipeline_results          # Sincronizar resultados da pipeline com Test Plan

# Ações pontuais
@fastqa:azdo_get_work_item_by_id_or_title   # Consultar work item específico
@fastqa:azdo_list_work_items_by_sprint      # Listar work items de uma sprint
@fastqa:azdo_create_bug                     # Reportar bug manualmente
@fastqa:azdo_update_work_item               # Atualizar campos
@fastqa:azdo_link_work_items                # Vincular itens
```

---

## ⚠️ Troubleshooting

### Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `401 Unauthorized` | PAT inválido ou expirado | Renovar token no `.env` |
| `403 Forbidden` | PAT sem permissão | Adicionar scope `Test Management (R&W)` ao PAT |
| `404 Not Found` | Work Item / Suite / Plan inexistente | Verificar IDs com `@fastqa:azdo_list_test_plans` |
| `413 Payload Too Large` | Arquivo > 130 MB | Comprimir vídeo antes do upload |
| `500 Internal Server Error` | Payload JSON mal formado | Verificar encoding UTF-8 e formato JSON |
| `ENOENT` | Arquivo não encontrado | Verificar caminho da evidência |
| `Test Point not found` | TC não está na Suite | Executar `@fastqa:azdo_add_testcase_to_suite` primeiro |
| `ETIMEDOUT` | Timeout de rede | Verificar conectividade; script tem retry automático |
| `Error retrieving work items for iteration` | Comando MCP incorreto ou API indisponível | Usar workflow correto: `list_iterations` → `list_backlog_work_items` → `get_work_items_batch_by_ids` e filtrar por `System.IterationPath` |
| `Your input to the tool was invalid (must be array)` | Parâmetro de busca incorreto | Verificar formato dos parâmetros MCP conforme documentação (alguns exigem arrays JSON) |
| MCP Azure DevOps não responde | Servidor MCP não está ativo | Verificar painel MCP no VS Code e reiniciar o servidor se necessário |
| `409 Conflict` (Git push) | Branch desatualizada ou conflito de merge | Fazer pull/rebase antes de push; verificar se branch existe com `--create-branch` |
| `422 Unprocessable Entity` (Git push) | Payload de push inválido ou arquivo muito grande | Verificar Base64 encoding; arquivos individuais < 100 MB |
| `Pipeline YAML validation error` | Sintaxe YAML inválida no pipeline gerado | Verificar indentação; usar `--dry-run` antes do `--push` |
| `Build not found (404)` | Build ID inexistente ou pipeline não executada | Verificar Build ID no portal Azure DevOps; aguardar conclusão da build |
| `0% test case mapping` | Nomes dos testes não correspondem aos Test Cases | Incluir ID do TC no nome do teste (ex: `TC-14_login_valido`); usar `--dry-run` para verificar mapeamento |
| `409 Conflict` (create-repo) | Repositório com mesmo nome já existe | Usar nome diferente ou `@fastqa:azdo_push_automation` para repo existente |
| `404 Not Found` (cross-project) | Projeto destino não encontrado | Verificar nome do projeto no Azure DevOps; PAT precisa acesso ao projeto |
| `Diretório fonte não encontrado` | Caminho do `--automation-dir` inválido | Verificar se diretório existe e contém arquivos; usar `--dry-run` para verificar |
| `Payload excede 100 MB` | Muitos arquivos ou arquivos muito grandes no push inicial | Reduzir escopo com `--target-path`; usar `--dry-run` para verificar tamanho |

### Verificação de Conectividade

```bash
# Testar conexão com Azure DevOps API
curl -u ":{SEU_PAT}" "https://dev.azure.com/{org}/{project}/_apis/wit/workitems/1?api-version=7.1"
```

### Logs

Logs são salvos automaticamente em: `fastqa/scripts/azure-devops/logs/`
- Formato: `{command}-{timestamp}.log`
- Conteúdo: Request URL, Status Code, Response Body, Duração, Erros

---

## 📊 Limites do Azure DevOps

| Recurso | Limite |
|---------|--------|
| Tamanho máximo de attachment | 130 MB |
| Attachments por Work Item | Ilimitado |
| Requests por minuto (API) | 200 (standard) |
| Tamanho máximo de campo HTML | 1 MB |
| Work Items por query | 20.000 |
| Arquivos por Git push | 1.000 (recomendado < 100) |
| Tamanho máximo por Git push | 500 MB total |
| Pipelines por projeto | Ilimitado |

---

## 🚀 Boas Práticas

### Tecnologia Obrigatória
- ✅ **SEMPRE usar TypeScript** para uploads de evidências e operações de batch
- ✅ **SEMPRE usar MCP Azure DevOps** para operações CRUD de work items e test management
- ✅ Executar scripts com: `npx tsx fastqa/scripts/azure-devops/commands/<script>.command.ts`
- ❌ **NUNCA usar PowerShell** (.ps1) para integração Azure DevOps
- ❌ Não usar comandos REST diretos via terminal (exceto `npx tsx`)
- ✅ Scripts TypeScript incluem normalização automática de paths Windows (converte \\ para /)

### Organização
- ✅ Usar `.env` para credenciais — **NUNCA** hardcodar PAT em código
- ✅ Comprimir vídeos antes do upload (H.264/WebM, máx 50 MB ideal)
- ✅ Nomear evidências com padrão: `{TS-ID}_{tipo}_{timestamp}.{ext}`
- ✅ Sempre vincular bugs ao Test Case e à User Story
- ✅ Gerar relatório após cada ciclo de execução
- ✅ Usar tags para organizar work items (`sprint-15`, `regression`, `api`, `smoke`)
- ✅ Manter logs para auditoria e rastreabilidade

### Segurança
- ❌ **NUNCA** commitar `.env` no Git
- ❌ Não commitar evidências binárias no Git (usar `.gitignore`)
- ❌ **Não usar scripts PowerShell (.ps1)** — usar MCP Azure DevOps + TypeScript para uploads
- ❌ Não expor PAT em logs ou outputs de terminal

### Convenções de Nomenclatura
| Item | Padrão | Exemplo |
|------|--------|---------|
| Evidência (vídeo) | `{TS-ID}_video_{timestamp}.webm` | `TS-001_video_20260219-1430.webm` |
| Evidência (screenshot) | `{TS-ID}_screenshot_{step}.png` | `TS-001_screenshot_03.png` |
| Bug (título) | `[BUG] {Módulo} - {Descrição}` | `[BUG] Login - Erro 500 ao submeter` |
| Test Case (título) | `{Módulo} - {Cenário}` | `Login - Autenticação com credenciais válidas` |
| Relatório | `report-{planId}-{timestamp}.md` | `report-110-20260219-1430.md` |

---

## 🔗 Links Úteis

- [Azure DevOps REST API — Work Items](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items)
- [Azure DevOps REST API — Test Plans](https://learn.microsoft.com/en-us/rest/api/azure/devops/testplan)
- [Azure DevOps REST API — Test Runs](https://learn.microsoft.com/en-us/rest/api/azure/devops/test/runs)
- [Azure DevOps REST API — Attachments](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/attachments)
- [Playwright API Testing](https://playwright.dev/docs/api-testing)
- [Criar PAT no Azure DevOps](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate)
- [Azure DevOps REST API — Git Pushes](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pushes)
- [Azure DevOps REST API — Pipelines](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines)
- [Azure DevOps REST API — Build](https://learn.microsoft.com/en-us/rest/api/azure/devops/build)
- [Azure Pipelines YAML Schema](https://learn.microsoft.com/en-us/azure/devops/pipelines/yaml-schema)
- [Azure DevOps REST API — Git Repositories](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/repositories)
- [Azure DevOps REST API — Projects (Core)](https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects)

---

**Última Atualização:** 19 de Fevereiro de 2026
**Versão:** 4.1
