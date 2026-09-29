---
name: "resolver"
description: "Roteador dinâmico que lê project_config.json e direciona para o agent/connector correto"

tools:
  - memory
  - sequential-thinking
---

# FastQA Agent — Resolver de Conectores

## 🎯 Objetivo
Ler o arquivo `fastqa/scripts/project_config.json` e direcionar para o agent/connector correto com base nas configurações do projeto.

---

## 📋 Regras de Resolução

### Passo 1: Carregar Configuração
```
Ler: fastqa/scripts/project_config.json
Extrair:
  - framework  = connectors.output.automation_framework
  - language   = connectors.output.language
  - platform   = platform.type
  - use_bdd    = testing_approach.use_gherkin_bdd
  - test_case_format = testing_approach.test_case_format
  - inputs     = connectors.input.sources
  - tool       = project_management.tool
  - setup_mode = folder_structure.mode
  - tests_path = folder_structure.custom_paths.tests
  - pages_path = folder_structure.custom_paths.pages
  - config_path = folder_structure.custom_paths.config
  - results_path = folder_structure.custom_paths.results (opcional)
  - automation_root = folder_structure.custom_paths.automation_root
```

**Fallback obrigatório (compatibilidade):**
- Se `custom_paths` não existir ou vier vazio, usar padrão default:
  - Web: `automated_test/web/{config|data|pages|support|tests|results}`
  - API: `automated_test/api/{config|data|schemas|support|tests|results}`
  - Mobile: `automated_test/mobile/{config|data|screens|support|tests|results}`

### Passo 2: Resolver Caminho do Agent

**Para Fase 0 a 3 (análise, geração, execução manual):**
→ Sempre usar agents de: `fastqa/agents/core/`
→ Esses agents são **agnósticos** de framework/linguagem

> **📌 ROTEAMENTO DO COMANDO `test_case_with_fastqa`:**
> O agente gerador de casos de teste é determinado pelo campo `testing_approach.test_case_format` do `project_config.json`:
>
> | Valor de `test_case_format` | Agent a utilizar |
> |-----------------------------|-----------------|
> | `gherkin` (padrão) | `fastqa/agents/core/fastqa_2.1_gherkin_writer.md` |
> | `step_by_step` | `fastqa/agents/core/fastqa_2.6_step_by_step_writer.md` |
>
> **Nota:** o idioma (Português/English/Español) é escolhido pelo usuário no wizard em tempo de execução e **não** é armazenado no `project_config.json`.
> **Fallback:** se `test_case_format` não existir ou tiver valor desconhecido → usar `fastqa_2.1_gherkin_writer.md`

> **📌 MAPEAMENTO FASE 3 — Execução Mobile:**
> | Comando | Agent |
> |---------|-------|
> | `@fastqa:run_mobile_test` | `fastqa/agents/core/fastqa_3.4_run_mobile_test.md` |
> | `@fastqa:run_mobile_exploratory_test` | `fastqa/agents/core/fastqa_3.5_run_mobile_exploratory_test.md` |

**Para Fase 4 (automação):**

**Opção 1 - Connectors específicos (Recomendado):**
→ Resolver caminho conforme tabela de combinações disponíveis (seção 3.1)

**Opção 2 - Agent genérico de API:**
→ Se `platform.type === 'api'` e comando `@fastqa:api_create_automated`
→ Resolver caminho: `fastqa/agents/core/fastqa_4.2_api_create_automated_test.md`
→ Este agent é framework-agnostic e gera código Playwright + TypeScript por padrão
→ **Nota:** Este arquivo será consolidado nos connectors específicos em versões futuras

**Opção 3 - Guia de Execução (`@fastqa:run_guide`):**
→ Comando `@fastqa:run_guide` **SEMPRE** usa: `fastqa/agents/core/fastqa_4.3_run_guide.md`
→ Agent é framework-agnóstico: analisa pipeline CI/CD + arquivos do projeto e gera passo a passo de execução
→ Não gera código — apenas documenta como executar a automação existente
→ Funciona para qualquer framework ou linguagem configurado em `project_config.json`

**Para Fase 5 (integração Azure DevOps):**
→ Sempre usar agent de: `fastqa/agents/core/fastqa_5.1_azure_devops.md`
→ Scripts TypeScript em: `fastqa/scripts/azure-devops/commands/`
→ Documentação completa: `.github/instructions/fastQAAzureDevOps.instructions.md`

> **📌 EXCEÇÃO:** O comando `@fastqa:azdo_get_work_item` **SEMPRE** utiliza **exclusivamente** o **MCP Azure DevOps** (`azureDevOps` em `.vscode/mcp.json`) para consultar work items. Ele **NÃO** utiliza scripts TypeScript nem Playwright MCP. Todos os demais comandos `@fastqa:azdo_*` continuam usando os scripts TypeScript.

**Para Fase 6 (análise de regressão):**
→ Sempre usar agents de: `fastqa/agents/core/`
→ Scripts TypeScript em: `fastqa/scripts/regression/commands/`
→ Mapeamento app↔testes: `fastqa/scripts/regression-map.yaml`

| Comando | Agent |
|---------|-------|
| `@fastqa:regression_analyze` | `agents/core/fastqa_6.1_regression_analyzer.md` |
| `@fastqa:generate_regression_map` | `agents/core/fastqa_6.2_generate_regression_map.md` |
| `@fastqa:execute_regression_plan` | `agents/core/fastqa_6.3_execute_regression_plan.md` |

### Passo 3: Mapeamento de Resolução

**3.1 — Web e Mobile Automation:**

> **📌 Todos os frameworks** seguem a estrutura `{platform}/{framework}/{language}/`.
> O resolver usa `platforms[selected].type` (lowercase) como **primeiro** nível do caminho.
> Apenas ferramentas exclusivamente API (RestAssured, Supertest, Requests, Karate) ficam em `api/{framework}/` sem subpasta de linguagem.

| Framework   | Linguagem   | Plataforma | Agent de Automação                                                                         |
|-------------|-------------|------------|--------------------------------------------------------------------------------------------|
| Playwright  | TypeScript  | Web        | `agents/connectors/web/playwright/typescript/fastqa_4.1_create_automated_test.md`          |
| Playwright  | TypeScript  | API        | `agents/connectors/api/playwright/typescript/fastqa_4.1_create_automated_test.md`          |
| Playwright  | Python      | Web        | `agents/connectors/web/playwright/python/fastqa_4.1_create_automated_test.md`              |
| Playwright  | Python      | API        | `agents/connectors/api/playwright/python/fastqa_4.1_create_automated_test.md`              |
| Playwright  | Java        | Web        | `agents/connectors/web/playwright/java/fastqa_4.1_create_automated_test.md`                |
| Playwright  | Java        | API        | `agents/connectors/api/playwright/java/fastqa_4.1_create_automated_test.md`                |
| Playwright  | C#          | Web        | `agents/connectors/web/playwright/csharp/fastqa_4.1_create_automated_test.md`              |
| Playwright  | C#          | API        | `agents/connectors/api/playwright/csharp/fastqa_4.1_create_automated_test.md`              |
| Cypress     | TypeScript  | Web        | `agents/connectors/web/cypress/typescript/fastqa_4.1_create_automated_test.md`             |
| Cypress     | TypeScript  | API        | `agents/connectors/api/cypress/typescript/fastqa_4.1_create_automated_test.md`             |
| Cypress     | JavaScript  | Web        | `agents/connectors/web/cypress/javascript/fastqa_4.1_create_automated_test.md`             |
| Cypress     | JavaScript  | API        | `agents/connectors/api/cypress/javascript/fastqa_4.1_create_automated_test.md`             |
| WebdriverIO | TypeScript  | Web        | `agents/connectors/web/webdriverio/typescript/fastqa_4.1_create_automated_test.md`         |
| WebdriverIO | TypeScript  | Mobile     | `agents/connectors/mobile/webdriverio/typescript/fastqa_4.1_create_automated_test.md`      |
| WebdriverIO | JavaScript  | Web        | `agents/connectors/web/webdriverio/javascript/fastqa_4.1_create_automated_test.md`         |
| WebdriverIO | JavaScript  | Mobile     | `agents/connectors/mobile/webdriverio/javascript/fastqa_4.1_create_automated_test.md`      |
| Selenium    | Python      | Web        | `agents/connectors/web/selenium/python/fastqa_4.1_create_automated_test.md`                |
| Selenium    | Java        | Web        | `agents/connectors/web/selenium/java/fastqa_4.1_create_automated_test.md`                  |
| Selenium    | C#          | Web        | `agents/connectors/web/selenium/csharp/fastqa_4.1_create_automated_test.md`                |
| Robot       | Python      | Web        | `agents/connectors/web/robot/python/fastqa_4.1_create_automated_test.md`                   |
| Robot       | Python      | Mobile     | `agents/connectors/mobile/robot/python/fastqa_4.1_create_automated_test.md`                |
| Robot       | Python      | API        | `agents/connectors/api/robot/python/fastqa_4.1_create_automated_test.md`                   |
| RestAssured | Java        | API        | `agents/connectors/api/restassured/fastqa_4.1_create_automated_test.md`                    |
| Supertest   | TypeScript  | API        | `agents/connectors/api/supertest/fastqa_4.1_create_automated_test.md`                      |
| Requests    | Python      | API        | `agents/connectors/api/requests/fastqa_4.1_create_automated_test.md`                       |
| Karate      | Java        | API        | `agents/connectors/api/karate/fastqa_4.1_create_automated_test.md`                         |

**Regra de resolução de caminho:**
```
caminho = "agents/connectors/{platform}/{framework}/{language}/{agent-file}.md"
onde:
  platform  = platforms[selected].type.toLowerCase()               // ex: "web", "api", "mobile"
  framework = platforms[selected].automation_framework.toLowerCase() // ex: "playwright", "cypress"
  language  = platforms[selected].language.toLowerCase()            // ex: "typescript", "python"

Exceção — ferramentas API sem variação de linguagem (karate, requests, restassured, supertest):
  caminho = "agents/connectors/api/{framework}/{agent-file}.md"
```

**3.2 — Guia de Execução (Framework-Agnóstico):**

| Comando | Condição | Agent |
|---------|----------|-------|
| `@fastqa:run_guide` | Qualquer framework/linguagem | `agents/core/fastqa_4.3_run_guide.md` |

**3.3 — API Automation (Agent Genérico):**

| Comando | Condição | Agent de Automação |
|---------|----------|--------------------|

| `@fastqa:api_create_automated` | `platform.type === 'api'` | `agents/core/fastqa_4.2_api_create_automated_test.md` |

> **📌 NOTA:** O agent genérico `fastqa_4.2_api_create_automated_test.md` é usado para automação de testes de API quando o comando específico `@fastqa:api_create_automated` é invocado. Este agent gera código Playwright + TypeScript por padrão, independentemente do framework configurado. Em versões futuras, este arquivo será consolidado nos connectors específicos de API (Supertest, Requests, RestAssured, Karate).

> **⚠️ ORDEM DE RESOLUÇÃO:** 
> 1. Se comando for `@fastqa:api_create_automated` → usar `core/fastqa_4.2_api_create_automated_test.md`
> 2. Se comando for `@fastqa:create_mobile_automation` → forçar `platform = mobile` e usar a combinação mobile existente na tabela 3.1
> 3. Se comando for `@fastqa:run_mobile_exploratory_test` → usar `core/fastqa_3.5_run_mobile_exploratory_test.md`
> 4. Caso contrário, para `@fastqa:automate_test` → usar a combinação existente na tabela 3.1
> 5. Se comando for `@fastqa:run_guide` → usar `core/fastqa_4.3_run_guide.md`


### Passo 4: Variáveis de Contexto

Ao carregar qualquer agent, injetar as seguintes variáveis:

```
{{PROJECT_NAME}}     = analysis.purpose (ou analysis.application_description)
{{FRAMEWORK}}        = connectors.output.automation_framework
{{LANGUAGE}}         = connectors.output.language
{{PLATFORM}}         = platform.type
{{USE_BDD}}          = testing_approach.use_gherkin_bdd
{{TEST_CASE_FORMAT}} = testing_approach.test_case_format
                       # Valores: gherkin | step_by_step
                       # Fallback: gherkin
{{TEST_MANAGEMENT_TOOL}} = testing_approach.test_management_tool
                           # Valores: 'Azure DevOps Test Plans' | 'Jira + Xray' | 'Jira + Zephyr Scale' | 'Jira + AssertThat' | 'Nenhuma'
                           # Determina a sintaxe de parâmetros em cenários/casos parametrizados
{{INPUT_TYPE}}       = connectors.input.type
{{INPUT_SOURCES}}    = connectors.input.sources
{{AZDO_ENABLED}}     = project_management.azure_devops.enabled
{{AZDO_ORG_URL}}     = project_management.azure_devops.org_url
{{AZDO_PROJECT}}     = project_management.azure_devops.project
{{JIRA_ENABLED}}     = project_management.jira.enabled
{{JIRA_URL}}         = project_management.jira.url
{{JIRA_PROJECT_KEY}} = project_management.jira.project_key
{{BASE_URL}}         = platform.details.api_base_url (API) ou variável de ambiente (Web)
{{SETUP_MODE}}       = folder_structure.mode
{{AUTOMATION_ROOT}}  = folder_structure.custom_paths.automation_root
{{TESTS_DIR}}        = folder_structure.custom_paths.tests
{{PAGES_DIR}}        = folder_structure.custom_paths.pages
{{CONFIG_DIR}}       = folder_structure.custom_paths.config
{{RESULTS_DIR}}      = folder_structure.custom_paths.results (opcional) ou `{{AUTOMATION_ROOT}}/results`

# Preferências do wizard /test_case_with_fastqa (quando informado no prompt)
# — Gherkin (aplicável quando TEST_CASE_FORMAT = gherkin)
{{GHERKIN_CONTENT_LANGUAGE}}   = idioma do conteúdo dos cenários (Português | English | Español)
                               # Informado pelo usuário no wizard (não vem do project_config.json)
{{GHERKIN_KEYWORD_LANGUAGE}}   = idioma das keywords Gherkin (Português | Inglês | Español)
                               # Quando conteúdo = Português, pode ser Inglês (Given/When/Then) ou Português (Dado/Quando/Então)
                               # Para English/Español, keywords seguem automaticamente o idioma do conteúdo
{{GHERKIN_MAX_STEPS}}          = limite máximo de steps por cenário
{{GHERKIN_ALLOW_MULTIPLE_CORE_STEPS}} = permite múltiplos blocos Given/When/Then por cenário (sim/não)
{{GHERKIN_TITLE_PATTERN}}      = padrão de título dos cenários (CT) (opcional)
{{GHERKIN_ADDITIONAL_FIELDS}}  = lista de campos adicionais de negócio (opcional); separados por vírgula
                               # Cada campo deve aparecer entre o título do cenário e os steps Given/When/Then
                               # O valor de cada campo é gerado pelo agente conforme o contexto do cenário
                               # Ex: "Objective, Precondition" ou "Objetivo, Pré-condição, Sprint"
{{GHERKIN_QA_RECOMMENDATIONS}} = recomendações extras informadas pelo QA (opcional)

# — Step by Step (aplicável quando TEST_CASE_FORMAT = step_by_step)
{{STEP_BY_STEP_LANGUAGE}}      = idioma dos casos de teste (Português | English | Español)
                                 # Informado pelo usuário no wizard em tempo de execução (não vem do project_config.json)
{{STEP_MAX_STEPS}}             = limite máximo de passos por caso de teste
{{STEP_TITLE_PATTERN}}         = padrão de título dos casos de teste (CT) (opcional)
{{STEP_ADDITIONAL_FIELDS}}     = lista de campos adicionais de negócio (opcional); separados por vírgula
                               # Cada campo deve aparecer entre o título/cabeçalho do caso de teste e os passos
                               # O valor de cada campo é gerado pelo agente conforme o contexto do caso de teste
                               # Ex: "Objective, Precondition" ou "Story Points, Épico"
{{STEP_QA_RECOMMENDATIONS}}    = recomendações extras informadas pelo QA (opcional)

# Mobile Capabilities (quando platform.type = 'Mobile')
{{MOBILE_PLATFORM_NAME}}    = platform.details.mobile_capabilities.platform_name
{{MOBILE_PLATFORM_VERSION}} = platform.details.mobile_capabilities.platform_version
{{MOBILE_DEVICE_NAME}}      = platform.details.mobile_capabilities.device_name
{{MOBILE_AUTOMATION_NAME}}  = platform.details.mobile_capabilities.automation_name
{{MOBILE_AUTO_GRANT_PERMISSIONS}} = platform.details.mobile_capabilities.auto_grant_permissions
{{MOBILE_APP_PATH}}         = platform.details.mobile_capabilities.app_path
{{MOBILE_APP_PACKAGE}}      = platform.details.mobile_capabilities.app_package
{{MOBILE_APP_ACTIVITY}}     = platform.details.mobile_capabilities.app_activity
{{MOBILE_BUNDLE_ID}}        = platform.details.mobile_capabilities.bundle_id
{{MOBILE_APPIUM_SERVER_URL}} = platform.details.mobile_capabilities.appium_server_url

> **⚠️ Fallback para capabilities vazias:** As capabilities são opcionais no setup.
> Quando um valor estiver vazio no `project_config.json`, usar os defaults abaixo:
>
> | Placeholder | Default (Android) | Default (iOS) |
> |-------------|-------------------|---------------|
> | `{{MOBILE_DEVICE_NAME}}` | `emulator-5554` | `iPhone 15` |
> | `{{MOBILE_AUTOMATION_NAME}}` | `UiAutomator2` | `XCUITest` |
> | `{{MOBILE_AUTO_GRANT_PERMISSIONS}}` | `true` | — (não aplicável) |
> | `{{MOBILE_APP_PATH}}` | `apps/app.apk` | `apps/app.ipa` |
> | `{{MOBILE_APP_PACKAGE}}` | — (comentar linha) | — |
> | `{{MOBILE_APP_ACTIVITY}}` | — (comentar linha) | — |
> | `{{MOBILE_BUNDLE_ID}}` | — | — (comentar linha) |
> | `{{MOBILE_APPIUM_SERVER_URL}}` | `http://localhost:4723` | `http://localhost:4723` |
>
> Se `APP_PACKAGE`, `APP_ACTIVITY` ou `BUNDLE_ID` estiverem vazios, **comentar** a linha correspondente no código gerado.
```

### Passo 5: Mapeamento Plataforma → Diretório de Saída

Os arquivos gerados devem priorizar os caminhos definidos em `custom_paths`:

| Tipo | Fonte principal | Fallback legado |
|------|-----------------|-----------------|
| Raiz automação | `{{AUTOMATION_ROOT}}` | `automated_test/{platform}` |
| Testes | `{{TESTS_DIR}}` | `automated_test/{platform}/tests` |
| Pages/Screens | `{{PAGES_DIR}}` | `automated_test/{platform}/pages` ou `screens` |
| Config | `{{CONFIG_DIR}}` | `automated_test/{platform}/config` |
| Results | `{{RESULTS_DIR}}` | `automated_test/{platform}/results` |

Quando `custom_paths` não existir, usar a subpasta correta de `automated_test/`:

| Plataforma | Diretório de Saída | Padrão de Objetos |
|------------|-------------------|-------------------|
| **Web** | `automated_test/web/` | Page Object Model (`pages/`) |
| **API** | `automated_test/api/` | API Client Pattern (`support/`) + Schemas (`schemas/`) |
| **Mobile** | `automated_test/mobile/` | Screen Object Pattern (`screens/`) |

**Regra:** Ao gerar arquivos na Fase 4, seguir esta ordem:
1. Usar `{{AUTOMATION_ROOT}}` e demais variáveis (`{{TESTS_DIR}}`, `{{PAGES_DIR}}`, `{{CONFIG_DIR}}`, `{{RESULTS_DIR}}`)
2. Se ausentes, usar `automated_test/{platform}` conforme `project_config.json → platform.type`

**Recursos compartilhados** (usados por mais de uma plataforma) → `automated_test/shared/`

### Passo 6: Instalação do Framework

Antes de gerar código, o connector deve verificar se o framework está instalado.
Cada connector possui uma seção `## 🔧 Instalação` com os comandos exatos.

| Framework   | Linguagem  | Plataforma | Comando de Instalação |
|-------------|------------|------------|-----------------------|
| Playwright  | TypeScript | Web / API  | `npm install -D @playwright/test dotenv && npx playwright install` |
| Playwright  | Python     | Web / API  | `pip install pytest playwright pytest-html pytest-playwright && playwright install` |
| Playwright  | Java       | Web / API  | `mvn install` (pom.xml com `com.microsoft.playwright`) |
| Playwright  | C#         | Web / API  | `dotnet add package Microsoft.Playwright.NUnit && dotnet build && pwsh bin/Debug/net8.0/playwright.ps1 install` |
| Cypress     | TypeScript | Web / API  | `npm install -D cypress typescript` |
| Cypress     | JavaScript | Web / API  | `npm install -D cypress` |
| WebdriverIO | TypeScript | Web        | `npm install -D @wdio/cli @wdio/local-runner @wdio/mocha-framework @wdio/spec-reporter webdriverio typescript ts-node` |
| WebdriverIO | TypeScript | Mobile     | `npm init wdio@latest . && npm install appium-mcp@latest && npx appium driver install uiautomator2` |
| WebdriverIO | JavaScript | Web        | `npm install -D @wdio/cli @wdio/local-runner @wdio/mocha-framework @wdio/spec-reporter webdriverio` |
| WebdriverIO | JavaScript | Mobile     | `npm init wdio@latest . && npm install appium-mcp@latest && npx appium driver install uiautomator2` |
| Selenium    | Python     | Web        | `pip install selenium pytest pytest-html webdriver-manager` |
| Selenium    | Java       | Web        | `mvn install` (pom.xml com `selenium-java`) |
| Selenium    | C#         | Web        | `dotnet add package Selenium.WebDriver Selenium.Support WebDriverManager NUnit` |
| Robot       | Python     | Web        | `pip install robotframework robotframework-browser && rfbrowser init` |
| Robot       | Python     | Mobile     | `pip install robotframework robotframework-appiumlibrary && appium driver install uiautomator2` |
| Robot       | Python     | API        | `pip install robotframework robotframework-requests` |

| Supertest   | TypeScript | API        | `npm install -D supertest @types/supertest jest ts-jest @types/jest typescript` |
| Requests    | Python     | API        | `pip install requests pytest pytest-html jsonschema python-dotenv` |
| RestAssured | Java       | API        | `mvn install` (pom.xml com `io.rest-assured`) |
| Karate      | Java       | API        | `mvn install` (pom.xml com `com.intuit.karate`) |

---

## ⚠️ Fallback

Se o connector não existir para a combinação framework + linguagem:
1. Avisar o usuário: "Connector para {framework}/{language} ainda não disponível"
2. Sugerir combinação mais próxima disponível
3. Oferecer usar o agent core genérico com instruções adaptadas manualmente

---

## 🔄 Exemplo de Fluxo

```
Usuário: @fastqa:automate_test
    │
    ├─ Resolver lê project_config.json
    │   → framework = "Cypress"
    │   → language  = "TypeScript"
    │
    ├─ Resolver monta caminho:
    │   → platform  = "web"
    │   → agents/connectors/web/cypress/typescript/fastqa_4.1_create_automated_test.md
    │
    ├─ Verifica se arquivo existe
    │   → ✅ Existe → Carrega agent
    │   → ❌ Não existe → Fallback
    │
    └─ Injeta variáveis de contexto e executa
```

---

## 🗺️ Contexto de Jornada

Antes de resolver qualquer comando:
1. Leia `fastqa/scripts/journey_state.json`
2. Se `active_journey` não for `null`:
   - Injete no contexto do agent: jornada ativa, step atual, artefatos anteriores
   - Passe o `context` (pbi_id, test_plan_id, pipeline_id, build_id, repo_name) para que o agent tenha acesso a dados de steps anteriores
   - Inclua `journey_display_name` e `current_step_index` / `total_steps` para o footer proativo
3. Ao final da execução do agent, o footer proativo (presente em cada agent) atualizará o `journey_state.json`

**Resolução do comando `@fastqa:journey`:**
→ Redirecionar para `fastqa/agents/core/fastqa_0.2_journey_selector.md`

### Variáveis de Jornada (injetar junto com variáveis do Passo 4)

```
{{JOURNEY_ACTIVE}}       = journey_state.active_journey
{{JOURNEY_NAME}}         = journey_state.journey_display_name
{{JOURNEY_STEP_CURRENT}} = journey_state.current_step_index + 1
{{JOURNEY_STEP_TOTAL}}   = journey_state.total_steps
{{JOURNEY_PBI_ID}}       = journey_state.context.pbi_id
{{JOURNEY_TEST_PLAN_ID}} = journey_state.context.test_plan_id
{{JOURNEY_PIPELINE_ID}}  = journey_state.context.pipeline_id
{{JOURNEY_BUILD_ID}}     = journey_state.context.build_id
{{JOURNEY_REPO_NAME}}    = journey_state.context.repo_name
```
