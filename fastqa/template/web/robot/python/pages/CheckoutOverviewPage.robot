*** Settings ***
Documentation    Page Object — Checkout: Overview (Step 2 — SauceDemo)
...              URL: https://www.saucedemo.com/checkout-step-two.html
...              Locators validados via inspeção DOM real (Playwright MCP) — 14/05/2026
Library          Browser
Resource         ../config/variables.robot
Resource         HeaderPage.robot

*** Variables ***
# ===========================================================================
# URL
# ===========================================================================
${URL_CHECKOUT_STEP2}         ${BASE_URL}${ROUTE_CHECKOUT_STEP2}

# ===========================================================================
# Estrutura da página
# ===========================================================================
${PAGE_TITLE}                 .title
${CART_ITEMS}                 .cart_item
${CART_ITEM_NAME}             .inventory_item_name
${CART_ITEM_PRICE}            .inventory_item_price
${CART_ITEM_QTY}              .cart_quantity
${LABEL_QTY}                  .cart_quantity_label
${LABEL_DESC}                 .cart_desc_label
${SUMMARY_INFO}               .summary_info

# ===========================================================================
# Informações de pagamento e envio
# ===========================================================================
${PAYMENT_INFO_LABEL}         .summary_info_label:has-text("Payment Information:")
${SHIPPING_INFO_LABEL}        .summary_info_label:has-text("Shipping Information:")
${PRICE_TOTAL_LABEL}          .summary_subtotal_label
${TAX_LABEL}                  .summary_tax_label
${TOTAL_LABEL}                .summary_total_label

# ===========================================================================
# Botões
# ===========================================================================
${BTN_FINISH}                 [data-test="finish"]
${BTN_CANCEL}                 [data-test="cancel"]

*** Keywords ***
# ===========================================================================
# Verificações
# ===========================================================================
Verificar Titulo Do Checkout Overview
    [Documentation]    Valida que o título é "Checkout: Overview".
    Wait For Elements State    ${PAGE_TITLE}    visible    timeout=${TIMEOUT}
    Get Text    ${PAGE_TITLE}    ==    Checkout: Overview

Verificar Quantidade De Itens No Resumo
    [Documentation]    Valida que o resumo exibe exatamente N itens.
    [Arguments]    ${quantidade_esperada}
    ${count}=    Get Element Count    ${CART_ITEMS}
    Should Be Equal As Integers    ${count}    ${quantidade_esperada}

Verificar Item No Resumo
    [Documentation]    Valida que um item com o nome especificado está no resumo do pedido.
    [Arguments]    ${nome_produto}
    Wait For Elements State    .cart_item:has-text("${nome_produto}")    visible    timeout=${TIMEOUT}

Verificar Secao De Pagamento Presente
    [Documentation]    Valida que a seção de Payment Information está visível.
    Wait For Elements State    ${PAYMENT_INFO_LABEL}    visible    timeout=${TIMEOUT}

Verificar Secao De Envio Presente
    [Documentation]    Valida que a seção de Shipping Information está visível.
    Wait For Elements State    ${SHIPPING_INFO_LABEL}    visible    timeout=${TIMEOUT}

Verificar Informacoes De Pedido Presentes
    [Documentation]    Valida todas as informações obrigatórias do resumo do pedido.
    Wait For Elements State    ${SUMMARY_INFO}          visible    timeout=${TIMEOUT}
    Wait For Elements State    ${PAYMENT_INFO_LABEL}    visible    timeout=${TIMEOUT}
    Wait For Elements State    ${SHIPPING_INFO_LABEL}   visible    timeout=${TIMEOUT}
    Wait For Elements State    ${PRICE_TOTAL_LABEL}     visible    timeout=${TIMEOUT}
    Wait For Elements State    ${TAX_LABEL}             visible    timeout=${TIMEOUT}
    Wait For Elements State    ${TOTAL_LABEL}           visible    timeout=${TIMEOUT}

Obter Subtotal
    [Documentation]    Retorna o texto do subtotal dos itens (ex: "Item total: $39.98").
    ${texto}=    Get Text    ${PRICE_TOTAL_LABEL}
    RETURN    ${texto}

Obter Total
    [Documentation]    Retorna o texto do total final incluindo impostos (ex: "Total: $43.18").
    ${texto}=    Get Text    ${TOTAL_LABEL}
    RETURN    ${texto}

# ===========================================================================
# Interações
# ===========================================================================
Clicar Em Finish
    [Documentation]    Clica no botão Finish e aguarda a tela de confirmação.
    Click    ${BTN_FINISH}
    Wait For Elements State    .complete-header    visible    timeout=${TIMEOUT}

Clicar Em Cancel No Overview
    [Documentation]    Clica no botão Cancel e aguarda retorno ao inventário.
    Click    ${BTN_CANCEL}
    Wait For Elements State    .inventory_list    visible    timeout=${TIMEOUT}
