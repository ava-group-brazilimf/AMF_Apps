*** Settings ***
Documentation    Configuração de Autenticação — SauceDemo
...              Aplicação: SauceDemo (https://www.saucedemo.com)
...              Geração: PBI-001 | Fluxo E2E de Compra — FastQA

*** Variables ***
# ===========================================================================
# URL de login
# Validado via Playwright MCP — 14/05/2026
# ===========================================================================
${AUTH_LOGIN_URL}             ${BASE_URL}${ROUTE_LOGIN}

# ===========================================================================
# Seletores do formulário de login
# Validados via inspeção DOM real (saucedemo.com) — 14/05/2026
# ===========================================================================
${AUTH_SEL_USER}              id=user-name
${AUTH_SEL_PASSWORD}          id=password
${AUTH_SEL_SUBMIT}            id=login-button
${AUTH_SEL_ERROR}             [data-test="error"]
${AUTH_SEL_ERROR_CLOSE}       .error-button

# ===========================================================================
# Requer MFA: SauceDemo não possui 2FA
# ===========================================================================
${AUTH_REQUIRES_MFA}          ${FALSE}

# ===========================================================================
# Seletores pós-login — verifica que o login foi bem-sucedido
# ===========================================================================
${AUTH_POST_LOGIN_SELECTOR}   .inventory_list
${AUTH_POST_LOGIN_URL}        ${BASE_URL}${ROUTE_INVENTORY}

# ===========================================================================
# Mensagens de erro de login (retornadas pelo SauceDemo)
# ===========================================================================
${AUTH_ERR_LOCKED}            Epic sadface: Sorry, this user has been locked out.
${AUTH_ERR_INVALID_CREDS}     Epic sadface: Username and password do not match
${AUTH_ERR_NO_USERNAME}       Epic sadface: Username is required
${AUTH_ERR_NO_PASSWORD}       Epic sadface: Password is required
