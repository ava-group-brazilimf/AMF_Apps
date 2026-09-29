from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class CheckoutPage(BasePage):
    FIRST_NAME_INPUT = '[data-test="firstName"]'
    LAST_NAME_INPUT = '[data-test="lastName"]'
    POSTAL_CODE_INPUT = '[data-test="postalCode"]'
    CONTINUE_BUTTON = '[data-test="continue"]'
    CANCEL_BUTTON = '[data-test="cancel"]'
    FINISH_BUTTON = '[data-test="finish"]'
    COMPLETE_TEXT = '[data-test="complete-text"]'
    ERROR_MESSAGE = '[data-test="error"]'

    def __init__(self, page: Page):
        super().__init__(page)

    def should_be_on_checkout_step_one(self) -> None:
        expect(self.page).to_have_url("https://www.saucedemo.com/checkout-step-one.html")

    def should_be_on_checkout_step_two(self) -> None:
        expect(self.page).to_have_url("https://www.saucedemo.com/checkout-step-two.html")

    def should_be_on_checkout_complete(self) -> None:
        expect(self.page).to_have_url("https://www.saucedemo.com/checkout-complete.html")

    def fill_first_name(self, first_name: str) -> None:
        self.page.locator(self.FIRST_NAME_INPUT).fill(first_name)

    def fill_last_name(self, last_name: str) -> None:
        self.page.locator(self.LAST_NAME_INPUT).fill(last_name)

    def try_fill_last_name(self, last_name: str) -> bool:
        # Para o problem_user, não basta tentar preencher.
        # Precisamos validar se o valor realmente persistiu no campo.
        field = self.page.locator(self.LAST_NAME_INPUT)
        field.fill(last_name)
        current_value = field.input_value()
        return current_value == last_name

    def fill_postal_code(self, postal_code: str) -> None:
        self.page.locator(self.POSTAL_CODE_INPUT).fill(postal_code)

    def fill_checkout_information(self, first_name: str, last_name: str, postal_code: str) -> None:
        self.fill_first_name(first_name)
        self.fill_last_name(last_name)
        self.fill_postal_code(postal_code)

    def click_continue(self) -> None:
        self.page.locator(self.CONTINUE_BUTTON).click()

    def click_cancel(self) -> None:
        self.page.locator(self.CANCEL_BUTTON).click()

    def click_finish(self) -> None:
        self.page.locator(self.FINISH_BUTTON).click()

    def should_show_order_success_message(self) -> None:
        expect(self.page.locator(self.COMPLETE_TEXT)).to_have_text(
            "Your order has been dispatched, and will arrive just as fast as the pony can get there!"
        )

    def should_show_checkout_error(self, expected_message: str) -> None:
        expect(self.page.locator(self.ERROR_MESSAGE)).to_be_visible()
        expect(self.page.locator(self.ERROR_MESSAGE)).to_contain_text(expected_message)