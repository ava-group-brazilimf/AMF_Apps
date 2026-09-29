---
name: "fastqa_4.1_create_automated_test_robot_python_mobile"
description: "Criador de Testes Automatizados — Robot Framework + Python (Mobile via AppiumLibrary)"

tools:
  - memory
  - sequential-thinking
  - appium-mcp
---

# Connector: Robot Framework + Python (Mobile)

## 🎯 Objetivo
Gerar scripts automatizados em **Robot Framework + AppiumLibrary** para testes Mobile (Android/iOS).

---

## 🔰 Passo 0 — Verificar Ambiente Mobile (Obrigatório)

> **Antes de qualquer ação**, perguntar ao usuário:
>
> **"Você já possui o ambiente mobile configurado? (Appium, Android SDK, emulador/dispositivo)"**

**Se o usuário responder NÃO ou tiver dúvida**, exibir o guia abaixo e **aguardar confirmação** antes de prosseguir:

| # | Requisito | Verificação |
|---|---|---|
| 1 | JDK 17+ instalado | `java -version` |
| 2 | Android Studio + SDK instalado | Android SDK Manager |
| 3 | Variável `ANDROID_HOME` configurada | `echo %ANDROID_HOME%` |
| 4 | Python 3.8+ instalado | `python --version` |
| 5 | Appium 2.x instalado | `appium -v` |
| 6 | Emulador ou dispositivo físico conectado | `adb devices` |

Para instalar as dependências Robot Framework + Appium:

```cmd
pip install robotframework robotframework-appiumlibrary
npx appium driver install uiautomator2
```

> 📖 Guia completo de pré-requisitos: `fastqa/agents/connectors/mobile/MOBILE_GUIDE.md`

**Se o usuário confirmar que o ambiente está pronto**, prosseguir para o Passo 0.1 (verificação do Appium MCP).

**0.1 — Verificar Appium MCP (obrigatório para locators precisos):**

Verificar disponibilidade via `tool_search_tool_regex` com padrão `appium_get_page_source|appium_find_elements`:

- **Disponível** → registrar ferramentas; durante a geração de Screen Resources usar `appium_get_page_source` para obter a árvore XML da tela atual e `appium_find_elements` para confirmar os accessibility IDs reais — substituir todos os `accessibility_id=placeholder` pelos valores inspecionados
- **Não disponível** → informar ao usuário:

> ⚠️ O servidor **appium-mcp** não está ativo. Para gerar locators precisos com base nos elementos reais do app:
> 1. Pressione `Ctrl+Shift+P` → "MCP: List Servers"
> 2. Localize **appium-mcp** e clique em **Start**
> 3. Confirme que o Appium Server está rodando (`appium --version`) e que há dispositivo/emulador conectado (`adb devices`)
>
> 📖 Configuração: `.vscode/mcp.json` (servidor `appium-mcp`)
>
> Deseja **continuar sem o MCP** (locators baseados nos test cases fornecidos) ou **aguardar ativação**?

**Aguardar resposta** antes de prosseguir.

---

**0.2 — Identificar Cenários (obrigatório quando múltiplos):**

Após receber o arquivo com os Test Cases, contar quantos `Scenario` / `Test Case` / casos de teste existem:

- **1 cenário** → prosseguir diretamente
- **Mais de 1 cenário** → listar todos numerados e perguntar ao usuário:

> **"Encontrei [N] cenários no arquivo:**
> 1. [nome do cenário 1]
> 2. [nome do cenário 2]
> ...
>
> Deseja automatizar **todos** ou **cenários específicos**? (ex.: `1, 3` ou `todos`)"

**Aguardar resposta** antes de prosseguir. Usar a seleção do usuário para determinar quais `Test Case` blocos gerar no `.robot`.

---

---

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `folder_structure.custom_paths.automation_root` → `{{AUTOMATION_ROOT}}`
- `folder_structure.custom_paths.tests` → `{{TESTS_DIR}}`
- `folder_structure.custom_paths.pages` → `{{SCREENS_DIR}}`
- `folder_structure.custom_paths.config` → `{{CONFIG_DIR}}`
- `folder_structure.custom_paths.results` → `{{RESULTS_DIR}}`

Fallback (se vazio):

> O subdiretório (`android/` ou `ios/`) é determinado por `platform.details.mobile_capabilities.platform_name` no `project_config.json`.

- `{{AUTOMATION_ROOT}} = automated_test/mobile`
- `{{TESTS_DIR}} = automated_test/mobile/android/tests` (ou `ios/tests` para iOS)
- `{{SCREENS_DIR}} = automated_test/mobile/android/screen` (ou `ios/screen` para iOS)
- `{{CONFIG_DIR}} = automated_test/mobile/config`
- `{{RESULTS_DIR}} = automated_test/mobile/android/results` (ou `ios/results` para iOS)

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** Gerado a partir da **funcionalidade informada pelo usuário**.
> - Arquivo de teste: `{funcionalidade_snake}.robot`
> - Screen Resource: `{FuncionalidadePascalCase}Screen.robot`
> - Dados: `{funcionalidade_snake}_data.robot`
> - Exemplo: `"login usuario"` → `login_usuario.robot`, `LoginUsuarioScreen.robot`

```
{{AUTOMATION_ROOT}}/
├── android/   (ou ios/ se plataforma iOS)
│   ├── data/
│   │   └── {funcionalidade_snake}_data.robot
│   ├── results/
│   │   └── (evidências geradas automaticamente)
│   ├── screen/
│   │   └── {FuncionalidadePascalCase}Screen.robot
│   ├── support/
│   │   └── gestures.robot
│   └── tests/
│       └── {funcionalidade_snake}.robot
├── app/
│   └── app.apk
├── config/
│   └── variables.robot
└── requirements.txt
```

---

## 📝 Templates

### Arquivo de Teste (`{funcionalidade_snake}.robot`)
```robot
*** Settings ***
Library           AppiumLibrary
Resource          ../screen/{FuncionalidadePascalCase}Screen.robot
Resource          ../../config/variables.robot
Suite Setup       Open Application    ${APPIUM_URL}
...               platformName=${PLATFORM}
...               deviceName=${DEVICE_NAME}
...               automationName=${AUTOMATION_NAME}
...               autoGrantPermissions=${AUTO_GRANT_PERMISSIONS}
...               APP_PACKAGE=${APP_PACKAGE}
...               APP_ACTIVITY=${APP_ACTIVITY}
...               app=${APP_PATH}
Suite Teardown    Close Application

*** Test Cases ***
{{SCENARIO_NAME}}
    [Documentation]    {{FEATURE_NAME}}
    [Tags]             {{FEATURE_NAME}}    positivo    {{US_ID}}
    Given que a tela de login está visível
    When preencho o email com "usuario@teste.com"
    And preencho a senha com "Senha@123"
    And toco no botão Entrar
    Then devo ver o dashboard

*** Keywords ***
Que a tela de login está visível
    Wait Until Element Is Visible    accessibility_id=email-input    timeout=15s

Preencho o email com "${email}"
    Input Text    accessibility_id=email-input    ${email}

Preencho a senha com "${senha}"
    Input Text    accessibility_id=password-input    ${senha}

Toco no botão Entrar
    Click Element    accessibility_id=login-button

Devo ver o dashboard
    Wait Until Element Is Visible    accessibility_id=dashboard-screen    timeout=15s
```

### Screen Resource (`{FuncionalidadePascalCase}Screen.robot`)

> **🔍 Se appium-mcp ativo:** Antes de fixar os locators, usar `appium_get_page_source` para obter a árvore XML da tela atual e `appium_find_elements` para validar os accessibility IDs reais. Substituir todos os `accessibility_id=placeholder` pelos valores inspecionados do app em execução.

```robot
*** Settings ***
Library    AppiumLibrary

*** Variables ***
${EMAIL_INPUT}       accessibility_id=email-input
${PASSWORD_INPUT}    accessibility_id=password-input
${LOGIN_BUTTON}      accessibility_id=login-button
${DASHBOARD}         accessibility_id=dashboard-screen
${WELCOME_TEXT}      accessibility_id=welcome-text

*** Keywords ***
Wait For Login Screen
    Wait Until Element Is Visible    ${EMAIL_INPUT}    timeout=15s

Fill Email
    [Arguments]    ${email}
    Input Text    ${EMAIL_INPUT}    ${email}

Fill Password
    [Arguments]    ${password}
    Input Text    ${PASSWORD_INPUT}    ${password}

Tap Login
    Click Element    ${LOGIN_BUTTON}

Verify Dashboard Visible
    Wait Until Element Is Visible    ${DASHBOARD}    timeout=15s

Get Welcome Text
    Get Text    ${WELCOME_TEXT}
```

### Gestures (`gestures.robot`)
```robot
*** Settings ***
Library    AppiumLibrary

*** Keywords ***
Swipe Up
    ${size}=    Get Window Size
    ${x}=       Evaluate    ${size['width']} / 2
    ${start_y}= Evaluate    ${size['height']} * 0.8
    ${end_y}=   Evaluate    ${size['height']} * 0.2
    Swipe    ${x}    ${start_y}    ${x}    ${end_y}    800

Swipe Down
    ${size}=    Get Window Size
    ${x}=       Evaluate    ${size['width']} / 2
    ${start_y}= Evaluate    ${size['height']} * 0.2
    ${end_y}=   Evaluate    ${size['height']} * 0.8
    Swipe    ${x}    ${start_y}    ${x}    ${end_y}    800

Long Press Element
    [Arguments]    ${locator}
    Long Press    ${locator}    1500
```

### Variables (`variables.robot`)
```robot
*** Variables ***
${APPIUM_URL}              http://localhost:4723
${PLATFORM}                Android
${DEVICE_NAME}             emulator-5554
${AUTOMATION_NAME}         UiAutomator2
${AUTO_GRANT_PERMISSIONS}  true
${APP_PACKAGE}             
${APP_ACTIVITY}            
${APP_PATH}                ${CURDIR}/../app/app.apk
```

### Requirements (`requirements.txt`)
```
robotframework>=7.0
robotframework-appiumlibrary>=2.0
Appium-Python-Client>=3.0
```

---

## 📋 Pré-requisitos
- Python 3.10+
- Appium Server 2.x (`npm install -g appium`)
- Driver UiAutomator2 (`appium driver install uiautomator2`)
- Android SDK ou Xcode instalado

## 🔧 Instalação
```bash
pip install robotframework robotframework-appiumlibrary
appium driver install uiautomator2
```

## 🚀 Comandos de Execução
```bash
appium &                                                        # Iniciar Appium Server
robot android/tests/{funcionalidade_snake}.robot               # Executar teste
robot --outputdir android/results/ android/tests/              # Com relatório
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução:**
```bash
robot android/tests/{funcionalidade_snake}.robot
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **SessionNotCreatedError** → verificar Appium Server, deviceName e capabilities
   - **Element not found** → revisar `accessibility_id` na Screen Resource
   - **AppiumLibrary not found** → `pip install robotframework-appiumlibrary`
   - **Timeout** → aumentar timeout em `Wait Until Element Is Visible`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
