import os

import allure
from dotenv import load_dotenv

from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage
from utils.logger import get_logger


load_dotenv()
logger = get_logger("test_problem_user_checkout")

PROBLEM_USER = os.getenv("PROBLEM_USER", "problem_user")
PASSWORD = os.getenv("VALID_PASSWORD", "secret_sauce")

FIRST_NAME = "Gabriel"
LAST_NAME = "Alves"
POSTAL_CODE = "03107000"


@allure.feature("Checkout")
@allure.story("Problem user apresenta comportamento inconsistente no checkout")
def test_problem_user_should_show_inconsistent_checkout_behavior(app_page):
    """Valida o comportamento inconsistente do problem_user durante o preenchimento do checkout."""
    login_page = LoginPage(app_page)
    inventory_page = InventoryPage(app_page)
    cart_page = CartPage(app_page)
    checkout_page = CheckoutPage(app_page)

    logger.info("Iniciando teste do fluxo problemático do problem_user.")

    with allure.step("Acessar a página de login"):
        login_page.navigate()

    with allure.step("Realizar login com problem_user"):
        login_page.login(PROBLEM_USER, PASSWORD)
        login_page.should_login_successfully()
        logger.info("problem_user autenticado com sucesso.")

    with allure.step("Adicionar itens manualmente ao carrinho"):
        inventory_page.add_backpack_to_cart()
        inventory_page.add_bike_light_to_cart()
        inventory_page.should_show_cart_badge_with_quantity("2")
        logger.info("Dois itens adicionados manualmente ao carrinho.")

    with allure.step("Abrir carrinho"):
        inventory_page.open_cart()
        cart_page.should_be_on_cart_page()
        logger.info("Carrinho aberto com sucesso.")

    with allure.step("Ir para checkout step one"):
        cart_page.click_checkout()
        checkout_page.should_be_on_checkout_step_one()
        logger.info("Checkout step one exibido com sucesso.")

    with allure.step("Preencher first name, last name e postal code"):
        checkout_page.fill_first_name(FIRST_NAME)
        last_name_filled = checkout_page.try_fill_last_name(LAST_NAME)
        checkout_page.fill_postal_code(POSTAL_CODE)

        logger.info(
            "Tentativa de preenchimento no checkout | first_name=%s | last_name=%s | postal_code=%s | last_name_persistido=%s",
            FIRST_NAME,
            LAST_NAME,
            POSTAL_CODE,
            last_name_filled,
        )

    with allure.step("Tentar avançar no checkout"):
        checkout_page.click_continue()

    current_url = app_page.url
    logger.info("URL após clicar em continue: %s", current_url)

    if "checkout-step-two.html" in current_url:
        logger.warning(
            "Comportamento inconsistente detectado: problem_user avançou para checkout-step-two."
        )
        checkout_page.should_be_on_checkout_step_two()
    else:
        logger.warning(
            "Comportamento problemático detectado: problem_user não avançou para checkout-step-two."
        )
        checkout_page.should_be_on_checkout_step_one()
        checkout_page.should_show_checkout_error("Error")

    assert "checkout-step-one.html" in current_url or "checkout-step-two.html" in current_url
    logger.info("Teste do problem_user finalizado com sucesso.")