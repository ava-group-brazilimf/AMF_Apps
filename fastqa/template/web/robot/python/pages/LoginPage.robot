*** Settings ***
Documentation    Page Object — Login Page (SauceDemo)
...              Locators validados via inspeção DOM real (Playwright MCP) — 14/05/2026
...              URL: https://www.saucedemo.com/
Library          Browser
Resource         ../config/variables.robot
Resource         ../config/auth_config.robot

*** Variables ***
# ===========================================================================
# URL
# ===========================================================================
${URL_LOGIN}                  ${BASE_URL}${ROUTE_LOGIN}

# ===========================================================================
# Elementos do formulário de login
# ===========================================================================
${INPUT_USERNAME}             id=user-name
${INPUT_PASSWORD}             id=password
${BTN_LOGIN}                  id=login-button
${MSG_ERROR}                  [data-test="error"]
${ICON_ERROR_CLOSE}           .error-button

# ===========================================================================
# Estrutura da página
# ===========================================================================
${LOGIN_LOGO}                 .login_logo
${LOGIN_WRAPPER}              .login_wrapper
${LOGIN_CONTAINER}            .login_container
${ACCEPTED_USERS_HEADER}      h4:has-text("Accepted usernames are:")
${PASSWORD_HEADER}            h4:has-text("Password for all users:")

*** Keywords ***
# ===========================================================================
# Navegação
# ===========================================================================
Navegar Para Pagina De Login
    [Documentation]    Navega para a tela de login e aguarda o campo de usuário.
    Go To    ${URL_LOGIN}
    Wait For Elements State    ${INPUT_USERNAME}    visible    timeout=${TIMEOUT}

# ===========================================================================
# Interações com o formulário
# ===========================================================================
Preencher Credenciais
    [Documentation]    Preenche os campos de usuário e senha.
    [Arguments]    ${usuario}    ${senha}
    Fill Text    ${INPUT_USERNAME}    ${usuario}
    Fill Text    ${INPUT_PASSWORD}    ${senha}

Limpar Credenciais
    [Documentation]    Limpa os campos de usuário e senha.
    Clear Text    ${INPUT_USERNAME}
    Clear Text    ${INPUT_PASSWORD}

Clicar Em Login
    [Documentation]    Clica no botão de login.
    Click    ${BTN_LOGIN}

Realizar Login Com
    [Documentation]    Navega para o login, preenche credenciais e submete.
    [Arguments]    ${usuario}    ${senha}
    Navegar Para Pagina De Login
    Preencher Credenciais    ${usuario}    ${senha}
    Clicar Em Login

# ===========================================================================
# Verificações
# ===========================================================================
Verificar Logo Exibido
    [Documentation]    Valida que o logo "Swag Labs" está visível.
    Wait For Elements State    ${LOGIN_LOGO}    visible    timeout=${TIMEOUT}
    Get Text    ${LOGIN_LOGO}    ==    Swag Labs

Verificar Elementos Estruturais Presentes
    [Documentation]    Valida que todos os elementos da tela de login estão visíveis.
    Wait For Elements State    ${LOGIN_LOGO}             visible    timeout=${TIMEOUT}
    Wait For Elements State    ${INPUT_USERNAME}         visible    timeout=${TIMEOUT}
    Wait For Elements State    ${INPUT_PASSWORD}         visible    timeout=${TIMEOUT}
    Wait For Elements State    ${BTN_LOGIN}              visible    timeout=${TIMEOUT}
    Wait For Elements State    ${ACCEPTED_USERS_HEADER}  visible    timeout=${TIMEOUT}
    Wait For Elements State    ${PASSWORD_HEADER}        visible    timeout=${TIMEOUT}

Verificar Mensagem De Erro
    [Documentation]    Valida que a mensagem de erro está visível e contém o texto esperado.
    [Arguments]    ${mensagem}
    Wait For Elements State    ${MSG_ERROR}    visible    timeout=${TIMEOUT}
    Get Text    ${MSG_ERROR}    contains    ${mensagem}

Verificar Mensagem De Erro Ausente
    [Documentation]    Valida que não há mensagem de erro visível.
    Wait For Elements State    ${MSG_ERROR}    hidden    timeout=${TIMEOUT}

Fechar Mensagem De Erro
    [Documentation]    Clica no botão X para fechar a mensagem de erro.
    Click    ${ICON_ERROR_CLOSE}
    Wait For Elements State    ${MSG_ERROR}    hidden    timeout=${TIMEOUT}
