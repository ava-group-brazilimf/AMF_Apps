import os
from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class LoginPage(BasePage):
    # Seletores declarados de forma explícita. Código claro vence código "esperto".
    USERNAME_INPUT = '[data-test="username"]'
    PASSWORD_INPUT = '[data-test="password"]'
    LOGIN_BUTTON = '[data-test="login-button"]'
    ERROR_MESSAGE = '[data-test="error"]'

    def __init__(self, page: Page):
        super().__init__(page)
        self.base_url = os.getenv("BASE_URL", "https://www.saucedemo.com/")
        self.inventory_url = f"{self.base_url.rstrip('/')}/inventory.html"

    def navigate(self) -> None:
        self.open(self.base_url)

    def fill_username(self, username: str) -> None:
        self.page.locator(self.USERNAME_INPUT).fill(username)

    def fill_password(self, password: str) -> None:
        self.page.locator(self.PASSWORD_INPUT).fill(password)

    def click_login(self) -> None:
        self.page.locator(self.LOGIN_BUTTON).click()

    def login(self, username: str, password: str) -> None:
        # Método de negócio: quem lê entende a intenção sem precisar decifrar o fluxo.
        self.fill_username(username)
        self.fill_password(password)
        self.click_login()

    def should_login_successfully(self) -> None:
        expect(self.page).to_have_url(self.inventory_url)

    def should_be_on_inventory_page(self) -> None:
        expect(self.page).to_have_url("https://www.saucedemo.com/inventory.html")

    def should_show_error(self, expected_message: str) -> None:
        expect(self.page.locator(self.ERROR_MESSAGE)).to_be_visible()
        expect(self.page.locator(self.ERROR_MESSAGE)).to_contain_text(expected_message)