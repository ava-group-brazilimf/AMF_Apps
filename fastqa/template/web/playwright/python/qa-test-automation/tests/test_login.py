import os

import allure
import pytest
from dotenv import load_dotenv

from pages.login_page import LoginPage
from utils.logger import get_logger


load_dotenv()
logger = get_logger("test_login")

PASSWORD = os.getenv("VALID_PASSWORD", "secret_sauce")

VALID_USERS = [
    os.getenv("STANDARD_USER", "standard_user"),
    os.getenv("PROBLEM_USER", "problem_user"),
    os.getenv("PERFORMANCE_GLITCH_USER", "performance_glitch_user"),
    os.getenv("ERROR_USER", "error_user"),
    os.getenv("VISUAL_USER", "visual_user"),
]

LOCKED_USER = os.getenv("LOCKED_OUT_USER", "locked_out_user")
INVALID_USER = os.getenv("INVALID_USER", "invalid_user")
INVALID_PASSWORD = os.getenv("INVALID_PASSWORD", "wrong_password")


@allure.feature("Login")
@allure.story("Usuários válidos")
@pytest.mark.parametrize("username", VALID_USERS)
def test_should_login_successfully_with_valid_users(app_page, username):
    """Valida que usuários ativos conseguem acessar o inventário com a senha correta."""
    login_page = LoginPage(app_page)

    logger.info("Iniciando teste de login com usuário válido: %s", username)
    login_page.navigate()
    login_page.login(username, PASSWORD)
    login_page.should_login_successfully()

    assert "inventory.html" in app_page.url
    logger.info("Login realizado com sucesso para o usuário: %s", username)


@allure.feature("Login")
@allure.story("Usuário bloqueado")
def test_should_show_error_for_locked_out_user(app_page):
    """Valida a mensagem de bloqueio para o usuário travado do ambiente de demonstração."""
    login_page = LoginPage(app_page)
    expected_message = "Epic sadface: Sorry, this user has been locked out."

    logger.info("Iniciando teste com usuário bloqueado.")
    login_page.navigate()
    login_page.login(LOCKED_USER, PASSWORD)
    login_page.should_show_error(expected_message)

    logger.info("Mensagem de bloqueio validada com sucesso.")


@allure.feature("Login")
@allure.story("Credenciais inválidas")
def test_should_show_error_for_invalid_credentials(app_page):
    """Valida a mensagem padrão para credenciais inexistentes."""
    login_page = LoginPage(app_page)
    expected_message = (
        "Epic sadface: Username and password do not match any user in this service"
    )

    logger.info("Iniciando teste com credenciais inválidas.")
    login_page.navigate()
    login_page.login(INVALID_USER, INVALID_PASSWORD)
    login_page.should_show_error(expected_message)

    logger.info("Mensagem de credenciais inválidas validada com sucesso.")
