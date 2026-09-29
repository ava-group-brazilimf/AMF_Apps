*** Settings ***
Documentation     SauceDemo — Checkout: Overview (Step 2)
...               Cenários: validação estrutural, itens no resumo, informações de pagamento
...               e envio, subtotal/total, botão Finish e botão Cancel.
...               PBI-001 | FastQA | Robot Framework + Python | 14/05/2026
Library           Browser
Resource          ../pages/CheckoutOverviewPage.robot
Resource          ../pages/CheckoutInformationPage.robot
Resource          ../pages/InventoryPage.robot
Resource          ../pages/CartPage.robot
Resource          ../pages/HeaderPage.robot
Resource          ../config/variables.robot
Resource          ../config/auth_config.robot
Resource          ../support/auth.resource

Suite Setup       Autenticar Na Aplicacao
Test Setup        Preparar Checkout Step2
Suite Teardown    Close Browser    ALL

Force Tags        checkout    checkout-step2    feature-checkout

*** Keywords ***
Preparar Checkout Step2
    [Documentation]    Reseta estado, adiciona um produto, faz checkout step 1
    ...                e avança para o step 2 (Overview).
    Resetar Estado Da Aplicacao
    Navegar Para Inventario
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Navegar Para Carrinho Via Icone
    Clicar Em Checkout
    Preencher E Continuar

*** Test Cases ***
# ===========================================================================
# CT-01 — Título da página é "Checkout: Overview"
# ===========================================================================
CT-01 - Pagina exibe titulo Checkout Overview
    [Documentation]    Valida que a página de overview exibe o título correto.
    [Tags]    smoke    ui    positive
    Verificar Titulo Do Checkout Overview

# ===========================================================================
# CT-02 — O produto adicionado aparece no resumo do pedido
# ===========================================================================
CT-02 - Produto adicionado aparece no resumo do pedido
    [Documentation]    Valida que o Sauce Labs Backpack aparece nos itens do overview.
    [Tags]    smoke    critical    positive
    Verificar Quantidade De Itens No Resumo    1
    Verificar Item No Resumo    ${PRODUCT_BACKPACK}

# ===========================================================================
# CT-03 — Seções de Payment Information e Shipping Information estão presentes
# ===========================================================================
CT-03 - Secoes de pagamento e envio estao visiveis no resumo
    [Documentation]    Valida que as seções "Payment Information" e "Shipping Information"
    ...                estão presentes no resumo do pedido.
    [Tags]    smoke    ui    positive
    Verificar Secao De Pagamento Presente
    Verificar Secao De Envio Presente

# ===========================================================================
# CT-04 — Subtotal, imposto e total estão todos visíveis
# ===========================================================================
CT-04 - Subtotal imposto e total estao visiveis no resumo do pedido
    [Documentation]    Valida que as informações de preço (subtotal, tax, total) estão presentes.
    [Tags]    smoke    critical    positive
    Verificar Informacoes De Pedido Presentes

# ===========================================================================
# CT-05 — Subtotal corresponde ao preço do produto adicionado
# ===========================================================================
CT-05 - Subtotal corresponde ao preco do produto adicionado
    [Documentation]    Valida que o subtotal exibido contém o preço esperado do Backpack ($29.99).
    [Tags]    regression    positive
    ${subtotal}=    Obter Subtotal
    Should Contain    ${subtotal}    ${PRICE_BACKPACK}

# ===========================================================================
# CT-06 — Dois produtos: subtotal corresponde à soma dos dois preços
# ===========================================================================
CT-06 - Dois produtos no resumo exibem subtotal correto com dois itens
    [Documentation]    Adiciona Backpack ($29.99) e Bike Light ($9.99) → subtotal = $39.98.
    [Tags]    regression    positive
    # Reseta e adiciona dois produtos para este teste específico
    Resetar Estado Da Aplicacao
    Navegar Para Inventario
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BIKE_LIGHT}
    Navegar Para Carrinho Via Icone
    Clicar Em Checkout
    Preencher E Continuar
    Verificar Quantidade De Itens No Resumo    2
    ${subtotal}=    Obter Subtotal
    Should Contain    ${subtotal}    39.98

# ===========================================================================
# CT-07 — Botão Finish conclui a compra e exibe tela de confirmação
# ===========================================================================
CT-07 - Botao Finish conclui a compra com sucesso
    [Documentation]    Valida que clicar em Finish navega para a tela de confirmação
    ...                "Checkout: Complete!".
    [Tags]    smoke    critical    positive    e2e
    Clicar Em Finish
    Get Url    contains    /checkout-complete.html
    Wait For Elements State    .complete-header    visible    timeout=${TIMEOUT}

# ===========================================================================
# CT-08 — Botão Cancel retorna ao inventário sem finalizar a compra
# ===========================================================================
CT-08 - Botao Cancel no overview retorna ao inventario
    [Documentation]    Valida que clicar em Cancel na overview retorna ao inventário
    ...                sem concluir a compra.
    [Tags]    regression    ui    positive
    Clicar Em Cancel No Overview
    Get Url    contains    /inventory.html
    Wait For Elements State    ${INVENTORY_LIST}    visible    timeout=${TIMEOUT}
