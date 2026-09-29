---
name: "fastqa_4.1_create_automated_test_robot_python_web"
description: "Criador de Testes Automatizados — Robot Framework + Python (Web)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Robot Framework + Python (Web)

## 🎯 Objetivo
Gerar scripts automatizados em **Robot Framework + Python** para testes Web, usando a biblioteca `Browser` (Playwright).

---

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `platforms[selected].details.custom_paths.automation_root` → `{{AUTOMATION_ROOT}}`
- `platforms[selected].details.custom_paths.tests` → `{{TESTS_DIR}}`
- `platforms[selected].details.custom_paths.pages` → `{{PAGES_DIR}}`
- `platforms[selected].details.custom_paths.config` → `{{CONFIG_DIR}}`
- `platforms[selected].details.custom_paths.results` → `{{RESULTS_DIR}}`

Fallback (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/web`
- `{{TESTS_DIR}} = automated_test/web/tests`
- `{{PAGES_DIR}} = automated_test/web/page`
- `{{CONFIG_DIR}} = automated_test/web/config`
- `{{RESULTS_DIR}} = automated_test/web/results`

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** Gerado a partir da **funcionalidade informada pelo usuário**.
> - Arquivo de teste: `{funcionalidade_snake}.robot`
> - Resource (Page): `{FuncionalidadePascalCase}Page.robot`
> - Dados: `{funcionalidade_snake}_data.robot`
> - Exemplo: `"login usuario"` → `login_usuario.robot`, `LoginUsuarioPage.robot`

```
{{AUTOMATION_ROOT}}/
├── config/
│   └── variables.robot
├── data/
│   └── {funcionalidade_snake}_data.robot
├── page/
│   └── {FuncionalidadePascalCase}Page.robot
├── support/
│   └── common.robot
├── tests/
│   └── {funcionalidade_snake}.robot
├── results/
└── requirements.txt
```

---

## 📝 Templates

### Se BDD Habilitado (`{feature}.robot`)
```robot
*** Settings ***
Library           Browser
Resource          ../page/{FuncionalidadePascalCase}Page.robot
Resource          ../config/variables.robot
Suite Setup       New Browser    chromium    headless=true
Suite Teardown    Close Browser
Test Setup        New Page       ${BASE_URL}

*** Test Cases ***
{{SCENARIO_NAME}}
    [Documentation]    {{FEATURE_NAME}}
    [Tags]             {{FEATURE_NAME}}    positivo    {{US_ID}}
    Given que estou na página de login
    When preencho o campo email com "usuario@teste.com"
    And preencho o campo senha com "Senha@123"
    And clico no botão Entrar
    Then devo ser redirecionado para o dashboard
    And devo ver a mensagem de boas vindas

*** Keywords ***
Que estou na página de login
    Get Url    ==    ${BASE_URL}/login

Preencho o campo email com "${email}"
    Fill Text    id=email    ${email}

Preencho o campo senha com "${senha}"
    Fill Text    id=password    ${senha}

Clico no botão Entrar
    Click    button[type="submit"]

Devo ser redirecionado para o dashboard
    Wait For Navigation    url=${BASE_URL}/dashboard

Devo ver a mensagem de boas vindas
    Get Text    .welcome-text    ==    Bem-vindo
```

### Se BDD NÃO Habilitado (`{feature}.robot`)
```robot
*** Settings ***
Library           Browser
Resource          ../page/{FuncionalidadePascalCase}Page.robot
Resource          ../config/variables.robot

*** Test Cases ***
Login Com Credenciais Validas
    [Documentation]    Validar login com credenciais válidas
    [Tags]             login    positivo
    Open Login Page
    Input Email    usuario@teste.com
    Input Password    Senha@123
    Submit Login
    Verify Dashboard Is Displayed
    Verify Welcome Message    Bem-vindo
```

### Page Resource (`{FuncionalidadePascalCase}Page.robot`)
```robot
*** Settings ***
Library    Browser

*** Variables ***
${LOGIN_EMAIL}       id=email
${LOGIN_PASSWORD}    id=password
${LOGIN_BUTTON}      button[type="submit"]
${WELCOME_TEXT}      .welcome-text
${DASHBOARD_URL}     ${BASE_URL}/dashboard

*** Keywords ***
Open Login Page
    New Page    ${BASE_URL}/login

Input Email
    [Arguments]    ${email}
    Fill Text    ${LOGIN_EMAIL}    ${email}

Input Password
    [Arguments]    ${password}
    Fill Text    ${LOGIN_PASSWORD}    ${password}

Submit Login
    Click    ${LOGIN_BUTTON}

Verify Dashboard Is Displayed
    Wait For Navigation    url=${DASHBOARD_URL}

Verify Welcome Message
    [Arguments]    ${expected}
    Get Text    ${WELCOME_TEXT}    ==    ${expected}
```

### Variables (`variables.robot`)
```robot
*** Variables ***
${BASE_URL}           {{BASE_URL}}
${BROWSER}            chromium
${HEADLESS}           true
${VIEWPORT_WIDTH}     1366
${VIEWPORT_HEIGHT}    768
```

### Requirements (`requirements.txt`)
```
robotframework>=7.0
robotframework-browser>=18.0
```

---

## 📋 Pré-requisitos
- Python 3.10+
- `pip install -r requirements.txt`
- `rfbrowser init`

## 🔧 Instalação
```bash
pip install robotframework robotframework-browser
rfbrowser init
```

## 🚀 Comandos de Execução
```bash
robot tests/                             # Todos os testes
robot tests/{feature}.robot              # Específico
robot --outputdir results/ tests/        # Com relatório
robot --include login tests/             # Filtrar por tag
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução:**
```bash
robot tests/{funcionalidade_snake}.robot
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **Import Error** → corrigir `Library` / `Resource` declarations
   - **Element not found** → revisar locators no Resource file `.robot`
   - **Keyword not found** → verificar nome do keyword no resource
   - **Timeout** → aumentar `Set Browser Implicit Wait`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
