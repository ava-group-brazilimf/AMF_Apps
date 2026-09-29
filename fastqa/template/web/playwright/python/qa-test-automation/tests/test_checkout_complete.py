import os

import allure
from dotenv import load_dotenv

from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage
from utils.logger import get_logger


load_dotenv()
logger = get_logger("test_checkout_complete")

STANDARD_USER = os.getenv("STANDARD_USER", "standard_user")
PASSWORD = os.getenv("VALID_PASSWORD", "secret_sauce")

FIRST_NAME = "Gabriel"
LAST_NAME = "Alves"
POSTAL_CODE = "06000-000"


@allure.feature("Checkout")
@allure.story("Finalizar compra com sucesso")
def test_should_complete_checkout_successfully(app_page):
    """Valida o fluxo completo de checkout até a mensagem final de sucesso."""
    login_page = LoginPage(app_page)
    inventory_page = InventoryPage(app_page)
    cart_page = CartPage(app_page)
    checkout_page = CheckoutPage(app_page)

    logger.info("Iniciando fluxo completo de checkout com standard_user.")

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

    with allure.step("Preencher informações do cliente"):
        checkout_page.fill_checkout_information(
            first_name=FIRST_NAME,
            last_name=LAST_NAME,
            postal_code=POSTAL_CODE,
        )

    with allure.step("Continuar para checkout step two"):
        checkout_page.click_continue()
        checkout_page.should_be_on_checkout_step_two()

    with allure.step("Finalizar compra"):
        checkout_page.click_finish()
        checkout_page.should_be_on_checkout_complete()
        checkout_page.should_show_order_success_message()

    assert "checkout-complete.html" in app_page.url
    logger.info("Checkout finalizado com sucesso.")