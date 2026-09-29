*** Settings ***
Documentation    Page Object — Checkout: Your Information (Step 1 — SauceDemo)
...              URL: https://www.saucedemo.com/checkout-step-one.html
...              Locators validados via inspeção DOM real (Playwright MCP) — 14/05/2026
Library          Browser
Resource         ../config/variables.robot
Resource         HeaderPage.robot

*** Variables ***
# ===========================================================================
# URL
# ===========================================================================
${URL_CHECKOUT_STEP1}         ${BASE_URL}${ROUTE_CHECKOUT_STEP1}

# ===========================================================================
# Estrutura da página
# ===========================================================================
${PAGE_TITLE}                 .title

# ===========================================================================
# Formulário de informações pessoais
# ===========================================================================
${INPUT_FIRST_NAME}           [data-test="firstName"]
${INPUT_LAST_NAME}            [data-test="lastName"]
${INPUT_POSTAL_CODE}          [data-test="postalCode"]
${MSG_ERROR}                  [data-test="error"]
${ICON_ERROR_CLOSE}           .error-button

# ===========================================================================
# Botões
# ===========================================================================
${BTN_CONTINUE}               [data-test="continue"]
${BTN_CANCEL}                 [data-test="cancel"]

*** Keywords ***
# ===========================================================================
# Verificações
# ===========================================================================
Verificar Titulo Do Checkout Info
    [Documentation]    Valida que o título é "Checkout: Your Information".
    Wait For Elements State    ${PAGE_TITLE}    visible    timeout=${TIMEOUT}
    Get Text    ${PAGE_TITLE}    ==    Checkout: Your Information

Verificar Campos Do Formulario Presentes
    [Documentation]    Valida que todos os campos do formulário estão visíveis.
    Wait For Elements State    ${INPUT_FIRST_NAME}    visible    timeout=${TIMEOUT}
    Wait For Elements State    ${INPUT_LAST_NAME}     visible    timeout=${TIMEOUT}
    Wait For Elements State    ${INPUT_POSTAL_CODE}   visible    timeout=${TIMEOUT}
    Wait For Elements State    ${BTN_CONTINUE}        visible    timeout=${TIMEOUT}
    Wait For Elements State    ${BTN_CANCEL}          visible    timeout=${TIMEOUT}

Verificar Mensagem De Erro
    [Documentation]    Valida que a mensagem de erro está visível e contém o texto esperado.
    [Arguments]    ${mensagem}
    Wait For Elements State    ${MSG_ERROR}    visible    timeout=${TIMEOUT}
    Get Text    ${MSG_ERROR}    contains    ${mensagem}

# ===========================================================================
# Interações
# ===========================================================================
Preencher Informacoes De Checkout
    [Documentation]    Preenche os campos First Name, Last Name e Postal Code.
    [Arguments]    ${primeiro_nome}    ${ultimo_nome}    ${cep}
    Fill Text    ${INPUT_FIRST_NAME}    ${primeiro_nome}
    Fill Text    ${INPUT_LAST_NAME}     ${ultimo_nome}
    Fill Text    ${INPUT_POSTAL_CODE}   ${cep}

Clicar Em Continue
    [Documentation]    Clica no botão Continue.
    Click    ${BTN_CONTINUE}

Clicar Em Cancel No Checkout Info
    [Documentation]    Clica no botão Cancel e aguarda retorno ao carrinho.
    Click    ${BTN_CANCEL}
    Wait For Elements State    .cart_list    visible    timeout=${TIMEOUT}

Preencher E Continuar
    [Documentation]    Preenche os campos e clica em Continue. Usa dados padrão do .env.
    [Arguments]    ${primeiro_nome}=${CHECKOUT_FIRST_NAME}    ${ultimo_nome}=${CHECKOUT_LAST_NAME}    ${cep}=${CHECKOUT_ZIP}
    Preencher Informacoes De Checkout    ${primeiro_nome}    ${ultimo_nome}    ${cep}
    Clicar Em Continue
    Wait For Elements State    .summary_info    visible    timeout=${TIMEOUT}
