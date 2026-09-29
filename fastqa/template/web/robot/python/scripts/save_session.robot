*** Settings ***
Documentation    Script para salvar sessão de login manualmente.
...              Abre o browser, aguarda confirmação do usuário e salva storage state.
Library          Browser
Library          OperatingSystem
Resource         ../config/variables.robot
Resource         ../config/auth_config.robot

*** Test Cases ***
Salvar Sessão De Login
    [Documentation]    Abre browser na tela de login.
    ...                O usuário faz login completo (usuário, senha, OTP).
    ...                Ao confirmar no terminal, salva storage_state.json.
    New Browser    browser=${BROWSER}    headless=False    args=['--start-maximized']
    New Context    viewport={'width': 1366, 'height': 768}    deviceScaleFactor=1
    New Page       ${AUTH_LOGIN_URL}

    Log    \n\n======================================================================    console=True
    Log    Faça o login completo no browser (usuário, senha, OTP).    console=True
    Log    Quando estiver na tela principal do PRM, crie o arquivo:    console=True
    Log    ${EXECDIR}${/}.auth${/}login_done.txt    console=True
    Log    O script vai detectar e continuar automaticamente.    console=True
    Log    ======================================================================\n    console=True

    # Aguarda até 5 minutos o usuário criar o arquivo .auth/login_done.txt
    Wait Until Created    ${EXECDIR}${/}.auth${/}login_done.txt    timeout=300s
    Remove File    ${EXECDIR}${/}.auth${/}login_done.txt

    Create Directory    ${EXECDIR}${/}.auth
    ${saved_path}=    Save Storage State
    Copy File    ${saved_path}    ${AUTH_STORAGE_PATH}
    Log    \n  Sessão salva em: ${AUTH_STORAGE_PATH}\n    console=True

    Close Browser    ALL
