*** Settings ***
Documentation    Page Object — Cart Page (Carrinho de Compras — SauceDemo)
...              URL: https://www.saucedemo.com/cart.html
...              Locators validados via inspeção DOM real (Playwright MCP) — 14/05/2026
Library          Browser
Library          Collections
Resource         ../config/variables.robot
Resource         HeaderPage.robot

*** Variables ***
# ===========================================================================
# URL
# ===========================================================================
${URL_CART}                   ${BASE_URL}${ROUTE_CART}

# ===========================================================================
# Estrutura da página
# ===========================================================================
${PAGE_TITLE}                 .title
${CART_LIST}                  .cart_list
${CART_ITEMS}                 .cart_item
${CART_ITEM_NAME}             .inventory_item_name
${CART_ITEM_DESC}             .inventory_item_desc
${CART_ITEM_PRICE}            .inventory_item_price
${CART_ITEM_QTY}              .cart_quantity
${LABEL_QTY}                  .cart_quantity_label
${LABEL_DESC}                 .cart_desc_label

# ===========================================================================
# Botões de ação
# ===========================================================================
${BTN_CONTINUE_SHOPPING}      [data-test="continue-shopping"]
${BTN_CHECKOUT}               [data-test="checkout"]
${BTN_REMOVE_ANY}             [data-test^="remove-"]

*** Keywords ***
# ===========================================================================
# Navegação
# ===========================================================================
Navegar Para Carrinho
    [Documentation]    Navega diretamente para a página do carrinho.
    Go To    ${URL_CART}
    Wait For Elements State    ${CART_LIST}    visible    timeout=${TIMEOUT}

# ===========================================================================
# Verificações
# ===========================================================================
Verificar Titulo Do Carrinho
    [Documentation]    Valida que o título da página é "Your Cart".
    Wait For Elements State    ${PAGE_TITLE}    visible    timeout=${TIMEOUT}
    Get Text    ${PAGE_TITLE}    ==    Your Cart

Verificar Quantidade De Itens No Carrinho
    [Documentation]    Valida que o carrinho exibe exatamente N itens.
    [Arguments]    ${quantidade_esperada}
    ${count}=    Get Element Count    ${CART_ITEMS}
    Should Be Equal As Integers    ${count}    ${quantidade_esperada}

Verificar Item Presente No Carrinho
    [Documentation]    Valida que um item com o nome especificado está no carrinho.
    [Arguments]    ${nome_produto}
    Wait For Elements State    .cart_item:has-text("${nome_produto}")    visible    timeout=${TIMEOUT}

Verificar Item Ausente No Carrinho
    [Documentation]    Valida que um item com o nome especificado NÃO está no carrinho.
    [Arguments]    ${nome_produto}
    Wait For Elements State    .cart_item:has-text("${nome_produto}")    hidden    timeout=${TIMEOUT}

Verificar Carrinho Vazio
    [Documentation]    Valida que não há nenhum item no carrinho.
    ${count}=    Get Element Count    ${CART_ITEMS}
    Should Be Equal As Integers    ${count}    0

Verificar Quantidade Do Item
    [Documentation]    Valida que a quantidade de um item no carrinho é a esperada.
    [Arguments]    ${nome_produto}    ${quantidade_esperada}
    ${qty}=    Get Text    .cart_item:has-text("${nome_produto}") .cart_quantity
    Should Be Equal    ${qty}    ${quantidade_esperada}

Verificar Preco Do Item No Carrinho
    [Documentation]    Valida o preço exibido para um item no carrinho.
    [Arguments]    ${nome_produto}    ${preco_esperado}
    ${preco}=    Get Text    .cart_item:has-text("${nome_produto}") .inventory_item_price
    Should Be Equal    ${preco}    ${preco_esperado}

# ===========================================================================
# Interações
# ===========================================================================
Remover Item Do Carrinho Por Nome
    [Documentation]    Clica no botão "Remove" do item especificado no carrinho.
    [Arguments]    ${nome_produto}
    ${slug}=    Evaluate    "${nome_produto}".lower().replace(" ", "-")
    Click    [data-test="remove-${slug}"]
    Log    [Cart] Item removido: ${nome_produto}    INFO

Clicar Em Continuar Comprando
    [Documentation]    Clica em "Continue Shopping" e aguarda o inventário carregar.
    Click    ${BTN_CONTINUE_SHOPPING}
    Wait For Elements State    .inventory_list    visible    timeout=${TIMEOUT}

Clicar Em Checkout
    [Documentation]    Clica em "Checkout" e aguarda a página de informações carregar.
    Click    ${BTN_CHECKOUT}
    Wait For Elements State    [data-test="firstName"]    visible    timeout=${TIMEOUT}
