*** Settings ***
Documentation    Recursos de Autenticação — SauceDemo
...              Fluxo: abre browser → navega para login → preenche credenciais → valida inventário.
...              SauceDemo não possui MFA nem storage state — login sempre realizado no início da suíte.
Library          Browser
Library          OperatingSystem
Resource         ../config/variables.robot
Resource         ../config/auth_config.robot

*** Keywords ***
# ===========================================================================
# Entry point principal — chamado em Suite Setup de todas as suítes
# ===========================================================================
Autenticar Na Aplicacao
    [Documentation]    Abre browser, navega para a tela de login e autentica com
    ...                as credenciais configuradas em variables.robot / .env.
    New Browser    browser=${BROWSER}    headless=${HEADLESS}
    New Context    viewport={'width': 1366, 'height': 768}
    New Page       ${AUTH_LOGIN_URL}
    Wait For Elements State    ${AUTH_SEL_USER}    visible    timeout=${TIMEOUT}
    Fill Text    ${AUTH_SEL_USER}      ${LOGIN_USER}
    Fill Text    ${AUTH_SEL_PASSWORD}  ${LOGIN_PASS}
    Click        ${AUTH_SEL_SUBMIT}
    Wait For Elements State    ${AUTH_POST_LOGIN_SELECTOR}    visible    timeout=${TIMEOUT}
    Log    [Auth] Login realizado com sucesso. URL: ${AUTH_POST_LOGIN_URL}    INFO

# ===========================================================================
# Login com credenciais explícitas — usado nos testes de login negativos
# ===========================================================================
Realizar Login Com Credenciais
    [Documentation]    Navega para a tela de login e autentica com as credenciais fornecidas.
    ...                Não valida sucesso — use a keyword de verificação correspondente.
    [Arguments]    ${usuario}    ${senha}
    Go To    ${AUTH_LOGIN_URL}
    Wait For Elements State    ${AUTH_SEL_USER}    visible    timeout=${TIMEOUT}
    Fill Text    ${AUTH_SEL_USER}      ${usuario}
    Fill Text    ${AUTH_SEL_PASSWORD}  ${senha}
    Click        ${AUTH_SEL_SUBMIT}

# ===========================================================================
# Verificações pós-login
# ===========================================================================
Verificar Login Com Sucesso
    [Documentation]    Valida que o login foi bem-sucedido: URL correta e inventário visível.
    Get Url    ==    ${AUTH_POST_LOGIN_URL}
    Wait For Elements State    ${AUTH_POST_LOGIN_SELECTOR}    visible    timeout=${TIMEOUT}

Verificar Erro De Login
    [Documentation]    Valida que a mensagem de erro de login está visível e contém o texto esperado.
    [Arguments]    ${mensagem_esperada}
    Wait For Elements State    ${AUTH_SEL_ERROR}    visible    timeout=${TIMEOUT}
    Get Text    ${AUTH_SEL_ERROR}    contains    ${mensagem_esperada}

# ===========================================================================
# Logout — abrir menu lateral e clicar em Logout
# ===========================================================================
Realizar Logout
    [Documentation]    Abre o menu lateral, clica em Logout e valida retorno à tela de login.
    Click    id=react-burger-menu-btn
    Wait For Elements State    id=logout_sidebar_link    visible    timeout=${TIMEOUT}
    Click    id=logout_sidebar_link
    Wait For Elements State    ${AUTH_SEL_USER}    visible    timeout=${TIMEOUT}
    Log    [Auth] Logout realizado com sucesso.    INFO


