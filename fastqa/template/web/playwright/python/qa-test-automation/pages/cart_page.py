from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class CartPage(BasePage):
    """Page Object do carrinho."""

    CHECKOUT_BUTTON = '[data-test="checkout"]'

    def __init__(self, page: Page):
        super().__init__(page)

    def should_be_on_cart_page(self) -> None:
        expect(self.page).to_have_url("https://www.saucedemo.com/cart.html")

    def click_checkout(self) -> None:
        self.page.locator(self.CHECKOUT_BUTTON).click()