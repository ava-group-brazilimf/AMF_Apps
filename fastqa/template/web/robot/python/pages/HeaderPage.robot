*** Settings ***
Documentation    Page Object — Header (Componente compartilhado — SauceDemo)
...              Presente em todas as páginas autenticadas: inventário, carrinho, checkout.
...              Locators validados via inspeção DOM real (Playwright MCP) — 14/05/2026
Library          Browser
Resource         ../config/variables.robot

*** Variables ***
# ===========================================================================
# Logo / Cabeçalho
# ===========================================================================
${APP_LOGO}                   .app_logo

# ===========================================================================
# Ícone do carrinho e badge de quantidade
# ===========================================================================
${CART_ICON}                  .shopping_cart_link
${CART_BADGE}                 .shopping_cart_badge

# ===========================================================================
# Menu Lateral (Burger Menu)
# ===========================================================================
${BURGER_MENU_BTN}            id=react-burger-menu-btn
${BURGER_MENU_CLOSE}          id=react-burger-cross-btn
${SIDEBAR_MENU}               .bm-menu-wrap
${MENU_ALL_ITEMS}             id=inventory_sidebar_link
${MENU_ABOUT}                 id=about_sidebar_link
${MENU_LOGOUT}                id=logout_sidebar_link
${MENU_RESET}                 id=reset_sidebar_link

*** Keywords ***
# ===========================================================================
# Logo
# ===========================================================================
Verificar Logo Da Aplicacao
    [Documentation]    Valida que o logo "Swag Labs" está visível no cabeçalho.
    Wait For Elements State    ${APP_LOGO}    visible    timeout=${TIMEOUT}
    Get Text    ${APP_LOGO}    ==    Swag Labs

# ===========================================================================
# Carrinho
# ===========================================================================
Verificar Badge Do Carrinho
    [Documentation]    Valida que o badge do carrinho exibe a quantidade esperada.
    [Arguments]    ${quantidade_esperada}
    Wait For Elements State    ${CART_BADGE}    visible    timeout=${TIMEOUT}
    Get Text    ${CART_BADGE}    ==    ${quantidade_esperada}

Verificar Badge Ausente
    [Documentation]    Valida que o badge do carrinho não está visível (carrinho vazio).
    Wait For Elements State    ${CART_BADGE}    hidden    timeout=${TIMEOUT}

Navegar Para Carrinho Via Icone
    [Documentation]    Clica no ícone do carrinho e aguarda a página de carrinho carregar.
    Click    ${CART_ICON}
    Wait For Elements State    .cart_list    visible    timeout=${TIMEOUT}

# ===========================================================================
# Menu Lateral
# ===========================================================================
Abrir Menu Lateral
    [Documentation]    Clica no ícone de hamburguer e aguarda o menu estar totalmente aberto.
    ...                Aguarda aria-hidden="true" (menu fechado) antes de clicar para evitar
    ...                toggle acidental durante animação de fechamento de teste anterior.
    Wait For Elements State    css=.bm-menu-wrap[aria-hidden="true"]    attached    timeout=${TIMEOUT}
    Click    ${BURGER_MENU_BTN}
    Wait For Elements State    css=.bm-menu-wrap[aria-hidden="false"]    attached    timeout=${TIMEOUT}
    Wait For Elements State    ${MENU_LOGOUT}    visible    timeout=${TIMEOUT}

Fechar Menu Lateral
    [Documentation]    Fecha o menu lateral e aguarda o fechamento completo (aria-hidden="true")
    ...                antes de retornar, evitando race condition no próximo open.
    Click    ${BURGER_MENU_CLOSE}
    Wait For Elements State    css=.bm-menu-wrap[aria-hidden="true"]    attached    timeout=${TIMEOUT}
    Wait For Elements State    ${BURGER_MENU_BTN}    visible    timeout=${TIMEOUT}

Verificar Links Do Menu Lateral
    [Documentation]    Valida que todos os links do menu lateral estão presentes.
    Abrir Menu Lateral
    Wait For Elements State    ${MENU_ALL_ITEMS}    visible    timeout=${TIMEOUT}
    Wait For Elements State    ${MENU_ABOUT}        visible    timeout=${TIMEOUT}
    Wait For Elements State    ${MENU_LOGOUT}       visible    timeout=${TIMEOUT}
    Wait For Elements State    ${MENU_RESET}        visible    timeout=${TIMEOUT}
    Fechar Menu Lateral

Realizar Logout Via Menu
    [Documentation]    Abre o menu lateral, clica em Logout e valida retorno à tela de login.
    Abrir Menu Lateral
    Click    ${MENU_LOGOUT}
    Wait For Elements State    id=user-name    visible    timeout=${TIMEOUT}

Resetar Estado Da Aplicacao Via Menu
    [Documentation]    Usa "Reset App State" do menu lateral para limpar carrinho e estado.
    Abrir Menu Lateral
    Click    ${MENU_RESET}
    Fechar Menu Lateral
