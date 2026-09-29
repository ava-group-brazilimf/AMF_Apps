*** Settings ***
Documentation     SauceDemo — Carrinho de Compras
...               Cenários: estado inicial, adicionar/remover itens, validação de preços,
...               botão Continue Shopping, navegação para checkout.
...               PBI-001 | FastQA | Robot Framework + Python | 14/05/2026
Library           Browser
Library           Collections
Resource          ../pages/CartPage.robot
Resource          ../pages/InventoryPage.robot
Resource          ../pages/HeaderPage.robot
Resource          ../config/variables.robot
Resource          ../config/auth_config.robot
Resource          ../support/auth.resource

Suite Setup       Autenticar Na Aplicacao
Test Setup        Preparar Carrinho
Suite Teardown    Close Browser    ALL

Force Tags        cart    feature-cart

*** Keywords ***
Preparar Carrinho
    [Documentation]    Reseta o estado da aplicação e navega para o inventário
    ...                antes de cada teste.
    Resetar Estado Da Aplicacao
    Navegar Para Inventario

*** Test Cases ***
# ===========================================================================
# CT-01 — Carrinho vazio exibe título "Your Cart" e lista sem itens
# ===========================================================================
CT-01 - Carrinho vazio exibe titulo Your Cart sem itens
    [Documentation]    Valida que acessar o carrinho sem adicionar produtos exibe
    ...                a lista de carrinho vazia e o título correto.
    [Tags]    smoke    ui    positive
    Navegar Para Carrinho Via Icone
    Verificar Titulo Do Carrinho
    Verificar Carrinho Vazio

# ===========================================================================
# CT-02 — Produto adicionado aparece no carrinho com nome e preço corretos
# ===========================================================================
CT-02 - Produto adicionado aparece no carrinho com nome e preco corretos
    [Documentation]    Valida que o Sauce Labs Backpack aparece no carrinho com
    ...                o preço $29.99 após ser adicionado no inventário.
    [Tags]    smoke    critical    positive
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Navegar Para Carrinho Via Icone
    Verificar Titulo Do Carrinho
    Verificar Quantidade De Itens No Carrinho    1
    Verificar Item Presente No Carrinho    ${PRODUCT_BACKPACK}
    Verificar Preco Do Item No Carrinho    ${PRODUCT_BACKPACK}    ${PRICE_BACKPACK}

# ===========================================================================
# CT-03 — Dois produtos adicionados aparecem ambos no carrinho
# ===========================================================================
CT-03 - Dois produtos adicionados aparecem no carrinho com quantidade 2
    [Documentation]    Valida que adicionar dois produtos distintos resulta em
    ...                dois itens no carrinho.
    [Tags]    regression    positive
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BIKE_LIGHT}
    Navegar Para Carrinho Via Icone
    Verificar Quantidade De Itens No Carrinho    2
    Verificar Item Presente No Carrinho    ${PRODUCT_BACKPACK}
    Verificar Item Presente No Carrinho    ${PRODUCT_BIKE_LIGHT}

# ===========================================================================
# CT-04 — Remover item do carrinho atualiza a lista corretamente
# ===========================================================================
CT-04 - Remover item do carrinho atualiza lista e badge
    [Documentation]    Valida que remover um produto do carrinho o remove da lista
    ...                e oculta o badge quando o carrinho fica vazio.
    [Tags]    smoke    critical    positive
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Navegar Para Carrinho Via Icone
    Verificar Quantidade De Itens No Carrinho    1
    Remover Item Do Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Verificar Carrinho Vazio
    Verificar Badge Ausente

# ===========================================================================
# CT-05 — Remover um de dois itens mantém o outro no carrinho
# ===========================================================================
CT-05 - Remover um de dois itens mantem o outro no carrinho
    [Documentation]    Valida que remover apenas um produto mantém o outro
    ...                no carrinho com badge "1".
    [Tags]    regression    positive
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BIKE_LIGHT}
    Navegar Para Carrinho Via Icone
    Remover Item Do Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Verificar Quantidade De Itens No Carrinho    1
    Verificar Item Ausente No Carrinho    ${PRODUCT_BACKPACK}
    Verificar Item Presente No Carrinho    ${PRODUCT_BIKE_LIGHT}
    Verificar Badge Do Carrinho    1

# ===========================================================================
# CT-06 — Cada item no carrinho exibe quantidade 1
# ===========================================================================
CT-06 - Cada item no carrinho exibe quantidade unitaria 1
    [Documentation]    Valida que a quantidade exibida ao lado de cada item é "1".
    [Tags]    regression    ui    positive
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Navegar Para Carrinho Via Icone
    Verificar Quantidade Do Item    ${PRODUCT_BACKPACK}    1

# ===========================================================================
# CT-07 — Continue Shopping retorna ao inventário
# ===========================================================================
CT-07 - Continue Shopping retorna ao inventario
    [Documentation]    Valida que clicar em "Continue Shopping" navega de volta
    ...                para a página de inventário.
    [Tags]    regression    ui    positive
    Navegar Para Carrinho Via Icone
    Clicar Em Continuar Comprando
    Wait For Elements State    ${INVENTORY_LIST}    visible    timeout=${TIMEOUT}
    Get Url    contains    /inventory.html

# ===========================================================================
# CT-08 — Botão Checkout redireciona para etapa de informações
# ===========================================================================
CT-08 - Botao Checkout redireciona para Checkout Your Information
    [Documentation]    Valida que clicar em "Checkout" com ao menos um produto
    ...                navega para a tela de informações de checkout.
    [Tags]    smoke    critical    positive    e2e
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Navegar Para Carrinho Via Icone
    Clicar Em Checkout
    Get Url    contains    /checkout-step-one.html
    Wait For Elements State    [data-test="firstName"]    visible    timeout=${TIMEOUT}
