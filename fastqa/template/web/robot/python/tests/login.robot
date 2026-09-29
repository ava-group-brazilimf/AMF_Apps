*** Settings ***
Documentation     SauceDemo — Login
...               Cenários: login bem-sucedido, usuário bloqueado, credenciais inválidas, campos obrigatórios.
...               PBI-001 | FastQA | Robot Framework + Python | 14/05/2026
Library           Browser
Resource          ../pages/LoginPage.robot
Resource          ../config/variables.robot
Resource          ../config/auth_config.robot

Suite Setup       Abrir Browser Para Login
Suite Teardown    Close Browser    ALL

*** Keywords ***
Abrir Browser Para Login
    [Documentation]    Abre o browser sem autenticar — os testes de login controlam as credenciais.
    New Browser    browser=${BROWSER}    headless=${HEADLESS}
    New Context    viewport={'width': 1366, 'height': 768}
    New Page       ${BASE_URL}${ROUTE_LOGIN}

*** Test Cases ***
# ===========================================================================
# CT-01 — Login bem-sucedido redireciona para inventário
# ===========================================================================
CT-01 - Login valido com standard_user redireciona para inventario
    [Documentation]    Valida que o login com standard_user e secret_sauce exibe o inventário.
    [Tags]    login    smoke    critical    positive    e2e
    Navegar Para Pagina De Login
    Preencher Credenciais    standard_user    secret_sauce
    Clicar Em Login
    Wait For Elements State    .inventory_list    visible    timeout=${TIMEOUT}
    Get Url    ==    ${BASE_URL}${ROUTE_INVENTORY}

# ===========================================================================
# CT-02 — Usuário bloqueado recebe mensagem de erro específica
# ===========================================================================
CT-02 - Login com locked_out_user exibe mensagem de usuario bloqueado
    [Documentation]    Valida que locked_out_user recebe a mensagem de bloqueio.
    [Tags]    login    negative    regression
    Navegar Para Pagina De Login
    Preencher Credenciais    locked_out_user    secret_sauce
    Clicar Em Login
    Verificar Mensagem De Erro    ${AUTH_ERR_LOCKED}

# ===========================================================================
# CT-03 — Senha incorreta exibe mensagem de credencial inválida
# ===========================================================================
CT-03 - Login com senha incorreta exibe mensagem de credenciais invalidas
    [Documentation]    Valida que credenciais incorretas exibem mensagem de erro adequada.
    [Tags]    login    negative    validation
    Navegar Para Pagina De Login
    Preencher Credenciais    standard_user    senha_errada
    Clicar Em Login
    Verificar Mensagem De Erro    ${AUTH_ERR_INVALID_CREDS}

# ===========================================================================
# CT-04 — Login sem usuário exibe campo obrigatório
# ===========================================================================
CT-04 - Login sem usuario exibe mensagem de campo obrigatorio
    [Documentation]    Valida que submeter o formulário sem usuário exibe erro de campo obrigatório.
    [Tags]    login    negative    validation
    Navegar Para Pagina De Login
    Clicar Em Login
    Verificar Mensagem De Erro    ${AUTH_ERR_NO_USERNAME}

# ===========================================================================
# CT-05 — Login sem senha exibe campo obrigatório
# ===========================================================================
CT-05 - Login sem senha exibe mensagem de campo obrigatorio
    [Documentation]    Valida que submeter com usuário mas sem senha exibe erro de campo obrigatório.
    [Tags]    login    negative    validation
    Navegar Para Pagina De Login
    Preencher Credenciais    standard_user    ${EMPTY}
    Clicar Em Login
    Verificar Mensagem De Erro    ${AUTH_ERR_NO_PASSWORD}

# ===========================================================================
# CT-06 — Página de login exibe elementos estruturais
# ===========================================================================
CT-06 - Pagina de login exibe logo e todos os elementos estruturais
    [Documentation]    Valida que a tela de login exibe logo, campos, botão e lista de usuários.
    [Tags]    login    smoke    ui    positive
    Navegar Para Pagina De Login
    Verificar Elementos Estruturais Presentes

# ===========================================================================
# CT-07 — Fechar mensagem de erro oculta o alerta
# ===========================================================================
CT-07 - Fechar mensagem de erro oculta o alerta na tela de login
    [Documentation]    Valida que clicar no botão X fecha a mensagem de erro.
    [Tags]    login    ui    positive
    Navegar Para Pagina De Login
    Clicar Em Login
    Verificar Mensagem De Erro    ${AUTH_ERR_NO_USERNAME}
    Fechar Mensagem De Erro
    Verificar Mensagem De Erro Ausente
