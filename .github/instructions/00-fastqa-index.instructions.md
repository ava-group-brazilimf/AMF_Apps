---
description: FastQA — Roteamento de comandos. Ao receber @fastqa ou @fastqa_code, use read_file para carregar o arquivo de detalhes correto ANTES de executar.
# applyTo escopado ao diretório do FastQA — NÃO voltar para '**'.
# Medido em 2026-08-04: com '**' este arquivo entra no prompt de sistema de TODA
# sessão e custa 6.815 tokens (systemTokens 23.595 -> 16.780 ao escopar), 5,3% da
# janela de 128K, inclusive em runs de F1 que nunca tocam QA.
# O roteamento @fastqa continua funcionando: .github/copilot-instructions.md
# carrega sempre e aponta para este índice.
applyTo: 'fastqa/**'
# `memory` e `sequential-thinking` são tools do ecossistema BMAD/MCP e NÃO existem
# no toolset do Copilot CLI (view/create/edit/glob/grep/powershell/task/web_*).
# Mantidas apenas para o uso original em VS Code com MCP configurado; no CLI são
# ignoradas — não declarar tools inexistentes em spec de agente (AGENTS.md § D5).
tools: ['memory', 'sequential-thinking']
---

# FastQA — Índice de Roteamento (Slim)

> **📌 REGRA CRÍTICA:** Este arquivo é apenas um **roteador**. Ao receber qualquer comando `@fastqa:*` ou `@fastqa_code:*`:
> 1. Localize o comando na tabela abaixo
> 2. Execute `read_file` no **Arquivo de Detalhes** correspondente
> 3. Siga o workflow completo descrito no arquivo carregado
>
> **NÃO** tente executar comandos sem antes carregar o arquivo de detalhes.

## ⚙️ Variáveis do Projeto

| Variável | Valor |
|----------|-------|
| `QA_AGENT_NAME` | **TEA** |
| `QA_AGENT_PATH` | `code_qa/_bmad/bmm/agents/tea.md` |
| `QA_WORKFLOWS_PATH` | `code_qa/_bmad/bmm/workflows/testarch/` |

## 🔀 Prefixos

| Prefixo | Comportamento |
|---------|---------------|
| `@fastqa:` | Executa diretamente |
| `@fastqa_code:` | Ativa TEA (`QA_AGENT_NAME`) **antes** de executar |

## 📋 Tabela de Roteamento

> **Caminho base:** `.github/instructions/`

### Jornadas de Trabalho → `00-fastqa-journey.md`

| Comando | Descrição |
|---------|----------|
| `@fastqa:journey` | Selecionar/retomar jornada de trabalho guiada |

### Fase 0: Setup & Help

| Comando | Descrição | Arquivo de Detalhes |
|---------|-----------|-------------------|
| `@fastqa:setup_project` | Wizard de configuração | **Este arquivo** (seção abaixo) |
| `@fastqa:help` | Menu de comandos | **Este arquivo** (seção abaixo) |
| `@fastqa_code:help` | Menu + TEA | **Este arquivo** (seção abaixo) |
| `@fastqa_code:help_code_avanade` | Menu BMAD + TEA | **Este arquivo** (seção abaixo) |

### Fase 0-1: Requisitos → `01-fastqa-requirements.md`

| Comando | Descrição |
|---------|-----------|
| `@fastqa:load_pbi` | Carregar PBI do Azure DevOps |
| `@fastqa:identify_gaps` | Identificar gaps em requisitos |
| `@fastqa:estimate_effort` | Estimativa de esforço |
| `@fastqa:analyze_requirements` | Análise de requisitos |
| `@fastqa:map_behaviors` | Mapeamento de comportamentos |

### Fase 2: Cenários → `02-fastqa-test-design.md`

| Comando | Descrição |
|---------|-----------|
| `@fastqa:ac_scope_analysis` | Análise de escopo de ACs para testes |
| `@fastqa:test_case_with_fastqa` | Gerar casos de teste (Gherkin ou Step by Step) |
| `@fastqa:test_case_with_playwright_mcp` | Gerar cenários com Playwright MCP |
| `@fastqa:validate_scenarios` | Validar cenários |
| `@fastqa:api_generate_scenarios` | Cenários Gherkin para API |
| `@fastqa:exploratory_api_test` | Testes exploratórios API |
| `@fastqa:destructive_api_test` | Testes destrutivos API |

### Fase 3: Execução → `03-fastqa-execution.md`

| Comando | Descrição |
|---------|-----------|
| `@fastqa:run_manual_test` | Execução manual via Playwright MCP |
| `@fastqa:run_parallel_tests` | Execução paralela |
| `@fastqa:run_manual_api_test_swagger` | Execução API via Swagger + MCP |
| `@fastqa:run_mobile_test` | Execução de testes Mobile via Appium MCP |
| `@fastqa:run_mobile_exploratory_test` | Teste exploratório Mobile via Appium MCP |

### Fase 4: Automação → `04-fastqa-automation.md`

| Comando | Descrição |
|---------|-----------|
| `@fastqa:automate_test` | Gerar scripts automatizados |
| `@fastqa:create_mobile_automation` | Criar automação de testes Mobile |
| `@fastqa:install_framework` | Instalar framework |
| `@fastqa:api_create_automated` | Automação de API |
| `@fastqa:verify_and_fix` | Verificar, corrigir e refatorar scripts |

### Fase 5: Azure DevOps → `05-fastqa-azure-devops.md`

| Comando | Descrição |
|---------|-----------|
| `@fastqa:azdo_get_work_item_by_id_or_title` | Consultar work item |
| `@fastqa:azdo_list_work_items_by_sprint` | Listar por sprint |
| `@fastqa:azdo_create_work_item` | Criar work item |
| `@fastqa:azdo_create_bug` | Criar bug QA |
| `@fastqa:azdo_create_test_case` | Criar test case |
| `@fastqa:azdo_update_work_item` | Atualizar work item |
| `@fastqa:azdo_link_work_items` | Vincular work items |
| `@fastqa:azdo_upload_evidence` | Upload evidência |
| `@fastqa:azdo_upload_folder_evidence` | Upload pasta evidências |
| `@fastqa:azdo_upload_test_execution` | Fluxo completo execução |
| `@fastqa:azdo_upload_batch_test_execution` | Upload em lote |
| `@fastqa:azdo_list_test_plans` | Listar Test Plans |
| `@fastqa:azdo_add_testcase_to_suite` | Adicionar TC a Suite |
| `@fastqa:azdo_generate_report` | Relatório execução |
| `@fastqa:azdo_push_automation` | Push automação |
| `@fastqa:azdo_generate_pipeline` | Gerar pipeline YAML |
| `@fastqa:azdo_sync_pipeline_results` | Sincronizar resultados |
| `@fastqa:azdo_create_repo` | Criar repositório |
| `@fastqa:azdo_create_pipeline` | Criar definição de pipeline |
| `@fastqa:azdo_run_pipeline` | Executar pipeline com polling |
| `@fastqa:azdo_set_pipeline_variable` | Configurar Variable Group |
| `@fastqa:azdo_verify_pipeline_results` | Verificar resultados + diagnóstico |
| `@fastqa:azdo_create_test_plan` | Criar Test Plan com suites |
| `@fastqa:azdo_update_test_plan` | Atualizar Test Plan |
| `@fastqa:azdo_health` | Diagnóstico da integração Azure DevOps |

### Fase 6: Análise de Regressão → `06-fastqa-regression.md`

| Comando | Descrição |
|---------|-----------|
| `@fastqa:generate_regression_map` | Gerar mapa de regressão a partir dos testes |
| `@fastqa:regression_analyze` | Analisar PR e gerar plano de regressão |
| `@fastqa:execute_regression_plan` | Executar plano de regressão |

## 🚀 Regras Globais

- ✅ **GHERKIN:** Por padrão, keywords em **INGLÊS** (`Given`, `When`, `Then`) + conteúdo em **PORTUGUÊS**
- ✅ **Exceção (`@fastqa:test_case_with_fastqa`):** respeitar o formato configurado (`test_case_format`) e o idioma escolhido no wizard (Português, Inglês ou Español)
- ✅ **Azure DevOps:** SEMPRE usar scripts **TypeScript** (`npx tsx`) — NUNCA PowerShell (.ps1)
- ✅ Não hardcodar credenciais
- ✅ Não commitar evidências binárias
- ✅ Estrutura padrão: `automated_test/` (raiz do projeto), `fastqa/manual_test/`, `fastqa/scripts/`

---

## ⚙️ `@fastqa:setup_project`

> **Detalhes completos abaixo — este comando está neste arquivo.**

### Fase 0-1: Carregamento & Análise de Requisitos

| Comando | Descrição | Arquivo |
|---------|-----------|---------|
| `@fastqa:load_pbi` | Carregar PBI do Azure DevOps | `01-fastqa-requirements.md` |
| `@fastqa:identify_gaps` | Identificar gaps em requisitos | `01-fastqa-requirements.md` |
| `@fastqa:estimate_effort` | Estimativa de esforço de testes | `01-fastqa-requirements.md` |
| `@fastqa:analyze_requirements` | Análise e estruturação de requisitos | `01-fastqa-requirements.md` |
| `@fastqa:map_behaviors` | Mapeamento de comportamentos testáveis | `01-fastqa-requirements.md` |

### Fase 2: Geração & Validação de Cenários

| Comando | Descrição | Arquivo |
|---------|-----------|---------|
| `@fastqa:ac_scope_analysis` | Análise de escopo de ACs para testes | `02-fastqa-test-design.md` |
| `@fastqa:test_case_with_fastqa` | Gerar casos de teste (Gherkin ou Step by Step, sem Playwright) | `02-fastqa-test-design.md` |
| `@fastqa:test_case_with_playwright_mcp` | Gerar cenários com Playwright MCP | `02-fastqa-test-design.md` |
| `@fastqa:validate_scenarios` | Validar qualidade e cobertura Gherkin | `02-fastqa-test-design.md` |
| `@fastqa:api_generate_scenarios` | Gerar cenários Gherkin para API | `02-fastqa-test-design.md` |
| `@fastqa:exploratory_api_test` | Testes exploratórios API (POISED/VADER) | `02-fastqa-test-design.md` |
| `@fastqa:destructive_api_test` | Testes destrutivos API (vulnerabilidades) | `02-fastqa-test-design.md` |

### Fase 3: Execução de Testes

| Comando | Descrição | Arquivo |
|---------|-----------|---------|
| `@fastqa:run_manual_test` | Execução manual via Playwright MCP | `03-fastqa-execution.md` |
| `@fastqa:run_parallel_tests` | Execução paralela de cenários | `03-fastqa-execution.md` |
| `@fastqa:run_manual_api_test_swagger` | Execução de API via Swagger UI + MCP | `03-fastqa-execution.md` |
| `@fastqa:run_mobile_test` | Execução de testes Mobile via Appium MCP | `03-fastqa-execution.md` |
| `@fastqa:run_mobile_exploratory_test` | Teste exploratório Mobile via Appium MCP | `03-fastqa-execution.md` |

### Fase 4: Automação

| Comando | Descrição | Arquivo |
|---------|-----------|---------|
| `@fastqa:automate_test` | Gerar scripts automatizados (Web/API/Mobile) | `04-fastqa-automation.md` |
| `@fastqa:create_mobile_automation` | Criar automação de testes Mobile (Appium) | `04-fastqa-automation.md` |
| `@fastqa:install_framework` | Instalar framework de testes | `04-fastqa-automation.md` |
| `@fastqa:api_create_automated` | Automação de testes de API (Playwright+TS) | `04-fastqa-automation.md` |
| `@fastqa:verify_and_fix` | Verificar, corrigir e refatorar scripts gerados | `04-fastqa-automation.md` |

### Fase 5.1: Azure DevOps — Board / Test Plan

| Comando | Descrição | Arquivo |
|---------|-----------|---------|
| `@fastqa:azdo_create_test_case` | Criar test case com steps | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_update_work_item` | Atualizar work item | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_link_work_items` | Vincular work items | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_upload_evidence` | Upload de evidência individual | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_upload_folder_evidence` | Upload de pasta de evidências | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_upload_test_execution` | Fluxo completo de execução | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_upload_batch_test_execution` | Upload em lote | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_list_test_plans` | Listar Test Plans/Suites/Cases | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_add_testcase_to_suite` | Adicionar TC a Suite | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_generate_report` | Relatório de execução | `05-fastqa-azure-devops.md` |

### Fase 5.2: Azure DevOps — CI / CD

| Comando | Descrição | Arquivo |
|---------|-----------|---------|
| `@fastqa:azdo_create_repo` | Criar repositório + push inicial | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_push_automation` | Push de automação para repo | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_generate_pipeline` | Gerar pipeline YAML CI/CD | `05-fastqa-azure-devops.md` |
| `@fastqa:azdo_sync_pipeline_results` | Sincronizar resultados pipeline | `05-fastqa-azure-devops.md` |

### Fase 6: Análise de Regressão

| Comando | Descrição | Arquivo |
|---------|-----------|---------|
| `@fastqa:generate_regression_map` | Gerar mapa de regressão a partir dos testes | `06-fastqa-regression.md` |
| `@fastqa:regression_analyze` | Analisar PR e gerar plano de regressão | `06-fastqa-regression.md` |
| `@fastqa:execute_regression_plan` | Executar plano de regressão com análise AI de falhas | `06-fastqa-regression.md` |

---

## ⚙️ `@fastqa:setup_project` — Setup do Projeto FastQA

Wizard interativo de configuração do projeto. O comando é executado via extensão FastQA no VS Code (`/setup_project`), que exibe diálogos nativos e popula automaticamente os arquivos de configuração.

**Workflow — 10 perguntas sequenciais:**

**Pré-pergunta:** O projeto já possui uma estrutura de testes?
- `Sim, já tenho uma estrutura` → modo **attach** (integra estrutura existente, detecta framework e caminhos automaticamente)
- `Não, configurar do zero` → modo **scaffold** (cria estrutura FastQA padrão)

---

**Pergunta 1/10 — 👤 Identificação:** Seu nome

**Pergunta 2/10 — 🏢 Cliente:** Qual é o cliente?

**Pergunta 3/10 — 📂 Projeto:** Nome do projeto

**Pergunta 4/10 — 👥 Squad:** Nome do squad responsável

---

**Pergunta 5/10 — 🔗 Integração, Gestão e Testes:** Selecione a ferramenta de integração e gerenciamento de testes
- Opções: `Azure DevOps + Test Plans` | `Azure DevOps (sem Test Plans)` | `Jira + Xray` | `Jira + Zephyr Scale` | `Jira + AssertThat` | `Jira (sem gerenciamento de testes)` | `Nenhuma` | `Outro`
- Se `Outro`: campo de texto livre (ex.: Linear, Trello, YouTrack)
- A escolha determina automaticamente o `integration` (Azure DevOps / Jira / Nenhuma) e o `testManagementTool` (ex.: Azure DevOps Test Plans / Jira + Xray / Nenhuma)

**Pergunta 5.1 (Condicional — apenas se Azure DevOps):** Deseja configurar as credenciais do MCP agora?
- `Sim, configurar agora` → solicita os três campos abaixo *(todos opcionais — pode deixar em branco)*:
  - **AZURE_DEVOPS_ORG_URL** — URL da organização (ex: `https://dev.azure.com/minha-org`)
  - **AZURE_DEVOPS_PAT** — Personal Access Token *(campo senha, mascarado)*
  - **AZURE_DEVOPS_DEFAULT_PROJECT** — Nome do projeto padrão
- `Não, configurar depois` → pula; pode ser configurado manualmente depois

> Ao informar as credenciais, a extensão atualiza automaticamente:
> 1. `.vscode/mcp.json` — servidor `azureDevOps` (campos `AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_PAT`, `AZURE_DEVOPS_DEFAULT_PROJECT`)
> 2. `fastqa/.env.example` — mesmas variáveis de ambiente
> 3. `fastqa/scripts/project_config.json` — seção `project_management.azure_devops`

---

**Pergunta 6/10 — 📝 Formato de Casos de Teste:** Qual o formato padrão para geração de casos de teste?
- `Gherkin (BDD)` → salva `test_case_format: "gherkin"` no `project_config.json`
- `Step by Step` → salva `test_case_format: "step_by_step"` no `project_config.json`
- `Outro` → abre campo de texto livre; salva `test_case_format: "<valor_digitado_em_snake_case>"` no `project_config.json`
- `Nenhum` → salva `test_case_format: "none"` no `project_config.json`

> O idioma (Português/Inglês/Español) é escolhido em tempo de execução no wizard de geração de cenários — não é armazenado no config.

---

**Pergunta 7/10 — 💻 Plataforma:** Qual a plataforma será testada?
- Opções: `Web` | `Mobile` | `API` | `Desktop`

**Perguntas 7a-7g (Condicional — apenas se Plataforma = Mobile):**

> **7a** é obrigatória (define Android ou iOS). Após isso, o usuário escolhe se deseja configurar as capabilities agora ou depois. Se escolher **"Não, configurar depois"**, todas as capabilities ficam com valores padrão e podem ser editadas manualmente em `project_config.json`.

| Sub-pergunta | Campo | Condição | Obrigatória | Exemplo |
|-------------|-------|----------|------------|--------|
| 7a — Plataforma Mobile | `platformName` | Sempre | Sim | `Android` ou `iOS` |
| 7b — Configurar capabilities agora? | — | Sempre | Sim | `Sim` / `Não` |
| 7c — Nome do Dispositivo | `appium:deviceName` | Se 7b = Sim | Não | `emulator-5554` |
| 7d — Auto Grant Permissions | `appium:autoGrantPermissions` | Se 7b = Sim + Android | Não | `Sim` / `Não` |
| 7d — Versão da Plataforma | `appium:platformVersion` | Se 7b = Sim + iOS | Não | `17.2` |
| 7e — Caminho do App | `appium:app` | Se 7b = Sim | Não | `apps/app.apk` |
| 7f — APP_PACKAGE | `appium:APP_PACKAGE` | Se 7b = Sim + Android | Não | `com.example.app` |
| 7g — APP_ACTIVITY | `appium:APP_ACTIVITY` | Se 7b = Sim + Android | Não | `.MainActivity` |
| 7f — Bundle ID | `bundleId` | Se 7b = Sim + iOS | Não | `com.example.app` |
| 7h — Appium Server URL | `appiumServerUrl` | Se 7b = Sim | Não | `http://localhost:4723` |

> `automationName` é definido automaticamente: `UiAutomator2` (Android) ou `XCUITest` (iOS)
>
> Todos os valores são salvos em `platform.details.mobile_capabilities` no `project_config.json`

**Pergunta 8/10 — 🧭 Framework de automação:** *(apenas no modo scaffold; no modo attach, detectado automaticamente)*
- **Web:** `Playwright/TypeScript` | `Playwright/JavaScript` | `Playwright/Python` | `Cypress/TypeScript` | `Cypress/JavaScript` | `Selenium/Python` | `Selenium/Java` | `Selenium/C#` | `Robot Framework/Python` | `Outro`
- **API:** `Supertest/TypeScript` | `Requests/Python` | `RestAssured/Java` | `Karate/Java` | `Robot Framework/Python` | `Playwright/TypeScript` | `Outro`
- **Mobile:** `WebdriverIO/TypeScript` | `WebdriverIO/JavaScript` | `Selenium/Python` | `Selenium/Java` | `Selenium/C#` | `Robot Framework/Python` | `Outro`
- **Desktop:** `Selenium/C#` | `Playwright/C#` | `Outro`
- Se `Outro`: campos de texto para nome do framework e linguagem

**Pergunta 9/10 — 🗄️ Formatos de massa de dados:** *(múltipla seleção)*
- `JSON (.json)` | `Excel (.xlsx)` | `CSV (.csv)` | `YAML (.yml)` | `XML (.xml)` | `Banco de Dados (SQL)` | `Fixtures (hardcoded)`

**Pergunta 10/10 — 🚀 Avanade CODE:** Configuração do Avanade CODE
- `Isolada` → instala BMAD Method localmente (`npm run setup:bmad` em `fastqa/`)
- `Integrada com o Time` → registra a escolha e exibe orientações para alinhamento com o time
- `Não instalar no momento` → registra `avanade_code.enabled: false` no `project_config.json`

---

**Após coletar as respostas, execute os seguintes passos na ordem:**

1. Copia a estrutura do template FastQA para o workspace (se ainda não existir)
2. Atualiza `.gitignore` com regras FastQA
3. Grava todas as escolhas em `fastqa/scripts/project_config.json`
4. Se credenciais Azure DevOps foram informadas: atualiza `.vscode/mcp.json` e `fastqa/.env.example`
5. Executa `npm install` na pasta `fastqa/`

**Resultado esperado:**
- Estrutura de pastas FastQA completa (`automated_test/` na raiz do projeto, `fastqa/manual_test/`, `fastqa/scripts/`)
- `fastqa/scripts/project_config.json` criado e preenchido com as escolhas do wizard
- Todos os agents FastQA lerão automaticamente o `project_config.json`
- `.vscode/mcp.json` e `fastqa/.env.example` configurados com credenciais Azure DevOps *(se informadas)*
- Avanade CODE configurado conforme escolha

**Pós-setup — Informações condicionais exibidas ao final:**

Se **Plataforma = Mobile**, exibir tabela de pré-requisitos:

| # | Requisito | Comando de validação |
|---|-----------|---------------------|
| 1 | JDK 17+ instalado e `JAVA_HOME` configurado | `java -version` |
| 2 | Android Studio + SDK instalados e `ANDROID_HOME` configurado | `adb version` |
| 3 | Node.js LTS + npm | `node -v && npm -v` |
| 4 | Appium Server + driver uiautomator2 | `appium --version && appium driver list --installed` |
| 5 | Ambiente validado com Appium Doctor | `appium-doctor --android` |
| 6 | Appium Inspector instalado | [Download](https://github.com/appium/appium-inspector/releases) |
| 7 | Emulador ou dispositivo físico conectado | `adb devices` |

> 📖 Guia completo: `fastqa/agents/connectors/mobile/MOBILE_GUIDE.md`

Se **Plataforma = Mobile** e **Framework = WebdriverIO**, exibir adicionalmente:
- Comandos de instalação das dependências WebdriverIO (`@wdio/cli`, `@wdio/local-runner`, `@wdio/appium-service`, etc.)
- Exemplo de capabilities Android (`platformName`, `appium:deviceName`, `appium:automationName`, `appium:autoGrantPermissions`, `appium:APP_PACKAGE`, `appium:APP_ACTIVITY`, `appium:app`)
> 📖 Guia completo: `fastqa/agents/connectors/mobile/webdriverio/DEVELOPER_WEBDRIVERIO_GUIDE.md`

---

## 🔍 Comandos de Help

### `@fastqa:help`

Exibe **sempre** o menu completo de comandos FastQA, organizado por fases, contendo para **cada comando**:
- nome do comando
- breve descrição (1 linha)

Formato obrigatório de saída do `@fastqa:help`:

`📚 Menu de Comandos FastQA`

- 🔍 **Fase 0 — Setup**
  - `@fastqa:setup_project` — Configura estrutura do projeto FastQA via wizard.

- 🔍 **Fase 1 — Análise de Requisitos**
  - `@fastqa:identify_gaps` — Identifica gaps, ambiguidades e inconsistências.
  - `@fastqa:estimate_effort` — Estima esforço e massa de testes.
  - `@fastqa:analyze_requirements` — Estrutura requisitos em formato testável.
  - `@fastqa:map_behaviors` — Mapeia fluxos principal, alternativos e exceções.

- 📝 **Fase 2 — Geração e Validação de Cenários**
  - `@fastqa:test_case_with_fastqa` — Gera casos de teste (Gherkin ou Step by Step) com FastQA Agents.
  - `@fastqa:test_case_with_playwright_mcp` — Gera cenários com apoio do Playwright MCP.
  - `@fastqa:validate_scenarios` — Valida cobertura, qualidade e automabilidade.
  - `@fastqa:api_generate_scenarios` — Gera cenários Gherkin para APIs.
  - `@fastqa:exploratory_api_test` — Executa testes exploratórios API (POISED/VADER).
  - `@fastqa:destructive_api_test` — Executa testes destrutivos de API.

- 🎬 **Fase 3 — Execução de Testes**
  - `@fastqa:run_manual_test` — Executa cenários Web manualmente via Playwright MCP.
  - `@fastqa:run_parallel_tests` — Executa múltiplos cenários em paralelo.
  - `@fastqa:run_manual_api_test_swagger` — Executa testes de API via Swagger + MCP.
  - `@fastqa:run_mobile_test` — Executa cenários Mobile (Android/iOS) via Appium MCP.
  - `@fastqa:run_mobile_exploratory_test` — Executa testes exploratórios Mobile via Appium MCP com geração opcional de evidências e cenários.

- 🤖 **Fase 4 — Automação**
  - `@fastqa:automate_test` — Gera scripts automatizados Web/Mobile.
  - `@fastqa:create_mobile_automation` — Cria automação de testes Mobile (Appium/WebdriverIO).
  - `@fastqa:install_framework` — Instala e configura framework de testes.
  - `@fastqa:api_create_automated` — Gera automação de testes de API.

- 🚀 **Fase 5 — Azure DevOps**
  - 🚀 **Fase 5.1 — Azure DevOps (Board / Test Plan)**
    - `@fastqa:load_pbi` — Carrega PBI/User Story do Azure DevOps.
    - `@fastqa:azdo_get_work_item_by_id_or_title` — Consulta work item por ID ou título.
    - `@fastqa:azdo_list_work_items_by_sprint` — Lista work items por sprint/iteração.
    - `@fastqa:azdo_create_work_item` — Cria work item no Azure DevOps.
    - `@fastqa:azdo_create_bug` — Cria bug com dados de QA e evidências.
    - `@fastqa:azdo_create_test_case` — Cria test case com steps.
    - `@fastqa:azdo_update_work_item` — Atualiza campos de work item.
    - `@fastqa:azdo_link_work_items` — Vincula work items.
    - `@fastqa:azdo_upload_evidence` — Faz upload de evidência individual.
    - `@fastqa:azdo_upload_folder_evidence` — Faz upload de pasta de evidências.
    - `@fastqa:azdo_upload_test_execution` — Executa fluxo completo de execução.
    - `@fastqa:azdo_upload_batch_test_execution` — Faz upload em lote de execuções.
    - `@fastqa:azdo_list_test_plans` — Lista Test Plans, Suites e Cases.
    - `@fastqa:azdo_add_testcase_to_suite` — Adiciona test case à suite.
    - `@fastqa:azdo_generate_report` — Gera relatório consolidado de execução.

  - 🚀 **Fase 5.2 — Azure DevOps (CI / CD)**
    - `@fastqa:azdo_create_repo` — Cria repositório com push inicial.
    - `@fastqa:azdo_push_automation` — Publica automação em repositório Azure DevOps.
    - `@fastqa:azdo_generate_pipeline` — Gera pipeline YAML de CI/CD.
    - `@fastqa:azdo_sync_pipeline_results` — Sincroniza resultados de pipeline com Test Plan.
    

- ℹ️ **Outras opções de help**
  - `@fastqa_code:help` — Exibe o menu completo no modo Code QA (TEA ativado).
  - `@fastqa_code:help_code_avanade` — Exibe o menu de workflows BMAD com TEA ativado.

  Ao final do menu, apresentar o fluxo recomendado e aguardar a escolha do usuário.

### `@fastqa_code:help`

Mesmo menu do `@fastqa:help` (comando + breve descrição por fase), porém ativando o modo Code QA (`QA_AGENT_NAME`) previamente. Informa também o comando `@fastqa_code:help_code_avanade`.

### `@fastqa_code:help_code_avanade`

1. Ativa o modo Code QA (Test Architect & Quality Advisor) do **`QA_AGENT_NAME`**
2. Traz o MENU de Opções do `QA_WORKFLOWS_PATH`


