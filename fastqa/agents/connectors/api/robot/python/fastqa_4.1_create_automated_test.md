---
name: "fastqa_4.1_create_automated_test_robot_python_api"
description: "Criador de Testes Automatizados — Robot Framework + Python (API via RequestsLibrary)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Robot Framework + Python (API)

## 🎯 Objetivo
Gerar scripts automatizados em **Robot Framework + RequestsLibrary** para testes de API REST.

---

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `platforms[selected].details.custom_paths.automation_root` → `{{AUTOMATION_ROOT}}`
- `platforms[selected].details.custom_paths.tests` → `{{TESTS_DIR}}`
- `platforms[selected].details.custom_paths.config` → `{{CONFIG_DIR}}`
- `platforms[selected].details.custom_paths.results` → `{{RESULTS_DIR}}`

Fallback (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/api`
- `{{TESTS_DIR}} = automated_test/api/tests`
- `{{CONFIG_DIR}} = automated_test/api/config`
- `{{RESULTS_DIR}} = automated_test/api/results`

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** Gerado a partir da **funcionalidade informada pelo usuário**.
> - Arquivo de teste: `{funcionalidade_snake}.robot`
> - Resource de keywords: `{FuncionalidadePascalCase}Api.robot`
> - Exemplo: `"autenticacao"` → `autenticacao.robot`, `AutenticacaoApi.robot`

```
{{AUTOMATION_ROOT}}/
├── config/
│   └── variables.robot
├── schemas/
│   └── {funcionalidade_snake}_schema.json
├── support/
│   └── common_api.robot
├── tests/
│   └── {funcionalidade_snake}.robot
├── results/
└── requirements.txt
```

---

## 📝 Templates

### Arquivo de Teste (`{funcionalidade_snake}.robot`)
```robot
*** Settings ***
Library           RequestsLibrary
Library           Collections
Library           OperatingSystem
Resource          ../config/variables.robot
Resource          ../support/common_api.robot
Suite Setup       Create Session    api    ${BASE_URL}    headers=${DEFAULT_HEADERS}
Suite Teardown    Delete All Sessions

*** Test Cases ***
{{SCENARIO_NAME}} - Sucesso
    [Documentation]    {{FEATURE_NAME}}
    [Tags]             {{FEATURE_NAME}}    positivo    {{US_ID}}
    ${payload}=    Create Dictionary    email=usuario@teste.com    password=Senha@123
    ${response}=   POST On Session    api    /auth/login    json=${payload}
    Status Should Be    200    ${response}
    ${body}=       Set Variable    ${response.json()}
    Should Not Be Empty    ${body}[token]
    Dictionary Should Contain Key    ${body}    user

{{SCENARIO_NAME}} - Credenciais Inválidas
    [Documentation]    Garantir erro 401 para credenciais inválidas
    [Tags]             {{FEATURE_NAME}}    negativo
    ${payload}=    Create Dictionary    email=errado@teste.com    password=errado
    ${response}=   POST On Session    api    /auth/login    json=${payload}    expected_status=401
    Status Should Be    401    ${response}
    ${body}=       Set Variable    ${response.json()}
    Should Contain    str(${body})    error
```

### Keywords de API (`{FuncionalidadePascalCase}Api.robot`)
```robot
*** Settings ***
Library    RequestsLibrary
Library    Collections

*** Keywords ***
Autenticar Usuário
    [Arguments]    ${email}    ${password}
    ${payload}=    Create Dictionary    email=${email}    password=${password}
    ${response}=   POST On Session    api    /auth/login    json=${payload}
    [Return]       ${response}

Validar Status Code
    [Arguments]    ${response}    ${expected_status}
    Status Should Be    ${expected_status}    ${response}

Validar Campo No Body
    [Arguments]    ${response}    ${field}
    ${body}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${body}    ${field}

Obter Token De Autenticação
    [Arguments]    ${email}    ${password}
    ${response}=   Autenticar Usuário    ${email}    ${password}
    ${body}=       Set Variable    ${response.json()}
    [Return]       ${body}[token]
```

### Common API Support (`common_api.robot`)
```robot
*** Settings ***
Library    RequestsLibrary
Library    Collections

*** Keywords ***
Criar Header Com Token
    [Arguments]    ${token}
    ${headers}=    Create Dictionary
    ...    Authorization=Bearer ${token}
    ...    Content-Type=application/json
    [Return]    ${headers}

Validar Schema JSON
    [Arguments]    ${response}    ${schema_path}
    ${body}=         Set Variable          ${response.json()}
    ${schema_text}=  Get File              ${schema_path}
    # Usar jsonschema externamente ou validação manual por campo
    Log    Schema path: ${schema_path}
```

### Variables (`variables.robot`)
```robot
*** Variables ***
${BASE_URL}           {{BASE_URL}}
&{DEFAULT_HEADERS}    Content-Type=application/json    Accept=application/json
${REQUEST_TIMEOUT}    30
```

### Requirements (`requirements.txt`)
```
robotframework>=7.0
robotframework-requests>=0.9.7
```

---

## 📋 Pré-requisitos
- Python 3.10+
- `pip install -r requirements.txt`
- API disponível e acessível em `{{BASE_URL}}`

## 🔧 Instalação
```bash
pip install robotframework robotframework-requests
```

## 🚀 Comandos de Execução
```bash
robot tests/{funcionalidade_snake}.robot          # Executar teste
robot --outputdir results/ tests/                 # Com relatório
robot --include positivo tests/                   # Apenas cenários positivos
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
   - **ConnectionError** → verificar se `BASE_URL` está correto e API está no ar
   - **Status code mismatch** → revisar endpoint e payload
   - **KeyError** → campo não existe no response body, ajustar assertions
   - **RequestsLibrary not found** → `pip install robotframework-requests`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
