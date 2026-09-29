*** Settings ***
Documentation    Page Object — Checkout: Complete! (Confirmação de Compra — SauceDemo)
...              URL: https://www.saucedemo.com/checkout-complete.html
...              Locators validados via inspeção DOM real (Playwright MCP) — 14/05/2026
Library          Browser
Resource         ../config/variables.robot
Resource         HeaderPage.robot

*** Variables ***
# ===========================================================================
# URL
# ===========================================================================
${URL_CHECKOUT_DONE}          ${BASE_URL}${ROUTE_CHECKOUT_DONE}

# ===========================================================================
# Estrutura da página
# ===========================================================================
${PAGE_TITLE}                 .title
${COMPLETE_HEADER}            .complete-header
${COMPLETE_TEXT}              .complete-text
${PONY_EXPRESS_IMG}           [data-test="pony-express"]
${BTN_BACK_HOME}              [data-test="back-to-products"]

# ===========================================================================
# Textos esperados (validados via Playwright MCP — 14/05/2026)
# ===========================================================================
${TEXT_COMPLETE_HEADER}       Thank you for your order!
${TEXT_COMPLETE_BODY}         Your order has been dispatched, and will arrive just as fast as the pony can get there!
${TEXT_PAGE_TITLE}            Checkout: Complete!

*** Keywords ***
# ===========================================================================
# Verificações
# ===========================================================================
Verificar Titulo Do Checkout Completo
    [Documentation]    Valida que o título é "Checkout: Complete!".
    Wait For Elements State    ${PAGE_TITLE}    visible    timeout=${TIMEOUT}
    Get Text    ${PAGE_TITLE}    ==    ${TEXT_PAGE_TITLE}

Verificar Mensagem De Confirmacao
    [Documentation]    Valida que a mensagem "Thank you for your order!" está visível.
    Wait For Elements State    ${COMPLETE_HEADER}    visible    timeout=${TIMEOUT}
    Get Text    ${COMPLETE_HEADER}    ==    ${TEXT_COMPLETE_HEADER}

Verificar Texto De Confirmacao
    [Documentation]    Valida que o texto de detalhe da confirmação está visível e correto.
    Wait For Elements State    ${COMPLETE_TEXT}    visible    timeout=${TIMEOUT}
    Get Text    ${COMPLETE_TEXT}    contains    dispatched

Verificar Imagem Pony Express
    [Documentation]    Valida que a imagem do Pony Express está visível.
    Wait For Elements State    ${PONY_EXPRESS_IMG}    visible    timeout=${TIMEOUT}

Verificar Pagina De Confirmacao Completa
    [Documentation]    Valida todos os elementos da tela de confirmação.
    Verificar Titulo Do Checkout Completo
    Verificar Imagem Pony Express
    Verificar Mensagem De Confirmacao
    Verificar Texto De Confirmacao
    Wait For Elements State    ${BTN_BACK_HOME}    visible    timeout=${TIMEOUT}

# ===========================================================================
# Interações
# ===========================================================================
Clicar Em Back Home
    [Documentation]    Clica em "Back Home" e aguarda retorno ao inventário.
    Click    ${BTN_BACK_HOME}
    Wait For Elements State    .inventory_list    visible    timeout=${TIMEOUT}
