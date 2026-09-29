*** Settings ***
Documentation    Page Object — Product Detail Page (SauceDemo)
...              URL: https://www.saucedemo.com/inventory-item.html?id=N
...              Locators validados via inspeção DOM real (Playwright MCP) — 14/05/2026
Library          Browser
Resource         ../config/variables.robot
Resource         HeaderPage.robot

*** Variables ***
# ===========================================================================
# Elementos da página de detalhe do produto
# ===========================================================================
${PRODUCT_IMG}                .inventory_details_img
${PRODUCT_NAME}               .inventory_details_name
${PRODUCT_DESC}               .inventory_details_desc
${PRODUCT_PRICE}              .inventory_details_price
${BTN_ADD_TO_CART}            [data-test="add-to-cart"]
${BTN_REMOVE}                 [data-test="remove"]
${BTN_BACK}                   [data-test="back-to-products"]

*** Keywords ***
# ===========================================================================
# Verificações estruturais
# ===========================================================================
Verificar Elementos Da Pagina De Detalhe
    [Documentation]    Valida que todos os elementos estruturais do detalhe estão visíveis.
    Wait For Elements State    ${PRODUCT_IMG}    visible    timeout=${TIMEOUT}
    Wait For Elements State    ${PRODUCT_NAME}   visible    timeout=${TIMEOUT}
    Wait For Elements State    ${PRODUCT_DESC}   visible    timeout=${TIMEOUT}
    Wait For Elements State    ${PRODUCT_PRICE}  visible    timeout=${TIMEOUT}
    Wait For Elements State    ${BTN_ADD_TO_CART}    visible    timeout=${TIMEOUT}
    Wait For Elements State    ${BTN_BACK}       visible    timeout=${TIMEOUT}

Verificar Nome Do Produto
    [Documentation]    Valida que o nome do produto exibido corresponde ao esperado.
    [Arguments]    ${nome_esperado}
    Get Text    ${PRODUCT_NAME}    contains    ${nome_esperado}

Verificar Preco Do Produto
    [Documentation]    Valida que o preço exibido corresponde ao esperado.
    [Arguments]    ${preco_esperado}
    Get Text    ${PRODUCT_PRICE}    ==    ${preco_esperado}

# ===========================================================================
# Interações
# ===========================================================================
Adicionar Produto Ao Carrinho
    [Documentation]    Clica no botão "Add to cart" na página de detalhe do produto.
    Click    ${BTN_ADD_TO_CART}
    Wait For Elements State    ${BTN_REMOVE}    visible    timeout=${TIMEOUT}

Voltar Para Inventario
    [Documentation]    Clica em "Back to products" e aguarda o inventário carregar.
    Click    ${BTN_BACK}
    Wait For Elements State    .inventory_list    visible    timeout=${TIMEOUT}
