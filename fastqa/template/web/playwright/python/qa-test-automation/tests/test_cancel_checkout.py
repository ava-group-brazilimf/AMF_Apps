import os

import allure
from dotenv import load_dotenv

from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage
from utils.logger import get_logger


load_dotenv()
logger = get_logger("test_cancel_checkout")

STANDARD_USER = os.getenv("STANDARD_USER", "standard_user")
PASSWORD = os.getenv("VALID_PASSWORD", "secret_sauce")


@allure.feature("Checkout")
@allure.story("Cancelar checkout na step one")
def test_should_cancel_checkout_from_step_one_and_return_to_cart(app_page):
    """Valida que o usuário consegue cancelar o checkout step one e retornar ao carrinho."""
    login_page = LoginPage(app_page)
    inventory_page = InventoryPage(app_page)
    cart_page = CartPage(app_page)
    checkout_page = CheckoutPage(app_page)

    logger.info("Iniciando fluxo de cancelamento do checkout com standard_user.")

    with allure.step("Acessar a página de login"):
        login_page.navigate()

    with allure.step("Realizar login com usuário válido"):
        login_page.login(STANDARD_USER, PASSWORD)
        login_page.should_login_successfully()

    with allure.step("Adicionar produtos selecionados ao carrinho"):
        inventory_page.add_selected_products_to_cart()
        inventory_page.should_show_cart_badge_with_quantity("4")

    with allure.step("Abrir carrinho"):
        inventory_page.open_cart()
        cart_page.should_be_on_cart_page()

    with allure.step("Ir para checkout step one"):
        cart_page.click_checkout()
        checkout_page.should_be_on_checkout_step_one()

    with allure.step("Cancelar checkout"):
        checkout_page.click_cancel()
        cart_page.should_be_on_cart_page()

    assert "cart.html" in app_page.url
    logger.info("Cancelamento do checkout validado com sucesso.")