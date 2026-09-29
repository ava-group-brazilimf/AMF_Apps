*** Settings ***
Documentation    Page Object — Inventory Page (Catálogo de Produtos — SauceDemo)
...              URL: https://www.saucedemo.com/inventory.html
...              Locators validados via inspeção DOM real (Playwright MCP) — 14/05/2026
Library          Browser
Library          Collections
Resource         ../config/variables.robot
Resource         HeaderPage.robot

*** Variables ***
# ===========================================================================
# URL
# ===========================================================================
${URL_INVENTORY}              ${BASE_URL}${ROUTE_INVENTORY}

# ===========================================================================
# Estrutura da página
# ===========================================================================
${PAGE_TITLE}                 .title
${INVENTORY_LIST}             .inventory_list
${INVENTORY_ITEMS}            .inventory_item

# ===========================================================================
# Elementos de cada item do inventário
# ===========================================================================
${ITEM_NAME}                  .inventory_item_name
${ITEM_DESC}                  .inventory_item_desc
${ITEM_PRICE}                 .inventory_item_price
${ITEM_IMG_CONTAINER}         .inventory_item_img

# ===========================================================================
# Botões de ação dos produtos
# data-test segue padrão: "add-to-cart-{slug}" / "remove-{slug}"
# Slug = nome em lowercase com espaços → hífens (ex: "sauce-labs-backpack")
# ===========================================================================
${BTN_ADD_TO_CART_ANY}        [data-test^="add-to-cart"]
${BTN_REMOVE_ANY}             [data-test^="remove-"]

# ===========================================================================
# Ordenação (Sort dropdown)
# ===========================================================================
${SORT_DROPDOWN}              [data-test="product-sort-container"]

*** Keywords ***
# ===========================================================================
# Navegação
# ===========================================================================
Navegar Para Inventario
    [Documentation]    Navega para a página de inventário e aguarda a lista de produtos.
    Go To    ${URL_INVENTORY}
    Wait For Elements State    ${INVENTORY_LIST}    visible    timeout=${TIMEOUT}

# ===========================================================================
# Verificações estruturais
# ===========================================================================
Verificar Titulo Do Inventario
    [Documentation]    Valida que o título da página é "Products".
    Wait For Elements State    ${PAGE_TITLE}    visible    timeout=${TIMEOUT}
    Get Text    ${PAGE_TITLE}    ==    Products

Verificar Quantidade De Produtos
    [Documentation]    Valida que a lista de produtos exibe exatamente N itens.
    [Arguments]    ${quantidade}
    ${count}=    Get Element Count    ${INVENTORY_ITEMS}
    Should Be Equal As Integers    ${count}    ${quantidade}

Verificar Produto Presente
    [Documentation]    Valida que um produto com o nome especificado está visível.
    [Arguments]    ${nome_produto}
    Wait For Elements State    .inventory_item_name:has-text("${nome_produto}")    visible    timeout=${TIMEOUT}

# ===========================================================================
# Interação com produtos — Add/Remove por nome
# ===========================================================================
Converter Nome Para Slug
    [Documentation]    Converte nome do produto para o formato slug do data-test.
    ...                Ex: "Sauce Labs Backpack" → "sauce-labs-backpack"
    [Arguments]    ${nome}
    ${slug}=    Evaluate    "${nome}".lower().replace(" ", "-")
    RETURN    ${slug}

Adicionar Produto Ao Carrinho Por Nome
    [Documentation]    Clica no botão "Add to cart" do produto especificado.
    [Arguments]    ${nome_produto}
    ${slug}=    Converter Nome Para Slug    ${nome_produto}
    Click    [data-test="add-to-cart-${slug}"]
    Log    [Inventory] Produto adicionado: ${nome_produto} (slug: ${slug})    INFO

Remover Produto Do Carrinho Por Nome
    [Documentation]    Clica no botão "Remove" do produto especificado (na página de inventário).
    [Arguments]    ${nome_produto}
    ${slug}=    Converter Nome Para Slug    ${nome_produto}
    Click    [data-test="remove-${slug}"]
    Log    [Inventory] Produto removido: ${nome_produto} (slug: ${slug})    INFO

# ===========================================================================
# Ordenação
# ===========================================================================
Ordenar Por
    [Documentation]    Seleciona uma opção de ordenação no dropdown.
    ...                Opções: "Name (A to Z)" | "Name (Z to A)" | "Price (low to high)" | "Price (high to low)"
    [Arguments]    ${opcao}
    Select Options By    ${SORT_DROPDOWN}    label    ${opcao}
    Wait For Elements State    ${INVENTORY_LIST}    visible    timeout=${TIMEOUT}

# ===========================================================================
# Coleta de dados da listagem
# ===========================================================================
Obter Nomes Dos Produtos
    [Documentation]    Retorna lista com os nomes de todos os produtos exibidos.
    ${elementos}=    Get Elements    ${ITEM_NAME}
    ${nomes}=    Create List
    FOR    ${el}    IN    @{elementos}
        ${texto}=    Get Text    ${el}
        Append To List    ${nomes}    ${texto}
    END
    RETURN    ${nomes}

Obter Precos Dos Produtos
    [Documentation]    Retorna lista com os preços de todos os produtos (ex: ["$29.99", "$9.99"]).
    ${elementos}=    Get Elements    ${ITEM_PRICE}
    ${precos}=    Create List
    FOR    ${el}    IN    @{elementos}
        ${texto}=    Get Text    ${el}
        Append To List    ${precos}    ${texto}
    END
    RETURN    ${precos}

# ===========================================================================
# Navegação para outras páginas
# ===========================================================================
Navegar Para Carrinho
    [Documentation]    Clica no ícone do carrinho para navegar à página de carrinho.
    Click    .shopping_cart_link
    Wait For Elements State    .cart_list    visible    timeout=${TIMEOUT}

Clicar No Nome Do Produto
    [Documentation]    Clica no link com o nome do produto para abrir a página de detalhe.
    [Arguments]    ${nome_produto}
    Click    .inventory_item_name:has-text("${nome_produto}")
    Wait For Elements State    .inventory_details_name    visible    timeout=${TIMEOUT}

# ===========================================================================
# Reset de estado
# ===========================================================================
Resetar Estado Da Aplicacao
    [Documentation]    Usa o menu lateral "Reset App State" para limpar o estado da sessão.
    ...                Se o usuário não estiver autenticado (tela de login), retorna sem
    ...                tentar abrir o menu lateral (que não existe na tela de login).
    ${url}=    Get Url
    ${na_login}=    Evaluate    '/login' in '${url}' or '${url}'.rstrip('/') == '${BASE_URL}'
    IF    ${na_login}
        Log    [Reset] Usuário na tela de login — reset ignorado.    INFO
        RETURN
    END
    Resetar Estado Da Aplicacao Via Menu
    Navegar Para Inventario
