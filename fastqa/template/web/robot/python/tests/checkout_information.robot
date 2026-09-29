*** Settings ***
Documentation     SauceDemo — Checkout: Your Information (Step 1)
...               Cenários: validação estrutural, campos obrigatórios, erros de validação,
...               preenchimento correto, botão Cancel retorna ao carrinho.
...               PBI-001 | FastQA | Robot Framework + Python | 14/05/2026
Library           Browser
Resource          ../pages/CheckoutInformationPage.robot
Resource          ../pages/InventoryPage.robot
Resource          ../pages/CartPage.robot
Resource          ../pages/HeaderPage.robot
Resource          ../config/variables.robot
Resource          ../config/auth_config.robot
Resource          ../support/auth.resource

Suite Setup       Autenticar Na Aplicacao
Test Setup        Preparar Checkout Step1
Suite Teardown    Close Browser    ALL

Force Tags        checkout    checkout-step1    feature-checkout

*** Keywords ***
Preparar Checkout Step1
    [Documentation]    Reseta estado, adiciona um produto ao carrinho e navega para checkout step 1.
    Resetar Estado Da Aplicacao
    Navegar Para Inventario
    Adicionar Produto Ao Carrinho Por Nome    ${PRODUCT_BACKPACK}
    Navegar Para Carrinho Via Icone
    Clicar Em Checkout

*** Test Cases ***
# ===========================================================================
# CT-01 — Título da página é "Checkout: Your Information"
# ===========================================================================
CT-01 - Pagina exibe titulo Checkout Your Information
    [Documentation]    Valida que a página de checkout step 1 exibe o título correto.
    [Tags]    smoke    ui    positive
    Verificar Titulo Do Checkout Info

# ===========================================================================
# CT-02 — Todos os campos e botões obrigatórios estão presentes
# ===========================================================================
CT-02 - Formulario exibe campos First Name Last Name Postal Code e botoes
    [Documentation]    Valida que os campos de First Name, Last Name, Postal Code,
    ...                botões Continue e Cancel estão visíveis.
    [Tags]    smoke    ui    positive
    Verificar Campos Do Formulario Presentes

# ===========================================================================
# CT-03 — Submeter formulário vazio exibe erro de First Name obrigatório
# ===========================================================================
CT-03 - Submeter formulario vazio exibe erro First Name is required
    [Documentation]    Valida que clicar em Continue sem preencher nenhum campo
    ...                exibe a mensagem "Error: First Name is required".
    [Tags]    regression    negative    validation
    Clicar Em Continue
    Verificar Mensagem De Erro    First Name is required

# ===========================================================================
# CT-04 — Submeter sem Last Name exibe erro de Last Name obrigatório
# ===========================================================================
CT-04 - Submeter sem Last Name exibe erro Last Name is required
    [Documentation]    Valida que preencher apenas First Name e tentar continuar
    ...                exibe a mensagem "Error: Last Name is required".
    [Tags]    regression    negative    validation
    Fill Text    ${INPUT_FIRST_NAME}    Test
    Clicar Em Continue
    Verificar Mensagem De Erro    Last Name is required

# ===========================================================================
# CT-05 — Submeter sem Postal Code exibe erro de Postal Code obrigatório
# ===========================================================================
CT-05 - Submeter sem Postal Code exibe erro Postal Code is required
    [Documentation]    Valida que preencher First Name e Last Name mas não o CEP
    ...                exibe a mensagem "Error: Postal Code is required".
    [Tags]    regression    negative    validation
    Fill Text    ${INPUT_FIRST_NAME}    Test
    Fill Text    ${INPUT_LAST_NAME}     User
    Clicar Em Continue
    Verificar Mensagem De Erro    Postal Code is required

# ===========================================================================
# CT-06 — Preencher todos os campos e clicar Continue avança para Overview
# ===========================================================================
CT-06 - Preencher todos os campos avanca para Checkout Overview
    [Documentation]    Valida que preencher First Name, Last Name e Postal Code
    ...                e clicar em Continue navega para a página de visão geral.
    [Tags]    smoke    critical    positive    e2e
    Preencher E Continuar
    Get Url    contains    /checkout-step-two.html
    Wait For Elements State    .summary_info    visible    timeout=${TIMEOUT}

# ===========================================================================
# CT-07 — Botão Cancel retorna ao carrinho
# ===========================================================================
CT-07 - Botao Cancel retorna ao carrinho
    [Documentation]    Valida que clicar em Cancel na tela de informações
    ...                navega de volta para o carrinho.
    [Tags]    regression    ui    positive
    Clicar Em Cancel No Checkout Info
    Get Url    contains    /cart.html
    Wait For Elements State    ${CART_LIST}    visible    timeout=${TIMEOUT}
