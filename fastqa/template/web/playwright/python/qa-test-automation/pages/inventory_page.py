from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class InventoryPage(BasePage):
    """Page Object da vitrine de produtos e início do checkout."""

    CART_LINK = '[data-test="shopping-cart-link"]'
    CART_BADGE = '[data-test="shopping-cart-badge"]'

    ADD_BACKPACK_BUTTON = '[data-test="add-to-cart-sauce-labs-backpack"]'
    ADD_BIKE_LIGHT_BUTTON = '[data-test="add-to-cart-sauce-labs-bike-light"]'
    ADD_FLEECE_JACKET_BUTTON = '[data-test="add-to-cart-sauce-labs-fleece-jacket"]'
    ADD_TSHIRT_RED_BUTTON = '[data-test="add-to-cart-test.allthethings()-t-shirt-(red)"]'

    def __init__(self, page: Page):
        super().__init__(page)

    def add_backpack_to_cart(self) -> None:
        self.page.locator(self.ADD_BACKPACK_BUTTON).click()

    def add_bike_light_to_cart(self) -> None:
        self.page.locator(self.ADD_BIKE_LIGHT_BUTTON).click()

    def add_fleece_jacket_to_cart(self) -> None:
        self.page.locator(self.ADD_FLEECE_JACKET_BUTTON).click()

    def add_tshirt_red_to_cart(self) -> None:
        self.page.locator(self.ADD_TSHIRT_RED_BUTTON).click()

    def add_selected_products_to_cart(self) -> None:
        self.add_backpack_to_cart()
        self.add_bike_light_to_cart()
        self.add_fleece_jacket_to_cart()
        self.add_tshirt_red_to_cart()

    def should_show_cart_badge_with_quantity(self, quantity: str) -> None:
        expect(self.page.locator(self.CART_BADGE)).to_have_text(quantity)

    def open_cart(self) -> None:
        self.page.locator(self.CART_LINK).click()