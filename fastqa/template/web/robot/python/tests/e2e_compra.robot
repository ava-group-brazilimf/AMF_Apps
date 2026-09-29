*** Settings ***
Documentation     SauceDemo — Fluxo E2E Completo de Compra
...               Cobre o checklist completo do PBI-001: login → inventário → carrinho
...               → checkout information → checkout overview → checkout complete → logout.
...               PBI-001 | FastQA | Robot Framework + Python | 14/05/2026
Library           Browser
Resource          ../pages/LoginPage.robot
Resource          ../pages/InventoryPage.robot
Resource          ../pages/CartPage.robot
Resource          ../pages/CheckoutInformationPage.robot
Resource          ../pages/CheckoutOverviewPage.robot
Resource          ../pages/CheckoutCompletePage.robot
Resource          ../pages/HeaderPage.robot
Resource          ../config/variables.robot
Resource          ../config/auth_config.robot
Resource          ../support/auth.resource

Suite Setup       Autenticar Na Aplicacao
Test Setup        Resetar Estado Da Aplicacao
Suite Teardown    Close Browser    ALL

Force Tags        e2e    jornada    feature-e2e-compra

*** Test Cases ***
# ===========================================================================
# CT-01 — Fluxo E2E completo: login → 1 produto → checkout → confirmação
# ===========================================================================
CT-01 - Fluxo E2E completo de compra com um produto
    [Documentation]    Valida o fluxo completo de compra do PBI-001:
    ...                1. Acesso ao inventário após login
    ...                2. Produto adicionado ao carrinho com badge correto
    ...                3. Navegação para o carrinho e validação
    ...                4. Checkout: preenchimento de dados pessoais
    ...                5. Checkout Overview: validação de itens e preços
    ...                6. Finalização com mensagem de sucesso
    [Tags]    smoke    critical    e2e    jornada    positive

    # — Etapa 1: Inventário —
    Navegar Para Inventario
    Verificar Titulo Do Inventario
    Verificar Produto Presente    ${PRODUCT_BACKPACK}

    # — Etapa 2: Adicionar produto ao carrinho —
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Verificar Badge Do Carrinho    1

    # — Etapa 3: Carrinho —
    Navegar Para Carrinho Via Icone
    Verificar Titulo Do Carrinho
    Verificar Item Presente No Carrinho    ${PRODUCT_BACKPACK}
    Verificar Preco Do Item No Carrinho    ${PRODUCT_BACKPACK}    ${PRICE_BACKPACK}
    Verificar Quantidade Do Item    ${PRODUCT_BACKPACK}    1

    # — Etapa 4: Checkout Step 1 —
    Clicar Em Checkout
    Verificar Titulo Do Checkout Info
    Verificar Campos Do Formulario Presentes
    Preencher E Continuar

    # — Etapa 5: Checkout Step 2 — Overview —
    Verificar Titulo Do Checkout Overview
    Verificar Quantidade De Itens No Resumo    1
    Verificar Item No Resumo    ${PRODUCT_BACKPACK}
    Verificar Informacoes De Pedido Presentes
    ${subtotal}=    Obter Subtotal
    Should Contain    ${subtotal}    ${PRICE_BACKPACK}

    # — Etapa 6: Finalizar compra —
    Clicar Em Finish
    Verificar Pagina De Confirmacao Completa

# ===========================================================================
# CT-02 — Fluxo E2E com dois produtos: soma de preços no overview
# ===========================================================================
CT-02 - Fluxo E2E com dois produtos valida subtotal correto
    [Documentation]    Adiciona Backpack ($29.99) + Bike Light ($9.99),
    ...                valida subtotal $39.98 e conclui a compra com sucesso.
    [Tags]    regression    e2e    positive

    Navegar Para Inventario
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BIKE_LIGHT}
    Verificar Badge Do Carrinho    2

    Navegar Para Carrinho Via Icone
    Verificar Quantidade De Itens No Carrinho    2
    Clicar Em Checkout

    Preencher E Continuar
    Verificar Quantidade De Itens No Resumo    2
    ${subtotal}=    Obter Subtotal
    Should Contain    ${subtotal}    39.98

    Clicar Em Finish
    Verificar Mensagem De Confirmacao

# ===========================================================================
# CT-03 — Remover produto do carrinho antes do checkout
# ===========================================================================
CT-03 - Remover produto do carrinho antes do checkout e prosseguir com outro
    [Documentation]    Adiciona dois produtos, remove um no carrinho,
    ...                conclui a compra apenas com o produto restante.
    [Tags]    regression    e2e    positive

    Navegar Para Inventario
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BIKE_LIGHT}
    Navegar Para Carrinho Via Icone
    Remover Item Do Carrinho Por Nome    ${PRODUCT_BACKPACK}

    Verificar Quantidade De Itens No Carrinho    1
    Verificar Item Ausente No Carrinho    ${PRODUCT_BACKPACK}
    Verificar Item Presente No Carrinho    ${PRODUCT_BIKE_LIGHT}
    Verificar Badge Do Carrinho    1

    Clicar Em Checkout
    Preencher E Continuar
    Verificar Quantidade De Itens No Resumo    1
    Verificar Item No Resumo    ${PRODUCT_BIKE_LIGHT}
    Clicar Em Finish
    Verificar Mensagem De Confirmacao

# ===========================================================================
# CT-04 — Botão "Back Home" retorna ao inventário após a compra
# ===========================================================================
CT-04 - Back Home retorna ao inventario apos confirmacao da compra
    [Documentation]    Após concluir a compra, valida que clicar em "Back Home"
    ...                retorna ao inventário.
    [Tags]    regression    e2e    positive

    Navegar Para Inventario
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_ONESIE}
    Navegar Para Carrinho Via Icone
    Clicar Em Checkout
    Preencher E Continuar
    Clicar Em Finish
    Verificar Mensagem De Confirmacao
    Clicar Em Back Home
    Wait For Elements State    ${INVENTORY_LIST}    visible    timeout=${TIMEOUT}
    Get Url    contains    /inventory.html

# ===========================================================================
# CT-05 — Logout encerra sessão e impede acesso direto ao inventário
# ===========================================================================
CT-05 - Logout encerra sessao e impede acesso direto ao inventario
    [Documentation]    Valida que após o logout o usuário é redirecionado para o login
    ...                e tentativa de acesso direto ao inventário redireciona para o login.
    [Tags]    regression    e2e    security    positive

    Navegar Para Inventario
    Realizar Logout Via Menu
    Wait For Elements State    id=user-name    visible    timeout=${TIMEOUT}
    Get Url    ==    ${BASE_URL}${ROUTE_LOGIN}

    # Tenta acessar diretamente o inventário sem autenticação
    Go To    ${BASE_URL}${ROUTE_INVENTORY}
    Wait For Elements State    id=user-name    visible    timeout=${TIMEOUT}
    Get Url    ==    ${BASE_URL}${ROUTE_LOGIN}

# ===========================================================================
# CT-06 — Fluxo E2E com todos os 6 produtos do catálogo
# ===========================================================================
CT-06 - Adicionar todos os 6 produtos e concluir compra com badge 6
    [Documentation]    Adiciona todos os 6 produtos disponíveis no SauceDemo,
    ...                valida badge "6", e conclui a compra com sucesso.
    ...                Usa [Setup] próprio pois CT-05 realiza logout, exigindo re-autenticação.
    [Tags]    regression    e2e    positive
    [Setup]    Autenticar Na Aplicacao

    Navegar Para Inventario
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BIKE_LIGHT}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BOLT_SHIRT}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_FLEECE_JACKET}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_ONESIE}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_RED_SHIRT}
    Verificar Badge Do Carrinho    6

    Navegar Para Carrinho Via Icone
    Verificar Quantidade De Itens No Carrinho    6
    Clicar Em Checkout
    Preencher E Continuar
    Verificar Quantidade De Itens No Resumo    6
    Clicar Em Finish
    Verificar Pagina De Confirmacao Completa
