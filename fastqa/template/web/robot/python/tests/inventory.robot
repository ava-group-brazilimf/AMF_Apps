*** Settings ***
Documentation     SauceDemo — Inventário de Produtos
...               Cenários: estado inicial, contagem de produtos, add/remove, badge do carrinho,
...               ordenação, navegação para detalhe do produto.
...               PBI-001 | FastQA | Robot Framework + Python | 14/05/2026
Library           Browser
Library           Collections
Resource          ../pages/InventoryPage.robot
Resource          ../pages/HeaderPage.robot
Resource          ../config/variables.robot
Resource          ../config/auth_config.robot
Resource          ../support/auth.resource

Suite Setup       Autenticar Na Aplicacao
Test Setup        Preparar Inventario
Suite Teardown    Close Browser    ALL

Force Tags        inventory    feature-inventory

*** Keywords ***
Preparar Inventario
    [Documentation]    Garante estado limpo antes de cada teste: reseta o estado da aplicação
    ...                e navega para o inventário.
    Resetar Estado Da Aplicacao
    Navegar Para Inventario

*** Test Cases ***
# ===========================================================================
# CT-01 — Estado inicial exibe o inventário com título e 6 produtos
# ===========================================================================
CT-01 - Estado inicial exibe titulo Products e lista com 6 produtos
    [Documentation]    Valida que após o login a página de inventário exibe o título
    ...                "Products" e os 6 produtos disponíveis no catálogo.
    [Tags]    smoke    critical    ui    positive
    Verificar Titulo Do Inventario
    Verificar Quantidade De Produtos    ${TOTAL_PRODUCTS}

# ===========================================================================
# CT-02 — Todos os produtos esperados estão presentes no catálogo
# ===========================================================================
CT-02 - Catalogo exibe todos os 6 produtos do SauceDemo
    [Documentation]    Valida que todos os 6 produtos conhecidos do SauceDemo
    ...                estão presentes na listagem.
    [Tags]    smoke    regression    ui    positive
    Verificar Produto Presente    ${PRODUCT_BACKPACK}
    Verificar Produto Presente    ${PRODUCT_BIKE_LIGHT}
    Verificar Produto Presente    ${PRODUCT_BOLT_SHIRT}
    Verificar Produto Presente    ${PRODUCT_FLEECE_JACKET}
    Verificar Produto Presente    ${PRODUCT_ONESIE}
    Verificar Produto Presente    ${PRODUCT_RED_SHIRT}

# ===========================================================================
# CT-03 — Adicionar produto ao carrinho atualiza badge para 1
# ===========================================================================
CT-03 - Adicionar produto ao carrinho atualiza badge para 1
    [Documentation]    Valida que adicionar um produto ao carrinho exibe badge "1" no ícone.
    [Tags]    smoke    critical    cart    positive
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Verificar Badge Do Carrinho    1

# ===========================================================================
# CT-04 — Adicionar dois produtos atualiza badge para 2
# ===========================================================================
CT-04 - Adicionar dois produtos atualiza badge para 2
    [Documentation]    Valida que adicionar dois produtos distintos exibe badge "2".
    [Tags]    regression    cart    positive
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BIKE_LIGHT}
    Verificar Badge Do Carrinho    2

# ===========================================================================
# CT-05 — Remover produto do carrinho (via inventário) remove o badge
# ===========================================================================
CT-05 - Remover produto adicionado oculta badge do carrinho
    [Documentation]    Valida que remover o único produto do carrinho oculta o badge.
    [Tags]    regression    cart    positive
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Verificar Badge Do Carrinho    1
    Remover Produto Do Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Verificar Badge Ausente

# ===========================================================================
# CT-06 — Botão muda de "Add to cart" para "Remove" após adição
# ===========================================================================
CT-06 - Botao muda para Remove apos adicionar produto ao carrinho
    [Documentation]    Valida que o botão do produto muda de estado após a adição.
    [Tags]    regression    ui    positive
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    ${slug}=    Converter Nome Para Slug    ${PRODUCT_BACKPACK}
    Wait For Elements State    [data-test="remove-${slug}"]    visible    timeout=${TIMEOUT}
    Wait For Elements State    [data-test="add-to-cart-${slug}"]    hidden    timeout=${TIMEOUT}

# ===========================================================================
# CT-07 — Ordenação por Nome A→Z mantém ordem alfabética
# ===========================================================================
CT-07 - Ordenacao por Nome A-Z exibe produtos em ordem alfabetica
    [Documentation]    Valida que a ordenação "Name (A to Z)" retorna produtos em ordem alfabética.
    [Tags]    regression    filter    positive
    Ordenar Por    Name (A to Z)
    ${nomes}=    Obter Nomes Dos Produtos
    ${nomes_ordenados}=    Evaluate    sorted(${nomes})
    Lists Should Be Equal    ${nomes}    ${nomes_ordenados}

# ===========================================================================
# CT-08 — Ordenação por Preço Low→High lista o mais barato primeiro
# ===========================================================================
CT-08 - Ordenacao por preco crescente coloca Onesie como primeiro produto
    [Documentation]    Valida que ordenar por "Price (low to high)" coloca o produto mais
    ...                barato (Sauce Labs Onesie - $7.99) como primeiro.
    [Tags]    regression    filter    positive
    Ordenar Por    Price (low to high)
    ${nomes}=    Obter Nomes Dos Produtos
    Should Be Equal    ${nomes}[0]    ${PRODUCT_ONESIE}

# ===========================================================================
# CT-09 — Clicar no nome do produto abre a página de detalhe
# ===========================================================================
CT-09 - Clicar no nome do produto abre pagina de detalhe
    [Documentation]    Valida que clicar no nome de um produto navega para
    ...                a página de detalhe com os dados corretos.
    [Tags]    regression    ui    positive
    Clicar No Nome Do Produto    ${PRODUCT_BACKPACK}
    Wait For Elements State    .inventory_details_name    visible    timeout=${TIMEOUT}
    Get Text    .inventory_details_name    contains    Backpack

# ===========================================================================
# CT-10 — Logo "Swag Labs" está visível no cabeçalho do inventário
# ===========================================================================
CT-10 - Cabecalho exibe logo Swag Labs e icone do carrinho
    [Documentation]    Valida que o cabeçalho compartilhado exibe o logo e o ícone do carrinho.
    [Tags]    smoke    ui    positive
    Verificar Logo Da Aplicacao
    Wait For Elements State    ${CART_ICON}    visible    timeout=${TIMEOUT}
